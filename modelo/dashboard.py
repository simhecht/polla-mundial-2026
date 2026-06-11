"""
dashboard.py — v3.4 UI limpia
Genera dashboard HTML con grupos y bracket eliminatorio espejado (estilo torneo).
"""
import sqlite3, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from predictor_v3 import simulate_group, simulate_group_mc, DB_PATH, regenerate_db
from simulate_knockout import get_bracket_data

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "dashboard_mundial2026.html")
GROUPS   = list("ABCDEFGHIJKL")
MC_SIMS  = 20_000

CONF_COLORS = {
    "UEFA":"#3b82f6","CONMEBOL":"#10b981","CONCACAF":"#f59e0b",
    "AFC":"#ef4444","CAF":"#8b5cf6","OFC":"#6b7280",
}
FLAG_EMOJIS = {
    "Mexico":"🇲🇽","South Korea":"🇰🇷","South Africa":"🇿🇦","Czechia":"🇨🇿",
    "Canada":"🇨🇦","Bosnia":"🇧🇦","Qatar":"🇶🇦","Switzerland":"🇨🇭",
    "Brazil":"🇧🇷","Morocco":"🇲🇦","Haiti":"🇭🇹","Scotland":"🏴󠁧󠁢󠁳󠁣󠁴󠁿",
    "USA":"🇺🇸","Paraguay":"🇵🇾","Australia":"🇦🇺","Turkey":"🇹🇷",
    "Germany":"🇩🇪","Curacao":"🇨🇼","Ivory Coast":"🇨🇮","Ecuador":"🇪🇨",
    "Netherlands":"🇳🇱","Japan":"🇯🇵","Sweden":"🇸🇪","Tunisia":"🇹🇳",
    "Belgium":"🇧🇪","Egypt":"🇪🇬","Iran":"🇮🇷","New Zealand":"🇳🇿",
    "Spain":"🇪🇸","Saudi Arabia":"🇸🇦","Uruguay":"🇺🇾","Cabo Verde":"🇨🇻",
    "France":"🇫🇷","Senegal":"🇸🇳","Norway":"🇳🇴","Iraq":"🇮🇶",
    "Argentina":"🇦🇷","Algeria":"🇩🇿","Austria":"🇦🇹","Jordan":"🇯🇴",
    "Portugal":"🇵🇹","DR Congo":"🇨🇩","Uzbekistan":"🇺🇿","Colombia":"🇨🇴",
    "England":"🏴󠁧󠁢󠁥󠁮󠁧󠁿","Croatia":"🇭🇷","Ghana":"🇬🇭","Panama":"🇵🇦",
}
# Códigos FIFA (3 letras) — usados en partidos y bracket para ahorrar espacio
TEAM_CODES = {
    "Mexico":"MEX","South Korea":"KOR","South Africa":"RSA","Czechia":"CZE",
    "Canada":"CAN","Bosnia":"BIH","Qatar":"QAT","Switzerland":"SUI",
    "Brazil":"BRA","Morocco":"MAR","Haiti":"HAI","Scotland":"SCO",
    "USA":"USA","Paraguay":"PAR","Australia":"AUS","Turkey":"TUR",
    "Germany":"GER","Curacao":"CUW","Ivory Coast":"CIV","Ecuador":"ECU",
    "Netherlands":"NED","Japan":"JPN","Sweden":"SWE","Tunisia":"TUN",
    "Belgium":"BEL","Egypt":"EGY","Iran":"IRN","New Zealand":"NZL",
    "Spain":"ESP","Saudi Arabia":"KSA","Uruguay":"URU","Cabo Verde":"CPV",
    "France":"FRA","Senegal":"SEN","Norway":"NOR","Iraq":"IRQ",
    "Argentina":"ARG","Algeria":"ALG","Austria":"AUT","Jordan":"JOR",
    "Portugal":"POR","DR Congo":"COD","Uzbekistan":"UZB","Colombia":"COL",
    "England":"ENG","Croatia":"CRO","Ghana":"GHA","Panama":"PAN",
}
HOST_TEAMS = {"Mexico","USA","Canada"}

# ---------------------------------------------------------------------------
# UI de edición (solo modo interactivo, servida por app.py)
# ---------------------------------------------------------------------------
EDIT_CSS = """
/* ── UI de edición (modo interactivo) ── */
.edit-bar{position:fixed;top:.8rem;right:.8rem;z-index:1000;display:flex;align-items:center;gap:.5rem;background:rgba(30,41,59,.92);border:1px solid var(--border);border-radius:999px;padding:.3rem .5rem .3rem .9rem;font-size:.74rem;color:var(--muted);box-shadow:0 4px 16px rgba(0,0,0,.35);backdrop-filter:blur(8px)}
.edit-bar button{background:transparent;color:var(--text);border:1px solid var(--border);border-radius:999px;padding:.22rem .75rem;font-size:.72rem;cursor:pointer;transition:border-color .15s ease,color .15s ease,transform .12s ease}
.edit-bar button:hover{border-color:var(--accent);color:var(--accent)}
.edit-bar button:active{transform:scale(.96)}
.edit-bar button:disabled{opacity:.5;cursor:wait}
.edit-btn{background:none;border:none;cursor:pointer;font-size:.72rem;padding:0 .1rem;opacity:0;transition:opacity .15s ease;line-height:1}
.match-block:hover .edit-btn,.ko-card:hover .edit-btn{opacity:.75}
.edit-btn:hover{opacity:1!important}
"""

