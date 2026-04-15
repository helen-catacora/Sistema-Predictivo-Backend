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
    ListFlowable,
    ListItem,
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
DARK_TEXT = colors.HexColor("#374151")

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
_BOTTOM_MARGIN = 0.65 * inch
_TOP_MARGIN = 1.75 * inch


# ── Helpers de logo ───────────────────────────────────────────────────

def _get_logo_path() -> "Path | None":
    for nombre in ["logo-emi.png", "logoEmi.png", "logo-emi.jpg", "logoEmi.jpg"]:
        ruta = _ASSETS_DIR / nombre
        if ruta.exists():
            return ruta
    return None


def _get_logo() -> "Image | None":
    path = _get_logo_path()
    if path:
        return Image(str(path), width=0.75 * inch, height=0.65 * inch)
    return None


# ── Canvas: header + footer + marca de agua en cada página ───────────

def _make_page_callback(titulo_reporte: str, usuario_nombre: str = ""):
    _fecha_gen = datetime.now(GMT_MINUS_4).strftime("%d/%m/%Y %H:%M")

    def _dibujar_pagina(canvas, doc):
        canvas.saveState()

        page_width, page_height = letter
        left_x = _LEFT_MARGIN
        right_x = page_width - _RIGHT_MARGIN

        # ── Marca de agua ─────────────────────────────────────────
        wm_path = _ASSETS_DIR / "emi.png"
        if wm_path.exists():
            wm_size = 4.5 * inch
            wm_x = (page_width - wm_size) / 2
            wm_y = (page_height - wm_size) / 2
            canvas.drawImage(
                str(wm_path), wm_x, wm_y, wm_size, wm_size,
                mask="auto", preserveAspectRatio=True,
            )
            canvas.setFillColorRGB(1, 1, 1)
            canvas.setFillAlpha(0.88)
            canvas.rect(wm_x, wm_y, wm_size, wm_size, fill=1, stroke=0)
            canvas.setFillAlpha(1.0)

        # ── Logo ──────────────────────────────────────────────────
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

        # ── Texto institucional ───────────────────────────────────
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

        # ── Línea separadora header ──────────────────────────────
        sep_y = logo_y - 5
        canvas.setStrokeColor(NAVY)
        canvas.setLineWidth(1.5)
        canvas.line(left_x, sep_y, right_x, sep_y)

        # ── Título del reporte ────────────────────────────────────
        canvas.setFont("Helvetica-Bold", 15)
        canvas.setFillColor(NAVY)
        canvas.drawCentredString(page_width / 2, sep_y - 22, titulo_reporte.upper())

        # ── Footer ────────────────────────────────────────────────
        footer_y = _BOTTOM_MARGIN - 5
        canvas.setStrokeColor(colors.HexColor("#D1D5DB"))
        canvas.setLineWidth(0.5)
        canvas.line(left_x, footer_y + 12, right_x, footer_y + 12)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(GRAY)
        canvas.drawString(left_x, footer_y, f"Generado el: {_fecha_gen}")
        canvas.drawRightString(right_x, footer_y, f"Página {doc.page}")

        canvas.restoreState()

    return _dibujar_pagina


# ── Elementos de encabezado ──────────────────────────────────────────

def _encabezado(titulo: str, subtitulo: str = "", usuario_nombre: str = "") -> list:
    estilos = getSampleStyleSheet()
    elementos = []

    if subtitulo:
        estilo_sub = ParagraphStyle(
            "SubtituloReporte",
            parent=estilos["Normal"],
            fontSize=10,
            leading=14,
            textColor=GRAY,
            spaceAfter=4,
        )
        elementos.append(Paragraph(subtitulo, estilo_sub))

    if usuario_nombre:
        estilo_meta = ParagraphStyle(
            "MetaReporte",
            parent=estilos["Normal"],
            fontSize=9,
            leading=14,
            textColor=GRAY,
            spaceAfter=2,
        )
        elementos.append(Paragraph(f"Generado por: {usuario_nombre}", estilo_meta))
    elementos.append(Spacer(1, 0.2 * inch))

    return elementos


# ── Estilos reutilizables ────────────────────────────────────────────

# [Cambio 2] Título de sección numerada: leading alto + spaceAfter generoso
_ESTILO_SECCION_NUMERADA = ParagraphStyle(
    "SeccionNumerada",
    fontSize=14,
    leading=20,
    textColor=NAVY,
    fontName="Helvetica-Bold",
    spaceBefore=18,
    spaceAfter=14,
)

# [Cambio 4] Subtítulo intermedio entre título principal y texto normal
_ESTILO_SUBTITULO = ParagraphStyle(
    "SubtituloSeccion",
    fontSize=11,
    leading=16,
    textColor=NAVY,
    fontName="Helvetica-Bold",
    spaceBefore=10,
    spaceAfter=8,
)

# [Cambio 1] Descripción introductoria: reducido spaceBefore/spaceAfter
_ESTILO_DESCRIPCION = ParagraphStyle(
    "SeccionDescripcion",
    fontSize=9,
    leading=13,
    textColor=GRAY,
    spaceBefore=0,
    spaceAfter=6,
)

