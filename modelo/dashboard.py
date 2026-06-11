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
# Íconos Lucide (lucide.dev, ISC) incrustados como SVG inline — sin CDN, el
# dashboard sigue siendo un único HTML que funciona offline. Las banderas de
# países se mantienen como emojis (Lucide no tiene banderas).
# ---------------------------------------------------------------------------
LUCIDE = {
    "ball":         '<path d="M11 7a16 16 20 0 1 10.98 4.362"/><path d="M12 12a13 13 0 0 1-8.66 5"/><path d="M16.83 13.634a16 16 0 0 1-9.267 7.328"/><path d="M20.66 17A13 13 0 0 0 12 12a13 13 0 0 1 0-10"/><path d="M8.17 15.366a16 16 0 0 1-1.713-11.69"/><circle cx="12" cy="12" r="10"/>',
    "trophy":       '<path d="M10 14.66v1.626a2 2 0 0 1-.976 1.696A5 5 0 0 0 7 21.978"/><path d="M14 14.66v1.626a2 2 0 0 0 .976 1.696A5 5 0 0 1 17 21.978"/><path d="M18 9h1.5a1 1 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M6 9a6 6 0 0 0 12 0V3a1 1 0 0 0-1-1H7a1 1 0 0 0-1 1z"/><path d="M6 9H4.5a1 1 0 0 1 0-5H6"/>',
    "pencil":       '<path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z"/><path d="m15 5 4 4"/>',
    "trash":        '<path d="M10 11v6"/><path d="M14 11v6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
    "check":        '<path d="M20 6 9 17l-5-5"/>',
    "circle-check": '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
    "house":        '<path d="M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"/><path d="M3 10a2 2 0 0 1 .709-1.528l7-6a2 2 0 0 1 2.582 0l7 6A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "target":       '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
    "refresh":      '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/>',
}


def _icon(name, cls=""):
    """SVG inline de un ícono Lucide para las partes estáticas del HTML.
    (El JS tiene su propio helper icon() con el mismo dict inyectado.)"""
    c = ("lc " + cls).strip()
    return (f'<svg class="{c}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
            f'aria-hidden="true">{LUCIDE[name]}</svg>')

