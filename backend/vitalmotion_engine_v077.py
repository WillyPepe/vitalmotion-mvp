

"""
VitalMotion MVP v0.7.7 — SQLite Connected Engine
Uses full SQLite catalog: 10_CATALOGO_E, 11_CATALOGO_I, 12_CATALOGO_C, 13_CATALOGO_S.
No repeated exercise IDs in one session across all blocks.
"""
from __future__ import annotations
import sqlite3, math, random, os
from typing import Dict, Any, List, Tuple, Set

DB_DEFAULT = os.environ.get("VITALMOTION_DB", "VitalMotion_v20_5_MVP_v076_NO_REPEAT_ENGINE.sqlite")

EQUIP_MAP = {
    "silla":"sin_equipamiento", "puedo ir al piso":"sin_equipamiento", "bandas":"banda_elastica",
    "mancuernas":"mancuernas", "barra/discos":"barra", "barras/discos":"barra", "kettlebell":"kettlebell",
    "polea alta":"cable_polea", "banco multiposiciones":"banco", "multiestacion":"maquina", "gimnasio":"maquina", "nada":"sin_equipamiento"
}
ZONE_MAP = {
    "cuello":"Cervical", "cervical":"Cervical", "dorsal":"Dorsal", "lumbar":"Lumbar",
    "espalda alta":"Dorsal", "espalda baja":"Lumbar", "hombro":"Hombro", "rodilla":"Rodilla",
    "cadera":"Cadera_Pelvis", "ingle":"Pubica_Inguinal", "gluteo":"Gluteos", "tobillo":"Tobillo_Pie",
    "pie":"Tobillo_Pie", "pantorrilla":"Pierna", "pierna pantorrilla":"Pierna", "pierna alta":"Muslo",
    "codo":"Codo", "muñeca":"Muneca_Mano", "muneca":"Muneca_Mano", "mano":"Muneca_Mano",
    "abdomen":"Abdomen_Core", "abdominal":"Abdomen_Core", "pecho":"Pecho", "brazo biceps/triceps":"Brazo",
    "antebrazo":"Antebrazo", "cabeza":"Cervical"
}

def _connect(db_path: str | None = None):
    path = db_path or DB_DEFAULT
    if not os.path.isabs(path):
        path = os.path.join(os.path.dirname(__file__), path)
        if not os.path.exists(path):
            path = os.path.join('/mnt/data', os.path.basename(path))
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    return con

def catalog_counts(db_path: str | None=None) -> Dict[str,int]:
    con=_connect(db_path); cur=con.cursor()
    tables = {"strength":"10_CATALOGO_E","isometrics":"11_CATALOGO_I","warmups":"12_CATALOGO_C","stretches":"13_CATALOGO_S"}
    out={k:cur.execute(f'SELECT COUNT(*) FROM "{v}"').fetchone()[0] for k,v in tables.items()}
    out["total"] = sum(out.values())
    out["integrity_check"] = cur.execute('PRAGMA integrity_check').fetchone()[0]
    con.close(); return out

def _rows(con, table: str, where: str="", params: Tuple=(), limit: int=5000) -> List[Dict[str,Any]]:
    q=f'SELECT * FROM "{table}" {where} LIMIT {limit}'
    return [dict(r) for r in con.execute(q, params).fetchall()]



def _clamp(v, lo, hi):
    try:
        v=float(v)
    except:
        return lo
    return max(lo, min(hi, v))

def _int(x, default=0):
    try: return int(float(x or 0))
    except Exception: return default

def _bmi(weight, height):
    try:
        h = float(height)/100
        return round(float(weight)/(h*h),1) if h>0 else 0
    except Exception: return 0

def _normalize_equipment(items):
    if not items: return {"sin_equipamiento"}
    out=set()
    for it in items:
        key=str(it).strip().lower()
        out.add(EQUIP_MAP.get(key, key.replace(" ","_")))
        if key in ("gimnasio","multiestacion"):
            out.update({"maquina","cable_polea","banco","mancuernas","barra","kettlebell","sin_equipamiento","banda_elastica"})
    out.add("sin_equipamiento")
    return out

def _clinical_time_governance(p: Dict[str,Any]) -> Dict[str,Any]:
    age=_int(p.get('age') or p.get('edad'), 40); energy=_int(p.get('energy') or p.get('energia'), 7)
    tp=max(20, min(120, _int(p.get('requested_time_min') or p.get('tp') or p.get('tiempo'), 60)))
    bmi=_bmi(p.get('weight_kg') or p.get('peso'), p.get('height_cm') or p.get('altura'))
    pains=p.get('pains') or p.get('dolencias') or []
    pain_max=max([_int(d.get('level') or d.get('dolor') or d.get('dolor_0_10')) for d in pains] or [0])
    conditions=set([str(c).lower() for c in (p.get('conditions') or p.get('condiciones') or [])])
    red_flags=[]; barriers=[]; score=0
    if age < 18 or age > 90:
        red_flags.append("age_out_of_scope")
    if any(x in conditions for x in ["dolor pecho","síncope/mareos severos","sincope/mareos severos","déficit neurológico progresivo","deficit neurologico progresivo","posoperatorio sin alta"]):
        red_flags.append("hard_red_flag")
    if pain_max>=8: score+=45; barriers.append("dolor severo: sesión mínima o derivación si hay síntomas de alarma")
    elif pain_max>=6: score+=25; barriers.append("dolor 6–7: se reduce volumen y se prioriza tolerancia")
    elif pain_max>=4: score+=12; barriers.append("dolor moderado: se controla volumen")
    if len(pains)>=2: score+=12; barriers.append("dos o más dolencias activas: se limita fatiga total")
    if bmi>=35: score+=25; barriers.append("IMC muy alto: se limita impacto, carga articular y duración")
    elif bmi>=30: score+=15; barriers.append("IMC alto: se controla carga articular y locomoción")
    if energy<=3: score+=20; barriers.append("energía muy baja: se entrega sesión corta")
    elif energy<=5: score+=10; barriers.append("energía baja: se reduce volumen hoy")
    if "hipertensión" in conditions or "hipertension" in conditions: score+=10; barriers.append("hipertensión: controlar densidad, Valsalva y pausas")
    if "pérdida de equilibrio" in conditions or "perdida de equilibrio" in conditions: score+=15; barriers.append("equilibrio bajo: se evitan ejercicios inestables")
    age_policy = _age_policy(p)
    if age>=85:
        score+=25; barriers.append(age_policy["explanation"])
    elif age>=75:
        score+=15; barriers.append(age_policy["explanation"])
    elif age>=65:
        score+=8; barriers.append(age_policy["explanation"])
    elif age>=55:
        score+=4; barriers.append(age_policy["explanation"])
    elif age>=40:
        barriers.append(age_policy["explanation"])
    if red_flags:
        sem="red"; tmax=0; strategy="block_or_professional_review"
    elif score>=55:
        sem="red"; tmax=min(tp,25); strategy="safe_recovery_or_block"
    elif score>=30:
        sem="orange"; tmax=min(tp,45); strategy="deload_session"
    elif score>=15:
        sem="yellow"; tmax=min(tp,75); strategy="controlled_standard"
    else:
        sem="green"; tmax=tp; strategy="controlled_standard"
    return {"tp":tp,"bmi":bmi,"score":score,"semaphore":sem,"tmax":tmax,"barriers":barriers,"red_flags":red_flags,"strategy":strategy,"pain_max":pain_max,"energy":energy,"age":age,"age_policy":age_policy}

