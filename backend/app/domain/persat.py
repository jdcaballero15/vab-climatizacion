"""Reglas de limpieza de la exportación de Persat (E11-01, E11-02, D-010).

Funciones puras sobre los valores crudos de cada celda. Detalle de cada regla en
docs/domain/migracion-persat.md. Las tablas de corrección son de marcas y tipos, no
tienen datos de clientes.
"""

import re
import unicodedata
from dataclasses import dataclass

# Registros de Persat que no son clientes (columna Tipo).
INTERNAL_CLIENT_TYPES = frozenset({"OPERARIO", "DEPOSITO", "ADMINISTRACION"})
# El cliente de ejemplo que trae Persat lleva su nombre. Palabra completa: hay apellidos
# reales que empiezan con "Test".
_TEST_RECORD = re.compile(r"\b(persat|prueba|test)\b", re.IGNORECASE)

# Valores de ClientSegment y TaxCondition (app/db/models/client.py), sin depender de la base.
_SEGMENT_KEYWORDS = (
    ("PARTICULAR", "private_person"),
    ("COMERCIO", "business"),
    ("ESTADO", "government"),
    ("SANATORIO", "healthcare"),
    ("CLINICA", "healthcare"),
    ("HOTEL", "hotel"),
)
_CUIT = re.compile(r"\b\d{2}[-. ]?\d{8}[-. ]?\d\b")
_TAX_CONDITIONS = (
    (re.compile(r"consumidor\s+final", re.IGNORECASE), "final_consumer"),
    (re.compile(r"responsable\s+inscripto|\bR\.?\s?I\b\.?", re.IGNORECASE), "registered_taxpayer"),
    (re.compile(r"monotribut\w*", re.IGNORECASE), "monotributo"),
)

AIR_CONDITIONER = "Aire acondicionado"
COMMERCIAL_FRIDGE = "Heladera comercial"
HOME_FRIDGE = "Heladera familiar"
NO_LOCATION = "Sin ubicación"

# Clave: solo letras en mayúscula, sin acentos.
_SUBTYPES = {
    "SPLIT": "Split",
    "APLIT": "Split",
    "SPLUT": "Split",
    "SPLI": "Split",
    "SPLIR": "Split",
    "SPLT": "Split",
    "SPLITINVERTER": "Split inverter",
    "PISOTECHO": "Piso techo",
    "ROOFTOP": "Rooftop",
    "BAJOSILUETA": "Bajo silueta",
    "COMPACTO": "Compacto",
    "CASETTE": "Cassette",
    "CASSETTE": "Cassette",
    "VENTANA": "Ventana",
    "FRIGOBAR": "Frigobar",
    "COMERCIAL": "Comercial",
}
_BRAND_FIXES = {
    "BLUSTAR": "Blue Star",
    "BLUESTAR": "Blue Star",
    "COVENTRI": "Coventry",
    "GOLMAN": "Goldman",
    "HITACHY": "Hitachi",
    "HOMELEADER": "Home Leader",
    "HOMELEDER": "Home Leader",
    "KERLVINATOR": "Kelvinator",
    "MIIDEA": "Midea",
    "PHILPO": "Philco",
    "STANDARELECTRIC": "Standard Electric",
    "STANDARDELECTRIC": "Standard Electric",
    "DELONGHI": "DeLonghi",
}
_BRAND_ACRONYMS = frozenset({"BGH", "LG", "RCA", "TCL"})
# Valores de la columna marca que no son una marca.
_NOT_BRANDS = frozenset({"ACEROINOXIDABLE"})
_GASES = {
    "22": "R-22",
    "410": "R-410A",
    "410A": "R-410A",
    "404": "R-404A",
    "404A": "R-404A",
    "134A": "R-134a",
    "32": "R-32",
    "AMONIACO": "Amoníaco",
}
# Errores de arrastre de una planilla: se toman como R-410A y quedan para revisar.
_GAS_DRAG_ERRORS = frozenset({"411", "413", "414", "415"})
_CAPACITY = re.compile(r"^(\d+)\s*(FRG|FG|F|TR|W)?$", re.IGNORECASE)
_CAPACITY_UNITS = {"TR": "TR", "W": "W"}


def text(value: object) -> str:
    """Celda como texto sin espacios de más; vacía si no hay nada."""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return " ".join(str(value).split())


def _key(value: str) -> str:
    """Mayúsculas sin acentos y solo letras y números, para comparar variantes."""
    plain = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]", "", plain.upper())


def _sentence(value: str) -> str:
    return value[:1].upper() + value[1:].lower()


# ---------- Clientes ----------


def is_internal_client(client_type: str) -> bool:
    return _key(client_type) in INTERNAL_CLIENT_TYPES


def is_test_record(name: str) -> bool:
    return bool(_TEST_RECORD.search(name))


def client_number(raw: str) -> str:
    """Sin espacios alrededor del guion: `CLI -123` pasa a `CLI-123`."""
    return re.sub(r"\s*-\s*", "-", raw)


def segment(client_type: str) -> str:
    key = _key(client_type)
    for keyword, value in _SEGMENT_KEYWORDS:
        if keyword in key:
            return value
    return "unclassified"


@dataclass(frozen=True)
class Description:
    tax_id: str | None
    tax_condition: str | None
    reference: str | None


def split_description(raw: str) -> Description:
    """CUIT (11 dígitos) y condición fiscal van al cliente; el resto, a la referencia."""
    rest = raw
    tax_id = None
    cuit = _CUIT.search(rest)
    if cuit:
        tax_id = re.sub(r"\D", "", cuit.group())
        rest = rest.replace(cuit.group(), " ")
    tax_condition = None
    for pattern, value in _TAX_CONDITIONS:
        match = pattern.search(rest)
        if match:
            tax_condition = value
            rest = rest.replace(match.group(), " ")
            break
    reference = text(rest).strip(" -,.;/")
    return Description(tax_id, tax_condition, reference or None)


