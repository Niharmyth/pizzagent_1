const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];
let MENU = null, CART = [], SUBTOTAL = 0, CATEGORY = 'single';
let FULFILMENT = null, SELECTED_STORE = null, SELECTED_ADDRESS = null, STORES = [];
let CURRENT_PIZZA_ID = null, MODAL_QTY = 1;
let SEARCH_QUERY = '', ACTIVE_FILTERS = new Set();

function toast(msg){ const t=$('#toast'); t.textContent=msg; t.classList.add('show'); setTimeout(()=>t.classList.remove('show'),2600); }
function esc(s=''){ return String(s).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#039;','"':'&quot;'}[c])); }
function sleep(ms){ return new Promise(r => setTimeout(r, ms)); }

/* ---------------- AGENTIC LIVE FLOW ---------------- */
const AI_FLOW_STAGES = ['customer','agent','tools','order','kitchen','ready'];
const AI_FLOW_COPY = {
  customer: ['Customer', 'Pizza selected', 'You choose a pizza or describe what you want to Pizzomania AI.'],
  agent: ['Pizza AI', 'Understanding your craving', 'The agent interprets taste, budget and dietary preferences.'],
  tools: ['Agent Tools', 'Validating the pizza', 'Menu availability, toppings, size, crust and server-side price are checked.'],
  order: ['Order Agent', 'Pizza approved', 'Your approved configuration enters the real cart and checkout flow.'],
  kitchen: ['Kitchen', 'Pizza is being prepared', 'The preparation sequence moves from dough to sauce to toppings to oven.'],
  ready: ['Delivery', 'Order ready', 'Your order status and pickup/delivery ETA are now available.']
};
let AI_FLOW_INDEX = 0;
let AI_FLOW_TIMER = null;
let AI_FLOW_HISTORY = [];

function flowPacketTo(stage){
  const packet = $('#flowPacket');
  if(!packet) return;
  const idx = AI_FLOW_STAGES.indexOf(stage);
  const pct = 6 + (idx / (AI_FLOW_STAGES.length - 1)) * 88;
  packet.classList.remove('running');
  packet.style.left = `${pct}%`;
  packet.style.top = '58px';
  void packet.offsetWidth;
  packet.classList.add('pulse');
  setTimeout(()=>packet.classList.remove('pulse'),700);
}

function pushFlowHistory(stage, detail){
  const copy = AI_FLOW_COPY[stage];
  AI_FLOW_HISTORY.unshift({stage, label:copy[0], detail:detail || copy[1], time:new Date()});
  AI_FLOW_HISTORY = AI_FLOW_HISTORY.slice(0,4);
  const log = $('#aiFlowHistory');
  if(!log) return;
  log.innerHTML = AI_FLOW_HISTORY.map((item,i)=>`<span class="flow-history-item ${i===0?'latest':''}"><i>${i===0?'●':'✓'}</i><b>${esc(item.label)}</b><em>${esc(item.detail)}</em></span>`).join('');
}

function setAgentFlow(stage, detail=null){
  const idx = AI_FLOW_STAGES.indexOf(stage);
  if(idx < 0) return;
  AI_FLOW_INDEX = idx;
  $$('.flow-node').forEach(node => {
    const n = AI_FLOW_STAGES.indexOf(node.dataset.flowNode);
    node.classList.toggle('active', n === idx);
    node.classList.toggle('done', n < idx);
  });
  const copy = AI_FLOW_COPY[stage];
  $('#aiFlowStatus').textContent = copy[0];
  $('#aiFlowDetail').textContent = detail || copy[1];
  $('#aiFlowEvent').innerHTML = `<span>LIVE EVENT</span><b>${esc(detail || copy[1])}</b>`;
  flowPacketTo(stage);
  pushFlowHistory(stage, detail);
}

function startAgentFlowDemo(){
  clearInterval(AI_FLOW_TIMER);
  AI_FLOW_HISTORY = [];
  const packet = $('#flowPacket');
  if(packet){ packet.classList.remove('running'); packet.style.left='6%'; }
  let i = 0;
  setAgentFlow(AI_FLOW_STAGES[0], 'Customer selects a pizza or tells Pizzomania AI what they want.');
  $('#playAiFlowBtn').disabled = true;
  $('#playAiFlowBtn').textContent = '● Demo running';
  AI_FLOW_TIMER = setInterval(() => {
    i += 1;
    if(i >= AI_FLOW_STAGES.length){
      clearInterval(AI_FLOW_TIMER);
      setAgentFlow('ready', 'Pizza journey complete — ready for pickup or delivery.');
      $('#playAiFlowBtn').disabled = false;
      $('#playAiFlowBtn').textContent = '↻ Play again';
      return;
    }
    const demoCopy = {
      agent:'AI understood the craving and is building a pizza proposal.',
      tools:'Checking menu availability, toppings and authoritative price.',
      order:'Customer approved the pizza — sending it into the real cart flow.',
      kitchen:'Order confirmed — the Pizzomania kitchen is preparing it.',
      ready:'Pizza is ready — order status and ETA are now available.'
    };
    setAgentFlow(AI_FLOW_STAGES[i], demoCopy[AI_FLOW_STAGES[i]]);
  }, 1500);
}

function resetAgentFlow(){
  clearInterval(AI_FLOW_TIMER);
  AI_FLOW_HISTORY = [];
  const packet = $('#flowPacket');
  if(packet){ packet.classList.remove('running','pulse'); packet.style.left='6%'; }
  setAgentFlow('customer', 'Waiting for a customer to start an order.');
  $('#playAiFlowBtn').disabled = false;
  $('#playAiFlowBtn').textContent = '▶ Play live demo';
}

$('#playAiFlowBtn')?.addEventListener('click', startAgentFlowDemo);

async function api(path, opt={}){
  const r = await fetch(path, opt);
  if(!r.ok){ let m='Request failed'; try{ m=(await r.json()).error||m; }catch(e){} throw new Error(m); }
  return r.json();
}

let FEATURED_BADGES = {};

async function loadMenu(){ MENU = await api('/api/menu'); FEATURED_BADGES = computeFeaturedBadges(MENU.pizzas); renderMenu(); }
async function loadStores(){ const d = await api('/api/stores'); STORES = d.stores; }
async function refreshCartFromServer(){ const r = await api('/api/cart'); CART=r.cart; SUBTOTAL=r.subtotal; renderCart(); }

function badgeClass(tag){ return tag === 'Healthy Choice' ? 'badge tomato' : 'badge'; }

// Compute at most two extra, data-driven badges per menu category (the
// top-rated pizza gets "Mania Favourite"; the next most-reviewed pizza in
// that category gets "Popular") so badges stay tasteful rather than
// appearing on every card.
function computeFeaturedBadges(pizzas){
  const byCategory = {};
  pizzas.forEach(p => { (byCategory[p.category] = byCategory[p.category] || []).push(p); });
  const featured = {};
  Object.values(byCategory).forEach(list => {
    if(!list.length) return;
    const topRated = [...list].sort((a,b) => (b.rating||0)-(a.rating||0) || (b.reviews||0)-(a.reviews||0))[0];
    featured[topRated.id] = 'Mania Favourite';
    const topReviewed = [...list].filter(p => p.id !== topRated.id).sort((a,b) => (b.reviews||0)-(a.reviews||0))[0];
    if(topReviewed) featured[topReviewed.id] = 'Popular';
  });
  return featured;
}

function featuredBadgeHtml(p){
  const label = FEATURED_BADGES[p.id];
  if(!label) return '';
  return `<span class="badge featured ${label==='Mania Favourite'?'mania':'popular'}">${label}</span>`;
}

/* ---------------- MENU / CARDS ---------------- */

function renderMenu(){
  const grid = $('#menuGrid');
  const q = SEARCH_QUERY.trim().toLowerCase();
  let pizzas = q
    ? MENU.pizzas.filter(p => (p.name + ' ' + p.description).toLowerCase().includes(q))
    : MENU.pizzas.filter(p => p.category === CATEGORY);

  if(ACTIVE_FILTERS.has('vegan')) pizzas = pizzas.filter(p => p.tags.includes('Vegan'));
  if(ACTIVE_FILTERS.has('vegetarian')) pizzas = pizzas.filter(p => p.tags.includes('Vegetarian'));
  if(ACTIVE_FILTERS.has('healthy')) pizzas = pizzas.filter(p => p.tags.includes('Healthy Choice'));
  if(ACTIVE_FILTERS.has('under500')) pizzas = pizzas.filter(p => p.base_cal < 500);
  if(ACTIVE_FILTERS.has('under15')) pizzas = pizzas.filter(p => p.base_price < 15);

  if(!pizzas.length){
    grid.innerHTML = `<div class="empty-menu"><p>No pizzas match your search or filters.</p><button class="secondary-btn" id="clearFiltersBtn">Clear search &amp; filters</button></div>`;
    $('#clearFiltersBtn').onclick = clearSearchAndFilters;
    return;
  }

  grid.innerHTML = pizzas.map(p => renderPizzaCard(p)).join('');
  pizzas.forEach(p => {
    $(`.customize-btn[data-id="${p.id}"]`).onclick = () => { setAgentFlow('customer', `Customer selected ${p.name} and opened customization.`); openCustomizeModal(p.id); };
  });
}

function clearSearchAndFilters(){
  SEARCH_QUERY = '';
  $('#menuSearch').value = '';
  ACTIVE_FILTERS.clear();
  $$('.chip').forEach(c => c.classList.remove('active'));
  renderMenu();
}

function ratingHtml(p){
  if(!p.rating) return '';
  return `<div class="pizza-rating"><span class="stars">★</span> ${p.rating.toFixed(1)} <span class="muted">(${p.reviews})</span></div>`;
}

function renderPizzaCard(p){
  const tagsHtml = p.tags.map(t => `<span class="${badgeClass(t)}">${esc(t)}</span>`).join('');
  return `
  <article class="pizza-card">
    <div class="pizza-photo">
      <span class="photo-fallback">🍕</span>
      <div class="photo-badges">${featuredBadgeHtml(p)}${tagsHtml}</div>
      <img src="${esc(p.image || '')}" alt="${esc(p.name)}" loading="lazy"
           onload="this.parentElement.classList.add('loaded')"
           onerror="this.remove()">
    </div>
    <div class="pizza-body">
      <div class="pizza-head"><h3>${esc(p.name)}</h3></div>
      ${ratingHtml(p)}
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
  $('#modalBadges').innerHTML = featuredBadgeHtml(p) + p.tags.map(t => `<span class="${badgeClass(t)}">${esc(t)}</span>`).join('');
  $('#modalTitle').textContent = p.name;
  $('#modalDesc').textContent = p.description;
  $('#modalCal').textContent = p.rating ? `${p.base_cal} cal (base) · ★ ${p.rating.toFixed(1)} (${p.reviews} reviews)` : `${p.base_cal} cal (base)`;
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

$('#menuSearch').addEventListener('input', () => { SEARCH_QUERY = $('#menuSearch').value; renderMenu(); });
$$('.chip').forEach(c => c.onclick = () => {
  c.classList.toggle('active');
  const f = c.dataset.filter;
  if(ACTIVE_FILTERS.has(f)) ACTIVE_FILTERS.delete(f); else ACTIVE_FILTERS.add(f);
  renderMenu();
});

$$('#categoryTabs .tab').forEach(b => b.onclick = () => {
  $$('#categoryTabs .tab').forEach(x => x.classList.remove('active'));
  b.classList.add('active'); CATEGORY = b.dataset.cat;
  SEARCH_QUERY = ''; $('#menuSearch').value = '';
  renderMenu();
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
  $('#storeList').innerHTML = STORES.map(s => `<button class="store-btn" data-id="${s.id}"><b>${esc(s.name)}</b><span>${esc(s.address)}</span>${s.rating ? `<span class="store-rating">★ ${s.rating.toFixed(1)} <span>(${s.reviews})</span></span>` : ''}</button>`).join('');
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

// Four-stage branded loading progression shown during the 10s countdown.
const LOADING_STAGES = [
  {img:'/static/images/loading/dough.png', text:'Preparing your dough…'},
  {img:'/static/images/loading/sauce.png', text:'Adding the sauce…'},
  {img:'/static/images/loading/oven.png', text:'Baking to perfection…'},
  {img:'/static/images/loading/ready.png', text:'Almost ready!'},
];
function setLoadingStage(elapsedSeconds){
  const idx = Math.min(LOADING_STAGES.length-1, Math.floor(elapsedSeconds / 2.5));
  const img = $('#loadingStageImg');
  if(img.dataset.stage == idx) return;
  img.dataset.stage = idx;
  const stage = LOADING_STAGES[idx];
  if(idx < 3) setAgentFlow('kitchen', stage.text);
  else setAgentFlow('ready', 'Pizza is ready — your order status is now available.');
  const wrap = $('.loading-stage');
  wrap.classList.remove('stage-fade');
  void wrap.offsetWidth;
  img.src = stage.img;
  img.alt = stage.text.replace('…', '');
  $('#loadingStageText').textContent = stage.text;
  wrap.classList.add('stage-fade');
}

$('#placeOrderBtn').onclick = placeOrder;

async function placeOrder(){
  setAgentFlow('order', 'Customer approved the pizza — sending it through checkout.');
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

  setAgentFlow('tools', 'Backend validated the order, fulfilment and kitchen route.');

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
  if(result.can_fulfil){
    setAgentFlow('kitchen', 'Order confirmed. The kitchen is now preparing your pizza.');
  }
  $('#traceDetails').hidden = false;

  $('#geminiMessageBox').hidden = false;
  $('#geminiMessageBox').textContent = result.gemini_message;

  if(result.can_fulfil){
    $('#countdownBox').hidden = false;
    let n = 10;
    $('#countdownNum').textContent = n;
    setLoadingStage(0);
    const timer = setInterval(() => {
      n -= 1; $('#countdownNum').textContent = Math.max(n,0);
      setLoadingStage(10 - n);
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
  saveOrderToHistory(order);
  incrementLoyaltyPoints();
  $('#trackThisOrderBtn').onclick = openTracker;
  CART = []; SUBTOTAL = 0; renderCart();
}

/* ---------------- ORDER HISTORY / LOYALTY / REORDER ---------------- */

function getOrderHistory(){
  try{ return JSON.parse(localStorage.getItem('hp_order_history') || '[]'); }
  catch(e){ return []; }
}

function saveOrderToHistory(order){
  const hist = getOrderHistory();
  hist.unshift(order);
  localStorage.setItem('hp_order_history', JSON.stringify(hist.slice(0, 10)));
  localStorage.setItem('hp_last_order', JSON.stringify(order));
}

function getLoyaltyPoints(){
  return parseInt(localStorage.getItem('hp_points_total') || '0', 10);
}

function incrementLoyaltyPoints(){
  const next = getLoyaltyPoints() + 1;
  localStorage.setItem('hp_points_total', String(next));
  return next;
}

function formatDate(iso){
  try{ return new Date(iso).toLocaleString(undefined, {dateStyle:'medium', timeStyle:'short'}); }
  catch(e){ return ''; }
}

function renderAccount(){
  const hist = getOrderHistory();
  const points = getLoyaltyPoints();
  const progress = points % 5;
  const rewards = Math.floor(points / 5);
  const dots = Array.from({length:5}, (_,i) => `<span class="loyalty-dot ${i < progress ? 'filled' : ''}">🍕</span>`).join('');
  const historyHtml = hist.length ? hist.map((o,i) => `
    <div class="history-card">
      <div class="history-head"><b>Order #${esc(o.order_number)}</b><span class="muted">${esc(formatDate(o.placed_at))}</span></div>
      <div class="history-items muted">${esc(o.items.map(it => `${it.qty}x ${it.name}`).join(', '))}</div>
      <div class="history-foot">
        <span>$${o.total.toFixed(2)} &middot; ${esc(o.fulfilment)}</span>
        <button class="secondary-btn reorder-btn" data-idx="${i}">🔁 Reorder</button>
      </div>
    </div>`).join('') : '<p class="muted">No orders yet — place one to start earning rewards!</p>';

  $('#accountContent').innerHTML = `
    <h2>👤 Your Account</h2>
    <div class="loyalty-box">
      <div class="loyalty-dots">${dots}</div>
      <p>${progress}/5 orders toward a free pizza${rewards > 0 ? ` &middot; 🎁 ${rewards} reward${rewards>1?'s':''} earned` : ''}</p>
    </div>
    <h3>Order history</h3>
    <div class="history-list">${historyHtml}</div>
  `;
  $$('.reorder-btn').forEach(b => b.onclick = () => reorder(hist[parseInt(b.dataset.idx,10)]));
}

async function reorder(order){
  if(!order) return;
  try{
    for(const item of order.items){
      await api('/api/cart/add', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({pizza_id:item.pizza_id, size:item.size, crust:item.crust, toppings:item.toppings, qty:item.qty})
      });
    }
    await refreshCartFromServer();
    toast('Order items added to your cart.');
    closeAccount();
    $('#cartPanel').scrollIntoView({behavior:'smooth'});
  }catch(e){ toast('Could not reorder: ' + e.message); }
}

function openAccount(){
  renderAccount();
  $('#accountBackdrop').hidden = false;
  $('#accountModal').hidden = false;
}
function closeAccount(){
  $('#accountBackdrop').hidden = true;
  $('#accountModal').hidden = true;
  setActiveNav('home');
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
    <div class="deal-slide ${i===0?'active':''}${d.image?' has-photo':''}" data-i="${i}"${d.image?` style="--deal-photo:url('${d.image}')"`:''}>
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
  {key:'placed', icon:'🧾'},
  {key:'prep', icon:'🥗'},
  {key:'bake', icon:'🔥'},
  {key:'quality', icon:'✅'},
  {key:'out', icon:'🚗'},
  {key:'done', icon:'🎉'},
];
let TRACKER_TIMER = null;

function syncFlowToOrderStatus(status){
  if(!status) return;
  const map={placed:'customer',prep:'kitchen',bake:'kitchen',quality:'tools',out:'ready',done:'ready'};
  const stage=map[status.stage_key];
  if(stage) setAgentFlow(stage, `Order status: ${status.status}.`);
}

function renderTracker(order, status){
  if(!status){
    $('#trackerContent').innerHTML='<p class="muted">I can’t retrieve the live order status right now. Please try again.</p>';
    return;
  }
  const idx=status.stage_index;
  const remainingMin=status.remaining_min;
  const stagesHtml=TRACKER_STAGES.map((st,i)=>{
    const cls=i<idx?'done':(i===idx?'current':'');
    const label=status.stages?.[i] || st.key;
    return `<div class="tracker-stage ${cls}"><div class="tracker-dot">${st.icon}</div><div class="tracker-stage-label">${esc(label)}</div></div>`;
  }).join('');
  const itemsSummary=order.items.map(i=>`${i.qty}x ${i.name}`).join(', ');
  const bakingHtml=status.stage_key==='bake'?`
    <div class="tracker-baking">
      <img src="/static/images/loading/oven.png" alt="Pizza baking in the oven" class="tracker-baking-img">
      <p class="tracker-baking-text">YOUR PIZZA IS IN THE OVEN 🔥<br><span>~${remainingMin} minute${remainingMin===1?'':'s'} remaining</span></p>
    </div>`:'';
  $('#trackerContent').innerHTML=`
    <p class="tracker-order-no">Order #${esc(order.order_number)}</p>
    <p class="tracker-meta">${order.fulfilment==='pickup'?`Pickup from ${esc(order.store.name)}`:`Delivering from ${esc(order.store.name)}`}</p>
    ${bakingHtml}
    <div class="tracker-stages">${stagesHtml}</div>
    <div class="tracker-eta">${idx>=TRACKER_STAGES.length-1?'Order complete!':`~${remainingMin} minute${remainingMin===1?'':'s'} remaining`}</div>
    <div class="tracker-items">${esc(itemsSummary)}</div>`;
  syncFlowToOrderStatus(status);
}

async function refreshTracker(order){
  try{
    const r=await api(`/api/order/status?order_number=${encodeURIComponent(order.order_number)}`);
    renderTracker(r.order,r.status);
  }catch(e){
    renderTracker(order,null);
  }
}

function openTracker(){
  closeStub();
  const raw=localStorage.getItem('hp_last_order');
  if(!raw){ openStub('track'); return; }
  let order;
  try{ order=JSON.parse(raw); }catch(e){ openStub('track'); return; }
  $('#trackerBackdrop').hidden=false;
  $('#trackerModal').hidden=false;
  refreshTracker(order);
  clearInterval(TRACKER_TIMER);
  TRACKER_TIMER=setInterval(()=>refreshTracker(order),20000);
}

function closeTracker(){
  $('#trackerBackdrop').hidden=true;
  $('#trackerModal').hidden=true;
  clearInterval(TRACKER_TIMER);
  setActiveNav('home');
}

$('#simpleToggle').onclick = () => { document.documentElement.classList.toggle('simple-mode'); $('#simpleToggle').classList.toggle('active'); };
$('#largeToggle').onclick = () => { document.documentElement.classList.toggle('large-text'); $('#largeToggle').classList.toggle('active'); };

/* ---------------- NAVIGATION (top nav + bottom nav) ---------------- */

const STUB_CONTENT = {
  track: {icon:'📦', title:'No order yet', body:"You haven't placed an order on this device. Place one and you'll be able to track it here."},
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
  else if(target === 'account'){ openAccount(); }
}

$$('.nav-link, .bn-btn, .cart-icon-btn, .brand[data-nav]').forEach(el => {
  el.addEventListener('click', (e) => {
    if(el.tagName === 'A') e.preventDefault();
    handleNav(el.dataset.nav);
  });
});

// Delegated close handling — belt-and-braces so a popup can ALWAYS be
// dismissed (click the ×, click the dark backdrop, or press Escape),
// even if a direct binding is ever missed.
document.addEventListener('click', (e) => {
  if(e.target.closest('#modalCloseBtn') || e.target.id === 'modalBackdrop'){ closeModal(); }
  if(e.target.closest('#stubCloseBtn') || e.target.id === 'stubBackdrop'){ closeStub(); }
  if(e.target.closest('#trackerCloseBtn') || e.target.id === 'trackerBackdrop'){ closeTracker(); }
  if(e.target.closest('#accountCloseBtn') || e.target.id === 'accountBackdrop'){ closeAccount(); }
});
document.addEventListener('keydown', (e) => {
  if(e.key === 'Escape'){ closeModal(); closeStub(); closeTracker(); closeAccount(); }
});

(async function init(){ await loadMenu(); await loadStores(); await loadDeals(); await refreshCartFromServer(); })();

/* ---------------- PIZZOMANIA AI — PHASE 1 ---------------- */
let AI_HISTORY = [];
let AI_LAST_SUGGESTIONS = [];

function aiFormat(text=''){
  const safe=esc(text);
  return safe.replace(/\*\*(.*?)\*\*/g,'<strong>$1</strong>').replace(/\n/g,'<br>');
}
function aiAddMessage(role,text){
  const chat=$('#aiChat'); if(!chat) return;
  const row=document.createElement('div'); row.className=`ai-msg ${role}`;
  row.innerHTML=`<div class="ai-bubble">${aiFormat(text)}</div>`;
  chat.appendChild(row); chat.scrollTop=chat.scrollHeight;
}
function aiSetActivity(trace=[]){
  const el=$('#aiActivity'); if(!el) return;
  if(!trace.length){ el.hidden=true; el.innerHTML=''; return; }
  el.hidden=false;
  el.innerHTML=trace.slice(-4).map(t=>`<span>${esc(t.label||'Checking…')}</span>`).join('');
}
function aiRenderSuggestions(suggestions=[]){
  AI_LAST_SUGGESTIONS=suggestions||[];
  const chat=$('#aiChat'); if(!chat || !AI_LAST_SUGGESTIONS.length) return;
  const wrap=document.createElement('div'); wrap.className='ai-result-list';
  wrap.innerHTML=AI_LAST_SUGGESTIONS.slice(0,3).map((p,i)=>`
    <div class="ai-result">
      <div class="ai-result-main">
        <img class="ai-result-img" src="${esc(p.image||'')}" alt="${esc(p.name)}" onerror="this.style.visibility='hidden'">
        <div>
          <h3>${esc(p.name)}</h3>
          <p>${esc(p.size)} · ${esc(p.crust)}${p.toppings?.length?` · ${p.toppings.map(esc).join(', ')}`:''}</p>
          <div class="ai-price">$${Number(p.unit_price).toFixed(2)} · ${p.calories} cal</div>
        </div>
      </div>
      <div class="ai-result-actions">
        <button data-ai-customize="${i}">Customize</button>
        <button class="ai-add" data-ai-add="${i}">Add to cart</button>
      </div>
    </div>`).join('');
  chat.appendChild(wrap);
  wrap.querySelectorAll('[data-ai-customize]').forEach(btn=>btn.onclick=()=>{
    const p=AI_LAST_SUGGESTIONS[Number(btn.dataset.aiCustomize)];
    if(p) { closeAI(); openCustomizeModal(p.id); }
  });
  wrap.querySelectorAll('[data-ai-add]').forEach(btn=>btn.onclick=async()=>{
    const p=AI_LAST_SUGGESTIONS[Number(btn.dataset.aiAdd)]; if(!p) return;
    try{
      const r=await api('/api/cart/add',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pizza_id:p.id,size:p.size,crust:p.crust,toppings:p.toppings||[],qty:p.qty||1})});
      CART=r.cart; SUBTOTAL=r.subtotal; renderCart(); bumpCart(); setAgentFlow('order', `Customer approved ${p.name} — the validated pizza is now in the cart.`); toast(`${p.name} added to cart.`);
      aiAddMessage('assistant',`Done — **${p.name}** is in your cart. You can keep shopping or head to checkout.`);
    }catch(e){ toast(e.message); }
  });
  chat.scrollTop=chat.scrollHeight;
}
function aiReset(){
  AI_HISTORY=[]; AI_LAST_SUGGESTIONS=[];
  $('#aiChat').innerHTML='';
  $('#aiActivity').hidden=true; $('#aiActivity').innerHTML='';
  aiAddMessage('assistant','👋 Hey! I\'m your pizza co-pilot. Tell me what you\'re craving — for example, “spicy and cheesy under $18” or “vegetarian for the family.”');
}
function openAI(prefill=''){
  setAgentFlow('agent', 'Pizzomania AI is listening and ready to build a pizza.');
  $('#aiBackdrop').hidden=false; $('#aiModal').hidden=false;
  if(!$('#aiChat').children.length) aiReset();
  if(prefill){ $('#aiInput').value=prefill; sendAIMessage(); }
  setTimeout(()=>$('#aiInput').focus(),50);
}
function closeAI(){ $('#aiBackdrop').hidden=true; $('#aiModal').hidden=true; }
async function sendAIMessage(){
  const input=$('#aiInput'); const message=(input.value||'').trim();
  if(!message) return;
  input.value=''; $('#aiSendBtn').disabled=true;
  aiAddMessage('user',message);
  AI_HISTORY.push({role:'user',content:message});
  aiSetActivity([{label:'Understanding your craving'}]);
  try{
    const r=await api('/api/agent/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
      message,
      history:AI_HISTORY.slice(-8),
      context:{page:'build-pizza',cart:CART.map(x=>({pizza_id:x.pizza_id,name:x.name,qty:x.qty})),fulfilment:FULFILMENT}
    })});
    aiSetActivity(r.trace||[]);
    aiAddMessage('assistant',r.reply||'I can help you build a pizza.');
    AI_HISTORY.push({role:'assistant',content:r.reply||''});
    if(r.suggestions?.length) aiRenderSuggestions(r.suggestions);
  }catch(e){ aiAddMessage('assistant',`I couldn't reach the pizza builder right now. ${e.message}`); }
  finally{ $('#aiSendBtn').disabled=false; input.focus(); }
}

$('#aiOpenBtn')?.addEventListener('click',()=>openAI());
$('#aiFloatingBtn')?.addEventListener('click',()=>openAI());
$('#aiCloseBtn')?.addEventListener('click',closeAI);
$('#aiBackdrop')?.addEventListener('click',closeAI);
$('#aiSendBtn')?.addEventListener('click',sendAIMessage);
$('#aiInput')?.addEventListener('keydown',e=>{if(e.key==='Enter') sendAIMessage();});
$$('[data-ai-prompt]').forEach(btn=>btn.addEventListener('click',()=>openAI(btn.dataset.aiPrompt)));
document.addEventListener('keydown',e=>{if(e.key==='Escape') closeAI();});