EDIT_JS = r"""
/* ── Modo interactivo: edición de resultados (servido por app.py) ── */
const jsq = s => String(s).replace(/\\/g, '\\\\').replace(/'/g, "\\'");

editGroupControls = r => {
  const edit = `<button class="edit-btn" title="Editar marcador" onclick="editMatch('group','${jsq(r.home_raw)}','${jsq(r.away_raw)}','${jsq(r.home)}','${jsq(r.away)}','${r.score}')">✏️</button>`;
  const clear = r.manual ? `<button class="edit-btn" title="Borrar este override" onclick="clearMatch('${jsq(r.home_raw)}','${jsq(r.away_raw)}')">🗑️</button>` : '';
  return edit + clear;
};

editKoControls = m => {
  const edit = `<button class="edit-btn" title="Editar marcador" onclick="editMatch('ko','${jsq(m.home)}','${jsq(m.away)}','${jsq(m.home_es)}','${jsq(m.away_es)}','${m.score}')">✏️</button>`;
  const clear = m.manual ? `<button class="edit-btn" title="Borrar este override" onclick="clearMatch('${jsq(m.home)}','${jsq(m.away)}')">🗑️</button>` : '';
  return edit + clear;
};

async function apiPost(path, body) {
  try {
    const res = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'},
                                   body: JSON.stringify(body)});
    const data = await res.json();
    if (!data.ok) { alert('Error: ' + (data.error || 'desconocido')); return null; }
    return data;
  } catch (e) {
    alert('Error de conexión con el servidor local: ' + e);
    return null;
  }
}

function parseScore(txt) {
  if (txt == null) return null;            // cancelado
  const m = txt.trim().match(/^(\d+)\s*[-:]\s*(\d+)$/);
  if (!m) { alert('Formato inválido. Usa por ejemplo: 2-1'); return null; }
  return [parseInt(m[1], 10), parseInt(m[2], 10)];
}

async function editMatch(scope, homeRaw, awayRaw, homeEs, awayEs, current) {
  const txt = prompt(`Marcador para ${homeEs} vs ${awayEs} (formato 2-1):`, current || '');
  const sc = parseScore(txt);
  if (!sc) return;
  let advancer = null;
  if (scope === 'ko' && sc[0] === sc[1]) {
    const a = prompt(`Empate ${sc[0]}-${sc[1]}: ¿quién avanza (prórroga/penales)?\nEscribe "${homeEs}" o "${awayEs}":`);
    if (a == null) return;
    const t = a.trim().toLowerCase();
    if (t === homeEs.toLowerCase() || t === homeRaw.toLowerCase()) advancer = homeRaw;
    else if (t === awayEs.toLowerCase() || t === awayRaw.toLowerCase()) advancer = awayRaw;
    else { alert('Equipo no reconocido. Debe ser uno de los dos del partido.'); return; }
  }
  const r = await apiPost('/api/override',
    {scope, home: homeRaw, away: awayRaw, gh: sc[0], ga: sc[1], advancer});
  if (r) location.reload();
}

async function clearMatch(homeRaw, awayRaw) {
  const r = await apiPost('/api/clear', {home: homeRaw, away: awayRaw});
  if (r) location.reload();
}

async function clearAllOverrides() {
  if (!confirm('¿Borrar TODOS los overrides manuales?')) return;
  const r = await apiPost('/api/clear', {all: true});
  if (r) location.reload();
}

async function recalcMC() {
  const btn = document.getElementById('recalcBtn');
  btn.disabled = true; btn.textContent = 'Recalculando…';
  const r = await apiPost('/api/recalc-mc', {});
  if (r) { location.reload(); return; }
  btn.disabled = false; btn.textContent = 'Recalcular';
}

/* Barra superior fija: contador de overrides + acciones globales */
(function () {
  let n = 0;
  GROUPS_DATA.forEach(g => g.results.forEach(r => { if (r.manual) n++; }));
  Object.values(BRACKET_DATA.rounds).forEach(ms => ms.forEach(m => { if (m.manual) n++; }));
  const bar = document.createElement('div');
  bar.className = 'edit-bar';
  bar.innerHTML = `<span>✏️ ${n} override${n === 1 ? '' : 's'}</span>
    ${n > 0 ? '<button onclick="clearAllOverrides()">Limpiar</button>' : ''}
    <button id="recalcBtn" onclick="recalcMC()" title="Recalcular Monte Carlo del bracket">Recalcular</button>`;
  document.body.appendChild(bar);
})();
"""

