/* ROM-Sync UI. Vanilla JS; all data via /api. */
'use strict';

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => Array.from(el.querySelectorAll(s));
const api = {
  get: async (p) => { const r = await fetch('/api/' + p); const j = await r.json(); if (j && j.error) throw new Error(j.error); return j; },
  post: async (p, body) => { const r = await fetch('/api/' + p, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}) }); const j = await r.json(); if (j && j.error) throw new Error(j.error); return j; },
};
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const fmtB = (n) => { if (n == null) return '?'; if (n < 0) return '-' + fmtB(-n); const u = ['B', 'KB', 'MB', 'GB', 'TB']; let i = 0; while (n >= 1024 && i < 4) { n /= 1024; i++; } return (i ? n.toFixed(n < 10 ? 2 : 1) : n) + ' ' + u[i]; };
const parseSize = (s) => { const m = String(s).trim().toLowerCase().match(/^([\d.]+)\s*(b|kb|mb|gb|tb|k|m|g|t)?$/); if (!m) return null; const mult = { b: 1, k: 1024, kb: 1024, m: 1048576, mb: 1048576, g: 1073741824, gb: 1073741824, t: 2 ** 40, tb: 2 ** 40 }[m[2] || 'b']; return Math.round(parseFloat(m[1]) * mult); };
const toast = (msg, bad) => { const t = $('#toast'); t.textContent = msg; t.className = bad ? 'bad' : ''; clearTimeout(t._h); t._h = setTimeout(() => t.classList.add('hidden'), bad ? 6000 : 2500); };
const modal = (html) => { $('#modal-box').innerHTML = html; $('#modal').classList.remove('hidden'); };
const closeModal = () => $('#modal').classList.add('hidden');
$('#modal').addEventListener('click', e => { if (e.target.id === 'modal') closeModal(); });

// ------------------------------------------------------------ state
const S = {
  lib: null, games: [], systems: {}, view: 'library',
  q: '', sort: 'title', grid: true,
  f: { system: new Set(), genre: new Set(), tag: new Set(), decade: new Set(), region: new Set(),
       franchise: new Set(), theme: new Set(), mode: new Set(), perspective: new Set(),
       sizeMin: null, sizeMax: null, yearMin: null, yearMax: null, rating: 0,
       matched: false, selected: false, ondevice: false, folder: false },
  device: null, devView: null,        // selected device id and its /profile view
  current: null, filtered: [],
  sizeLog: { min: Math.log(1024), max: Math.log(64 * 2 ** 30) },
};

// ------------------------------------------------------------ derived per game
function prep(g) {
  g.sysLabel = S.systems[g.system] || g.system;
  g.decade = g.year ? Math.floor(g.year / 10) * 10 + 's' : null;
  g.regions = (g.region || '').split(',').map(x => x.trim()).filter(Boolean);
  g.tagNames = g.tags.map(t => t.tag);
  g.kinds = { franchise: [], theme: [], mode: [], perspective: [], other: [] };
  for (const t of g.tags) (g.kinds[t.kind] || g.kinds.other).push(t.tag);
  g.otherTags = g.kinds.other;
  g.hay = [g.title, g.name, g.igdb, g.sysLabel, g.system, ...g.genres, ...g.tagNames, ...g.regions].filter(Boolean).join(' | ').toLowerCase();
  g.sortTitle = (g.title || g.name).toLowerCase().replace(/^(the|a|an)\s+/, '');
  // plain-comparable key: accents stripped, digit runs zero-padded so "2" sorts before "10" without ICU collation
  g.sortKey = g.sortTitle.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/\d+/g, d => d.padStart(8, '0'));
  g.sysKey = g.sysLabel.toLowerCase();
}

// ------------------------------------------------------------ cross-system twins
// "The same game, on another system." The key is IGDB's canonical name (games.igdb_name), not igdb_id
// and not the file title. Measured on this catalogue 2026-09-17: igdb_id links 39% of the cross-system
// pairs a human would call duplicates, because IGDB issues a separate id per platform release; the
// canonical name links 95%. The file title is the fallback for unscraped games (ps2 is 0% scraped).
//
// Trailing release-form markers are then stripped, which is what makes "Majora's Mask 3D" meet
// "Majora's Mask" and "Donkey Kong Country Returns 3D" meet the Wii original. That strip is a guess,
// not a fact: "Earthworm Jim 3D" is a different game from "Earthworm Jim". So a pair that only meets
// after the strip is carried as LOOSE and the card says so. Nothing is ever resolved automatically;
// two different games can share a name outright (Punch-Out!! arcade, NES and Wii are three games).
const TWIN_ROMAN = { ii: '2', iii: '3', iv: '4', v: '5', vi: '6', vii: '7', viii: '8', ix: '9', x: '10' };
const TWIN_STOP = new Set(['the', 'a', 'an', 'part']);
const TWIN_FORM = new Set(['3d', 'hd', 'dx', 'deluxe', 'remaster', 'remastered', 'remake',
                           'definitive', 'anniversary', 'edition']);
const TWIN_LEET = { '!': 'i', '@': 'a', '$': 's', '^': '' };
function twinWords(g) {
  let base = (g.igdb || g.title || g.name || '').toLowerCase().replace(/&/g, 'and').replace(/'/g, '');
  base = base.split('').map(ch => (ch in TWIN_LEET ? TWIN_LEET[ch] : ch)).join('');
  return base.replace(/[^a-z0-9]+/g, ' ').trim().split(' ')
    .filter(w => w && !TWIN_STOP.has(w)).map(w => TWIN_ROMAN[w] || w);
}
function twinKey(g) { return twinWords(g).join(''); }
function twinKeyLoose(g) {
  const w = twinWords(g);
  while (w.length > 1 && TWIN_FORM.has(w[w.length - 1])) w.pop();
  return w.join('');
}
function buildTwins() {
  const exact = new Map(), loose = new Map();
  for (const g of S.games) {
    for (const [map, k] of [[exact, twinKey(g)], [loose, twinKeyLoose(g)]]) {
      if (!k) continue;
      if (!map.has(k)) map.set(k, []);
      map.get(k).push(g);
    }
  }
  const exactOf = new Map();
  for (const group of exact.values()) for (const g of group) exactOf.set(g.id, group);
  S.twins = new Map();
  for (const group of loose.values()) {
    if (group.length < 2) continue;
    for (const g of group) {
      const mine = new Set((exactOf.get(g.id) || []).map(x => x.id));
      const others = group.filter(o => o.id !== g.id && o.system !== g.system)
        .map(o => ({ g: o, loose: !mine.has(o.id) }));
      if (others.length) S.twins.set(g.id, others);
    }
  }
}
function twinsOf(g) { return (S.twins && S.twins.get(g.id)) || []; }
function twinBadge(g) {
  const t = twinsOf(g); if (!t.length) return '';
  const dupe = S.devView && isSelected(g) && t.some(x => isSelected(x.g));
  const systems = [...new Set(t.map(x => x.g.system))];
  const tip = (dupe ? 'already selected on ' : 'also in the library on ') + systems.join(', ')
    + (S.current && S.current.id === g.id ? '' : ' - click the tile, then hover, to compare');
  return `<span class="twin ${dupe ? 'dupe' : ''}" title="${esc(tip)}">\u21c4</span>`;
}

// ---- the compare card. It belongs to the selected tile only, so the grid stays quiet while browsing,
// and it fades with the pointer entering and leaving that tile (or the card itself).
const TWIN = { el: null, id: null, t: null };
function twinRow(x, me, host, loose) {
  const cover = x.cover ? `<img src="/covers/${encodeURIComponent(x.cover)}" alt="">` : '<div class="nocov"></div>';
  const marks = [];
  if (S.devView && isSelected(x)) marks.push('<span class="on">selected</span>');
  if (S.devView && onDevice(x)) marks.push('<span class="on">on device</span>');
  if (loose) marks.push('<span class="loose">loose match</span>');
  let act = '<span class="muted">this one</span>';
  if (!me) {
    if (!S.devView) act = '';
    else if (isSelected(x)) act = '<span class="muted">kept</span>';
    else if (isSelected(host)) act = `<button data-switch="${x.id}" data-from="${host.id}" title="deselect the ${esc(host.sysLabel)} copy and select this one instead">Switch</button>`;
    else act = `<button data-add="${x.id}" title="select this version as well">Select</button>`;
  }
  return `<div class="tw-row ${me ? 'me' : ''}" data-twinid="${x.id}">${cover}`
    + `<div class="tw-meta"><div class="t" title="${esc(x.name)}">${esc(x.title || x.name)}</div>`
    + `<div class="s">${esc(x.sysLabel)} &middot; ${x.year || '\u2014'} &middot; ${fmtB(x.size)}</div>`
    + `<div class="s">${marks.join(' ')}</div></div><div class="tw-act">${act}</div></div>`;
}
function twinCardHtml(g) {
  const list = twinsOf(g).slice().sort((a, b) => (a.g.sysLabel || '').localeCompare(b.g.sysLabel || ''));
  const key = g.igdb
    ? `<div class="tw-key">matched on IGDB's name: \u201c${esc(g.igdb)}\u201d</div>`
    : '<div class="tw-key warn">no IGDB match - matched on the file name, so check these really are the same game</div>';
  return `<div class="tw-head">Same game on ${list.length} other system${list.length > 1 ? 's' : ''}</div>${key}`
    + twinRow(g, true, g, false) + list.map(x => twinRow(x.g, false, g, x.loose)).join('');
}
function hideTwinCard(now) {
  clearTimeout(TWIN.t);
  const el = TWIN.el;
  if (!el) return;
  TWIN.el = null; TWIN.id = null;
  el.classList.remove('show');
  if (now) el.remove(); else setTimeout(() => el.remove(), 220);
}
function showTwinCard(tile, g) {
  if (TWIN.id === g.id) { clearTimeout(TWIN.t); return; }
  hideTwinCard(true);
  const el = document.createElement('div');
  el.className = 'twinpop';
  el.innerHTML = twinCardHtml(g);
  document.body.appendChild(el);
  const r = tile.getBoundingClientRect(), w = el.offsetWidth, h = el.offsetHeight;
  let left = r.right + 10; if (left + w > innerWidth - 8) left = Math.max(8, r.left - w - 10);
  let top = r.top - 4; if (top + h > innerHeight - 8) top = Math.max(8, innerHeight - h - 8);
  el.style.left = left + 'px'; el.style.top = top + 'px';
  el.onmouseenter = () => clearTimeout(TWIN.t);
  el.onmouseleave = () => { TWIN.t = setTimeout(hideTwinCard, 120); };
  el.onclick = async (e) => {
    const sw = e.target.closest('[data-switch]');
    const add = e.target.closest('[data-add]');
    try {
      if (sw) { hideTwinCard(); await switchTo(+sw.dataset.from, +sw.dataset.switch); return; }
      if (add) {
        const x = S.games.find(y => y.id === +add.dataset.add);
        hideTwinCard(); await setSelected(x, true); applyFilters(); renderSelSummary();
        toast(`Selected the ${x.sysLabel} version`); return;
      }
      const row = e.target.closest('.tw-row[data-twinid]');
      if (row) { const x = S.games.find(y => y.id === +row.dataset.twinid); hideTwinCard(); if (x) openDetail(x); }
    } catch (err) { toast(err.message, true); }
  };
  requestAnimationFrame(() => el.classList.add('show'));
  TWIN.el = el; TWIN.id = g.id;
}
// Set an explicit selection state, honouring the system's default so an override is only stored when it
// differs from that default (same rule as toggleSelect). Never starts managing a system just to exclude.
async function setSelected(g, want) {
  if (!S.device) { toast('Pick a device in the top-right first'); return; }
  const mode = S.devView.modes[g.system];
  let include = want;
  if (mode == null) {
    if (!want) return;
    await api.post(`profile/${S.device}/select-system`, { system: g.system, mode: 'none' });
    S.devView.modes[g.system] = 'none';
    include = true;
  } else {
    if (mode === 'all' && want) include = null;
    if (mode === 'none' && !want) include = null;
  }
  await api.post(`profile/${S.device}/select-game`, { game_id: g.id, include });
  if (include == null) delete S.devView.overrides[String(g.id)]; else S.devView.overrides[String(g.id)] = include;
}
// Move the selection onto one version: every other version of the same game is deselected, so the
// dropdown in the detail panel can only ever leave one selected.
async function switchTo(fromId, toId) {
  const to = S.games.find(x => x.id === toId); if (!to) return;
  const family = [S.games.find(x => x.id === fromId), ...twinsOf(to).map(x => x.g), to].filter(Boolean);
  for (const x of family) if (x.id !== toId && isSelected(x)) await setSelected(x, false);
  await setSelected(to, true);
  applyFilters(); renderSelSummary();
  toast(`Switched to ${to.sysLabel}: ${to.title || to.name}`);
}

// ------------------------------------------------------------ search parsing
const OPS = /^(year|size|rating|votes|system|genre|region|tag|files|franchise|theme|mode|perspective)\s*(>=|<=|>|<|:|=)\s*(.+)$/i;
function parseQuery(q) {
  const terms = [], clauses = [];
  const re = /"([^"]+)"|(\S+)/g; let m;
  while ((m = re.exec(q))) {
    const tok = m[1] || m[2];
    const o = tok.match(OPS);
    if (o) {
      const [, k, op, vRaw] = o; const key = k.toLowerCase(); const v = vRaw.toLowerCase().replace(/^"|"$/g, '');
      if (['year', 'rating', 'votes', 'files'].includes(key)) clauses.push({ key, op: op === ':' || op === '=' ? '=' : op, v: parseFloat(v) });
      else if (key === 'size') clauses.push({ key, op: op === ':' || op === '=' ? '≈' : op, v: parseSize(v) });
      else clauses.push({ key, op: '~', v });
    } else terms.push(tok.toLowerCase());
  }
  return { terms, clauses };
}
function num(g, key) { return key === 'files' ? (g.files || 1) : g[key]; }
function matchClause(g, c) {
  if (c.op === '~') {
    const pool = { system: [g.system, g.sysLabel], genre: g.genres, region: g.regions, tag: g.tagNames, franchise: g.kinds.franchise, theme: g.kinds.theme, mode: g.kinds.mode, perspective: g.kinds.perspective }[c.key] || [];
    return pool.some(x => String(x).toLowerCase().includes(c.v));
  }
  const x = num(g, c.key); if (x == null || c.v == null || Number.isNaN(c.v)) return false;
  switch (c.op) { case '>': return x > c.v; case '<': return x < c.v; case '>=': return x >= c.v; case '<=': return x <= c.v; case '=': return x === c.v; case '≈': return Math.abs(x - c.v) <= c.v * 0.05; }
  return false;
}

