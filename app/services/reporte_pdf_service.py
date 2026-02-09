"""Servicio de generación de reportes PDF con reportlab."""
from datetime import datetime, timezone
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Colores institucionales
NAVY = colors.HexColor("#1B2A4A")
NAVY_LIGHT = colors.HexColor("#2C3E50")
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


def _encabezado(titulo: str, subtitulo: str = "") -> list:
    """Genera los elementos del encabezado institucional."""
    styles = getSampleStyleSheet()
    elementos = []

    estilo_inst = ParagraphStyle(
        "Institucional",
        parent=styles["Normal"],
        fontSize=10,
        textColor=GRAY,
        spaceAfter=4,
    )
    estilo_titulo = ParagraphStyle(
        "TituloReporte",
        parent=styles["Title"],
        fontSize=18,
        textColor=NAVY,
        spaceAfter=4,
    )
    estilo_sub = ParagraphStyle(
        "SubtituloReporte",
        parent=styles["Normal"],
        fontSize=10,
        textColor=GRAY,
        spaceAfter=8,
    )
    estilo_fecha = ParagraphStyle(
        "FechaReporte",
        parent=styles["Normal"],
        fontSize=9,
        textColor=GRAY,
    )

    elementos.append(Paragraph("SISTEMA PREDICTIVO DE ABANDONO ESTUDIANTIL — EMI", estilo_inst))
    elementos.append(Paragraph(titulo, estilo_titulo))
    if subtitulo:
        elementos.append(Paragraph(subtitulo, estilo_sub))
    fecha = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    elementos.append(Paragraph(f"Generado: {fecha}", estilo_fecha))
    elementos.append(Spacer(1, 0.3 * inch))

    return elementos


def _tabla(headers: list[str], rows: list[list], col_widths=None) -> Table:
    """Crea una tabla con estilo institucional."""
    data = [headers] + rows
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        # Encabezado
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        # Filas
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
        ("TOPPADDING", (0, 1), (-1, -1), 6),
        # Bordes
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        # Filas alternas
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
        fontSize=13,
        textColor=NAVY,
        fontName="Helvetica-Bold",
        spaceBefore=12,
        spaceAfter=8,
    )
    return Paragraph(texto, estilo)


# =====================================================================
# Generadores de cada tipo de reporte
# =====================================================================

def generar_predictivo_general(resumen: dict, dist_riesgo: list, dist_paralelo: list) -> bytes:
    """Reporte predictivo general: resumen + distribución riesgo + distribución paralelo."""
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    elementos = _encabezado("Reporte Predictivo General", "Resumen ejecutivo de predicciones de abandono")

    # Tabla resumen
    elementos.append(_seccion_titulo("Resumen General"))
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
    elementos.append(_tabla(["Indicador", "Valor"], resumen_rows, col_widths=[3.5 * inch, 2.5 * inch]))
    elementos.append(Spacer(1, 0.3 * inch))

    # Distribución de riesgo
    elementos.append(_seccion_titulo("Distribución por Nivel de Riesgo"))
    riesgo_rows = [
        [d.get("nivel", ""), str(d.get("cantidad", 0)), f"{d.get('porcentaje', 0)}%"]
        for d in dist_riesgo
    ]
    elementos.append(_tabla(["Nivel", "Cantidad", "Porcentaje"], riesgo_rows))
    elementos.append(Spacer(1, 0.3 * inch))

    # Distribución por paralelo
    if dist_paralelo:
        elementos.append(_seccion_titulo("Distribución por Paralelo"))
        paralelo_rows = [
            [d.get("paralelo", ""), d.get("area", ""), str(d.get("total", 0)),
             str(d.get("alto_riesgo", 0)), str(d.get("critico", 0))]
            for d in dist_paralelo
        ]
        elementos.append(_tabla(
            ["Paralelo", "Area", "Total", "Alto Riesgo", "Critico"],
            paralelo_rows,
        ))

    doc.build(elementos)
    return buf.getvalue()


