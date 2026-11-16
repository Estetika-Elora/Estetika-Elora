"""Servicio de horarios disponibles (HU-23 · PRO-23): genera los bloques de un servicio.

Pasos de `generar`:
1. Validar el rango de fechas (desde hoy, hasta ≥ desde, máximo 90 días).
2. Obtener el horario de atención de la sede (API-I17); sin horario responde 422.
3. Verificar que el servicio se ofrezca en la sede y esté activo.
4. Consultar los horarios ocupados y bloqueados (API-I18).
5. Generar los bloques del tamaño de la duración del servicio y guardarlos.

`regenerar_sede` lo dispara HU-17 al guardar el horario (API-I19): regenera los próximos
30 días de cada servicio activo de la sede, cada uno con su propia duración.
"""

from datetime import date, datetime
from typing import Callable

from app.domain.disponibilidad import (
    GeneracionRequest,
    GeneracionResponse,
    generar_bloques,
    rango_regeneracion,
    validar_rango,
)
from app.domain.errores import PrecondicionNoCumplida
from app.repository.bloque_horario_repository import BloqueHorarioRepository
from app.service.sede_service import SedeService
from app.service.servicio_service import ServicioService


class DisponibilidadService:
    def __init__(
        self,
        sede_service: SedeService,
        servicio_service: ServicioService,
        repositorio: BloqueHorarioRepository,
        reloj: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._sedes = sede_service
        self._servicios = servicio_service
        self._repositorio = repositorio
        self._reloj = reloj

    def generar(self, sede_id: int, servicio_id: int, datos: GeneracionRequest) -> GeneracionResponse:
        ahora = self._reloj()
        validar_rango(datos.desde, datos.hasta, ahora.date())
        horario = self._horario_configurado(sede_id, servicio_id)
        servicio = self._servicios.obtener_ofrecido_en_sede(servicio_id, sede_id)
        cantidad = self._generar_y_guardar(sede_id, servicio, horario, datos.desde, datos.hasta, ahora)
        return GeneracionResponse(
            sede_id=sede_id,
            servicio_id=servicio_id,
            desde=datos.desde,
            hasta=datos.hasta,
            duracion_min=servicio["duracion_min"],
            bloques_generados=cantidad,
        )

    def regenerar_sede(self, sede_id: int) -> None:
        ahora = self._reloj()
        horario = self._sedes.obtener_horario(sede_id).model_dump(mode="json")["horario"]
        desde, hasta = rango_regeneracion(ahora.date())
        for servicio in self._servicios.listar_activos_de_sede(sede_id):
            self._generar_y_guardar(sede_id, servicio, horario, desde, hasta, ahora)

    def _horario_configurado(self, sede_id: int, servicio_id: int) -> list[dict]:
        horario = self._sedes.obtener_horario(sede_id).model_dump(mode="json")["horario"]
        if not horario:
            raise PrecondicionNoCumplida(
                "La sede no tiene horario de atención configurado",
                {"sede_id": sede_id, "servicio_id": servicio_id},
            )
        return horario

    def _generar_y_guardar(
        self, sede_id: int, servicio: dict, horario: list[dict], desde: date, hasta: date, ahora: datetime
    ) -> int:
        servicio_id = servicio["servicio_id"]
        ocupados = self._ocupados(sede_id, servicio_id, desde, hasta)
        bloques = generar_bloques(horario, desde, hasta, servicio["duracion_min"], ocupados, ahora)
        return self._repositorio.reemplazar_en_rango(sede_id, servicio_id, desde, hasta, bloques)

    def _ocupados(self, sede_id: int, servicio_id: int, desde: date, hasta: date) -> list[tuple[date, int, int]]:
        """API-I18: intervalos ocupados por reservas confirmadas y bloqueos de agenda.

        Las reservas llegan con HU-37 y los bloqueos con HU-24; mientras tanto no hay ninguno.
        """
        return []