# ---------------------------------------------------------------------------
# UI de edición (solo modo interactivo, servida por app.py)
# ---------------------------------------------------------------------------
EDIT_CSS = """
/* ── UI de edición (modo interactivo) ── */
.edit-bar{position:fixed;top:.8rem;right:.8rem;z-index:1000;display:flex;align-items:center;gap:.5rem;background:rgba(30,41,59,.92);border:1px solid var(--border);border-radius:999px;padding:.3rem .5rem .3rem .9rem;font-size:.74rem;color:var(--muted);box-shadow:0 4px 16px rgba(0,0,0,.35);backdrop-filter:blur(8px)}
.edit-bar span{display:inline-flex;align-items:center;gap:.3rem}
.edit-bar button{display:inline-flex;align-items:center;gap:.35rem;background:transparent;color:var(--text);border:1px solid var(--border);border-radius:999px;padding:.22rem .75rem;font-size:.72rem;cursor:pointer;transition:border-color .15s ease,color .15s ease,transform .12s ease}
.edit-bar button:hover{border-color:var(--accent);color:var(--accent)}
.edit-bar button:active{transform:scale(.96)}
.edit-bar button:disabled{opacity:.5;cursor:wait}
.edit-btn{background:none;border:none;cursor:pointer;padding:0 .1rem;color:var(--muted);opacity:0;transition:opacity .15s ease,color .15s ease;line-height:1}
.edit-btn .lc{width:.9rem;height:.9rem;vertical-align:middle}
.edit-btn:hover{color:var(--text)}
.edit-btn.btn-ok:hover{color:var(--green)}
.edit-btn.btn-del:hover{color:var(--red)}
.match-block:hover .edit-btn,.ko-card:hover .edit-btn{opacity:.8}
.edit-btn:hover{opacity:1!important}
@media (hover:none){.edit-btn{opacity:.55}}
@media (max-width:700px){.edit-bar{top:auto;bottom:.8rem;right:.8rem}}

/* ── Modal de edición ── */
.modal-overlay{position:fixed;inset:0;z-index:2000;background:rgba(2,6,23,.6);backdrop-filter:blur(3px);display:flex;align-items:center;justify-content:center;opacity:0;pointer-events:none;transition:opacity .15s ease}
.modal-overlay.open{opacity:1;pointer-events:auto}
.modal{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:1.3rem 1.5rem;width:min(92vw,360px);box-shadow:0 16px 48px rgba(0,0,0,.5);transform:scale(.96);opacity:0;transition:transform .18s cubic-bezier(0.23,1,0.32,1),opacity .18s ease}
.modal-overlay.open .modal{transform:scale(1);opacity:1}
.modal-kind{display:inline-flex;align-items:center;gap:.35rem;font-size:.66rem;text-transform:uppercase;letter-spacing:1.5px;font-weight:700;margin-bottom:.3rem}
.modal-kind.k-bet{color:var(--accent)}
.modal-kind.k-result{color:var(--green)}
.modal h3{font-size:1rem;margin-bottom:1.1rem;font-weight:600}
.modal-score{display:flex;align-items:center;justify-content:center;gap:.6rem;margin-bottom:1rem}
.modal-team{display:flex;flex-direction:column;align-items:center;gap:.1rem;width:3.2rem}
.modal-team .mt-flag{font-size:1.5rem;line-height:1}
.modal-team .mt-code{font-size:.7rem;font-weight:700;color:var(--muted);letter-spacing:.5px}
.modal-score input{width:3.2rem;height:2.6rem;text-align:center;font-size:1.25rem;font-weight:700;color:var(--text);background:var(--bg);border:1px solid var(--border);border-radius:8px;outline:none;transition:border-color .15s ease}
.modal-score input:focus{border-color:var(--accent)}
.modal-score input::-webkit-outer-spin-button,.modal-score input::-webkit-inner-spin-button{-webkit-appearance:none;margin:0}
.modal-score input[type=number]{-moz-appearance:textfield;appearance:textfield}
.modal-dash{color:var(--muted);font-weight:700}
.modal-adv{margin-bottom:1rem}
.modal-adv-label{font-size:.74rem;color:var(--muted);margin-bottom:.45rem;text-align:center}
.modal-seg{display:flex;gap:.4rem;justify-content:center}
.modal-seg button{flex:1;max-width:9rem;padding:.4rem .6rem;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:8px;font-size:.78rem;font-weight:600;cursor:pointer;transition:border-color .15s ease,background-color .15s ease,transform .12s ease}
.modal-seg button:active{transform:scale(.97)}
.modal-seg button.sel{border-color:var(--green);background:rgba(16,185,129,.12);color:var(--green)}
.modal-actions{display:flex;align-items:center;gap:.5rem}
.modal-actions button{padding:.45rem .9rem;border-radius:8px;font-size:.78rem;font-weight:600;cursor:pointer;border:1px solid var(--border);background:transparent;color:var(--text);transition:border-color .15s ease,color .15s ease,transform .12s ease}
.modal-actions button:active{transform:scale(.97)}
.modal-actions .m-save{background:var(--accent);border-color:var(--accent);color:#0f172a}
.modal-actions .m-save:hover{filter:brightness(1.08)}
.modal-actions .m-cancel:hover{border-color:var(--muted)}
.modal-actions .m-del{color:var(--red);border-color:transparent;padding-left:.2rem}
.modal-actions .m-del:hover{border-color:var(--red)}
.modal-err{color:var(--red);font-size:.72rem;text-align:center;margin-bottom:.7rem;min-height:.9em}
"""