// ------------------------------------------------------------ filtering
const FACETS = ['system', 'genre', 'tag', 'franchise', 'theme', 'mode', 'perspective', 'decade', 'region'];
// Which facet filters a game fails (null = none, or a facet name, or 'many'). One pass serves both the
// result list (fails === null) and every facet's counts (a game counts toward facet F when it fails only F).
function facetFail(g) {
  const f = S.f; let fail = null;
  const mark = (k) => { fail = fail === null ? k : 'many'; };
  if (f.system.size && !f.system.has(g.system)) mark('system');
  if (f.genre.size && !g.genres.some(x => f.genre.has(x))) mark('genre');
  if (f.tag.size && !g.otherTags.some(x => f.tag.has(x))) mark('tag');
  for (const k of ['franchise', 'theme', 'mode', 'perspective']) if (f[k].size && !g.kinds[k].some(x => f[k].has(x))) mark(k);
  if (f.decade.size && !f.decade.has(g.decade)) mark('decade');
  if (f.region.size && !g.regions.some(x => f.region.has(x))) mark('region');
  return fail;
}
function passesRanges(g) {
  const f = S.f;
  if (f.sizeMin != null && g.size < f.sizeMin) return false;
  if (f.sizeMax != null && g.size > f.sizeMax) return false;
  if (f.yearMin != null && (g.year == null || g.year < f.yearMin)) return false;
  if (f.yearMax != null && (g.year == null || g.year > f.yearMax)) return false;
  if (f.rating && (g.rating == null || g.rating < f.rating)) return false;
  if (f.matched && !g.matched) return false;
  if (f.folder && g.kind !== 'folder') return false;
  if (f.selected && !isSelected(g)) return false;
  if (f.ondevice && !onDevice(g)) return false;
  return true;
}
function passes(g, skipFacet) {
  if (!passesRanges(g)) return false;
  const fail = facetFail(g);
  return fail === null || (skipFacet != null && fail === skipFacet);
}
function passesQuery(g, pq) {
  if (!pq.terms.every(t => g.hay.includes(t))) return false;
  return pq.clauses.every(c => matchClause(g, c));
}
function applyFilters() {
  const pq = parseQuery(S.q);
  const base = [];                       // passes the search box and the range/flag filters
  const fails = new Map();               // game id -> facet it fails (null when it passes all)
  S.filtered = [];
  for (const g of sortedGames()) {   // already in sort order, so the filtered list needs no sort
    if (!passesQuery(g, pq) || !passesRanges(g)) continue;
    base.push(g);
    const fail = facetFail(g); fails.set(g.id, fail);
    if (fail === null) S.filtered.push(g);
  }
  renderFacets(base, fails);
  renderGrid();
  renderChips();
  $('#count').textContent = `${S.filtered.length.toLocaleString()} of ${S.games.length.toLocaleString()} · ${fmtB(S.filtered.reduce((a, g) => a + g.size, 0))}`;
  updateShownButton();
}
function updateShownButton() {       // the shown-buttons follow the current filter without re-rendering the summary
  const b = $('#sel-clear-shown'), s = $('#sel-select-shown'); if (!b || !S.devView) return;
  const shownSel = S.filtered.reduce((a, g) => a + (isSelected(g) ? 1 : 0), 0), rest = S.filtered.length - shownSel;
  b.disabled = !shownSel; b.textContent = 'Clear shown' + (shownSel ? ' (' + shownSel.toLocaleString() + ')' : '');
  if (s) { s.disabled = !rest; s.textContent = 'Select shown' + (rest ? ' (' + rest.toLocaleString() + ')' : ''); }
}
const byKey = (a, b) => a.sortKey < b.sortKey ? -1 : a.sortKey > b.sortKey ? 1 : 0;
const CMP = {
  title: byKey,
  year: (a, b) => (b.year || 0) - (a.year || 0) || byKey(a, b),
  rating: (a, b) => (b.rating || 0) - (a.rating || 0) || (b.votes || 0) - (a.votes || 0) || byKey(a, b),
  size: (a, b) => b.size - a.size || byKey(a, b),
  system: (a, b) => (a.sysKey < b.sysKey ? -1 : a.sysKey > b.sysKey ? 1 : 0) || byKey(a, b),
  mtime: (a, b) => (b.mtime || 0) - (a.mtime || 0) || byKey(a, b),
};
S.sortedBy = null; S.sorted = [];
function sortedGames() {              // the whole library in the current order, sorted once per mode
  if (S.sortedBy !== S.sort || S.sorted.length !== S.games.length) { S.sorted = S.games.slice().sort(CMP[S.sort] || CMP.title); S.sortedBy = S.sort; }
  return S.sorted;
}

// ------------------------------------------------------------ facets
// Facet lists show the top FACET_SHOW values; "more…" expands the rest in place (no inner scrollbar),
// "less…" pulls it back; the heading collapses the whole section. Both states are remembered per facet.
const FACET_SHOW = 10;
const FX = { expanded: new Set(), collapsed: new Set() };
try { const j = JSON.parse(localStorage.getItem('romsync.facets') || '{}'); FX.expanded = new Set(j.expanded || []); FX.collapsed = new Set(j.collapsed || []); } catch (e) { /* fresh */ }
function saveFacetState() { try { localStorage.setItem('romsync.facets', JSON.stringify({ expanded: [...FX.expanded], collapsed: [...FX.collapsed] })); } catch (e) { /* not available */ } }
function renderFacets(base, fails) {
  const defs = { system: g => [g.system], genre: g => g.genres, franchise: g => g.kinds.franchise, theme: g => g.kinds.theme, mode: g => g.kinds.mode, perspective: g => g.kinds.perspective, tag: g => g.otherTags, decade: g => g.decade ? [g.decade] : [], region: g => g.regions };
  for (const [facet, fn] of Object.entries(defs)) {
    const counts = new Map();
    for (const g of base) { const fl = fails.get(g.id); if (fl === null || fl === facet) for (const v of fn(g)) counts.set(v, (counts.get(v) || 0) + 1); }
    // keep facet values that are chosen but now zero
    for (const v of S.f[facet]) if (!counts.has(v)) counts.set(v, 0);
    let entries = Array.from(counts.entries());
    if (facet === 'decade') entries.sort((a, b) => a[0].localeCompare(b[0]));
    else entries.sort((a, b) => b[1] - a[1] || String(a[0]).localeCompare(String(b[0])));
    if (['tag', 'genre', 'region', 'franchise', 'theme', 'mode', 'perspective'].includes(facet)) entries = entries.slice(0, 60);
    const box = $(`.facet[data-facet=${facet}]`); const body = $('.facet-body', box);
    const chosen = S.f[facet];
    const expanded = FX.expanded.has(facet);
    // chosen values always show, even when they sit past the fold
    let shown = expanded ? entries : entries.slice(0, FACET_SHOW).concat(entries.slice(FACET_SHOW).filter(([v]) => chosen.has(v)));
    const hidden = entries.length - shown.length;
    body.innerHTML = shown.map(([v, n]) => `<div class="fact ${chosen.has(v) ? 'on' : ''} ${n ? '' : 'zero'}" data-v="${esc(v)}"><span>${esc(facet === 'system' ? (S.systems[v] || v) : v)}</span><span class="n">${n}</span></div>`).join('') || '<div class="muted">—</div>';
    if (hidden > 0) body.innerHTML += `<div class="fact more" data-more="1"><span>more…</span><span class="n">+${hidden}</span></div>`;
    else if (expanded && entries.length > FACET_SHOW) body.innerHTML += `<div class="fact more" data-more="0"><span>less…</span><span class="n"></span></div>`;
    body.onclick = (e) => {
      const m = e.target.closest('.more'); if (m) { m.dataset.more === '1' ? FX.expanded.add(facet) : FX.expanded.delete(facet); saveFacetState(); renderFacets(base, fails); return; }
      const el = e.target.closest('.fact'); if (!el) return; const v = el.dataset.v; const set = S.f[facet]; set.has(v) ? set.delete(v) : set.add(v); applyFilters();
    };
    box.classList.toggle('collapsed', FX.collapsed.has(facet));
    const h = $('h4', box); const badge = $('.sel-n', h); const nSel = chosen.size;
    if (badge) badge.textContent = nSel ? nSel : '';
  }
}
// Section headings collapse and expand their section; the clear button keeps its own job.
$$('#filters .facet h4').forEach(h => {
  const box = h.parentElement; const key = box.dataset.facet || (h.textContent.trim().split(/\s/)[0].toLowerCase());
  box.dataset.key = key;
  h.insertAdjacentHTML('afterbegin', '<i class="chev"></i>');
  if (!$('.sel-n', h)) h.insertAdjacentHTML('beforeend', '<span class="sel-n"></span>');
  if (FX.collapsed.has(key)) box.classList.add('collapsed');
  h.addEventListener('click', (e) => {
    if (e.target.closest('button, input, select')) return;
    box.classList.toggle('collapsed'); box.classList.contains('collapsed') ? FX.collapsed.add(key) : FX.collapsed.delete(key); saveFacetState();
  });
});
function renderChips() {
  const chips = [];
  for (const facet of ['system', 'genre', 'franchise', 'theme', 'mode', 'perspective', 'tag', 'decade', 'region']) for (const v of S.f[facet]) chips.push({ facet, v, label: facet === 'system' ? (S.systems[v] || v) : v });
  const f = S.f;
  if (f.sizeMin != null || f.sizeMax != null) chips.push({ facet: 'size', label: `size ${f.sizeMin != null ? '≥ ' + fmtB(f.sizeMin) : ''} ${f.sizeMax != null ? '≤ ' + fmtB(f.sizeMax) : ''}` });
  if (f.yearMin != null || f.yearMax != null) chips.push({ facet: 'year', label: `year ${f.yearMin ?? ''}–${f.yearMax ?? ''}` });
  if (f.rating) chips.push({ facet: 'rating', label: `rating ≥ ${f.rating}` });
  $('#active-chips').innerHTML = chips.map(c => `<span class="chip" data-facet="${c.facet}" data-v="${esc(c.v ?? '')}">${esc(c.label)} ✕</span>`).join('') + (chips.length ? '<span class="chip" data-facet="*">clear all</span>' : '');
}
$('#active-chips').onclick = (e) => {
  const el = e.target.closest('.chip'); if (!el) return; const f = el.dataset.facet;
  if (f === '*') resetFilters();
  else if (S.f[f] instanceof Set) S.f[f].delete(el.dataset.v);
  else if (f === 'size') { S.f.sizeMin = S.f.sizeMax = null; syncSizeInputs(); }
  else if (f === 'year') { S.f.yearMin = S.f.yearMax = null; syncYearInputs(); }
  else if (f === 'rating') { S.f.rating = 0; $('#rating-min').value = 0; $('#rating-val').textContent = 'any'; }
  applyFilters();
};
$$('.facet h4 .clear').forEach(b => b.onclick = () => { S.f[b.dataset.clear].clear(); applyFilters(); });
function resetFilters() {
  for (const k of Object.keys(S.f)) if (S.f[k] instanceof Set) S.f[k].clear();
  Object.assign(S.f, { sizeMin: null, sizeMax: null, yearMin: null, yearMax: null, rating: 0, matched: false, selected: false, ondevice: false, folder: false });
  ['f-matched', 'f-selected', 'f-ondevice', 'f-folder'].forEach(id => $('#' + id).checked = false);
  $('#rating-min').value = 0; $('#rating-val').textContent = 'any';
  syncSizeInputs(); syncYearInputs();
}

