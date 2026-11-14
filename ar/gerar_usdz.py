"""Converte os modelos .glb em .usdz para o iPhone (AR Quick Look), mantendo as animações.

Uso:  pip install usd-core numpy pillow
      python3 gerar_usdz.py
Lê modelos/*.glb e grava modelos/*.usdz.
"""
import io, json, os, re, shutil, struct, sys, tempfile
import numpy as np
from PIL import Image
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade, UsdUtils, Vt

FPS = 30
AQUI = os.path.dirname(os.path.abspath(__file__))
PASTA = os.path.join(AQUI, "modelos")

CTYPE = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def read_glb(path):
    d = open(path, "rb").read()
    jl = struct.unpack("<I", d[12:16])[0]
    js = json.loads(d[20:20 + jl])
    bl = struct.unpack("<I", d[20 + jl:24 + jl])[0]
    return js, d[28 + jl:28 + jl + bl]


def accessor(js, binb, i):
    a = js["accessors"][i]; bv = js["bufferViews"][a["bufferView"]]
    dt = np.dtype(CTYPE[a["componentType"]]); n = NCOMP[a["type"]]
    off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    stride = bv.get("byteStride", 0) or dt.itemsize * n
    raw = np.frombuffer(binb, np.uint8, count=stride * (a["count"] - 1) + dt.itemsize * n, offset=off)
    out = np.lib.stride_tricks.as_strided(raw, (a["count"], dt.itemsize * n), (stride, 1)).copy()
    arr = out.view(dt).reshape(a["count"], n)
    if a.get("normalized"):
        arr = arr.astype(np.float32) / np.iinfo(dt).max
    return arr if n > 1 else arr[:, 0]


def image_bytes(js, binb, img_i):
    im = js["images"][img_i]; bv = js["bufferViews"][im["bufferView"]]
    o = bv.get("byteOffset", 0)
    return Image.open(io.BytesIO(binb[o:o + bv["byteLength"]]))


def safe(name, i):
    s = re.sub(r"[^A-Za-z0-9_]", "_", name or "n")
    return f"n{i}_{s}"[:60]