EDIT_JS = r"""
/* ── Modo interactivo: edición de apuestas y resultados reales (app.py) ──
   Cada partido renderizado se registra en MATCH_REG; los botones de la fila
   abren el modal con el índice del registro. kind: 'bet' (apuesta manual,
   /api/override) | 'result' (resultado real, /api/result). */
const MATCH_REG = [];

function regControls(entry) {
  const i = MATCH_REG.push(entry) - 1;
  if (entry.played) {
    return `<button class="edit-btn" title="Editar resultado real" onclick="openDlg(${i},'result')">${icon('pencil')}</button>` +
           `<button class="edit-btn btn-del" title="Quitar resultado real" onclick="delEntry(${i},'result')">${icon('trash')}</button>`;
  }
  return `<button class="edit-btn btn-ok" title="Ingresar resultado real" onclick="openDlg(${i},'result')">${icon('circle-check')}</button>` +
         `<button class="edit-btn" title="Editar apuesta" onclick="openDlg(${i},'bet')">${icon('pencil')}</button>` +
         (entry.manual ? `<button class="edit-btn btn-del" title="Borrar apuesta manual" onclick="delEntry(${i},'bet')">${icon('trash')}</button>` : '');
}

editGroupControls = r => regControls({
  scope: 'group', home: r.home_raw, away: r.away_raw, homeEs: r.home, awayEs: r.away,
  score: r.score, advancer: null, played: !!r.played, manual: !!r.manual,
  bet: {score: r.score, advancer: null},
});

editKoControls = m => regControls({
  scope: 'ko', home: m.home, away: m.away, homeEs: m.home_es, awayEs: m.away_es,
  score: m.score, advancer: m.advancer, played: !!m.played, manual: !!m.manual,
  bet: {score: m.score, advancer: m.advancer},
});

async function apiPost(path, body) {
  try {
    const res = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'},
                                   body: JSON.stringify(body)});
    const data = await res.json();
    if (!data.ok) return {error: data.error || 'desconocido'};
    return data;
  } catch (e) {
    return {error: 'sin conexión con el servidor local (' + e + ')'};
  }
}

/* ── Modal ── */
const DLG = {entry: null, kind: 'bet', adv: null};

(function buildModal() {
  const ov = document.createElement('div');
  ov.className = 'modal-overlay';
  ov.id = 'editModal';
  ov.innerHTML = `
    <div class="modal" role="dialog" aria-modal="true">
      <div class="modal-kind" id="mKind"></div>
      <h3 id="mTitle"></h3>
      <div class="modal-score">
        <div class="modal-team"><span class="mt-flag" id="mFlagH"></span><span class="mt-code" id="mCodeH"></span></div>
        <input id="mGh" type="number" min="0" max="20" inputmode="numeric">
        <span class="modal-dash">–</span>
        <input id="mGa" type="number" min="0" max="20" inputmode="numeric">
        <div class="modal-team"><span class="mt-flag" id="mFlagA"></span><span class="mt-code" id="mCodeA"></span></div>
      </div>
      <div class="modal-adv" id="mAdvRow" hidden>
        <div class="modal-adv-label">Empate en 90' — ¿quién avanza?</div>
        <div class="modal-seg">
          <button type="button" id="mAdvH"></button>
          <button type="button" id="mAdvA"></button>
        </div>
      </div>
      <div class="modal-err" id="mErr"></div>
      <div class="modal-actions">
        <button type="button" class="m-del" id="mDelete">Borrar</button>
        <span style="flex:1"></span>
        <button type="button" class="m-cancel" onclick="closeDlg()">Cancelar</button>
        <button type="button" class="m-save" id="mSave">Guardar</button>
      </div>
    </div>`;
  document.body.appendChild(ov);
  ov.addEventListener('click', e => { if (e.target === ov) closeDlg(); });
  document.addEventListener('keydown', e => {
    if (!ov.classList.contains('open')) return;
    if (e.key === 'Escape') closeDlg();
    if (e.key === 'Enter') document.getElementById('mSave').click();
  });
  ['mGh', 'mGa'].forEach(id =>
    document.getElementById(id).addEventListener('input', syncAdvRow));
  document.getElementById('mAdvH').onclick = () => setAdv('home');
  document.getElementById('mAdvA').onclick = () => setAdv('away');
  document.getElementById('mSave').onclick = saveDlg;
  document.getElementById('mDelete').onclick = () => {
    closeDlg();
    delEntry(DLG.idx, DLG.kind);
  };
})();

function setAdv(side) {
  DLG.adv = side;
  document.getElementById('mAdvH').classList.toggle('sel', side === 'home');
  document.getElementById('mAdvA').classList.toggle('sel', side === 'away');
}

function syncAdvRow() {
  const e = DLG.entry;
  if (!e || e.scope !== 'ko') return;
  const gh = document.getElementById('mGh').value,
        ga = document.getElementById('mGa').value;
  document.getElementById('mAdvRow').hidden = !(gh !== '' && gh === ga);
}

function openDlg(idx, kind) {
  const e = MATCH_REG[idx];
  DLG.entry = e; DLG.kind = kind; DLG.idx = idx; DLG.adv = null;
  document.getElementById('mKind').innerHTML = kind === 'result'
    ? `${icon('circle-check')} Resultado real` : `${icon('pencil')} Apuesta manual`;
  document.getElementById('mKind').className = 'modal-kind ' + (kind === 'result' ? 'k-result' : 'k-bet');
  document.getElementById('mTitle').textContent = `${e.homeEs} vs ${e.awayEs}`;
  document.getElementById('mFlagH').textContent = getFlag(e.home);
  document.getElementById('mCodeH').textContent = getCode(e.home);
  document.getElementById('mFlagA').textContent = getFlag(e.away);
  document.getElementById('mCodeA').textContent = getCode(e.away);
  document.getElementById('mAdvH').textContent = getCode(e.home);
  document.getElementById('mAdvA').textContent = getCode(e.away);
  const sc = (e.score || '').match(/^(\d+)-(\d+)$/);
  document.getElementById('mGh').value = sc ? sc[1] : '';
  document.getElementById('mGa').value = sc ? sc[2] : '';
  if (e.scope === 'ko' && e.advancer) setAdv(e.advancer === e.home ? 'home' : 'away');
  document.getElementById('mErr').textContent = '';
  // Borrar: visible si hay algo que borrar para este kind
  const canDel = (kind === 'result' && e.played) || (kind === 'bet' && e.manual);
  document.getElementById('mDelete').style.visibility = canDel ? 'visible' : 'hidden';
  document.getElementById('editModal').classList.add('open');
  syncAdvRow();
  document.getElementById('mGh').focus();
  document.getElementById('mGh').select();
}

function closeDlg() {
  document.getElementById('editModal').classList.remove('open');
}

async function saveDlg() {
  const e = DLG.entry;
  const gh = parseInt(document.getElementById('mGh').value, 10),
        ga = parseInt(document.getElementById('mGa').value, 10);
  const err = document.getElementById('mErr');
  if (isNaN(gh) || isNaN(ga) || gh < 0 || ga < 0 || gh > 20 || ga > 20) {
    err.textContent = 'Ingresa un marcador válido (0–20).'; return;
  }
  let advancer = null;
  if (e.scope === 'ko' && gh === ga) {
    if (!DLG.adv) { err.textContent = 'Elige quién avanza en el empate.'; return; }
    advancer = DLG.adv === 'home' ? e.home : e.away;
  }
  const body = {scope: e.scope, home: e.home, away: e.away, gh, ga, advancer};
  if (DLG.kind === 'result') {
    // Congelar la apuesta vigente (la que el usuario está viendo) la primera
    // vez que se ingresa el resultado; en ediciones el server preserva el bet.
    let bet = null;
    if (!e.played) {
      const bs = (e.bet.score || '').match(/^(\d+)-(\d+)$/);
      if (bs) bet = {score: [parseInt(bs[1], 10), parseInt(bs[2], 10)],
                     advancer: e.bet.advancer || null};
    }
    body.bet = bet;
  }
  const btn = document.getElementById('mSave');
  btn.disabled = true; btn.textContent = 'Guardando…';
  const r = await apiPost(DLG.kind === 'result' ? '/api/result' : '/api/override', body);
  btn.disabled = false; btn.textContent = 'Guardar';
  if (r.error) { err.textContent = r.error; return; }
  location.reload();
}

async function delEntry(idx, kind) {
  const e = MATCH_REG[idx];
  const what = kind === 'result' ? 'el resultado real' : 'la apuesta manual';
  if (!confirm(`¿Borrar ${what} de ${e.homeEs} vs ${e.awayEs}?`)) return;
  const r = await apiPost(kind === 'result' ? '/api/clear-result' : '/api/clear',
                          {home: e.home, away: e.away});
  if (!r.error) location.reload(); else alert('Error: ' + r.error);
}

async function clearAllOverrides() {
  if (!confirm('¿Borrar TODAS las apuestas manuales? (los resultados reales no se tocan)')) return;
  const r = await apiPost('/api/clear', {all: true});
  if (!r.error) location.reload(); else alert('Error: ' + r.error);
}

async function recalcMC() {
  const btn = document.getElementById('recalcBtn');
  btn.disabled = true; btn.innerHTML = `${icon('refresh')} Recalculando…`;
  const r = await apiPost('/api/recalc-mc', {});
  if (!r.error) { location.reload(); return; }
  btn.disabled = false; btn.innerHTML = `${icon('refresh')} Recalcular`;
  alert('Error: ' + r.error);
}

/* Barra fija: contadores + acciones globales */
(function () {
  let n = 0, p = 0;
  GROUPS_DATA.forEach(g => g.results.forEach(r => { if (r.manual) n++; if (r.played) p++; }));
  Object.values(BRACKET_DATA.rounds).forEach(ms => ms.forEach(m => { if (m.manual) n++; if (m.played) p++; }));
  const bar = document.createElement('div');
  bar.className = 'edit-bar';
  bar.innerHTML = `<span title="Resultados reales ingresados">${icon('circle-check', 'lc-green')} ${p}</span>
    <span title="Apuestas fijadas a mano">${icon('pencil')} ${n}</span>
    ${n > 0 ? '<button onclick="clearAllOverrides()">Limpiar apuestas</button>' : ''}
    <button id="recalcBtn" onclick="recalcMC()" title="Recalcular Monte Carlo del bracket">${icon('refresh')} Recalcular</button>`;
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

/* ── Íconos Lucide ── */
.lc{width:1em;height:1em;display:inline-block;vertical-align:-0.125em;flex-shrink:0}
.lc-accent{color:var(--accent)}
.lc-green{color:var(--green)}
.lc-host{color:var(--host);width:.85em;height:.85em}
.lc-title{width:1.45rem;height:1.45rem;color:var(--accent);vertical-align:-0.18em}
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
.m-score.real{background:rgba(16,185,129,.15);color:var(--text);box-shadow:inset 0 0 0 1px rgba(16,185,129,.35)}
.m-sub{grid-column:2;justify-self:center;white-space:nowrap;text-align:center;font-size:.66rem;color:var(--green);font-weight:600;margin-top:3px;min-height:.9em}
.m-actions{grid-column:3;display:flex;gap:.2rem;align-items:center;justify-self:end;margin-top:3px}
.m-tag{font-size:.6rem;color:var(--green);text-transform:uppercase;letter-spacing:1.5px;font-weight:600}
.m-bet{color:var(--muted);font-weight:500}
.pts-badge{font-weight:700}
.pts-hi{color:var(--green)}
.pts-mid{color:var(--accent)}
.pts-low{color:var(--muted)}
.pts-zero{color:var(--red)}

/* ── Puntos polla (resumen) ── */
.points-strip{display:flex;justify-content:center;align-items:center;gap:1.8rem;background:linear-gradient(135deg,rgba(16,185,129,.10),rgba(245,158,11,.06));border:1px solid rgba(16,185,129,.35);border-radius:10px;padding:.6rem 1.2rem;margin-bottom:1.4rem;font-size:.84rem;color:var(--muted);flex-wrap:wrap}
.points-strip span{display:inline-flex;align-items:center;gap:.4rem}
.points-strip b{color:var(--text);font-size:1rem}
.points-strip .ps-total b{color:var(--green);font-size:1.15rem}

/* ── Campeón ── */
.champion-card{background:linear-gradient(135deg,rgba(245,158,11,.12),rgba(16,185,129,.05));border:1px solid var(--accent);border-radius:12px;padding:1.2rem 1.6rem;margin-bottom:1.6rem;display:flex;align-items:center;gap:2.5rem;flex-wrap:wrap}
.champion-info{display:flex;align-items:center;gap:1rem}
.champion-trophy{display:flex}
.champion-trophy .lc{width:2.3rem;height:2.3rem}
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
.ko-card.ko-played{border-color:rgba(16,185,129,.5)}
.ko-card.ko-played .ko-score{background:rgba(16,185,129,.08)}

/* ── Bracket móvil (lista vertical por ronda) ── */
#bracketList{display:none}
.bkl-title{font-size:.68rem;text-transform:uppercase;letter-spacing:1.5px;color:var(--muted);font-weight:600;margin:1.1rem 0 .5rem;text-align:center}
.ko-card.bkl{position:static;width:auto!important;height:auto!important;margin-bottom:.55rem;font-size:.78rem}
.ko-card.bkl .ko-pct{font-size:.72rem}
.ko-card.bkl .ko-score{font-size:.7rem;padding:3px 4px}

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

/* ── Móvil ── */
@media (max-width:700px){
  header{padding:1.5rem 1rem .9rem}
  header h1{font-size:1.3rem}
  header p{font-size:.78rem}
  .container{padding:0 .75rem 4.5rem}
  .groups-grid{grid-template-columns:1fr;gap:1rem}
  .standings-table th:nth-child(5),.standings-table td:nth-child(5),
  .standings-table th:nth-child(6),.standings-table td:nth-child(6){display:none}
  .points-strip{gap:.9rem;font-size:.78rem}
  .champion-card{padding:1rem;gap:1rem}
  .bracket-wrap{display:none}
  #bracketList{display:block}
}
"""

