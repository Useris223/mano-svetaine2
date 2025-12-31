async function addToCart(id) {
  const r = await fetch('/api/cart/add', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ id, qty: 1 })
  });
  const j = await r.json();
  alert(j.ok ? 'Įdėta į krepšelį ✅' : (j.error || 'Klaida'));
}

async function updateQty(id, qty) {
  const r = await fetch('/api/cart/update', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ id, qty })
  });
  const j = await r.json();
  if (!j.ok) alert(j.error || 'Klaida');
  window.location.reload();
}
