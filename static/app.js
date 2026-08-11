const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];
let MENU = null, CART = [], SUBTOTAL = 0, CATEGORY = 'single';
let FULFILMENT = null, SELECTED_STORE = null, SELECTED_ADDRESS = null, STORES = [];

function toast(msg){ const t=$('#toast'); t.textContent=msg; t.classList.add('show'); setTimeout(()=>t.classList.remove('show'),2600); }
function esc(s=''){ return String(s).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#039;','"':'&quot;'}[c])); }
function sleep(ms){ return new Promise(r => setTimeout(r, ms)); }

async function api(path, opt={}){
  const r = await fetch(path, opt);
  if(!r.ok){ let m='Request failed'; try{ m=(await r.json()).error||m; }catch(e){} throw new Error(m); }
  return r.json();
}

async function loadMenu(){ MENU = await api('/api/menu'); renderMenu(); }
async function loadStores(){ const d = await api('/api/stores'); STORES = d.stores; }
async function refreshCartFromServer(){ const r = await api('/api/cart'); CART=r.cart; SUBTOTAL=r.subtotal; renderCart(); }

function renderMenu(){
  const grid = $('#menuGrid');
  const pizzas = MENU.pizzas.filter(p => p.category === CATEGORY);
  grid.innerHTML = pizzas.map(p => renderPizzaCard(p)).join('');
  pizzas.forEach(p => bindCard(p));
}

function badgeClass(tag){ return tag === 'Healthy Choice' ? 'badge tomato' : 'badge'; }

function renderPizzaCard(p){
  const sizes = MENU.allowed_sizes[p.category];
  const tagsHtml = p.tags.map(t => `<span class="${badgeClass(t)}">${esc(t)}</span>`).join('');
  const sizeOptions = sizes.map((s,i) => `<label class="opt"><input type="radio" name="size-${p.id}" value="${s}" ${i===0?'checked':''}> ${s}</label>`).join('');
  const crustOptions = MENU.crusts.map((c,i) => `<label class="opt"><input type="radio" name="crust-${p.id}" value="${esc(c.name)}" ${i===0?'checked':''}> ${esc(c.name)}${c.price>0?` (+$${c.price.toFixed(2)})`:''}</label>`).join('');
  const toppingOptions = MENU.toppings.map(t => `<label class="opt"><input type="checkbox" name="topping-${p.id}" value="${esc(t.name)}"> ${esc(t.name)} (+$${t.price.toFixed(2)})</label>`).join('');
  return `
  <article class="pizza-card">
    <div class="pizza-photo" id="photo-${p.id}">
      <span class="photo-fallback">🍕</span>
      <div class="photo-badges">${tagsHtml}</div>
      <img src="${esc(p.image || '')}" alt="${esc(p.name)}" loading="lazy"
           onload="this.parentElement.classList.add('loaded')"
           onerror="this.remove()">
    </div>
    <div class="pizza-body">
      <div class="pizza-head"><h3>${esc(p.name)}</h3></div>
      <p class="pizza-desc">${esc(p.description)}</p>
      <div class="pizza-meta"><span class="price">From $${p.base_price.toFixed(2)}</span><span class="cal">${p.base_cal} cal</span></div>
      <button class="secondary-btn customize-btn" data-id="${p.id}">Customize &amp; Add</button>
      <div class="customize-panel" id="panel-${p.id}" hidden>
        <div class="opt-group"><span class="opt-label">Size</span>${sizeOptions}</div>
        <div class="opt-group"><span class="opt-label">Crust</span>${crustOptions}</div>
        <div class="opt-group"><span class="opt-label">Extra toppings</span><div class="topping-grid">${toppingOptions}</div></div>
        <div class="qty-row">
          <span class="opt-label">Qty</span>
          <button class="qty-btn" data-action="dec" data-id="${p.id}">-</button>
          <span id="qty-${p.id}">1</span>
          <button class="qty-btn" data-action="inc" data-id="${p.id}">+</button>
        </div>
        <button class="primary-btn add-btn" data-id="${p.id}">Add to cart &mdash; $${p.base_price.toFixed(2)}</button>
      </div>
    </div>
  </article>`;
}

function bindCard(p){
  const panel = $(`#panel-${p.id}`);
  $(`.customize-btn[data-id="${p.id}"]`).onclick = () => { panel.hidden = !panel.hidden; };
  let qty = 1;
  panel.querySelectorAll(`.qty-btn[data-id="${p.id}"]`).forEach(b => {
    b.onclick = () => { qty = b.dataset.action==='inc' ? qty+1 : Math.max(1,qty-1); $(`#qty-${p.id}`).textContent=qty; updateAddPrice(p.id); };
  });
  panel.querySelectorAll('input').forEach(inp => inp.addEventListener('change', () => updateAddPrice(p.id)));
  $(`.add-btn[data-id="${p.id}"]`).onclick = () => addToCart(p.id, qty);
  updateAddPrice(p.id);
}

function getSelection(pizzaId){
  const size = document.querySelector(`input[name="size-${pizzaId}"]:checked`).value;
  const crust = document.querySelector(`input[name="crust-${pizzaId}"]:checked`).value;
  const toppings = [...document.querySelectorAll(`input[name="topping-${pizzaId}"]:checked`)].map(i=>i.value);
  return {size, crust, toppings};
}

function updateAddPrice(pizzaId){
  const p = MENU.pizzas.find(x => x.id === pizzaId);
  const {size, crust, toppings} = getSelection(pizzaId);
  const sizeStep = MENU.size_price_step;
  const allowed = MENU.allowed_sizes[p.category];
  const base = allowed[0];
  const sizeMod = sizeStep[size] - sizeStep[base];
  const crustObj = MENU.crusts.find(c => c.name === crust);
  const toppingSum = toppings.reduce((s,name) => s + (MENU.toppings.find(t=>t.name===name)?.price||0), 0);
  const qty = parseInt($(`#qty-${pizzaId}`).textContent,10) || 1;
  const unit = p.base_price + sizeMod + (crustObj?crustObj.price:0) + toppingSum;
  const btn = $(`.add-btn[data-id="${pizzaId}"]`);
  if(btn) btn.textContent = `Add to cart — $${(unit*qty).toFixed(2)}`;
}

async function addToCart(pizzaId, qty){
  const {size, crust, toppings} = getSelection(pizzaId);
  try{
    const r = await api('/api/cart/add', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({pizza_id:pizzaId,size,crust,toppings,qty})});
    CART=r.cart; SUBTOTAL=r.subtotal; renderCart(); toast('Added to cart.');
    bumpCart();
  }catch(e){ toast(e.message); }
}

