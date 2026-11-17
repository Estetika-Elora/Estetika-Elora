"""Repositorio de reservas en memoria (lista de diccionarios).

Cada reserva es {"reserva_id", "usuario_id", "sede_id", "servicio_id", "fecha", "hora",
"estado", "creada_en"}. Los identificadores empiezan en 1050 para coincidir con los casos de
prueba de la HU-37.
"""

import copy
import threading
from datetime import date

from app.domain.reserva import EstadoReserva


class ReservaRepository:
    def __init__(self, id_inicial: int = 1050) -> None:
        self._reservas: list[dict] = []
        self._siguiente_id = id_inicial
        self._candado = threading.Lock()

    def crear(self, datos: dict) -> dict | None:
        """Guarda la reserva. Devuelve None si ese horario ya tiene una reserva confirmada
        para la misma sede y servicio (RN-21, como un índice único)."""
        with self._candado:
            if any(
                r["sede_id"] == datos["sede_id"]
                and r["servicio_id"] == datos["servicio_id"]
                and r["fecha"] == datos["fecha"]
                and r["hora"] == datos["hora"]
                and r["estado"] == EstadoReserva.CONFIRMED
                for r in self._reservas
            ):
                return None
            reserva = {"reserva_id": self._siguiente_id, **datos}
            self._reservas.append(reserva)
            self._siguiente_id += 1
            return copy.deepcopy(reserva)

    def listar_confirmadas(self, sede_id: int, servicio_id: int, fecha: date) -> list[dict]:
        return [
            copy.deepcopy(r)
            for r in self._reservas
            if r["sede_id"] == sede_id
            and r["servicio_id"] == servicio_id
            and r["fecha"] == fecha
            and r["estado"] == EstadoReserva.CONFIRMED
        ]


reserva_repository = ReservaRepository()