// size slider: log scale between 1 KB and 64 GB
const sliderToBytes = (v) => v <= 0 ? null : v >= 1000 ? null : Math.round(Math.exp(S.sizeLog.min + (S.sizeLog.max - S.sizeLog.min) * v / 1000));
const bytesToSlider = (b) => b == null ? null : Math.round((Math.log(Math.max(1024, b)) - S.sizeLog.min) / (S.sizeLog.max - S.sizeLog.min) * 1000);
function syncSizeInputs() {
  $('#size-lo').value = S.f.sizeMin == null ? 0 : bytesToSlider(S.f.sizeMin); $('#size-hi').value = S.f.sizeMax == null ? 1000 : bytesToSlider(S.f.sizeMax);
  $('#size-min').value = S.f.sizeMin == null ? '' : fmtB(S.f.sizeMin); $('#size-max').value = S.f.sizeMax == null ? '' : fmtB(S.f.sizeMax);
}
function syncYearInputs() {
  $('#year-lo').value = S.f.yearMin ?? 1975; $('#year-hi').value = S.f.yearMax ?? 2026;
  $('#year-min').value = S.f.yearMin ?? ''; $('#year-max').value = S.f.yearMax ?? '';
}
$('#size-lo').oninput = (e) => { let v = +e.target.value; if (v > +$('#size-hi').value - 10) v = +$('#size-hi').value - 10; e.target.value = v; S.f.sizeMin = sliderToBytes(v); $('#size-min').value = S.f.sizeMin == null ? '' : fmtB(S.f.sizeMin); applyFilters(); };
$('#size-hi').oninput = (e) => { let v = +e.target.value; if (v < +$('#size-lo').value + 10) v = +$('#size-lo').value + 10; e.target.value = v; S.f.sizeMax = sliderToBytes(v); $('#size-max').value = S.f.sizeMax == null ? '' : fmtB(S.f.sizeMax); applyFilters(); };
$('#size-min').onchange = (e) => { S.f.sizeMin = e.target.value.trim() ? parseSize(e.target.value) : null; syncSizeInputs(); applyFilters(); };
$('#size-max').onchange = (e) => { S.f.sizeMax = e.target.value.trim() ? parseSize(e.target.value) : null; syncSizeInputs(); applyFilters(); };
$('#year-lo').oninput = (e) => { let v = +e.target.value; if (v > +$('#year-hi').value) v = +$('#year-hi').value; e.target.value = v; S.f.yearMin = v <= 1975 ? null : v; $('#year-min').value = S.f.yearMin ?? ''; applyFilters(); };
$('#year-hi').oninput = (e) => { let v = +e.target.value; if (v < +$('#year-lo').value) v = +$('#year-lo').value; e.target.value = v; S.f.yearMax = v >= 2026 ? null : v; $('#year-max').value = S.f.yearMax ?? ''; applyFilters(); };
$('#year-min').onchange = (e) => { S.f.yearMin = e.target.value ? +e.target.value : null; syncYearInputs(); applyFilters(); };
$('#year-max').onchange = (e) => { S.f.yearMax = e.target.value ? +e.target.value : null; syncYearInputs(); applyFilters(); };
$('#rating-min').oninput = (e) => { S.f.rating = +e.target.value; $('#rating-val').textContent = S.f.rating ? S.f.rating : 'any'; applyFilters(); };
for (const [id, key] of [['f-matched', 'matched'], ['f-selected', 'selected'], ['f-ondevice', 'ondevice'], ['f-folder', 'folder']]) $('#' + id).onchange = (e) => { S.f[key] = e.target.checked; applyFilters(); };
$$('.smart').forEach(b => b.onclick = () => { $('#search').value = b.dataset.q; S.q = b.dataset.q; applyFilters(); });
let qTimer; $('#search').oninput = (e) => { clearTimeout(qTimer); qTimer = setTimeout(() => { S.q = e.target.value; applyFilters(); }, 120); };
$('#sort').onchange = (e) => { S.sort = e.target.value; applyFilters(); };
$('#tile').oninput = (e) => { document.documentElement.style.setProperty('--tile', e.target.value + 'px'); V.rowH = 0; renderWindow(true); };
$('#view-grid').onclick = () => { S.grid = true; $('#view-grid').classList.add('active'); $('#view-list').classList.remove('active'); renderGrid(); };
$('#view-list').onclick = () => { S.grid = false; $('#view-list').classList.add('active'); $('#view-grid').classList.remove('active'); renderGrid(); };

// ------------------------------------------------------------ selection (per device)
function isSelected(g) {
  const v = S.devView; if (!v) return false;
  const o = v.overrides[String(g.id)]; if (o != null) return !!o;
  return v.modes[g.system] === 'all';
}
function isOverride(g) { return S.devView && S.devView.overrides[String(g.id)] != null; }
function onDevice(g) { return S.devView && S.devView.onDeviceSet.has(g.system + '\\' + g.name); }
async function toggleSelect(g) {
  if (!S.device) { toast('Pick a device in the top-right first'); return; }
  const mode = S.devView.modes[g.system];
  const cur = isSelected(g);
  let include = !cur;
  // if the new state equals the system default, drop the override instead
  if (mode === 'all' && include) include = null; if (mode === 'none' && !include) include = null;
  if (mode == null) { // system not managed yet: managing it as "none" with this one game included
    await api.post(`profile/${S.device}/select-system`, { system: g.system, mode: 'none' });
    S.devView.modes[g.system] = 'none';
    include = true;
  }
  await api.post(`profile/${S.device}/select-game`, { game_id: g.id, include });
  if (include == null) delete S.devView.overrides[String(g.id)]; else S.devView.overrides[String(g.id)] = include;
  refreshTile(g); renderSelSummary(); if (S.current && S.current.id === g.id) renderDetail(S.current);
}
function renderSelSummary() {
  const el = $('#sel-summary');
  if (!S.devView) { el.textContent = ''; stopCapacity(); return; }
  let n = 0, b = 0; for (const g of S.games) if (isSelected(g)) { n++; b += g.size; }
  const shownSel = S.filtered.reduce((a, g) => a + (isSelected(g) ? 1 : 0), 0);
  const onDev = S.devView.on_device.filter(r => !r.startsWith('bios\\')).length;
  el.innerHTML = `<b><a href="#" id="go-device" title="open the device page">${esc(S.devView.profile.name)}</a></b>: <span id="sel-count">${n.toLocaleString()} selected, ${fmtB(b)} · <span id="dev-count">${onDev.toLocaleString()} on device</span></span> <span id="sync-ctl"></span> <button id="sel-select-shown" title="select every game in the current filter" ${S.filtered.length > shownSel ? '' : 'disabled'}>Select shown${S.filtered.length > shownSel ? ' (' + (S.filtered.length - shownSel).toLocaleString() + ')' : ''}</button> <button id="sel-clear-shown" title="deselect the games in the current filter" ${shownSel ? '' : 'disabled'}>Clear shown${shownSel ? ' (' + shownSel.toLocaleString() + ')' : ''}</button> <button id="sel-clear-all" title="deselect every game for this device" ${n ? '' : 'disabled'}>Clear all</button>`;
  $('#go-device').onclick = (e) => { e.preventDefault(); showDevice(S.device); };
  $('#sel-clear-shown').onclick = () => clearShown();
  $('#sel-select-shown').onclick = () => selectShown();
  $('#sel-clear-all').onclick = () => clearAll();
  renderSyncCtl();
  clearTimeout(CAP.debounce); CAP.debounce = setTimeout(() => refreshCapacity(false), 250);   // coalesce rapid selection clicks
}

// ------------------------------------------------------------ Sync: one action
// "Sync" makes the device match the selection: send what is missing, replace what changed, remove what is
// no longer selected. Nothing is wiped; anything on the device the store has no copy of is pulled back to
// the PC before it is removed. While it runs the control shows a spinner, % done, ETA and what is moving;
// the on-device count and the capacity meter follow the run live.
const SYNC = { job: null, device: null, t0: 0, samples: [], prev: { bytes: 0, sent: 0, removed: 0, freed: 0 }, curRun: null, timer: null, last: null };
function syncCtlHtml(v, id) {
  if (!v) return '';
  if (SYNC.job && SYNC.device === id) return syncProgressHtml();
  if (!v.connected) return `<button id="sync-go" disabled title="plug the device in to sync">Sync</button>`;
  return `<button id="sync-go" class="primary" title="make the device match the selection">Sync</button>`;
}
function fmtEta(sec) { if (sec == null || !isFinite(sec)) return '…'; if (sec < 60) return Math.max(1, Math.round(sec)) + ' s'; if (sec < 3600) return Math.round(sec / 60) + ' min'; return (sec / 3600).toFixed(1) + ' h'; }
function syncProgressHtml() {
  const p = SYNC.last;
  if (!p) return `<span class="syncing"><i class="spin"></i> starting…</span>`;
  return `<span class="syncing" title="${esc(p.tip)}"><i class="spin"></i><b>${p.pct}%</b> <span class="muted">ETA ${fmtEta(p.eta)} · ${esc(p.phaseText)}</span></span>`;
}
let devPageView = null;                    // the profile view the device page was drawn from
function renderSyncCtl() {
  const el = $('#sync-ctl'); if (el) { el.innerHTML = syncCtlHtml(S.devView, S.device); const b = $('#sync-go', el); if (b) b.onclick = () => startSync(S.device); }
  const dv = $('#dv-sync'); if (dv && devPageView) { dv.innerHTML = syncCtlHtml(devPageView, devPageId); const b = $('#sync-go', dv); if (b) b.onclick = () => startSync(devPageId); }
}
async function startSync(id) {
  if (SYNC.job) { toast('A sync is already running'); return; }
  let p; try { p = await api.get(`profile/${id}/plan`); } catch (e) { toast(e.message, true); return; }
  const n = p.send.length + p.update.length + p.remove.length;
  if (!n) { toast('Nothing to do: the device already matches your selection'); return; }
  if (p.bytes.fits === false) { toast(`Does not fit: the selection needs ${fmtB(p.bytes.net - p.bytes.free)} more than the device has`, true); return; }
  const name = (S.device === id && S.devView) ? S.devView.profile.name : devPageId === id && devPageView ? devPageView.profile.name : 'the device';
  const sz = (l) => fmtB(l.reduce((a, o) => a + o.size, 0));
  const row = (k, l, label) => l.length ? `<tr><td>${label}</td><td class="num">${l.length.toLocaleString()}</td><td class="num">${sz(l)}</td></tr>` : '';
  modal(`<h3>Sync ${esc(name)}</h3>
    <div class="muted">Makes the device's game folders match your selection. Games only; nothing is wiped.</div>
    <table style="margin:12px 0"><tbody>${row('send', p.send, 'Send')}${row('update', p.update, 'Replace')}${row('remove', p.remove, 'Remove from device')}
    <tr><td class="muted">Already in place</td><td class="num muted">${p.unchanged.toLocaleString()}</td><td></td></tr></tbody></table>
    <div class="muted">Net change ${fmtB(p.bytes.net)}${p.bytes.free != null ? ` · ${fmtB(p.bytes.free)} free now, ${fmtB(p.bytes.free - p.bytes.net)} after` : ''}</div>
    <div class="actions"><button id="sync-cancel">Cancel</button><button class="primary" id="sync-start">Start</button></div>`);
  $('#sync-cancel').onclick = closeModal;
  $('#sync-start').onclick = async () => {
    closeModal();
    try {
      const j = await api.post(`profile/${id}/sync`, {});
      let onDev = 0; try { const fresh = await api.get('profile/' + id); onDev = fresh.on_device.filter(r => !r.startsWith('bios\\')).length; } catch (e) { /* count stays approximate */ }
      SYNC.job = j.id; SYNC.device = id; SYNC.t0 = Date.now(); SYNC.tFirst = 0; SYNC.prev = { bytes: 0, sent: 0, removed: 0, freed: 0 }; SYNC.curRun = null; SYNC.last = null;
      SYNC.start = { free: j.free_at_start, capacity: j.capacity, onDevice: onDev, bytesTotal: j.bytes_total, removesTotal: j.plan.remove.n, plan: j.plan };
      renderSyncCtl();
      if (SYNC.timer) clearInterval(SYNC.timer);
      SYNC.timer = setInterval(pollSync, 1000); pollSync();
    } catch (e) { toast(e.message, true); }
  };
}
async function pollSync() {
  if (!SYNC.job) return;
  let j, r = null;
  try { j = await api.get('job/' + SYNC.job); if (j.run) r = await api.get(`run/${j.run}?brief=1`); } catch (e) { return; }
  if (j.run && j.run !== SYNC.curRun) {              // a new run id: bank the finished one
    if (SYNC.curRun && SYNC.curLast) { SYNC.prev.bytes += SYNC.curLast.bytes; SYNC.prev.sent += SYNC.curLast.sent; SYNC.prev.removed += SYNC.curLast.removed; SYNC.prev.freed += SYNC.curLast.freed; }
    SYNC.curRun = j.run; SYNC.curLast = null;
  }
  const st = r ? r.status : {}; const cur = { bytes: (r ? r.bytes_done : 0) + (st.state === 'running' ? (st.cur_bytes || 0) : 0), sent: st.sent || 0, removed: st.removed || 0, freed: r ? r.bytes_removed : 0 };
  SYNC.curLast = cur;
  const bytes = SYNC.prev.bytes + cur.bytes, sent = SYNC.prev.sent + cur.sent, removed = SYNC.prev.removed + cur.removed, freed = SYNC.prev.freed + cur.freed;
  const S0 = SYNC.start; const W = 1 << 20;                         // a removal counts as 1 MB of work
  const work = bytes + removed * W, total = Math.max(1, S0.bytesTotal + S0.removesTotal * W);
  const pct = Math.min(99, Math.floor(work / total * 100));
  const now = Date.now(); if (work > 0 && !SYNC.tFirst) SYNC.tFirst = now;   // rate = average since the first byte moved
  const rate = SYNC.tFirst && now - SYNC.tFirst > 2000 ? work / ((now - SYNC.tFirst) / 1000) : 0;
  const eta = rate > 0 ? (total - work) / rate : null;
  const phaseText = st.phase === 'remove' ? `removing ${esc(st.current || '')}` : st.current ? `sending ${esc(st.current || '')}` : (st.phase || 'starting');
  SYNC.last = { pct, eta, phaseText, tip: `${fmtB(bytes)} of ${fmtB(S0.bytesTotal)} moved · sent ${sent} · removed ${removed} · failed ${st.failed || 0}${rate ? ' · ' + fmtB(rate) + '/s' : ''}` };
  // live counts: what is on the device now, and its free space, from what the run has done so far
  const dc = $('#dev-count'); if (dc) dc.textContent = `${Math.max(0, S0.onDevice + sent - removed).toLocaleString()} on device`;
  if (CAP.last && CAP.last.capacity && S0.free != null) {
    const free = S0.free - bytes + freed;
    renderCapacity({ ...CAP.last, connected: true, live: true, free, on_device: { n: S0.onDevice + sent - removed, bytes: (CAP.last.on_device.bytes || 0) + bytes - freed }, plan: { add: Math.max(0, S0.bytesTotal - bytes), drop: 0, net: Math.max(0, S0.bytesTotal - bytes) } });
  }
  if (j.state === 'running') { renderSyncCtl(); return; }
  clearInterval(SYNC.timer); SYNC.timer = null;
  const res = j.result || {}; SYNC.job = null;
  if (j.state === 'error') toast('Sync failed: ' + (j.error || '').split('\n')[0], true);
  else {
    const bits = [`sent ${res.sent}`, `removed ${res.removed}`]; if (res.failed) bits.push(`${res.failed} failed`);
    toast(`${S.devView ? S.devView.profile.name : 'Device'} synced: ${bits.join(', ')} (${fmtB(res.bytes)})`, !!res.failed);
  }
  if (S.device === SYNC.device) await setDevice(S.device);          // fresh on-device set, selection summary, tiles
  await refreshCapacity(true);
  if (S.view === 'device' && devPageId === SYNC.device) renderDevicePage(SYNC.device);
  renderSyncCtl();
}

