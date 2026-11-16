/* AstroByte: idioma (PT/EN) e acessibilidade, usados por todas as páginas.

   Idioma
   - Marque textos com data-i18n="chave" (texto), data-i18n-html="chave" (HTML)
     ou data-i18n-attr="aria-label:chave;title:outra".
   - Cada página registra suas traduções com AB.registrar({pt:{...}, en:{...}}).
   - Para conteúdo gerado por script: AB.t("chave"), AB.lang e AB.aoMudarIdioma(fn).
   - O idioma vem de ?lang=en na URL, ou da última escolha da pessoa.

   Acessibilidade
   - Texto maior, alto contraste, reduzir movimento, fonte mais legível,
     sublinhar links e leitura em voz alta.
   - As escolhas ficam salvas neste navegador.
   - Scripts de animação podem consultar AB.movimentoReduzido().
*/
(function () {
  "use strict";
  const raiz = document.documentElement;
  const guardar = (k, v) => { try { localStorage.setItem(k, v); } catch (e) {} };
  const ler = k => { try { return localStorage.getItem(k); } catch (e) { return null; } };

  /* ------------------------------------------------------------------ idioma */
  const DIC = { pt: {}, en: {} };
  const ouvintes = [];
  const IDIOMAS = ["pt", "en"];
  let lang = (new URLSearchParams(location.search).get("lang") || ler("ab-idioma") || "pt").slice(0, 2);
  if (!IDIOMAS.includes(lang)) lang = "pt";

  const COMUM = {
    pt: {
      "menu.btn": "Menu", "menu.aria": "Menu principal", "menu.ra": "Realidade aumentada", "menu.Game": "Game",
      "menu.cartas": "Card Game", "menu.parceiro": "Parceiro", "menu.spherex": "SPHEREx · Planeta X",
      "logo.aria": "AstroByte, início",
      "rodape.redes": "Redes sociais do AstroByte", "rodape.fale": "Fale com a gente:",
      "rodape.credito": "Página criada pela equipe AstroByte para o NASA Space Apps Challenge 2026. Imagens e dados científicos: NASA.",
      "ab.idioma": "Idioma", "ab.titulo": "Acessibilidade", "ab.abrir": "Abrir opções de acessibilidade",
      "ab.texto": "Tamanho do texto", "ab.menor": "Diminuir texto", "ab.normal": "Texto normal", "ab.maior": "Aumentar texto",
      "ab.contraste": "Alto contraste", "ab.movimento": "Reduzir movimento", "ab.fonte": "Fonte mais legível",
      "ab.links": "Sublinhar links", "ab.ouvir": "Ouvir o texto da página", "ab.parar": "Parar leitura",
      "ab.restaurar": "Restaurar padrão", "ab.fechar": "Fechar", "ab.semvoz": "Seu navegador não tem leitura em voz alta."
    },
    en: {
      "menu.btn": "Menu", "menu.aria": "Main menu", "menu.ra": "Augmented reality", "menu.Game": "Game",
      "menu.cartas": "Card Game", "menu.parceiro": "Partner", "menu.spherex": "SPHEREx · Planet X",
      "logo.aria": "AstroByte, home",
      "rodape.redes": "AstroByte social media", "rodape.fale": "Contact us:",
      "rodape.credito": "Page created by the AstroByte team for the NASA Space Apps Challenge 2026. Images and scientific data: NASA.",
      "ab.idioma": "Language", "ab.titulo": "Accessibility", "ab.abrir": "Open accessibility options",
      "ab.texto": "Text size", "ab.menor": "Smaller text", "ab.normal": "Normal text", "ab.maior": "Larger text",
      "ab.contraste": "High contrast", "ab.movimento": "Reduce motion", "ab.fonte": "More readable font",
      "ab.links": "Underline links", "ab.ouvir": "Read the page aloud", "ab.parar": "Stop reading",
      "ab.restaurar": "Reset", "ab.fechar": "Close", "ab.semvoz": "Your browser does not support reading aloud."
    }
  };
  Object.assign(DIC.pt, COMUM.pt); Object.assign(DIC.en, COMUM.en);

  function t(chave) { return (DIC[lang] && DIC[lang][chave]) ?? DIC.pt[chave] ?? chave; }

  function aplicar(onde) {
    const base = onde || document;
    base.querySelectorAll("[data-i18n]").forEach(el => { el.textContent = t(el.dataset.i18n); });
    base.querySelectorAll("[data-i18n-html]").forEach(el => { el.innerHTML = t(el.dataset.i18nHtml); });
    base.querySelectorAll("[data-i18n-attr]").forEach(el => {
      el.dataset.i18nAttr.split(";").forEach(par => {
        const [attr, chave] = par.split(":").map(s => s.trim());
        if (attr && chave) el.setAttribute(attr, t(chave));
      });
    });
    raiz.lang = lang === "en" ? "en" : "pt-BR";
    const titulo = document.querySelector("title[data-i18n]");
    if (titulo) document.title = t(titulo.dataset.i18n);
  }

  function mudarIdioma(novo) {
    if (!IDIOMAS.includes(novo) || novo === lang) return;
    lang = novo; guardar("ab-idioma", lang);
    aplicar(); atualizarBotoes();
    ouvintes.forEach(fn => { try { fn(lang); } catch (e) { console.error(e); } });
  }

  /* ------------------------------------------------------------ acessibilidade */
  const PADRAO = { texto: 0, contraste: false, movimento: false, fonte: false, links: false };
  let prefs = Object.assign({}, PADRAO);
  try { Object.assign(prefs, JSON.parse(ler("ab-acessibilidade") || "{}")); } catch (e) {}
  const sistemaReduz = !!(window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches);

  function aplicarPrefs() {
    const escala = [1, 1.15, 1.3, 0.9][prefs.texto === -1 ? 3 : prefs.texto] || 1;
    raiz.style.setProperty("--ab-escala", escala);
    raiz.dataset.abTexto = String(prefs.texto);
    raiz.toggleAttribute("data-ab-contraste", !!prefs.contraste);
    raiz.toggleAttribute("data-ab-movimento", !!prefs.movimento);
    raiz.toggleAttribute("data-ab-fonte", !!prefs.fonte);
    raiz.toggleAttribute("data-ab-links", !!prefs.links);
    guardar("ab-acessibilidade", JSON.stringify(prefs));
    window.dispatchEvent(new CustomEvent("ab:acessibilidade", { detail: Object.assign({}, prefs) }));
  }

  const CSS = `
  html{font-size:calc(100% * var(--ab-escala,1))}
  html[data-ab-contraste]{--muted:#EEEAF7;--line:rgba(255,255,255,.6);--glass:rgba(0,0,0,.96);--glass-strong:#000;--panel:#000;--ink:#FFFFFF}
  html[data-ab-contraste] body{background:#000}
  html[data-ab-contraste] .nebula{display:none}
  html[data-ab-contraste] *{text-shadow:none!important}
  html[data-ab-contraste] a{color:#FFE08A}
  html[data-ab-movimento] *,html[data-ab-movimento] *::before,html[data-ab-movimento] *::after{animation:none!important;transition:none!important;scroll-behavior:auto!important}
  html[data-ab-fonte] body,html[data-ab-fonte] body *:not(svg):not(svg *):not(canvas){font-family:"Atkinson Hyperlegible","Verdana",sans-serif!important;letter-spacing:.02em!important;font-style:normal!important}
  html[data-ab-links] a{text-decoration:underline!important;text-underline-offset:3px}
  .ab-ferramentas{display:flex;align-items:center;gap:6px;position:relative;z-index:30}
  .top .ab-ferramentas{margin-left:auto;margin-right:8px}
  .ab-ferramentas button{display:inline-flex;align-items:center;justify-content:center;gap:4px;min-width:38px;height:38px;padding:0 9px;border:1px solid rgba(255,244,220,.25);border-radius:999px;background:rgba(0,0,0,.55);color:#FFF4DC;font:700 .82rem/1 "Atkinson Hyperlegible",system-ui,sans-serif;cursor:pointer}
  .ab-ferramentas button:hover{border-color:#FFC24A}
  .ab-ferramentas button[aria-pressed="true"]{background:#FFC24A;color:#1A1004;border-color:#FFC24A}
  .ab-ferramentas .ab-idiomas{display:inline-flex;border:1px solid rgba(255,244,220,.25);border-radius:999px;overflow:hidden}
  .ab-ferramentas .ab-idiomas button{border:0;border-radius:0;min-width:34px;height:36px;background:transparent}
  .ab-ferramentas svg{width:20px;height:20px}
  .ab-painel{position:fixed;z-index:1000;top:calc(70px + env(safe-area-inset-top,0px));right:12px;width:min(320px,calc(100vw - 24px));max-height:calc(100dvh - 90px);overflow:auto;padding:14px;border:1px solid rgba(255,244,220,.3);border-radius:16px;background:#07081A;color:#FFF4DC;box-shadow:0 18px 50px rgba(0,0,0,.6);font:400 15px/1.4 "Atkinson Hyperlegible",system-ui,sans-serif}
  .ab-painel[hidden]{display:none}
  .ab-painel h2{margin:0 0 10px;font:700 17px/1.2 "Atkinson Hyperlegible",system-ui,sans-serif;color:#FFC24A}
  .ab-painel .ab-linha{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:8px 0;border-top:1px solid rgba(255,244,220,.12)}
  .ab-painel .ab-grupo{display:flex;gap:6px}
  .ab-painel button{min-height:40px;padding:0 12px;border:1px solid rgba(255,244,220,.3);border-radius:10px;background:transparent;color:#FFF4DC;font:700 15px/1 "Atkinson Hyperlegible",system-ui,sans-serif;cursor:pointer}
  .ab-painel button[aria-pressed="true"]{background:#FFC24A;color:#1A1004;border-color:#FFC24A}
  .ab-painel .ab-largo{width:100%;margin-top:8px}
  .ab-painel .ab-aviso{margin:6px 0 0;font-size:13px;color:#B9B3C9}
  .ab-ferramentas button:focus-visible,.ab-painel button:focus-visible{outline:3px solid #FFC24A;outline-offset:2px}
  @media (max-width:420px){.ab-ferramentas .ab-txt{display:none}}`;

  /* --------------------------------------------------------------- interface */
  let painel, btnAb, btnsIdioma = [], btnsPrefs = {}, btnOuvir, falando = false;

  function atualizarBotoes() {
    btnsIdioma.forEach(b => b.setAttribute("aria-pressed", String(b.dataset.lang === lang)));
    Object.entries(btnsPrefs).forEach(([k, b]) => {
      if (k.startsWith("texto")) b.setAttribute("aria-pressed", String(prefs.texto === Number(k.split(":")[1])));
      else b.setAttribute("aria-pressed", String(!!prefs[k]));
    });
    if (btnOuvir) btnOuvir.textContent = falando ? t("ab.parar") : t("ab.ouvir");
  }

  function montar() {
    const estilo = document.createElement("style");
    estilo.textContent = CSS; document.head.appendChild(estilo);

    const lugar = document.getElementById("abFerramentas");
    const caixa = lugar || Object.assign(document.createElement("div"), { style: "position:fixed;top:12px;right:12px;z-index:900" });
    caixa.classList.add("ab-ferramentas");
    if (!lugar) document.body.appendChild(caixa);

    // seletor de idioma
    const idiomas = document.createElement("div");
    idiomas.className = "ab-idiomas"; idiomas.setAttribute("role", "group");
    idiomas.dataset.i18nAttr = "aria-label:ab.idioma";
    [["pt", "PT", "Português"], ["en", "EN", "English"]].forEach(([codigo, rotulo, nome]) => {
      const b = document.createElement("button");
      b.type = "button"; b.textContent = rotulo; b.dataset.lang = codigo; b.lang = codigo;
      b.setAttribute("aria-label", nome);
      b.addEventListener("click", () => mudarIdioma(codigo));
      idiomas.appendChild(b); btnsIdioma.push(b);
    });
    caixa.appendChild(idiomas);

    // botão de acessibilidade
    btnAb = document.createElement("button");
    btnAb.type = "button"; btnAb.setAttribute("aria-expanded", "false"); btnAb.setAttribute("aria-controls", "abPainel");
    btnAb.dataset.i18nAttr = "aria-label:ab.abrir;title:ab.titulo";
    btnAb.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="4" r="2"/><path d="M4 8l8 2 8-2M12 10v5l-3 6M12 15l3 6"/></svg>';
    caixa.appendChild(btnAb);

    // painel
    painel = document.createElement("div");
    painel.className = "ab-painel"; painel.id = "abPainel"; painel.hidden = true;
    painel.setAttribute("role", "dialog"); painel.dataset.i18nAttr = "aria-label:ab.titulo";
    painel.innerHTML = `
      <h2 data-i18n="ab.titulo"></h2>
      <div class="ab-linha"><span data-i18n="ab.texto"></span><div class="ab-grupo">
        <button type="button" data-pref="texto:-1" data-i18n-attr="aria-label:ab.menor">A−</button>
        <button type="button" data-pref="texto:0" data-i18n-attr="aria-label:ab.normal">A</button>
        <button type="button" data-pref="texto:1" data-i18n-attr="aria-label:ab.maior">A+</button>
        <button type="button" data-pref="texto:2" data-i18n-attr="aria-label:ab.maior">A++</button></div></div>
      <div class="ab-linha"><span data-i18n="ab.contraste"></span><button type="button" data-pref="contraste">◐</button></div>
      <div class="ab-linha"><span data-i18n="ab.movimento"></span><button type="button" data-pref="movimento">⏸</button></div>
      <div class="ab-linha"><span data-i18n="ab.fonte"></span><button type="button" data-pref="fonte">Aa</button></div>
      <div class="ab-linha"><span data-i18n="ab.links"></span><button type="button" data-pref="links">U̲</button></div>
      <button type="button" class="ab-largo" id="abOuvir"></button>
      <p class="ab-aviso" id="abAvisoVoz" hidden data-i18n="ab.semvoz"></p>
      <button type="button" class="ab-largo" id="abRestaurar" data-i18n="ab.restaurar"></button>
      <button type="button" class="ab-largo" id="abFechar" data-i18n="ab.fechar"></button>`;
    document.body.appendChild(painel);

    painel.querySelectorAll("[data-pref]").forEach(b => {
      btnsPrefs[b.dataset.pref] = b;
      b.addEventListener("click", () => {
        const p = b.dataset.pref;
        if (p.startsWith("texto")) prefs.texto = Number(p.split(":")[1]);
        else prefs[p] = !prefs[p];
        aplicarPrefs(); atualizarBotoes();
      });
    });
    painel.querySelector("#abRestaurar").addEventListener("click", () => { prefs = Object.assign({}, PADRAO); aplicarPrefs(); atualizarBotoes(); });
    painel.querySelector("#abFechar").addEventListener("click", () => fecharPainel(true));
    btnOuvir = painel.querySelector("#abOuvir");
    btnOuvir.addEventListener("click", alternarLeitura);

    btnAb.addEventListener("click", () => (painel.hidden ? abrirPainel() : fecharPainel(true)));
    document.addEventListener("keydown", e => { if (e.key === "Escape" && !painel.hidden) fecharPainel(true); });
    document.addEventListener("click", e => { if (!painel.hidden && !painel.contains(e.target) && !caixa.contains(e.target)) fecharPainel(false); });

    aplicar(); atualizarBotoes();
  }

  function abrirPainel() {
    painel.hidden = false; btnAb.setAttribute("aria-expanded", "true");
    const r = btnAb.getBoundingClientRect();
    painel.style.top = Math.max(8, r.bottom + 8) + "px";
    const primeiro = painel.querySelector("button"); if (primeiro) primeiro.focus();
  }
  function fecharPainel(devolverFoco) {
    painel.hidden = true; btnAb.setAttribute("aria-expanded", "false");
    if (devolverFoco) btnAb.focus();
  }

  /* leitura em voz alta do conteúdo principal da página */
  function alternarLeitura() {
    if (!("speechSynthesis" in window)) { painel.querySelector("#abAvisoVoz").hidden = false; return; }
    if (falando) { speechSynthesis.cancel(); falando = false; atualizarBotoes(); return; }
    const alvo = document.querySelector("[data-ab-leitura]") || document.querySelector("main") || document.body;
    const texto = (alvo.innerText || "").replace(/\s+/g, " ").trim().slice(0, 6000);
    if (!texto) return;
    const fala = new SpeechSynthesisUtterance(texto);
    fala.lang = lang === "en" ? "en-US" : "pt-BR"; fala.rate = 1;
    fala.onend = fala.onerror = () => { falando = false; atualizarBotoes(); };
    speechSynthesis.cancel(); speechSynthesis.speak(fala); falando = true; atualizarBotoes();
  }

  /* ------------------------------------------------------------------- API */
  window.AB = {
    get lang() { return lang; },
    t, aplicar,
    registrar(dic) { IDIOMAS.forEach(l => Object.assign(DIC[l], (dic && dic[l]) || {})); if (document.readyState !== "loading") aplicar(); },
    aoMudarIdioma(fn) { ouvintes.push(fn); },
    mudarIdioma,
    movimentoReduzido() { return sistemaReduz || !!prefs.movimento; },
    get prefs() { return Object.assign({}, prefs); }
  };

  aplicarPrefs();
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", montar);
  else montar();
})();
