"""
dashboard.py — v3.1 + Bracket eliminatorio
Genera dashboard HTML con grupos y bracket de fase eliminatoria.
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
HOST_TEAMS = {"Mexico","USA","Canada"}


def build_html(groups_data, bracket_data):
    gj = json.dumps(groups_data, ensure_ascii=False)
    bj = json.dumps(bracket_data, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Polla Mundial 2026 — Predicciones v3.2</title>
<style>
:root {{
  --bg:#0f172a;--card:#1e293b;--border:#334155;
  --text:#f1f5f9;--muted:#94a3b8;--accent:#f59e0b;
  --green:#10b981;--red:#ef4444;--blue:#3b82f6;--host:#f97316;
  --purple:#8b5cf6;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif}}
header{{background:linear-gradient(135deg,#1e3a5f,#0f172a);padding:2rem;text-align:center;border-bottom:2px solid var(--accent)}}
header h1{{font-size:2rem;color:var(--accent);letter-spacing:2px}}
header p{{color:var(--muted);margin-top:.5rem;font-size:.9rem}}
.container{{max-width:1400px;margin:0 auto;padding:2rem 1rem}}
.tab-bar{{display:flex;gap:.5rem;margin-bottom:1.5rem;flex-wrap:wrap}}
.tab{{padding:.4rem 1rem;border-radius:6px;border:1px solid var(--border);cursor:pointer;font-size:.85rem;background:var(--card);color:var(--muted);transition:all .2s}}
.tab.active,.tab:hover{{background:var(--accent);color:#000;border-color:var(--accent);font-weight:600}}
.tab-content{{display:none}}.tab-content.active{{display:block}}
.model-info{{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:1rem 1.5rem;margin-bottom:1.5rem;font-size:.83rem;color:var(--muted)}}
.model-info strong{{color:var(--accent)}}
.legend{{display:flex;gap:1.5rem;margin-bottom:1rem;flex-wrap:wrap;font-size:.8rem}}
.legend-item{{display:flex;align-items:center;gap:.4rem;color:var(--muted)}}
.legend-box{{width:12px;height:12px;border-radius:3px}}
.groups-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:1.5rem}}
.group-card{{background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden}}
.group-header{{padding:.75rem 1rem;background:var(--border);display:flex;align-items:center;gap:.75rem}}
.group-letter{{font-size:1.5rem;font-weight:900;color:var(--accent)}}
.standings-table{{width:100%;border-collapse:collapse;font-size:.82rem}}
.standings-table th{{padding:.4rem;color:var(--muted);text-align:right;font-weight:500;font-size:.75rem}}
.standings-table th:first-child{{text-align:left}}
.standings-table td{{padding:.4rem;border-top:1px solid var(--border);text-align:right}}
.standings-table td:first-child{{text-align:left}}
.standings-table tr.qualified td{{background:rgba(16,185,129,.10)}}
.standings-table tr.qualified-3rd td{{background:rgba(245,158,11,.08)}}
.team-name{{display:flex;align-items:center;gap:.35rem;font-weight:500}}
.pts{{font-weight:700;color:var(--accent)}}
.mc-pct{{font-size:.72rem;color:var(--green);font-weight:600}}
.mc-pct.low{{color:var(--muted)}}
.conf-badge{{display:inline-block;font-size:.65rem;padding:1px 5px;border-radius:3px;color:white;font-weight:700;white-space:nowrap}}
.matches-section{{padding:.75rem 1rem;border-top:1px solid var(--border)}}
.matches-section h4{{font-size:.72rem;text-transform:uppercase;color:var(--muted);letter-spacing:1px;margin-bottom:.5rem}}
.match-row{{display:flex;align-items:center;padding:.28rem 0;font-size:.8rem;gap:.3rem;border-bottom:1px solid rgba(51,65,85,.4)}}
.match-row:last-child{{border-bottom:none}}
.match-teams{{flex:1;display:flex;justify-content:space-between;align-items:center;gap:.3rem}}
.match-home{{text-align:right;flex:1;font-size:.78rem}}
.match-score{{font-weight:700;color:var(--accent);padding:2px 6px;min-width:3rem;text-align:center;background:var(--border);border-radius:4px;font-size:.82rem}}
.match-away{{flex:1;font-size:.78rem}}
.match-meta{{font-size:.68rem;color:var(--muted);white-space:nowrap;text-align:right}}
.third-note{{font-size:.73rem;color:var(--muted);padding:.4rem 1rem;font-style:italic}}
footer{{text-align:center;padding:2rem;color:var(--muted);font-size:.8rem;border-top:1px solid var(--border);margin-top:3rem}}

/* ── Bracket ── */
.bracket-wrap{{overflow-x:auto;padding-bottom:1rem}}
.champion-card{{background:linear-gradient(135deg,rgba(245,158,11,.15),rgba(16,185,129,.08));border:2px solid var(--accent);border-radius:12px;padding:1.5rem 2rem;margin-bottom:2rem;display:flex;align-items:center;gap:2rem;flex-wrap:wrap}}
.champion-trophy{{font-size:3rem}}
.champion-info h2{{font-size:1.4rem;color:var(--accent)}}
.champion-info p{{color:var(--muted);font-size:.85rem;margin-top:.25rem}}
.odds-grid{{display:flex;gap:1rem;flex-wrap:wrap;flex:1}}
.odds-row{{flex:1;min-width:220px;max-width:340px}}
.odds-team{{display:flex;align-items:center;gap:.5rem;margin-bottom:.35rem;font-size:.82rem}}
.odds-flag{{width:1.4em;text-align:center}}
.odds-name{{flex:1;font-weight:500}}
.odds-prob{{font-weight:700;color:var(--accent);min-width:3.5em;text-align:right}}
.odds-bar-bg{{background:var(--border);border-radius:3px;height:5px;margin-bottom:.6rem;overflow:hidden}}
.odds-bar-fill{{height:100%;border-radius:3px;background:linear-gradient(90deg,var(--accent),var(--green));transition:width .3s}}

.bracket-note{{font-size:.78rem;color:var(--muted);margin-bottom:1rem;background:var(--card);border:1px solid var(--border);border-radius:6px;padding:.6rem 1rem}}
.bracket-rounds{{display:flex;gap:0;min-width:1100px}}
.round-col{{flex:0 0 200px;position:relative}}
.round-header{{text-align:center;font-size:.72rem;text-transform:uppercase;letter-spacing:1px;color:var(--accent);font-weight:700;padding:.4rem;height:32px;background:var(--card);border-bottom:1px solid var(--border);border-right:1px solid var(--border)}}
.round-body{{position:relative;border-right:1px solid var(--border)}}
.ko-card{{position:absolute;left:4px;right:4px;background:var(--card);border:1px solid var(--border);border-radius:6px;overflow:hidden;font-size:.71rem;cursor:default;transition:border-color .15s}}
.ko-card:hover{{border-color:var(--accent);z-index:10}}
.ko-card.sec-a{{border-left:3px solid var(--blue)}}
.ko-card.sec-b{{border-left:3px solid var(--green)}}
.ko-card.sec-c{{border-left:3px solid var(--host)}}
.ko-card.sec-d{{border-left:3px solid var(--purple)}}
.ko-card.sec-sf{{border-left:3px solid var(--accent)}}
.ko-card.sec-final{{border-left:3px solid #ec4899;border:2px solid #ec4899}}
.ko-team{{display:flex;align-items:center;gap:.25rem;padding:3px 5px}}
.ko-team.winner{{background:rgba(245,158,11,.12);font-weight:700}}
.ko-team.winner .ko-name{{color:var(--accent)}}
.ko-flag{{width:1.1em;text-align:center;flex-shrink:0}}
.ko-name{{flex:1;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}}
.ko-pct{{font-size:.67rem;color:var(--muted);white-space:nowrap}}
.ko-team.winner .ko-pct{{color:var(--green);font-weight:700}}
.ko-divider{{height:1px;background:var(--border);margin:0 4px}}
.ko-score{{text-align:center;font-size:.65rem;color:var(--muted);padding:1px 4px}}
.ko-score span{{color:var(--accent);font-weight:700}}
.connector-right{{position:absolute;right:-1px;width:8px;border-top:1px solid var(--muted);top:50%}}
</style>
</head>
<body>
<header>
  <h1>⚽ POLLA MUNDIAL 2026</h1>
  <p>Modelo v3.2 · Poisson + Dixon-Coles (ρ=−0.10) · ELO^2.8/2.1 · Resultado dominante → marcador · Calibrado 9 jun 2026</p>
</header>

<div class="container">
  <div class="tab-bar">
    <div class="tab active" onclick="showTab('grupos',this)">📊 Grupos</div>
    <div class="tab" onclick="showTab('bracket',this)">🏆 Bracket</div>
    <div class="tab" onclick="showTab('info',this)">ℹ️ Metodología</div>
  </div>

  <!-- ────── TAB GRUPOS ────── -->
  <div id="grupos" class="tab-content active">
    <div class="model-info">
      <strong>Modelo v3.2:</strong> ELO exponente 2.8/2.1 (calibrado 9 jun 2026 · 19 amistosos + 12 cuotas mercado) ·
      Forma ±25% cap · Ventaja local: 🇲🇽 +20% / 🇺🇸 +13% / 🇨🇦 +10% ·
      Dixon-Coles ρ=−0.10 · Marcador: resultado dominante → mejor marcador en esa categoría (margen ≥5pp) ·
      <strong>%Clasif</strong> = Monte Carlo 20,000 simulaciones · Validación: 79% dir · 74% top-3 · 42% exacto
    </div>
    <div class="legend">
      <div class="legend-item"><div class="legend-box" style="background:rgba(16,185,129,.4)"></div> Clasifican directo (1° y 2°)</div>
      <div class="legend-item"><div class="legend-box" style="background:rgba(245,158,11,.3)"></div> Posible mejor 3°</div>
      <div class="legend-item">🏠 = Ventaja de local anfitrión</div>
    </div>
    <div class="groups-grid" id="groupsContainer"></div>
  </div>

  <!-- ────── TAB BRACKET ────── -->
  <div id="bracket" class="tab-content">

    <div id="championCard" class="champion-card"></div>

    <div class="bracket-note">
      <strong>Empates en eliminatoria:</strong>
      90 min → Prórroga (λ×0.45, 30 min) → Penales muerte súbita (76% conversión por tiro) ·
      Determinista: gana el equipo con mayor probabilidad de victoria (proxy de favoritismo en prórroga) ·
      <strong>MC:</strong> se simula el resultado completo incluyendo penales
      <br>
      <strong>Bracket:</strong> fixture oficial FIFA 2026 · Annex C aplicado para combinación de 3eros B,C,D,E,F,G,I,L ·
      Colores por sección: <span style="color:var(--blue)">■ A→QF1</span>
      <span style="color:var(--green)"> ■ B→QF2</span>
      <span style="color:var(--host)"> ■ C→QF3</span>
      <span style="color:var(--purple)"> ■ D→QF4</span>
    </div>

    <div class="bracket-wrap">
      <div class="bracket-rounds" id="bracketRounds"></div>
    </div>
  </div>

  <!-- ────── TAB INFO ────── -->
  <div id="info" class="tab-content">
    <div style="max-width:700px;line-height:1.75;color:var(--muted)">
      <h3 style="color:var(--text);margin-bottom:1rem">Metodología v3.1</h3>
      <p><strong style="color:var(--accent)">Base ELO:</strong> Fuerza relativa de cada selección.
      Exponentes ataque/defensa = 2.8/2.1 (calibrados el 9 jun 2026 por grid search sobre 19
      amistosos + 12 cuotas de mercado). Curazao tiene λ≈0.52 vs Alemania.</p><br>
      <p><strong style="color:var(--accent)">Forma reciente:</strong> Score 1-10, capped ±25%.
      Eliminado el multiplicador sin límite (v2 daba ×1.8 para forma 9).</p><br>
      <p><strong style="color:var(--accent)">Ventaja de local:</strong> México +20%/−13%,
      USA +13%/−6%, Canadá +10%/−5%. Basado en Pollard (2006): ~0.3 goles adicionales
      para el anfitrión mundialista. Incluye efecto arbitral.</p><br>
      <p><strong style="color:var(--accent)">Dixon-Coles ρ=−0.10:</strong> Calibrado para
      fútbol internacional. Ajusta la probabilidad de marcadores bajos (0-0, 1-0, 0-1).</p><br>
      <p><strong style="color:var(--accent)">Monte Carlo 20,000 iter.:</strong> % de clasificación
      real, no solo el marcador modal. Empates en eliminatoria se resuelven con prórroga y penales.</p><br>
      <p><strong style="color:var(--accent)">Selección de marcador (v3.2):</strong> En vez del marcador
      individual más probable (que tiende al 1-1 en duelos equilibrados), el modelo elige primero el
      <em>resultado dominante</em> (victoria local/empate/visita por prob. acumulada). Si la diferencia
      entre prob. local y visitante es menor a 5pp, el partido se trata como empate. Luego se elige el
      mejor marcador dentro de esa categoría. Esto alinea los pronósticos con el histórico mundialista:
      ~15% de 1-1 en eliminatorias (1990–2022), no el 84% que generaba v3.1.</p>
    </div>
  </div>
</div>

<footer>Polla Mundial 2026 · Predictor v3.2 · Calibrado 9 jun 2026 · Monte Carlo 20k sims · Result-first scoring</footer>

<script>
const GROUPS_DATA = {gj};
const BRACKET_DATA = {bj};

const FLAGS = {json.dumps(FLAG_EMOJIS, ensure_ascii=False)};
const CONF_COLORS = {{"UEFA":"#3b82f6","CONMEBOL":"#10b981","CONCACAF":"#f59e0b","AFC":"#ef4444","CAF":"#8b5cf6","OFC":"#6b7280"}};

function getFlag(name) {{ return FLAGS[name] || '🏳'; }}

function showTab(id, el) {{
  document.querySelectorAll('.tab-content').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  el.classList.add('active');
}}

/* ── Groups ── */
function renderGroups() {{
  const c = document.getElementById('groupsContainer');
  GROUPS_DATA.forEach(group => {{
    const card = document.createElement('div');
    card.className = 'group-card';
    const rows = group.standings.map((t,i) => {{
      const rc = i<2?'qualified':(i===2?'qualified-3rd':'');
      const cc = CONF_COLORS[t.confederation]||'#6b7280';
      const mc = t.mc_clasif||0;
      const mcCls = mc>60?'mc-pct':'mc-pct low';
      return `<tr class="${{rc}}">
        <td><div class="team-name">
          <span class="conf-badge" style="background:${{cc}}">${{t.confederation?.substring(0,3)}}</span>
          ${{t.flag}}${{t.is_host?' 🏠':''}} ${{t.name_es}}
        </div></td>
        <td>${{t.w}}</td><td>${{t.d}}</td><td>${{t.l}}</td>
        <td>${{t.gf}}</td><td>${{t.ga}}</td><td>${{t.gf-t.ga>0?'+':''}}${{t.gf-t.ga}}</td>
        <td class="pts">${{t.pts}}</td>
        <td class="${{mcCls}}">${{mc}}%</td>
      </tr>`;
    }}).join('');
    const matchRows = group.results.map(r => `
      <div class="match-row">
        <div class="match-teams">
          <span class="match-home">${{r.home}}</span>
          <span class="match-score">${{r.score}}</span>
          <span class="match-away">${{r.away}}</span>
        </div>
        <span class="match-meta">${{r.prob_h}}·${{r.prob_d}}·${{r.prob_a}}${{r.host_team?`<span style="color:var(--host)"> 🏠${{r.host_team}}</span>`:''}}</span>
      </div>`).join('');
    card.innerHTML = `
      <div class="group-header">
        <span class="group-letter">${{group.group}}</span>
        <span style="color:var(--muted);font-size:.82rem">${{group.standings.map(t=>t.flag+' '+t.name_es).join(' · ')}}</span>
      </div>
      <table class="standings-table">
        <thead><tr><th>Equipo</th><th>G</th><th>E</th><th>P</th><th>GF</th><th>GC</th><th>DG</th><th>PTS</th><th>MC%</th></tr></thead>
        <tbody>${{rows}}</tbody>
      </table>
      <div class="third-note">🔶 3° puede clasificar como mejor tercero · MC% = % clasif. directo (Monte Carlo)</div>
      <div class="matches-section">
        <h4>Partidos (Local% · Empate% · Visit%)</h4>
        ${{matchRows}}
      </div>`;
    c.appendChild(card);
  }});
}}

/* ── Champion odds ── */
function renderChampionCard() {{
  const odds = BRACKET_DATA.mc_odds;
  const champion = BRACKET_DATA.champion_es;
  const champFlag = getFlag(BRACKET_DATA.champion);
  const maxProb = odds[0]?.prob || 1;

  const top8 = odds.slice(0, 8);
  const col1 = top8.slice(0, 4);
  const col2 = top8.slice(4, 8);

  function makeOddsRows(list) {{
    return list.map(t => `
      <div class="odds-team">
        <span class="odds-flag">${{getFlag(t.name)}}</span>
        <span class="odds-name">${{t.name_es}}</span>
        <span class="odds-prob">${{t.prob}}%</span>
      </div>
      <div class="odds-bar-bg"><div class="odds-bar-fill" style="width:${{(t.prob/maxProb*100).toFixed(1)}}%"></div></div>
    `).join('');
  }}

  document.getElementById('championCard').innerHTML = `
    <div style="display:flex;align-items:center;gap:1rem">
      <div class="champion-trophy">🏆</div>
      <div class="champion-info">
        <h2>${{champFlag}} ${{champion}}</h2>
        <p>Campeón predicho · ${{(odds.find(t=>t.name===BRACKET_DATA.champion)||{{prob:0}}).prob}}% MC</p>
        <p style="font-size:.75rem;margin-top:.3rem">Monte Carlo 20k · λ×0.90 eliminatoria</p>
      </div>
    </div>
    <div class="odds-grid">
      <div class="odds-row">${{makeOddsRows(col1)}}</div>
      <div class="odds-row">${{makeOddsRows(col2)}}</div>
    </div>`;
}}

/* ── Bracket visual ── */
function renderBracket() {{
  const ROUNDS  = ['R32','R16','QF','SF','Final'];
  const LABELS  = {{R32:'Dieciseisavos',R16:'Octavos',QF:'Cuartos',SF:'Semis',Final:'Final 🏆'}};
  const SPANS   = {{R32:1,R16:2,QF:4,SF:8,Final:16}};
  const SLOT    = 60;   // px per R32 slot
  const CARD_H  = 56;   // px card height
  const TOTAL   = 16 * SLOT;
  const HDR_H   = 32;

  const container = document.getElementById('bracketRounds');

  function sectionClass(round, idx) {{
    if (round==='SF') return 'sec-sf';
    if (round==='Final') return 'sec-final';
    const n = BRACKET_DATA.rounds[round].length;
    const s = Math.floor(idx / (n / 4));
    return ['sec-a','sec-b','sec-c','sec-d'][Math.min(s,3)];
  }}

  ROUNDS.forEach(round => {{
    const col  = document.createElement('div');
    col.className = 'round-col';

    const hdr = document.createElement('div');
    hdr.className = 'round-header';
    hdr.textContent = LABELS[round];
    col.appendChild(hdr);

    const body = document.createElement('div');
    body.className = 'round-body';
    body.style.height = TOTAL + 'px';

    const matches = BRACKET_DATA.rounds[round];
    const span    = SPANS[round];

    matches.forEach((m, i) => {{
      const centerY = (span * i + span / 2) * SLOT;
      const top     = Math.round(centerY - CARD_H / 2);

      const card = document.createElement('div');
      card.className = `ko-card ${{sectionClass(round, i)}}`;
      card.style.top  = top + 'px';
      card.style.height = CARD_H + 'px';

      const hw = m.winner === m.home;
      const aw = m.winner === m.away;
      const scoreDisp = m.went_et ? `${{m.score}} <span style="color:var(--muted);font-weight:400">(ET/Pen)</span>` : `<span>${{m.score}}</span>`;

      card.innerHTML = `
        <div class="ko-team ${{hw?'winner':''}}">
          <span class="ko-flag">${{getFlag(m.home)}}</span>
          <span class="ko-name">${{m.home_es}}</span>
          <span class="ko-pct">${{m.prob_h}}%</span>
        </div>
        <div class="ko-divider"></div>
        <div class="ko-team ${{aw?'winner':''}}">
          <span class="ko-flag">${{getFlag(m.away)}}</span>
          <span class="ko-name">${{m.away_es}}</span>
          <span class="ko-pct">${{m.prob_a}}%</span>
        </div>
        <div class="ko-score">${{scoreDisp}} <span style="color:var(--muted)">·</span> E${{m.prob_d}}%</div>`;

      card.title = `${{m.home_es}} vs ${{m.away_es}} | ${{m.score}}${{m.went_et?' (ET/Pen)':''}} | L:${{m.prob_h}}% E:${{m.prob_d}}% V:${{m.prob_a}}%`;

      body.appendChild(card);
    }});

    col.appendChild(body);
    container.appendChild(col);
  }});
}}

renderGroups();
renderChampionCard();
renderBracket();
</script>
</body>
</html>"""


