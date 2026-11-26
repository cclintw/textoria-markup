const authorityById = new Map(AUTHORITY.map(item => [item.authority_id, item]));
let map = null;
let marker = null;
let activeMapPoint = null;
const icons = {
  leftExpand: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="M4 6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6z"/><path d="M9 4v16"/><path d="M14 10l2 2-2 2"/></svg>',
  leftCollapse: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="M4 6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6z"/><path d="M9 4v16"/><path d="M15 10l-2 2 2 2"/></svg>',
  rightExpand: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="M4 6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6z"/><path d="M15 4v16"/><path d="M10 10l-2 2 2 2"/></svg>',
  rightCollapse: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="M4 6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6z"/><path d="M15 4v16"/><path d="M9 10l2 2-2 2"/></svg>'
};

const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
}[char]));

function countMentions() {
  const counts = new Map();
  document.querySelectorAll('.entity[data-authority-id]').forEach(node => {
    const id = node.dataset.authorityId;
    counts.set(id, (counts.get(id) || 0) + 1);
  });
  return counts;
}

function initStats(counts) {
  const typeCounts = {person: 0, place: 0, office: 0, reign: 0};
  let totalMentions = 0;
  AUTHORITY.forEach(item => {
    const count = counts.get(item.authority_id) || 0;
    totalMentions += count;
    if (item.entity_type in typeCounts) typeCounts[item.entity_type] += count;
  });
  document.getElementById('totalEntities').textContent = AUTHORITY.length;
  document.getElementById('totalMentions').textContent = totalMentions;
  Object.entries(typeCounts).forEach(([type, count]) => {
    const target = document.querySelector(`[data-type-count="${type}"]`);
    if (target) target.textContent = count;
  });
}

function initFrequencyList(counts) {
  const list = document.getElementById('frequencyList');
  const rows = AUTHORITY
    .map(item => ({...item, count: counts.get(item.authority_id) || 0}))
    .filter(item => item.count > 0)
    .sort((a, b) => b.count - a.count || String(a.entity_text || '').localeCompare(String(b.entity_text || ''), 'zh-Hant'));
  list.innerHTML = rows.map(item => {
    const name = item.canonical_name && item.canonical_name !== item.entity_text
      ? `${item.entity_text} → ${item.canonical_name}`
      : item.entity_text;
    return `
      <li>
        <button class="freq-btn" type="button" data-authority-id="${esc(item.authority_id)}">
          <span class="freq-name">${esc(name)}</span>
          <span class="freq-count">${item.count}</span>
        </button>
      </li>
    `;
  }).join('');
  list.querySelectorAll('[data-authority-id]').forEach(btn => {
    btn.addEventListener('click', () => selectAuthority(btn.dataset.authorityId, true));
  });
}

function initEntityClicks() {
  document.querySelectorAll('.entity[data-authority-id]').forEach(node => {
    node.addEventListener('click', event => {
      event.stopPropagation();
      selectAuthority(node.dataset.authorityId, false, node);
    });
  });
}

function selectAuthority(authorityId, scrollToFirst = false, sourceNode = null) {
  const item = authorityById.get(authorityId);
  if (!item) return;
  expandRightPanel();
  document.querySelectorAll('.entity.is-selected').forEach(node => node.classList.remove('is-selected'));
  const matches = document.querySelectorAll(`.entity[data-authority-id="${CSS.escape(authorityId)}"]`);
  matches.forEach(node => node.classList.add('is-selected'));
  if (scrollToFirst && matches[0]) {
    matches[0].scrollIntoView({block: 'center'});
  } else if (sourceNode) {
    sourceNode.classList.add('is-selected');
  }
  renderDetail(item, matches.length);
}

function expandRightPanel() {
  if (!document.body.classList.contains('right-collapsed')) return;
  document.body.classList.remove('right-collapsed');
  updatePanelToggleIcons();
  if (map) setTimeout(() => map.invalidateSize(), 240);
}

