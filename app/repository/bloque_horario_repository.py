"""Repositorio de bloques de horario disponibles en memoria (lista de diccionarios).

Cada bloque es {"sede_id", "servicio_id", "fecha", "hora"}. Los genera HU-23 y los
consulta HU-36. Al regenerar, los bloques del rango se reemplazan; los de otras fechas
no se tocan.
"""

import copy
import threading
from datetime import date


class BloqueHorarioRepository:
    def __init__(self) -> None:
        self._bloques: list[dict] = []
        self._candado = threading.Lock()

    def reemplazar_en_rango(
        self, sede_id: int, servicio_id: int, desde: date, hasta: date, bloques: list[dict]
    ) -> int:
        with self._candado:
            self._bloques = [
                b
                for b in self._bloques
                if not (
                    b["sede_id"] == sede_id
                    and b["servicio_id"] == servicio_id
                    and desde <= b["fecha"] <= hasta
                )
            ]
            self._bloques.extend(
                {"sede_id": sede_id, "servicio_id": servicio_id, **bloque} for bloque in bloques
            )
            return len(bloques)

    def listar(self, sede_id: int, servicio_id: int, fecha: date) -> list[dict]:
        return sorted(
            (
                copy.deepcopy(b)
                for b in self._bloques
                if b["sede_id"] == sede_id and b["servicio_id"] == servicio_id and b["fecha"] == fecha
            ),
            key=lambda b: b["hora"],
        )


bloque_horario_repository = BloqueHorarioRepository()