def email(raw: str) -> str | None:
    return raw.lower() or None


def phone(raw: object) -> str | None:
    return text(raw) or None


# ---------- Equipos ----------


def subtype(raw: str) -> str | None:
    return _SUBTYPES.get(_key(raw))


def equipment_type_name(raw_type: str, subtype_name: str | None) -> str:
    """Heladera si el tipo lo dice (familiar si es frigobar); cualquier otro, aire."""
    if "HELAD" in _key(raw_type):
        return HOME_FRIDGE if subtype_name == "Frigobar" else COMMERCIAL_FRIDGE
    return AIR_CONDITIONER


def function(raw: str) -> str | None:
    """La columna MODELO de Persat dice en realidad frío solo o frío/calor."""
    key = _key(raw)
    if "CALOR" in key:
        return "Frío/calor"
    if key.startswith("FRIO"):
        return "Frío solo"
    return None


def brand(raw: str) -> str | None:
    """Marca unificada, o None si la celda no es una marca (vacía, un número, un material)."""
    key = _key(raw)
    if not key or key.isdigit() or key in _NOT_BRANDS:
        return None
    if key in _BRAND_FIXES:
        return _BRAND_FIXES[key]
    if key in _BRAND_ACRONYMS:
        return key
    return " ".join(word.capitalize() for word in raw.split())


def is_known_brand(raw: str) -> bool:
    key = _key(raw)
    return key in _BRAND_FIXES or key in _BRAND_ACRONYMS or key in _KNOWN_BRAND_KEYS


@dataclass(frozen=True)
class Gas:
    name: str | None
    to_review: bool


def gas(raw: str) -> Gas:
    key = _key(raw).removeprefix("R")
    if not key:
        return Gas(None, False)
    if key in _GAS_DRAG_ERRORS:
        return Gas("R-410A", True)
    if key in _GASES:
        return Gas(_GASES[key], False)
    return Gas(raw, True)


def capacity(raw: str) -> str | None:
    """`3000FG`, `3000FRG` y `3000` son 3000 frigorías; también TR y W."""
    match = _CAPACITY.match(raw.strip())
    if not match:
        return raw or None
    number, unit = match.groups()
    return f"{number} {_CAPACITY_UNITS.get((unit or '').upper(), 'frigorías')}"


def voltage(raw: str) -> str | None:
    match = re.search(r"(220|380)", raw)
    return f"{match.group(1)} V" if match else (raw or None)


# Marcas que aparecen en la exportación: sirven para detectar columnas corridas.
_KNOWN_BRAND_KEYS = frozenset(
    {
        "ATMA",
        "BGH",
        "BRYANT",
        "CARRIER",
        "CONQUEROR",
        "COVENTRY",
        "DIPLOMATIC",
        "DURABRAND",
        "ELECTROLUX",
        "FEDER",
        "GOLDMAN",
        "GOLDSTAR",
        "GENERALELECTRIC",
        "HISENSE",
        "HITACHI",
        "INELRO",
        "KELVINATOR",
        "LENNOX",
        "LUFT",
        "MARSHALL",
        "MIDEA",
        "NOBLEX",
        "PANORAMIC",
        "PHILCO",
        "PHILIPS",
        "SAMSUNG",
        "SANYO",
        "SIAM",
        "SURREY",
        "TADIRAN",
        "TELEFUNKEN",
        "TEMSTAR",
        "TOPHOUSE",
        "TOSHIBA",
        "TRANE",
        "WHIRLPOOL",
        "YORK",
    }
)


@dataclass(frozen=True)
class EquipmentData:
    type_name: str
    brand: str | None
    notes: str | None
    to_review: tuple[str, ...]


def equipment_data(
    *,
    raw_type: str,
    raw_subtype: str,
    raw_model: str,
    raw_brand: str,
    raw_capacity: str,
    raw_gas: str,
    raw_voltage: str,
) -> EquipmentData:
    """Tipo, marca y la línea de observaciones de un equipo de Persat."""
    review: list[str] = []
    extra: list[str] = []
    # Columnas corridas: una marca en el subtipo, y la capacidad en la marca.
    if is_known_brand(raw_subtype) and not raw_capacity:
        raw_brand, raw_capacity, raw_subtype = raw_subtype, raw_brand, ""
    sub = subtype(raw_subtype) or subtype(raw_model) or subtype(raw_type)
    if raw_subtype and not subtype(raw_subtype):
        extra.append(raw_subtype)
    if not raw_type:
        review.append("tipo vacío, se toma como aire acondicionado")
    func = function(raw_model)
    if raw_model and not func and not subtype(raw_model):
        extra.append(raw_model)
    brand_name = brand(raw_brand)
    if raw_brand and not brand_name:
        if _key(raw_brand).isdigit() and not raw_capacity:
            raw_capacity = raw_brand
        else:
            extra.append(raw_brand)
    gas_data = gas(raw_gas)
    if gas_data.to_review:
        review.append(f"gas '{raw_gas}' para revisar")
    parts = [
        sub,
        func,
        capacity(raw_capacity),
        gas_data.name,
        voltage(raw_voltage),
        *extra,
    ]
    notes = ". ".join(_sentence(p) if p in extra else p for p in parts if p)
    return EquipmentData(
        type_name=equipment_type_name(raw_type, sub),
        brand=brand_name,
        notes=f"{notes}." if notes else None,
        to_review=tuple(review),
    )
