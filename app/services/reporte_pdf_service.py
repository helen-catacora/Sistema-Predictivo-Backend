"""Servicio de generación de reportes PDF con reportlab."""
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ── Colores institucionales ───────────────────────────────────────────
NAVY = colors.HexColor("#1B2A4A")
YELLOW = colors.HexColor("#F5A623")
RED = colors.HexColor("#EF4444")
GREEN = colors.HexColor("#22C55E")
GRAY = colors.HexColor("#6B7280")
GRAY_LIGHT = colors.HexColor("#F3F4F6")

NIVEL_COLORES = {
    "Bajo": GREEN,
    "Medio": YELLOW,
    "Alto": colors.HexColor("#F97316"),
    "Critico": RED,
}

# ── Zona horaria y rutas ──────────────────────────────────────────────
GMT_MINUS_4 = timezone(timedelta(hours=-4))
_ASSETS_DIR = Path(__file__).parent.parent.parent / "assets"

# ── Márgenes y medidas de página ──────────────────────────────────────
_LEFT_MARGIN = 0.75 * inch
_RIGHT_MARGIN = 0.75 * inch
_BOTTOM_MARGIN = 0.5 * inch
# topMargin alto para dejar espacio al header dibujado en canvas
_TOP_MARGIN = 1.75 * inch


# ── Helpers de logo ───────────────────────────────────────────────────

def _get_logo_path() -> "Path | None":
    """Devuelve la ruta del logo si existe, probando múltiples nombres."""
    for nombre in ["logo-emi.png", "logoEmi.png", "logo-emi.jpg", "logoEmi.jpg"]:
        ruta = _ASSETS_DIR / nombre
        if ruta.exists():
            return ruta
    return None


def _get_logo() -> "Image | None":
    """Retorna un objeto Image de reportlab con el logo, o None si no existe."""
    path = _get_logo_path()
    if path:
        return Image(str(path), width=0.75 * inch, height=0.65 * inch)
    return None


# ── Canvas: header + marca de agua en cada página ────────────────────

def _make_page_callback(titulo_reporte: str, usuario_nombre: str = ""):
    """Retorna una función que dibuja el header institucional y marca de agua en cada página."""

    def _dibujar_pagina(canvas, doc):
        canvas.saveState()

        page_width, page_height = letter
        left_x = _LEFT_MARGIN
        right_x = page_width - _RIGHT_MARGIN

        # ── Marca de agua (centrada, baja opacidad) ───────────────
        wm_path = _ASSETS_DIR / "emi.png"
        if wm_path.exists():
            wm_size = 4.5 * inch
            wm_x = (page_width - wm_size) / 2
            wm_y = (page_height - wm_size) / 2
            canvas.drawImage(
                str(wm_path), wm_x, wm_y, wm_size, wm_size,
                mask="auto", preserveAspectRatio=True,
            )
            # Capa blanca para reducir opacidad de la imagen
            canvas.setFillColorRGB(1, 1, 1)
            canvas.setFillAlpha(0.88)
            canvas.rect(wm_x, wm_y, wm_size, wm_size, fill=1, stroke=0)
            canvas.setFillAlpha(1.0)

        # ── Logo (extremo izquierdo) ──────────────────────────────
        logo_w = 0.75 * inch
        logo_h = 0.65 * inch
        top_y = page_height - 0.35 * inch
        logo_y = top_y - logo_h

        logo_path = _get_logo_path()
        if logo_path:
            canvas.drawImage(
                str(logo_path), left_x, logo_y, logo_w, logo_h,
                mask="auto", preserveAspectRatio=True,
            )

        # ── Texto institucional (extremo derecho) ─────────────────
        inst = "ESCUELA MILITAR DE INGENIERÍA — SISTEMA PREDICTIVO DE ABANDONO ESTUDIANTIL"
        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(NAVY)
        inst_w = canvas.stringWidth(inst, "Helvetica-Bold", 8)
        avail = right_x - (left_x + logo_w + 0.15 * inch)

        if inst_w <= avail:
            canvas.drawRightString(right_x, logo_y + (logo_h - 8) / 2, inst)
        else:
            l1 = "ESCUELA MILITAR DE INGENIERÍA"
            l2 = "SISTEMA PREDICTIVO DE ABANDONO ESTUDIANTIL"
            canvas.drawRightString(right_x, logo_y + logo_h * 0.65, l1)
            canvas.drawRightString(right_x, logo_y + logo_h * 0.25, l2)

        # ── Línea separadora ──────────────────────────────────────
        sep_y = logo_y - 5
        canvas.setStrokeColor(NAVY)
        canvas.setLineWidth(1.5)
        canvas.line(left_x, sep_y, right_x, sep_y)

        # ── Título del reporte (centrado, bajo la línea) ──────────
        canvas.setFont("Helvetica-Bold", 15)
        canvas.setFillColor(NAVY)
        canvas.drawCentredString(page_width / 2, sep_y - 22, titulo_reporte)

        canvas.restoreState()

    return _dibujar_pagina