function renderDetail(item, count) {
  const rows = [
    ['原文', item.entity_text],
    ['類型', typeLabel(item.entity_type)],
    ['CBDB 名稱', item.canonical_name],
    ['CBDB ID', item.source_id],
    ['出現次數', count],
    ['朝代', item.dynasty],
    ['Index year', item.index_year],
    ['生卒', formatLife(item)],
    ['職官拼音', item.office_pinyin],
    ['職官譯名', item.office_translation],
    ['說明', item.note],
  ].filter(([, value]) => value !== undefined && value !== null && value !== '');
  const sourceUrl = item.source_url
    ? `<tr><th>參考來源</th><td><a href="${esc(item.source_url)}" target="_blank" rel="noreferrer">開啟 CBDB</a></td></tr>`
    : '';
  const heading = esc(item.canonical_name || item.entity_text);
  document.getElementById('detail').className = '';
  document.getElementById('detail').innerHTML = `
    <h4 class="detail-title">${heading}</h4>
    <div class="detail-subtitle">${esc(item.source || 'CBDB')}:${esc(item.source_id || '')} / ${esc(item.authority_id)}</div>
    <table class="detail-table">
      ${rows.map(([label, value]) => `<tr><th>${esc(label)}</th><td>${esc(value)}</td></tr>`).join('')}
      ${sourceUrl}
    </table>
  `;
  renderMap(item);
}

function typeLabel(type) {
  return {person: '人物', place: '地點', office: '職官', reign: '年號'}[type] || type;
}

function formatLife(item) {
  if (!item.birth_year && !item.death_year) return '';
  return `${item.birth_year || '?'}-${item.death_year || '?'}`;
}

let leafletAssets;
function loadLeaflet() {
  if (!leafletAssets) {
    const base = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet';
    const assets = [document.createElement('link'), document.createElement('script')];
    const [style, script] = assets;
    style.rel = 'stylesheet';
    style.href = base + '.css';
    style.integrity = 'sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=';
    script.src = base + '.js';
    script.integrity = 'sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=';
    leafletAssets = Promise.all(assets.map(asset => new Promise((resolve, reject) => {
      asset.crossOrigin = 'anonymous';
      asset.onload = resolve;
      asset.onerror = reject;
      document.head.append(asset);
    }))).catch(error => {
      assets.forEach(asset => asset.remove());
      leafletAssets = null;
      throw error;
    });
  }
  return leafletAssets;
}

async function renderMap(item) {
  const section = document.getElementById('mapSection');
  const mapEl = document.getElementById('map');
  const {latitude: lat, longitude: lng, source, source_id: sourceId} = item?.location || {};
  activeMapPoint = null;
  section.hidden = true;
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;
  // File URLs cannot send the HTTP referrer required by the OSM tile service.
  if (!['https:', 'http:'].includes(window.location.protocol)) return;
  const point = {lat, lng};
  activeMapPoint = point;
  try {
    await loadLeaflet();
  } catch {
    return;
  }
  if (activeMapPoint !== point) return;
  section.hidden = false;
  if (!map) {
    map = L.map(mapEl, {scrollWheelZoom: false});
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    new ResizeObserver(refreshMapView).observe(mapEl);
  }
  map.setView([lat, lng], 8, {animate: false});
  if (marker) marker.remove();
  const popup = document.createElement('div');
  popup.textContent = item.canonical_name;
  const label = [source, sourceId].filter(Boolean).join(' · ');
  if (label) popup.append(document.createElement('br'), label);
  marker = L.marker([lat, lng]).addTo(map).bindPopup(popup);
  refreshMapView();
}

function refreshMapView() {
  if (!map || !activeMapPoint || !map.getContainer().getBoundingClientRect().width) return;
  map.invalidateSize({pan: false});
  if (marker) marker.openPopup();
}

function initTypeBadges() {
  document.querySelectorAll('.type-badge[data-type]').forEach(btn => {
    btn.addEventListener('click', () => {
      const type = btn.dataset.type;
      btn.classList.toggle('is-off');
      document.body.classList.toggle(`hide-${type}`, btn.classList.contains('is-off'));
    });
  });
}

function initChapterSpy() {
  const links = new Map([...document.querySelectorAll('[data-chapter-link]')].map(link => [link.dataset.chapterLink, link]));
  const observer = new IntersectionObserver(entries => {
    const visible = entries
      .filter(entry => entry.isIntersecting)
      .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
    if (!visible) return;
    links.forEach(link => link.classList.remove('active'));
    const link = links.get(visible.target.id);
    if (link) link.classList.add('active');
  }, {rootMargin: '-80px 0px -72% 0px', threshold: 0.01});
  document.querySelectorAll('article[id]').forEach(article => observer.observe(article));
}