async function reloadSelection() {   // re-read the device view after a bulk change, redraw what depends on it
  const v = await api.get('profile/' + S.device); v.onDeviceSet = new Set(v.on_device); S.devView = v;
  applyFilters(); renderSelSummary(); if (S.current) renderDetail(S.current);
}
async function clearShown() {
  const ids = S.filtered.filter(isSelected).map(g => g.id); if (!ids.length) return;
  if (!confirm(`Deselect the ${ids.length.toLocaleString()} selected game${ids.length > 1 ? 's' : ''} in the current view for ${S.devView.profile.name}?\n(Games outside this filter keep their selection.)`)) return;
  try { const r = await api.post(`profile/${S.device}/select-games`, { game_ids: ids, include: false }); await reloadSelection(); toast(`${r.changed.toLocaleString()} deselected`); }
  catch (e) { toast(e.message, true); }
}
async function selectShown() {
  const ids = S.filtered.filter(g => !isSelected(g)).map(g => g.id); if (!ids.length) return;
  const bytes = S.filtered.filter(g => !isSelected(g)).reduce((a, g) => a + g.size, 0);
  if (!confirm(`Select the ${ids.length.toLocaleString()} unselected game${ids.length > 1 ? 's' : ''} in the current view for ${S.devView.profile.name}? (${fmtB(bytes)})`)) return;
  try {
    // games in systems this device does not manage yet are managed as "none" first, so the selection can take
    const unmanaged = [...new Set(S.filtered.filter(g => S.devView.modes[g.system] == null).map(g => g.system))];
    for (const s of unmanaged) await api.post(`profile/${S.device}/select-system`, { system: s, mode: 'none' });
    const r = await api.post(`profile/${S.device}/select-games`, { game_ids: ids, include: true }); await reloadSelection(); toast(`${r.changed.toLocaleString()} selected`);
  } catch (e) { toast(e.message, true); }
}
async function clearAll() {
  let n = 0; for (const g of S.games) if (isSelected(g)) n++;
  if (!n) return;
  if (!confirm(`Clear ALL ${n.toLocaleString()} selected games for ${S.devView.profile.name}?\nSystems stay managed, so the next sync would remove them from the device.`)) return;
  try { await api.post(`profile/${S.device}/select-clear`, {}); await reloadSelection(); toast('selection cleared'); }
  catch (e) { toast(e.message, true); }
}

// ------------------------------------------------------------ destination capacity meter
// Live view of the device: selection total (actual file sizes), what is on it now, and the projected
// fill after the pending sync. green < 80 %, yellow 80-90 %, red >= 90 %, "full" when it would not fit.
const CAP = { timer: null, last: null, device: null, debounce: null };
function stopCapacity() { if (CAP.timer) clearInterval(CAP.timer); CAP.timer = null; CAP.last = null; CAP.device = null; $('#cap-meter').classList.add('hidden'); }
async function refreshCapacity(probe) {
  if (!S.device) { stopCapacity(); return; }
  if (CAP.device !== S.device) { CAP.last = null; CAP.device = S.device; if (CAP.timer) clearInterval(CAP.timer); CAP.timer = setInterval(() => refreshCapacity(true), 30000); }
  let c; try { c = await api.get(`profile/${S.device}/capacity` + (probe ? '?refresh=1' : '')); } catch (e) { return; }
  if (CAP.device !== S.device) return;
  renderCapacity(c);
  if (CAP.last && CAP.last.state !== 'full' && c.state === 'full') toast(`${S.devView.profile.name} is full: the selection needs ${fmtB(c.short_by)} more than the device has`, true);
  else if (CAP.last && CAP.last.state !== 'red' && c.state === 'red' && CAP.last.state !== 'full') toast(`${S.devView.profile.name} is over 90% after this selection`);
  CAP.last = c;
}
function renderCapacity(c) {
  const el = $('#cap-meter'); el.classList.remove('hidden', 'green', 'yellow', 'red', 'full', 'unknown');
  const sel = `<b>${fmtB(c.selected.bytes)}</b> selected`;
  if (c.state === 'unknown' || !c.capacity) {
    el.classList.add('unknown');
    el.innerHTML = `<span class="meter" title="device capacity unknown"><i style="width:0"></i></span><span class="pct">–</span><span class="cnt">${sel} · capacity unknown${c.connected ? '' : ' (not connected)'}</span>`;
    return;
  }
  const pctAfter = Math.min(100, Math.round(c.after.fraction * 100));
  const pctNow = Math.min(100, Math.round((c.capacity - c.free) / c.capacity * 100));
  el.classList.add(c.state);
  const when = c.connected ? 'live' : 'last seen ' + (c.last_seen || '').slice(0, 16).replace('T', ' ');
  const tip = `after sync: ${fmtB(c.after.used)} used of ${fmtB(c.capacity)} (${pctAfter}%), ${fmtB(c.after.free)} free\nnow: ${fmtB(c.capacity - c.free)} used, ${fmtB(c.free)} free (${when})\nselected: ${c.selected.n.toLocaleString()} games, ${fmtB(c.selected.bytes)}\non device: ${c.on_device.n.toLocaleString()} items, ${fmtB(c.on_device.bytes)}\nsync: +${fmtB(c.plan.add)} −${fmtB(c.plan.drop)}`;
  const label = c.live ? `${sel} · <b>${fmtB(c.free)}</b> free now → ${fmtB(c.after.free)} after` : c.state === 'full' ? `${sel} · FULL, short by ${fmtB(c.short_by)}` : `${sel} · ${fmtB(c.after.free)} free after sync`;
  el.innerHTML = `<span class="meter" title="${esc(tip)}"><i class="now" style="width:${pctNow}%"></i><i style="width:${pctAfter}%"></i></span><span class="pct">${pctAfter}%</span><span class="cnt">${label}</span>`;
  el.title = tip;
}

// ------------------------------------------------------------ grid (windowed)
// Only the rows in and around the viewport exist in the DOM. The whole list is 8k+ tiles;
// rendering all of them cost ~1 s per filter click and 60k DOM nodes.
const V = { cols: 1, gap: 14, rowH: 0, first: -1, last: -1, raf: null, mode: null };
function tileHtml(g, dev) {
  const sel = dev ? `<span class="sel ${isSelected(g) ? 'in' : ''} ${isOverride(g) ? 'over' : ''}" data-sel="${g.id}" title="click to include/exclude for this device">${isSelected(g) ? '✓' : ''}</span>` : '';
  const od = dev && onDevice(g) ? '<span class="ondev">on device</span>' : '';
  const cur = S.current && S.current.id === g.id ? 'current' : '';
  if (S.grid) {
    const cover = g.cover ? `<img class="cov" loading="lazy" decoding="async" src="/covers/${encodeURIComponent(g.cover)}" alt="">` : `<div class="nocov">${esc(g.title || g.name)}</div>`;
    return `<div class="tile ${cur}" data-id="${g.id}">${cover}${sel}${od}${twinBadge(g)}<div class="cap"><div class="t" title="${esc(g.name)}">${esc(g.title || g.name)}</div><div class="s"><span>${esc(g.system)}</span><span>${g.year || ''}${g.rating ? ' · ' + g.rating : ''}</span></div></div></div>`;
  }
  return `<div class="lrow ${cur}" data-id="${g.id}">${sel || '<span></span>'}${g.cover ? `<img loading="lazy" decoding="async" src="/covers/${encodeURIComponent(g.cover)}">` : '<span></span>'}<span class="t" title="${esc(g.name)}">${esc(g.title || g.name)}${od}</span><span class="muted">${esc(g.sysLabel)}</span><span class="num">${g.year || ''}</span><span class="num">${g.rating || ''}</span><span class="num muted">${fmtB(g.size)}</span></div>`;
}
function gridCols() {
  const grid = $('#grid');
  if (!S.grid) return 1;
  const cs = getComputedStyle(grid);
  const w = grid.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
  const tile = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--tile')) || 150;
  return Math.max(1, Math.floor((w + V.gap) / (tile + V.gap)));
}
function renderGrid() {            // full reset: layout may have changed (filter, sort, view, tile size, resize)
  const grid = $('#grid'); grid.className = S.grid ? '' : 'list';
  let inner = $('#grid-inner');
  if (!inner) { grid.innerHTML = '<div id="grid-inner"></div>'; inner = $('#grid-inner'); }
  if (V.mode !== S.grid) { V.rowH = 0; V.mode = S.grid; }
  V.first = -1; V.last = -1;
  renderWindow(true);
}
function renderWindow(force) {
  const grid = $('#grid'), inner = $('#grid-inner'); if (!inner) return;
  const cols = gridCols(); if (cols !== V.cols) { V.cols = cols; V.rowH = 0; force = true; }
  const n = S.filtered.length, rows = Math.ceil(n / cols);
  inner.style.gridTemplateColumns = S.grid ? `repeat(${cols}, minmax(0, 1fr))` : '';
  if (!n) { inner.style.height = '0px'; inner.style.paddingTop = '0px'; inner.innerHTML = '<div class="muted" style="grid-column:1/-1">nothing matches</div>'; V.first = V.last = -1; return; }
  if (!V.rowH) {                    // measure one row at the current width, then lay out for real
    inner.style.paddingTop = '0px'; inner.style.height = '';
    inner.innerHTML = S.filtered.slice(0, cols).map(g => tileHtml(g, !!S.devView)).join('');
    const first = inner.firstElementChild; V.rowH = (first ? first.getBoundingClientRect().height : 200) + (S.grid ? V.gap : 0);
    force = true;
  }
  const rowH = V.rowH, top = grid.scrollTop, vh = grid.clientHeight;
  const firstRow = Math.max(0, Math.floor(top / rowH) - 2), lastRow = Math.min(rows, Math.ceil((top + vh) / rowH) + 2);
  if (!force && firstRow === V.first && lastRow === V.last) return;
  V.first = firstRow; V.last = lastRow;
  inner.style.height = (rows * rowH) + 'px'; inner.style.paddingTop = (firstRow * rowH) + 'px';
  const dev = !!S.devView, html = [];
  for (let i = firstRow * cols; i < Math.min(n, lastRow * cols); i++) html.push(tileHtml(S.filtered[i], dev));
  inner.innerHTML = html.join('');
}
$('#grid').onscroll = () => { if (V.raf) return; V.raf = requestAnimationFrame(() => { V.raf = null; renderWindow(false); }); };
new ResizeObserver(() => { if (V.rsz) clearTimeout(V.rsz); V.rsz = setTimeout(() => { V.rowH = 0; renderWindow(true); }, 80); }).observe($('#grid'));
function refreshTile(g) {          // redraw one tile in place (selection toggles) instead of the whole window
  const el = $(`#grid [data-id="${g.id}"]`); if (!el) return;
  const tmp = document.createElement('div'); tmp.innerHTML = tileHtml(g, !!S.devView); el.replaceWith(tmp.firstElementChild);
}
$('#grid').onclick = (e) => {
  const sel = e.target.closest('[data-sel]');
  if (sel) { e.stopPropagation(); const g = S.games.find(x => x.id === +sel.dataset.sel); toggleSelect(g).catch(err => toast(err.message, true)); return; }
  const t = e.target.closest('[data-id]'); if (!t) return;
  const g = S.games.find(x => x.id === +t.dataset.id); openDetail(g);
};

