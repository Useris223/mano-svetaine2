async function addToCart(id) {
  try {
    const r = await fetch('/api/cart/add', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ id, qty: 1 })
    });
    const j = await r.json();
    if (!j.ok) {
      alert(j.error || 'Klaida');
      return;
    }
    alert('Įdėta į krepšelį ✅');
  } catch (e) {
    alert('Network error ❌');
  }
}
