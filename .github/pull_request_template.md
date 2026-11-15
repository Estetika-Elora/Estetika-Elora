## Descripción
<!-- ¿Qué cambia este PR y por qué? -->

## Tipo de cambio
- [ ] Nueva funcionalidad (feat)
- [ ] Corrección de error (fix)
- [ ] Refactorización / estructura (refactor)
- [ ] Documentación (docs)
- [ ] Configuración / CI (chore, ci)

## Capas afectadas
- [ ] `app/api`
- [ ] `app/service`
- [ ] `app/domain`
- [ ] `app/repository`
- [ ] `main.py` / configuración

## ¿Cómo se probó?
<!-- Ej.: uvicorn main:app --reload y prueba de endpoints en /docs -->

## Checklist
- [ ] El servidor arranca sin errores con `uvicorn main:app --reload`
- [ ] Los endpoints afectados responden bien en `/docs`
- [ ] No hay lógica de negocio en `app/api` ni imports de FastAPI en `app/service`, `app/domain` o `app/repository`