# ── Elementos de encabezado (flujo de texto: subtítulo + meta) ────────

def _encabezado(titulo: str, subtitulo: str = "", usuario_nombre: str = "") -> list:
    """Retorna los elementos de subtítulo, fecha y usuario como flowables.
    El logo y el título principal se dibujan en canvas en cada página.
    """
    estilos = getSampleStyleSheet()
    elementos = []

    if subtitulo:
        estilo_sub = ParagraphStyle(
            "SubtituloReporte",
            parent=estilos["Normal"],
            fontSize=10,
            leading=14,
            textColor=GRAY,
            spaceAfter=6,
        )
        elementos.append(Paragraph(subtitulo, estilo_sub))

    estilo_meta = ParagraphStyle(
        "MetaReporte",
        parent=estilos["Normal"],
        fontSize=9,
        leading=14,
        textColor=GRAY,
        spaceAfter=3,
    )
    fecha = datetime.now(GMT_MINUS_4).strftime("%d/%m/%Y %H:%M GMT-4")
    elementos.append(Paragraph(f"Generado: {fecha}", estilo_meta))
    if usuario_nombre:
        elementos.append(Paragraph(f"Generado por: {usuario_nombre}", estilo_meta))
    elementos.append(Spacer(1, 0.25 * inch))

    return elementos


# ── Helpers de tablas y secciones ────────────────────────────────────

