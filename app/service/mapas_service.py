"""Validación de direcciones con Nominatim de OpenStreetMap (API-E04). Gratis, sin API key.

Nominatim no conoce la placa colombiana ("# 48-20"): encuentra la vía ("Carrera 33"), y si
la vía no existe devuelve otra parecida ("Carrera 999" → "Carrera 10"). Por eso:

1. Se separa la dirección en vía principal ("Carrera 33") y cruce ("Calle 48").
2. Se busca la vía en la ciudad y se exige que el campo `road` del resultado sea la misma
   vía. Si no coincide, la dirección no es válida.
3. Se busca también la vía del cruce para ubicar la sede cerca de la esquina real: se toma
   el par de tramos más cercano entre ambas vías (punto medio si están a menos de 500 m;
   si no, el tramo de la vía principal más cercano al cruce).

Limitación: la precisión es de cuadra, no de placa exacta (OSM no tiene la numeración
colombiana).

Política de uso de Nominatim: máximo 1 petición por segundo y User-Agent propio.
"""

import math
import re
import threading
import time
import unicodedata
from dataclasses import dataclass

import httpx

from app.domain.errores import ServicioExternoNoDisponible

URL_NOMINATIM = "https://nominatim.openstreetmap.org/search"
DISTANCIA_MAXIMA_CRUCE_METROS = 500

# Abreviaturas comunes de vías en Colombia → nombre usado en OpenStreetMap.
_TIPOS_VIA = {
    "avenida calle": "Avenida Calle",
    "av calle": "Avenida Calle",
    "ac": "Avenida Calle",
    "avenida carrera": "Avenida Carrera",
    "av carrera": "Avenida Carrera",
    "ak": "Avenida Carrera",
    "calle": "Calle",
    "cll": "Calle",
    "cl": "Calle",
    "carrera": "Carrera",
    "cra": "Carrera",
    "kra": "Carrera",
    "kr": "Carrera",
    "cr": "Carrera",
    "diagonal": "Diagonal",
    "dg": "Diagonal",
    "transversal": "Transversal",
    "tv": "Transversal",
    "tr": "Transversal",
    "avenida": "Avenida",
    "av": "Avenida",
}

# Tipo de la vía que cruza a la vía principal en la nomenclatura en cuadrícula.
_TIPO_CRUCE = {
    "Calle": "Carrera",
    "Avenida Calle": "Carrera",
    "Diagonal": "Carrera",
    "Carrera": "Calle",
    "Avenida Carrera": "Calle",
    "Transversal": "Calle",
}

_NUMERO = r"\d+(?:\s?[a-z](?![a-z]))?"
_PATRON_DIRECCION = re.compile(
    rf"^(?P<tipo>{'|'.join(sorted(_TIPOS_VIA, key=len, reverse=True))})\s*"
    rf"(?P<numero>{_NUMERO})\s*(?:bis\s*(?:[a-z](?![a-z]))?\s*)?(?:sur|norte|este|oeste)?\s*"
    rf"(?:#|no|n°|nº|numero)?\s*"
    rf"(?P<cruce>{_NUMERO})\s*(?:bis\s*(?:[a-z](?![a-z]))?\s*)?-\s*\d+"
)


@dataclass(frozen=True)
class Coordenadas:
    latitud: float
    longitud: float


@dataclass(frozen=True)
class DireccionColombiana:
    via: str  # "Carrera 33"
    cruce: str | None  # "Calle 48"


def _sin_acentos(texto: str) -> str:
    normal = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in normal if not unicodedata.combining(c))


def _normalizar(texto: str) -> str:
    texto = _sin_acentos(texto).lower().replace(".", " ")
    return " ".join(texto.split())


def _numero_limpio(numero: str) -> str:
    return numero.replace(" ", "").upper()


def parsear_direccion(direccion: str) -> DireccionColombiana | None:
    """Convierte "Cra 33 # 48-20" en vía "Carrera 33" y cruce "Calle 48".

    Devuelve None si la dirección no sigue la nomenclatura en cuadrícula.
    """
    coincidencia = _PATRON_DIRECCION.match(_normalizar(direccion))
    if coincidencia is None:
        return None
    tipo = _TIPOS_VIA[coincidencia["tipo"]]
    via = f"{tipo} {_numero_limpio(coincidencia['numero'])}"
    tipo_cruce = _TIPO_CRUCE.get(tipo)
    cruce = f"{tipo_cruce} {_numero_limpio(coincidencia['cruce'])}" if tipo_cruce else None
    return DireccionColombiana(via=via, cruce=cruce)


