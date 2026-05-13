# VitalMotion Clinical Engine

## Objetivo

VitalMotion debe generar sesiones de ejercicio adaptativas, seguras y explicables para usuarios entre 18 y 90 años.

El motor no debe prohibir movimiento innecesariamente.
Debe adaptar, proteger y progresar.

## Principios clínicos

- Seguridad antes que intensidad.
- Adaptación antes que prohibición.
- Progresión gradual.
- Explicación visible de cada decisión.
- Uso del historial para mejorar futuras sesiones.
- Priorización de adherencia.
- Semáforos clínicos claros.

## Componentes actuales

### Time Governance

El tiempo pedido por el usuario es una preferencia.
El sistema calcula un tiempo máximo clínicamente tolerable.

### No Repeat Engine

Evita repetir ejercicios exactos dentro de la sesión.

### Strength Tolerance

No elimina fuerza automáticamente.
Permite fuerza segura, dosificada y terapéutica.

### Age Adaptation

Adapta progresivamente según edad:
- densidad
- pausas
- complejidad
- unilateralidad
- recuperación

### Tempo Intelligence

Adapta tempo según:
- objetivo
- edad
- dolor
- energía
- riesgo
- tipo de ejercicio

### Scoring

Ordena ejercicios según compatibilidad con:
- objetivo
- dolencias
- condiciones
- seguridad
- equipamiento
- limitaciones

### Feedback

Actualmente existe feedback:
- post sesión
- por ejercicio
- por serie
- isométrico

Debe evolucionar a feedback móvil real dentro de la ejecución.

## Próxima evolución clínica

### Feedback intra-sesión

Cada ejercicio debe poder registrar:
- dolor
- RPE
- dificultad
- técnica
- molestia
- carga usada
- tolerancia

### Progresión longitudinal

El sistema debe usar historial para:
- subir volumen
- bajar volumen
- ajustar peso
- modificar tempo
- cambiar densidad
- sustituir ejercicios

### Runtime safety vivo

Durante la sesión, si el usuario reporta dolor o fatiga:
- reducir carga
- aumentar pausa
- cambiar ejercicio
- acortar sesión
- activar alerta clínica

## Reglas críticas

- Nunca borrar historial.
- Nunca borrar tablas clínicas.
- Toda decisión debe ser explicable.
- Todo cambio debe ser auditable.
- Toda progresión debe ser gradual.
- El usuario debe poder moverse siempre que sea seguro.
