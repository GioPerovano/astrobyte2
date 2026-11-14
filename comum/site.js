/* Comum do site AstroByte: menu do celular e céu estrelado animado. */
/* ---------- menu (celular) ---------- */
const menuBtn=document.getElementById("menuBtn"), menu=document.getElementById("menu");
menuBtn.addEventListener("click",()=>{
  const open=menuBtn.getAttribute("aria-expanded")!=="true";
  menuBtn.setAttribute("aria-expanded",open);
  if(open) menu.dataset.open=""; else delete menu.dataset.open;
});
document.addEventListener("click",e=>{ if(!menu.contains(e.target)&&!menuBtn.contains(e.target)){ delete menu.dataset.open; menuBtn.setAttribute("aria-expanded","false"); } });
// enquanto o site parceiro não tiver endereço, o link não faz nada
document.getElementById("partnerLink").addEventListener("click",e=>{ if(e.currentTarget.hasAttribute("data-pending")) e.preventDefault(); });

/* ---------- céu estrelado animado ---------- */
(function ceu(){
  const cv=document.getElementById("ceu"), ctx=cv.getContext && cv.getContext("2d");
  if(!ctx) return;
  const calmo=!!(window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches);
  let W=0,H=0,dpr=1,estrelas=[],cadente=null,proxCadente=performance.now()+5000;
  const cores=["255,244,220","255,214,150","200,215,255","255,255,255"];
  function criar(){
    dpr=Math.min(window.devicePixelRatio||1,2);
    W=innerWidth; H=innerHeight; cv.width=W*dpr; cv.height=H*dpr; ctx.setTransform(dpr,0,0,dpr,0,0);
    const n=Math.round(W*H/2600);
    estrelas=Array.from({length:n},()=>{
      const camada=Math.random();
      return {x:Math.random()*W, y:Math.random()*H, r:camada<.85?Math.random()*.9+.3:Math.random()*1.4+1,
        v:(camada<.6?.004:camada<.9?.01:.02), fase:Math.random()*6.28, ritmo:.6+Math.random()*1.8,
        cor:cores[(Math.random()*cores.length)|0], brilho:camada>.97};
    });
  }
  function desenhar(t){
    ctx.clearRect(0,0,W,H);
    for(const s of estrelas){
      if(!calmo){ s.x+=s.v; s.y+=s.v*.35; if(s.x>W+2) s.x=-2; if(s.y>H+2) s.y=-2; }
      const a=calmo?.8:.45+.55*Math.abs(Math.sin(s.fase+t/1000*s.ritmo*.6));
      ctx.fillStyle=`rgba(${s.cor},${a})`;
      ctx.beginPath(); ctx.arc(s.x,s.y,s.r,0,6.283); ctx.fill();
      if(s.brilho){ // estrelas maiores ganham uma cruz de brilho, como na logo
        ctx.strokeStyle=`rgba(255,214,150,${a*.5})`; ctx.lineWidth=.7;
        ctx.beginPath(); ctx.moveTo(s.x-s.r*4,s.y); ctx.lineTo(s.x+s.r*4,s.y); ctx.moveTo(s.x,s.y-s.r*4); ctx.lineTo(s.x,s.y+s.r*4); ctx.stroke();
      }
    }
    if(!calmo){
      if(!cadente && t>proxCadente){ cadente={x:Math.random()*W*.7, y:Math.random()*H*.3, vida:0}; }
      if(cadente){
        cadente.vida+=1; const p=cadente.vida/60, x=cadente.x+p*260, y=cadente.y+p*110;
        const g=ctx.createLinearGradient(x-90,y-38,x,y);
        g.addColorStop(0,"rgba(255,194,74,0)"); g.addColorStop(1,`rgba(255,236,190,${1-p})`);
        ctx.strokeStyle=g; ctx.lineWidth=1.6; ctx.beginPath(); ctx.moveTo(x-90,y-38); ctx.lineTo(x,y); ctx.stroke();
        if(p>=1){ cadente=null; proxCadente=t+9000+Math.random()*9000; }
      }
      requestAnimationFrame(desenhar);
    }
  }
  criar(); addEventListener("resize",()=>{ criar(); if(calmo) desenhar(0); });
  requestAnimationFrame(desenhar);
})();
