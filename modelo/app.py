"""
app.py — Mini-app local para editar resultados desde el dashboard.
===================================================================
Servidor HTTP local (solo stdlib) que sirve el dashboard del Mundial 2026
con UI de edición en vivo:

  GET  /                → genera el HTML al vuelo con los datos actuales
                          (overrides incluidos). El Monte Carlo (la parte
                          cara) se calcula UNA vez al inicio y se cachea;
                          las partes deterministas se recalculan en cada GET.
  POST /api/override    → {"scope":"group"|"ko","home":raw,"away":raw,
                           "gh":int,"ga":int,"advancer":raw|null}
  POST /api/clear       → {"home":raw,"away":raw} o {"all":true}
  POST /api/recalc-mc   → recalcula el Monte Carlo del bracket con el R32
                          actual (puede tardar; responde al terminar).

Uso:
    python3 app.py [--port 8765] [--n-sims 5000] [--no-browser]
"""
import argparse
import json
import os
import sqlite3
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from predictor_v3 import DB_PATH, regenerate_db, simulate_group_mc, get_team
from simulate_knockout import compute_mc_odds
from dashboard import GROUPS, render_dashboard_html
from overrides import set_group_override, set_ko_override, clear_overrides, load_overrides

# ---------------------------------------------------------------------------
# Estado global del server (cache del Monte Carlo)
# ---------------------------------------------------------------------------
STATE = {
    "n_sims":   5000,
    "mc_odds":  None,   # probabilidades de campeón (bracket MC) — cacheado
    "group_mc": None,   # {grupo: finish_counts} — cacheado (no depende de overrides)
}
LOCK = threading.Lock()  # protege recálculos del MC


def init_state(n_sims):
    """Inicializa DB y calcula el Monte Carlo UNA vez (parte cara)."""
    STATE["n_sims"] = n_sims
    print("Inicializando DB...")
    regenerate_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        print(f"Monte Carlo de grupos ({n_sims:,} sims por grupo)...", end=" ", flush=True)
        group_mc = {}
        for g in GROUPS:
            fc, _, _ = simulate_group_mc(g, conn, n_sims=n_sims)
            group_mc[g] = fc
        STATE["group_mc"] = group_mc
        print("✓", flush=True)
        print(f"Monte Carlo del bracket ({n_sims:,} sims)...", end=" ", flush=True)
        STATE["mc_odds"] = compute_mc_odds(conn, n_sims=n_sims)
        print("✓", flush=True)
    finally:
        conn.close()


def render_html():
    """Genera el HTML interactivo con los datos actuales (overrides incluidos).
    Reutiliza el Monte Carlo cacheado; lo determinista se recalcula siempre."""
    conn = sqlite3.connect(DB_PATH)
    try:
        return render_dashboard_html(
            conn,
            mc_odds=STATE["mc_odds"],
            group_mc=STATE["group_mc"],
            interactive=True,
            verbose=False,
        )
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Validación / lógica de los endpoints
# ---------------------------------------------------------------------------
def _validate_team(conn, name):
    """Valida que el nombre raw exista en la tabla teams. Retorna el nombre
    raw canónico (acepta también name_es) o lanza ValueError."""
    if not name or not isinstance(name, str):
        raise ValueError("Falta el nombre del equipo")
    return get_team(conn, name)["name"]   # ValueError si no existe