def _allowed(row, equipment:Set[str], sem:str, pains:List[Dict[str,Any]], conditions:Set[str]) -> bool:
    eq=(row.get('equipamiento') or 'sin_equipamiento')
    if eq not in equipment and eq not in ('sin_equipamiento','pared_apoyo'):
        return False
    seg=(row.get('seguridad_base') or 'muy_seguro').lower()
    if sem in ('red','orange') and seg not in ('muy_seguro','seguro'):
        return False
    # zone pain risk filtering for strength only
    pain_zones=[ZONE_MAP.get(str(d.get('zone') or d.get('zona') or '').lower(), str(d.get('zone') or d.get('zona') or '')) for d in pains]
    for z in pain_zones:
        if z=='Lumbar' and _int(row.get('riesgo_lumbar'))>=3: return False
        if z=='Rodilla' and _int(row.get('riesgo_rodilla'))>=3: return False
        if z=='Hombro' and _int(row.get('riesgo_hombro'))>=3: return False
    if ("hipertensión" in conditions or "hipertension" in conditions) and row.get('familia') in ('POWER','OLY'):
        return False
    return True

def _sort_key(row, pains, objective):
    # prioritize safer, related zones, low risk, then family diversity via randomized small factor
    zones=[ZONE_MAP.get(str(d.get('zone') or d.get('zona') or '').lower(), str(d.get('zone') or d.get('zona') or '')) for d in pains]
    zone_bonus = 0 if not zones else (0 if row.get('zona_principal') in zones else 2)
    risk=_int(row.get('riesgo_lumbar'))+_int(row.get('riesgo_rodilla'))+_int(row.get('riesgo_hombro'))
    seg=(row.get('seguridad_base') or '').lower()
    segscore={'muy_seguro':0,'seguro':1,'moderado':3,'exigente':5}.get(seg,2)
    return (zone_bonus, segscore, risk, random.random())


def _age_policy(payload: Dict[str,Any]) -> Dict[str,Any]:
    age = _int(payload.get('age') or payload.get('edad'), 40)
    if age < 18 or age > 90:
        return {"band":"fuera de rango","density_factor":0.0,"rest_bonus":0,"tempo_bias":"block","explanation":"edad fuera del rango cubierto por VitalMotion"}
    if age >= 85:
        return {"band":"85-90 fragilidad","density_factor":0.65,"rest_bonus":20,"tempo_bias":"fragility","explanation":"edad 85–90: se prioriza movilidad, fuerza básica, pausas largas y control"}
    if age >= 75:
        return {"band":"75-84 senior fuerte","density_factor":0.75,"rest_bonus":15,"tempo_bias":"senior_strong","explanation":"edad 75–84: menor densidad, más recuperación y control motor"}
    if age >= 65:
        return {"band":"65-74 senior moderado","density_factor":0.85,"rest_bonus":10,"tempo_bias":"senior","explanation":"edad 65–74: se controla densidad, estabilidad y recuperación"}
    if age >= 55:
        return {"band":"55-64 adaptación visible","density_factor":0.92,"rest_bonus":5,"tempo_bias":"controlled","explanation":"edad 55–64: más control y pausas levemente mayores"}
    if age >= 40:
        return {"band":"40-54 microadaptación","density_factor":0.97,"rest_bonus":0,"tempo_bias":"normal","explanation":"edad 40–54: microcontrol de densidad sin restringir entrenamiento"}
    return {"band":"18-39 estándar","density_factor":1.0,"rest_bonus":0,"tempo_bias":"normal","explanation":"edad 18–39: sin ajuste específico por edad"}

def _max_pain(payload: Dict[str,Any]) -> int:
    pains = payload.get('pains') or payload.get('dolencias') or []
    return max([_int(d.get('level') or d.get('dolor') or d.get('dolor_0_10')) for d in pains] or [0])

def _choose_tempo(payload: Dict[str,Any], block: str, sem: str) -> Dict[str,Any]:
    objective = str(payload.get('goal') or payload.get('objetivo') or '').lower()
    age_policy = _age_policy(payload)
    pain = _max_pain(payload)
    conditions = set([str(c).lower() for c in (payload.get('conditions') or payload.get('condiciones') or [])])
    limitations = set([str(c).lower() for c in (payload.get('limitations') or payload.get('limitaciones') or [])])

    tempo = "2-1-2-1"
    reason = "tempo base controlado"

    if block != "strength":
        return {"tempo":tempo, "tempo_total_sec":_tempo_seconds(tempo), "reason":reason}

    if "hipertrofia" in objective or "volumen" in objective:
        tempo = "3-0-2-0"
        reason = "objetivo hipertrofia: más tiempo bajo tensión sin agregar impacto"
    if "deportivo" in objective or "potencia" in objective:
        tempo = "1-0-X-0"
        reason = "objetivo deportivo/potencia: intención concéntrica rápida controlada"

    if "rehabilitación" in objective or "rehabilitacion" in objective or pain >= 6 or sem in ("orange","red"):
        tempo = "3-1-2-1"
        reason = "dolor/rehabilitación: más control motor y menor impulsividad"
    elif pain >= 4:
        tempo = "3-1-2-1"
        reason = "dolor moderado: tempo más lento para mejorar tolerancia"

    if age_policy["tempo_bias"] in ("senior","senior_strong","fragility") and tempo == "2-1-2-1":
        tempo = "3-1-2-1"
        reason = age_policy["explanation"] + ": tempo más controlado"
    if "poco equilibrio" in limitations or "pérdida de equilibrio" in conditions or "perdida de equilibrio" in conditions:
        tempo = "2-2-2-2"
        reason = "equilibrio limitado: pausas para estabilidad y control"

    return {"tempo":tempo, "tempo_total_sec":_tempo_seconds(tempo), "reason":reason}

