"""AstroByte AR: gera os 10 modelos .glb.

Texturas reais da NASA:
  - github.com/nasa/NASA-3D-Resources (Images and Textures): Marte, Júpiter, Saturno, Vênus, Netuno,
    Plutão, Caronte, luas de Júpiter, mapa estelar Tycho, foto da Lua (Apollo) e o modelo do Spitzer.
  - Blue Marble Next Generation (NASA), via github.com/NASAWorldWind/WebWorldWind.
Coloque as imagens em ./texturas (veja o LEIA-ME) e rode:  python3 gerar_modelos.py

Cada .glb traz:
  - cartões de informação em português dentro do próprio 3D (aparecem na câmera do Android e do iPhone);
  - uma animação (rotação dos planetas, luas e corpos em órbita).
"""
import io, json, math, os, struct
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

AQUI = os.path.dirname(os.path.abspath(__file__))
TEX = os.environ.get("TEXTURAS", os.path.join(AQUI, "texturas"))
OUT = os.path.join(AQUI, "modelos")
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
HOTSPOTS = {}


# ============================================================ escritor de GLB (glTF 2.0) mínimo
class GLB:
    def __init__(self):
        self.bin = bytearray()
        self.j = {"asset": {"version": "2.0", "generator": "AstroByte"}, "scenes": [{"nodes": []}], "scene": 0,
                  "nodes": [], "meshes": [], "materials": [], "accessors": [], "bufferViews": [],
                  "images": [], "textures": [], "samplers": [{"magFilter": 9729, "minFilter": 9987,
                                                              "wrapS": 10497, "wrapT": 33071}]}
        self.anim = {"channels": [], "samplers": []}
        self._img_cache = {}

    def _view(self, data, target=None):
        while len(self.bin) % 4:
            self.bin.append(0)
        bv = {"buffer": 0, "byteOffset": len(self.bin), "byteLength": len(data)}
        if target:
            bv["target"] = target
        self.bin += data
        self.j["bufferViews"].append(bv)
        return len(self.j["bufferViews"]) - 1

    def _acc(self, arr, typ, target=None, minmax=False):
        arr = np.ascontiguousarray(arr)
        comp = 5126 if arr.dtype == np.float32 else 5125
        a = {"bufferView": self._view(arr.tobytes(), target), "componentType": comp,
             "count": int(arr.shape[0]), "type": typ}
        if minmax:
            a["min"] = arr.min(0).tolist() if arr.ndim > 1 else [float(arr.min())]
            a["max"] = arr.max(0).tolist() if arr.ndim > 1 else [float(arr.max())]
        self.j["accessors"].append(a)
        return len(self.j["accessors"]) - 1

    def image(self, im, key=None):
        if key and key in self._img_cache:
            return self._img_cache[key]
        b = io.BytesIO()
        if im.mode == "RGBA":
            im.save(b, "PNG", optimize=True); mime = "image/png"
        else:
            im.convert("RGB").save(b, "JPEG", quality=84, optimize=True); mime = "image/jpeg"
        self.j["images"].append({"bufferView": self._view(b.getvalue()), "mimeType": mime})
        self.j["textures"].append({"source": len(self.j["images"]) - 1, "sampler": 0})
        t = len(self.j["textures"]) - 1
        if key:
            self._img_cache[key] = t
        return t

    def material(self, name, color=(1, 1, 1, 1), tex=None, metallic=0.0, rough=0.85,
                 emissive=None, emissive_tex=None, blend=False, double=False):
        pbr = {"baseColorFactor": list(color) if len(color) == 4 else list(color) + [1],
               "metallicFactor": metallic, "roughnessFactor": rough}
        if tex is not None:
            pbr["baseColorTexture"] = {"index": tex}
        m = {"name": name, "pbrMetallicRoughness": pbr}
        if emissive:
            m["emissiveFactor"] = list(emissive)
        if emissive_tex is not None:
            m["emissiveTexture"] = {"index": emissive_tex}
        if blend:
            m["alphaMode"] = "BLEND"
        if double:
            m["doubleSided"] = True
        self.j["materials"].append(m)
        return len(self.j["materials"]) - 1

    def mesh(self, name, pos, nrm, uv, idx, mat):
        attrs = {"POSITION": self._acc(np.asarray(pos, np.float32), "VEC3", 34962, True),
                 "NORMAL": self._acc(np.asarray(nrm, np.float32), "VEC3", 34962)}
        if uv is not None:
            attrs["TEXCOORD_0"] = self._acc(np.asarray(uv, np.float32), "VEC2", 34962)
        ind = self._acc(np.asarray(idx, np.uint32).reshape(-1), "SCALAR", 34963)
        self.j["meshes"].append({"name": name, "primitives": [{"attributes": attrs, "indices": ind, "material": mat}]})
        return len(self.j["meshes"]) - 1

    def node(self, name, mesh=None, t=None, r=None, s=None, children=None, parent=None):
        n = {"name": name}
        if mesh is not None: n["mesh"] = mesh
        if t is not None: n["translation"] = [float(v) for v in t]
        if r is not None: n["rotation"] = [float(v) for v in r]
        if s is not None: n["scale"] = [float(v) for v in s]
        self.j["nodes"].append(n)
        i = len(self.j["nodes"]) - 1
        if parent is None:
            self.j["scenes"][0]["nodes"].append(i)
        else:
            self.j["nodes"][parent].setdefault("children", []).append(i)
        return i

    def channel(self, node, path, times, values):
        typ = "VEC4" if path == "rotation" else "VEC3"
        inp = self._acc(np.asarray(times, np.float32), "SCALAR", minmax=True)
        out = self._acc(np.asarray(values, np.float32), typ)
        self.anim["samplers"].append({"input": inp, "output": out, "interpolation": "LINEAR"})
        self.anim["channels"].append({"sampler": len(self.anim["samplers"]) - 1,
                                      "target": {"node": node, "path": path}})

    def spin(self, node, period, clip, reverse=False, base=None):
        """Gira o nó em torno do seu eixo Y; clip deve ser múltiplo de period."""
        steps = int(round(clip / period)) * 8
        times = np.linspace(0, clip, steps + 1)
        sign = -1 if reverse else 1
        vals = []
        for t in times:
            a = sign * 2 * math.pi * (t / period)
            q = (0, math.sin(a / 2), 0, math.cos(a / 2))
            vals.append(qmul(base, q) if base else q)
        self.channel(node, "rotation", times, vals)

    def save(self, path, clip_name="Animação"):
        if self.anim["channels"]:
            self.anim["name"] = clip_name
            self.j["animations"] = [self.anim]
        for k in ("images", "textures"):
            if not self.j[k]:
                del self.j[k]
        if "textures" not in self.j:
            del self.j["samplers"]
        while len(self.bin) % 4:
            self.bin.append(0)
        self.j["buffers"] = [{"byteLength": len(self.bin)}]
        js = json.dumps(self.j, separators=(",", ":"), ensure_ascii=False).encode()
        while len(js) % 4:
            js += b" "
        total = 12 + 8 + len(js) + 8 + len(self.bin)
        with open(path, "wb") as f:
            f.write(b"glTF" + struct.pack("<II", 2, total) + struct.pack("<I", len(js)) + b"JSON" + js
                    + struct.pack("<I", len(self.bin)) + b"BIN\x00" + bytes(self.bin))


