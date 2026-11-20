// GTM tools site: loads data.json, then drives the filters, the three charts and the table.
// No build step. Tabulator and Chart.js come from CDNs (see index.html).
'use strict';

const FLAGS = ['Yes', 'No', 'Unknown'];
const EMPTY = { q: '', main: '', tags: [], freemium: '', trial: '', review: false };

let tools = [];
let state = { ...EMPTY, tags: [] };
let table, charts = {};
let categoryOrder = [];   // fixed bar order (by total count), so bars never jump around when filtering
let tagOrder = [];        // tag picker order (by total count)
const openRows = new Set();

const $ = (id) => document.getElementById(id);
const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

function el(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  Object.assign(node, props);
  for (const c of [].concat(children)) if (c != null) node.append(c);
  return node;
}

function safeUrl(url) {
  return /^https?:\/\//i.test(url || '') ? url : '';
}

function link(url, text, cls) {
  const href = safeUrl(url);
  if (!href) return null;
  return el('a', { href, textContent: text, target: '_blank', rel: 'noopener noreferrer', className: cls || '' });
}

function countBy(list, key) {
  const m = new Map();
  for (const t of list) {
    for (const v of [].concat(t[key])) m.set(v, (m.get(v) || 0) + 1);
  }
  return m;
}

// ---------- filtering ----------

// `skip` leaves one filter out: each chart counts the tools that match every *other* filter,
// so it still shows the alternatives to the value you picked.
function matches(t, s, skip) {
  if (s.q) {
    for (const word of s.q.toLowerCase().split(/\s+/)) if (word && !t._search.includes(word)) return false;
  }
  if (skip !== 'main' && s.main && t.main !== s.main) return false;
  if (skip !== 'tags' && s.tags.length && !s.tags.some((tag) => t.tags.includes(tag))) return false;
  if (skip !== 'freemium' && s.freemium && t.freemium !== s.freemium) return false;
  if (skip !== 'trial' && s.trial && t.trial !== s.trial) return false;
  if (s.review && !t.review) return false;
  return true;
}

function setState(patch) {
  state = { ...state, ...patch };
  render();
}

// ---------- URL hash (shareable filtered views) ----------

function writeHash() {
  const p = new URLSearchParams();
  if (state.q) p.set('q', state.q);
  if (state.main) p.set('main', state.main);
  if (state.tags.length) p.set('tags', state.tags.join('|'));
  if (state.freemium) p.set('freemium', state.freemium);
  if (state.trial) p.set('trial', state.trial);
  if (state.review) p.set('review', '1');
  const hash = p.toString();
  const url = location.pathname + location.search + (hash ? '#' + hash : '');
  if (url !== location.pathname + location.search + location.hash) history.replaceState(null, '', url);
}

function readHash() {
  const p = new URLSearchParams(location.hash.slice(1));
  const oneOf = (v, list) => (list.includes(v) ? v : '');
  return {
    q: p.get('q') || '',
    main: oneOf(p.get('main') || '', categoryOrder),
    tags: (p.get('tags') || '').split('|').filter((t) => tagOrder.includes(t)),
    freemium: oneOf(p.get('freemium') || '', FLAGS),
    trial: oneOf(p.get('trial') || '', FLAGS),
    review: p.get('review') === '1',
  };
}

// ---------- controls ----------

function setupControls() {
  const mainSelect = $('main');
  for (const c of [...categoryOrder].sort()) mainSelect.append(el('option', { value: c, textContent: c }));

  let typing;
  $('q').addEventListener('input', (e) => {
    clearTimeout(typing);
    typing = setTimeout(() => setState({ q: e.target.value.trim() }), 120);
  });
  mainSelect.addEventListener('change', (e) => setState({ main: e.target.value }));
  $('freemium').addEventListener('change', (e) => setState({ freemium: e.target.value }));
  $('trial').addEventListener('change', (e) => setState({ trial: e.target.value }));
  $('review').addEventListener('change', (e) => setState({ review: e.target.checked }));
  $('reset').addEventListener('click', () => { openRows.clear(); setState({ ...EMPTY, tags: [] }); });

  // Tag picker: a dropdown panel with a search box and checkboxes.
  const button = $('tag-button'), panel = $('tag-panel');
  const toggle = (open) => {
    panel.hidden = !open;
    button.setAttribute('aria-expanded', String(open));
    if (open) { $('tag-search').value = ''; renderTagList(); $('tag-search').focus(); }
  };
  button.addEventListener('click', () => toggle(panel.hidden));
  document.addEventListener('click', (e) => { if (!$('tag-picker').contains(e.target)) toggle(false); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !panel.hidden) { toggle(false); button.focus(); } });
  $('tag-search').addEventListener('input', renderTagList);
  $('tag-list').addEventListener('change', (e) => {
    const tag = e.target.value;
    const tags = e.target.checked ? [...state.tags, tag] : state.tags.filter((t) => t !== tag);
    setState({ tags });
  });

  window.addEventListener('hashchange', () => { state = readHash(); render(); });
}

