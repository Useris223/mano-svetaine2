(function snow(){
  const canvas = document.getElementById("snowCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  let w, h, flakes;
  function resize(){
    w = canvas.width = window.innerWidth * devicePixelRatio;
    h = canvas.height = window.innerHeight * devicePixelRatio;
    canvas.style.width = window.innerWidth + "px";
    canvas.style.height = window.innerHeight + "px";
    flakes = Array.from({length: 140}, () => ({
      x: Math.random() * w,
      y: Math.random() * h,
      r: (Math.random()*1.8 + 0.6) * devicePixelRatio,
      s: (Math.random()*0.9 + 0.4) * devicePixelRatio,
      a: Math.random()*0.5 + 0.2
    }));
  }
  resize();
  window.addEventListener("resize", resize);

  function tick(){
    ctx.clearRect(0,0,w,h);
    for (const f of flakes){
      ctx.beginPath();
      ctx.fillStyle = `rgba(255,255,255,${f.a})`;
      ctx.arc(f.x, f.y, f.r, 0, Math.PI*2);
      ctx.fill();

      f.y += f.s;
      f.x += Math.sin(f.y * 0.002) * (0.35 * devicePixelRatio);

      if (f.y > h + 10) {
        f.y = -10;
        f.x = Math.random() * w;
      }
    }
    requestAnimationFrame(tick);
  }
  tick();
})();