// The card is tied to the selected tile: click a game, then hovering that tile fades the comparison in,
// and leaving it fades the card out. Hovering anything else does nothing, so the grid stays quiet.
$('#grid').addEventListener('mouseover', (e) => {
  const t = e.target.closest('[data-id]');
  if (!t) return;
  const id = +t.dataset.id;
  if (!S.current || S.current.id !== id) { if (TWIN.id !== null) { clearTimeout(TWIN.t); TWIN.t = setTimeout(hideTwinCard, 120); } return; }
  const g = S.games.find(x => x.id === id);
  if (!g || !twinsOf(g).length) return;
  clearTimeout(TWIN.t);
  TWIN.t = setTimeout(() => showTwinCard(t, g), 90);
});
$('#grid').addEventListener('mouseleave', () => { clearTimeout(TWIN.t); TWIN.t = setTimeout(hideTwinCard, 160); });
$('#grid').addEventListener('scroll', () => hideTwinCard(true), { passive: true });

// ------------------------------------------------------------ detail
async function openDetail(g) {
  $$('#grid .current').forEach(x => x.classList.remove('current'));
  const el = $(`#grid [data-id="${g.id}"]`); if (el) el.classList.add('current');
  S.current = g;
  $('#detail').classList.remove('hidden');
  $('#detail').innerHTML = '<div class="muted">loading…</div>';
  try { g.detail = await api.get('game/' + g.id); renderDetail(g); } catch (e) { $('#detail').innerHTML = esc(e.message); }
}
// The system tag in the detail panel doubles as the version picker when the game exists on more than
// one system. Choosing a system moves the device selection onto that version and opens it, so exactly
// one version of a game can be selected at a time.
function versionPicker(g) {
  const t = twinsOf(g);
  if (!t.length) return `<span class="chip kind-system" data-sys="${esc(g.system)}">${esc(g.sysLabel)}</span>`;
  const all = [{ g, loose: false }, ...t].sort((a, b) => (a.g.sysLabel || '').localeCompare(b.g.sysLabel || ''));
  const opts = all.map(x => `<option value="${x.g.id}" ${x.g.id === g.id ? 'selected' : ''}>`
    + `${esc(x.g.sysLabel)}${x.g.year ? ' \u00b7 ' + x.g.year : ''}`
    + `${S.devView && isSelected(x.g) ? ' \u2713' : ''}${x.loose ? ' (loose)' : ''}</option>`).join('');
  return `<select class="chip kind-system vpick" id="d-version" title="this game is in the library on ${all.length} systems">${opts}</select>`;
}

function renderDetail(g) {
  const d = g.detail || {};
  const tagChip = (t) => `<span class="chip kind-${t.kind}" data-tag="${esc(t.tag)}" title="${t.kind}${t.state === 'proposed' ? ' (suggested — click ✓ to accept)' : ''}">${esc(t.tag)}${t.state === 'proposed' ? ' <b data-accept="1">✓</b> <b data-accept="0">✗</b>' : ' <b data-del="1">✕</b>'}</span>`;
  const selBtn = S.devView ? `<button class="${isSelected(g) ? 'primary' : ''}" id="d-sel">${isSelected(g) ? '✓ Selected for ' + esc(S.devView.profile.name) : 'Select for ' + esc(S.devView.profile.name)}</button>` : '';
  $('#detail').innerHTML = `
    <button class="close" id="d-close">✕</button>
    ${g.cover ? `<img class="big" src="/covers/${encodeURIComponent(g.cover)}">` : '<div class="nocov big" style="height:200px;display:flex;align-items:center;justify-content:center">no cover</div>'}
    <h3>${esc(g.title || g.name)}</h3>
    <div class="meta">${versionPicker(g)}${g.year ? `<span>${g.year}</span>` : ''}${g.rating ? `<span class="rating">★ ${g.rating}</span><span>${g.votes} votes</span>` : ''}<span>${fmtB(g.size)}${g.kind === 'folder' ? ` · ${g.files} files` : ''}</span>${g.regions.length ? `<span>${esc(g.regions.join(', '))}</span>` : ''}</div>
    <div style="margin:10px 0">${selBtn}</div>
    <div class="chips">${g.genres.map(x => `<span class="chip" data-genre="${esc(x)}">${esc(x)}</span>`).join('')}${g.tags.map(tagChip).join('')}</div>
    <div class="tagadd"><input id="tag-new" placeholder="add a tag (e.g. franchise: Mortal Kombat)"><button id="tag-add">Add</button></div>
    ${(d.media || []).filter(m => m.kind === 'screenshot').length ? `<div class="shots">${d.media.filter(m => m.kind === 'screenshot').map(m => `<img loading="lazy" src="/screens/t_screenshot_med/${esc(m.image_id)}" data-big="/screens/t_screenshot_huge/${esc(m.image_id)}">`).join('')}</div>` : ''}
    <div class="summary">${esc(d.summary || (g.matched ? '' : 'No IGDB match yet. The file name is all we know.'))}</div>
    ${d.igdb_name && d.igdb_name !== g.title ? `<div class="kv">IGDB: ${esc(d.igdb_name)}${d.confidence ? ` (match ${Math.round(d.confidence * 100)}%)` : ''}</div>` : ''}
    <div class="kv">${esc(d.path || g.name)}</div>
    <div class="tagadd"><input id="igdb-id" placeholder="wrong match? paste the IGDB id or game URL" title="Open the game on igdb.com; the id is in the page's 'Game ID' box or the URL slug works too"><button id="igdb-fix">Fix match</button></div>
    ${(d.on_devices || []).length ? `<div class="kv" style="color:var(--ok)">On: ${esc(d.on_devices.join(', '))}</div>` : ''}
    ${(d.versions || []).length ? `<div class="versions"><h4>Other versions</h4>${d.versions.map(v => `<div class="v" data-id="${v.id}"><span class="chip kind-system">${esc(S.systems[v.system] || v.system)}</span><span class="t" style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${esc(v.name)}">${esc(v.name)}</span><span class="muted">${fmtB(v.size)}</span></div>`).join('')}</div>` : ''}
  `;
  $('#d-close').onclick = () => { $('#detail').classList.add('hidden'); S.current = null; $$('#grid .current').forEach(x => x.classList.remove('current')); };
  if ($('#d-sel')) $('#d-sel').onclick = () => toggleSelect(g).catch(err => toast(err.message, true));
  if ($('#d-version')) $('#d-version').onchange = async (e) => {
    const id = +e.target.value;
    const to = S.games.find(x => x.id === id);
    if (!to || id === g.id) return;
    try {
      if (S.devView && isSelected(g)) await switchTo(g.id, id);        // move the selection with it
      openDetail(to);
    } catch (err) { toast(err.message, true); e.target.value = String(g.id); }
  };
  $('#tag-add').onclick = async () => {
    const v = $('#tag-new').value.trim(); if (!v) return;
    let kind = 'user', tag = v; const m = v.match(/^(franchise|theme|genre)\s*:\s*(.+)$/i); if (m) { kind = m[1].toLowerCase(); tag = m[2].trim(); }
    await api.post('tag/add', { game_id: g.id, tag, kind });
    g.tags.push({ tag, kind, state: 'accepted' }); prep(g); renderDetail(g); applyFilters();
  };
  $('#igdb-fix').onclick = async () => {
    const v = $('#igdb-id').value.trim(); if (!v) return;
    try {
      const r = await api.post(`game/${g.id}/rematch`, { igdb: v });
      toast('Matched to ' + r.igdb_name); await loadLibrary(); const gg = S.games.find(x => x.id === g.id); if (gg) openDetail(gg);
    } catch (e) { toast(e.message, true); }
  };
  $('#detail').onclick = async (e) => {
    const shot = e.target.closest('.shots img'); if (shot) { modal(`<img src="${shot.dataset.big}" style="max-width:100%;max-height:80vh;display:block">`); return; }
    const v = e.target.closest('.v[data-id]'); if (v) { const gg = S.games.find(x => x.id === +v.dataset.id); if (gg) openDetail(gg); return; }
    const del = e.target.closest('[data-del]'); if (del) { const tag = del.closest('[data-tag]').dataset.tag; await api.post('tag/remove', { game_id: g.id, tag }); g.tags = g.tags.filter(t => t.tag !== tag); prep(g); renderDetail(g); applyFilters(); return; }
    const acc = e.target.closest('[data-accept]'); if (acc) { const tag = acc.closest('[data-tag]').dataset.tag; const ok = acc.dataset.accept === '1'; await api.post('tag/decide', { game_id: g.id, tag, accept: ok }); g.tags = ok ? g.tags.map(t => t.tag === tag ? { ...t, state: 'accepted' } : t) : g.tags.filter(t => t.tag !== tag); prep(g); renderDetail(g); applyFilters(); return; }
    const gen = e.target.closest('[data-genre]'); if (gen) { S.f.genre.clear(); S.f.genre.add(gen.dataset.genre); applyFilters(); return; }
    const tg = e.target.closest('[data-tag]'); if (tg) { const kind = (g.tags.find(t => t.tag === tg.dataset.tag) || {}).kind; const key = ['franchise', 'theme', 'mode', 'perspective'].includes(kind) ? kind : 'tag'; S.f[key].clear(); S.f[key].add(tg.dataset.tag); applyFilters(); return; }
    const sy = e.target.closest('[data-sys]'); if (sy) { S.f.system.clear(); S.f.system.add(sy.dataset.sys); applyFilters(); }
  };
}

// ------------------------------------------------------------ device picker
async function loadDevicePicker() {
  const d = await api.get('devices');
  const sel = $('#device-select');
  const cur = sel.value;
  sel.innerHTML = '<option value="">— no device —</option>' + d.profiles.map(p => `<option value="${p.id}">${esc(p.name)}</option>`).join('');
  sel.value = cur || localStorage.getItem('romsync.device') || '';
  await setDevice(sel.value);
  return d;
}
async function setDevice(id) {
  S.device = id || null; localStorage.setItem('romsync.device', id || '');
  S.devView = null;
  if (id) {
    try { const v = await api.get('profile/' + id); v.onDeviceSet = new Set(v.on_device); S.devView = v; } catch (e) { toast(e.message, true); S.device = null; }
  }
  renderSelSummary(); applyFilters(); if (S.current) renderDetail(S.current);
}
$('#device-select').onchange = (e) => setDevice(e.target.value);

// ------------------------------------------------------------ views
function showView(name) {
  S.view = name;
  $$('.view').forEach(v => v.classList.toggle('active', v.id === 'view-' + name));
  $$('.nav').forEach(b => b.classList.toggle('active', b.dataset.view === name || (name === 'device' && b.dataset.view === 'devices')));
  if (name === 'devices') renderDevices();
  if (name === 'sysfiles') renderSysfiles();
  if (name === 'settings') renderSettings();
}
$$('.nav').forEach(b => b.onclick = () => showView(b.dataset.view));

