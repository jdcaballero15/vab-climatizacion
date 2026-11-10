"""Armado de los PDF (E09): comprobantes de retiro y devolución e informe mensual.

Funciones puras: reciben los datos ya leídos y devuelven los bytes. Nunca llevan precios
(decisión de Gonza del 2026-11-10). Con fuentes base de PDF (latin-1): alcanzan para el
español.
"""

from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO

from fpdf import FPDF

COMPANY = "VAB Climatización"


@dataclass(frozen=True)
class ReceiptData:
    title: str
    order_number: int
    client_name: str
    client_number: str
    site: str
    equipment: str | None
    done_at: datetime
    crew: str | None
    technicians: list[str]
    condition: str | None
    signer_name: str
    signature_png: bytes | None
    # Solo la devolución: falla, reparación, observación y materiales, sin precios.
    work_lines: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ReportLine:
    date: str
    number: int
    equipment: str
    work_type: str
    failure: str
    repair: str


@dataclass(frozen=True)
class MonthlyReportData:
    client_name: str
    client_number: str
    period: str
    lines: list[ReportLine]
    # Fecha fija para que el mismo período dé el mismo archivo (criterio 4).
    generated_for: datetime


def _latin(text: str) -> str:
    return text.encode("latin-1", "replace").decode("latin-1")


class _Document(FPDF):
    def __init__(self, title: str, created: datetime) -> None:
        super().__init__(format="A4")
        self.set_creation_date(created)
        self.set_title(_latin(title))
        self.set_author(_latin(COMPANY))
        self.set_auto_page_break(auto=True, margin=15)
        self.add_page()
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, _latin(COMPANY), new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "B", 13)
        self.cell(0, 8, _latin(title), new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def field(self, label: str, value: str) -> None:
        self.set_font("Helvetica", "B", 10)
        self.cell(45, 6, _latin(label))
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 6, _latin(value or "-"), new_x="LMARGIN", new_y="NEXT")

    def output_bytes(self) -> bytes:
        return bytes(self.output())


def build_receipt(data: ReceiptData) -> bytes:
    """Comprobante de retiro o devolución con la firma del cliente (E09-01, E09-02)."""
    pdf = _Document(f"{data.title} - Orden N° {data.order_number}", data.done_at)
    pdf.field("Cliente", f"{data.client_name} (N° {data.client_number})")
    pdf.field("Domicilio", data.site)
    pdf.field("Equipo", data.equipment or "Sin equipo cargado")
    pdf.field("Fecha", f"{data.done_at:%d/%m/%Y %H:%M}")
    pdf.field("Escuadrilla", data.crew or "-")
    pdf.field("Técnicos", ", ".join(data.technicians) or "-")
    if data.condition:
        pdf.field("Estado del equipo", data.condition)
    if data.work_lines:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "Trabajo realizado", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        for line in data.work_lines:
            pdf.multi_cell(0, 6, _latin(f"- {line}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.field("Firmó", data.signer_name)
    if data.signature_png:
        pdf.image(BytesIO(data.signature_png), w=60)
    return pdf.output_bytes()


def build_monthly_report(data: MonthlyReportData) -> bytes:
    """Informe mensual del cliente: cada trabajo con fecha, equipo, tipo, falla y
    reparación; sin precios (E09-04)."""
    pdf = _Document(f"Informe de trabajos - {data.period}", data.generated_for)
    pdf.field("Cliente", f"{data.client_name} (N° {data.client_number})")
    pdf.field("Trabajos", str(len(data.lines)))
    pdf.ln(3)
    widths = (22, 16, 38, 30, 42, 42)
    headers = ("Fecha", "Orden", "Equipo", "Tipo", "Falla", "Reparación")
    pdf.set_font("Helvetica", "B", 9)
    for width, header in zip(widths, headers, strict=True):
        pdf.cell(width, 7, _latin(header), border=1)
    pdf.ln()
    pdf.set_font("Helvetica", "", 8)
    for line in data.lines:
        values = (
            line.date,
            str(line.number),
            line.equipment,
            line.work_type,
            line.failure,
            line.repair,
        )
        for width, value in zip(widths, values, strict=True):
            pdf.cell(width, 6, _latin(value[:40] or "-"), border=1)
        pdf.ln()
    return pdf.output_bytes()