def convert(glb_path, usdz_path):
    js, binb = read_glb(glb_path)
    work = tempfile.mkdtemp()
    os.makedirs(os.path.join(work, "tex"))
    usdc = os.path.join(work, "cena.usdc")
    stage = Usd.Stage.CreateNew(usdc)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    root = UsdGeom.Xform.Define(stage, "/Raiz")
    stage.SetDefaultPrim(root.GetPrim())

    # ---- animações por nó
    anims = {}
    clip = 0.0
    for an in js.get("animations", []):
        for ch in an["channels"]:
            s = an["samplers"][ch["sampler"]]
            t = accessor(js, binb, s["input"]); v = accessor(js, binb, s["output"])
            anims.setdefault(ch["target"]["node"], {})[ch["target"]["path"]] = (t, v)
            clip = max(clip, float(t.max()))
    if clip:
        stage.SetTimeCodesPerSecond(FPS); stage.SetFramesPerSecond(FPS)
        stage.SetStartTimeCode(0); stage.SetEndTimeCode(round(clip * FPS))

    # ---- materiais (texturas com fator já aplicado, para máxima compatibilidade)
    tex_cache = {}

    def baked(img_i, factor, role):
        key = (img_i, tuple(round(f, 4) for f in factor), role)
        if key in tex_cache:
            return tex_cache[key]
        im = image_bytes(js, binb, img_i)
        has_alpha = im.mode in ("RGBA", "LA") or "transparency" in im.info
        im = im.convert("RGBA" if has_alpha else "RGB")
        a = np.asarray(im).astype(np.float32)
        a[..., :3] *= np.array(factor[:3], np.float32)
        out = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), im.mode)
        ext = "png" if has_alpha else "jpg"
        rel = f"tex/{role}_{img_i}_{len(tex_cache)}.{ext}"
        asset = "./" + rel
        out.save(os.path.join(work, rel), quality=88) if ext == "jpg" else out.save(os.path.join(work, rel))
        tex_cache[key] = (asset, has_alpha)
        return tex_cache[key]

    mats = {}
    mat_scope = UsdGeom.Scope.Define(stage, "/Raiz/Materiais")

    def material(mi):
        if mi in mats:
            return mats[mi]
        m = js["materials"][mi] if mi is not None else {}
        pbr = m.get("pbrMetallicRoughness", {})
        bc = pbr.get("baseColorFactor", [1, 1, 1, 1])
        path = f"/Raiz/Materiais/{safe(m.get('name'), mi if mi is not None else 999)}"
        mat = UsdShade.Material.Define(stage, path)
        sh = UsdShade.Shader.Define(stage, path + "/PBR")
        sh.CreateIdAttr("UsdPreviewSurface")
        sh.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(float(pbr.get("metallicFactor", 1.0)))
        sh.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(float(pbr.get("roughnessFactor", 1.0)))
        blend = m.get("alphaMode") == "BLEND"
        reader = None

        def tex_node(rel, name):
            nonlocal reader
            if reader is None:
                reader = UsdShade.Shader.Define(stage, path + "/LeitorUV")
                reader.CreateIdAttr("UsdPrimvarReader_float2")
                reader.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st")
            t = UsdShade.Shader.Define(stage, path + "/" + name)
            t.CreateIdAttr("UsdUVTexture")
            t.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(rel)
            t.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(reader.ConnectableAPI(), "result")
            t.CreateInput("wrapS", Sdf.ValueTypeNames.Token).Set("repeat")
            t.CreateInput("wrapT", Sdf.ValueTypeNames.Token).Set("clamp")
            return t

        if "baseColorTexture" in pbr:
            rel, alpha = baked(js["textures"][pbr["baseColorTexture"]["index"]]["source"], bc, "cor")
            t = tex_node(rel, "TexCor")
            t.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)
            sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(t.ConnectableAPI(), "rgb")
            if blend and alpha:
                t.CreateOutput("a", Sdf.ValueTypeNames.Float)
                sh.CreateInput("opacity", Sdf.ValueTypeNames.Float).ConnectToSource(t.ConnectableAPI(), "a")
            elif blend:
                sh.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(float(bc[3]))
        else:
            sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*bc[:3]))
            if blend:
                sh.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(float(bc[3]))
        ef = m.get("emissiveFactor")
        if "emissiveTexture" in m and ef:
            rel, _ = baked(js["textures"][m["emissiveTexture"]["index"]]["source"], ef, "brilho")
            t = tex_node(rel, "TexBrilho")
            t.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)
            sh.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(t.ConnectableAPI(), "rgb")
        elif ef and any(ef):
            sh.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*ef))
        sh.CreateOutput("surface", Sdf.ValueTypeNames.Token)
        mat.CreateSurfaceOutput().ConnectToSource(sh.ConnectableAPI(), "surface")
        mats[mi] = (mat, bool(m.get("doubleSided")))
        return mats[mi]

    # ---- nós e malhas
    def build(ni, parent_path):
        n = js["nodes"][ni]
        path = f"{parent_path}/{safe(n.get('name'), ni)}"
        xf = UsdGeom.Xform.Define(stage, path)
        an = anims.get(ni, {})
        if "matrix" in n and not an:
            M = np.array(n["matrix"], float).reshape(4, 4)  # glTF coluna-a-coluna = convenção de linha do USD
            xf.AddTransformOp().Set(Gf.Matrix4d(*M.flatten().tolist()))
        else:
            if "translation" in n or "translation" in an:
                op = xf.AddTranslateOp()
                if "translation" in an:
                    for t, v in zip(*an["translation"]):
                        op.Set(Gf.Vec3d(*map(float, v)), round(float(t) * FPS, 4))
                else:
                    op.Set(Gf.Vec3d(*n["translation"]))
            if "rotation" in n or "rotation" in an:
                op = xf.AddOrientOp()
                if "rotation" in an:
                    for t, q in zip(*an["rotation"]):
                        op.Set(Gf.Quatf(float(q[3]), float(q[0]), float(q[1]), float(q[2])), round(float(t) * FPS, 4))
                else:
                    q = n["rotation"]; op.Set(Gf.Quatf(q[3], q[0], q[1], q[2]))
            if "scale" in n or "scale" in an:
                op = xf.AddScaleOp()
                if "scale" in an:
                    for t, v in zip(*an["scale"]):
                        op.Set(Gf.Vec3f(*map(float, v)), round(float(t) * FPS, 4))
                else:
                    op.Set(Gf.Vec3f(*n["scale"]))
        if "mesh" in n:
            for pi, prim in enumerate(js["meshes"][n["mesh"]]["primitives"]):
                if prim.get("mode", 4) != 4:
                    continue
                at = prim["attributes"]
                P = accessor(js, binb, at["POSITION"])
                I = accessor(js, binb, prim["indices"]).astype(np.int32) if "indices" in prim else np.arange(len(P), dtype=np.int32)
                mesh = UsdGeom.Mesh.Define(stage, f"{path}/malha{pi}")
                mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(P.astype(np.float32)))
                mesh.CreateFaceVertexCountsAttr(Vt.IntArray([3] * (len(I) // 3)))
                mesh.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(I))
                mesh.CreateSubdivisionSchemeAttr("none")
                mesh.CreateExtentAttr(Vt.Vec3fArray([Gf.Vec3f(*P.min(0).tolist()), Gf.Vec3f(*P.max(0).tolist())]))
                if "NORMAL" in at:
                    N = accessor(js, binb, at["NORMAL"]).astype(np.float32)
                    mesh.CreateNormalsAttr(Vt.Vec3fArray.FromNumpy(N)); mesh.SetNormalsInterpolation("vertex")
                if "TEXCOORD_0" in at:
                    UV = accessor(js, binb, at["TEXCOORD_0"]).astype(np.float32).copy(); UV[:, 1] = 1 - UV[:, 1]
                    pv = UsdGeom.PrimvarsAPI(mesh).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.vertex)
                    pv.Set(Vt.Vec2fArray.FromNumpy(UV))
                mat, double = material(prim.get("material"))
                if double:
                    mesh.CreateDoubleSidedAttr(True)
                UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(mat)
        for c in n.get("children", []):
            build(c, path)

    for ni in js["scenes"][js.get("scene", 0)]["nodes"]:
        build(ni, "/Raiz")
    stage.GetRootLayer().Save()

    cwd = os.getcwd(); os.chdir(work)
    try:
        if os.path.exists(usdz_path):
            os.remove(usdz_path)
        ok = UsdUtils.CreateNewARKitUsdzPackage("cena.usdc", usdz_path)
    finally:
        os.chdir(cwd)
    shutil.rmtree(work)
    return ok


def check(path):
    """Abre o .usdz e confere se todas as texturas existem dentro do pacote."""
    st = Usd.Stage.Open(path)
    errs = []
    for prim in st.Traverse():
        if prim.GetTypeName() == "Shader":
            a = prim.GetAttribute("inputs:file")
            if a and a.Get() is not None and not a.Get().resolvedPath:
                errs.append(f"textura ausente: {a.Get().path}")
    return errs, []


if __name__ == "__main__":
    nomes = sys.argv[1:] or sorted(f[:-4] for f in os.listdir(PASTA) if f.endswith(".glb"))
    for nome in nomes:
        out = os.path.join(PASTA, nome + ".usdz")
        ok = convert(os.path.join(PASTA, nome + ".glb"), out)
        errs, fails = check(out)
        print(f"{nome:16s} {'ok' if ok else 'FALHOU':6s} {os.path.getsize(out) // 1024:6d} KB  erros={len(errs)} falhas={len(fails)}")
        for e in (errs + fails)[:4]:
            print("   ", e)