def _tempo_seconds(tempo: str) -> int:
    total = 0
    for part in str(tempo).split("-"):
        if part.upper() == "X":
            total += 1
        else:
            try:
                total += int(part)
            except Exception:
                total += 0
    return total or 6

def _side_switch_rest(item: Dict[str,Any], sem: str) -> int:
    lat=(item.get('lateralidad') or 'bilateral').lower()
    if lat != 'unilateral':
        return 0
    # cambio real de lado: reposicionamiento, banda/apoyo y seguridad
    return 10 if sem in ('green','yellow') else 15

def _seconds(item:Dict[str,Any], block:str, sem:str, target_fill=False, payload:Dict[str,Any]|None=None) -> int:
    lat=(item.get('lateralidad') or 'bilateral').lower()
    sides=2 if lat=='unilateral' else 1
    side_switch=_side_switch_rest(item, sem)
    if block=='warmups':
        sec=60 if sem=='green' else 45 if sem=='yellow' else 35
        return sec*sides + side_switch + 10
    if block=='stretches':
        sec=45 if sem in ('green','yellow') else 30
        return sec*sides + side_switch + 10
    if block=='isometrics':
        sets=2 if sem in ('green','yellow') else 1
        hold=25 if sem in ('green','yellow') else 20
        agep=_age_policy(payload or {})
        dser=(35 + agep["rest_bonus"]) if sets>1 else 0
        dej=25 + agep["rest_bonus"]
        return sides*(sets*hold + (sets-1)*dser) + side_switch + dej
    # strength
    agep=_age_policy(payload or {})
    sets=2 if sem in ('green','yellow') else 1
    reps=10 if sem=='green' else 8 if sem=='yellow' else 6
    tempo_info=_choose_tempo(payload or {}, block, sem)
    tempo_sec=tempo_info["tempo_total_sec"]
    dser=(60 + agep["rest_bonus"]) if sets>1 else 0
    dej=45 + agep["rest_bonus"]
    return sides*(sets*reps*tempo_sec + (sets-1)*dser) + side_switch + dej

def _decorate(item, block, sem, payload=None):
    sec=_seconds(item, block, sem, payload=payload)
    lat=(item.get('lateralidad') or 'bilateral').lower(); sides=2 if lat=='unilateral' else 1
    side_switch=_side_switch_rest(item, sem)
    out={"id":item.get('id'),"name":item.get('nombre'),"block":block,"family":item.get('familia') or item.get('grupo') or '',"zone":item.get('zona_principal'),"equipment":item.get('equipamiento') or 'sin_equipamiento',"laterality":lat,"sides":sides,"side_switch_rest_sec":side_switch,"seconds":sec,"minutes":round(sec/60,1)}
    if block=='warmups':
        hold=60 if sem=='green' else 45 if sem=='yellow' else 35
        out.update({"type":"warmup","hold_sec":hold,"rest_between_sides_sec":side_switch,"rest_between_exercises_sec":10,"formula":f"{sides} lado(s) × {hold}s + cambio lado {side_switch}s + descanso ejercicio 10s"})
    elif block=='stretches':
        hold=45 if sem in ('green','yellow') else 30
        out.update({"type":"stretch","hold_sec":hold,"rest_between_sides_sec":side_switch,"rest_between_exercises_sec":10,"formula":f"{sides} lado(s) × {hold}s + cambio lado {side_switch}s + descanso ejercicio 10s"})
    elif block=='isometrics':
        agep=_age_policy(payload or {})
        sets=2 if sem in ('green','yellow') else 1; hold=25 if sem in ('green','yellow') else 20; dser=(35 + agep["rest_bonus"]) if sets>1 else 0; dej=25 + agep["rest_bonus"]
        out.update({"type":"isometric","sets":sets,"hold_sec":hold,"rest_between_sets_sec":dser,"rest_between_sides_sec":side_switch,"rest_between_exercises_sec":dej,"age_policy":agep,"formula":f"{sides} lado(s) × ({sets}×{hold}s + ({sets}-1)×{dser}s) + cambio lado {side_switch}s + descanso ejercicio {dej}s"})
    else:
        agep=_age_policy(payload or {})
        sets=2 if sem in ('green','yellow') else 1; reps=10 if sem=='green' else 8 if sem=='yellow' else 6; tempo_info=_choose_tempo(payload or {}, block, sem); tempo=tempo_info["tempo"]; tempo_sec=tempo_info["tempo_total_sec"]; dser=(60 + agep["rest_bonus"]) if sets>1 else 0; dej=45 + agep["rest_bonus"]
        out.update({"type":"strength","sets":sets,"reps":reps,"tempo":tempo,"tempo_total_sec":tempo_sec,"tempo_reason":tempo_info["reason"],"rest_between_reps_sec":0,"rest_between_sets_sec":dser,"rest_between_sides_sec":side_switch,"rest_between_exercises_sec":dej,"age_policy":agep,"formula":f"{sides} lado(s) × ({sets} series × {reps} reps × tempo {tempo} = {tempo_sec}s/rep + ({sets}-1)×{dser}s) + cambio lado {side_switch}s + descanso ejercicio {dej}s"})
    return out

def _get_candidates(con, table, rel_table, rel_col, pains, equipment, sem, conditions):
    ids=[]
    for d in pains:
        z=ZONE_MAP.get(str(d.get('zone') or d.get('zona') or '').lower(), str(d.get('zone') or d.get('zona') or ''))
        rows=_rows(con,'05_DOLENCIAS','WHERE zona LIKE ?', (f'%{z}%',), 1000)
        for r in rows[:30]:
            ids += [x[0] for x in con.execute(f'SELECT {rel_col} FROM "{rel_table}" WHERE id_dolencia=? LIMIT 200', (r['id_dolencia'],)).fetchall()]
    if ids:
        placeholders=','.join('?'*len(set(ids)))
        cand=_rows(con, table, f'WHERE id IN ({placeholders})', tuple(set(ids)), 5000)
        if len(cand)>30: return [r for r in cand if _allowed(r,equipment,sem,pains,conditions)]
    return [r for r in _rows(con, table, '', (), 5000) if _allowed(r,equipment,sem,pains,conditions)]