# ---------------------------------------------------------------------------
# CSS base del dashboard
# ---------------------------------------------------------------------------
BASE_CSS = """
:root {
  --bg:#0f172a;--card:#1e293b;--border:#334155;
  --text:#f1f5f9;--muted:#94a3b8;--accent:#f59e0b;
  --green:#10b981;--red:#ef4444;--blue:#3b82f6;--host:#f97316;
  --line:#475569;
  --ease-out:cubic-bezier(0.23,1,0.32,1);
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif}
header{padding:2.2rem 1rem 1.4rem;text-align:center}
header h1{font-size:1.7rem;font-weight:700;letter-spacing:.5px}
header h1 em{font-style:normal;color:var(--accent)}
header p{color:var(--muted);margin-top:.35rem;font-size:.85rem}
.container{max-width:1440px;margin:0 auto;padding:0 1.5rem 2rem}

/* ── Tabs ── */
.tab-bar{display:flex;gap:.4rem;margin-bottom:1.6rem;justify-content:center;flex-wrap:wrap}
.tab{padding:.45rem 1.3rem;border-radius:999px;border:1px solid transparent;cursor:pointer;font-size:.85rem;color:var(--muted);transition:color .15s var(--ease-out),background-color .15s var(--ease-out)}
.tab:hover{color:var(--text)}
.tab:active{transform:scale(.97)}
.tab.active{background:var(--card);color:var(--text);border-color:var(--border);font-weight:600}
.tab-content{display:none}.tab-content.active{display:block}

/* ── Grupos ── */
.groups-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(350px,1fr));gap:1.2rem}
.group-card{background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden}
.group-header{padding:.55rem 1rem;display:flex;align-items:baseline;gap:.5rem;border-bottom:1px solid var(--border)}
.group-label{font-size:.68rem;text-transform:uppercase;letter-spacing:2px;color:var(--muted)}
.group-letter{font-size:1.15rem;font-weight:800;color:var(--accent)}
.standings-table{width:100%;border-collapse:collapse;font-size:.8rem}
.standings-table th{padding:.35rem .45rem;color:var(--muted);text-align:right;font-weight:500;font-size:.66rem;text-transform:uppercase;letter-spacing:.5px}
.standings-table th:first-child{text-align:left;padding-left:1rem}
.standings-table td{padding:.4rem .45rem;border-top:1px solid rgba(51,65,85,.5);text-align:right}
.standings-table td:first-child{text-align:left;padding-left:1rem}
.standings-table tr.qualified td{background:rgba(16,185,129,.08)}
.standings-table tr.qualified-3rd td{background:rgba(245,158,11,.06)}
.team-name{display:flex;align-items:center;gap:.4rem;font-weight:500;white-space:nowrap}
.pts{font-weight:700;color:var(--accent)}
.mc-pct{font-size:.72rem;color:var(--green);font-weight:600}
.mc-pct.low{color:var(--muted);font-weight:500}

/* ── Partidos ── */
.matches-section{padding:.3rem 1rem .55rem;border-top:1px solid var(--border)}
.match-block{display:grid;grid-template-columns:1fr 4rem 1fr;column-gap:.6rem;align-items:center;padding:.5rem .35rem;border-bottom:1px solid rgba(51,65,85,.45)}
.match-block:last-child{border-bottom:none}
.match-block.match-manual{background:rgba(245,158,11,.05);border-radius:8px}
.m-prob{font-size:.64rem;color:var(--muted)}
.m-prob.ph{text-align:right}
.m-prob.pd{text-align:center}
.m-prob.pa{text-align:left}
.m-team{display:flex;align-items:center;gap:.35rem;font-size:.8rem;font-weight:600;letter-spacing:.5px}
.m-team.home{justify-content:flex-end}
.m-flag{font-size:1rem}
.m-score{text-align:center;font-weight:700;color:var(--accent);background:rgba(51,65,85,.6);border-radius:6px;padding:2px 0;font-size:.85rem}
.m-sub{grid-column:2;text-align:center;font-size:.66rem;color:var(--green);font-weight:600;margin-top:3px;min-height:.9em}
.m-actions{grid-column:3;display:flex;gap:.2rem;align-items:center;margin-top:3px}

/* ── Campeón ── */
.champion-card{background:linear-gradient(135deg,rgba(245,158,11,.12),rgba(16,185,129,.05));border:1px solid var(--accent);border-radius:12px;padding:1.2rem 1.6rem;margin-bottom:1.6rem;display:flex;align-items:center;gap:2.5rem;flex-wrap:wrap}
.champion-info{display:flex;align-items:center;gap:1rem}
.champion-trophy{font-size:2.2rem}
.champion-info h2{font-size:1.25rem;color:var(--accent)}
.champion-info p{color:var(--muted);font-size:.8rem;margin-top:.2rem}
.odds-grid{display:flex;gap:1.5rem;flex-wrap:wrap;flex:1}
.odds-row{flex:1;min-width:220px;max-width:340px}
.odds-team{display:flex;align-items:center;gap:.5rem;margin-bottom:.3rem;font-size:.8rem}
.odds-flag{width:1.4em;text-align:center}
.odds-name{flex:1;font-weight:500}
.odds-prob{font-weight:700;color:var(--accent);min-width:3.5em;text-align:right}
.odds-bar-bg{background:var(--border);border-radius:3px;height:4px;margin-bottom:.55rem;overflow:hidden}
.odds-bar-fill{height:100%;border-radius:3px;background:linear-gradient(90deg,var(--accent),var(--green))}

/* ── Bracket espejado ── */
.bracket-wrap{overflow-x:auto;padding-bottom:1rem}
#bracketRounds{position:relative;margin:0 auto}
.bk-hdr{position:absolute;top:0;text-align:center;font-size:.64rem;text-transform:uppercase;letter-spacing:1.5px;color:var(--muted);font-weight:600}
.bk-line{position:absolute;background:var(--line)}
.ko-card{position:absolute;background:var(--card);border:1px solid var(--border);border-radius:8px;font-size:.72rem;overflow:hidden;transition:border-color .15s ease}
.ko-card:hover{border-color:var(--accent);z-index:10}
.ko-card.ko-final{border-color:var(--accent);box-shadow:0 0 14px rgba(245,158,11,.18)}
.ko-card.ko-manual{border-color:var(--accent);background:rgba(245,158,11,.07)}
.ko-team{display:flex;align-items:center;gap:.3rem;padding:4px 8px 0}
.ko-flag{flex-shrink:0}
.ko-name{flex:1;font-weight:600;letter-spacing:.5px;overflow:hidden;white-space:nowrap}
.ko-pct{font-size:.66rem;color:var(--muted);white-space:nowrap}
.ko-team.winner .ko-name{color:var(--accent)}
.ko-team.winner .ko-pct{color:var(--green);font-weight:700}
.ko-score{text-align:center;font-size:.64rem;color:var(--muted);margin-top:3px;padding:2px 4px;border-top:1px solid rgba(51,65,85,.5);white-space:nowrap}
.ko-score .ko-res{color:var(--text);font-weight:700}
.ko-ev{color:var(--green);font-weight:600}

/* ── Metodología ── */
.method{max-width:700px;line-height:1.7;color:var(--muted)}
.method h3{color:var(--text);margin-bottom:1rem}
.method p{margin-bottom:1rem}
.method strong{color:var(--accent)}

/* ── Ayuda (abajo de todo) ── */
.help-box{background:var(--card);border:1px solid var(--border);border-radius:10px;font-size:.8rem;color:var(--muted);margin-top:2.5rem}
.help-box summary{cursor:pointer;padding:.8rem 1.2rem;color:var(--text);font-weight:600;font-size:.85rem;user-select:none;list-style-position:inside}
.help-box ul{list-style:none;padding:.2rem 1.3rem 1rem;display:flex;flex-direction:column;gap:.5rem;line-height:1.5}
.help-box b{color:var(--text);font-weight:600}

footer{text-align:center;padding:1.6rem;color:var(--muted);font-size:.75rem;margin-top:1rem}
"""