// ---- Devices
async function renderDevices(refresh) {
  const el = $('#device-list'); el.innerHTML = '<div class="muted">looking…</div>';
  const d = await api.get('devices' + (refresh ? '?refresh=1' : ''));
  $('#probe-note').textContent = 'checked ' + new Date(d.probed_at * 1000).toLocaleTimeString() +
    (d.probe_error ? ' — could not look: ' + d.probe_error : '');
  const entries = d.entries || [];

  el.innerHTML = entries.map(e => {
    const used = e.info && e.info.capacity && e.info.free != null ? 1 - e.info.free / e.info.capacity : 0;
    const cap = e.info && e.info.capacity
      ? `${fmtB(e.info.free)} free of ${fmtB(e.info.capacity)}` : 'capacity unknown';

    if (e.kind === 'profile') {
      const lamp = `<span class="lamp ${e.online ? 'on' : ''}"></span>`;
      const where = e.online
        ? `${esc(e.label || e.transport)} · ROMs at ${esc(e.roms_root)}`
        : `last seen ${esc((e.last_seen || '').slice(0, 16).replace('T', ' ') || 'never')}`;
      // Sync is the only action, and it is live only when the device is actually here.
      const sync = e.online
        ? `<button class="primary" data-sync="${e.id}">Sync</button>`
        : `<button class="primary" disabled title="Connect this device to sync">Sync</button>`;
      return `<div class="card ${e.online ? '' : 'offline'}">
        <h3>${lamp}${esc(e.name)}</h3>
        <div class="dev-state">${e.online ? 'online' : 'offline'} · ${where}</div>
        <div class="muted">${cap}</div><div class="bar"><i style="width:${Math.round(used * 100)}%"></i></div>
        <div class="dev-figs">
          <div><b>${e.selected}</b><span>selected</span></div>
          <div><b>${e.on_device}</b><span>on device</span></div>
          <div><b>${fmtB(e.on_device_bytes)}</b><span>used by games</span></div>
        </div>
        <div class="actions">${sync}<button data-open="${e.id}">Contents</button><button data-use="${e.id}">Choose games</button></div>
      </div>`;
    }

    // Plugged in, no profile yet.
    const bad = e.state && e.state !== 'device';
    const note = bad ? `<span class="pill warn">${esc(e.state)} — accept the debugging prompt on the device</span>`
      : e.marker ? `<span class="pill warn">carries ROM-Sync.json from another PC: ${esc(e.marker.name || '')}</span>`
      : `<span class="pill">no profile yet</span>`;
    const act = bad ? ''
      : e.marker ? `<button class="primary" data-adopt="${e.index}">Adopt profile</button>`
      : `<button class="primary" data-new="${e.index}" data-kind="${e.transport}" data-root="${esc(e.roms_root)}">New profile…</button>`;
    return `<div class="card">
      <h3><span class="lamp ${bad ? 'bad' : 'on'}"></span>${esc(e.label)}</h3>
      <div class="dev-state">${esc(e.transport === 'volume' ? 'drive' : e.transport)}</div>
      <div class="muted">${cap}</div><div class="bar"><i style="width:${Math.round(used * 100)}%"></i></div>
      <div>${note}</div><div class="actions">${act}</div></div>`;
  }).join('') || '<div class="muted">No profiles, and nothing plugged in that could be a destination.</div>';

  $('#view-devices').onclick = async (e) => {
    const b = e.target.closest('button'); if (!b || b.disabled) return;
    try {
      if (b.dataset.sync) { $('#device-select').value = b.dataset.sync; await setDevice(b.dataset.sync); showDevice(b.dataset.sync); startSync(b.dataset.sync); }
      else if (b.dataset.open) showDevice(b.dataset.open);
      else if (b.dataset.use) { $('#device-select').value = b.dataset.use; await setDevice(b.dataset.use); showView('library'); }
      else if (b.dataset.adopt) { const r = await api.post('profile/adopt', { index: +b.dataset.adopt }); await loadDevicePicker(); showDevice(r.id); }
      else if (b.dataset.new) newProfileDialog(+b.dataset.new, b.dataset.kind, b.dataset.root);
    } catch (err) { toast(err.message, true); }
  };
}
$('#refresh-devices').onclick = () => renderDevices(true);
function newProfileDialog(index, kind, root) {
  modal(`<h3>New device profile</h3>
    <div class="field"><label>Name</label><input id="np-name" placeholder="e.g. AYN Thor, Steam Deck SD card"></div>
    <div class="field"><label>ROMs folder on the device (ES-DE layout)</label><input id="np-root" value="${esc(root)}">
      <span class="muted">Created there if it does not exist — you will be asked first.</span></div>
    <label class="row"><input type="checkbox" id="np-marker" checked> write ROM-Sync.json to the device so it is recognised anywhere</label>
    <div class="actions"><button id="np-cancel">Cancel</button><button class="primary" id="np-ok">Create</button></div>`);
  $('#np-cancel').onclick = closeModal;
  $('#np-ok').onclick = async () => {
    const name = $('#np-name').value.trim(); const r = $('#np-root').value.trim(); if (!name) return;
    if (!confirm(`Create profile "${name}" with ROMs folder "${r}" on this ${kind === 'mtp' ? 'device' : 'drive'}?` + ($('#np-marker').checked ? '\nROM-Sync.json will be written there.' : ''))) return;
    try { const res = await api.post('profile/new', { index, name, roms_root: r, marker: $('#np-marker').checked }); closeModal(); await loadDevicePicker(); showDevice(res.id); } catch (e) { toast(e.message, true); }
  };
}