def qmul(a, b):
    ax, ay, az, aw = a; bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz)


def qaxis(axis, deg):
    a = math.radians(deg) / 2
    x, y, z = axis
    return (x * math.sin(a), y * math.sin(a), z * math.sin(a), math.cos(a))


# ============================================================ geometria
def sphere_geo(r, seg=64, rings=32):
    pos, nrm, uv, idx = [], [], [], []
    for j in range(rings + 1):
        v = j / rings
        lat = math.pi / 2 - v * math.pi
        for i in range(seg + 1):
            u = i / seg
            lon = u * 2 * math.pi - math.pi
            n = (math.cos(lat) * math.cos(lon), math.sin(lat), -math.cos(lat) * math.sin(lon))
            nrm.append(n); pos.append(tuple(c * r for c in n)); uv.append((u, v))
    w = seg + 1
    for j in range(rings):
        for i in range(seg):
            a, b, c, d = j * w + i, j * w + i + 1, (j + 1) * w + i, (j + 1) * w + i + 1
            if j != 0: idx.append((a, c, b))
            if j != rings - 1: idx.append((b, c, d))
    return pos, nrm, uv, idx


def flat(pos, idx):
    """Duplica vértices por face (sombreado plano) e calcula normais."""
    P, N, I = [], [], []
    pos = np.asarray(pos, float)
    for f in idx:
        a, b, c = pos[list(f)]
        n = np.cross(b - a, c - a); n /= (np.linalg.norm(n) + 1e-12)
        k = len(P); P += [a, b, c]; N += [n, n, n]; I.append((k, k + 1, k + 2))
    return P, N, None, I


def prism(r, h, sides, y0=0.0):
    pos, idx = [], []
    for k in range(sides):
        a = 2 * math.pi * k / sides
        pos += [(r * math.cos(a), y0, r * math.sin(a)), (r * math.cos(a), y0 + h, r * math.sin(a))]
    pos += [(0, y0, 0), (0, y0 + h, 0)]
    cb, ct = 2 * sides, 2 * sides + 1
    for k in range(sides):
        n = (k + 1) % sides
        a0, a1, b0, b1 = 2 * k, 2 * k + 1, 2 * n, 2 * n + 1
        idx += [(a0, a1, b0), (b0, a1, b1), (cb, a0, b0), (ct, b1, a1)]
    return flat(pos, idx)


def box(sx, sy, sz):
    x, y, z = sx / 2, sy / 2, sz / 2
    v = [(-x, -y, -z), (x, -y, -z), (x, y, -z), (-x, y, -z), (-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z)]
    f = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4), (3, 7, 6), (3, 6, 2), (0, 4, 7), (0, 7, 3), (1, 2, 6), (1, 6, 5)]
    return flat(v, f)


def frustum_shell(r0, r1, h, y0, thick=0.008, seg=72):
    v, f = [], []
    for rr, yy in ((r0, y0), (r1, y0 + h)):
        for s in range(seg):
            a = 2 * math.pi * s / seg; v.append((rr * math.cos(a), yy, rr * math.sin(a)))
    for rr, yy in ((r0, y0), (r1, y0 + h)):
        for s in range(seg):
            a = 2 * math.pi * s / seg; v.append(((rr - thick) * math.cos(a), yy, (rr - thick) * math.sin(a)))
    O0, O1, I0, I1 = 0, seg, 2 * seg, 3 * seg
    for s in range(seg):
        n = (s + 1) % seg
        f += [(O0 + s, O1 + s, O0 + n), (O0 + n, O1 + s, O1 + n), (I0 + s, I0 + n, I1 + s), (I0 + n, I1 + n, I1 + s),
              (O1 + s, I1 + s, O1 + n), (O1 + n, I1 + s, I1 + n), (O0 + s, O0 + n, I0 + s), (O0 + n, I0 + n, I0 + s)]
    pos = np.array(v)
    # normais suaves: radiais para fora/dentro
    nrm = []
    for k, p in enumerate(v):
        rad = np.array([p[0], 0, p[2]]); rad /= np.linalg.norm(rad)
        nrm.append(tuple(rad if k < 2 * seg else -rad))
    return v, nrm, None, f


