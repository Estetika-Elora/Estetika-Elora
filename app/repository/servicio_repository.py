"""Repositorio de servicios en memoria (lista de diccionarios).

Mínimo necesario para HU-23: solo consulta. El CRUD de servicios llega con HU-21 y la
asociación servicio-sede (campo `sedes`) con HU-22.
Datos semilla coherentes con los casos de prueba de las HU:
- Servicio 9: Limpieza facial, 60 minutos, activo en la sede 41.
- Servicio 10: Masaje relajante, 90 minutos, activo en la sede 41.
- Servicio 11: Depilación con cera, 45 minutos, inactivo (no genera horarios).
"""

import copy

from app.domain.estados import EstadoRegistro


class ServicioRepository:
    def __init__(self) -> None:
        self._servicios: list[dict] = [
            {
                "servicio_id": 9,
                "empresa_id": 18,
                "nombre": "Limpieza facial",
                "categoria": "Facial",
                "descripcion": "Limpieza profunda con extracción y mascarilla",
                "duracion_min": 60,
                "precio": 85000,
                "estado": EstadoRegistro.ACTIVE,
                "sedes": [41],
            },
            {
                "servicio_id": 10,
                "empresa_id": 18,
                "nombre": "Masaje relajante",
                "categoria": "Corporal",
                "descripcion": "Masaje de cuerpo completo con aceites esenciales",
                "duracion_min": 90,
                "precio": 120000,
                "estado": EstadoRegistro.ACTIVE,
                "sedes": [41],
            },
            {
                "servicio_id": 11,
                "empresa_id": 18,
                "nombre": "Depilación con cera",
                "categoria": "Depilación",
                "descripcion": "Depilación de piernas completas con cera tibia",
                "duracion_min": 45,
                "precio": 50000,
                "estado": EstadoRegistro.INACTIVE,
                "sedes": [41],
            },
        ]

    def obtener_por_id(self, servicio_id: int) -> dict | None:
        for servicio in self._servicios:
            if servicio["servicio_id"] == servicio_id:
                return copy.deepcopy(servicio)
        return None

    def listar_por_sede(self, sede_id: int) -> list[dict]:
        return [copy.deepcopy(s) for s in self._servicios if sede_id in s["sedes"]]


servicio_repository = ServicioRepository()
