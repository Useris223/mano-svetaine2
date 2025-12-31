// Toast
function toast(msg) {
  const el = document.getElementById('toast');
  if (!el) return;
  const box = el.querySelector('div');
  box.textContent = msg;
  el.classList.remove('hidden');
  setTimeout(() => el.classList.add('hidden'), 2200);
}
window.toast = toast;

// Add to cart
async function addToCart(id) {
  try {
    const r = await fetch('/api/cart/add', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ id, qty: 1 })
    });
    const j = await r.json();
    toast(j.ok ? 'Įdėta į krepšelį ✅' : (j.error || 'Klaida'));
  } catch {
    toast('Network error ❌');
  }
}

// 3D tilt cards
(function initTilt(){
  const cards = document.querySelectorAll('[data-tilt]');
  const max = 10; // degrees
  cards.forEach(card => {
    card.addEventListener('mousemove', (e) => {
      const r = card.getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width - 0.5;
      const y = (e.clientY - r.top) / r.height - 0.5;
      const rx = (-y * max).toFixed(2);
      const ry = (x * max).toFixed(2);
      card.style.transform = `perspective(900px) rotateX(${rx}deg) rotateY(${ry}deg) translateY(-2px)`;
    });
    card.addEventListener('mouseleave', () => {
      card.style.transform = `perspective(900px) rotateX(0deg) rotateY(0deg) translateY(0px)`;
    });
  });
})();
