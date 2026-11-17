"""Servicio de reservas (MOD-05).

`consultar_disponibilidad` (HU-36 · PRO-36):
1. Validar el formato de la fecha (YYYY-MM-DD); si no, 400.
2. Pedir al catálogo los horarios generados para la sede, el servicio y la fecha (API-I03).
   Si el servicio no existe o no se ofrece en la sede responde 404.
3. Quitar los horarios con reserva confirmada (RN-21) y los que ya empezaron.

`crear` (HU-37 · PRO-37):
1. Verificar que la cuenta exista y esté activa (API-I04, RN-04); suspendida responde 403.
2. Verificar que el horario siga libre (API-I03); si no, 409.
3. Guardar la reserva en estado CONFIRMED. Si otra petición tomó el mismo horario al mismo
   tiempo, el repositorio la rechaza y también responde 409 (RN-21).
4. Enviar el correo de confirmación (API-E03). Si el correo falla, la reserva se conserva y
   la respuesta lo indica con `correo_enviado = false`.
"""

from datetime import date, datetime
from typing import Callable

from app.domain.errores import RecursoDuplicado, ServicioExternoNoDisponible
from app.domain.reserva import (
    MENSAJE_HORARIO_NO_DISPONIBLE,
    DisponibilidadResponse,
    EstadoReserva,
    ReservaCreate,
    ReservaResponse,
    filtrar_horarios_libres,
    leer_fecha_consulta,
    verificar_puede_reservar,
)
from app.repository.reserva_repository import ReservaRepository
from app.service.disponibilidad_service import DisponibilidadService
from app.service.plantillas_correo import correo_reserva_confirmada
from app.service.sede_service import SedeService
from app.service.usuario_service import ServicioCorreo, UsuarioService


class ReservaService:
    def __init__(
        self,
        repositorio: ReservaRepository,
        disponibilidad: DisponibilidadService,
        sedes: SedeService,
        usuarios: UsuarioService,
        correo: ServicioCorreo,
        reloj: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._repositorio = repositorio
        self._disponibilidad = disponibilidad
        self._sedes = sedes
        self._usuarios = usuarios
        self._correo = correo
        self._reloj = reloj

    def consultar_disponibilidad(self, sede_id: int, servicio_id: int, fecha: str) -> DisponibilidadResponse:
        return self._disponibilidad_del_dia(sede_id, servicio_id, leer_fecha_consulta(fecha))[0]

    def crear(self, datos: ReservaCreate) -> ReservaResponse:
        usuario = self._usuarios.obtener_cuenta(datos.usuario_id)
        verificar_puede_reservar(usuario)

        disponibilidad, nombre_servicio = self._disponibilidad_del_dia(datos.sede_id, datos.servicio_id, datos.fecha)
        if datos.hora not in disponibilidad.horarios_libres:
            raise RecursoDuplicado(MENSAJE_HORARIO_NO_DISPONIBLE, self._datos_horario(datos))
        nombre_sede = self._sedes.obtener_nombre(datos.sede_id)

        reserva = self._repositorio.crear(
            {
                "usuario_id": datos.usuario_id,
                "sede_id": datos.sede_id,
                "servicio_id": datos.servicio_id,
                "fecha": datos.fecha,
                "hora": datos.hora,
                "estado": EstadoReserva.CONFIRMED,
                "creada_en": self._reloj(),
            }
        )
        if reserva is None:
            raise RecursoDuplicado(MENSAJE_HORARIO_NO_DISPONIBLE, self._datos_horario(datos))

        return ReservaResponse(
            reserva_id=reserva["reserva_id"],
            sede=nombre_sede,
            servicio=nombre_servicio,
            fecha=reserva["fecha"],
            hora=reserva["hora"],
            estado=reserva["estado"],
            correo_enviado=self._enviar_confirmacion(usuario, reserva, nombre_sede, nombre_servicio),
        )

    def _disponibilidad_del_dia(
        self, sede_id: int, servicio_id: int, fecha: date
    ) -> tuple[DisponibilidadResponse, str]:
        bloques = self._disponibilidad.listar_bloques(sede_id, servicio_id, fecha)
        reservadas = {r["hora"] for r in self._repositorio.listar_confirmadas(sede_id, servicio_id, fecha)}
        respuesta = DisponibilidadResponse(
            sede_id=sede_id,
            servicio_id=servicio_id,
            fecha=fecha,
            duracion_min=bloques["duracion_min"],
            horarios_libres=filtrar_horarios_libres(fecha, bloques["horas"], reservadas, self._reloj()),
        )
        return respuesta, bloques["nombre"]

    def _enviar_confirmacion(self, usuario: dict, reserva: dict, sede: str, servicio: str) -> bool:
        correo = correo_reserva_confirmada(
            usuario["correo"],
            usuario["nombre"],
            reserva["reserva_id"],
            sede,
            servicio,
            reserva["fecha"].isoformat(),
            reserva["hora"],
        )
        try:
            self._correo.enviar(correo)
        except ServicioExternoNoDisponible:
            return False
        return True

    @staticmethod
    def _datos_horario(datos: ReservaCreate) -> dict:
        return {
            "sede_id": datos.sede_id,
            "servicio_id": datos.servicio_id,
            "fecha": datos.fecha.isoformat(),
            "hora": datos.hora,
        }
