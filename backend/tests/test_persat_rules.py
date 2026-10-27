"""Reglas de limpieza de la exportación de Persat (docs/domain/migracion-persat.md)."""

import pytest

from app.domain import persat


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(" CLI -123 ", "CLI-123"), ("CLP - 9999", "CLP-9999"), ("10642", "10642")],
)
def test_numero_de_cliente_sin_espacios_en_el_guion(raw: str, expected: str) -> None:
    assert persat.client_number(persat.text(raw)) == expected


def test_texto_de_celda() -> None:
    assert persat.text("  Av.   Belgrano  123 ") == "Av. Belgrano 123"
    assert persat.text(3815551234.0) == "3815551234"
    assert persat.text(None) == ""


@pytest.mark.parametrize("client_type", ["OPERARIO", "DEPOSITO", "Depósito", "ADMINISTRACION"])
def test_registros_internos(client_type: str) -> None:
    assert persat.is_internal_client(client_type)


def test_cliente_comun_no_es_interno() -> None:
    assert not persat.is_internal_client("Cliente")


@pytest.mark.parametrize("name", ["Cliente Persat", "PRUEBA", "test"])
def test_registros_de_prueba(name: str) -> None:
    assert persat.is_test_record(name)


def test_un_apellido_que_empieza_con_test_no_es_de_prueba() -> None:
    assert not persat.is_test_record("Ficticio Testino")


@pytest.mark.parametrize(
    ("client_type", "expected"),
    [
        ("PARTICULARES", "private_person"),
        ("COMERCIOS", "business"),
        ("ESTADO", "government"),
        ("SANATORIOS- CLINICAS", "healthcare"),
        ("HOTELES", "hotel"),
        ("Cliente", "unclassified"),
        ("", "unclassified"),
    ],
)
def test_segmento_por_tipo(client_type: str, expected: str) -> None:
    assert persat.segment(client_type) == expected


def test_descripcion_con_cuit() -> None:
    assert persat.split_description("20-12345678-9") == persat.Description(
        "20123456789", None, None
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Consumidor Final", "final_consumer"),
        ("RI", "registered_taxpayer"),
        ("Responsable Inscripto", "registered_taxpayer"),
        ("Monotributista", "monotributo"),
    ],
)
def test_descripcion_con_condicion_fiscal(raw: str, expected: str) -> None:
    assert persat.split_description(raw) == persat.Description(None, expected, None)


def test_descripcion_mezclada_reparte_cada_parte() -> None:
    result = persat.split_description("30712345674 - RI - Piso 3 depto B")
    assert result == persat.Description("30712345674", "registered_taxpayer", "Piso 3 depto B")


def test_descripcion_sin_cuit_ni_condicion_va_a_la_referencia() -> None:
    assert persat.split_description("Frente a la plaza") == persat.Description(
        None, None, "Frente a la plaza"
    )
    # "RI" dentro de una palabra no es la condición fiscal.
    assert persat.split_description("Barrio Rivadavia").tax_condition is None


def test_email_en_minusculas() -> None:
    assert persat.email("Compras@Ficticio.COM") == "compras@ficticio.com"
    assert persat.email("") is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("SPLIT", "Split"),
        ("APLIT", "Split"),
        ("SPLIT.", "Split"),
        ("Piso Techo", "Piso techo"),
        ("CASETTE", "Cassette"),
        ("FRIGO BAR", "Frigobar"),
        ("SPLIT INVERTER", "Split inverter"),
        ("", None),
    ],
)
def test_subtipo_unificado(raw: str, expected: str | None) -> None:
    assert persat.subtype(raw) == expected