def _fill_block(cands, block, target_sec, sem, used_ids:Set[str], pains, objective, payload=None):
    selected=[]; total=0
    pool=sorted(cands, key=lambda r:_sort_key(r,pains,objective))
    # prevent repeated pattern early where possible
    used_patterns=set()
    passes=[True, False]
    for strict_pattern in passes:
        for row in pool:
            if row['id'] in used_ids: continue
            pat=row.get('patron_base') or row.get('nombre')
            if strict_pattern and pat in used_patterns: continue
            sec=_seconds(row, block, sem, payload=payload)
            if total + sec > target_sec*1.08 and total >= target_sec*0.85: break
            selected.append(_decorate(row, block, sem, payload=payload)); used_ids.add(row['id']); used_patterns.add(pat); total+=sec
            if total >= target_sec*0.98: break
        if total >= target_sec*0.90: break
    return selected, total



# ===== Longitudinal Adaptation REAL =====



def _ensure_feedback_tables(con):
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS VM_SESSION_FEEDBACK (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT,
        rpe INTEGER,
        pain_post INTEGER,
        energy_post INTEGER,
        completed INTEGER,
        notes TEXT
    )
    """)
    con.commit()

def save_feedback(payload: Dict[str,Any], db_path: str|None=None) -> Dict[str,Any]:
    con = _connect(db_path)
    _ensure_feedback_tables(con)
    rpe = max(1, min(10, _int(payload.get("rpe"), 5)))
    pain_post = max(0, min(10, _int(payload.get("pain_post"), 0)))
    energy_post = max(1, min(10, _int(payload.get("energy_post"), 5)))
    completed = 1 if str(payload.get("completed", "true")).lower() in ("true","1","si","sí","yes") else 0
    notes = str(payload.get("notes") or "")[:500]

    cur = con.cursor()
    cur.execute("""
    INSERT INTO VM_SESSION_FEEDBACK (
        ts, rpe, pain_post, energy_post, completed, notes
    )
    VALUES (?,?,?,?,?,?)
    """, (
        __import__("time").strftime("%Y-%m-%d %H:%M:%S"),
        rpe,
        pain_post,
        energy_post,
        completed,
        notes
    ))
    con.commit()
    summary = _feedback_summary(con)
    con.close()
    return {
        "ok": True,
        "saved": True,
        "feedback_summary": summary
    }

def _feedback_summary(con):
    try:
        cur = con.cursor()
        _ensure_feedback_tables(con)
        n = cur.execute("SELECT COUNT(*) FROM VM_SESSION_FEEDBACK").fetchone()[0]
        avg_rpe = cur.execute("SELECT AVG(rpe) FROM VM_SESSION_FEEDBACK").fetchone()[0]
        avg_pain = cur.execute("SELECT AVG(pain_post) FROM VM_SESSION_FEEDBACK").fetchone()[0]
        avg_energy = cur.execute("SELECT AVG(energy_post) FROM VM_SESSION_FEEDBACK").fetchone()[0]
        completed = cur.execute("SELECT AVG(completed) FROM VM_SESSION_FEEDBACK").fetchone()[0]
        return {
            "feedback_count": n,
            "avg_rpe": round(avg_rpe,1) if avg_rpe else 0,
            "avg_pain_post": round(avg_pain,1) if avg_pain else 0,
            "avg_energy_post": round(avg_energy,1) if avg_energy else 0,
            "completion_rate": round(completed,2) if completed is not None else 0
        }
    except Exception:
        return {
            "feedback_count": 0,
            "avg_rpe": 0,
            "avg_pain_post": 0,
            "avg_energy_post": 0,
            "completion_rate": 0
        }

def _feedback_adaptation(con) -> Dict[str,Any]:
    s = _feedback_summary(con)
    notes = []
    modifier = "neutral"
    if s["feedback_count"] == 0:
        return {
            "modifier": "no_feedback_yet",
            "summary": s,
            "notes": ["sin feedback post-sesión todavía"]
        }
    if s["avg_pain_post"] >= 6 or s["avg_rpe"] >= 8:
        modifier = "reduce_next"
        notes.append("feedback histórico alto: conviene bajar volumen/densidad próxima sesión")
    elif s["avg_pain_post"] <= 3 and s["avg_rpe"] <= 6 and s["completion_rate"] >= 0.8:
        modifier = "progress_slowly"
        notes.append("feedback histórico favorable: se puede progresar gradualmente si el check-in diario acompaña")
    else:
        modifier = "maintain"
        notes.append("feedback histórico intermedio: mantener dosis y observar respuesta")
    return {
        "modifier": modifier,
        "summary": s,
        "notes": notes
    }


def _ensure_history_tables(con):
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS VM_USER_HISTORY (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT,
        age INTEGER,
        objective TEXT,
        semaphore TEXT,
        tp REAL,
        te REAL,
        pain_max INTEGER,
        energy INTEGER,
        exercises INTEGER,
        density_factor REAL,
        avg_tempo TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS VM_EXERCISE_HISTORY (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT,
        exercise_id TEXT,
        exercise_name TEXT,
        block TEXT,
        tempo TEXT,
        seconds REAL
    )
    """)

    con.commit()

def _history_summary(con):
    try:
        cur = con.cursor()

        cur.execute("SELECT COUNT(*) FROM VM_USER_HISTORY")
        sessions = cur.fetchone()[0]

        cur.execute("SELECT AVG(te) FROM VM_USER_HISTORY")
        avg_te = cur.fetchone()[0]

        cur.execute("SELECT semaphore, COUNT(*) c FROM VM_USER_HISTORY GROUP BY semaphore ORDER BY c DESC LIMIT 1")
        row = cur.fetchone()

        return {
            "sessions": sessions,
            "avg_te": round(avg_te,1) if avg_te else 0,
            "most_common_semaphore": row[0] if row else None
        }
    except:
        return {
            "sessions": 0,
            "avg_te": 0,
            "most_common_semaphore": None
        }

