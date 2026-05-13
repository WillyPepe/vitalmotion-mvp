from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict
import os
from pathlib import Path
from vitalmotion_engine_v077 import generate_session, catalog_counts, save_feedback, save_exercise_feedback, save_set_feedback, save_isometric_feedback

DB_PATH = os.environ.get("VITALMOTION_DB") or str(Path(__file__).resolve().parent / "VitalMotion_v20_6_MVP_v077_SQLITE_CONNECTED.sqlite")
DB_FILE = Path(DB_PATH)
DB_ZIP = DB_FILE.parent / "VitalMotion_v20_6_MVP_v077_SQLITE_CONNECTED.zip"

if not DB_FILE.exists() and DB_ZIP.exists():
    import zipfile
    with zipfile.ZipFile(DB_ZIP, "r") as z:
        z.extractall(DB_FILE.parent)
app = FastAPI(title='VitalMotion API', version='0.7.8.6-recovery')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])

class Payload(BaseModel):
    data: Dict[str, Any] | None = None

@app.get('/health')
def health():
    return {'status':'ok','version':'0.7.8.6','db':DB_PATH,'catalog':catalog_counts(DB_PATH)}

@app.get('/catalog/summary')
def catalog_summary():
    return catalog_counts(DB_PATH)

@app.post('/session/generate')
def session_generate(payload: Dict[str, Any]):
    try:
        data = payload.get('data', payload)
        # Normalización segura backend
        if 'weight_kg' in data:
            data['weight_kg'] = round(float(data.get('weight_kg') or 0))
        if 'peso' in data:
            data['peso'] = round(float(data.get('peso') or 0))
        if 'energy' in data:
            data['energy'] = max(1, min(10, round(float(data.get('energy') or 1))))
        if 'energia' in data:
            data['energia'] = max(1, min(10, round(float(data.get('energia') or 1))))
        if 'requested_time_min' in data:
            data['requested_time_min'] = max(20, min(120, round(float(data.get('requested_time_min') or 20))))
        return generate_session(data, DB_PATH)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/feedback/save')
def feedback_save(payload: Dict[str, Any]):
    try:
        data = payload.get('data', payload)
        return save_feedback(data, DB_PATH)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/feedback/exercise')
def feedback_exercise(payload: Dict[str, Any]):
    try:
        data = payload.get('data', payload)
        return save_exercise_feedback(data, DB_PATH)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/feedback/set')
def feedback_set(payload: Dict[str, Any]):
    try:
        data = payload.get('data', payload)
        return save_set_feedback(data, DB_PATH)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/feedback/isometric')
def feedback_isometric(payload: Dict[str, Any]):
    try:
        data = payload.get('data', payload)
        return save_isometric_feedback(data, DB_PATH)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