def generar_estudiantes_riesgo(estudiantes: list[dict]) -> bytes:
    """Reporte de estudiantes con riesgo Alto o Critico."""
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    elementos = _encabezado(
        "Estudiantes en Riesgo",
        f"Listado de estudiantes con nivel Alto o Critico — {len(estudiantes)} estudiante(s)",
    )

    if not estudiantes:
        styles = getSampleStyleSheet()
        elementos.append(Paragraph("No se encontraron estudiantes en riesgo alto o critico.", styles["Normal"]))
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
            ["Codigo", "Nombre", "Paralelo", "Probabilidad", "Nivel", "Fecha"],
            rows,
        ))

    doc.build(elementos)
    return buf.getvalue()


def generar_por_paralelo(paralelo_info: dict, estudiantes: list[dict]) -> bytes:
    """Reporte desglosado por paralelo."""
    nombre_par = paralelo_info.get("nombre", "")
    area = paralelo_info.get("area", "")

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    elementos = _encabezado(
        f"Reporte por Paralelo: {nombre_par}",
        f"Area: {area} — {len(estudiantes)} estudiante(s)",
    )

    if not estudiantes:
        styles = getSampleStyleSheet()
        elementos.append(Paragraph("No se encontraron estudiantes en este paralelo.", styles["Normal"]))
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
            ["Codigo", "Nombre", "Asistencia", "Prob. Abandono", "Nivel Riesgo"],
            rows,
        ))

    doc.build(elementos)
    return buf.getvalue()


def generar_asistencia(resumen_materias: list[dict], paralelo_nombre: str | None = None) -> bytes:
    """Reporte de asistencia por materia."""
    subtitulo = f"Paralelo: {paralelo_nombre}" if paralelo_nombre else "Todos los paralelos"

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    elementos = _encabezado("Reporte de Asistencia", subtitulo)

    if not resumen_materias:
        styles = getSampleStyleSheet()
        elementos.append(Paragraph("No se encontraron registros de asistencia.", styles["Normal"]))
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
            ["Materia", "Total Clases", "Presentes", "Ausentes", "% Asistencia"],
            rows,
        ))

    doc.build(elementos)
    return buf.getvalue()


def generar_individual(
    estudiante: dict,
    predicciones: list[dict],
    alertas: list[dict],
    acciones: list[dict],
) -> bytes:
    """Reporte individual de un estudiante."""
    nombre = estudiante.get("nombre_completo", "")
    codigo = estudiante.get("codigo_estudiante", "")

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    elementos = _encabezado(f"Reporte Individual: {nombre}", f"Codigo: {codigo}")

    # Datos personales
    elementos.append(_seccion_titulo("Datos del Estudiante"))
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
        elementos.append(_tabla(["Campo", "Valor"], datos_rows, col_widths=[3 * inch, 3.5 * inch]))
    elementos.append(Spacer(1, 0.2 * inch))

    # Historial de predicciones
    elementos.append(_seccion_titulo("Historial de Predicciones"))
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
        elementos.append(_tabla(["Fecha", "Probabilidad", "Nivel", "Tipo"], pred_rows))
    else:
        styles = getSampleStyleSheet()
        elementos.append(Paragraph("Sin predicciones registradas.", styles["Normal"]))
    elementos.append(Spacer(1, 0.2 * inch))

    # Alertas
    elementos.append(_seccion_titulo("Alertas"))
    if alertas:
        alerta_rows = [
            [a.get("tipo", ""), a.get("nivel", ""), a.get("titulo", ""),
             a.get("estado", ""), str(a.get("fecha_creacion", ""))]
            for a in alertas
        ]
        elementos.append(_tabla(["Tipo", "Nivel", "Titulo", "Estado", "Fecha"], alerta_rows))
    else:
        styles = getSampleStyleSheet()
        elementos.append(Paragraph("Sin alertas registradas.", styles["Normal"]))
    elementos.append(Spacer(1, 0.2 * inch))

    # Acciones
    if acciones:
        elementos.append(_seccion_titulo("Acciones Tomadas"))
        accion_rows = [
            [str(a.get("fecha", "")), a.get("descripcion", "")]
            for a in acciones
        ]
        elementos.append(_tabla(["Fecha", "Descripcion"], accion_rows))

    doc.build(elementos)
    return buf.getvalue()