def _save_session_history(con, payload, result):
    try:
        _ensure_history_tables(con)

        tg = result.get("time_governance") or {}
        blocks = result.get("blocks") or {}

        tempos = []

        for arr in blocks.values():
            for e in arr:
                if e.get("tempo"):
                    tempos.append(e.get("tempo"))

        avg_tempo = tempos[0] if tempos else None

        cur = con.cursor()

        cur.execute("""
        INSERT INTO VM_USER_HISTORY (
            ts, age, objective, semaphore,
            tp, te, pain_max, energy,
            exercises, density_factor, avg_tempo
        )
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            __import__("time").strftime("%Y-%m-%d %H:%M:%S"),
            payload.get("age") or payload.get("edad"),
            payload.get("goal") or payload.get("objetivo"),
            tg.get("semaphore"),
            result.get("tp"),
            result.get("te_min"),
            tg.get("pain_max"),
            tg.get("energy"),
            sum(len(v) for v in blocks.values()),
            (tg.get("age_policy") or {}).get("density_factor"),
            avg_tempo
        ))

        for block_name, arr in blocks.items():
            for e in arr:
                cur.execute("""
                INSERT INTO VM_EXERCISE_HISTORY (
                    ts, exercise_id, exercise_name,
                    block, tempo, seconds
                )
                VALUES (?,?,?,?,?,?)
                """, (
                    __import__("time").strftime("%Y-%m-%d %H:%M:%S"),
                    e.get("id"),
                    e.get("name"),
                    block_name,
                    e.get("tempo"),
                    e.get("seconds")
                ))

        con.commit()

    except Exception as ex:
        print("history save error:", ex)

# ===== End Longitudinal Adaptation =====



# ===== Detailed Exercise / Set Feedback REAL =====

def _ensure_detailed_feedback_tables(con):
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS VM_EXERCISE_FEEDBACK (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT,
        exercise_id TEXT,
        exercise_name TEXT,
        block TEXT,
        difficulty TEXT,
        pain_during INTEGER,
        pain_zone TEXT,
        control_quality TEXT,
        would_repeat INTEGER,
        notes TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS VM_SET_FEEDBACK (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT,
        exercise_id TEXT,
        exercise_name TEXT,
        set_number INTEGER,
        weight_kg REAL,
        reps_completed INTEGER,
        rpe INTEGER,
        pain_during INTEGER,
        next_load_action TEXT,
        notes TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS VM_ISOMETRIC_FEEDBACK (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT,
        exercise_id TEXT,
        exercise_name TEXT,
        hold_target_sec INTEGER,
        hold_completed_sec INTEGER,
        difficulty TEXT,
        pain_during INTEGER,
        tremor_fatigue TEXT,
        notes TEXT
    )
    """)
    con.commit()

def save_exercise_feedback(payload: Dict[str,Any], db_path: str|None=None) -> Dict[str,Any]:
    con = _connect(db_path)
    _ensure_detailed_feedback_tables(con)
    cur = con.cursor()
    items = payload.get("items") or []
    saved = 0
    for it in items:
        cur.execute("""
        INSERT INTO VM_EXERCISE_FEEDBACK (
            ts, exercise_id, exercise_name, block,
            difficulty, pain_during, pain_zone,
            control_quality, would_repeat, notes
        )
        VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            __import__("time").strftime("%Y-%m-%d %H:%M:%S"),
            str(it.get("exercise_id") or ""),
            str(it.get("exercise_name") or ""),
            str(it.get("block") or ""),
            str(it.get("difficulty") or "adecuado"),
            max(0, min(10, _int(it.get("pain_during"), 0))),
            str(it.get("pain_zone") or ""),
            str(it.get("control_quality") or "correcto"),
            1 if str(it.get("would_repeat", "true")).lower() in ("true","1","si","sí","yes") else 0,
            str(it.get("notes") or "")[:500]
        ))
        saved += 1
    con.commit()
    summary = _detailed_feedback_summary(con)
    con.close()
    return {"ok": True, "saved": saved, "detailed_feedback_summary": summary}

def save_set_feedback(payload: Dict[str,Any], db_path: str|None=None) -> Dict[str,Any]:
    con = _connect(db_path)
    _ensure_detailed_feedback_tables(con)
    cur = con.cursor()
    items = payload.get("items") or []
    saved = 0
    for it in items:
        cur.execute("""
        INSERT INTO VM_SET_FEEDBACK (
            ts, exercise_id, exercise_name, set_number,
            weight_kg, reps_completed, rpe,
            pain_during, next_load_action, notes
        )
        VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            __import__("time").strftime("%Y-%m-%d %H:%M:%S"),
            str(it.get("exercise_id") or ""),
            str(it.get("exercise_name") or ""),
            _int(it.get("set_number"), 1),
            float(it.get("weight_kg") or 0),
            _int(it.get("reps_completed"), 0),
            max(1, min(10, _int(it.get("rpe"), 5))),
            max(0, min(10, _int(it.get("pain_during"), 0))),
            str(it.get("next_load_action") or "mantener"),
            str(it.get("notes") or "")[:500]
        ))
        saved += 1
    con.commit()
    summary = _detailed_feedback_summary(con)
    con.close()
    return {"ok": True, "saved": saved, "detailed_feedback_summary": summary}

def save_isometric_feedback(payload: Dict[str,Any], db_path: str|None=None) -> Dict[str,Any]:
    con = _connect(db_path)
    _ensure_detailed_feedback_tables(con)
    cur = con.cursor()
    items = payload.get("items") or []
    saved = 0
    for it in items:
        cur.execute("""
        INSERT INTO VM_ISOMETRIC_FEEDBACK (
            ts, exercise_id, exercise_name,
            hold_target_sec, hold_completed_sec,
            difficulty, pain_during, tremor_fatigue, notes
        )
        VALUES (?,?,?,?,?,?,?,?,?)
        """, (
            __import__("time").strftime("%Y-%m-%d %H:%M:%S"),
            str(it.get("exercise_id") or ""),
            str(it.get("exercise_name") or ""),
            _int(it.get("hold_target_sec"), 0),
            _int(it.get("hold_completed_sec"), 0),
            str(it.get("difficulty") or "adecuado"),
            max(0, min(10, _int(it.get("pain_during"), 0))),
            str(it.get("tremor_fatigue") or "normal"),
            str(it.get("notes") or "")[:500]
        ))
        saved += 1
    con.commit()
    summary = _detailed_feedback_summary(con)
    con.close()
    return {"ok": True, "saved": saved, "detailed_feedback_summary": summary}

