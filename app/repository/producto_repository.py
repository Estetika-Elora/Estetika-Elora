"""Repositorio de productos en memoria (lista de diccionarios).

Cada producto guarda sus imágenes como diccionarios {"url", "identificador"}: la URL es la
que ve el cliente y el identificador permite borrar la imagen del almacenamiento.
"""

import copy


class ProductoRepository:
    def __init__(self, id_inicial: int = 77) -> None:
        # Empieza en 77 para que coincida con los casos de prueba de HU-31.
        self._productos: list[dict] = []
        self._siguiente_id = id_inicial

    def crear(self, datos: dict) -> dict:
        producto = {"producto_id": self._siguiente_id, **copy.deepcopy(datos)}
        self._productos.append(producto)
        self._siguiente_id += 1
        return copy.deepcopy(producto)

    def obtener_por_id(self, producto_id: int) -> dict | None:
        for producto in self._productos:
            if producto["producto_id"] == producto_id:
                return copy.deepcopy(producto)
        return None

    def listar_por_empresa(self, empresa_id: int) -> list[dict]:
        return [copy.deepcopy(p) for p in self._productos if p["empresa_id"] == empresa_id]

    def actualizar(self, producto_id: int, cambios: dict) -> dict | None:
        for producto in self._productos:
            if producto["producto_id"] == producto_id:
                producto.update(copy.deepcopy(cambios))
                return copy.deepcopy(producto)
        return None

    def eliminar(self, producto_id: int) -> dict | None:
        for indice, producto in enumerate(self._productos):
            if producto["producto_id"] == producto_id:
                return self._productos.pop(indice)
        return None


# Instancia única compartida por toda la aplicación.
producto_repository = ProductoRepository()