# Texto interpretativo (items de la lista)
_ESTILO_INTERPRETACION = ParagraphStyle(
    "Interpretacion",
    fontName="Helvetica",
    fontSize=9,
    leading=14,
    textColor=DARK_TEXT,
    spaceAfter=2,
)


# ── Helpers de tablas y secciones ────────────────────────────────────

def _tabla(headers: list[str], rows: list[list], col_widths=None) -> Table:
    """Crea una tabla con estilo institucional. [Cambio 5] padding 10pt."""
    data = [headers] + rows
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("TOPPADDING", (0, 0), (-1, 0), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
        ("LEFTPADDING", (0, 0), (-1, 0), 10),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("TOPPADDING", (0, 1), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 8),
        ("LEFTPADDING", (0, 1), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        *[
            ("BACKGROUND", (0, i), (-1, i), GRAY_LIGHT)
            for i in range(2, len(data), 2)
        ],
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return table


def _tabla_metadata(rows: list[list]) -> Table:
    """Tabla de metadatos estilo ficha. [Cambio 5] padding 10pt."""
    table = Table(rows, colWidths=[2.5 * inch, 4 * inch])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (-1, -1), DARK_TEXT),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
    ]))
    return table


def _seccion_numerada(numero: str, titulo: str, descripcion: str = "") -> list:
    """Sección numerada con título grande y descripción breve (1 oración)."""
    elementos = []
    elementos.append(Paragraph(f"{numero}. {titulo.upper()}", _ESTILO_SECCION_NUMERADA))
    if descripcion:
        elementos.append(Paragraph(descripcion, _ESTILO_DESCRIPCION))
    return elementos


def _subtitulo(texto: str) -> Paragraph:
    """[Cambio 4] Subtítulo intermedio entre título de sección y contenido."""
    return Paragraph(texto, _ESTILO_SUBTITULO)


def _lista_hallazgos(parrafos: list[str]) -> list:
    """[Cambio 3] Convierte los párrafos de interpretación en ListFlowable con viñetas."""
    if not parrafos:
        return []
    items = [
        ListItem(
            Paragraph(p, _ESTILO_INTERPRETACION),
            bulletColor=NAVY,
            bulletFontSize=7,
        )
        for p in parrafos
    ]
    lista = ListFlowable(
        items,
        bulletType="bullet",
        bulletFontSize=7,
        bulletOffsetY=-1,
        leftIndent=14,
        bulletDedent=10,
        spaceBefore=4,
        spaceAfter=8,
    )
    return [lista]


def _nuevo_doc(buf: BytesIO) -> SimpleDocTemplate:
    return SimpleDocTemplate(
        buf,
        pagesize=letter,
        topMargin=_TOP_MARGIN,
        bottomMargin=_BOTTOM_MARGIN,
        leftMargin=_LEFT_MARGIN,
        rightMargin=_RIGHT_MARGIN,
    )


# ═════════════════════════════════════════════════════════════════════
# Funciones de interpretación analítica
# ═════════════════════════════════════════════════════════════════════

def _interpretar_predictivo_general(resumen: dict, dist_riesgo: list, dist_paralelo: list) -> list[str]:
    parrafos = []
    total_pred = resumen.get("total_predicciones_activas", 0)
    alto = resumen.get("total_alto_riesgo", 0)
    critico = resumen.get("total_critico", 0)
    pct = resumen.get("porcentaje_alto_riesgo", 0)
    alertas_crit = resumen.get("total_alertas_criticas", 0)
    total_est = resumen.get("total_estudiantes", 0)

    if total_pred == 0:
        parrafos.append("No se registran predicciones activas en el sistema.")
        return parrafos

    en_riesgo = alto + critico
    parrafos.append(
        f"Del total de {total_pred} estudiantes con predicción activa, "
        f"{en_riesgo} ({pct}%) se encuentran en nivel de riesgo Alto o Crítico. "
        f"De estos, {critico} están en nivel Crítico (probabilidad ≥70%) y "
        f"{alto} en nivel Alto (probabilidad entre 50% y 70%)."
    )

    if total_est > 0 and total_pred < total_est:
        sin_pred = total_est - total_pred
        parrafos.append(
            f"Existen {sin_pred} estudiantes sin predicción de riesgo "
            f"(cobertura: {round(total_pred / total_est * 100, 1)}%)."
        )

    alertas_activas = resumen.get("total_alertas_activas", 0)
    if alertas_activas > 0:
        txt = f"Se registran {alertas_activas} alertas activas en el sistema"
        if alertas_crit > 0:
            txt += f", de las cuales {alertas_crit} son de tipo crítico"
        txt += "."
        parrafos.append(txt)

    if dist_paralelo:
        max_par = max(dist_paralelo, key=lambda d: d.get("alto_riesgo", 0) + d.get("critico", 0))
        max_riesgo = max_par.get("alto_riesgo", 0) + max_par.get("critico", 0)
        if max_riesgo > 0:
            parrafos.append(
                f"El paralelo con mayor concentración de riesgo es '{max_par.get('paralelo', '')}' "
                f"({max_par.get('area', '')}), con {max_riesgo} estudiante(s) en nivel Alto o Crítico."
            )
        sin_riesgo = [d for d in dist_paralelo if d.get("alto_riesgo", 0) + d.get("critico", 0) == 0]
        if sin_riesgo:
            nombres = ", ".join(d.get("paralelo", "") for d in sin_riesgo)
            parrafos.append(
                f"Paralelos sin estudiantes en riesgo Alto o Crítico: {nombres}."
            )

    return parrafos


