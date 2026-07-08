(function () {
  'use strict';

  const I18N = { en_us: {}, zh_cn: {} };
  let lang = 'zh_cn';
  let games = [];
  let sortCol = 'playtime_hours';
  let sortAsc = false;
  let playtimeFormat = false;

  /* ── Init ─────────────────────────────────────────── */

  async function init() {
    await loadI18n();
    detectLang();
    applyI18n();
    bindEvents();
    loadFromStorage();
  }

  async function loadI18n() {
    for (const code of ['zh_cn', 'en_us']) {
      try {
        const resp = await fetch(`i18n/${code}.json`);
        I18N[code] = await resp.json();
      } catch (e) {
        console.warn(`Failed to load i18n/${code}.json`, e);
      }
    }
  }

  function detectLang() {
    const saved = localStorage.getItem('sle-lang');
    if (saved && I18N[saved]) { lang = saved; return; }
    const nav = navigator.language || '';
    if (nav.startsWith('zh')) lang = 'zh_cn';
    else lang = 'en_us';
  }

  /* ── i18n helpers ────────────────────────────────── */

  function t(key) {
    const gui = I18N[lang] && I18N[lang].gui;
    return (gui && gui[key]) || key;
  }

  function colName(key) {
    const cols = I18N[lang] && I18N[lang].columns;
    return (cols && cols[key]) || key;
  }

  function applyI18n() {
    document.documentElement.lang = lang === 'zh_cn' ? 'zh-CN' : 'en';
    document.title = t('window_title');
    setText('brand', t('window_title'));
    setText('desc', t('web_desc'));
    setText('lbl-api-key', t('label_api_key'));
    setText('lbl-steam-id', t('label_steam_id'));
    setAttr('api-key', 'placeholder', t('web_api_key_placeholder'));
    setAttr('steam-id', 'placeholder', t('web_steam_id_placeholder'));
    setText('btn-export', t('web_btn_export'));
    setText('btn-show-key', t('show_key'));
    setText('btn-csv', t('web_btn_download_csv'));
    setText('btn-json', t('web_btn_download_json'));
    setText('btn-clear', t('web_btn_clear'));
    setAttr('search', 'placeholder', t('web_search_placeholder'));
    setText('link-key', t('web_get_key_link'));
    setText('link-id', t('web_find_id_link'));
    document.getElementById('lang-switcher').value = lang;

    const ths = document.querySelectorAll('#game-table th');
    ths.forEach(th => { th.textContent = colName(th.dataset.col); });
    if (!games.length) setStatus(t('web_msg_no_data'), '');
  }

  function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  function setAttr(id, attr, val) {
    const el = document.getElementById(id);
    if (el) el.setAttribute(attr, val);
  }

  function setStatus(msg, cls) {
    const el = document.getElementById('status-msg');
    el.textContent = msg;
    el.className = 'status-msg ' + (cls || '');
  }

  /* ── Form events ──────────────────────────────────── */

  function bindEvents() {
    document.getElementById('btn-export').addEventListener('click', onExport);
    document.getElementById('export-form').addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); onExport(e); }
    });
    document.getElementById('btn-show-key').addEventListener('click', toggleKeyVisibility);
    document.getElementById('btn-csv').addEventListener('click', () => download('csv'));
    document.getElementById('btn-json').addEventListener('click', () => download('json'));
    document.getElementById('btn-clear').addEventListener('click', clearResults);
    document.getElementById('lang-switcher').addEventListener('change', onLangChange);
    document.getElementById('search').addEventListener('input', onSearch);
    document.querySelectorAll('#game-table th').forEach(th => {
      th.addEventListener('click', () => onSort(th.dataset.col));
    });
    document.getElementById('api-key').addEventListener('change', saveToStorage);
    document.getElementById('steam-id').addEventListener('change', saveToStorage);
  }

  function toggleKeyVisibility() {
    const inp = document.getElementById('api-key');
    const btn = document.getElementById('btn-show-key');
    if (inp.type === 'password') {
      inp.type = 'text';
      btn.textContent = lang === 'zh_cn' ? '隐藏' : 'Hide';
    } else {
      inp.type = 'password';
      btn.textContent = t('show_key');
    }
  }

  async function onExport(e) {
    e.preventDefault();
    const key = document.getElementById('api-key').value.trim();
    const steamid = document.getElementById('steam-id').value.trim();
    if (!key || !steamid) {
      setStatus(t('msg_validation_fail'), 'error');
      return;
    }
    setStatus(t('web_msg_loading'), '');
    saveToStorage();
    try {
      const apiUrl = 'https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/' +
        `?key=${encodeURIComponent(key)}&steamid=${encodeURIComponent(steamid)}` +
        '&include_appinfo=1&include_played_free_games=1&format=json';
      const proxyHost = localStorage.getItem('sle-proxy');
      const fetchUrl = proxyHost
        ? `${proxyHost}?url=${encodeURIComponent(apiUrl)}`
        : apiUrl;
      let resp;
      resp = await fetch(fetchUrl);
      if (!resp.ok) {
        setStatus(t('web_msg_fetch_error'), 'error');
        return;
      }
      const data = await resp.json();
      const raw = (data.response && data.response.games) || [];
      if (!raw.length) {
        setStatus(t('web_msg_empty'), 'error');
        return;
      }
      games = raw.map(g => ({
        appid: g.appid,
        name: g.name || `Unknown (${g.appid})`,
        playtime_hours: roundTo1((g.playtime_forever || 0) / 60),
        playtime_2weeks_hours: roundTo1((g.playtime_2weeks || 0) / 60),
        is_free: g.playtime_forever > 0 && g.playtime_forever <= 5,
        unplayed: (g.playtime_forever || 0) === 0,
      }));
      sortCol = 'playtime_hours';
      sortAsc = false;
      playtimeFormat = true;
      renderAll();
      setStatus(t('msg_export_done') + ` — ${games.length} ${lang === 'zh_cn' ? '个游戏' : 'games'}`, 'success');
    } catch (err) {
      if (!proxyHost && (err.message || '').toLowerCase().includes('networkerror')) {
        setStatus(
          (lang === 'zh_cn'
            ? '浏览器 CORS 限制。请部署免费的 Cloudflare Worker（见 scripts/cors-proxy.js），然后将 Worker URL 填写到下方「代理地址」输入框中。'
            : 'CORS blocked. Deploy the free Cloudflare Worker at scripts/cors-proxy.js, then paste its URL into the Proxy field below.'),
          'error'
        );
      } else {
        setStatus(t('web_msg_fetch_error'), 'error');
      }
      console.error(err);
    }
  }

  function roundTo1(n) { return Math.round(n * 10) / 10; }

  /* ── Render ───────────────────────────────────────── */

  function renderAll() {
    document.getElementById('results').classList.remove('hidden');
    renderSummary();
    renderTable();
  }

  function renderSummary() {
    const total = games.length;
    const played = games.filter(g => !g.unplayed).length;
    const unplayed = total - played;
    const totalH = roundTo1(games.reduce((s, g) => s + g.playtime_hours, 0));

    document.getElementById('summary').innerHTML = `
      <div class="summary-item"><div class="num">${total}</div><div class="lbl">${t('web_summary_total')}</div></div>
      <div class="summary-item"><div class="num">${played}</div><div class="lbl">${t('web_summary_played')}</div></div>
      <div class="summary-item"><div class="num">${unplayed}</div><div class="lbl">${t('web_summary_unplayed')}</div></div>
      <div class="summary-item"><div class="num">${totalH}h</div><div class="lbl">${t('web_summary_playtime')}</div></div>
    `;
  }

  function renderTable() {
    const q = document.getElementById('search').value.trim().toLowerCase();
    let filtered = games;
    if (q) filtered = games.filter(g => g.name.toLowerCase().includes(q));

    const sorted = [...filtered].sort((a, b) => {
      let va = a[sortCol], vb = b[sortCol];
      if (typeof va === 'string') va = va.toLowerCase();
      if (typeof vb === 'string') vb = vb.toLowerCase();
      if (va < vb) return sortAsc ? -1 : 1;
      if (va > vb) return sortAsc ? 1 : -1;
      return 0;
    });

    const tbody = document.querySelector('#game-table tbody');
    tbody.innerHTML = sorted.map(g => {
      const nameHtml = escapeHtml(g.name) +
        (g.is_free ? ` <span class="tag tag-free">${t('web_msg_free_game')}</span>` : '') +
        (g.unplayed ? ` <span class="tag tag-unplayed">${t('web_msg_unplayed_game')}</span>` : '');
      return `<tr>
        <td>${g.appid}</td>
        <td>${nameHtml}</td>
        <td class="num-cell">${fmtPlaytime(g.playtime_hours)}</td>
        <td class="num-cell">${fmtPlaytime(g.playtime_2weeks_hours)}</td>
      </tr>`;
    }).join('');

    updateSortArrows();
  }

  function fmtPlaytime(h) {
    if (!playtimeFormat) return h.toFixed(1);
    return h >= 1 ? h.toFixed(1) + ' h' : (h > 0 ? (h * 60).toFixed(0) + ' min' : '—');
  }

  function escapeHtml(str) {
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  }

  function updateSortArrows() {
    document.querySelectorAll('#game-table th').forEach(th => {
      const arrow = th.querySelector('.sort-arrow');
      if (arrow) arrow.remove();
      if (th.dataset.col === sortCol) {
        const span = document.createElement('span');
        span.className = 'sort-arrow';
        span.textContent = sortAsc ? '▲' : '▼';
        th.appendChild(span);
      }
    });
  }

  /* ── Sort & Search ────────────────────────────────── */

  function onSort(col) {
    if (col === sortCol) {
      sortAsc = !sortAsc;
    } else {
      sortCol = col;
      sortAsc = false;
    }
    playtimeFormat = (col === 'playtime_hours' || col === 'playtime_2weeks_hours');
    renderTable();
  }

  function onSearch() { renderTable(); }

  /* ── Download ─────────────────────────────────────── */

  function download(fmt) {
    setStatus(t('web_msg_exporting'), '');
    const cols = ['appid', 'name', 'playtime_hours', 'playtime_2weeks_hours'];
    const headers = cols.map(colName);
    let content, mime, ext;

    if (fmt === 'csv') {
      const rows = [headers.map(h => `"${h}"`).join(',')];
      for (const g of games) {
        rows.push(cols.map(c => `"${String(g[c] !== undefined ? g[c] : '').replace(/"/g, '""')}"`).join(','));
      }
      content = '\uFEFF' + rows.join('\n');
      mime = 'text/csv;charset=utf-8';
      ext = 'csv';
    } else {
      const out = games.map(g => {
        const obj = {};
        cols.forEach((c, i) => { obj[headers[i]] = g[c]; });
        return obj;
      });
      content = JSON.stringify(out, null, 2);
      mime = 'application/json';
      ext = 'json';
    }

    const blob = new Blob([content], { type: mime });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `steam_library.${ext}`;
    a.click();
    URL.revokeObjectURL(a.href);
    setStatus(t('msg_export_done') + ` — ${games.length} ${lang === 'zh_cn' ? '个游戏' : 'games'}`, 'success');
  }

  /* ── Clear ────────────────────────────────────────── */

  function clearResults() {
    games = [];
    sortCol = 'playtime_hours';
    sortAsc = false;
    document.getElementById('results').classList.add('hidden');
    document.querySelector('#game-table tbody').innerHTML = '';
    document.getElementById('search').value = '';
    document.getElementById('summary').innerHTML = '';
    setStatus(t('web_msg_no_data'), '');
  }

  /* ── Language ─────────────────────────────────────── */

  function onLangChange() {
    lang = document.getElementById('lang-switcher').value;
    localStorage.setItem('sle-lang', lang);
    applyI18n();
    if (games.length) renderAll();
  }

  /* ── Persistence ──────────────────────────────────── */

  function loadFromStorage() {
    const key = localStorage.getItem('sle-api-key');
    const sid = localStorage.getItem('sle-steam-id');
    if (key) document.getElementById('api-key').value = key;
    if (sid) document.getElementById('steam-id').value = sid;
    localStorage.setItem('sle-proxy', 'https://dark-morning-0609.funny-entity.workers.dev');
  }

  function saveToStorage() {
    localStorage.setItem('sle-api-key', document.getElementById('api-key').value.trim());
    localStorage.setItem('sle-steam-id', document.getElementById('steam-id').value.trim());
    localStorage.setItem('sle-proxy', 'https://dark-morning-0609.funny-entity.workers.dev');
  }

  /* ── Boot ─────────────────────────────────────────── */

  init();
})();