def _clave_via(nombre: str) -> str:
    """Forma comparable de una vía: "Avenida Carrera 27 A" → "carrera 27a"."""
    texto = _normalizar(nombre)
    texto = re.sub(r"^avenida (calle|carrera) ", r"\1 ", texto)
    return re.sub(r"(\d+) ([a-z])\b", r"\1\2", texto)


def es_misma_via(via_encontrada: str | None, via_buscada: str) -> bool:
    if not via_encontrada:
        return False
    encontrada, buscada = _clave_via(via_encontrada), _clave_via(via_buscada)
    # Acepta sufijos como "Carrera 33 Sur", pero no "Carrera 33A" cuando se busca "Carrera 33".
    return encontrada == buscada or encontrada.startswith(buscada + " ")


def _distancia_metros(a: Coordenadas, b: Coordenadas) -> float:
    radio = 6_371_000
    lat1, lat2 = math.radians(a.latitud), math.radians(b.latitud)
    dlat = lat2 - lat1
    dlon = math.radians(b.longitud - a.longitud)
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * radio * math.asin(math.sqrt(h))


class MapasService:
    _bloqueo = threading.Lock()
    _ultima_peticion = 0.0

    def __init__(
        self, user_agent: str, timeout: float = 10.0, pausa_entre_peticiones: float = 1.0
    ) -> None:
        self._user_agent = user_agent
        self._timeout = timeout
        self._pausa = pausa_entre_peticiones

    def geocodificar(self, direccion: str, ciudad: str) -> Coordenadas | None:
        """Devuelve las coordenadas de la dirección o None si no existe en el mapa.

        Lanza ServicioExternoNoDisponible si Nominatim no responde.
        """
        partes = parsear_direccion(direccion)
        if partes is None:
            # Dirección fuera de la cuadrícula (p. ej. "Km 2 vía Girón"): búsqueda libre.
            resultados = self._buscar({"q": f"{direccion}, {ciudad}, Colombia"}, limite=1)
            if not resultados:
                return None
            punto = self._coordenadas(resultados[0])
            return Coordenadas(round(punto.latitud, 6), round(punto.longitud, 6))

        tramos_via = self._buscar_via(partes.via, ciudad)
        if not tramos_via:
            return None
        punto = tramos_via[0]

        if partes.cruce:
            tramos_cruce = self._buscar_via(partes.cruce, ciudad)
            mejor = min(
                ((a, b) for a in tramos_via for b in tramos_cruce),
                key=lambda par: _distancia_metros(*par),
                default=None,
            )
            if mejor:
                a, b = mejor
                if _distancia_metros(a, b) <= DISTANCIA_MAXIMA_CRUCE_METROS:
                    # Los dos tramos están en la misma esquina: se toma el punto medio.
                    punto = Coordenadas((a.latitud + b.latitud) / 2, (a.longitud + b.longitud) / 2)
                else:
                    # Vías largas (p. ej. Calle 72 en Bogotá): el tramo más cercano al cruce.
                    punto = a

        return Coordenadas(round(punto.latitud, 6), round(punto.longitud, 6))

    def _buscar_via(self, via: str, ciudad: str) -> list[Coordenadas]:
        resultados = self._buscar({"street": via, "city": ciudad}, limite=10)
        return [
            self._coordenadas(r)
            for r in resultados
            if es_misma_via(r.get("address", {}).get("road"), via)
        ]

    @staticmethod
    def _coordenadas(resultado: dict) -> Coordenadas:
        return Coordenadas(float(resultado["lat"]), float(resultado["lon"]))

    def _buscar(self, parametros: dict, limite: int) -> list[dict]:
        consulta = {
            **parametros,
            "format": "jsonv2",
            "addressdetails": 1,
            "countrycodes": "co",
            "limit": limite,
        }
        self._esperar_turno()
        try:
            respuesta = httpx.get(
                URL_NOMINATIM,
                params=consulta,
                headers={"User-Agent": self._user_agent},
                timeout=self._timeout,
            )
        except httpx.HTTPError as error:
            raise ServicioExternoNoDisponible(
                "El servicio de mapas no está disponible en este momento", {}
            ) from error
        if respuesta.status_code != 200:
            raise ServicioExternoNoDisponible(
                "El servicio de mapas no está disponible en este momento",
                {"codigo_servicio": respuesta.status_code},
            )
        return respuesta.json()

    def _esperar_turno(self) -> None:
        """Respeta el límite de 1 petición por segundo, aunque lleguen peticiones en paralelo."""
        with MapasService._bloqueo:
            espera = MapasService._ultima_peticion + self._pausa - time.monotonic()
            if espera > 0:
                time.sleep(espera)
            MapasService._ultima_peticion = time.monotonic()