def _detailed_feedback_summary(con):
    _ensure_detailed_feedback_tables(con)
    cur = con.cursor()
    ex_n = cur.execute("SELECT COUNT(*) FROM VM_EXERCISE_FEEDBACK").fetchone()[0]
    set_n = cur.execute("SELECT COUNT(*) FROM VM_SET_FEEDBACK").fetchone()[0]
    iso_n = cur.execute("SELECT COUNT(*) FROM VM_ISOMETRIC_FEEDBACK").fetchone()[0]
    avg_set_rpe = cur.execute("SELECT AVG(rpe) FROM VM_SET_FEEDBACK").fetchone()[0]
    avg_set_pain = cur.execute("SELECT AVG(pain_during) FROM VM_SET_FEEDBACK").fetchone()[0]
    avg_ex_pain = cur.execute("SELECT AVG(pain_during) FROM VM_EXERCISE_FEEDBACK").fetchone()[0]
    repeat_rate = cur.execute("SELECT AVG(would_repeat) FROM VM_EXERCISE_FEEDBACK").fetchone()[0]
    return {
        "exercise_feedback_count": ex_n,
        "set_feedback_count": set_n,
        "isometric_feedback_count": iso_n,
        "avg_set_rpe": round(avg_set_rpe,1) if avg_set_rpe else 0,
        "avg_set_pain": round(avg_set_pain,1) if avg_set_pain else 0,
        "avg_exercise_pain": round(avg_ex_pain,1) if avg_ex_pain else 0,
        "repeat_rate": round(repeat_rate,2) if repeat_rate is not None else 0
    }

def _detailed_feedback_adaptation(con):
    s = _detailed_feedback_summary(con)
    notes = []
    modifier = "no_detailed_feedback_yet"
    if s["set_feedback_count"] or s["exercise_feedback_count"] or s["isometric_feedback_count"]:
        if s["avg_set_pain"] >= 5 or s["avg_exercise_pain"] >= 5 or s["avg_set_rpe"] >= 8:
            modifier = "reduce_or_modify_exercises"
            notes.append("feedback detallado alto: bajar carga, cambiar ejercicio o aumentar descanso")
        elif s["avg_set_rpe"] and s["avg_set_rpe"] <= 6 and s["avg_set_pain"] <= 3 and s["repeat_rate"] >= 0.8:
            modifier = "progress_carefully"
            notes.append("feedback detallado favorable: se puede progresar una variable por vez")
        else:
            modifier = "maintain_and_observe"
            notes.append("feedback detallado intermedio: mantener y observar respuesta")
    else:
        notes.append("sin feedback por ejercicio/serie todavía")
    return {"modifier": modifier, "summary": s, "notes": notes}

# ===== End Detailed Feedback =====




# ===== Progression Engine REAL INITIAL =====

def _progression_recommendation(con):
    try:
        cur = con.cursor()

        # session feedback
        fb = _feedback_summary(con)
        dfb = _detailed_feedback_summary(con)

        sessions = cur.execute("SELECT COUNT(*) FROM VM_USER_HISTORY").fetchone()[0]

        recommendation = {
            "status": "baseline",
            "volume_delta": 0,
            "density_delta": 0,
            "load_delta": 0,
            "complexity_delta": 0,
            "reason": "sin suficiente historial"
        }

        if sessions < 3:
            recommendation["reason"] = "menos de 3 sesiones: priorizar estabilidad y aprendizaje motor"
            return recommendation

        # protective logic
        if fb["avg_pain_post"] >= 6 or dfb["avg_set_pain"] >= 5:
            recommendation.update({
                "status": "protect",
                "volume_delta": -0.15,
                "density_delta": -0.20,
                "load_delta": -0.10,
                "complexity_delta": -0.20,
                "reason": "dolor acumulado elevado: bajar carga/densidad"
            })
            return recommendation

        if fb["avg_rpe"] >= 8 or dfb["avg_set_rpe"] >= 8:
            recommendation.update({
                "status": "fatigue_control",
                "volume_delta": -0.10,
                "density_delta": -0.15,
                "load_delta": -0.05,
                "complexity_delta": 0,
                "reason": "fatiga alta sostenida: controlar recuperación"
            })
            return recommendation

        # progression logic
        if (
            fb["completion_rate"] >= 0.8 and
            fb["avg_pain_post"] <= 3 and
            dfb["avg_set_pain"] <= 3 and
            dfb["avg_set_rpe"] <= 6
        ):
            recommendation.update({
                "status": "progress",
                "volume_delta": 0.05,
                "density_delta": 0.05,
                "load_delta": 0.03,
                "complexity_delta": 0.03,
                "reason": "historial favorable: progresión lenta segura"
            })
            return recommendation

        recommendation.update({
            "status": "maintain",
            "reason": "respuesta intermedia: mantener y observar"
        })
        return recommendation

    except Exception:
        return {
            "status": "error",
            "volume_delta": 0,
            "density_delta": 0,
            "load_delta": 0,
            "complexity_delta": 0,
            "reason": "error leyendo progresión"
        }

# ===== End Progression Engine =====




# ===== Fatigue Management REAL INITIAL =====

def _fatigue_state(con):
    try:
        cur = con.cursor()

        sessions = cur.execute("""
        SELECT te, pain_max, energy
        FROM VM_USER_HISTORY
        ORDER BY id DESC
        LIMIT 7
        """).fetchall()

        fb = _feedback_summary(con)
        detailed = _detailed_feedback_summary(con)

        if not sessions:
            return {
                "status": "unknown",
                "fatigue_score": 0,
                "recovery_score": 0,
                "recommendation": "sin historial suficiente"
            }

        avg_te = sum([s[0] or 0 for s in sessions]) / len(sessions)
        avg_pain = sum([s[1] or 0 for s in sessions]) / len(sessions)
        avg_energy = sum([s[2] or 0 for s in sessions]) / len(sessions)

        fatigue_score = 0

        if avg_te >= 75:
            fatigue_score += 2
        elif avg_te >= 55:
            fatigue_score += 1

        if avg_pain >= 5:
            fatigue_score += 3
        elif avg_pain >= 3:
            fatigue_score += 1

        if avg_energy <= 3:
            fatigue_score += 3
        elif avg_energy <= 5:
            fatigue_score += 1

        if fb["avg_rpe"] >= 8:
            fatigue_score += 2
        elif fb["avg_rpe"] >= 6:
            fatigue_score += 1

        if detailed["avg_set_rpe"] >= 8:
            fatigue_score += 2

        if detailed["avg_set_pain"] >= 5:
            fatigue_score += 2

        if fatigue_score >= 8:
            status = "high_fatigue"
            rec = "reducir densidad, volumen y complejidad"
        elif fatigue_score >= 5:
            status = "moderate_fatigue"
            rec = "controlar recuperación y mantener progresión conservadora"
        else:
            status = "recovered"
            rec = "fatiga controlada"

        recovery_score = max(0, 10 - fatigue_score)

        return {
            "status": status,
            "fatigue_score": fatigue_score,
            "recovery_score": recovery_score,
            "avg_te_last_sessions": round(avg_te,1),
            "avg_pain_last_sessions": round(avg_pain,1),
            "avg_energy_last_sessions": round(avg_energy,1),
            "recommendation": rec
        }

    except Exception:
        return {
            "status": "error",
            "fatigue_score": 0,
            "recovery_score": 0,
            "recommendation": "error leyendo fatiga"
        }