def _interpretar_estudiantes_riesgo(estudiantes: list[dict], total_con_prediccion: int) -> list[str]:
    parrafos = []
    total = len(estudiantes)

    if total == 0:
        parrafos.append("No se identificaron estudiantes en nivel de riesgo Alto o Crítico.")
        return parrafos

    if total_con_prediccion > 0:
        pct = round(total / total_con_prediccion * 100, 1)
        parrafos.append(
            f"Se identificaron {total} estudiantes en riesgo ({pct}% del total con predicción)."
        )

    criticos = [e for e in estudiantes if e.get("nivel_riesgo") == "Critico"]
    altos = [e for e in estudiantes if e.get("nivel_riesgo") == "Alto"]
    if criticos or altos:
        parrafos.append(
            f"{len(criticos)} en nivel Crítico (probabilidad ≥70%) y "
            f"{len(altos)} en nivel Alto (probabilidad entre 50% y 70%)."
        )

    probs = [e.get("probabilidad_abandono", 0) for e in estudiantes if e.get("probabilidad_abandono") is not None]
    if probs:
        parrafos.append(
            f"Probabilidades de abandono entre {min(probs):.1%} y {max(probs):.1%}."
        )

    paralelos: dict[str, int] = {}
    for e in estudiantes:
        par = e.get("paralelo", "Sin paralelo")
        paralelos[par] = paralelos.get(par, 0) + 1
    if len(paralelos) > 1:
        dist = ", ".join(f"{nombre}: {cant}" for nombre, cant in sorted(paralelos.items(), key=lambda x: -x[1]))
        parrafos.append(f"Distribución por paralelo: {dist}.")

    return parrafos


def _interpretar_por_paralelo(estudiantes: list[dict]) -> list[str]:
    parrafos = []
    total = len(estudiantes)

    if total == 0:
        parrafos.append("No se encontraron estudiantes registrados en este paralelo.")
        return parrafos

    con_pred = [e for e in estudiantes if e.get("nivel_riesgo") not in (None, "Sin prediccion")]
    sin_pred = total - len(con_pred)
    altos = [e for e in con_pred if e.get("nivel_riesgo") in ("Alto", "Critico")]

    txt = f"De los {total} estudiantes, {len(con_pred)} cuentan con predicción"
    if sin_pred > 0:
        txt += f" y {sin_pred} aún no tienen predicción"
    txt += "."
    if altos:
        criticos = [e for e in altos if e.get("nivel_riesgo") == "Critico"]
        altos_only = [e for e in altos if e.get("nivel_riesgo") == "Alto"]
        txt += f" {len(altos_only)} en nivel Alto y {len(criticos)} en nivel Crítico."
    parrafos.append(txt)

    asistencias = [e.get("porcentaje_asistencia", 0) for e in estudiantes]
    if asistencias:
        promedio = sum(asistencias) / len(asistencias)
        parrafos.append(f"Asistencia promedio del paralelo: {promedio:.1f}%.")

        baja_asist = [e for e in estudiantes if e.get("porcentaje_asistencia", 0) < 60]
        if baja_asist:
            parrafos.append(
                f"{len(baja_asist)} estudiante(s) con asistencia inferior al 60%."
            )
            baja_y_riesgo = [e for e in baja_asist if e.get("nivel_riesgo") in ("Alto", "Critico")]
            if baja_y_riesgo:
                parrafos.append(
                    f"De estos, {len(baja_y_riesgo)} también en nivel de riesgo Alto o Crítico."
                )

    return parrafos


def _resumen_texto_asistencia(grupos: list[dict]) -> list:
    """Genera párrafos de texto resumiendo asistencia por semestre → paralelo.
    Para cada paralelo indica el promedio y las materias con asistencia inferior al 70%."""
    if not grupos:
        return [Paragraph("No se encontraron registros de asistencia.", _ESTILO_INTERPRETACION)]

    elementos = []
    semestres_vistos: dict[str, list[dict]] = {}
    for g in grupos:
        sem = g.get("semestre", "Sin Semestre")
        semestres_vistos.setdefault(sem, []).append(g)

    for semestre, paralelos in semestres_vistos.items():
        elementos.append(_subtitulo(semestre))
        textos = []
        for g in paralelos:
            paralelo = g.get("paralelo", "")
            materias = g.get("materias", [])
            pcts = [m.get("porcentaje_asistencia", 0) for m in materias]
            promedio = sum(pcts) / len(pcts) if pcts else 0.0
            bajas = sorted(
                [m for m in materias if m.get("porcentaje_asistencia", 0) < 70],
                key=lambda m: m.get("porcentaje_asistencia", 0),
            )
            if bajas:
                lista_bajas = ", ".join(
                    f"{m['materia']} ({m['porcentaje_asistencia']:.1f}%)" for m in bajas
                )
                texto = (
                    f"<b>Paralelo {paralelo}</b>: asistencia promedio del {promedio:.1f}%. "
                    f"Materias con baja asistencia: {lista_bajas}."
                )
            else:
                texto = (
                    f"<b>Paralelo {paralelo}</b>: asistencia promedio del {promedio:.1f}%. "
                    f"Sin materias con asistencia inferior al 70%."
                )
            textos.append(texto)
        elementos.extend(_lista_hallazgos(textos))

    return elementos


