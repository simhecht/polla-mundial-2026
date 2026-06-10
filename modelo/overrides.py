"""
overrides.py
============
Overrides manuales de resultados para el escenario determinista.

Permite fijar a mano el marcador (y en eliminatoria, quién avanza) de
cualquier partido. El override se aplica dentro de simulate_group /
predict_ko_match, por lo que cascadea automáticamente a la tabla del grupo,
al ranking de terceros y al bracket completo (build_r32 deriva todo de
simulate_group).

IMPORTANTE: los overrides NO tocan el Monte Carlo (simulate_group_mc,
sim_ko_match_mc, bracket_mc) — las probabilidades siguen siendo del modelo;
el override solo fija la apuesta/escenario determinista.

Archivo de datos: modelo/data/overrides.json
Estructura:
    {
      "groups": [{"home": str, "away": str, "score": [gh, ga]}],
      "ko":     [{"home": str, "away": str, "score": [gh, ga],
                  "advancer": str | null}]
    }
Los nombres son los nombres raw de la DB (columna `name` de `teams`).
Los lookups aceptan el par invertido: si está guardado como (B, A) y se
consulta (A, B), se retorna el marcador volteado. El advancer es un nombre
de equipo, por lo que no se voltea.
"""

import json
import os

DATA_DIR       = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OVERRIDES_PATH = os.path.join(DATA_DIR, "overrides.json")


# ---------------------------------------------------------------------------
# Lectura / escritura
# ---------------------------------------------------------------------------
def load_overrides():
    """Carga overrides.json. Si no existe, retorna estructura vacía."""
    if not os.path.exists(OVERRIDES_PATH):
        return {"groups": [], "ko": []}
    with open(OVERRIDES_PATH, encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("groups", [])
    data.setdefault("ko", [])
    return data


def save_overrides(data):
    """Guarda overrides.json (crea data/ si no existe)."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OVERRIDES_PATH, "w", encoding="utf-8") as f:
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


def group_override(home, away):
    """Retorna (gh, ga) para el par (home, away) o None si no hay override.
    Si el override está guardado en orientación invertida, voltea el marcador."""
    for e in load_overrides()["groups"]:
        m = _match_pair(e, home, away)
        if m == 1:
            return (int(e["score"][0]), int(e["score"][1]))
        if m == -1:
            return (int(e["score"][1]), int(e["score"][0]))
    return None


def ko_override(home, away):
    """Retorna {"score": (gh, ga), "advancer": str|None} o None si no hay
    override. El marcador se voltea si la orientación está invertida; el
    advancer es nombre de equipo y no se voltea."""
    for e in load_overrides()["ko"]:
        m = _match_pair(e, home, away)
        if m:
            gh, ga = int(e["score"][0]), int(e["score"][1])
            score = (gh, ga) if m == 1 else (ga, gh)
            return {"score": score, "advancer": e.get("advancer")}
    return None


# ---------------------------------------------------------------------------
# Escritura de overrides individuales
# ---------------------------------------------------------------------------
def set_group_override(home, away, gh, ga):
    """Fija (o reemplaza) el override de grupo para el par (home, away)."""
    data = load_overrides()
    data["groups"] = [e for e in data["groups"] if not _match_pair(e, home, away)]
    data["groups"].append({"home": home, "away": away,
                           "score": [int(gh), int(ga)]})
    save_overrides(data)


def set_ko_override(home, away, gh, ga, advancer=None):
    """Fija (o reemplaza) el override KO para el par (home, away).
    advancer: nombre raw del equipo que avanza (requerido solo si gh == ga)."""
    data = load_overrides()
    data["ko"] = [e for e in data["ko"] if not _match_pair(e, home, away)]
    data["ko"].append({"home": home, "away": away,
                       "score": [int(gh), int(ga)], "advancer": advancer})
    save_overrides(data)


def clear_overrides(home=None, away=None):
    """Sin argumentos: borra TODOS los overrides. Con (home, away): borra los
    overrides de ese par (cualquier orientación, grupos y KO).
    Retorna el número de overrides eliminados."""
    data = load_overrides()
    if home is None and away is None:
        n = len(data["groups"]) + len(data["ko"])
        save_overrides({"groups": [], "ko": []})
        return n
    n = 0
    for key in ("groups", "ko"):
        antes = len(data[key])
        data[key] = [e for e in data[key] if not _match_pair(e, home, away)]
        n += antes - len(data[key])
    save_overrides(data)
    return n