# ---------------------------------------------------------------------------
# JS base del dashboard (render de grupos, campeón y bracket espejado)
# ---------------------------------------------------------------------------
BASE_JS = r"""
function getFlag(name) { return FLAGS[name] || '🏳'; }
function getCode(name) { return CODES[name] || (name || '').substring(0, 3).toUpperCase(); }

function showTab(id, el) {
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  el.classList.add('active');
}

/* ── Grupos ── */
function renderGroups() {
  const c = document.getElementById('groupsContainer');
  GROUPS_DATA.forEach(group => {
    const card = document.createElement('div');
    card.className = 'group-card';
    const rows = group.standings.map((t, i) => {
      const rc = i < 2 ? 'qualified' : (i === 2 ? 'qualified-3rd' : '');
      const mc = t.mc_clasif || 0;
      const mcCls = mc > 60 ? 'mc-pct' : 'mc-pct low';
      return `<tr class="${rc}">
        <td><div class="team-name">${t.flag} ${t.name_es}${t.is_host ? ' 🏠' : ''}</div></td>
        <td>${t.w}</td><td>${t.d}</td><td>${t.l}</td>
        <td>${t.gf}</td><td>${t.ga}</td><td>${t.gf - t.ga > 0 ? '+' : ''}${t.gf - t.ga}</td>
        <td class="pts">${t.pts}</td>
        <td class="${mcCls}">${mc}%</td>
      </tr>`;
    }).join('');
    const matchRows = group.results.map(r => {
      const hostHome = r.host_team && r.home_raw.startsWith(r.host_team);
      const hostAway = r.host_team && r.away_raw.startsWith(r.host_team);
      const ev = r.exp_pts != null ? `EV ${r.exp_pts.toFixed(1)}` : '';
      const manual = r.manual ? ' <span title="Resultado fijado manualmente">✏️</span>' : '';
      return `
      <div class="match-block${r.manual ? ' match-manual' : ''}"
           title="${r.home} vs ${r.away} · Local ${r.prob_h}% · Empate ${r.prob_d}% · Visita ${r.prob_a}%">
        <span class="m-prob ph">${Math.round(r.prob_h)}%</span>
        <span class="m-prob pd">${Math.round(r.prob_d)}%</span>
        <span class="m-prob pa">${Math.round(r.prob_a)}%</span>
        <span class="m-team home">${getCode(r.home_raw)}${hostHome ? ' 🏠' : ''} <span class="m-flag">${getFlag(r.home_raw)}</span></span>
        <span class="m-score">${r.score}</span>
        <span class="m-team away"><span class="m-flag">${getFlag(r.away_raw)}</span> ${getCode(r.away_raw)}${hostAway ? ' 🏠' : ''}</span>
        <span class="m-sub">${ev}${manual}</span>
        <span class="m-actions">${editGroupControls(r)}</span>
      </div>`;
    }).join('');
    card.innerHTML = `
      <div class="group-header"><span class="group-label">Grupo</span><span class="group-letter">${group.group}</span></div>
      <table class="standings-table">
        <thead><tr><th>Equipo</th><th>G</th><th>E</th><th>P</th><th>GF</th><th>GC</th><th>DG</th><th>Pts</th><th title="Probabilidad de clasificar directo (Monte Carlo)">Clasif</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <div class="matches-section">${matchRows}</div>`;
    c.appendChild(card);
  });
}

/* ── Campeón ── */
function renderChampionCard() {
  const odds = BRACKET_DATA.mc_odds;
  const maxProb = odds[0]?.prob || 1;
  const champProb = (odds.find(t => t.name === BRACKET_DATA.champion) || {prob: 0}).prob;
  const top8 = odds.slice(0, 8);
  const makeRows = list => list.map(t => `
    <div class="odds-team">
      <span class="odds-flag">${getFlag(t.name)}</span>
      <span class="odds-name">${t.name_es}</span>
      <span class="odds-prob">${t.prob}%</span>
    </div>
    <div class="odds-bar-bg"><div class="odds-bar-fill" style="width:${(t.prob / maxProb * 100).toFixed(1)}%"></div></div>`).join('');
  document.getElementById('championCard').innerHTML = `
    <div class="champion-info">
      <div class="champion-trophy">🏆</div>
      <div>
        <h2>${getFlag(BRACKET_DATA.champion)} ${BRACKET_DATA.champion_es}</h2>
        <p>Campeón predicho · ${champProb}% de probabilidad</p>
      </div>
    </div>
    <div class="odds-grid">
      <div class="odds-row">${makeRows(top8.slice(0, 4))}</div>
      <div class="odds-row">${makeRows(top8.slice(4, 8))}</div>
    </div>`;
}

/* ── Bracket espejado: mitades izquierda/derecha, final al centro ── */
function renderBracket() {
  const W = 132, G = 24, SLOT = 78, CARD_H = 68, HDR = 34;
  const R = BRACKET_DATA.rounds;
  const LABELS = {R32: '16avos', R16: 'Octavos', QF: 'Cuartos', SF: 'Semifinal', Final: 'Final'};
  const COLS = [
    {round: 'R32',   from: 0, to: 8,  span: 1},
    {round: 'R16',   from: 0, to: 4,  span: 2},
    {round: 'QF',    from: 0, to: 2,  span: 4},
    {round: 'SF',    from: 0, to: 1,  span: 8},
    {round: 'Final', from: 0, to: 1,  span: 8},
    {round: 'SF',    from: 1, to: 2,  span: 8},
    {round: 'QF',    from: 2, to: 4,  span: 4},
    {round: 'R16',   from: 4, to: 8,  span: 2},
    {round: 'R32',   from: 8, to: 16, span: 1},
  ];
  const x  = c => c * (W + G);
  const cy = (span, i) => HDR + (span * i + span / 2) * SLOT;
  const wrap = document.getElementById('bracketRounds');
  wrap.style.width  = (9 * W + 8 * G) + 'px';
  wrap.style.height = (HDR + 8 * SLOT) + 'px';

  COLS.forEach((L, ci) => {
    const hdr = document.createElement('div');
    hdr.className = 'bk-hdr';
    hdr.style.left  = x(ci) + 'px';
    hdr.style.width = W + 'px';
    hdr.textContent = LABELS[L.round];
    wrap.appendChild(hdr);

    for (let i = L.from; i < L.to; i++) {
      const m = R[L.round][i];
      const card = document.createElement('div');
      card.className = 'ko-card' + (m.manual ? ' ko-manual' : '') + (L.round === 'Final' ? ' ko-final' : '');
      card.style.left   = x(ci) + 'px';
      card.style.top    = (cy(L.span, i - L.from) - CARD_H / 2) + 'px';
      card.style.width  = W + 'px';
      card.style.height = CARD_H + 'px';
      const hw = m.winner === m.home, aw = m.winner === m.away;
      const res = m.went_et ? `${m.score} pen ${getCode(m.advancer)}` : m.score;
      const ev = m.exp_pts != null ? ` <span class="ko-ev">EV ${m.exp_pts.toFixed(1)}</span>` : '';
      card.innerHTML = `
        <div class="ko-team ${hw ? 'winner' : ''}"><span class="ko-flag">${getFlag(m.home)}</span><span class="ko-name">${getCode(m.home)}</span><span class="ko-pct">${m.prob_h}%</span></div>
        <div class="ko-team ${aw ? 'winner' : ''}"><span class="ko-flag">${getFlag(m.away)}</span><span class="ko-name">${getCode(m.away)}</span><span class="ko-pct">${m.prob_a}%</span></div>
        <div class="ko-score"><span class="ko-res">${res}</span>${ev}${m.manual ? ' ✏️' : ''}${editKoControls(m)}</div>`;
      card.title = `${m.home_es} vs ${m.away_es} · ${m.score}${m.went_et ? ` (pen: ${m.advancer_es})` : ''} · Local ${m.prob_h}% · Empate ${m.prob_d}% · Visita ${m.prob_a}% · EV ${m.exp_pts}${m.manual ? ' · fijado manualmente' : ''}`;
      wrap.appendChild(card);
    }
  });

  /* Líneas conectoras entre rondas */
  const hline = (x1, x2, y) => {
    const d = document.createElement('div');
    d.className = 'bk-line';
    d.style.left = Math.min(x1, x2) + 'px';
    d.style.top = y + 'px';
    d.style.width = Math.abs(x2 - x1) + 'px';
    d.style.height = '1px';
    wrap.appendChild(d);
  };
  const vline = (x0, y1, y2) => {
    const d = document.createElement('div');
    d.className = 'bk-line';
    d.style.left = x0 + 'px';
    d.style.top = Math.min(y1, y2) + 'px';
    d.style.width = '1px';
    d.style.height = Math.abs(y2 - y1) + 'px';
    wrap.appendChild(d);
  };
  const LINKS = [[0,1],[1,2],[2,3],[3,4],[8,7],[7,6],[6,5],[5,4]];
  LINKS.forEach(([si, di]) => {
    const S = COLS[si], D = COLS[di];
    const sCount = S.to - S.from, dCount = D.to - D.from;
    const leftSide = si < di;
    const gapL = (leftSide ? x(si) : x(di)) + W;   // borde izquierdo del espacio entre columnas
    const midX = gapL + G / 2;
    for (let j = 0; j < dCount; j++) {
      const ty = cy(D.span, j);
      if (sCount === dCount) { hline(gapL, gapL + G, ty); continue; }
      const c1 = cy(S.span, 2 * j), c2 = cy(S.span, 2 * j + 1);
      if (leftSide) {
        hline(x(si) + W, midX, c1);
        hline(x(si) + W, midX, c2);
        hline(midX, x(di), ty);
      } else {
        hline(midX, x(si), c1);
        hline(midX, x(si), c2);
        hline(x(di) + W, midX, ty);
      }
      vline(midX, c1, c2);
    }
  });
}

renderGroups();
renderChampionCard();
renderBracket();
"""


