function toast(msg){
  const t=document.getElementById('toast');
  t.firstElementChild.textContent=msg;
  t.classList.remove('hidden');
  setTimeout(()=>t.classList.add('hidden'),2200);
}

async function addToCart(id){
  const r=await fetch('/api/cart/add',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({id,qty:1})
  });
  const j=await r.json();
  toast(j.ok?'Įdėta į krepšelį ✅':'Klaida');
}