// ---- Device page
let devPageId = null;
async function showDevice(id) {
  devPageId = id; showView('device');
  const page = $('#device-page'); page.innerHTML = '<div class="muted">loading…</div>';
  try { await renderDevicePage(id, true); } catch (e) { page.innerHTML = `<div class="pill bad">${esc(e.message)}</div>`; }
}
// The device page watches for the device: a fresh probe on open, then every 15 s while the page is
// showing; the page re-renders when the connection state changes (plugged in / unplugged).
const DEVWATCH = { timer: null, id: null, connected: null };
function watchDevice(id, connected) {
  DEVWATCH.id = id; DEVWATCH.connected = connected;
  if (DEVWATCH.timer) clearInterval(DEVWATCH.timer);
  DEVWATCH.timer = setInterval(async () => {
    if (S.view !== 'device' || devPageId !== id) { clearInterval(DEVWATCH.timer); DEVWATCH.timer = null; return; }
    try {
      const d = await api.get('devices?refresh=1');
      const now = d.candidates.some(c => c.profile && c.profile.id === id);
      if (now !== DEVWATCH.connected) { DEVWATCH.connected = now; toast(now ? 'device connected' : 'device disconnected'); await renderDevicePage(id); }
    } catch (e) { /* probe hiccup: try again next tick */ }
  }, 15000);
}
async function renderDevicePage(id, probe) {
  if (probe) { try { await api.get('devices?refresh=1'); } catch (e) { /* stale cache is still usable */ } }
  const v = await api.get('profile/' + id);
  watchDevice(id, v.connected);
  const pageEl = $('#device-page'); const keepScroll = pageEl ? pageEl.scrollTop : 0;
  requestAnimationFrame(() => { if (pageEl && keepScroll) pageEl.scrollTop = keepScroll; });
  const page = $('#device-page');
  const systems = Object.keys(v.store_systems).sort();
  const modeSeg = (s) => { const m = v.modes[s]; return `<span class="seg" data-sys="${s}"><button class="${m === 'all' ? 'active' : ''}" data-mode="all" title="select every game in this system">all</button><button class="${m === 'all' ? '' : 'active'}" data-mode="none" title="select none (per-game picks in the Library still apply)">none</button></span>`; };
  const used = v.info.capacity && v.info.free != null ? 1 - v.info.free / v.info.capacity : 0;
  page.innerHTML = `
    <h2>${esc(v.profile.name)} <span class="pill ${v.connected ? 'ok' : 'warn'}">${v.connected ? 'connected' : 'not plugged in'}</span>
      <span class="spacer"></span>
      <button id="dv-rename">Rename</button><button id="dv-use">Select games in Library</button><span id="dv-sync"></span><button id="dv-scan" ${v.connected ? '' : 'disabled'}>Scan device</button><button id="dv-marker" ${v.connected ? '' : 'disabled'} title="rewrite ROM-Sync.json on the device">Write ROM-Sync.json</button></h2>
    <div class="muted">${v.profile.kind === 'mtp' ? 'USB device ' + esc(v.profile.mtp_device_id) + ' \\ ' + esc(v.profile.mtp_storage_id) : 'Drive'} · ROMs folder: ${esc(v.profile.roms_root)} · ${v.connected ? fmtB(v.info.free) + ' free of ' + fmtB(v.info.capacity) : 'last seen ' + esc((v.profile.last_seen || '').slice(0, 16).replace('T', ' '))}</div>
    ${v.connected ? `<div class="bar"><i style="width:${Math.round(used * 100)}%"></i></div>` : ''}
    <div id="dv-job"></div>
    <h2>Systems</h2>
    <table><thead><tr><th>System</th><th class="num">In store</th><th class="num">Store size</th><th class="num">On device</th><th class="num">Device size</th><th>Selection</th><th>Overrides</th></tr></thead><tbody>
    ${systems.map(s => { const st = v.store_systems[s]; const dv = v.device_systems[s] || { n: 0, bytes: 0 }; const ov = S.games.filter(g => g.system === s && v.overrides[String(g.id)] != null).length; return `<tr><td>${esc(S.systems[s] || s)} <span class="muted">${s}</span></td><td class="num">${st.n}</td><td class="num">${fmtB(st.bytes)}</td><td class="num">${dv.n}</td><td class="num">${fmtB(dv.bytes)}</td><td>${modeSeg(s)}</td><td>${ov ? ov + (v.modes[s] === 'all' ? ' excluded' : ' picked') : ''}</td></tr>`; }).join('')}
    ${Object.keys(v.device_systems).filter(s => !v.store_systems[s] && s !== 'bios').map(s => `<tr><td>${esc(s)} <span class="pill warn">on device, not a store system: left alone</span></td><td></td><td></td><td class="num">${v.device_systems[s].n}</td><td class="num">${fmtB(v.device_systems[s].bytes)}</td><td></td><td></td></tr>`).join('')}
    </tbody></table>
    <h2>Sync</h2>
    <div id="dv-planbox" class="muted">loading…</div>
    <h2>System files <button id="dv-sysfiles">Open System files</button></h2>
    <div class="muted">${(v.readiness || []).filter(r => r.state === 'missing').map(r => `<span class="pill bad">${esc(r.label)}: missing ${esc(r.missing.join(', '))}</span>`).join(' ') || ((v.readiness || []).some(r => r.state === 'unknown') ? 'Not read yet: open System files and press Refresh from device.' : 'Every system on the device has what its emulator needs.')}</div>
    <h2>History</h2>
    <table><thead><tr><th>Run</th><th>Started</th><th>State</th><th>Sent</th><th>Removed</th><th>Pulled</th><th>Failed</th><th class="num">Moved</th></tr></thead><tbody>
    ${v.runs.map(r => { const c = r.counts ? JSON.parse(r.counts) : {}; return `<tr><td>#${r.id}</td><td>${esc((r.started || '').slice(0, 16).replace('T', ' '))}</td><td>${esc(r.state)}</td><td>${c.sent ?? ''}</td><td>${c.removed ?? ''}</td><td>${c.pulled ?? ''}</td><td>${c.failed ? `<span class="pill bad">${c.failed}</span>` : c.failed ?? ''}</td><td class="num">${fmtB(r.bytes_moved)}</td></tr>`; }).join('') || '<tr><td colspan="8" class="muted">no runs yet</td></tr>'}
    </tbody></table>`;
  page.onclick = async (e) => {
    const b = e.target.closest('button'); if (!b) return;
    try {
      if (b.dataset.mode) {
        const s = b.closest('[data-sys]').dataset.sys;
        await api.post(`profile/${id}/select-system`, { system: s, mode: b.dataset.mode });
        if (S.device === id) await setDevice(id);
        await renderDevicePage(id);
      } else if (b.id === 'dv-use') { $('#device-select').value = id; await setDevice(id); showView('library'); }
      else if (b.id === 'dv-rename') { const n = prompt('New name', v.profile.name); if (n && n.trim()) { await api.post(`profile/${id}/rename`, { name: n.trim() }); await loadDevicePicker(); await renderDevicePage(id); } }
      else if (b.id === 'dv-scan') { const j = await api.post(`profile/${id}/scan`); await watchJob(j.id, 'Scanning the device (read-only)…', async () => { if (S.device === id) await setDevice(id); await renderDevicePage(id); }); }
      else if (b.id === 'dv-sysfiles') { if (S.device !== id) { $('#device-select').value = id; await setDevice(id); } showView('sysfiles'); }
      else if (b.id === 'dv-marker') { if (!confirm('Write ROM-Sync.json to the device now?')) return; await api.post(`profile/${id}/write-marker`); toast('ROM-Sync.json written'); }
    } catch (err) { toast(err.message, true); }
  };
  devPageView = v; renderSyncCtl();
  showPlanSummary(id);
}
// What Sync would do right now, read-only: the numbers behind the one button.
async function showPlanSummary(id) {
  const box = $('#dv-planbox'); if (!box) return;
  let p; try { p = await api.get(`profile/${id}/plan`); } catch (e) { box.innerHTML = `<span class="pill bad">${esc(e.message)}</span>`; return; }
  if (devPageId !== id || !$('#dv-planbox')) return;
  const sz = (l) => fmtB(l.reduce((a, o) => a + o.size, 0));
  const parts = [];
  if (p.send.length) parts.push(`<b>send ${p.send.length.toLocaleString()}</b> (${sz(p.send)})`);
  if (p.update.length) parts.push(`<b>replace ${p.update.length.toLocaleString()}</b> (${sz(p.update)})`);
  if (p.remove.length) parts.push(`<b>remove ${p.remove.length.toLocaleString()}</b> (${sz(p.remove)})`);
  const b = p.bytes;
  const unknown = Object.keys(p.unknown_systems).length ? `<div class="muted">Folders on the device that are not store systems are left alone: ${esc(Object.entries(p.unknown_systems).map(([s, n]) => `${s} (${n})`).join(', '))}</div>` : '';
  box.className = '';
  box.innerHTML = `<div>${parts.length ? 'Sync will ' + parts.join(', ') : '<span class="pill ok">the device matches your selection</span>'} · ${p.unchanged.toLocaleString()} already in place</div>
    <div class="muted" style="margin-top:4px">Net change ${fmtB(b.net)}${b.free != null ? ` · ${fmtB(b.free)} free now · ${b.fits ? '<span class="pill ok">fits</span>' : '<span class="pill bad">does not fit</span>'}` : ''}. Games only, nothing wiped: Sync copies and removes the difference; bios and system files are never touched. <span id="plan-detail-toggle" class="link">show list</span></div>
    <div id="plan-detail" class="hidden plan-detail">${['send', 'update', 'remove'].map(k => p[k].map(o => `<div><span class="pill">${k}</span> ${esc(o.system)} \\ ${esc(o.name)} <span class="muted">${fmtB(o.size)}</span></div>`).join('')).join('')}</div>`;
  const t = $('#plan-detail-toggle'); if (t) t.onclick = () => { const d = $('#plan-detail'); d.classList.toggle('hidden'); t.textContent = d.classList.contains('hidden') ? 'show list' : 'hide list'; };
}
async function watchJob(jobId, label, done) {
  const box = $('#dv-job'); box.innerHTML = `<div class="progress">${esc(label)}</div>`;
  while (true) {
    await new Promise(r => setTimeout(r, 1500));
    const j = await api.get('job/' + jobId);
    if (j.state === 'done') { box.innerHTML = `<div class="progress">Done: ${esc(JSON.stringify(j.result))}</div>`; await done(); return; }
    if (j.state === 'error') { box.innerHTML = `<div class="progress" style="border-color:var(--bad)">Failed: <pre>${esc(j.error)}</pre></div>`; return; }
  }
}
// ---- System files
// System files: per-system readiness for the selected device, laid out like a system-information
// pane: systems on the left (most games on the device first), the chosen system's items on the right.
const SF = { data: null, sel: null, busy: new Set() };
const SF_STATE = { ready: ['ok', 'ready'], missing: ['bad', 'missing'], optional: ['warn', 'optional'], none: ['muted', 'nothing needed'], unseen: ['muted', 'not seen over USB'], unknown: ['muted', 'not scanned'] };
function sfDot(state) { const [c, t] = SF_STATE[state] || ['muted', state]; return `<i class="dot ${c}" title="${t}"></i>`; }
function sfPill(state) { const [c, t] = SF_STATE[state] || ['muted', state]; return `<span class="pill ${c === 'muted' ? '' : c}">${t}</span>`; }
async function renderSysfiles() {
  const page = $('#sysfiles-page'); page.innerHTML = '<div class="muted">checking…</div>';
  if (!S.device) {
    const d = await api.get('sysfiles');
    page.innerHTML = `<h2>System files in the store <span class="muted">${esc(S.lib.store)}\\bios · D:\\Games\\_firmware</span></h2>
      <p class="muted">Pick a device in the top-right to see what its emulators have and need. The app checks and places these files; it never generates them.</p>
      <table><thead><tr><th>System</th><th>Emulator</th><th>File</th><th>Need</th><th>Store</th><th>Note</th></tr></thead><tbody>
      ${d.store.map(r => `<tr><td>${esc(S.systems[r.system] || r.system)}</td><td>${esc(r.emulator)}</td><td>${esc(r.name)}</td><td>${r.required ? 'required' : 'optional'}</td><td>${r.store_present ? `<span class="pill ${r.store_verified === false ? 'warn' : 'ok'}">${r.store_size != null ? fmtB(r.store_size) : 'present'}${r.store_verified === true ? ' verified' : r.store_verified === false ? ' not a known dump' : ''}</span>` : '<span class="pill bad">missing</span>'}</td><td class="muted">${esc(r.note)}</td></tr>`).join('')}
      </tbody></table>`;
    return;
  }
  SF.data = await api.get('sysfiles?device=' + S.device);
  if (!SF.sel || !SF.data.systems.some(x => x.system === SF.sel)) SF.sel = (SF.data.systems.find(x => x.on_device.n) || SF.data.systems[0] || {}).system;
  page.innerHTML = `<h2>${esc(S.devView.profile.name)}: system files <span class="spacer"></span><span class="muted" id="sf-scanned">${SF.data.scanned_at ? 'device read ' + esc(SF.data.scanned_at.slice(0, 16).replace('T', ' ')) : 'device not read yet'}</span> <button id="sf-scan" ${S.devView.connected ? '' : 'disabled'} title="read the staging and emulator folders on the device (read-only)">Refresh from device</button></h2>
    <div class="muted" style="margin:-6px 0 10px">Add / Update copies a system's files into <b>${esc(SF.data.stage_root)}\\&lt;system&gt;</b> on the device; you install them from there with the emulator's own menus. Installed shows what the emulator actually reads.</div>
    <div id="sf-job"></div>
    <div class="sf-pane"><div class="sf-list" id="sf-list"></div><div class="sf-detail" id="sf-detail"></div></div>`;
  $('#sf-scan').onclick = async () => {
    try { const j = await api.post(`profile/${S.device}/scan-sysfiles`); const box = $('#sf-job'); box.innerHTML = '<div class="progress">Reading the emulator folders on the device…</div>';
      while (true) { await new Promise(r => setTimeout(r, 1200)); const jj = await api.get('job/' + j.id); if (jj.state === 'done') { box.innerHTML = ''; toast(`read ${jj.result.paths} folders, ${jj.result.entries} entries`); await renderSysfiles(); return; } if (jj.state === 'error') { box.innerHTML = `<div class="progress" style="border-color:var(--bad)">Failed: <pre>${esc(jj.error)}</pre></div>`; return; } box.firstElementChild.textContent = 'Reading the device… ' + (jj.progress || ''); }
    } catch (e) { toast(e.message, true); }
  };
  renderSfList(); renderSfDetail();
}
function renderSfList() {
  const el = $('#sf-list'); if (!el) return;
  const rows = SF.data.systems; let html = ''; let divider = false;
  for (const s of rows) {
    if (!divider && !s.on_device.n) { divider = true; html += '<div class="sf-divider">in the store, not on the device</div>'; }
    html += `<div class="sf-row ${s.system === SF.sel ? 'active' : ''} ${s.on_device.n ? '' : 'dim'}" data-sys="${s.system}">${sfDot(s.state)}<span class="name">${esc(s.label)}</span><span class="n">${s.on_device.n ? s.on_device.n.toLocaleString() : ''}</span></div>`;
  }
  html += `<div class="sf-divider">${esc(SF.data.stage_root)}</div><div class="sf-row ${SF.sel === '*others' ? 'active' : ''}" data-sys="*others"><i class="dot ${SF.data.others.length ? 'warn' : ''}"></i><span class="name">Other files</span><span class="n">${SF.data.others.length || ''}</span></div>`;
  el.innerHTML = html;
  el.onclick = (e) => { const r = e.target.closest('.sf-row'); if (!r) return; SF.sel = r.dataset.sys; $$('.sf-row', el).forEach(x => x.classList.toggle('active', x.dataset.sys === SF.sel)); renderSfDetail(); };
}
const SF_STAGED = { current: ['ok', 'current'], different: ['warn', 'different version'], staged: ['ok', 'staged'], 'not staged': ['bad', 'not staged'], unknown: ['', 'not read'] };
const SF_INST = { installed: ['ok', 'installed'], different: ['warn', 'different version'], missing: ['bad', 'not installed'], unseen: ['', 'not visible'], 'n/a': ['', 'n/a'], unknown: ['', 'not read'] };
const pillOf = (map, k) => { const [c, t] = map[k] || ['', k]; return `<span class="pill ${c}">${t}</span>`; };
function sfReqRow(r) {
  const store = r.store_present ? `<span class="pill ${r.store_verified === false ? 'warn' : 'ok'}">${r.store_size != null ? fmtB(r.store_size) : 'present'}${r.store_verified === true ? ' verified' : r.store_verified === false ? ' not a known dump' : ''}</span>` : '<span class="pill bad">not in store</span>';
  return `<tr><td><b>${esc(r.name)}</b>${r.staged_name !== r.name ? ` <span class="muted">${esc(r.staged_name)}</span>` : ''}<div class="muted">${esc(r.note)}</div></td><td>${r.required ? 'required' : 'optional'}${r.group ? ' <span class="muted">(any one)</span>' : ''}</td><td>${store}</td><td>${pillOf(SF_STAGED, r.staged)}</td><td>${pillOf(SF_INST, r.installed)}<div class="muted sm">${esc(r.installed_path)}</div></td></tr>`;
}
function renderSfDetail() {
  const el = $('#sf-detail'); if (!el) return;
  if (SF.sel === '*others') return renderSfOthers(el);
  const s = SF.data.systems.find(x => x.system === SF.sel); if (!s) { el.innerHTML = ''; return; }
  const busy = SF.busy.has(s.system);
  const emu = s.emulator_seen === false ? `${esc(s.emulator)} <span class="pill">not seen over USB</span> <span class="muted">open it once on the device, then Refresh from device</span>` : s.emulator_seen ? `${esc(s.emulator)} <span class="pill ok">installed</span> <span class="muted">${esc(s.package || '')}</span>` : esc(s.emulator);
  const stageLabel = s.stage_action === 'update' ? 'Update' : 'Add';
  const btns = s.requirements.length ? `<span class="sf-actions"><button class="primary" data-act="stage" ${s.stage_action && !busy ? '' : 'disabled'} title="copy this system's files from the store into ${esc(s.stage_path)}">${busy ? '<i class="spin"></i>' : stageLabel}</button><button data-act="unstage" ${s.can_unstage && !busy ? '' : 'disabled'} title="delete this system's files from ${esc(s.stage_path)}">Remove</button></span>` : '';
  el.innerHTML = `<h3>${esc(s.label)} <span class="muted">${esc(s.system)}</span> ${sfPill(s.state)}${btns}</h3>
    <table class="kv"><tbody>
      <tr><td>Emulator</td><td>${emu}</td></tr>
      <tr><td>Games on device</td><td>${s.on_device.n.toLocaleString()} · ${fmtB(s.on_device.bytes)} <span class="muted">(${s.in_store.n.toLocaleString()} in the store)</span></td></tr>
      <tr><td>Installed</td><td>${s.state === 'missing' ? 'Missing: ' + esc(s.missing.join(', ')) : s.state === 'unseen' ? esc(s.emulator) + ' has not written any app data where USB can see it, so its install folder cannot be read; the games and staged files are unaffected' : s.state === 'unknown' ? 'Press Refresh from device' : SF_STATE[s.state][1]}${s.note ? `<div class="muted">${esc(s.note)}</div>` : ''}</td></tr>
      ${s.requirements.length ? `<tr><td>Staged</td><td>${esc(s.stage_state)} <span class="muted">in ${esc(s.stage_path)}</span></td></tr>` : ''}
    </tbody></table>
    ${s.requirements.length ? `<table class="sf-req"><thead><tr><th>Item</th><th>Need</th><th>Store</th><th>Staged</th><th>Installed</th></tr></thead><tbody>${s.requirements.map(r => sfReqRow(r)).join('')}</tbody></table>` : ''}`;
  el.onclick = async (e) => {
    const b = e.target.closest('button[data-act]'); if (!b || b.disabled) return;
    if (SYNC.job && SYNC.device === S.device) { toast('Wait for the sync to finish'); return; }
    const sys = s.system; SF.busy.add(sys); renderSfDetail();
    try {
      let row;
      if (b.dataset.act === 'stage') {
        const j = await api.post(`profile/${S.device}/sysfiles-stage`, { system: sys });
        while (true) { await new Promise(r => setTimeout(r, 800)); const jj = await api.get('job/' + j.id); if (jj.state === 'done') { row = jj.result.system; toast(`${s.label}: ${jj.result.placed.length ? 'placed ' + jj.result.placed.join(', ') : 'nothing to copy'} → ${s.stage_path}`); break; } if (jj.state === 'error') throw new Error(jj.error.split('\n')[0]); }
      } else {
        const r = await api.post(`profile/${S.device}/sysfiles-unstage`, { system: sys }); row = r.system; toast(`${s.label}: removed ${r.removed.length ? r.removed.join(', ') : 'nothing'} from ${s.stage_path}`);
      }
      const i = SF.data.systems.findIndex(x => x.system === sys); if (i >= 0) SF.data.systems[i] = row;
      SF.busy.delete(sys);
      if (SF.sel === sys) renderSfDetail();
      const li = $(`.sf-row[data-sys="${sys}"]`); if (li) li.firstElementChild.outerHTML = sfDot(row.state);
      SF.data = await api.get('sysfiles?device=' + S.device); renderSfList();          // others may have changed
    } catch (err) { SF.busy.delete(sys); toast(err.message, true); renderSfDetail(); }
  };
}
function renderSfOthers(el) {
  const o = SF.data.others;
  el.innerHTML = `<h3>Other files in ${esc(SF.data.stage_root)} <span class="muted">${o.length}</span></h3>
    <div class="muted" style="margin-bottom:8px">Files under the staging folder that belong to no system's set. Remove deletes the file from the device.</div>
    ${o.length ? `<table class="sf-req"><thead><tr><th>Folder</th><th>Name</th><th>Size</th><th></th></tr></thead><tbody>${o.map(f => `<tr><td class="muted">${esc(f.path)}</td><td><b>${esc(f.name)}</b>${f.kind === 'folder' ? ' <span class="muted">(folder)</span>' : ''}</td><td>${f.kind === 'folder' ? '' : fmtB(f.size)}</td><td class="acts"><button data-rm="${esc(f.rel)}" data-name="${esc(f.name)}" ${SF.busy.has(f.rel + '/' + f.name) ? 'disabled' : ''}>${SF.busy.has(f.rel + '/' + f.name) ? '<i class="spin"></i>' : 'Remove'}</button></td></tr>`).join('')}</tbody></table>` : '<div class="pill ok">nothing stray</div>'}`;
  el.onclick = async (e) => {
    const b = e.target.closest('button[data-rm]'); if (!b || b.disabled) return;
    const key = b.dataset.rm + '/' + b.dataset.name; SF.busy.add(key); b.disabled = true; b.innerHTML = '<i class="spin"></i>';
    try { const r = await api.post(`profile/${S.device}/sysfiles-remove-other`, { path: b.dataset.rm, name: b.dataset.name }); SF.data.others = r.others; SF.busy.delete(key); toast(`${b.dataset.name} removed`); renderSfOthers(el); renderSfList(); }
    catch (err) { SF.busy.delete(key); toast(err.message, true); renderSfOthers(el); }
  };
}

// ---- Recover
async function renderRecover() {
  const page = $('#recover-page'); page.innerHTML = '<div class="muted">loading…</div>';
  const d = await api.get('devices');
  let html = `<h2>Recover</h2><p class="muted">Two ways back: items pulled from a device in earlier runs, and items already pulled, waiting to be placed in the store. Placing never overwrites a store file.</p>`;
  for (const p of d.profiles) {
    let v; try { v = await api.get('profile/' + p.id); } catch (e) { continue; }
    const missing = v.on_device.filter(rel => { const [sys, name] = rel.split('\\'); return sys !== 'bios' && !S.games.some(g => g.system === sys && g.name === name); });
    html += `<h2>${esc(p.name)}</h2>`;
    html += missing.length ? `<table><thead><tr><th>On device, not in store</th><th></th></tr></thead><tbody>${missing.map(rel => `<tr><td>${esc(rel)}</td><td class="muted">not selected, so the next Sync removes it from the device</td></tr>`).join('')}</tbody></table>` : '<div class="muted">Everything on this device is in the store.</div>';
    const runs = v.runs.filter(r => { const c = r.counts ? JSON.parse(r.counts) : {}; return c.pulled; });
    for (const r of runs) {
      const rr = await api.get('run/' + r.id);
      if (!rr.pulled.length) continue;
      html += `<h4>Pulled in run #${r.id}</h4><table><tbody>${rr.pulled.map(it => `<tr><td>${esc(it.system)} \\ ${esc(it.name)}</td><td>${it.in_store ? '<span class="pill">store already has this name</span>' : `<button class="primary" data-place="${r.id}" data-sys="${esc(it.system)}" data-name="${esc(it.name)}">Place in store</button>`}</td><td class="muted">${esc(it.path)}</td></tr>`).join('')}</tbody></table>`;
    }
  }
  page.innerHTML = html;
  page.onclick = async (e) => { const b = e.target.closest('[data-place]'); if (!b) return; try { const r = await api.post('place', { run: +b.dataset.place, system: b.dataset.sys, name: b.dataset.name }); toast('Placed at ' + r.path); await api.post('scan-store'); renderRecover(); } catch (err) { toast(err.message, true); } };
}

