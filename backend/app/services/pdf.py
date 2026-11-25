"""Armado de los PDF: comprobantes de retiro y devolución, informe mensual (E09) y
detalle de factura (E04-09).

Funciones puras: reciben los datos ya leídos y devuelven los bytes. Los de E09 nunca llevan
precios (decisión de Gonza del 2026-11-10); el detalle de factura es el único con importes
y es para administración. Con fuentes base de PDF (latin-1): alcanzan para el español.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, time
from io import BytesIO

from fpdf import FPDF

from app.core.config import Settings


@dataclass(frozen=True)
class CompanyHeader:
    """Quién emite el PDF (E09-07): nombre y, si están cargados, CUIT y domicilio."""

    name: str = "VAB Climatización"
    tax_id: str | None = None
    address: str | None = None

    def details(self) -> str | None:
        """La línea debajo del nombre: "CUIT ... · domicilio", o None si no hay datos."""
        parts = [f"CUIT {self.tax_id}" if self.tax_id else None, self.address]
        text = " · ".join(part for part in parts if part)
        return text or None


# Sin datos de configuración: solo el nombre.
DEFAULT_COMPANY = CompanyHeader()


def company_header(settings: Settings) -> CompanyHeader:
    return CompanyHeader(
        name=settings.company_name.strip() or CompanyHeader.name,
        tax_id=settings.company_tax_id.strip() or None,
        address=settings.company_address.strip() or None,
    )


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


@dataclass(frozen=True)
class InvoiceLine:
    description: str
    # Vacíos en mano de obra y otros cargos: solo los materiales llevan cantidad y precio.
    quantity: str
    unit_price: str
    amount: str


@dataclass(frozen=True)
class InvoiceOrder:
    number: int
    client: str
    site: str
    work: str
    lines: list[InvoiceLine]
    total: str


@dataclass(frozen=True)
class InvoiceDetailData:
    number: str
    issued_on: date
    orders: list[InvoiceOrder]
    total: str


def _latin(text: str) -> str:
    return text.encode("latin-1", "replace").decode("latin-1")


class _Document(FPDF):
    def __init__(self, title: str, created: datetime, company: CompanyHeader) -> None:
        super().__init__(format="A4")
        self.set_creation_date(created)
        self.set_title(_latin(title))
        self.set_author(_latin(company.name))
        self.set_auto_page_break(auto=True, margin=15)
        self.add_page()
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, _latin(company.name), new_x="LMARGIN", new_y="NEXT")
        details = company.details()
        if details:
            self.set_font("Helvetica", "", 9)
            self.cell(0, 5, _latin(details), new_x="LMARGIN", new_y="NEXT")
            self.ln(2)
        self.set_font("Helvetica", "B", 13)
        self.cell(0, 8, _latin(title), new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def field(self, label: str, value: str) -> None:
        self.set_font("Helvetica", "B", 10)
        self.cell(45, 6, _latin(label))
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 6, _latin(value or "-"), new_x="LMARGIN", new_y="NEXT")

    def fit(self, text: str, width: float) -> str:
        """El texto que entra en la celda; si no entra, recortado con "..."."""
        clean = _latin(text)
        if self.get_string_width(clean) <= width:
            return clean
        while clean and self.get_string_width(clean + "...") > width:
            clean = clean[:-1]
        return clean.rstrip() + "..."

    def output_bytes(self) -> bytes:
        return bytes(self.output())


def build_receipt(data: ReceiptData, company: CompanyHeader = DEFAULT_COMPANY) -> bytes:
    """Comprobante de retiro o devolución con la firma del cliente (E09-01, E09-02)."""
    pdf = _Document(f"{data.title} - Orden N° {data.order_number}", data.done_at, company)
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


def build_monthly_report(
    data: MonthlyReportData, company: CompanyHeader = DEFAULT_COMPANY
) -> bytes:
    """Informe mensual del cliente: cada trabajo con fecha, equipo, tipo, falla y
    reparación; sin precios (E09-04)."""
    pdf = _Document(f"Informe de trabajos - {data.period}", data.generated_for, company)
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
            pdf.cell(width, 6, pdf.fit(value or "-", width - 2), border=1)
        pdf.ln()
    return pdf.output_bytes()


def build_invoice_detail(
    data: InvoiceDetailData, company: CompanyHeader = DEFAULT_COMPANY
) -> bytes:
    """Detalle de lo facturado, orden por orden, para pasarlo al sistema de facturación o
    mandárselo al cliente. No reemplaza la factura electrónica (E04-09)."""
    pdf = _Document(
        f"Detalle de la factura {data.number}", datetime.combine(data.issued_on, time()), company
    )
    pdf.field("Fecha", f"{data.issued_on:%d/%m/%Y}")
    pdf.field("Órdenes", ", ".join(f"N° {order.number}" for order in data.orders))
    widths = (100, 22, 34, 34)
    for order in data.orders:
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, _latin(f"Orden N° {order.number}"), new_x="LMARGIN", new_y="NEXT")
        pdf.field("Cliente", order.client)
        pdf.field("Domicilio", order.site)
        pdf.field("Trabajo", order.work)
        pdf.set_font("Helvetica", "B", 9)
        for width, header in zip(
            widths, ("Concepto", "Cantidad", "Precio", "Importe"), strict=True
        ):
            pdf.cell(width, 7, _latin(header), border=1, align="L" if width == 100 else "R")
        pdf.ln()
        pdf.set_font("Helvetica", "", 9)
        for line in order.lines:
            pdf.cell(widths[0], 6, pdf.fit(line.description, widths[0] - 2), border=1)
            for width, value in zip(
                widths[1:], (line.quantity, line.unit_price, line.amount), strict=True
            ):
                pdf.cell(width, 6, _latin(value), border=1, align="R")
            pdf.ln()
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(sum(widths[:3]), 7, "Total de la orden", border=1, align="R")
        pdf.cell(widths[3], 7, _latin(order.total), border=1, align="R")
        pdf.ln()
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(sum(widths[:3]), 8, "Total facturado", align="R")
    pdf.cell(widths[3], 8, _latin(data.total), align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 8)
    pdf.multi_cell(0, 5, _latin("Documento no válido como factura."))
    return pdf.output_bytes()