def _tabla(headers: list[str], rows: list[list], col_widths=None) -> Table:
    """Crea una tabla con estilo institucional."""
    data = [headers] + rows
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
        ("TOPPADDING", (0, 1), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        *[
            ("BACKGROUND", (0, i), (-1, i), GRAY_LIGHT)
            for i in range(2, len(data), 2)
        ],
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return table


def _seccion_titulo(texto: str) -> Paragraph:
    """Título de sección dentro del reporte."""
    estilo = ParagraphStyle(
        "SeccionTitulo",
        fontSize=12,
        textColor=NAVY,
        fontName="Helvetica-Bold",
        spaceBefore=6,
        spaceAfter=10,
    )
    return Paragraph(texto, estilo)


def _nuevo_doc(buf: BytesIO) -> SimpleDocTemplate:
    """Crea un SimpleDocTemplate con los márgenes institucionales."""
    return SimpleDocTemplate(
        buf,
        pagesize=letter,
        topMargin=_TOP_MARGIN,
        bottomMargin=_BOTTOM_MARGIN,
        leftMargin=_LEFT_MARGIN,
        rightMargin=_RIGHT_MARGIN,
    )


# ═════════════════════════════════════════════════════════════════════
# Generadores de cada tipo de reporte
# ═════════════════════════════════════════════════════════════════════

def generar_predictivo_general(
    resumen: dict,
    dist_riesgo: list,
    dist_paralelo: list,
    usuario_nombre: str = "",
) -> bytes:
    """Reporte predictivo general: resumen + distribución riesgo + distribución paralelo."""
    titulo = "Reporte Predictivo General"
    buf = BytesIO()
    doc = _nuevo_doc(buf)
    page_cb = _make_page_callback(titulo, usuario_nombre)
    elementos = _encabezado(titulo, "Resumen ejecutivo de predicciones de abandono", usuario_nombre)

    resumen_rows = [
        ["Total Estudiantes", str(resumen.get("total_estudiantes", 0))],
        ["Predicciones Activas", str(resumen.get("total_predicciones_activas", 0))],
        ["Alto Riesgo", str(resumen.get("total_alto_riesgo", 0))],
        ["Critico", str(resumen.get("total_critico", 0))],
        ["Medio Riesgo", str(resumen.get("total_medio_riesgo", 0))],
        ["Bajo Riesgo", str(resumen.get("total_bajo_riesgo", 0))],
        ["% Alto Riesgo", f"{resumen.get('porcentaje_alto_riesgo', 0)}%"],
        ["Alertas Activas", str(resumen.get("total_alertas_activas", 0))],
        ["Alertas Criticas", str(resumen.get("total_alertas_criticas", 0))],
    ]
    elementos.append(KeepTogether([
        _seccion_titulo("Resumen General"),
        _tabla(["Indicador", "Valor"], resumen_rows, col_widths=[3.5 * inch, 2.5 * inch]),
    ]))
    elementos.append(Spacer(1, 0.25 * inch))

    riesgo_rows = [
        [d.get("nivel", ""), str(d.get("cantidad", 0)), f"{d.get('porcentaje', 0)}%"]
        for d in dist_riesgo
    ]
    elementos.append(KeepTogether([
        _seccion_titulo("Distribución por Nivel de Riesgo"),
        _tabla(["Nivel", "Cantidad", "Porcentaje"], riesgo_rows),
    ]))
    elementos.append(Spacer(1, 0.25 * inch))

    if dist_paralelo:
        paralelo_rows = [
            [d.get("paralelo", ""), d.get("area", ""), str(d.get("total", 0)),
             str(d.get("alto_riesgo", 0)), str(d.get("critico", 0))]
            for d in dist_paralelo
        ]
        elementos.append(KeepTogether([
            _seccion_titulo("Distribución por Paralelo"),
            _tabla(["Paralelo", "Area", "Total", "Alto Riesgo", "Critico"], paralelo_rows),
        ]))

    doc.build(elementos, onFirstPage=page_cb, onLaterPages=page_cb)
    return buf.getvalue()


def generar_estudiantes_riesgo(
    estudiantes: list[dict],
    usuario_nombre: str = "",
) -> bytes:
    """Reporte de estudiantes con riesgo Alto o Critico."""
    titulo = "Estudiantes en Riesgo"
    buf = BytesIO()
    doc = _nuevo_doc(buf)
    page_cb = _make_page_callback(titulo, usuario_nombre)
    elementos = _encabezado(
        titulo,
        f"Listado de estudiantes con nivel Alto o Critico — {len(estudiantes)} estudiante(s)",
        usuario_nombre,
    )

    if not estudiantes:
        elementos.append(Paragraph("No se encontraron estudiantes en riesgo alto o critico.", getSampleStyleSheet()["Normal"]))
    else:
        rows = [
            [
                e.get("codigo_estudiante", ""),
                e.get("nombre_estudiante", ""),
                e.get("paralelo", ""),
                f"{e.get('probabilidad_abandono', 0):.1%}",
                e.get("nivel_riesgo", ""),
                str(e.get("fecha_prediccion", "")),
            ]
            for e in estudiantes
        ]
        elementos.append(_tabla(
            ["Codigo", "Nombre", "Paralelo", "Probabilidad", "Nivel", "Fecha"], rows,
        ))

    doc.build(elementos, onFirstPage=page_cb, onLaterPages=page_cb)
    return buf.getvalue()


def generar_por_paralelo(
    paralelo_info: dict,
    estudiantes: list[dict],
    usuario_nombre: str = "",
) -> bytes:
    """Reporte desglosado por paralelo."""
    nombre_par = paralelo_info.get("nombre", "")
    area = paralelo_info.get("area", "")
    titulo = f"Reporte por Paralelo: {nombre_par}"

    buf = BytesIO()
    doc = _nuevo_doc(buf)
    page_cb = _make_page_callback(titulo, usuario_nombre)
    elementos = _encabezado(titulo, f"Area: {area} — {len(estudiantes)} estudiante(s)", usuario_nombre)

    if not estudiantes:
        elementos.append(Paragraph("No se encontraron estudiantes en este paralelo.", getSampleStyleSheet()["Normal"]))
    else:
        rows = [
            [
                e.get("codigo_estudiante", ""),
                e.get("nombre_completo", ""),
                f"{e.get('porcentaje_asistencia', 0):.1f}%",
                f"{e.get('probabilidad', 0):.1%}" if e.get("probabilidad") is not None else "Sin prediccion",
                e.get("nivel_riesgo", "Sin prediccion"),
            ]
            for e in estudiantes
        ]
        elementos.append(_tabla(
            ["Codigo", "Nombre", "Asistencia", "Prob. Abandono", "Nivel Riesgo"], rows,
        ))

    doc.build(elementos, onFirstPage=page_cb, onLaterPages=page_cb)
    return buf.getvalue()


def generar_asistencia(
    resumen_materias: list[dict],
    paralelo_nombre: str | None = None,
    usuario_nombre: str = "",
) -> bytes:
    """Reporte de asistencia por materia."""
    titulo = "Reporte de Asistencia"
    subtitulo = f"Paralelo: {paralelo_nombre}" if paralelo_nombre else "Todos los paralelos"

    buf = BytesIO()
    doc = _nuevo_doc(buf)
    page_cb = _make_page_callback(titulo, usuario_nombre)
    elementos = _encabezado(titulo, subtitulo, usuario_nombre)

    if not resumen_materias:
        elementos.append(Paragraph("No se encontraron registros de asistencia.", getSampleStyleSheet()["Normal"]))
    else:
        rows = [
            [
                m.get("materia", ""),
                str(m.get("total_clases", 0)),
                str(m.get("presentes", 0)),
                str(m.get("ausentes", 0)),
                f"{m.get('porcentaje_asistencia', 0):.1f}%",
            ]
            for m in resumen_materias
        ]
        elementos.append(_tabla(
            ["Materia", "Total Clases", "Presentes", "Ausentes", "% Asistencia"], rows,
        ))

    doc.build(elementos, onFirstPage=page_cb, onLaterPages=page_cb)
    return buf.getvalue()


def generar_individual(
    estudiante: dict,
    predicciones: list[dict],
    alertas: list[dict],
    acciones: list[dict],
    usuario_nombre: str = "",
) -> bytes:
    """Reporte individual de un estudiante."""
    nombre = estudiante.get("nombre_completo", "")
    codigo = estudiante.get("codigo_estudiante", "")
    titulo = f"Reporte Individual: {nombre}"

    buf = BytesIO()
    doc = _nuevo_doc(buf)
    page_cb = _make_page_callback(titulo, usuario_nombre)
    elementos = _encabezado(titulo, f"Codigo: {codigo}", usuario_nombre)

    # Datos personales
    datos_rows = []
    for campo, label in [
        ("codigo_estudiante", "Codigo"),
        ("nombre_completo", "Nombre"),
        ("paralelo", "Paralelo"),
        ("genero", "Genero"),
        ("edad", "Edad"),
        ("grado", "Grado"),
        ("estrato_socioeconomico", "Estrato Socioeconomico"),
        ("ocupacion_laboral", "Trabaja"),
        ("con_quien_vive", "Con quien vive"),
        ("apoyo_economico", "Apoyo Economico"),
        ("modalidad_ingreso", "Modalidad de Ingreso"),
        ("tipo_colegio", "Tipo de Colegio"),
        ("porcentaje_asistencia", "% Asistencia"),
    ]:
        val = estudiante.get(campo)
        if val is not None:
            if campo == "porcentaje_asistencia":
                val = f"{val:.1f}%"
            datos_rows.append([label, str(val)])
    if datos_rows:
        elementos.append(KeepTogether([
            _seccion_titulo("Datos del Estudiante"),
            _tabla(["Campo", "Valor"], datos_rows, col_widths=[3 * inch, 4 * inch]),
        ]))
    elementos.append(Spacer(1, 0.2 * inch))

    # Historial de predicciones
    styles = getSampleStyleSheet()
    if predicciones:
        pred_rows = [
            [
                str(p.get("fecha_prediccion", "")),
                f"{p.get('probabilidad_abandono', 0):.1%}",
                p.get("nivel_riesgo", ""),
                p.get("tipo", ""),
            ]
            for p in predicciones
        ]
        elementos.append(KeepTogether([
            _seccion_titulo("Historial de Predicciones"),
            _tabla(["Fecha", "Probabilidad", "Nivel", "Tipo"], pred_rows),
        ]))
    else:
        elementos.append(_seccion_titulo("Historial de Predicciones"))
        elementos.append(Paragraph("Sin predicciones registradas.", styles["Normal"]))
    elementos.append(Spacer(1, 0.2 * inch))

    # Alertas
    if alertas:
        alerta_rows = [
            [a.get("tipo", ""), a.get("nivel", ""), a.get("titulo", ""),
             a.get("estado", ""), str(a.get("fecha_creacion", ""))]
            for a in alertas
        ]
        elementos.append(KeepTogether([
            _seccion_titulo("Alertas"),
            _tabla(["Tipo", "Nivel", "Titulo", "Estado", "Fecha"], alerta_rows),
        ]))
    else:
        elementos.append(_seccion_titulo("Alertas"))
        elementos.append(Paragraph("Sin alertas registradas.", styles["Normal"]))
    elementos.append(Spacer(1, 0.2 * inch))

    # Acciones
    if acciones:
        accion_rows = [
            [str(a.get("fecha", "")), a.get("descripcion", "")]
            for a in acciones
        ]
        elementos.append(KeepTogether([
            _seccion_titulo("Acciones Tomadas"),
            _tabla(["Fecha", "Descripcion"], accion_rows),
        ]))

    doc.build(elementos, onFirstPage=page_cb, onLaterPages=page_cb)
    return buf.getvalue()