// ---- Settings
async function runJob(post, body, jobEl, done) {
  jobEl.className = 'job'; jobEl.textContent = 'starting…';
  try {
    const j = await api.post(post, body || {});
    if (!j.id) { jobEl.textContent = typeof j === 'object' ? JSON.stringify(j) : String(j); if (done) await done(j); return; }
    while (true) {
      await new Promise(r => setTimeout(r, 1500));
      const jj = await api.get('job/' + j.id);
      jobEl.textContent = jj.progress || 'running…';
      if (jj.state === 'done') { jobEl.textContent = 'done: ' + JSON.stringify(jj.result); if (done) await done(jj.result); return; }
      if (jj.state === 'error') { jobEl.className = 'job bad'; jobEl.textContent = jj.error.split('\n')[0]; return; }
    }
  } catch (e) { jobEl.className = 'job bad'; jobEl.textContent = e.message; }
}
async function renderSettings() {
  const page = $('#settings-page'); page.innerHTML = '<div class="muted">loading…</div>';
  const st = await api.get('settings');
  const c = st.counts;
  const running = st.jobs.filter(j => j.state === 'running');
  page.innerHTML = `<h2>Settings</h2>
  <div class="settings-grid">
    <div class="card"><h3>Library</h3>
      <div class="field"><label>Store root (the ES-DE ROMs folder)</label><div style="display:flex;gap:6px"><input id="s-store" value="${esc(st.store_root)}" style="flex:1"><button id="s-store-save">Save</button></div></div>
      <div class="stat"><span>Games</span><b>${c.games.toLocaleString()}</b></div>
      <div class="stat"><span>Systems</span><b>${c.systems}</b></div>
      <div class="stat"><span>Device profiles</span><b>${c.devices}</b></div>
      <div class="actions"><button id="s-scan">Rescan store</button></div>
      <div class="job" id="j-scan"></div>
    </div>
    <div class="card"><h3>IGDB</h3>
      <div class="field"><label>Twitch Client ID</label><input id="s-cid" value="${esc(st.igdb.client_id)}" autocomplete="off"></div>
      <div class="field"><label>Client Secret</label><input id="s-sec" type="password" placeholder="${st.igdb.has_secret ? '•••••••• (saved; type to replace)' : 'not set'}" autocomplete="new-password"></div>
      <div class="actions"><button id="s-igdb-save">Save credentials</button></div>
      <div class="stat"><span>Matched</span><b>${c.matched.toLocaleString()}</b></div>
      <div class="stat"><span>Not found on IGDB</span><b>${c.unmatched.toLocaleString()}</b></div>
      <div class="stat"><span>Never looked up</span><b>${c.pending.toLocaleString()}</b></div>
<div class="stat"><span>Covers from libretro</span><b>${c.libretro.toLocaleString()}</b></div>
<div class="stat"><span>Still no cover</span><b>${c.nocover.toLocaleString()}</b></div>
      <div class="actions">
        <button id="s-scrape" class="${c.pending ? 'primary' : ''}" title="Cover, description, rating, genres, then screenshots and tags">Match ${c.pending ? c.pending.toLocaleString() + ' new' : 'unmatched'} games</button>
        <button id="s-scrape-unmatched" title="Try the ${c.unmatched} games IGDB did not find last time">Retry not-found</button>
        <button id="s-libretro" title="Box art from libretro-thumbnails, matched by No-Intro name, for the ${c.nocover} games with no cover. Never replaces an IGDB cover.">Fill missing covers (libretro)</button>
<button id="s-enrich" title="Screenshots, franchise/theme/mode tags for matched games that lack them">Fetch screenshots &amp; tags</button>
        <button id="s-scrape-all" class="danger" title="Throw away every match and look all ${c.games.toLocaleString()} games up again">Re-match everything</button>
      </div>
      <div class="job" id="j-igdb"></div>
    </div>
    <div class="card"><h3>Linked tags</h3>
      <p class="muted" style="margin:6px 0">Title rules propose a franchise where IGDB gave none (Ultimate Mortal Kombat 3 → Mortal Kombat). Proposals wait for your tick below; nothing is accepted for you.</p>
      <div class="stat"><span>Suggested, awaiting review</span><b id="s-proposed">${c.proposed.toLocaleString()}</b></div>
      <div class="actions"><button id="s-reason">Propose franchise tags</button></div>
      <div class="job" id="j-reason"></div>
    </div>
    <div class="card"><h3>Data</h3>
      <div class="stat"><span>App folder</span><span class="kv" style="text-align:right">${esc(st.app_dir)}</span></div>
      <div class="stat"><span>Database</span><b>${fmtB(st.db.bytes)}</b></div>
      <div class="stat"><span>Covers</span><b>${st.covers.files.toLocaleString()} · ${fmtB(st.covers.bytes)}</b></div>
      <div class="stat"><span>Screenshot cache</span><b>${st.screens.files.toLocaleString()} · ${fmtB(st.screens.bytes)}</b></div>
      <div class="stat"><span>Logs</span><span class="kv" style="text-align:right">${esc(st.data_dir)}\\logs</span></div>
      ${running.length ? `<div class="job">running now: ${esc(running.map(j => j.kind + ' — ' + (j.progress || '')).join('; '))}</div>` : ''}
    </div>
  </div>
  <h2>Suggested tags <span class="muted" id="sugg-count"></span></h2>
  <div id="sugg" class="sugg"><div class="muted">loading…</div></div>`;

  $('#s-store-save').onclick = async () => { try { await api.post('settings', { store_root: $('#s-store').value }); toast('Store root saved'); } catch (e) { toast(e.message, true); } };
  $('#s-igdb-save').onclick = async () => { try { await api.post('settings', { client_id: $('#s-cid').value, client_secret: $('#s-sec').value }); toast('IGDB credentials saved'); $('#s-sec').value = ''; } catch (e) { toast(e.message, true); } };
  $('#s-scan').onclick = () => runJob('scan-store', {}, $('#j-scan'), async () => { await loadLibrary(); renderSettings(); });
  $('#s-scrape').onclick = () => runJob('scrape', {}, $('#j-igdb'), async () => { await loadLibrary(); renderSettings(); });
  $('#s-scrape-unmatched').onclick = () => runJob('scrape', { retry_unmatched: true }, $('#j-igdb'), async () => { await loadLibrary(); renderSettings(); });
  $('#s-libretro').onclick = () => runJob('covers-libretro', {}, $('#j-igdb'), async () => { await loadLibrary(); renderSettings(); });
$('#s-enrich').onclick = () => runJob('enrich', {}, $('#j-igdb'), async () => { await loadLibrary(); renderSettings(); });
  $('#s-scrape-all').onclick = () => {
    modal(`<h3>Re-match everything?</h3><p>Every game's IGDB match, cover, description and IGDB tags are replaced by a fresh lookup. Your own tags and accepted suggestions are kept. This takes about an hour for ${c.games.toLocaleString()} games.</p><div class="actions"><button id="m-no">Cancel</button><button class="danger" id="m-yes">Re-match everything</button></div>`);
    $('#m-no').onclick = closeModal;
    $('#m-yes').onclick = () => { closeModal(); runJob('scrape', { all: true }, $('#j-igdb'), async () => { await loadLibrary(); renderSettings(); }); };
  };
  $('#s-reason').onclick = () => runJob('reason', {}, $('#j-reason'), async () => { await loadLibrary(); renderSettings(); });
  renderSuggestions();
}
async function renderSuggestions() {
  const box = $('#sugg'); if (!box) return;
  const rows = await api.get('tags/proposed');
  $('#sugg-count').textContent = rows.length ? `${rows.length.toLocaleString()} waiting` : '';
  if (!rows.length) { box.innerHTML = '<div class="muted">Nothing waiting for review.</div>'; return; }
  const by = {}; for (const r of rows) (by[r.tag] = by[r.tag] || []).push(r);
  const names = Object.keys(by).sort((a, b) => by[b].length - by[a].length || a.localeCompare(b));
  box.innerHTML = names.map(fr => `<div class="fr" data-fr="${esc(fr)}"><span class="chip kind-suggested">${esc(fr)}</span><b class="muted">${by[fr].length} game${by[fr].length > 1 ? 's' : ''}</b><button data-all="1">Accept all</button><button data-all="0">Reject all</button></div>
    <div class="rows">${by[fr].map(r => `<div class="row2" data-gid="${r.game_id}" data-tag="${esc(r.tag)}"><span class="t">${esc(r.title)}</span><span class="sys">${esc(S.systems[r.system] || r.system)}</span><span class="act"><button data-one="1" title="accept">✓</button> <button data-one="0" title="reject">✗</button></span></div>`).join('')}</div>`).join('');
  box.onclick = async (e) => {
    const b = e.target.closest('button'); if (!b) return;
    try {
      if (b.dataset.all != null) {
        const fr = b.closest('.fr').dataset.fr; const items = by[fr].map(r => ({ game_id: r.game_id, tag: r.tag }));
        await api.post('tags/decide-many', { items, accept: b.dataset.all === '1' });
      } else {
        const row = b.closest('.row2'); await api.post('tag/decide', { game_id: +row.dataset.gid, tag: row.dataset.tag, accept: b.dataset.one === '1' });
      }
      await loadLibrary(); renderSuggestions(); const n = (await api.get('tags/proposed')).length; if ($('#s-proposed')) $('#s-proposed').textContent = n.toLocaleString();
    } catch (err) { toast(err.message, true); }
  };
}

// ------------------------------------------------------------ boot
async function loadLibrary() {
  $('#count').textContent = 'loading library…';
  S.lib = await api.get('library');
  S.systems = S.lib.systems; S.games = S.lib.games; S.games.forEach(prep); S.sortedBy = null;
  buildTwins();
  const sizes = S.games.map(g => g.size).filter(x => x > 0);
  S.sizeLog = { min: Math.log(Math.max(1024, Math.min(...sizes))), max: Math.log(Math.max(...sizes) * 1.05) };
  syncSizeInputs(); syncYearInputs();
  applyFilters();
}
(async function boot() {
  await loadLibrary();
  await loadDevicePicker();
})().catch(e => { $('#count').textContent = e.message; console.error(e); });
