from dotenv import load_dotenv

# Se carga el .env antes de importar los routers: estos leen las variables al crearse.
load_dotenv()

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from starlette.exceptions import HTTPException as StarletteHTTPException  # noqa: E402

from app.api import producto_router, sede_router  # noqa: E402
from app.api.respuestas import cuerpo_error, traducir_errores_validacion  # noqa: E402
from app.service.almacenamiento_service import AlmacenamientoLocal  # noqa: E402

app = FastAPI(title="Estetika-Elora")

app.include_router(sede_router.router)
app.include_router(producto_router.router)

# Sin credenciales de Cloudinary las imágenes se guardan en local y se sirven en /uploads.
if isinstance(producto_router.almacenamiento, AlmacenamientoLocal):
    app.mount(
        "/uploads",
        StaticFiles(directory=producto_router.almacenamiento.carpeta),
        name="uploads",
    )


@app.exception_handler(StarletteHTTPException)
def manejar_http(request: Request, error: StarletteHTTPException) -> JSONResponse:
    """Devuelve todos los errores HTTP con el formato {message, data, success}."""
    if isinstance(error.detail, dict) and "success" in error.detail:
        cuerpo = error.detail
    else:
        cuerpo = cuerpo_error(str(error.detail))
    return JSONResponse(status_code=error.status_code, content=cuerpo, headers=error.headers)


@app.exception_handler(RequestValidationError)
def manejar_validacion(request: Request, error: RequestValidationError) -> JSONResponse:
    """Los errores de validación responden 400 (no 422) con el formato estándar."""
    return JSONResponse(status_code=400, content=traducir_errores_validacion(error.errors()))


@app.get("/health")
def health():
    return {"status": "ok"}