def build_html(groups_data, bracket_data, interactive=False):
    """Genera el HTML del dashboard.
    interactive=True (app.py) inyecta la UI de edición de resultados;
    con False (default) el HTML estático queda sin UI de edición."""
    gj = json.dumps(groups_data, ensure_ascii=False)
    bj = json.dumps(bracket_data, ensure_ascii=False)
    fj = json.dumps(FLAG_EMOJIS, ensure_ascii=False)
    cj = json.dumps(TEAM_CODES, ensure_ascii=False)
    edit_css = EDIT_CSS if interactive else ""
    edit_js  = EDIT_JS if interactive else ""

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Polla Mundial 2026</title>
<style>{BASE_CSS}{edit_css}</style>
</head>
<body>
<header>
  <h1>⚽ Polla <em>Mundial 2026</em></h1>
  <p>Simulador de predicciones · Monte Carlo 20.000 simulaciones</p>
</header>

<div class="container">
  <div class="tab-bar">
    <div class="tab active" onclick="showTab('grupos',this)">Grupos</div>
    <div class="tab" onclick="showTab('bracket',this)">Bracket</div>
    <div class="tab" onclick="showTab('info',this)">Metodología</div>
  </div>

  <!-- ────── TAB GRUPOS ────── -->
  <div id="grupos" class="tab-content active">
    <div class="groups-grid" id="groupsContainer"></div>
  </div>

  <!-- ────── TAB BRACKET ────── -->
  <div id="bracket" class="tab-content">
    <div id="championCard" class="champion-card"></div>
    <div class="bracket-wrap">
      <div id="bracketRounds"></div>
    </div>
  </div>

  <!-- ────── TAB METODOLOGÍA ────── -->
  <div id="info" class="tab-content">
    <div class="method">
      <h3>Metodología — modelo v3.3</h3>
      <p><strong>Resumen:</strong> ELO exponente 2.8/2.1, calibrado el 9 jun 2026 con 19 amistosos
      + 12 cuotas de mercado · forma ±25% · Dixon-Coles ρ=−0.10 · Monte Carlo 20.000 simulaciones ·
      Validación: 79% dirección · 74% top-3 · 42% marcador exacto.</p>
      <p><strong>Base ELO:</strong> Fuerza relativa de cada selección.
      Exponentes ataque/defensa = 2.8/2.1 (calibrados el 9 jun 2026 por grid search sobre 19
      amistosos + 12 cuotas de mercado). Curazao tiene λ≈0.52 vs Alemania.</p>
      <p><strong>Forma reciente:</strong> Score 1-10, capped ±25%.
      Eliminado el multiplicador sin límite (v2 daba ×1.8 para forma 9).</p>
      <p><strong>Ventaja de local:</strong> México +20%/−13%,
      USA +13%/−6%, Canadá +10%/−5%. Basado en Pollard (2006): ~0.3 goles adicionales
      para el anfitrión mundialista. Incluye efecto arbitral.</p>
      <p><strong>Dixon-Coles ρ=−0.10:</strong> Calibrado para
      fútbol internacional. Ajusta la probabilidad de marcadores bajos (0-0, 1-0, 0-1).</p>
      <p><strong>Monte Carlo 20.000 iter.:</strong> % de clasificación
      real, no solo el marcador modal. Empates en eliminatoria se resuelven con prórroga
      (λ×0.45, 30 min) y penales muerte súbita (76% conversión). λ×0.90 en eliminatoria.</p>
      <p><strong>Bracket:</strong> Fixture oficial FIFA 2026 · mejores terceros según Annex C
      (combinación B,C,D,E,F,G,I,L).</p>
      <p><strong>Selección de marcador (v3.3 — apuesta por valor esperado):</strong>
      El modelo elige el marcador (y en eliminatoria, quién avanza) que <em>maximiza los puntos
      esperados</em> según el reglamento de la polla. Esto reemplaza la heurística del
      "resultado dominante" de v3.2. El EV mostrado refleja cuántos puntos se esperan ganar
      en promedio con esa apuesta. Los overrides manuales permiten fijar cualquier marcador (✏️).</p>
    </div>
  </div>

  <!-- ────── AYUDA (abajo de todo) ────── -->
  <details class="help-box">
    <summary>¿Cómo leer este dashboard?</summary>
    <ul>
      <li><b>Marcador</b> — es la apuesta que más puntos promete según el reglamento de la polla; no siempre es el resultado más probable.</li>
      <li><b>EV</b> — puntos que esa apuesta gana en promedio (valor esperado).</li>
      <li><b>% sobre cada partido</b> — probabilidad de victoria local · empate · victoria visita.</li>
      <li><b>% junto a cada equipo en el bracket</b> — probabilidad de avanzar a la siguiente ronda.</li>
      <li><b>Clasif</b> — probabilidad de terminar 1° o 2° del grupo (Monte Carlo).</li>
      <li><b>Fila verde</b> — clasifica directo a 16avos (1° y 2° del grupo).</li>
      <li><b>Fila ámbar</b> — puede clasificar como uno de los 8 mejores terceros.</li>
      <li><b>🏠</b> — anfitrión jugando de local (México +20% · USA +13% · Canadá +10%).</li>
      <li><b>✏️</b> — resultado fijado manualmente por ti.</li>
      <li><b>pen XXX</b> — empate en 90 minutos; ese equipo avanza por prórroga o penales.</li>
      <li><b>Puntos en grupos</b> — 6 marcador exacto · 4 ganador + goles de un equipo · 3 ganador · 1 goles de un equipo.</li>
      <li><b>Puntos en eliminatoria</b> — 9 exacto · 6 ganador + goles · 6 acertar quién avanza · 3 goles de un equipo en empates.</li>
    </ul>
  </details>