function syncControls() {
  const q = $('q');
  if (document.activeElement !== q) q.value = state.q;
  $('main').value = state.main;
  $('freemium').value = state.freemium;
  $('trial').value = state.trial;
  $('review').checked = state.review;
  for (const id of ['main', 'freemium', 'trial']) $(id).classList.toggle('is-active', !!state[id]);
  const button = $('tag-button');
  button.textContent = state.tags.length ? `Tags (${state.tags.length})` : 'Tags';
  button.classList.toggle('is-active', state.tags.length > 0);
}

function renderTagList() {
  const counts = countBy(tools.filter((t) => matches(t, state, 'tags')), 'tags');
  const find = $('tag-search').value.trim().toLowerCase();
  const list = $('tag-list');
  list.replaceChildren(...tagOrder
    .filter((tag) => !find || tag.toLowerCase().includes(find))
    .map((tag) => el('label', {}, [
      el('input', { type: 'checkbox', value: tag, checked: state.tags.includes(tag) }),
      el('span', { textContent: tag }),
      el('span', { className: 'n', textContent: String(counts.get(tag) || 0) }),
    ])));
}

function renderChips() {
  const chips = [];
  const chip = (label, clear) => chips.push(el('span', { className: 'chip' }, [
    label,
    el('button', { type: 'button', textContent: '×', title: 'Remove filter', ariaLabel: `Remove filter ${label}`, onclick: clear }),
  ]));
  if (state.q) chip(`Search: "${state.q}"`, () => setState({ q: '' }));
  if (state.main) chip(`Category: ${state.main}`, () => setState({ main: '' }));
  for (const tag of state.tags) chip(`Tag: ${tag}`, () => setState({ tags: state.tags.filter((t) => t !== tag) }));
  if (state.freemium) chip(`Freemium: ${state.freemium}`, () => setState({ freemium: '' }));
  if (state.trial) chip(`Trial: ${state.trial}`, () => setState({ trial: '' }));
  if (state.review) chip('Needs manual review', () => setState({ review: false }));
  $('chips').replaceChildren(...chips);
}

// ---------- charts ----------

// Draws the count just past the end of each bar (Chart.js has no built-in data labels).
const valueLabels = {
  id: 'valueLabels',
  afterDatasetsDraw(chart) {
    const { ctx } = chart;
    const data = chart.data.datasets[0].data;
    ctx.save();
    ctx.font = '12px system-ui, -apple-system, "Segoe UI", Roboto, sans-serif';
    ctx.fillStyle = css('--text-2');
    ctx.textBaseline = 'middle';
    chart.getDatasetMeta(0).data.forEach((bar, i) => {
      ctx.fillText(String(data[i]), bar.x + 6, bar.y);
    });
    ctx.restore();
  },
};

function barChart(canvas, labels, onPick) {
  return new Chart(canvas, {
    type: 'bar',
    data: { labels, datasets: [{ data: labels.map(() => 0), borderRadius: 4, borderSkipped: 'start', maxBarThickness: 18, categoryPercentage: 0.8, barPercentage: 0.9 }] },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      animation: false,               // instant redraw on every filter change
      layout: { padding: { right: 28 } },
      plugins: {
        legend: { display: false },
        tooltip: {
          displayColors: false,
          callbacks: { label: (c) => `${c.raw} ${c.raw === 1 ? 'tool' : 'tools'} · click to filter` },
        },
      },
      scales: {
        x: { beginAtZero: true, ticks: { precision: 0 }, border: { display: false } },
        y: { grid: { display: false }, ticks: { autoSkip: false }, border: { display: false } },
      },
      onClick: (evt, elements) => { if (elements.length) onPick(labels[elements[0].index]); },
      onHover: (evt, elements) => { evt.native.target.style.cursor = elements.length ? 'pointer' : 'default'; },
    },
    plugins: [valueLabels],
  });
}

function setupCharts() {
  $('main-box').style.height = `${categoryOrder.length * 24 + 40}px`;
  charts.main = barChart($('chart-main'), categoryOrder, (v) => setState({ main: state.main === v ? '' : v }));
  charts.freemium = barChart($('chart-freemium'), FLAGS, (v) => setState({ freemium: state.freemium === v ? '' : v }));
  charts.trial = barChart($('chart-trial'), FLAGS, (v) => setState({ trial: state.trial === v ? '' : v }));
  applyChartTheme();
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => { applyChartTheme(); renderCharts(); });
}

function applyChartTheme() {
  Chart.defaults.color = css('--text-2');
  Chart.defaults.font.family = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif';
  for (const chart of Object.values(charts)) {
    chart.options.scales.x.grid.color = css('--grid');
    chart.options.scales.x.ticks.color = css('--text-3');
    chart.options.scales.y.ticks.color = css('--text-2');
  }
}

// One hue for the bars; "Unknown" is neutral gray. When a value is picked, the other bars fade.
function colors(labels, selected) {
  const accent = css('--accent'), soft = css('--accent-soft'), neutral = css('--neutral'), page = css('--surface-2');
  return labels.map((label) => {
    const base = label === 'Unknown' ? neutral : accent;
    if (!selected || label === selected) return base;
    return label === 'Unknown' ? page : soft;
  });
}

