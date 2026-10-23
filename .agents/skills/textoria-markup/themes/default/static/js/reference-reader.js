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
    ['座標', formatCoords(item)],
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

function formatCoords(item) {
  const x = Number(item.x_coord);
  const y = Number(item.y_coord);
  if (!Number.isFinite(x) || !Number.isFinite(y) || (x === 0 && y === 0)) return '';
  return `${y}, ${x}`;
}

function renderMap(item) {
  const section = document.getElementById('mapSection');
  const message = document.getElementById('mapMessage');
  const mapEl = document.getElementById('map');
  const x = Number(item.x_coord);
  const y = Number(item.y_coord);
  if (!Number.isFinite(x) || !Number.isFinite(y) || (x === 0 && y === 0)) {
    if (item.entity_type === 'place') {
      section.hidden = false;
      mapEl.hidden = true;
      message.hidden = false;
      message.textContent = '此 CBDB 地名記錄未提供可用 GIS 座標，因此不顯示地圖。';
    } else {
      section.hidden = true;
    }
    return;
  }
  section.hidden = false;
  mapEl.hidden = false;
  message.hidden = true;
  activeMapPoint = {lat: y, lng: x, label: item.canonical_name, sourceId: item.source_id || ''};
  setTimeout(() => {
    if (!window.L) {
      message.hidden = false;
      message.textContent = 'Leaflet 尚未載入。若以本機檔案開啟，請確認瀏覽器可連線到 Leaflet CDN 與 OpenStreetMap tile server。';
      return;
    }
    if (!map) {
      map = L.map('map', {scrollWheelZoom: false});
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 18,
        attribution: '&copy; OpenStreetMap contributors'
      }).addTo(map);
    }
    map.setView([y, x], 8, {animate: true});
    if (marker) marker.remove();
    marker = L.marker([y, x]).addTo(map).bindPopup(`${esc(item.canonical_name)}<br>CBDB:${esc(item.source_id || '')}`);
    marker.openPopup();
    refreshMapView();
    setTimeout(refreshMapView, 260);
  }, 80);
}

function refreshMapView() {
  if (!map || !activeMapPoint) return;
  const point = [activeMapPoint.lat, activeMapPoint.lng];
  map.invalidateSize({pan: false});
  map.setView(point, map.getZoom() || 8, {animate: false});
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