def tube(points, radius, sides=8):
    pts = np.asarray(points, float)
    t = np.gradient(pts, axis=0); t /= np.linalg.norm(t, axis=1)[:, None] + 1e-12
    ref = np.array([0, 1, 0.0]) if abs(t[0][1]) < 0.9 else np.array([1, 0, 0.0])
    nm = np.cross(t[0], ref); nm /= np.linalg.norm(nm)
    pos, nrm, idx = [], [], []
    for k in range(len(pts)):
        if k:
            nm = nm - np.dot(nm, t[k]) * t[k]; nm /= np.linalg.norm(nm)
        bn = np.cross(t[k], nm)
        for s in range(sides):
            a = 2 * math.pi * s / sides
            d = math.cos(a) * nm + math.sin(a) * bn
            pos.append(pts[k] + radius * d); nrm.append(d)
    for k in range(len(pts) - 1):
        for s in range(sides):
            a = k * sides + s; b = k * sides + (s + 1) % sides
            idx += [(a, a + sides, b), (b, a + sides, b + sides)]
    return pos, nrm, None, idx


def ring_geo(r_in, r_out, seg=128):
    """Anel plano (XZ) com as duas faces; u = posição radial (0 dentro, 1 fora)."""
    pos, nrm, uv, idx = [], [], [], []
    for side, ny in ((0, 1), (1, -1)):
        base = len(pos)
        for s in range(seg + 1):
            a = 2 * math.pi * s / seg
            for k, rr in enumerate((r_in, r_out)):
                pos.append((rr * math.cos(a), 0, rr * math.sin(a))); nrm.append((0, ny, 0)); uv.append((k, 0.5))
        for s in range(seg):
            a, b, c, d = base + 2 * s, base + 2 * s + 1, base + 2 * s + 2, base + 2 * s + 3
            idx += [(a, c, b), (b, c, d)] if ny < 0 else [(a, b, c), (b, d, c)]
    return pos, nrm, uv, idx


# ============================================================ texturas
def load(name, size=None):
    im = Image.open(os.path.join(TEX, name)).convert("RGB")
    return im.resize(size, Image.LANCZOS) if size else im


def moon_texture():
    """Foto da Lua cheia (Apollo, NASA) reprojetada no hemisfério voltado para a Terra.
    O hemisfério oposto recebe um tom neutro, porque a foto não mostra esse lado."""
    src = np.asarray(Image.open(os.path.join(TEX, "lua_apollo.jpg")).convert("RGB"), float)
    g = src.mean(2); ys, xs = np.where(g > 25)
    cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
    R = (xs.max() - xs.min() + ys.max() - ys.min()) / 4
    W, H = 1024, 512
    u = (np.arange(W) + 0.5) / W; v = (np.arange(H) + 0.5) / H
    lon = u[None, :] * 2 * np.pi - np.pi; lat = np.pi / 2 - v[:, None] * np.pi
    x = np.cos(lat) * np.cos(lon); y = np.sin(lat); z = -np.cos(lat) * np.sin(lon)
    # hemisfério da foto voltado para +X; na foto, +Z do modelo fica à esquerda
    px = cx - z * R * 0.985; py = cy - y * R * 0.985
    img = src[np.clip(py, 0, src.shape[0] - 1).astype(int), np.clip(px, 0, src.shape[1] - 1).astype(int)]
    neutral = np.array([128, 128, 126], float)
    w = np.clip((x + 0.12) / 0.24, 0, 1)[..., None]
    out = img * w + neutral * (1 - w)
    return Image.fromarray(out.astype(np.uint8))


