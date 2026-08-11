const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];
let MENU = null, CART = [], SUBTOTAL = 0, CATEGORY = 'single';
let FULFILMENT = null, SELECTED_STORE = null, SELECTED_ADDRESS = null, STORES = [];
let CURRENT_PIZZA_ID = null, MODAL_QTY = 1;

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

function badgeClass(tag){ return tag === 'Healthy Choice' ? 'badge tomato' : 'badge'; }

/* ---------------- MENU / CARDS ---------------- */

function renderMenu(){
  const grid = $('#menuGrid');
  const pizzas = MENU.pizzas.filter(p => p.category === CATEGORY);
  grid.innerHTML = pizzas.map(p => renderPizzaCard(p)).join('');
  pizzas.forEach(p => {
    $(`.customize-btn[data-id="${p.id}"]`).onclick = () => openCustomizeModal(p.id);
  });
}

function renderPizzaCard(p){
  const tagsHtml = p.tags.map(t => `<span class="${badgeClass(t)}">${esc(t)}</span>`).join('');
  return `
  <article class="pizza-card">
    <div class="pizza-photo">
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
    </div>
  </article>`;
}

/* ---------------- CUSTOMIZATION MODAL ---------------- */

function openCustomizeModal(pizzaId){
  const p = MENU.pizzas.find(x => x.id === pizzaId);
  if(!p) return;
  CURRENT_PIZZA_ID = pizzaId;
  MODAL_QTY = 1;

  $('#modalImg').src = p.image || '';
  $('#modalImg').alt = p.name;
  $('#modalBadges').innerHTML = p.tags.map(t => `<span class="${badgeClass(t)}">${esc(t)}</span>`).join('');
  $('#modalTitle').textContent = p.name;
  $('#modalDesc').textContent = p.description;
  $('#modalCal').textContent = `${p.base_cal} cal (base)`;
  $('#modalQty').textContent = MODAL_QTY;

  const sizes = MENU.allowed_sizes[p.category];
  $('#modalSizeOptions').innerHTML = sizes.map((s,i) => `<label class="opt"><input type="radio" name="modalSize" value="${s}" ${i===0?'checked':''}> ${s}</label>`).join('');
  $('#modalCrustOptions').innerHTML = MENU.crusts.map((c,i) => `<label class="opt"><input type="radio" name="modalCrust" value="${esc(c.name)}" ${i===0?'checked':''}> ${esc(c.name)}${c.price>0?` (+$${c.price.toFixed(2)})`:''}</label>`).join('');
  $('#modalToppingOptions').innerHTML = MENU.toppings.map(t => `<label class="opt"><input type="checkbox" name="modalTopping" value="${esc(t.name)}"> ${esc(t.name)} (+$${t.price.toFixed(2)})</label>`).join('');

  $$('#modalSizeOptions input, #modalCrustOptions input, #modalToppingOptions input').forEach(inp => {
    inp.addEventListener('change', updateModalPrice);
  });

  updateModalPrice();

  $('#modalBackdrop').hidden = false;
  $('#customizeModal').hidden = false;
  document.body.style.overflow = 'hidden';
}

function closeModal(){
  $('#modalBackdrop').hidden = true;
  $('#customizeModal').hidden = true;
  document.body.style.overflow = '';
}

function getModalSelection(){
  const size = document.querySelector('input[name="modalSize"]:checked')?.value;
  const crust = document.querySelector('input[name="modalCrust"]:checked')?.value;
  const toppings = [...document.querySelectorAll('input[name="modalTopping"]:checked')].map(i => i.value);
  return {size, crust, toppings};
}

function updateModalPrice(){
  const p = MENU.pizzas.find(x => x.id === CURRENT_PIZZA_ID);
  if(!p) return;
  const {size, crust, toppings} = getModalSelection();
  const sizeStep = MENU.size_price_step;
  const allowed = MENU.allowed_sizes[p.category];
  const base = allowed[0];
  const sizeMod = sizeStep[size] - sizeStep[base];
  const crustObj = MENU.crusts.find(c => c.name === crust);
  const toppingSum = toppings.reduce((s,name) => s + (MENU.toppings.find(t=>t.name===name)?.price||0), 0);
  const unit = p.base_price + sizeMod + (crustObj?crustObj.price:0) + toppingSum;
  $('#modalAddBtn').textContent = `Add to cart — $${(unit*MODAL_QTY).toFixed(2)}`;
}

$('#modalQtyDec').onclick = () => { MODAL_QTY = Math.max(1, MODAL_QTY-1); $('#modalQty').textContent = MODAL_QTY; updateModalPrice(); };
$('#modalQtyInc').onclick = () => { MODAL_QTY += 1; $('#modalQty').textContent = MODAL_QTY; updateModalPrice(); };
$('#modalCloseBtn').onclick = closeModal;
$('#modalBackdrop').onclick = closeModal;