function bumpCart(){
  const panel = $('#cartPanel');
  panel.classList.remove('bump');
  void panel.offsetWidth;
  panel.classList.add('bump');
}

function renderCart(){
  const box = $('#cartItems');
  if(!CART.length){
    box.innerHTML = '<p class="muted">Your cart is empty.</p>';
  } else {
    box.innerHTML = CART.map((item,i) => `
      <div class="cart-item">
        <div>
          <b>${item.qty}x ${esc(item.name)}</b>
          <div class="cart-item-sub">${esc(item.size)} &middot; ${esc(item.crust)}${item.toppings.length?` &middot; +${item.toppings.map(esc).join(', ')}`:''}</div>
        </div>
        <div class="cart-item-right"><span>$${(item.unit_price*item.qty).toFixed(2)}</span><button class="remove-btn" data-idx="${i}">&#10005;</button></div>
      </div>`).join('');
    box.querySelectorAll('.remove-btn').forEach(b => b.onclick = () => removeItem(parseInt(b.dataset.idx,10)));
  }
  $('#cartSubtotal').textContent = `$${SUBTOTAL.toFixed(2)}`;
  $('#checkoutBtn').disabled = CART.length === 0;
}

async function removeItem(idx){
  try{
    const r = await api('/api/cart/remove', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({index:idx})});
    CART=r.cart; SUBTOTAL=r.subtotal; renderCart();
  }catch(e){ toast(e.message); }
}

$$('#categoryTabs .tab').forEach(b => b.onclick = () => {
  $$('#categoryTabs .tab').forEach(x => x.classList.remove('active'));
  b.classList.add('active'); CATEGORY = b.dataset.cat; renderMenu();
});

$('#heroOrderBtn').onclick = () => $('#menuSection').scrollIntoView({behavior:'smooth'});
$('#checkoutBtn').onclick = () => { $('#checkoutSection').hidden = false; $('#checkoutSection').scrollIntoView({behavior:'smooth'}); };
$('#pickupBtn').onclick = () => selectFulfilment('pickup');
$('#deliveryBtn').onclick = () => selectFulfilment('delivery');

function selectFulfilment(type){
  FULFILMENT = type;
  $('#pickupBtn').classList.toggle('active', type==='pickup');
  $('#deliveryBtn').classList.toggle('active', type==='delivery');
  $('#pickupPanel').hidden = type !== 'pickup';
  $('#deliveryPanel').hidden = type !== 'delivery';
  SELECTED_STORE = null; SELECTED_ADDRESS = null;
  $('#placeOrderBtn').disabled = true;
  if(type === 'pickup') renderStores();
}

function renderStores(){
  $('#storeList').innerHTML = STORES.map(s => `<button class="store-btn" data-id="${s.id}"><b>${esc(s.name)}</b><span>${esc(s.address)}</span></button>`).join('');
  $$('.store-btn').forEach(b => b.onclick = () => {
    $$('.store-btn').forEach(x => x.classList.remove('active'));
    b.classList.add('active'); SELECTED_STORE = b.dataset.id; $('#placeOrderBtn').disabled = false;
  });
}