@pytest.mark.parametrize(
    ("raw_type", "raw_subtype", "expected"),
    [
        ("A.AC.", "SPLIT", persat.AIR_CONDITIONER),
        ("", "SPLIT", persat.AIR_CONDITIONER),
        ("HELADERA", "Comercial", persat.COMMERCIAL_FRIDGE),
        ("Helader", "FRIGO BAR", persat.HOME_FRIDGE),
    ],
)
def test_tipo_de_equipo(raw_type: str, raw_subtype: str, expected: str) -> None:
    assert persat.equipment_type_name(raw_type, persat.subtype(raw_subtype)) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("Frio Solo", "Frío solo"), ("Frio slo", "Frío solo"), ("FRIO / CALOR", "Frío/calor")],
)
def test_funcion_desde_la_columna_modelo(raw: str, expected: str) -> None:
    assert persat.function(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("CARRIER", "Carrier"),
        ("Carrier", "Carrier"),
        ("HITACHY", "Hitachi"),
        ("Home Leder", "Home Leader"),
        ("BLU STAR", "Blue Star"),
        ("Mi Idea", "Midea"),
        ("bgh", "BGH"),
        ("General Electric", "General Electric"),
        ("15000", None),
        ("Acero Inoxidable", None),
        ("", None),
    ],
)
def test_marca_unificada(raw: str, expected: str | None) -> None:
    assert persat.brand(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("R22", "R-22"),
        ("R-410", "R-410A"),
        ("410", "R-410A"),
        ("R-404", "R-404A"),
        ("R-134a", "R-134a"),
        ("R32", "R-32"),
    ],
)
def test_gas_unificado(raw: str, expected: str) -> None:
    assert persat.gas(raw) == persat.Gas(expected, False)


def test_gas_con_error_de_arrastre_es_r410a_para_revisar() -> None:
    assert persat.gas("R413") == persat.Gas("R-410A", True)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("3000FG", "3000 frigorías"),
        ("3000FRG", "3000 frigorías"),
        ("3000 FG", "3000 frigorías"),
        ("3000", "3000 frigorías"),
        ("4500F", "4500 frigorías"),
        ("20TR", "20 TR"),
        ("1254W", "1254 W"),
        ("", None),
    ],
)
def test_capacidad(raw: str, expected: str | None) -> None:
    assert persat.capacity(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"), [("220v", "220 V"), ("380", "380 V"), ("380v Trifasic", "380 V")]
)
def test_tension(raw: str, expected: str) -> None:
    assert persat.voltage(raw) == expected


def _data(**overrides: str) -> persat.EquipmentData:
    values = {
        "raw_type": "A.AC.",
        "raw_subtype": "SPLIT",
        "raw_model": "",
        "raw_brand": "CARRIER",
        "raw_capacity": "3000FG",
        "raw_gas": "R410",
        "raw_voltage": "",
    }
    values.update(overrides)
    return persat.equipment_data(**values)


def test_observaciones_en_una_linea() -> None:
    data = _data(raw_model="Frio/ Calor", raw_voltage="220V")
    assert data == persat.EquipmentData(
        type_name=persat.AIR_CONDITIONER,
        brand="Carrier",
        notes="Split. Frío/calor. 3000 frigorías. R-410A. 220 V.",
        to_review=(),
    )


def test_columnas_corridas_marca_en_subtipo() -> None:
    data = _data(raw_subtype="BGH", raw_brand="15000", raw_capacity="")
    assert data.brand == "BGH"
    assert data.notes == "15000 frigorías. R-410A."


def test_tipo_vacio_queda_para_revisar() -> None:
    data = _data(raw_type="")
    assert data.type_name == persat.AIR_CONDITIONER
    assert data.to_review == ("tipo vacío, se toma como aire acondicionado",)


def test_lo_que_no_tiene_campo_propio_va_a_observaciones() -> None:
    data = _data(
        raw_type="HELADERA",
        raw_subtype="Comercial",
        raw_model="Tipo Mesada",
        raw_brand="Acero Inoxidable",
        raw_capacity="",
        raw_gas="R-404",
    )
    assert data.type_name == persat.COMMERCIAL_FRIDGE
    assert data.brand is None
    assert data.notes == "Comercial. R-404A. Tipo mesada. Acero inoxidable."