# ---------------------------------------------------------------------------
# JS base del dashboard (render de grupos, campeón y bracket espejado)
# ---------------------------------------------------------------------------
BASE_JS = r"""
function getFlag(name) { return FLAGS[name] || '🏳'; }
function getCode(name) { return CODES[name] || (name || '').substring(0, 3).toUpperCase(); }
function ptsClass(p) { return p >= 4 ? 'pts-hi' : p >= 3 ? 'pts-mid' : p >= 1 ? 'pts-low' : 'pts-zero'; }
function icon(name, cls) {
  return `<svg class="lc${cls ? ' ' + cls : ''}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${LUCIDE[name]}</svg>`;
}

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
        <td><div class="team-name">${t.flag} ${t.name_es}${t.is_host ? ' ' + icon('house', 'lc-host') : ''}</div></td>
        <td>${t.w}</td><td>${t.d}</td><td>${t.l}</td>
        <td>${t.gf}</td><td>${t.ga}</td><td>${t.gf - t.ga > 0 ? '+' : ''}${t.gf - t.ga}</td>
        <td class="pts">${t.pts}</td>
        <td class="${mcCls}">${mc}%</td>
      </tr>`;
    }).join('');
    const matchRows = group.results.map(r => {
      const hostHome = r.host_team && r.home_raw.startsWith(r.host_team);
      const hostAway = r.host_team && r.away_raw.startsWith(r.host_team);
      let probsRow, scoreCls = 'm-score', sub, title;
      if (r.played) {
        probsRow = `<span class="m-prob ph"></span><span class="m-tag" style="text-align:center">${icon('check')} jugado</span><span class="m-prob pa"></span>`;
        scoreCls += ' real';
        sub = r.bet
          ? `<span class="m-bet">Apuesta ${r.bet}</span> <span class="pts-badge ${ptsClass(r.points)}">+${r.points}</span>`
          : '';
        title = `${r.home} vs ${r.away} · Resultado real ${r.score}` +
                (r.bet ? ` · Apuesta ${r.bet} → ${r.points} pts` : '');
      } else {
        probsRow = `<span class="m-prob ph">${Math.round(r.prob_h)}%</span>
        <span class="m-prob pd">${Math.round(r.prob_d)}%</span>
        <span class="m-prob pa">${Math.round(r.prob_a)}%</span>`;
        const ev = r.exp_pts != null ? `EV ${r.exp_pts.toFixed(1)}` : '';
        const manual = r.manual ? ` <span title="Apuesta fijada manualmente">${icon('pencil')}</span>` : '';
        sub = `${ev}${manual}`;
        title = `${r.home} vs ${r.away} · Local ${r.prob_h}% · Empate ${r.prob_d}% · Visita ${r.prob_a}%`;
      }
      return `
      <div class="match-block${r.manual ? ' match-manual' : ''}" title="${title}">
        ${probsRow}
        <span class="m-team home">${getCode(r.home_raw)}${hostHome ? ' ' + icon('house', 'lc-host') : ''} <span class="m-flag">${getFlag(r.home_raw)}</span></span>
        <span class="${scoreCls}">${r.score}</span>
        <span class="m-team away"><span class="m-flag">${getFlag(r.away_raw)}</span> ${getCode(r.away_raw)}${hostAway ? ' ' + icon('house', 'lc-host') : ''}</span>
        <span class="m-sub">${sub}</span>
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
      <div class="champion-trophy">${icon('trophy', 'lc-accent')}</div>
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

/* ── Tarjeta KO (compartida por bracket espejado y lista móvil) ── */
function koCardHTML(m) {
  const hw = m.winner === m.home, aw = m.winner === m.away;
  const res = m.went_et ? `${m.score} pen ${getCode(m.advancer)}` : m.score;
  let extra;
  if (m.played) {
    extra = m.points != null
      ? ` <span class="pts-badge ${ptsClass(m.points)}">+${m.points}</span>`
      : ` <span class="m-tag">${icon('check')}</span>`;
  } else {
    extra = (m.exp_pts != null ? ` <span class="ko-ev">EV ${m.exp_pts.toFixed(1)}</span>` : '') +
            (m.manual ? ` ${icon('pencil')}` : '');
  }
  const pct = side => m.played ? '' : `<span class="ko-pct">${side}%</span>`;
  return `
    <div class="ko-team ${hw ? 'winner' : ''}"><span class="ko-flag">${getFlag(m.home)}</span><span class="ko-name">${getCode(m.home)}</span>${pct(m.prob_h)}</div>
    <div class="ko-team ${aw ? 'winner' : ''}"><span class="ko-flag">${getFlag(m.away)}</span><span class="ko-name">${getCode(m.away)}</span>${pct(m.prob_a)}</div>
    <div class="ko-score"><span class="ko-res">${res}</span>${extra}${editKoControls(m)}</div>`;
}

function koCardTitle(m) {
  const base = `${m.home_es} vs ${m.away_es} · ${m.score}${m.went_et ? ` (pen: ${m.advancer_es})` : ''}`;
  if (m.played) {
    return base + ' · resultado real' +
           (m.bet ? ` · Apuesta ${m.bet}${m.bet_advancer ? ` (pen: ${getCode(m.bet_advancer)})` : ''} → ${m.points} pts` : '');
  }
  return base + ` · Local ${m.prob_h}% · Empate ${m.prob_d}% · Visita ${m.prob_a}%` +
         (m.exp_pts != null ? ` · EV ${m.exp_pts}` : '') +
         (m.manual ? ' · apuesta fijada manualmente' : '');
}

function koCardClass(m, extra) {
  return 'ko-card' + (m.played ? ' ko-played' : m.manual ? ' ko-manual' : '') + (extra || '');
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
      card.className = koCardClass(m, L.round === 'Final' ? ' ko-final' : '');
      card.style.left   = x(ci) + 'px';
      card.style.top    = (cy(L.span, i - L.from) - CARD_H / 2) + 'px';
      card.style.width  = W + 'px';
      card.style.height = CARD_H + 'px';
      card.innerHTML = koCardHTML(m);
      card.title = koCardTitle(m);
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

/* ── Bracket móvil: lista vertical por ronda ── */
function renderBracketList() {
  const list = document.getElementById('bracketList');
  const ORDER = [['R32', '16avos de final'], ['R16', 'Octavos de final'],
                 ['QF', 'Cuartos de final'], ['SF', 'Semifinales'], ['Final', 'Final']];
  ORDER.forEach(([key, label]) => {
    const t = document.createElement('div');
    t.className = 'bkl-title';
    t.innerHTML = key === 'Final' ? `${icon('trophy', 'lc-accent')} ${label}` : label;
    list.appendChild(t);
    BRACKET_DATA.rounds[key].forEach(m => {
      const card = document.createElement('div');
      card.className = koCardClass(m, ' bkl' + (key === 'Final' ? ' ko-final' : ''));
      card.innerHTML = koCardHTML(m);
      card.title = koCardTitle(m);
      list.appendChild(card);
    });
  });
}

/* ── Resumen de puntos polla (visible solo con partidos jugados) ── */
function renderPointsStrip() {
  let gp = 0, gn = 0, kp = 0, kn = 0;
  GROUPS_DATA.forEach(g => g.results.forEach(r => {
    if (r.played) { gn++; gp += r.points || 0; }
  }));
  Object.values(BRACKET_DATA.rounds).forEach(ms => ms.forEach(m => {
    if (m.played) { kn++; kp += m.points || 0; }
  }));
  const el = document.getElementById('pointsStrip');
  if (gn + kn === 0) { el.hidden = true; return; }
  el.hidden = false;
  const j = n => `${n} jugado${n === 1 ? '' : 's'}`;
  el.innerHTML = `<span class="ps-total">${icon('target', 'lc-green')} Puntos polla: <b>${gp + kp}</b></span>
    <span>Grupos: <b>${gp}</b> · ${j(gn)}</span>` +
    (kn ? `<span>Eliminatoria: <b>${kp}</b> · ${j(kn)}</span>` : '');
}

renderGroups();
renderChampionCard();
renderBracket();
renderBracketList();
renderPointsStrip();
"""