def handle_override(body):
    scope = body.get("scope")
    if scope not in ("group", "ko"):
        return {"ok": False, "error": 'scope debe ser "group" o "ko"'}
    try:
        gh, ga = int(body.get("gh")), int(body.get("ga"))
    except (TypeError, ValueError):
        return {"ok": False, "error": "gh y ga deben ser enteros"}
    if gh < 0 or ga < 0 or gh > 20 or ga > 20:
        return {"ok": False, "error": "Marcador fuera de rango (0-20)"}

    conn = sqlite3.connect(DB_PATH)
    try:
        home = _validate_team(conn, body.get("home"))
        away = _validate_team(conn, body.get("away"))
        advancer = body.get("advancer")
        if scope == "ko":
            if gh == ga:
                if not advancer:
                    return {"ok": False, "error":
                            "advancer es obligatorio en partidos KO con empate"}
                advancer = _validate_team(conn, advancer)
                if advancer not in (home, away):
                    return {"ok": False, "error":
                            "advancer debe ser uno de los dos equipos del partido"}
            else:
                advancer = None   # con ganador en 90' el advancer es redundante
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()

    if scope == "group":
        set_group_override(home, away, gh, ga)
    else:
        set_ko_override(home, away, gh, ga, advancer=advancer)
    return {"ok": True, "scope": scope, "home": home, "away": away,
            "score": [gh, ga], "advancer": advancer}


def handle_clear(body):
    if body.get("all"):
        n = clear_overrides()
        return {"ok": True, "removed": n}
    home, away = body.get("home"), body.get("away")
    if not home or not away:
        return {"ok": False, "error": 'Se requiere {"home","away"} o {"all":true}'}
    n = clear_overrides(home, away)
    return {"ok": True, "removed": n}


def handle_recalc_mc():
    """Recalcula el Monte Carlo del bracket con el R32 actual (overrides
    incluidos). El MC de grupos no depende de overrides → no se recalcula."""
    with LOCK:
        conn = sqlite3.connect(DB_PATH)
        try:
            STATE["mc_odds"] = compute_mc_odds(conn, n_sims=STATE["n_sims"])
        finally:
            conn.close()
    return {"ok": True, "n_sims": STATE["n_sims"]}


# ---------------------------------------------------------------------------
# Servidor HTTP
# ---------------------------------------------------------------------------
class DashboardHandler(BaseHTTPRequestHandler):

    def _send(self, status, content_type, payload):
        data = payload.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, obj, status=200):
        self._send(status, "application/json", json.dumps(obj, ensure_ascii=False))

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            try:
                self._send(200, "text/html", render_html())
            except Exception as e:
                self._send_json({"ok": False, "error": f"Error generando dashboard: {e}"}, 500)
        elif self.path == "/api/overrides":
            # Conveniencia: estado actual de overrides.json
            self._send_json({"ok": True, "overrides": load_overrides()})
        else:
            self._send_json({"ok": False, "error": "Ruta no encontrada"}, 404)

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(body, dict):
                raise ValueError("el body debe ser un objeto JSON")
        except (ValueError, json.JSONDecodeError) as e:
            self._send_json({"ok": False, "error": f"JSON inválido: {e}"}, 400)
            return

        try:
            if self.path == "/api/override":
                resp = handle_override(body)
            elif self.path == "/api/clear":
                resp = handle_clear(body)
            elif self.path == "/api/recalc-mc":
                resp = handle_recalc_mc()
            else:
                self._send_json({"ok": False, "error": "Ruta no encontrada"}, 404)
                return
        except Exception as e:
            self._send_json({"ok": False, "error": str(e)}, 500)
            return
        self._send_json(resp, 200 if resp.get("ok") else 400)

    def log_message(self, fmt, *args):
        print(f"  [{self.log_date_time_string()}] {fmt % args}")


def main():
    ap = argparse.ArgumentParser(
        description="Dashboard interactivo local — Polla Mundial 2026")
    ap.add_argument("--port", type=int, default=8765, help="Puerto (default 8765)")
    ap.add_argument("--n-sims", type=int, default=5000,
                    help="Simulaciones Monte Carlo (default 5000)")
    ap.add_argument("--no-browser", action="store_true",
                    help="No abrir el navegador automáticamente")
    args = ap.parse_args()

    init_state(args.n_sims)

    url = f"http://127.0.0.1:{args.port}/"
    httpd = ThreadingHTTPServer(("127.0.0.1", args.port), DashboardHandler)
    print(f"\n✅ Dashboard interactivo en {url}", flush=True)
    print("   Ctrl+C para detener.\n", flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nDeteniendo servidor...")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
