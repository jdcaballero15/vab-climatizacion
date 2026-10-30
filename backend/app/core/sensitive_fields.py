"""Campos que el rol tecnico nunca debe ver (ADR 0006).

Este es el unico archivo donde se edita la lista. El test de contrato
(tests/test_technician_contract.py) la recorre contra cada esquema *TechnicianOut
y falla si alguno la expone a cualquier profundidad. Al agregar un recurso con un
campo sensible nuevo, sumalo aca.
"""

FORBIDDEN_TECHNICIAN_FIELDS: frozenset[str] = frozenset(
    {
        "price",
        "unit_price",
        "list_price",
        "amount",
        "charge",
        "total",
        # Cobro de la orden (E04-14).
        "billing",
        "parts_amount",
        "labor_amount",
        "invoice_number",
        "history",
        # Datos de contacto del cliente: el técnico ve solo el nombre (E03-02).
        "phone",
        "email",
    }
)