</div>

<footer>Polla Mundial 2026 · Modelo v3.3 · Calibrado 9 jun 2026</footer>

<script>
const GROUPS_DATA = {gj};
const BRACKET_DATA = {bj};
const FLAGS = {fj};
const CODES = {cj};

/* Hooks de edición: no-op en el HTML estático; el modo interactivo
   (app.py) los redefine para inyectar los botones ✏️/🗑️. */
let editGroupControls = r => '';
let editKoControls = m => '';
{edit_js}
{BASE_JS}
</script>
</body>
</html>"""


def collect_groups_data(conn, n_sims=MC_SIMS, group_mc=None, verbose=True):
    """Recolecta los datos de la fase de grupos (parte determinista + MC).

    group_mc : dict opcional {grupo: finish_counts} con el Monte Carlo de
               grupos precalculado (cache de app.py — los overrides no afectan
               el MC, así que es seguro reutilizarlo entre reloads).
               Si es None, se calcula con simulate_group_mc (n_sims).
    """
    from predictor_v3 import MATCH_VENUES, HOST_ADVANTAGE

    all_groups = []
    for g in GROUPS:
        if verbose:
            print(f"  Grupo {g}...", end=" ", flush=True)
        sorted_teams, results = simulate_group(g, conn=conn, verbose=False)
        if group_mc is not None and g in group_mc:
            finish_counts = group_mc[g]
        else:
            finish_counts, _, _ = simulate_group_mc(g, conn, n_sims=n_sims)
        cur = conn.cursor()
        for t in sorted_teams:
            cur.execute("SELECT confederation FROM teams WHERE name=?", (t["name"],))
            row = cur.fetchone()
            t["confederation"] = row[0] if row else ""
            t["flag"]    = FLAG_EMOJIS.get(t["name"], "🏳")
            t["is_host"] = t["name"] in HOST_TEAMS
            fc = finish_counts.get(t["name"], [0,0,0,0])
            # Normalizar por el total real de simulaciones (sum(fc)) para que
            # funcione con cualquier n_sims del cache de app.py.
            total_sims = sum(fc) or 1
            t["mc_clasif"] = round((fc[0]+fc[1]) / total_sims * 100, 1)
        for r in results:
            hn = r.get("home_raw", r["home"])
            an = r.get("away_raw", r["away"])
            ven = MATCH_VENUES.get((hn, an))
            r["host_team"] = None
            if ven:
                for hname, hdata in HOST_ADVANTAGE.items():
                    if ven in hdata["venues"] and (hn==hname or an==hname):
                        r["host_team"] = hname[:3]
                        break
        if verbose:
            print("✓")
        all_groups.append({
            "group": g,
            "standings": [{"name_es":t["name_es"],"name":t["name"],"pts":t["pts"],
                           "w":t["w"],"d":t["d"],"l":t["l"],"gf":t["gf"],"ga":t["ga"],
                           "confederation":t.get("confederation",""),
                           "flag":t.get("flag","🏳"),"is_host":t.get("is_host",False),
                           "mc_clasif":t.get("mc_clasif",0)} for t in sorted_teams],
            "results": results,
        })
    return all_groups


def render_dashboard_html(conn, n_sims=MC_SIMS, mc_odds=None, group_mc=None,
                          interactive=False, verbose=True):
    """Recolecta los datos actuales (overrides incluidos) y retorna el HTML.

    mc_odds  : probabilidades de campeón precalculadas (cache de app.py);
               si es None se corre el Monte Carlo del bracket (caro).
    group_mc : Monte Carlo de grupos precalculado (ver collect_groups_data).
    interactive : inyecta la UI de edición (solo app.py).
    """
    all_groups = collect_groups_data(conn, n_sims=n_sims, group_mc=group_mc,
                                     verbose=verbose)
    if verbose:
        print(f"  Bracket eliminatorio...", end=" ", flush=True)
    bracket = get_bracket_data(conn, n_sims=n_sims, mc_odds=mc_odds)
    if verbose:
        print("✓")
    return build_html(all_groups, bracket, interactive=interactive)


def generate_dashboard():
    print("Inicializando DB...")
    regenerate_db()
    conn = sqlite3.connect(DB_PATH)
    html = render_dashboard_html(conn, n_sims=MC_SIMS, verbose=True)
    conn.close()
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n✅ Dashboard generado: {OUTPUT_PATH}")
    return OUTPUT_PATH


if __name__ == "__main__":
    generate_dashboard()