function initPanelToggles() {
  const left = document.getElementById('toggleLeft');
  const right = document.getElementById('toggleRight');
  collapsePanelsOnSmallScreen();
  left.addEventListener('click', () => {
    document.body.classList.toggle('left-collapsed');
    updatePanelToggleIcons();
  });
  right.addEventListener('click', () => {
    document.body.classList.toggle('right-collapsed');
    updatePanelToggleIcons();
    if (!document.body.classList.contains('right-collapsed') && map) {
      setTimeout(refreshMapView, 240);
    }
  });
  window.addEventListener('resize', syncPanelDrawerState);
  updatePanelToggleIcons();
}

function collapsePanelsOnSmallScreen() {
  if (!window.matchMedia('(max-width: 1120px)').matches) return;
  document.body.classList.add('left-collapsed', 'right-collapsed');
}

function collapseLeftPanelOnSmallScreen() {
  if (!window.matchMedia('(max-width: 1120px)').matches) return;
  document.body.classList.add('left-collapsed');
  updatePanelToggleIcons();
}

function initMobileChapterLinks() {
  document.querySelectorAll('[data-chapter-link]').forEach(link => {
    link.addEventListener('click', collapseLeftPanelOnSmallScreen);
  });
}

function updatePanelToggleIcons() {
  const left = document.getElementById('toggleLeft');
  const right = document.getElementById('toggleRight');
  if (!left || !right) return;
  const leftCollapsed = document.body.classList.contains('left-collapsed');
  const rightCollapsed = document.body.classList.contains('right-collapsed');
  document.querySelector('.chapter-panel')?.classList.toggle('is-collapsed', leftCollapsed);
  document.querySelector('.inspector')?.classList.toggle('is-collapsed', rightCollapsed);
  syncPanelDrawerState();
  left.innerHTML = leftCollapsed ? icons.leftExpand : icons.leftCollapse;
  right.innerHTML = rightCollapsed ? icons.rightExpand : icons.rightCollapse;
  left.setAttribute('aria-expanded', String(!leftCollapsed));
  right.setAttribute('aria-expanded', String(!rightCollapsed));
}

function syncPanelDrawerState() {
  const chapters = document.querySelector('.chapter-panel');
  const inspector = document.querySelector('.inspector');
  if (!chapters || !inspector) return;
  const narrow = window.matchMedia('(max-width: 1120px)').matches;
  const leftCollapsed = document.body.classList.contains('left-collapsed');
  const rightCollapsed = document.body.classList.contains('right-collapsed');
  if (!narrow) {
    [chapters, inspector].forEach(panel => {
      panel.style.transform = '';
      panel.style.opacity = '';
      panel.style.pointerEvents = '';
      panel.style.width = '';
      panel.style.padding = '';
      panel.style.borderWidth = '';
      panel.style.overflow = '';
    });
    return;
  }
  chapters.style.transform = leftCollapsed ? 'translateX(-100%)' : 'translateX(0)';
  chapters.style.opacity = leftCollapsed ? '0' : '1';
  chapters.style.pointerEvents = leftCollapsed ? 'none' : 'auto';
  chapters.style.width = leftCollapsed ? '0px' : 'min(84vw, 340px)';
  chapters.style.padding = leftCollapsed ? '0px' : '12px';
  chapters.style.borderWidth = leftCollapsed ? '0px' : '';
  chapters.style.overflow = 'auto';
  inspector.style.transform = rightCollapsed ? 'translateX(100%)' : 'translateX(0)';
  inspector.style.opacity = rightCollapsed ? '0' : '1';
  inspector.style.pointerEvents = rightCollapsed ? 'none' : 'auto';
  inspector.style.width = rightCollapsed ? '0px' : 'min(84vw, 340px)';
  inspector.style.padding = rightCollapsed ? '0px' : '14px';
  inspector.style.borderWidth = rightCollapsed ? '0px' : '';
  inspector.style.overflow = 'auto';
}