def _interpretar_individual(
    estudiante: dict,
    predicciones: list[dict],
    alertas: list[dict],
    acciones: list[dict],
    shap_factores: list[dict] | None = None,
) -> list[str]:
    parrafos = []
    nombre = estudiante.get("nombre_completo", "El estudiante")

    if not predicciones:
        parrafos.append(f"{nombre} no cuenta con predicciones de riesgo registradas.")
        return parrafos

    ultima = predicciones[0]
    prob = ultima.get("probabilidad_abandono", 0)
    nivel = ultima.get("nivel_riesgo", "")
    parrafos.append(
        f"Nivel de riesgo actual: {nivel} con probabilidad de abandono del {prob:.1%}."
    )

    if len(predicciones) >= 2:
        primera_prob = predicciones[-1].get("probabilidad_abandono", 0)
        ultima_prob = predicciones[0].get("probabilidad_abandono", 0)
        diff = ultima_prob - primera_prob
        n = len(predicciones)
        if diff > 0.05:
            parrafos.append(
                f"Tendencia creciente en {n} predicciones: de {primera_prob:.1%} a {ultima_prob:.1%}."
            )
        elif diff < -0.05:
            parrafos.append(
                f"Tendencia decreciente en {n} predicciones: de {primera_prob:.1%} a {ultima_prob:.1%}."
            )
        else:
            parrafos.append(
                f"Probabilidad estable en {n} predicciones (entre {min(primera_prob, ultima_prob):.1%} y {max(primera_prob, ultima_prob):.1%})."
            )

    features = ultima.get("features_utilizadas") or {}
    if features:
        _LABELS = {
            "Mat": "Materias cursadas", "Rep": "Materias reprobadas",
            "2T": "Materias en 2do turno", "Prom": "Promedio",
            "edad": "Edad",
        }
        partes = []
        for key, label in _LABELS.items():
            val = features.get(key)
            if val is not None:
                partes.append(f"{label}: {val}")
        if partes:
            parrafos.append(f"Variables académicas: {', '.join(partes)}.")

    pct_asist = estudiante.get("porcentaje_asistencia")
    if pct_asist is not None and pct_asist > 0:
        if pct_asist < 60:
            parrafos.append(f"Asistencia general: {pct_asist:.1f}% (nivel bajo).")
        elif pct_asist < 80:
            parrafos.append(f"Asistencia general: {pct_asist:.1f}%.")

    if alertas:
        activas = sum(1 for a in alertas if a.get("estado") == "activa")
        en_seg = sum(1 for a in alertas if a.get("estado") == "en_seguimiento")
        resueltas = sum(1 for a in alertas if a.get("estado") == "resuelta")
        partes_alerta = []
        if activas:
            partes_alerta.append(f"{activas} activa(s)")
        if en_seg:
            partes_alerta.append(f"{en_seg} en seguimiento")
        if resueltas:
            partes_alerta.append(f"{resueltas} resuelta(s)")
        parrafos.append(f"{len(alertas)} alerta(s): {', '.join(partes_alerta)}.")

    if acciones:
        ultima_accion = acciones[0].get("fecha", "")
        parrafos.append(
            f"{len(acciones)} acción(es) de seguimiento registrada(s)"
            f"{f', última el {ultima_accion}' if ultima_accion else ''}."
        )
    else:
        parrafos.append("Sin acciones de seguimiento registradas.")

    # Interpretación SHAP
    if shap_factores:
        top_riesgo = [f["nombre"] for f in shap_factores if f["tipo"] == "riesgo"][:2]
        top_prot = [f["nombre"] for f in shap_factores if f["tipo"] == "protector"][:2]
        if top_riesgo:
            parrafos.append(
                f"Principales factores que contribuyen al riesgo: {', '.join(top_riesgo)}."
            )
        if top_prot:
            parrafos.append(
                f"Factores protectores identificados: {', '.join(top_prot)}."
            )

    return parrafos


# ═════════════════════════════════════════════════════════════════════
# Generadores de cada tipo de reporte
# ═════════════════════════════════════════════════════════════════════