def build_html(groups_data, bracket_data, interactive=False):
    """Genera el HTML del dashboard.
    interactive=True (app.py) inyecta la UI de edición de resultados;
    con False (default) el HTML estático queda sin UI de edición."""
    gj = json.dumps(groups_data, ensure_ascii=False)
    bj = json.dumps(bracket_data, ensure_ascii=False)
    fj = json.dumps(FLAG_EMOJIS, ensure_ascii=False)
    cj = json.dumps(TEAM_CODES, ensure_ascii=False)
    lj = json.dumps(LUCIDE, ensure_ascii=False)
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
  <h1>{_icon("ball", "lc-title")} Polla <em>Mundial 2026</em></h1>
  <p>Simulador de predicciones · Monte Carlo 20.000 simulaciones</p>
</header>

<div class="container">
  <div id="pointsStrip" class="points-strip" hidden></div>
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
    <div id="bracketList"></div>
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
      en promedio con esa apuesta. Los overrides manuales permiten fijar cualquier marcador ({_icon("pencil")}).</p>
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
      <li><b>{_icon("house", "lc-host")}</b> — anfitrión jugando de local (México +20% · USA +13% · Canadá +10%).</li>
      <li><b>{_icon("pencil")}</b> — apuesta fijada manualmente por ti.</li>
      <li><b>{_icon("circle-check", "lc-green")} / marcador verde</b> — resultado real de un partido ya jugado; el modelo re-simula solo lo pendiente.</li>
      <li><b>Apuesta X-Y · +N</b> — en partidos jugados: tu apuesta congelada y los puntos de polla que ganó.</li>
      <li><b>{_icon("target", "lc-green")} Puntos polla</b> — suma de los puntos obtenidos en todos los partidos jugados.</li>
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
const LUCIDE = {lj};

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