# ===== End Fatigue Management =====




# ===== V12 / V12.1 Runtime Scoring REAL INITIAL =====

def _profile_id_from_payload(payload: Dict[str,Any], tg: Dict[str,Any]) -> str:
    age = _int(payload.get("age") or payload.get("edad"), 40)
    bmi = tg.get("bmi")
    objective = str(payload.get("goal") or payload.get("objetivo") or "").lower()
    pains = payload.get("pains") or payload.get("dolencias") or []
    conditions = set([str(c).lower() for c in (payload.get("conditions") or payload.get("condiciones") or [])])
    if age >= 65:
        return "P_MVP_V9_02"  # Adulto mayor / fragilidad independiente
    if bmi and bmi >= 30:
        return "P_MVP_V9_03"  # Obesidad / descondicionamiento independiente
    if "rehabilitación" in objective or "rehabilitacion" in objective or pains:
        return "P_MVP_V9_04"
    if "hipertensión" in conditions or "hipertension" in conditions:
        return "P_MVP_V9_05"
    return "P_MVP_V9_01"

def _load_v12_scores(con, ids, profile_id):
    if not ids:
        return {}
    try:
        cur = con.cursor()
        placeholders = ",".join(["?"] * len(ids))
        sql = f"""
        SELECT exercise_id, global_score_v12, clinical_safety_score,
               fatigue_recovery_score, adherence_feasibility_score,
               recommendation_status, hard_block_v12, hard_block_reason
        FROM v12_1_scoring_full_overlay
        WHERE profile_id = ? AND exercise_id IN ({placeholders})
        """
        rows = cur.execute(sql, [profile_id] + list(ids)).fetchall()
        out = {}
        for r in rows:
            out[str(r[0])] = {
                "global_score_v12": float(r[1] or 0),
                "clinical_safety_score": float(r[2] or 0),
                "fatigue_recovery_score": float(r[3] or 0),
                "adherence_feasibility_score": float(r[4] or 0),
                "recommendation_status": str(r[5] or ""),
                "hard_block_v12": int(r[6] or 0),
                "hard_block_reason": str(r[7] or "")
            }
        return out
    except Exception:
        return {}

def _apply_runtime_scoring(candidates, con, payload, tg, block_name):
    profile_id = _profile_id_from_payload(payload, tg)
    ids = [str(r.get("id")) for r in candidates]
    scores = _load_v12_scores(con, ids, profile_id)

    scored = []
    blocked = 0
    for row in candidates:
        rid = str(row.get("id"))
        score = scores.get(rid)
        if score:
            row = dict(row)
            row["_v12_profile_id"] = profile_id
            row["_v12_score"] = score
            if score.get("hard_block_v12"):
                blocked += 1
                continue
            scored.append(row)
        else:
            scored.append(row)

    def score_key(r):
        s = r.get("_v12_score") or {}
        # Higher score first, but keep previous random/diversity behavior downstream.
        return -(
            0.50 * float(s.get("global_score_v12", 50)) +
            0.25 * float(s.get("clinical_safety_score", 50)) +
            0.15 * float(s.get("fatigue_recovery_score", 50)) +
            0.10 * float(s.get("adherence_feasibility_score", 50))
        )

    scored = sorted(scored, key=score_key)
    return scored, {
        "profile_id": profile_id,
        "block": block_name,
        "scored_candidates": len(scores),
        "blocked_by_v12": blocked,
        "available_after_scoring": len(scored)
    }

# ===== End V12 / V12.1 Runtime Scoring =====


