# VitalMotion — Deploy Ready v0.7.8.6

Paquete preparado para GitHub + Render + Vercel.

## Estructura

- `backend/`: FastAPI + motor + SQLite.
- `frontend/`: HTML/JS listo para Vercel.
- `docs/`: pasos y auditoría.

## Prueba local

Windows:
```bat
cd backend
start_local_windows.bat
```

Mac/Linux:
```bash
cd backend
chmod +x start_local_mac_linux.sh
./start_local_mac_linux.sh
```

Abrir `frontend/index.html` y conectar a:
```text
http://127.0.0.1:8080
```

## Deploy

Render backend:
```bash
pip install -r requirements.txt
uvicorn app_v077_sqlite_connected:app --host 0.0.0.0 --port $PORT
```

Vercel frontend:
- Root directory: `frontend`
- Sin build command.
- Output: raíz del proyecto.

## Nota

SQLite sirve para demo/colaboración. Para usuarios reales, migrar historial/feedback a PostgreSQL u otra base persistente.
