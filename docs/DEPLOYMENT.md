# VitalMotion Deployment

## Arquitectura de deploy actual

Frontend:
- Vercel

Backend:
- Render

Repositorio:
- GitHub

Base:
- SQLite persistente

---

# URLs oficiales

## Frontend producción

https://vitalmotion-frontend-theta.vercel.app

## Backend producción

https://vitalmotion-backend.onrender.com

## Health endpoint

https://vitalmotion-backend.onrender.com/health

---

# Flujo de actualización

GitHub
→ push/commit
→ Vercel redeploy
→ Frontend actualizado

GitHub backend
→ Render redeploy
→ Backend actualizado

---

# Reglas críticas de deploy

## Frontend

Nunca dejar:

http://127.0.0.1:8080

como URL por defecto.

Siempre usar:

https://vitalmotion-backend.onrender.com

## Backend

Debe mantener:
- FastAPI
- SQLite
- endpoints estables
- CORS habilitado

## SQLite

Nunca borrar:
- tablas
- historial
- feedback
- catálogo clínico

---

# Checklist antes de publicar

## Frontend

- conecta API
- genera sesión
- feedback funciona
- no usa localhost
- funciona incógnito
- funciona Mac
- funciona Windows

## Backend

- /health responde OK
- Render activo
- SQLite accesible
- endpoints responden
- sin errores 500

---

# Estrategia futura

## Corto plazo

- estabilización
- auditoría
- documentación
- logging
- analytics

## Mediano plazo

- PostgreSQL
- autenticación
- multiusuario
- dashboards

## Largo plazo

- IA adaptativa
- motor predictivo
- clínica profesional
- SaaS