def generate_session(payload: Dict[str,Any], db_path: str|None=None) -> Dict[str,Any]:
    payload['weight_kg']=round(_clamp(payload.get('weight_kg',70),20,250))
    payload['height_cm']=round(_clamp(payload.get('height_cm',170),100,230))
    payload['age']=round(_clamp(payload.get('age',40),10,100))
    payload['energy']=round(_clamp(payload.get('energy',5),1,10))
    random.seed(payload.get('seed') if payload.get('seed') is not None else None)
    con=_connect(db_path); counts=catalog_counts(db_path)
    tg=_clinical_time_governance(payload)
    if tg['red_flags']:
        return {"ok":False,"blocked":True,"time_governance":tg,"message":"Este sistema no contempla una sesión segura para tu situación actual; buscá un profesional que pueda ayudarte."}
    tp=tg['tp']; sem=tg['semaphore']; objective=(payload.get('goal') or payload.get('objetivo') or 'funcional')
    pains=payload.get('pains') or payload.get('dolencias') or []
    conditions=set([str(c).lower() for c in (payload.get('conditions') or payload.get('condiciones') or [])])
    equipment=_normalize_equipment(payload.get('equipment') or payload.get('equipamiento') or [])
    target=tg['tmax'] or tp
    target=round(target * (tg.get('age_policy') or {}).get('density_factor',1.0), 1)
    # block allocation
    if sem=='green': alloc={'warmups':0.13,'strength':0.50,'isometrics':0.12,'stretches':0.25}
    elif sem=='yellow': alloc={'warmups':0.16,'strength':0.42,'isometrics':0.20,'stretches':0.22}
    else: alloc={'warmups':0.22,'strength':0.22,'isometrics':0.36,'stretches':0.20}
    # hard min/max block caps
    targets={k:int(target*60*v) for k,v in alloc.items()}
    targets['warmups']=max(5*60, min(15*60, targets['warmups']))
    targets['stretches']=max(3*60, min(15*60, targets['stretches']))
    used=set()
    c_w=_get_candidates(con,'12_CATALOGO_C','23_REL_D_C','id_c',pains,equipment,sem,conditions)
    c_s=_get_candidates(con,'13_CATALOGO_S','24_REL_D_S','id_s',pains,equipment,sem,conditions)
    c_i=_get_candidates(con,'11_CATALOGO_I','22_REL_D_I','id_i',pains,equipment,sem,conditions)
    c_e=_get_candidates(con,'10_CATALOGO_E','21_REL_D_E','id_e',pains,equipment,sem,conditions)

    scoring_trace=[]
    c_w,tr_w=_apply_runtime_scoring(c_w,con,payload,tg,'warmups'); scoring_trace.append(tr_w)
    c_s,tr_s=_apply_runtime_scoring(c_s,con,payload,tg,'stretches'); scoring_trace.append(tr_s)
    c_i,tr_i=_apply_runtime_scoring(c_i,con,payload,tg,'isometrics'); scoring_trace.append(tr_i)
    c_e,tr_e=_apply_runtime_scoring(c_e,con,payload,tg,'strength'); scoring_trace.append(tr_e)
    warm, tw=_fill_block(c_w,'warmups',targets['warmups'],sem,used,pains,objective,payload)
    strength, ts=_fill_block(c_e,'strength',targets['strength'],sem,used,pains,objective,payload)
    iso, ti=_fill_block(c_i,'isometrics',targets['isometrics'],sem,used,pains,objective,payload)
    stretch, tst=_fill_block(c_s,'stretches',targets['stretches'],sem,used,pains,objective,payload)
    # secondary fill to approach target with allowed strength/warmup/stretch without repeats
    total=tw+ts+ti+tst
    remaining=int(target*60-total)
    if remaining>120:
        # fill proportionally but never repeat ids
        extra_pool=(c_e+c_w+c_i+c_s)
        extra=[]
        for row in sorted(extra_pool, key=lambda r:_sort_key(r,pains,objective)):
            if row['id'] in used: continue
            # infer block from id prefix/table style
            b='strength' if str(row['id']).startswith('E') else 'isometrics' if str(row['id']).startswith('I') else 'warmups' if str(row['id']).startswith('C') else 'stretches'
            sec=_seconds(row,b,sem,payload=payload)
            if total+sec > target*60*1.05: continue
            item=_decorate(row,b,sem,payload=payload); used.add(row['id']); total+=sec
            if b=='strength': strength.append(item)
            elif b=='isometrics': iso.append(item)
            elif b=='warmups': warm.append(item)
            else: stretch.append(item)
            if total>=target*60*0.95: break
    blocks={"warmups":warm,"strength":strength,"isometrics":iso,"stretches":stretch}
    for k,v in blocks.items():
        pass
    duplicates=[]
    seen=set()
    for arr in blocks.values():
        for e in arr:
            if e['id'] in seen: duplicates.append(e['id'])
            seen.add(e['id'])
    te=round(total/60,1)
    explanation=[]
    explanation.append("Edad: " + (tg.get("age_policy") or {}).get("explanation","sin ajuste específico"))
    if tg['barriers']:
        explanation.append("Se entrega menos que Tp porque hay barreras activas: " + " | ".join(tg['barriers']))
    elif abs(te-tp)>tp*0.05:
        explanation.append("El motor quedó fuera del ±5%; con API conectada se puede ampliar dosificación/catálogo si el target lo permite.")
    tempos_used=[]
    for arr in blocks.values():
        for e in arr:
            if e.get("tempo") and e.get("tempo_reason"):
                tempos_used.append(e["tempo"] + ": " + e["tempo_reason"])
    if tempos_used:
        explanation.append("Tempo aplicado: " + tempos_used[0])
    result={"ok":True,"session_variation":"auto_randomized_if_no_seed","catalog":counts,"time_governance":tg,"tp":tp,"target_min":target,"te_min":te,"within_5_percent":abs(te-tp)<=tp*0.05 if target==tp else abs(te-target)<=max(2,target*0.08),"duplicates":duplicates,"blocks":blocks,"block_minutes":{k:round(sum(e['seconds'] for e in v)/60,1) for k,v in blocks.items()},"decision_trace":{"equipment_used":sorted(equipment),"candidate_counts":{"warmups":len(c_w),"strength":len(c_e),"isometrics":len(c_i),"stretches":len(c_s)},"selected_counts":{k:len(v) for k,v in blocks.items()},"scoring_trace":scoring_trace,"policy":"No repeated ID across all blocks; full SQLite catalog queried. V12/V12.1 scoring overlay applied before selection."},"explanation":explanation}

    _save_session_history(con, payload, result)
    result["history_summary"] = _history_summary(con)
    result["feedback_adaptation"] = _feedback_adaptation(con)
    result["detailed_feedback_adaptation"] = _detailed_feedback_adaptation(con)
    result["progression_recommendation"] = _progression_recommendation(con)
    result["fatigue_state"] = _fatigue_state(con)
    if result["feedback_adaptation"].get("notes"):
        result["explanation"].extend(["Feedback: " + n for n in result["feedback_adaptation"]["notes"]])
    if result["detailed_feedback_adaptation"].get("notes"):
        result["explanation"].extend(["Feedback detallado: " + n for n in result["detailed_feedback_adaptation"]["notes"]])

    if result["progression_recommendation"]:
        result["explanation"].append(
            "Progresión longitudinal: " +
            result["progression_recommendation"]["reason"]
        )

    if result["fatigue_state"]:
        result["explanation"].append(
            "Fatiga acumulada: " +
            result["fatigue_state"]["recommendation"]
        )

    result["explanation"].append("Scoring V12/V12.1: ranking multidimensional aplicado al catálogo antes de seleccionar ejercicios.")

    con.close()

    return result


# ===== VitalMotion Recovery Safe Patch =====

SIDE_TRANSITION_SECONDS = 10

def vm_tempo_tut(tempo):
    try:
        total = 0
        for part in str(tempo).split("-"):
            if part.upper() == "X":
                total += 1
            else:
                total += int(part)
        return total
    except:
        return 6

def vm_unilateral_total(work_seconds, exercise_rest=10):
    return (
        work_seconds +
        SIDE_TRANSITION_SECONDS +
        work_seconds +
        exercise_rest
    )

# ===== End Safe Patch =====


# ===== VitalMotion v0.7.7.3 REAL PATCH =====

SIDE_SWITCH_SECONDS = 10

def vm_real_tempo_display(tempo):
    try:
        parts = str(tempo).split("-")
        total = 0
        for p in parts:
            if p.upper() == "X":
                total += 1
            else:
                total += int(p)

        return {
            "tempo_visible": str(tempo),
            "tut_total": total
        }
    except:
        return {
            "tempo_visible": "2-1-2-1",
            "tut_total": 6
        }

def vm_real_unilateral_time(seconds_per_side, exercise_rest=10):
    return (
        seconds_per_side +
        SIDE_SWITCH_SECONDS +
        seconds_per_side +
        exercise_rest
    )

# ===== END PATCH =====