def generar_predictivo_general(
    resumen: dict,
    dist_riesgo: list,
    dist_paralelo: list,
    usuario_nombre: str = "",
    importancias_globales: list | None = None,
) -> bytes:
    titulo = "Reporte Predictivo General"
    buf = BytesIO()
    doc = _nuevo_doc(buf)
    page_cb = _make_page_callback(titulo, usuario_nombre)
    elementos = _encabezado(titulo, "Resumen ejecutivo de predicciones de abandono", usuario_nombre)

    # 1. Hallazgos Principales
    elementos.extend(_seccion_numerada(
        "1", "Hallazgos Principales",
        "Observaciones clave identificadas a partir del análisis de predicciones.",
    ))
    interp = _interpretar_predictivo_general(resumen, dist_riesgo, dist_paralelo)
    if interp:
        elementos.extend(_lista_hallazgos(interp))

    # 2. Resumen General
    elementos.extend(_seccion_numerada(
        "2", "Resumen General",
        "Indicadores globales del sistema de predicción.",
    ))
    elementos.append(_subtitulo("2.1 Indicadores principales"))
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
    elementos.append(Spacer(1, 0.25 * inch))

    # 3. Distribución por Nivel de Riesgo
    elementos.extend(_seccion_numerada(
        "3", "Distribución por Nivel de Riesgo",
        "Cantidad y porcentaje de estudiantes en cada nivel de riesgo.",
    ))
    elementos.append(_subtitulo("3.1 Desglose por nivel"))
    riesgo_rows = [
        [d.get("nivel", ""), str(d.get("cantidad", 0)), f"{d.get('porcentaje', 0)}%"]
        for d in dist_riesgo
    ]
    elementos.append(_tabla(["Nivel", "Cantidad", "Porcentaje"], riesgo_rows))
    elementos.append(Spacer(1, 0.25 * inch))

    # 4. Distribución por Paralelo
    if dist_paralelo:
        elementos.extend(_seccion_numerada(
            "4", "Distribución por Paralelo",
            "Estudiantes con predicción por paralelo y niveles de riesgo Alto y Crítico.",
        ))
        elementos.append(_subtitulo("4.1 Detalle por paralelo"))
        paralelo_rows = [
            [d.get("paralelo", ""), d.get("area", ""), str(d.get("total", 0)),
             str(d.get("alto_riesgo", 0)), str(d.get("critico", 0))]
            for d in dist_paralelo
        ]
        elementos.append(_tabla(["Paralelo", "Area", "Total", "Alto Riesgo", "Critico"], paralelo_rows))

    # 5. Variables Más Influyentes del Modelo
    if importancias_globales:
        elementos.extend(_seccion_numerada(
            "5", "Variables Más Influyentes del Modelo",
            "Factores con mayor peso predictivo en el modelo actual (importancia acumulada por variable).",
        ))
        interp_imp = _interpretar_importancias_globales(importancias_globales)
        if interp_imp:
            elementos.extend(_lista_hallazgos(interp_imp))
        elementos.append(_subtitulo("5.1 Importancia por variable"))
        imp_rows = [
            [d.get("feature", ""), f"{d.get('importancia', 0):.1f}%"]
            for d in importancias_globales
        ]
        elementos.append(_tabla(
            ["Variable", "Importancia (%)"], imp_rows,
            col_widths=[4.5 * inch, 2 * inch],
        ))

    doc.build(elementos, onFirstPage=page_cb, onLaterPages=page_cb)
    return buf.getvalue()


def _interpretar_importancias_globales(importancias: list[dict]) -> list[str]:
    parrafos = []
    if not importancias:
        return parrafos
    top3 = importancias[:3]
    nombres = ", ".join(d.get("feature", "") for d in top3)
    parrafos.append(
        f"Las tres variables con mayor influencia en el modelo son: {nombres}. "
        "Estas variables deben considerarse prioritarias al diseñar intervenciones de retención."
    )
    alto_academico = [d for d in importancias if d.get("feature", "") in (
        "Promedio académico", "Materias reprobadas", "Materias cursadas", "Materias en 2do turno"
    )]
    alto_socio = [d for d in importancias if d.get("feature", "") in (
        "Estrato socioeconómico", "Situación laboral", "Apoyo económico", "Con quién vive"
    )]
    if alto_academico and alto_socio:
        parrafos.append(
            "El modelo combina factores académicos y socioeconómicos, lo que sugiere "
            "que las estrategias de retención deben ser integrales."
        )
    elif alto_academico:
        parrafos.append(
            "El rendimiento académico es el principal determinante del riesgo de abandono en este modelo."
        )
    elif alto_socio:
        parrafos.append(
            "Los factores socioeconómicos tienen mayor peso predictivo, indicando la necesidad "
            "de apoyo extracurricular y económico."
        )
    return parrafos


