"""
results.py
==========
Resultados REALES de partidos ya jugados.

A diferencia de los overrides (que fijan la apuesta del escenario), un
resultado real representa lo que efectivamente pasó en la cancha:

  - Fija el marcador en el escenario determinista (tabla, terceros, bracket),
    con prioridad sobre cualquier override del mismo partido.
  - Condiciona el Monte Carlo: los partidos jugados no se sortean, se fijan
    (simulate_group_mc y bracket_mc re-simulan solo lo que falta).
  - Congela la apuesta vigente al momento de ingresarlo (snapshot `bet`),
    lo que permite calcular automáticamente los puntos de la polla
    (polla_points) comparando apuesta vs realidad.

Archivo de datos: modelo/data/results.json — JSON plano, pensado para que
un futuro front (TypeScript / escenario A) lo consuma directamente.
Estructura:
    {
      "groups": [{"home": str, "away": str, "score": [gh, ga],
                  "bet": [gh, ga] | null}],
      "ko":     [{"home": str, "away": str, "score": [gh, ga],
                  "advancer": str | null,
                  "bet": {"score": [gh, ga], "advancer": str | null} | null}]
    }
Los nombres son los nombres raw de la DB (columna `name` de `teams`).
Los lookups aceptan el par invertido (marcadores se voltean; los advancer
son nombres de equipo y no se voltean). En KO, `advancer` solo es necesario
si el marcador a 90' fue empate; con victoria se deriva del marcador.
"""

import json
import os

DATA_DIR     = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
RESULTS_PATH = os.path.join(DATA_DIR, "results.json")


# ---------------------------------------------------------------------------
# Lectura / escritura
# ---------------------------------------------------------------------------
def load_results():
    """Carga results.json. Si no existe, retorna estructura vacía."""
    if not os.path.exists(RESULTS_PATH):
        return {"groups": [], "ko": []}
    with open(RESULTS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("groups", [])
    data.setdefault("ko", [])
    return data


def save_results(data):
    """Guarda results.json (crea data/ si no existe)."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Lookups (tolerantes al orden del par)
# ---------------------------------------------------------------------------
def _match_pair(entry, home, away):
    """1 si la entrada coincide en orientación directa, -1 si invertida, 0 si no."""
    if entry["home"] == home and entry["away"] == away:
        return 1
    if entry["home"] == away and entry["away"] == home:
        return -1
    return 0


def _flip(score):
    return (int(score[1]), int(score[0]))


def group_result(home, away):
    """Retorna {"score": (gh, ga), "bet": (gh, ga)|None} para el par
    (home, away), o None si el partido no tiene resultado real.
    Marcadores volteados si la entrada está en orientación invertida."""
    for e in load_results()["groups"]:
        m = _match_pair(e, home, away)
        if m:
            score = tuple(int(x) for x in e["score"])
            bet   = tuple(int(x) for x in e["bet"]) if e.get("bet") else None
            if m == -1:
                score = _flip(score)
                bet   = _flip(bet) if bet else None
            return {"score": score, "bet": bet}
    return None


def ko_result(home, away):
    """Retorna {"score": (gh, ga), "advancer": str|None,
                "bet": {"score": (gh, ga), "advancer": str|None}|None}
    o None si el partido no tiene resultado real. Marcadores volteados si
    la orientación está invertida; los advancer (nombres) no se voltean."""
    for e in load_results()["ko"]:
        m = _match_pair(e, home, away)
        if m:
            score = tuple(int(x) for x in e["score"])
            bet = None
            if e.get("bet"):
                bet = {"score": tuple(int(x) for x in e["bet"]["score"]),
                       "advancer": e["bet"].get("advancer")}
            if m == -1:
                score = _flip(score)
                if bet:
                    bet["score"] = _flip(bet["score"])
            return {"score": score, "advancer": e.get("advancer"), "bet": bet}
    return None


# ---------------------------------------------------------------------------
# Escritura de resultados individuales
# ---------------------------------------------------------------------------
def set_group_result(home, away, gh, ga, bet=None):
    """Fija (o reemplaza) el resultado real de un partido de grupos.

    bet : [gh, ga] — apuesta vigente al ingresar el resultado. Si el partido
          ya tenía resultado con bet congelado, se PRESERVA el bet original
          (editar un marcador real no debe re-congelar la apuesta)."""
    data = load_results()
    prev = [e for e in data["groups"] if _match_pair(e, home, away)]
    if prev and prev[0].get("bet"):
        m = _match_pair(prev[0], home, away)
        bet = prev[0]["bet"] if m == 1 else list(_flip(prev[0]["bet"]))
    data["groups"] = [e for e in data["groups"] if not _match_pair(e, home, away)]
    data["groups"].append({"home": home, "away": away,
                           "score": [int(gh), int(ga)],
                           "bet": [int(bet[0]), int(bet[1])] if bet else None})
    save_results(data)


def set_ko_result(home, away, gh, ga, advancer=None, bet=None):
    """Fija (o reemplaza) el resultado real de un partido KO.

    advancer : nombre raw del que avanzó (obligatorio solo si gh == ga).
    bet      : {"score": [gh, ga], "advancer": str|None} — apuesta vigente.
               Igual que en grupos, un bet ya congelado se preserva."""
    data = load_results()
    prev = [e for e in data["ko"] if _match_pair(e, home, away)]
    if prev and prev[0].get("bet"):
        m = _match_pair(prev[0], home, away)
        pb = prev[0]["bet"]
        bet = pb if m == 1 else {"score": list(_flip(pb["score"])),
                                 "advancer": pb.get("advancer")}
    data["ko"] = [e for e in data["ko"] if not _match_pair(e, home, away)]
    data["ko"].append({"home": home, "away": away,
                       "score": [int(gh), int(ga)], "advancer": advancer,
                       "bet": ({"score": [int(bet["score"][0]), int(bet["score"][1])],
                                "advancer": bet.get("advancer")} if bet else None)})
    save_results(data)


def clear_results(home=None, away=None):
    """Sin argumentos: borra TODOS los resultados. Con (home, away): borra el
    resultado de ese par (cualquier orientación, grupos y KO).
    Retorna el número de resultados eliminados."""
    data = load_results()
    if home is None and away is None:
        n = len(data["groups"]) + len(data["ko"])
        save_results({"groups": [], "ko": []})
        return n
    n = 0
    for key in ("groups", "ko"):
        antes = len(data[key])
        data[key] = [e for e in data[key] if not _match_pair(e, home, away)]
        n += antes - len(data[key])
    save_results(data)
    return n