function renderCharts() {
  const update = (chart, dim, labels) => {
    const counts = countBy(tools.filter((t) => matches(t, state, dim)), dim);
    const ds = chart.data.datasets[0];
    ds.data = labels.map((l) => counts.get(l) || 0);
    ds.backgroundColor = colors(labels, state[dim]);
    ds.hoverBackgroundColor = ds.backgroundColor;
    chart.update();
  };
  update(charts.main, 'main', categoryOrder);
  update(charts.freemium, 'freemium', FLAGS);
  update(charts.trial, 'trial', FLAGS);
}

// ---------- table ----------

function nameCell(cell) {
  const t = cell.getData();
  const wrap = el('span');
  const a = link(t.company_url, t.name, 'tool-name');
  wrap.append(a || el('span', { className: 'tool-name', textContent: t.name }));
  if (t.review) wrap.append(el('span', { className: 'flag', textContent: '⚑', title: `Manual review: ${t.review}` }));
  return wrap;
}

function tagsCell(cell) {
  const t = cell.getData();
  return el('div', { className: 'tags' }, t.tags.slice(1).map((tag) => el('span', { className: 'tag', textContent: tag })));
}

const pill = (cell) => el('span', { className: `pill ${cell.getValue()}`, textContent: cell.getValue() });

function details(t) {
  const rows = [
    ['Said in the chat', t.chat_category || '—'],
    ['Website', link(t.company_url, t.company_url) || '—'],
    ['Product page', link(t.product_url, t.product_url) || '—'],
    ['Pricing page', link(t.pricing_url, t.pricing_url) || '—'],
    ['All tags', t.tags.join(', ')],
  ];
  if (t.review) rows.push(['Manual review', t.review]);
  return el('dl', { className: 'details' }, rows.flatMap(([k, v]) => [el('dt', { textContent: k }), el('dd', {}, v)]));
}

function setupTable() {
  table = new Tabulator('#table', {
    data: tools,
    index: 'id',
    layout: 'fitColumns',
    renderVertical: 'basic',     // 300 rows: no virtual DOM needed, and rows can grow when opened
    responsiveLayout: 'hide',
    placeholder: 'No tools match these filters',
    initialSort: [{ column: 'name', dir: 'asc' }],
    columns: [
      { title: 'Tool', field: 'name', formatter: nameCell, minWidth: 160, widthGrow: 2, responsive: 0, sorter: 'string' },
      { title: 'Main category', field: 'main', minWidth: 150, widthGrow: 2, responsive: 1 },
      { title: 'Tags', field: 'tags', formatter: tagsCell, headerSort: false, minWidth: 200, widthGrow: 4, responsive: 3 },
      { title: 'Freemium', field: 'freemium', formatter: pill, width: 110, hozAlign: 'center', headerHozAlign: 'center', responsive: 2 },
      { title: 'Trial', field: 'trial', formatter: pill, width: 110, hozAlign: 'center', headerHozAlign: 'center', responsive: 2 },
      {
        title: 'Pricing', field: 'pricing_url', headerSort: false, width: 90, responsive: 4,
        formatter: (cell) => link(cell.getValue(), 'Pricing ↗') || '',
      },
    ],
    rowFormatter: (row) => {
      const node = row.getElement();
      node.querySelector(':scope > .details')?.remove();
      if (openRows.has(row.getData().id)) node.append(details(row.getData()));
    },
  });
  table.on('rowClick', (e, row) => {
    if (e.target.closest('a, .details')) return;
    const id = row.getData().id;
    openRows.has(id) ? openRows.delete(id) : openRows.add(id);
    row.reformat();
  });
  return new Promise((resolve) => table.on('tableBuilt', resolve));
}

// ---------- render ----------

function render() {
  writeHash();
  syncControls();
  renderChips();
  if (!$('tag-panel').hidden) renderTagList();
  renderCharts();
  table.setFilter((data) => matches(data, state));
  const n = tools.filter((t) => matches(t, state)).length;
  $('count').textContent = n === tools.length ? `${n} tools` : `${n} of ${tools.length} tools`;
}

async function main() {
  let data;
  try {
    const res = await fetch('data.json', { cache: 'no-cache' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    data = await res.json();
  } catch (err) {
    $('count').textContent = `Could not load data.json (${err.message}). Run python3 -I scripts/build_site.py first.`;
    return;
  }
  tools = data.tools.map((t) => ({ ...t, _search: [t.name, t.main, t.chat_category, ...t.tags].join(' ').toLowerCase() }));
  $('built').textContent = `${data.count} tools · data built ${data.built_at}`;

  const byCount = (m) => [...m.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).map(([k]) => k);
  categoryOrder = byCount(countBy(tools, 'main'));
  tagOrder = byCount(countBy(tools, 'tags'));

  setupControls();
  setupCharts();
  await setupTable();
  state = readHash();
  render();
}

main();