$('#checkAddressBtn').onclick = async () => {
  const q = $('#addressInput').value.trim();
  if(!q) return toast('Enter an address first.');
  $('#addressStatus').textContent = 'Checking address…';
  $('#addressResults').innerHTML = '';
  try{
    const r = await api('/api/address/lookup', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({query:q})});
    $('#addressStatus').textContent = r.fallback ? "We couldn't verify that live — pick the closest match below:" : 'Select the correct address:';
    $('#addressResults').innerHTML = r.results.map((res,i) => `<button class="address-btn" data-i="${i}">${esc(res.label)}</button>`).join('');
    $$('.address-btn').forEach((b,i) => b.onclick = () => {
      $$('.address-btn').forEach(x => x.classList.remove('active'));
      b.classList.add('active'); SELECTED_ADDRESS = r.results[i]; $('#placeOrderBtn').disabled = false;
    });
  }catch(e){ $('#addressStatus').textContent = `Could not check address: ${e.message}`; }
};

$('#placeOrderBtn').onclick = placeOrder;

async function placeOrder(){
  $('#orderFlow').hidden = false;
  $('#orderFlow').scrollIntoView({behavior:'smooth'});
  $('#progressLines').innerHTML = '';
  $('#traceDetails').hidden = true;
  $('#geminiMessageBox').hidden = true;
  $('#countdownBox').hidden = true;
  $('#confirmationBox').hidden = true;
  $('#unavailableBox').hidden = true;
  $('#placeOrderBtn').disabled = true;

  const payload = {fulfilment: FULFILMENT};
  if(FULFILMENT === 'pickup') payload.store_id = SELECTED_STORE; else payload.address = SELECTED_ADDRESS;

  let result;
  try{
    result = await api('/api/order/process', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
  }catch(e){
    $('#progressLines').innerHTML = `<p class="error-line">Something went wrong: ${esc(e.message)}</p>`;
    $('#placeOrderBtn').disabled = false;
    return;
  }

  const friendly = {
    1: 'Checking your order…',
    2: FULFILMENT === 'pickup' ? 'Confirming your pickup store…' : 'Finding your nearest kitchen…',
    3: 'Confirming with our assistant…',
    4: result.can_fulfil ? 'Order confirmed!' : 'Checking delivery availability…'
  };

  for(const step of result.steps){
    await sleep(550);
    const line = document.createElement('p');
    line.className = 'progress-line';
    line.textContent = `✓ ${friendly[step.step] || step.title}`;
    $('#progressLines').appendChild(line);
  }

  $('#traceSteps').innerHTML = result.steps.map(s => `<div class="trace-step"><b>STEP ${s.step} - ${esc(s.title)}</b><p>${esc(s.detail)}</p></div>`).join('');
  $('#traceDetails').hidden = false;

  $('#geminiMessageBox').hidden = false;
  $('#geminiMessageBox').textContent = result.gemini_message;

  if(result.can_fulfil){
    $('#countdownBox').hidden = false;
    let n = 10;
    $('#countdownNum').textContent = n;
    const timer = setInterval(() => {
      n -= 1; $('#countdownNum').textContent = Math.max(n,0);
      if(n <= 0){ clearInterval(timer); showConfirmation(result.order); }
    }, 1000);
  } else {
    $('#unavailableBox').hidden = false;
    $('#unavailableBox').innerHTML = `<p>Delivery isn't available for this address. Scroll up and choose Pickup instead.</p>`;
    await refreshCartFromServer();
    $('#placeOrderBtn').disabled = false;
  }
}

function showConfirmation(order){
  $('#countdownBox').hidden = true;
  const box = $('#confirmationBox');
  box.hidden = false;
  const itemsHtml = order.items.map(i => `<li>${i.qty}x ${esc(i.name)} (${esc(i.size)}, ${esc(i.crust)}) — $${(i.unit_price*i.qty).toFixed(2)}</li>`).join('');
  box.innerHTML = `
    <h2>&#127881; Order Confirmed</h2>
    <p class="order-number">Order #${esc(order.order_number)}</p>
    <ul class="order-items">${itemsHtml}</ul>
    <div class="order-line"><span>Subtotal</span><span>$${order.subtotal.toFixed(2)}</span></div>
    <div class="order-line"><span>Delivery fee</span><span>$${order.delivery_fee.toFixed(2)}</span></div>
    <div class="order-line total"><span>Total</span><span>$${order.total.toFixed(2)}</span></div>
    <p>${order.fulfilment==='pickup' ? `Pickup at <b>${esc(order.store.name)}</b>, ${esc(order.store.address)}.` : `Delivering from <b>${esc(order.store.name)}</b> — approx ${order.distance_km}km away.`}</p>
    <p>Estimated ${order.fulfilment==='pickup'?'ready':'delivery'} time: <b>${order.eta_minutes} minutes</b>.</p>
  `;
  CART = []; SUBTOTAL = 0; renderCart();
}

$('#simpleToggle').onclick = () => { document.documentElement.classList.toggle('simple-mode'); $('#simpleToggle').classList.toggle('active'); };
$('#largeToggle').onclick = () => { document.documentElement.classList.toggle('large-text'); $('#largeToggle').classList.toggle('active'); };

(async function init(){ await loadMenu(); await loadStores(); await refreshCartFromServer(); })();
