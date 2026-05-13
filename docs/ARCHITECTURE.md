# VitalMotion Architecture

## Estado actual

VitalMotion funciona como una app web full-stack:

- Frontend: Vercel
- Backend: FastAPI en Render
- Base de datos: SQLite
- Código fuente: GitHub
- Motor clínico: Python

## Flujo principal

Usuario
→ Frontend Vercel
→ Backend FastAPI Render
→ Motor VitalMotion
→ SQLite
→ Sesión recomendada

## Componentes principales

### Frontend

Ubicación:

`frontend/index.html`

Responsabilidades:

- ingreso de usuario
- conexión a API
- generación de sesión
- visualización de resultados
- feedback
- historial visible

### Backend

Ubicación:

`backend/app_v077_sqlite_connected.py`

Responsabilidades:

- exponer API
- conectar SQLite
- recibir perfil de usuario
- devolver sesión generada
- guardar feedback

### Motor clínico

Ubicación:

`backend/vitalmotion_engine_v077.py`

Responsabilidades:

- selección de ejercicios
- scoring
- semáforo clínico
- time governance
- age adaptation
- tempo intelligence
- no repeat
- progresión básica

### Base SQLite

Archivo actual:

`VitalMotion_v20_6_MVP_v077_SQLITE_CONNECTED.sqlite`

Contiene:

- catálogo de ejercicios
- scoring
- historial
- feedback
- capas clínicas

## Deploy actual

### Frontend

Vercel:

`https://vitalmotion-frontend-theta.vercel.app`

### Backend

Render:

`https://vitalmotion-backend.onrender.com`

Endpoint de salud:

`https://vitalmotion-backend.onrender.com/health`

## Reglas de continuidad

- No romper el runtime estable.
- No trabajar sobre placeholders.
- Todo cambio debe pasar por GitHub.
- Todo cambio debe poder revertirse.
- El frontend no debe depender de localhost.
- Toda mejora clínica debe ser explicable.
- Toda versión nueva debe conectar FastAPI + SQLite.
- Ninguna tabla histórica debe borrarse.