def generar_estudiantes_riesgo(
    estudiantes: list[dict],
    usuario_nombre: str = "",
    total_con_prediccion: int = 0,
) -> bytes:
    titulo = "Estudiantes en Riesgo"
    buf = BytesIO()
    doc = _nuevo_doc(buf)
    page_cb = _make_page_callback(titulo, usuario_nombre)
    elementos = _encabezado(
        titulo,
        f"Estudiantes con nivel Alto o Critico — {len(estudiantes)} estudiante(s)",
        usuario_nombre,
    )

    # 1. Análisis del Grupo en Riesgo
    elementos.extend(_seccion_numerada(
        "1", "Análisis del Grupo en Riesgo",
        "Resumen del conjunto de estudiantes en nivel de riesgo Alto o Crítico.",
    ))
    interp = _interpretar_estudiantes_riesgo(estudiantes, total_con_prediccion)
    if interp:
        elementos.extend(_lista_hallazgos(interp))

    # 2. Listado de Estudiantes en Riesgo
    elementos.extend(_seccion_numerada(
        "2", "Listado de Estudiantes en Riesgo",
        "Detalle individual con probabilidad de abandono y nivel de riesgo.",
    ))
    if not estudiantes:
        elementos.append(Paragraph("No se encontraron estudiantes en riesgo alto o critico.", getSampleStyleSheet()["Normal"]))
    else:
        elementos.append(_subtitulo("2.1 Estudiantes identificados"))
        page_w = letter[0] - _LEFT_MARGIN - _RIGHT_MARGIN
        nombre_w = 1.9 * inch
        fixed_w = (1.1 + 0.7 + 0.55 + 0.6 + 0.75) * inch + nombre_w
        factor_w = page_w - fixed_w
        _st_factor = ParagraphStyle("FactorCell", fontSize=7, leading=9, wordWrap="LTR")
        _st_nombre = ParagraphStyle("NombreCell", fontSize=8, leading=10, wordWrap="LTR")
        rows = [
            [
                e.get("codigo_estudiante", ""),
                Paragraph(e.get("nombre_estudiante", "").title(), _st_nombre),
                e.get("paralelo", ""),
                f"{e.get('probabilidad_abandono', 0):.1%}",
                e.get("nivel_riesgo", ""),
                str(e.get("fecha_prediccion", "")),
                Paragraph(e.get("factores_principales", "—"), _st_factor),
            ]
            for e in estudiantes
        ]
        elementos.append(_tabla(
            ["Codigo", "Nombre", "Paralelo", "Prob.", "Nivel", "Fecha", "Factores Principales"],
            rows,
            col_widths=[
                1.1 * inch, nombre_w, 0.7 * inch,
                0.55 * inch, 0.6 * inch, 0.75 * inch,
                factor_w,
            ],
        ))

    doc.build(elementos, onFirstPage=page_cb, onLaterPages=page_cb)
    return buf.getvalue()


def generar_por_paralelo(
    paralelo_info: dict,
    estudiantes: list[dict],
    usuario_nombre: str = "",
) -> bytes:
    nombre_par = paralelo_info.get("nombre", "")
    area = paralelo_info.get("area", "")
    titulo = f"Reporte por Paralelo: {nombre_par}"

    buf = BytesIO()
    doc = _nuevo_doc(buf)
    page_cb = _make_page_callback(titulo, usuario_nombre)
    elementos = _encabezado(titulo, f"Area: {area} — {len(estudiantes)} estudiante(s)", usuario_nombre)

    # 1. Análisis del Paralelo
    elementos.extend(_seccion_numerada(
        "1", "Análisis del Paralelo",
        "Situación de riesgo y asistencia de los estudiantes del paralelo.",
    ))
    interp = _interpretar_por_paralelo(estudiantes)
    if interp:
        elementos.extend(_lista_hallazgos(interp))

    # 2. Detalle de Estudiantes
    elementos.extend(_seccion_numerada(
        "2", "Detalle de Estudiantes",
        "Listado con asistencia y nivel de riesgo por estudiante.",
    ))
    if not estudiantes:
        elementos.append(Paragraph("No se encontraron estudiantes en este paralelo.", getSampleStyleSheet()["Normal"]))
    else:
        elementos.append(_subtitulo("2.1 Estudiantes del paralelo"))
        page_w = letter[0] - _LEFT_MARGIN - _RIGHT_MARGIN
        nombre_w = 2.0 * inch
        fixed_w = (1.1 + 0.75 + 0.55 + 0.6) * inch + nombre_w
        factor_w = page_w - fixed_w
        _st_factor = ParagraphStyle("FactorCell2", fontSize=7, leading=9, wordWrap="LTR")
        _st_nombre2 = ParagraphStyle("NombreCell2", fontSize=8, leading=10, wordWrap="LTR")
        rows = [
            [
                e.get("codigo_estudiante", ""),
                Paragraph(e.get("nombre_completo", "").title(), _st_nombre2),
                f"{e.get('porcentaje_asistencia', 0):.1f}%",
                f"{e.get('probabilidad', 0):.1%}" if e.get("probabilidad") is not None else "Sin prediccion",
                e.get("nivel_riesgo", "Sin prediccion"),
                Paragraph(e.get("factores_principales", "—"), _st_factor),
            ]
            for e in estudiantes
        ]
        elementos.append(_tabla(
            ["Codigo", "Nombre", "Asistencia", "Prob.", "Nivel", "Factores Principales"],
            rows,
            col_widths=[
                1.1 * inch, nombre_w, 0.75 * inch,
                0.55 * inch, 0.6 * inch,
                factor_w,
            ],
        ))

    doc.build(elementos, onFirstPage=page_cb, onLaterPages=page_cb)
    return buf.getvalue()


_ESTILO_SUBSUBTITULO = ParagraphStyle(
    "SubSubtitulo",
    fontSize=10,
    leading=14,
    textColor=DARK_TEXT,
    fontName="Helvetica-Bold",
    spaceBefore=8,
    spaceAfter=6,
    leftIndent=12,
)