$('#modalAddBtn').onclick = async () => {
  const {size, crust, toppings} = getModalSelection();
  try{
    const r = await api('/api/cart/add', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({pizza_id:CURRENT_PIZZA_ID,size,crust,toppings,qty:MODAL_QTY})});
    CART=r.cart; SUBTOTAL=r.subtotal; renderCart(); toast('Added to cart.'); bumpCart();
    closeModal();
  }catch(e){ toast(e.message); }
};

function bumpCart(){
  const panel = $('#cartPanel');
  panel.classList.remove('bump');
  void panel.offsetWidth;
  panel.classList.add('bump');
}

/* ---------------- CART ---------------- */

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
  updateCartBadges();
}

function updateCartBadges(){
  const count = CART.reduce((n,i) => n+i.qty, 0);
  [$('#navCartCount'), $('#bottomCartCount')].forEach(el => {
    if(!el) return;
    el.textContent = count > 99 ? '99+' : count;
    el.hidden = count === 0;
  });
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
    <button class="secondary-btn" id="trackThisOrderBtn">📦 Track this order</button>
  `;
  localStorage.setItem('hp_last_order', JSON.stringify(order));
  $('#trackThisOrderBtn').onclick = openTracker;
  CART = []; SUBTOTAL = 0; renderCart();
}

/* ---------------- DEALS CAROUSEL ---------------- */

let DEALS = [], DEAL_IDX = 0, DEAL_TIMER = null;

async function loadDeals(){
  try{
    const r = await api('/api/deals');
    DEALS = r.deals || [];
    renderDeals();
    startDealRotation();
  }catch(e){ /* deals are non-essential; fail silently */ }
}

function renderDeals(){
  if(!DEALS.length) return;
  $('#dealTrack').innerHTML = DEALS.map((d,i) => `
    <div class="deal-slide ${i===0?'active':''}" data-i="${i}">
      <div class="deal-icon">${d.icon}</div>
      <div class="deal-text">
        <h3>${esc(d.title)}</h3>
        <p>${esc(d.desc)}</p>
        ${d.code ? `<span class="deal-code">CODE: ${esc(d.code)}</span>` : ''}
      </div>
    </div>`).join('');
  $('#dealDots').innerHTML = DEALS.map((_,i) => `<button class="deal-dot ${i===0?'active':''}" data-i="${i}"></button>`).join('');
  $$('.deal-dot').forEach(b => b.onclick = () => { showDeal(parseInt(b.dataset.i,10)); resetDealRotation(); });
}

function showDeal(i){
  DEAL_IDX = (i + DEALS.length) % DEALS.length;
  $$('.deal-slide').forEach(s => s.classList.toggle('active', parseInt(s.dataset.i,10) === DEAL_IDX));
  $$('.deal-dot').forEach((d,idx) => d.classList.toggle('active', idx === DEAL_IDX));
}

function startDealRotation(){
  DEAL_TIMER = setInterval(() => showDeal(DEAL_IDX+1), 4500);
}
function resetDealRotation(){
  clearInterval(DEAL_TIMER);
  startDealRotation();
}

$('#dealPrev').onclick = () => { showDeal(DEAL_IDX-1); resetDealRotation(); };
$('#dealNext').onclick = () => { showDeal(DEAL_IDX+1); resetDealRotation(); };

/* ---------------- ORDER TRACKER ---------------- */

const TRACKER_STAGES = [
  {key:'placed', icon:'🧾', pct:0, label:'Order placed'},
  {key:'prep', icon:'🥗', pct:0.12, label:'Preparing'},
  {key:'bake', icon:'🔥', pct:0.42, label:'Baking'},
  {key:'quality', icon:'✅', pct:0.72, label:'Quality check'},
  {key:'out', icon:'🚗', pct:0.88},   // label depends on fulfilment
  {key:'done', icon:'🎉', pct:1.0},   // label depends on fulfilment
];
let TRACKER_TIMER = null;

function stageLabel(stage, fulfilment){
  if(stage.key === 'out') return fulfilment === 'pickup' ? 'Ready for pickup' : 'Out for delivery';
  if(stage.key === 'done') return fulfilment === 'pickup' ? 'Picked up' : 'Delivered';
  return stage.label;
}

function computeStage(order){
  const placedAt = new Date(order.placed_at).getTime();
  const etaMs = Math.max(1, order.eta_minutes) * 60000;
  const elapsed = Date.now() - (isNaN(placedAt) ? Date.now() : placedAt);
  const frac = Math.min(1, Math.max(0, elapsed / etaMs));
  let idx = 0;
  TRACKER_STAGES.forEach((s,i) => { if(frac >= s.pct) idx = i; });
  const remainingMin = Math.max(0, Math.ceil((etaMs - elapsed) / 60000));
  return {idx, remainingMin};
}

function renderTracker(order){
  const {idx, remainingMin} = computeStage(order);
  const stagesHtml = TRACKER_STAGES.map((s,i) => {
    const cls = i < idx ? 'done' : (i === idx ? 'current' : '');
    return `<div class="tracker-stage ${cls}">
      <div class="tracker-dot">${s.icon}</div>
      <div class="tracker-stage-label">${esc(stageLabel(s, order.fulfilment))}</div>
    </div>`;
  }).join('');
  const itemsSummary = order.items.map(i => `${i.qty}x ${i.name}`).join(', ');
  $('#trackerContent').innerHTML = `
    <p class="tracker-order-no">Order #${esc(order.order_number)}</p>
    <p class="tracker-meta">${order.fulfilment==='pickup' ? `Pickup from ${esc(order.store.name)}` : `Delivering from ${esc(order.store.name)}`}</p>
    <div class="tracker-stages">${stagesHtml}</div>
    <div class="tracker-eta">${idx >= TRACKER_STAGES.length-1 ? 'Order complete!' : `~${remainingMin} minute${remainingMin===1?'':'s'} remaining`}</div>
    <div class="tracker-items">${esc(itemsSummary)}</div>
  `;
}

function openTracker(){
  closeStub();
  const raw = localStorage.getItem('hp_last_order');
  if(!raw){
    openStub('track');
    return;
  }
  const order = JSON.parse(raw);
  renderTracker(order);
  $('#trackerBackdrop').hidden = false;
  $('#trackerModal').hidden = false;
  clearInterval(TRACKER_TIMER);
  TRACKER_TIMER = setInterval(() => renderTracker(order), 20000);
}

function closeTracker(){
  $('#trackerBackdrop').hidden = true;
  $('#trackerModal').hidden = true;
  clearInterval(TRACKER_TIMER);
  setActiveNav('home');
}

$('#simpleToggle').onclick = () => { document.documentElement.classList.toggle('simple-mode'); $('#simpleToggle').classList.toggle('active'); };
$('#largeToggle').onclick = () => { document.documentElement.classList.toggle('large-text'); $('#largeToggle').classList.toggle('active'); };

/* ---------------- NAVIGATION (top nav + bottom nav) ---------------- */

const STUB_CONTENT = {
  track: {icon:'📦', title:'No order yet', body:"You haven't placed an order on this device. Place one and you'll be able to track it here."},
  account: {icon:'👤', title:'Account', body:"Accounts, saved addresses and order history aren't part of this demo yet."},
};

function openStub(key){
  const s = STUB_CONTENT[key];
  if(!s) return;
  $('#stubContent').innerHTML = `<div class="stub-icon">${s.icon}</div><h3>${esc(s.title)}</h3><p>${esc(s.body)}</p>`;
  $('#stubBackdrop').hidden = false;
  $('#stubModal').hidden = false;
}
function closeStub(){ $('#stubBackdrop').hidden = true; $('#stubModal').hidden = true; setActiveNav('home'); }

function setActiveNav(target){
  $$('.nav-link, .bn-btn').forEach(el => el.classList.toggle('active', el.dataset.nav === target));
}

function handleNav(target){
  setActiveNav(target);
  if(target === 'home'){ $('#homeTop').scrollIntoView({behavior:'smooth'}); }
  else if(target === 'menu'){ $('#menuSection').scrollIntoView({behavior:'smooth'}); }
  else if(target === 'cart'){ $('#cartPanel').scrollIntoView({behavior:'smooth'}); bumpCart(); }
  else if(target === 'deals'){ $('#dealsSection').scrollIntoView({behavior:'smooth'}); }
  else if(target === 'track'){ openTracker(); }
  else if(target === 'account'){ openStub('account'); }
}

$$('.nav-link, .bn-btn, .cart-icon-btn').forEach(el => {
  el.addEventListener('click', () => handleNav(el.dataset.nav));
});

// Delegated close handling — belt-and-braces so a popup can ALWAYS be
// dismissed (click the ×, click the dark backdrop, or press Escape),
// even if a direct binding is ever missed.
document.addEventListener('click', (e) => {
  if(e.target.closest('#modalCloseBtn') || e.target.id === 'modalBackdrop'){ closeModal(); }
  if(e.target.closest('#stubCloseBtn') || e.target.id === 'stubBackdrop'){ closeStub(); }
  if(e.target.closest('#trackerCloseBtn') || e.target.id === 'trackerBackdrop'){ closeTracker(); }
});
document.addEventListener('keydown', (e) => {
  if(e.key === 'Escape'){ closeModal(); closeStub(); closeTracker(); }
});

(async function init(){ await loadMenu(); await loadStores(); await loadDeals(); await refreshCartFromServer(); })();