def generate_dashboard():
    print("Inicializando DB...")
    regenerate_db()
    conn = sqlite3.connect(DB_PATH)

    from predictor_v3 import MATCH_VENUES, HOST_ADVANTAGE

    # ── Fase de grupos ──
    all_groups = []
    for g in GROUPS:
        print(f"  Grupo {g}...", end=" ", flush=True)
        sorted_teams, results = simulate_group(g, conn=conn, verbose=False)
        finish_counts, _, _   = simulate_group_mc(g, conn, n_sims=MC_SIMS)
        cur = conn.cursor()
        for t in sorted_teams:
            cur.execute("SELECT confederation FROM teams WHERE name=?", (t["name"],))
            row = cur.fetchone()
            t["confederation"] = row[0] if row else ""
            t["flag"]    = FLAG_EMOJIS.get(t["name"], "🏳")
            t["is_host"] = t["name"] in HOST_TEAMS
            fc = finish_counts.get(t["name"], [0,0,0,0])
            t["mc_clasif"] = round((fc[0]+fc[1]) / MC_SIMS * 100, 1)
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

    # ── Bracket eliminatorio ──
    print("  Bracket eliminatorio (MC 20k)...", end=" ", flush=True)
    bracket = get_bracket_data(conn, n_sims=MC_SIMS)
    print("✓")

    conn.close()
    html = build_html(all_groups, bracket)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n✅ Dashboard generado: {OUTPUT_PATH}")
    return OUTPUT_PATH


if __name__ == "__main__":
    generate_dashboard()