def _tabla_asistencia_paralelo(materias: list[dict]) -> Table:
    """Tabla de materias con fila de TOTAL al final."""
    rows = []
    tot_clases = tot_pres = tot_aus = 0
    for m in materias:
        tc = m.get("total_clases", 0)
        pr = m.get("presentes", 0)
        au = m.get("ausentes", 0)
        pct = m.get("porcentaje_asistencia", 0)
        rows.append([m.get("materia", ""), str(tc), str(pr), str(au), f"{pct:.1f}%"])
        tot_clases += tc
        tot_pres += pr
        tot_aus += au

    pct_total = (tot_pres / tot_clases * 100) if tot_clases > 0 else 0
    total_row = ["TOTAL", str(tot_clases), str(tot_pres), str(tot_aus), f"{pct_total:.1f}%"]

    headers = ["Materia", "Total Clases", "Presentes", "Ausentes", "% Asistencia"]
    data = [headers] + rows + [total_row]
    t = Table(data, repeatRows=1)
    last = len(data) - 1
    t.setStyle(TableStyle([
        # Header
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("TOPPADDING", (0, 0), (-1, 0), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
        ("LEFTPADDING", (0, 0), (-1, 0), 10),
        # Data rows
        ("FONTNAME", (0, 1), (-1, last - 1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, last - 1), 8),
        ("TOPPADDING", (0, 1), (-1, last - 1), 8),
        ("BOTTOMPADDING", (0, 1), (-1, last - 1), 8),
        ("LEFTPADDING", (0, 1), (-1, last - 1), 10),
        *[("BACKGROUND", (0, i), (-1, i), GRAY_LIGHT) for i in range(2, last, 2)],
        # Total row
        ("BACKGROUND", (0, last), (-1, last), NAVY),
        ("TEXTCOLOR", (0, last), (-1, last), colors.white),
        ("FONTNAME", (0, last), (-1, last), "Helvetica-Bold"),
        ("FONTSIZE", (0, last), (-1, last), 8),
        ("TOPPADDING", (0, last), (-1, last), 8),
        ("BOTTOMPADDING", (0, last), (-1, last), 8),
        ("LEFTPADDING", (0, last), (-1, last), 10),
        # Grid
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


def generar_asistencia(
    grupos: list[dict],
    paralelo_nombre: str | None = None,
    usuario_nombre: str = "",
) -> bytes:
    """Genera reporte de asistencia jerárquico: Semestre → Paralelo → Materias."""
    titulo = "Reporte de Asistencia"
    subtitulo = f"Paralelo: {paralelo_nombre}" if paralelo_nombre else "Todos los paralelos"

    buf = BytesIO()
    doc = _nuevo_doc(buf)
    page_cb = _make_page_callback(titulo, usuario_nombre)
    elementos = _encabezado(titulo, subtitulo, usuario_nombre)

    # 1. Análisis de Asistencia
    elementos.extend(_seccion_numerada(
        "1", "Análisis de Asistencia",
        "Resumen de asistencia por semestre, área y paralelo.",
    ))
    elementos.extend(_resumen_texto_asistencia(grupos))

    # 2. Detalle por Semestre y Paralelo
    # Los elementos de la sección se guardan para incluirlos en el primer
    # KeepTogether del loop, evitando que el título quede solo al fondo de página.
    seccion2 = _seccion_numerada(
        "2", "Detalle por Semestre y Paralelo",
        "Asistencia por materia desglosada por semestre y paralelo.",
    )
    styles = getSampleStyleSheet()

    if not grupos:
        elementos.extend(seccion2)
        elementos.append(Paragraph("No se encontraron registros de asistencia.", styles["Normal"]))
    else:
        primer_bloque = True
        semestres_vistos: list[str] = []
        for g in grupos:
            semestre = g.get("semestre", "Sin Semestre")
            paralelo = g.get("paralelo", "")
            materias = g.get("materias", [])

            bloque = []
            if primer_bloque:
                bloque.extend(seccion2)
                primer_bloque = False
            if semestre not in semestres_vistos:
                semestres_vistos.append(semestre)
                bloque.append(_subtitulo(f"Semestre: {semestre}"))

            bloque.extend([
                Paragraph(f"Paralelo: {paralelo}", _ESTILO_SUBSUBTITULO),
                _tabla_asistencia_paralelo(materias),
                Spacer(1, 0.15 * inch),
            ])
            elementos.append(KeepTogether(bloque))

    doc.build(elementos, onFirstPage=page_cb, onLaterPages=page_cb)
    return buf.getvalue()


def generar_individual(
    estudiante: dict,
    predicciones: list[dict],
    alertas: list[dict],
    acciones: list[dict],
    usuario_nombre: str = "",
    shap_factores: list[dict] | None = None,
) -> bytes:
    nombre = estudiante.get("nombre_completo", "")
    codigo = estudiante.get("codigo_estudiante", "")
    titulo = f"Reporte Individual: {nombre}"

    buf = BytesIO()
    doc = _nuevo_doc(buf)
    page_cb = _make_page_callback(titulo, usuario_nombre)
    elementos = _encabezado(titulo, f"Codigo: {codigo}", usuario_nombre)

    # 1. Análisis de Situación del Estudiante
    elementos.extend(_seccion_numerada(
        "1", "Análisis de Situación",
        "Interpretación basada en predicciones, asistencia y alertas del estudiante.",
    ))
    interp = _interpretar_individual(estudiante, predicciones, alertas, acciones, shap_factores)
    if interp:
        elementos.extend(_lista_hallazgos(interp))

    # 2. Datos del Estudiante
    elementos.extend(_seccion_numerada(
        "2", "Datos del Estudiante",
        "Información personal, académica y sociodemográfica.",
    ))
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
        elementos.append(_subtitulo("2.1 Ficha del estudiante"))
        elementos.append(_tabla(["Campo", "Valor"], datos_rows, col_widths=[3 * inch, 4 * inch]))
    elementos.append(Spacer(1, 0.2 * inch))

    # 3. Factores de Riesgo Identificados (SHAP)
    elementos.extend(_seccion_numerada(
        "3", "Factores de Riesgo Identificados",
        "Variables que más influyen en la predicción de abandono de este estudiante.",
    ))
    styles = getSampleStyleSheet()
    if shap_factores:
        factores_riesgo = [f for f in shap_factores if f["tipo"] == "riesgo"]
        factores_protectores = [f for f in shap_factores if f["tipo"] == "protector"]

        if factores_riesgo:
            elementos.append(_subtitulo("3.1 Factores que incrementan el riesgo"))
            riesgo_rows = [
                [
                    f["nombre"],
                    f["valor"],
                    f"+{f['contribucion']:.4f}",
                ]
                for f in factores_riesgo
            ]
            t = _tabla(
                ["Factor", "Valor del Estudiante", "Contribución"],
                riesgo_rows,
                col_widths=[2.8 * inch, 2.0 * inch, 1.5 * inch],
            )
            # Color rojo en columna de contribución
            for i, _ in enumerate(factores_riesgo, start=1):
                t.setStyle(TableStyle([("TEXTCOLOR", (2, i), (2, i), RED)]))
            elementos.append(t)
            elementos.append(Spacer(1, 0.12 * inch))

        if factores_protectores:
            elementos.append(_subtitulo("3.2 Factores protectores (reducen el riesgo)"))
            prot_rows = [
                [
                    f["nombre"],
                    f["valor"],
                    f"{f['contribucion']:.4f}",
                ]
                for f in factores_protectores
            ]
            t2 = _tabla(
                ["Factor", "Valor del Estudiante", "Contribución"],
                prot_rows,
                col_widths=[2.8 * inch, 2.0 * inch, 1.5 * inch],
            )
            for i, _ in enumerate(factores_protectores, start=1):
                t2.setStyle(TableStyle([("TEXTCOLOR", (2, i), (2, i), GREEN)]))
            elementos.append(t2)
            elementos.append(Spacer(1, 0.12 * inch))

        elementos.append(Paragraph(
            "<i>Nota: La contribución indica cuánto empuja cada variable hacia el abandono (+) "
            "o lo reduce (−).</i>",
            ParagraphStyle("NotaShap", parent=getSampleStyleSheet()["Normal"],
                           fontSize=8, textColor=GRAY, leading=12),
        ))
    else:
        elementos.append(Paragraph(
            "No se dispone de datos de features para esta predicción.",
            styles["Normal"],
        ))
    elementos.append(Spacer(1, 0.2 * inch))

    # 4. Historial de Predicciones
    elementos.extend(_seccion_numerada(
        "4", "Historial de Predicciones",
        "Registro cronológico de predicciones realizadas.",
    ))
    if predicciones:
        elementos.append(_subtitulo("4.1 Predicciones registradas"))
        pred_rows = [
            [
                str(p.get("fecha_prediccion", "")),
                f"{p.get('probabilidad_abandono', 0):.1%}",
                p.get("nivel_riesgo", ""),
            ]
            for p in predicciones
        ]
        elementos.append(_tabla(["Fecha", "Probabilidad", "Nivel"], pred_rows))
    else:
        elementos.append(Paragraph("Sin predicciones registradas.", styles["Normal"]))
    elementos.append(Spacer(1, 0.2 * inch))

    # 5. Alertas
    elementos.extend(_seccion_numerada(
        "5", "Alertas",
        "Alertas generadas para el estudiante.",
    ))
    if alertas:
        elementos.append(_subtitulo("5.1 Historial de alertas"))
        alerta_rows = [
            [a.get("tipo", ""), a.get("nivel", ""), a.get("titulo", ""),
             a.get("estado", ""), str(a.get("fecha_creacion", ""))]
            for a in alertas
        ]
        elementos.append(_tabla(["Tipo", "Nivel", "Titulo", "Estado", "Fecha"], alerta_rows))
    else:
        elementos.append(Paragraph("Sin alertas registradas.", styles["Normal"]))
    elementos.append(Spacer(1, 0.2 * inch))

    # 6. Acciones Tomadas
    if acciones:
        elementos.extend(_seccion_numerada(
            "6", "Acciones Tomadas",
            "Acciones de seguimiento realizadas con el estudiante.",
        ))
        elementos.append(_subtitulo("6.1 Registro de acciones"))
        accion_rows = [
            [str(a.get("fecha", "")), a.get("descripcion", "")]
            for a in acciones
        ]
        elementos.append(_tabla(["Fecha", "Descripcion"], accion_rows))

    doc.build(elementos, onFirstPage=page_cb, onLaterPages=page_cb)
    return buf.getvalue()