def noise_texture(base, seed, bands=0.0, contrast=0.18):
    rng = np.random.default_rng(seed)
    h, w = 256, 512
    n = sum(np.kron(rng.normal(0, 1, (h // s, w // s)), np.ones((s, s))) / (k + 1)
            for k, s in enumerate((64, 32, 16, 8, 4)))
    yy = np.linspace(0, 1, h)[:, None]
    n = n / (np.abs(n).max() + 1e-9) * contrast + bands * np.sin(yy * 40 + n * 2)
    img = np.clip(np.array(base)[None, None, :] * (1 + n[..., None]), 0, 1)
    return Image.fromarray((img * 255).astype(np.uint8)).resize((1024, 512), Image.BICUBIC)


def saturn_rings_texture():
    w = 1024
    x = np.linspace(0, 1, w)
    # raio relativo ao raio de Saturno, de 1,24 (anel C) até 2,27 (fim do anel A)
    r = 1.24 + x * (2.27 - 1.24)
    a = np.where(r < 1.53, 0.25, np.where(r < 1.95, 0.9, np.where(r < 2.03, 0.05, 0.7)))
    rng = np.random.default_rng(3)
    a = np.clip(a * (0.85 + 0.15 * np.convolve(rng.normal(0, 1, w), np.ones(9) / 9, "same")), 0, 1)
    col = np.stack([0.85 + 0.0 * x, 0.78 + 0.0 * x, 0.62 + 0.0 * x], 1) * (0.8 + 0.2 * (a[:, None]))
    rgba = np.concatenate([col, a[:, None]], 1)
    img = (np.repeat(rgba[None], 4, 0) * 255).astype(np.uint8)
    return Image.fromarray(img, "RGBA")


# ============================================================ cartões de informação dentro do 3D
def card_image(title, line=None, accent=(255, 200, 97)):
    """Cartão curto: um título e, no máximo, uma linha."""
    fb = ImageFont.truetype(FONT_B, 64); fr = ImageFont.truetype(FONT_R, 44)
    pad = 40
    w = int(max(fb.getlength(title), fr.getlength(line) if line else 0)) + 2 * pad + 14
    h = pad + 70 + (60 if line else 0) + pad - 10
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=34, fill=(20, 28, 68, 220))
    d.rounded_rectangle((0, 0, 12, h - 1), radius=6, fill=accent + (255,))
    d.text((pad, pad - 8), title, font=fb, fill=(240, 243, 252, 255))
    if line:
        d.text((pad, pad + 70), line, font=fr, fill=(255, 214, 140, 255))
    return im


def label_image(text, accent=(255, 200, 97)):
    f = ImageFont.truetype(FONT_B, 54)
    w = int(f.getlength(text)) + 60
    im = Image.new("RGBA", (w, 90), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, 89), radius=24, fill=(20, 28, 68, 215))
    d.rounded_rectangle((0, 0, 10, 89), radius=5, fill=accent + (255,))
    d.text((32, 12), text, font=f, fill=(240, 243, 252, 255))
    return im


def add_card(g, name, im, height_m, center, parent=None, yaw=0.0):
    """Placa de duas faces que brilha sozinha, como uma tela. Tamanho definido pela altura."""
    t = g.image(im)
    m = g.material(f"{name}_mat", (0.08, 0.08, 0.1, 1), tex=t, rough=1.0, emissive=(1, 1, 1), emissive_tex=t, blend=True)
    h = height_m; w = h * im.width / im.height
    x, y, eps = w / 2, h / 2, 0.0015
    pos = [(-x, -y, eps), (x, -y, eps), (x, y, eps), (-x, y, eps),
           (x, -y, -eps), (-x, -y, -eps), (-x, y, -eps), (x, y, -eps)]
    nrm = [(0, 0, 1)] * 4 + [(0, 0, -1)] * 4
    uv = [(0, 1), (1, 1), (1, 0), (0, 0)] * 2
    mesh = g.mesh(name, pos, nrm, uv, [(0, 1, 2), (0, 2, 3), (4, 5, 6), (4, 6, 7)], m)
    return g.node(name, mesh, t=center, r=qaxis((0, 1, 0), yaw), parent=parent)


def label(g, name, text, height_m, center, accent=(255, 200, 97)):
    return add_card(g, f"rotulo_{name}", label_image(text, accent), height_m, center)


# ============================================================ helpers de cena
def planet(g, name, radius, tex_img=None, color=(1, 1, 1), center=(0, 0, 0), tilt=0.0, parent=None,
           seg=64, rough=0.9, emissive=None, emissive_tex=False, key=None, face_yaw=0.0, glow_tex=0.22):
    """Esfera com eixo inclinado. Planetas com textura ganham um leve brilho próprio (glow_tex)."""
    t = g.image(tex_img, key) if tex_img is not None else None
    if t is not None and emissive is None and glow_tex:
        emissive, emissive_tex = (glow_tex,) * 3, True
    m = g.material(f"{name}_mat", tuple(color), tex=t, rough=rough, emissive=emissive,
                   emissive_tex=t if emissive_tex else None)
    p, n, uv, idx = sphere_geo(radius, seg, seg // 2)
    mesh = g.mesh(name, p, n, uv, idx, m)
    tilt_node = g.node(f"{name}_eixo", t=center, r=qaxis((0, 0, 1), tilt), parent=parent)
    body = g.node(name, mesh, r=qaxis((0, 1, 0), face_yaw) if face_yaw else None, parent=tilt_node)
    return tilt_node, body


def halo(g, name, radius, color, parent, clip, period, alpha=0.22, amp=0.05, size=1.12):
    """Brilho em volta do planeta: uma casca transparente que pulsa devagar."""
    m = g.material(f"{name}_brilho_mat", tuple(color) + (alpha,), rough=1.0,
                   emissive=tuple(c * 0.9 for c in color), blend=True)
    p, n, uv, idx = sphere_geo(radius * size, 48, 24)
    node = g.node(f"{name}_brilho", g.mesh(f"{name}_brilho", p, n, uv, idx, m), parent=parent)
    steps = int(round(clip / period)) * 16
    times = np.linspace(0, clip, steps + 1)
    vals = [(1 + amp * math.sin(2 * math.pi * t / period),) * 3 for t in times]
    g.channel(node, "scale", times, vals)
    return node


def solid(g, name, geo, color, metallic=0.0, rough=0.7, t=None, r=None, parent=None, double=False, emissive=None):
    p, n, uv, idx = geo
    m = g.material(f"{name}_mat", color, metallic=metallic, rough=rough, double=double, emissive=emissive)
    return g.node(name, g.mesh(name, p, n, uv, idx, m), t=t, r=r, parent=parent)


def orbit_anim(g, node, radius, period, clip, phase=0.0, center=(0, 0, 0)):
    steps = int(round(clip / period)) * 48
    times = np.linspace(0, clip, steps + 1)
    vals = [(center[0] + radius * math.cos(phase + 2 * math.pi * t / period), center[1],
             center[2] - radius * math.sin(phase + 2 * math.pi * t / period)) for t in times]
    g.channel(node, "translation", times, vals)


def hs(scene, items):
    HOTSPOTS[scene] = [{"id": i, "pos": " ".join(f"{float(v):.3f}" for v in p), "label": l} for i, p, l in items]


# ============================================================ cenas
def cena_spherex():
    g = GLB(); clip = 40
    nave = g.node("nave")
    solid(g, "modulo_de_servico", prism(0.34, 0.32, 6), (0.22, 0.23, 0.26, 1), 0.6, 0.5, parent=nave)
    solid(g, "painel_solar", box(0.02, 0.62, 0.95), (0.1, 0.16, 0.42, 1), 0.3, 0.35,
          t=(-0.46, 0.2, 0), r=qaxis((0, 0, 1), -18), parent=nave, emissive=(0.03, 0.06, 0.2))
    solid(g, "suporte", box(0.16, 0.04, 0.04), (0.6, 0.6, 0.62, 1), 0.8, 0.4, t=(-0.36, 0.18, 0), parent=nave)
    for k, (r0, r1, h) in enumerate([(0.30, 0.56, 0.62), (0.34, 0.66, 0.70), (0.38, 0.76, 0.78)]):
        solid(g, f"escudo_{k + 1}", frustum_shell(r0, r1, h, 0.32 + 0.02 * k), (0.88, 0.89, 0.93, 1), 1.0, 0.2, parent=nave)
    p, n, _, i = prism(0.15, 0.42, 32, 0.32)
    solid(g, "telescopio", (p, n, None, i), (0.05, 0.05, 0.07, 1), 0.2, 0.6, parent=nave)
    p, n, _, i = prism(0.13, 0.01, 32, 0.74)
    solid(g, "espelho", (p, n, None, i), (1.0, 0.75, 0.3, 1), 1.0, 0.15, parent=nave, emissive=(1.0, 0.6, 0.2))
    # luz infravermelha "entrando" no telescópio: brilho pulsante dentro dos cones
    halo(g, "luz", 0.12, (1.0, 0.55, 0.35), g.node("luz_pos", t=(0, 0.8, 0), parent=nave), clip, 4, alpha=0.3, amp=0.25, size=1.0)
    g.spin(nave, 40, clip)
    add_card(g, "cartao", card_image("SPHEREx", "Mapeia o céu em 102 cores"), 0.16, (0, 1.35, 0))
    g.save(f"{OUT}/spherex.glb")
    hs("spherex", [("escudos", (0.6, 1.0, 0.35), "Escudos"), ("telescopio", (0, 0.8, 0), "Telescópio")])


def cena_spitzer():
    src = os.path.join(TEX, "spitzer.glb")
    data = open(src, "rb").read()
    jl = struct.unpack("<I", data[12:16])[0]
    js = json.loads(data[20:20 + jl]); bl = struct.unpack("<I", data[20 + jl:24 + jl])[0]
    g = GLB(); g.j = js; g.bin = bytearray(data[28 + jl:28 + jl + bl])
    for k in ("images", "textures", "materials", "samplers"):
        g.j.setdefault(k, [])
    g.j["samplers"].append({"magFilter": 9729, "minFilter": 9987, "wrapS": 33071, "wrapT": 33071})
    samp = len(g.j["samplers"]) - 1
    originais = list(g.j["scenes"][g.j.get("scene", 0)]["nodes"])
    g.j["scenes"] = [{"nodes": []}]; g.j["scene"] = 0
    giro = g.node("giro")  # gira o telescópio inteiro devagar, como numa vitrine
    g.j["nodes"][giro]["children"] = originais
    g.spin(giro, 60, 60)
    im = card_image("Spitzer", "Tamanho real: 4,5 m")
    t = g.image(im); g.j["textures"][t]["sampler"] = samp
    m = g.material("cartao_mat", (0.08, 0.08, 0.1, 1), tex=t, rough=1, emissive=(1, 1, 1), emissive_tex=t, blend=True)
    h = 0.4; w = h * im.width / im.height; x, y, e = w / 2, h / 2, 0.002
    pos = [(-x, -y, e), (x, -y, e), (x, y, e), (-x, y, e), (x, -y, -e), (-x, -y, -e), (-x, y, -e), (x, y, -e)]
    mesh = g.mesh("cartao", pos, [(0, 0, 1)] * 4 + [(0, 0, -1)] * 4, [(0, 1), (1, 1), (1, 0), (0, 0)] * 2,
                  [(0, 1, 2), (0, 2, 3), (4, 5, 6), (4, 6, 7)], m)
    g.node("cartao", mesh, t=(0, 3.3, 0))
    g.save(f"{OUT}/spitzer.glb")
    hs("spitzer", [])


def cena_ceu():
    g = GLB(); clip = 60
    t = load("tycho.jpg", (2048, 1024))
    t = ImageOps.autocontrast(t, cutoff=0.5)
    t = Image.eval(t, lambda v: int(255 * (v / 255) ** 0.55))
    t = ImageEnhance.Brightness(t).enhance(1.35)
    pivot = g.node("suporte_globo", t=(0, 0.45, 0), r=qaxis((0, 0, 1), 23.4))
    _, body = planet(g, "globo_celeste", 0.4, t, (0.35, 0.35, 0.4), parent=pivot, seg=96, rough=1.0,
                     emissive=(1, 1, 1), emissive_tex=True)
    g.spin(body, 60, clip)
    halo(g, "globo", 0.4, (0.55, 0.65, 1.0), pivot, clip, 6, alpha=0.12, amp=0.03, size=1.06)
    solid(g, "haste", prism(0.012, 0.06, 16), (0.7, 0.7, 0.72, 1), 1, 0.3)
    solid(g, "base", prism(0.14, 0.015, 48), (0.12, 0.12, 0.14, 1), 0.4, 0.5)
    add_card(g, "cartao", card_image("O céu inteiro", "A faixa clara é a Via Láctea"), 0.14, (0, 0.98, 0))
    g.save(f"{OUT}/ceu.glb")
    hs("ceu", [("polo", (-0.159, 0.84, 0), "Polo norte celeste")])


PLANETAS = [  # nome, raio (Terra = 1), textura, cor, inclinação do eixo, período (s), retrógrado, brilho
    ("Mercúrio", 0.383, None, (0.62, 0.6, 0.58), 0.03, 60, False, (0.8, 0.75, 0.7)),
    ("Vênus", 0.949, "venus.jpg", (1, 1, 1), 2.6, 60, True, (1.0, 0.8, 0.45)),
    ("Terra", 1.0, "terra_bluemarble.jpg", (1, 1, 1), 23.4, 10, False, (0.4, 0.65, 1.0)),
    ("Marte", 0.532, "marte.jpg", (1, 1, 1), 25.2, 10, False, (1.0, 0.55, 0.35)),
    ("Júpiter", 11.21, "jupiter.jpg", (1, 1, 1), 3.1, 4, False, (1.0, 0.8, 0.6)),
    ("Saturno", 9.45, "saturno.jpg", (1, 1, 1), 26.7, 5, False, (1.0, 0.88, 0.6)),
    ("Urano", 4.01, None, (0.62, 0.86, 0.88), 97.8, 6, False, (0.55, 0.9, 0.95)),
    ("Netuno", 3.88, "netuno.jpg", (1, 1, 1), 28.3, 6, False, (0.35, 0.55, 1.0)),
]


def add_saturn_rings(g, radius, parent):
    rt = g.image(saturn_rings_texture(), "aneis")
    m = g.material("aneis_mat", (1, 1, 1, 1), tex=rt, rough=0.9, blend=True, double=True,
                   emissive=(0.35, 0.32, 0.25), emissive_tex=rt)
    p, n, uv, idx = ring_geo(radius * 1.24, radius * 2.27)
    g.node("aneis", g.mesh("aneis", p, n, uv, idx, m), parent=parent)


def cena_sistema_solar():
    g = GLB(); clip = 60
    RE = 0.012
    x = -0.75; y0 = 0.25
    items = []
    for k_pl, (nome, rr, texf, col, tilt, per, retro, cor_brilho) in enumerate(PLANETAS):
        r = rr * RE
        x += r
        if texf:
            tex = load(texf, (1024, 512))
        elif nome == "Mercúrio":
            tex = noise_texture(col, 11, 0.0, 0.35)
        else:
            tex = noise_texture(col, 12, 0.03, 0.06)
        tilt_node, body = planet(g, nome, r, tex, center=(x, y0, 0), tilt=tilt, key=nome)
        g.spin(body, per, clip, reverse=retro)
        halo(g, nome, r, cor_brilho, tilt_node, clip, 5 if k_pl % 2 else 6, alpha=0.2)
        if nome == "Saturno":
            add_saturn_rings(g, r, tilt_node)
        ly = y0 + max(r, 0.03) + 0.04 + (0.03 if nome == "Saturno" else 0) + (0.05 if k_pl % 2 and k_pl < 4 else 0)
        label(g, nome, nome, 0.028, (x, ly, 0))
        items.append((nome, (x, ly + 0.035, 0), nome))
        x += r + (0.12 if k_pl < 3 else 0.07 if nome != "Saturno" else 0.17)
    add_card(g, "cartao", card_image("Os 8 planetas", "Tamanhos em escala, distâncias não"), 0.09, (0.0, 0.62, -0.05))
    g.save(f"{OUT}/sistema-solar.glb")
    HOTSPOTS["sistema-solar"] = [{"id": i, "pos": " ".join(f"{v:.3f}" for v in p), "label": l} for i, p, l in items]


def cena_terra_lua():
    g = GLB(); clip = 40
    RE = 0.12
    tilt, earth = planet(g, "Terra", RE, load("terra_bluemarble.jpg"), center=(-0.3, 0.35, 0), tilt=23.4, seg=96)
    g.spin(earth, 4, clip)
    halo(g, "Terra", RE, (0.4, 0.65, 1.0), tilt, clip, 5, alpha=0.22, amp=0.03, size=1.08)
    piv = g.node("orbita_lua", t=(-0.3, 0.35, 0), r=qaxis((0, 0, 1), 5.1))
    spin_piv = g.node("giro_orbita", parent=piv)
    _, moon = planet(g, "Lua", RE * 0.2727, moon_texture(), center=(0.75, 0, 0), parent=spin_piv, face_yaw=180, glow_tex=0.3)
    g.spin(spin_piv, 40, clip)
    pts = [(-0.3 + 0.75 * math.cos(a), 0.35 + 0.75 * math.cos(a) * math.sin(math.radians(5.1)),
            -0.75 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 181)]
    solid(g, "trilha_lua", tube(pts, 0.0018), (0.7, 0.75, 0.9, 1), 0, 0.8, emissive=(0.35, 0.4, 0.55))
    add_card(g, "cartao_terra", card_image("Terra", "1 dia = 24 horas"), 0.11, (-0.3, 0.6, 0))
    label(g, "lua", "Lua", 0.04, (0.45, 0.5, 0))
    g.save(f"{OUT}/terra-lua.glb")
    hs("terra-lua", [("terra", (-0.3, 0.42, 0.1), "Terra"), ("lua", (0.45, 0.56, 0), "Lua")])


def cena_marte():
    g = GLB(); clip = 20
    tilt, body = planet(g, "Marte", 0.2, load("marte.jpg"), center=(0, 0.3, 0), tilt=25.2, seg=96)
    g.spin(body, 20, clip)
    halo(g, "Marte", 0.2, (1.0, 0.55, 0.35), tilt, clip, 5, alpha=0.16, amp=0.03, size=1.06)
    add_card(g, "cartao", card_image("Marte", "1 dia = 24 h 37 min"), 0.11, (0, 0.65, 0))
    g.save(f"{OUT}/marte.glb")
    hs("marte", [("calota", (-0.085, 0.5, 0), "Calota polar")])


def cena_jupiter():
    g = GLB(); clip = 60
    RJ = 0.28; cy = 0.35
    tilt, body = planet(g, "Júpiter", RJ, load("jupiter.jpg", (1024, 512)), center=(0, cy, 0), tilt=3.1, seg=96)
    g.spin(body, 6, clip)
    halo(g, "Júpiter", RJ, (1.0, 0.8, 0.6), tilt, clip, 6, alpha=0.15, amp=0.025, size=1.06)
    luas = [("Io", 3643, "io.jpg", 0.48, 7.5), ("Europa", 3122, "europa.jpg", 0.62, 15),
            ("Ganimedes", 5268, "ganimedes.jpg", 0.82, 30), ("Calisto", 4821, "calisto.jpg", 1.05, 60)]
    for k, (nome, diam, texf, dist, per) in enumerate(luas):
        r = RJ * diam / 142984 * 3
        n_tilt, _ = planet(g, nome, r, load(texf, (1024, 512)), center=(dist, cy, 0), seg=48, glow_tex=0.35)
        orbit_anim(g, n_tilt, dist, per, clip, phase=k * 1.3, center=(0, cy, 0))
        pts = [(dist * math.cos(a), cy, -dist * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 181)]
        solid(g, f"trilha_{nome}", tube(pts, 0.0015), (0.7, 0.75, 0.9, 1), 0, 0.8, emissive=(0.3, 0.35, 0.5))
        label(g, nome, nome, 0.035, (dist, cy + 0.07, -0.0))
    add_card(g, "cartao", card_image("Júpiter", "Io dá 4 voltas enquanto Ganimedes dá 1"), 0.11, (0, 0.78, 0))
    g.save(f"{OUT}/jupiter.glb")
    hs("jupiter", [("faixas", (0, 0.49, 0.24), "Faixas de nuvens")])


def cena_saturno():
    g = GLB(); clip = 10
    R = 0.2
    tilt, body = planet(g, "Saturno", R, load("saturno.jpg", (1024, 512)), center=(0, 0.45, 0), tilt=26.7, seg=96)
    g.spin(body, 10, clip)
    halo(g, "Saturno", R, (1.0, 0.88, 0.6), tilt, clip, 5, alpha=0.16, amp=0.03, size=1.06)
    add_saturn_rings(g, R, tilt)
    add_card(g, "cartao", card_image("Saturno", "Anéis de gelo e rocha"), 0.11, (0, 0.9, 0))
    g.save(f"{OUT}/saturno.glb")
    hs("saturno", [("aneis", (0.4, 0.45, 0.1), "Anéis"), ("divisao", (-0.39, 0.6, 0), "Divisão de Cassini")])


# Elementos orbitais APROXIMADOS (eclíptica J2000). Conferir no JPL Small-Body Database.
ORBITAS = {
    "Netuno": dict(a=30.07, e=0.009, i=1.77, O=131.8, w=273.2, cor=(0.35, 0.55, 0.95), per=6, tex="netuno.jpg", r=0.012),
    "Plutão": dict(a=39.48, e=0.249, i=17.14, O=110.3, w=113.8, cor=(0.85, 0.72, 0.55), per=10, tex="plutao.jpg", r=0.009),
    "2012 VP113": dict(a=271.0, e=0.70, i=24.1, O=90.8, w=293.0, cor=(0.95, 0.45, 0.35), per=20, tex=None, r=0.009),
    "Planeta X": dict(a=380.0, e=0.21, i=16.0, O=97.0, w=157.0, cor=(0.75, 0.6, 1.0), per=30, tex=None, r=0.02),
    "Sedna": dict(a=506.0, e=0.855, i=11.93, O=144.4, w=311.3, cor=(0.95, 0.35, 0.25), per=60, tex=None, r=0.009),
}
ESC = 1 / 700.0


def kepler_pos(el, M):
    E = M
    for _ in range(30):
        E = E - (E - el["e"] * math.sin(E) - M) / (1 - el["e"] * math.cos(E))
    nu = 2 * math.atan2(math.sqrt(1 + el["e"]) * math.sin(E / 2), math.sqrt(1 - el["e"]) * math.cos(E / 2))
    return orbit_point(el, nu)


def orbit_point(el, nu):
    i, O, w = map(math.radians, (el["i"], el["O"], el["w"]))
    a, e = el["a"], el["e"]
    r = a * (1 - e * e) / (1 + e * math.cos(nu)); u = w + nu
    x = r * (math.cos(O) * math.cos(u) - math.sin(O) * math.sin(u) * math.cos(i))
    y = r * (math.sin(O) * math.cos(u) + math.cos(O) * math.sin(u) * math.cos(i))
    z = r * math.sin(u) * math.sin(i)
    return np.array([x, z, -y]) * ESC


def cena_planeta_x():
    g = GLB(); clip = 60
    lift = np.array([0, 0.25, 0])
    sol, _ = planet(g, "Sol", 0.022, None, (1.0, 0.82, 0.35), center=tuple(lift), emissive=(1.0, 0.75, 0.3), seg=32)
    halo(g, "Sol", 0.022, (1.0, 0.7, 0.25), sol, clip, 3, alpha=0.35, amp=0.2, size=1.6)
    labels = []
    for k, (nome, el) in enumerate(ORBITAS.items()):
        pts = [orbit_point(el, nu) + lift for nu in np.linspace(0, 2 * math.pi, 361)]
        r = 0.0025 if nome != "Planeta X" else 0.0035
        col = el["cor"] + (1,)
        emi = tuple(c * 0.6 for c in el["cor"])
        if nome == "Planeta X":
            for s in range(0, 360, 8):
                solid(g, f"orbita_px_{s}", tube(pts[s:s + 5], r), col, 0, 0.6, emissive=emi)
        else:
            solid(g, f"orbita_{nome}", tube(pts, r), col, 0, 0.6, emissive=emi)
        tex = load(el["tex"], (512, 256)) if el["tex"] else None
        n_tilt, _ = planet(g, nome, el["r"], tex, el["cor"] if not tex else (1, 1, 1), center=tuple(pts[0]), seg=32,
                           emissive=None if tex else tuple(c * 0.5 for c in el["cor"]), glow_tex=0.4)
        if nome == "Planeta X":
            halo(g, "PlanetaX", el["r"], el["cor"], n_tilt, clip, 4, alpha=0.3, amp=0.25, size=1.5)
        steps = int(clip / el["per"]) * 120
        times = np.linspace(0, clip, steps + 1)
        vals = [kepler_pos(el, 2 * math.pi * t / el["per"] + k) + lift for t in times]
        g.channel(n_tilt, "translation", times, vals)
        if nome not in ("Netuno", "Plutão"):
            far = orbit_point(el, math.pi) + lift
            label(g, nome, nome, 0.045, tuple(far + np.array([0, 0.06, 0])), tuple(int(c * 255) for c in el["cor"]))
            labels.append((nome.lower().replace(" ", "-"), far + np.array([0, 0.11, 0]), nome))
    label(g, "sol", "Sol", 0.035, tuple(lift + np.array([0, 0.07, 0])))
    add_card(g, "cartao", card_image("A pista do Planeta X", "Tracejado: a órbita que ele teria"), 0.1, (0.0, 0.62, -0.5))
    g.save(f"{OUT}/planeta-x.glb")
    hs("planeta-x", labels + [("sol", lift + np.array([0, 0.12, 0]), "Sol")])


def cena_tamanho():
    g = GLB(); clip = 30
    RE = 0.06
    t1, b1 = planet(g, "Terra", RE, load("terra_bluemarble.jpg", (1024, 512)), center=(-0.52, RE, 0), tilt=23.4)
    g.spin(b1, 10, clip); halo(g, "Terra", RE, (0.4, 0.65, 1.0), t1, clip, 5, alpha=0.22, amp=0.04, size=1.1)
    RX = RE * 2.2
    t2, b2 = planet(g, "Planeta X", RX, noise_texture((0.62, 0.58, 0.78), 7, 0.12, 0.08), center=(-0.2, RX, 0), tilt=10)
    g.spin(b2, 15, clip); halo(g, "PlanetaX", RX, (0.75, 0.6, 1.0), t2, clip, 3, alpha=0.25, amp=0.08, size=1.1)
    RN = RE * 3.88
    t3, b3 = planet(g, "Netuno", RN, load("netuno.jpg", (1024, 512)), center=(0.38, RN, 0), tilt=28.3)
    g.spin(b3, 6, clip); halo(g, "Netuno", RN, (0.35, 0.55, 1.0), t3, clip, 5, alpha=0.18, amp=0.03, size=1.07)
    for nome, x, top in (("Terra", -0.52, 2 * RE), ("Planeta X?", -0.2, 2 * RX), ("Netuno", 0.38, 2 * RN)):
        label(g, nome, nome, 0.035, (x, top + 0.05, 0))
    add_card(g, "cartao", card_image("Do tamanho de quê?", "Planeta X: entre a Terra e Netuno"), 0.1, (0, 0.68, -0.2))
    g.save(f"{OUT}/tamanho.glb")
    hs("tamanho", [("terra", (-0.52, 2 * RE + 0.1, 0), "Terra"), ("px", (-0.2, 2 * RX + 0.1, 0), "Planeta X"),
                   ("netuno", (0.38, 2 * RN + 0.1, 0), "Netuno")])


CENAS = [cena_spherex, cena_spitzer, cena_ceu, cena_sistema_solar, cena_terra_lua, cena_marte,
         cena_jupiter, cena_saturno, cena_planeta_x, cena_tamanho]

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for f in CENAS:
        f()
    json.dump(HOTSPOTS, open(os.path.join(OUT, "rotulos.json"), "w"), ensure_ascii=False, indent=1)
    for f in sorted(os.listdir(OUT)):
        print(f"{f:24s} {os.path.getsize(os.path.join(OUT, f)) // 1024:6d} KB")
