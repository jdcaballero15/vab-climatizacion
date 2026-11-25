"""Datos técnicos del equipo (E03-10). Las listas viven en el código: sumar un gas no
necesita migración."""

from typing import Literal

# "Otro": el detalle va en las observaciones del equipo.
Refrigerant = Literal["R22", "R410A", "R32", "R407C", "R404A", "R134a", "R290", "other"]

# 220 monofásica, 380 trifásica.
PowerSupply = Literal["220", "380"]
