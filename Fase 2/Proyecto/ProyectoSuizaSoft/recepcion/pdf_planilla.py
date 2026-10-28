import os
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

# COLORES DE MARCA (DISEÑO ORIGINAL)
VERDE = colors.HexColor('#238636')
VERDE_CLARO = colors.HexColor('#2ea043')
NEUTRO = colors.HexColor('#37474F')
AMARILLO = colors.HexColor('#f1c40f')
GRIS_OSC = colors.HexColor('#1c2128')
GRIS_MED = colors.HexColor('#6e7681')
FONDO_SUB = colors.HexColor('#f6f8fa')
ROJO = colors.HexColor('#f85149')
# Antes era gris claro (#d0d7de); ahora negro para que TODOS los recuadros
# del documento tengan el mismo marco, sin que unos se vean "mas corridos"
# que otros por tener un borde mas debil.
BORDE = colors.HexColor('#000000')

# Dimensiones exactas y unificadas
ALTO_BANDA = 4.8 * mm
ANCHO_UTIL = 198 * mm
ESPACIO_SECCION = 1.8
# Espacio real (no una linea) entre la banda de titulo de cada seccion y su
# tabla de datos, para que quede separada en vez de pegada.
ESPACIO_BANDA_TABLA = 1.6

def _fmt_hora_cl(v):
    """Deja la hora como HH:MM aunque venga con segundos (HH:MM:SS)."""
    if not v or v == '-':
        return '-'
    s = str(v).strip()
    return s[:5] if len(s) >= 5 else s

def _fmt_kg_cl(v):
    try: n = float(v)
    except (TypeError, ValueError): n = 0.0
    parts = f"{n:.2f}".split('.')
    parts[0] = f"{int(parts[0]):,}".replace(',', '.')
    return f"{parts[0]},{parts[1]} kg"

def _fmt_fecha_cl(v):
    """Convierte fechas YYYY-MM-DD a formato chileno DD-MM-YYYY"""
    if not v or v == '-': 
        return '-'
    s = str(v).strip()[:10]
    p = s.split('-') if '-' in s else (s.split('/') if '/' in s else [])
    if len(p) == 3 and len(p[0]) == 4:
        return f"{p[2]}-{p[1]}-{p[0]}"
    return s

def construir_pdf_planilla(datos):
    enc = datos.get('encabezado', {})
    nombre_fruta = datos.get('nombre_fruta', 'FRUTA')
    planilla_id = datos.get('planilla_id', 0)
    colores_list = datos.get('colores', [])
    calibres_list = datos.get('calibres', [])
    defectos_list = datos.get('defectos', [])
    valor_estimacion = datos.get('estimacion', 0.0)
    estado_lib = datos.get('liberacion', '')
    observ = datos.get('observacion', '')
    logo_path = datos.get('logo_path')
    imagenes_list = datos.get('imagenes', [])

    styles = getSampleStyleSheet()
    micro = ParagraphStyle('micro', parent=styles['Normal'], fontSize=5.5, leading=6.5, textColor=colors.HexColor('#333333'))
    tiny = ParagraphStyle('tiny', parent=styles['Normal'], fontSize=5.2, leading=6.5, textColor=colors.HexColor('#333333'))
    obs_style = ParagraphStyle('obs', parent=styles['Normal'], fontSize=6.5, leading=8, textColor=colors.HexColor('#000000'))

    # La cabecera (logo + datos de la empresa + N° de planilla) se dibuja
    # aparte en CADA página (ver _dibujar_cabecera_y_pie más abajo), no como
    # un elemento más del "story" — así sale igual en la primera página y en
    # todas las que se agreguen después (por ejemplo las de evidencia
    # fotográfica), en vez de aparecer solo una vez al principio.
    cabecera_tabla = _cabecera_empresa(planilla_id, nombre_fruta, micro, logo_path)
    margen_arriba = 9 * mm
    _, alto_cabecera = cabecera_tabla.wrap(ANCHO_UTIL, A4[1])
    espacio_bajo_cabecera = 3 * mm

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=margen_arriba + alto_cabecera + espacio_bajo_cabecera, bottomMargin=8*mm,
        leftMargin=6*mm, rightMargin=6*mm,
        title=f"Planilla {planilla_id} - {nombre_fruta}"
    )

    def _dibujar_cabecera_y_pie(canvas, doc_actual):
        cabecera_tabla.wrapOn(canvas, ANCHO_UTIL, A4[1])
        cabecera_tabla.drawOn(canvas, doc_actual.leftMargin, A4[1] - margen_arriba - alto_cabecera)
        _pie_pagina(canvas, doc_actual)

    story = []

    # 1. Datos Generales (CON LAS FECHAS EN FORMATO DÍA-MES-AÑO)
    story.append(_banda("DATOS GENERALES"))
    story.append(Spacer(1, ESPACIO_BANDA_TABLA))
    story.append(_tabla_encabezado(enc))
    story.append(Spacer(1, ESPACIO_SECCION))

    # 3. Colores
    story.append(_banda("I. DISTRIBUCION DE COLOR Y MADUREZ"))
    story.append(Spacer(1, ESPACIO_BANDA_TABLA))
    story.append(_tabla_colores(colores_list, tiny))
    story.append(Spacer(1, ESPACIO_SECCION))

    # 4. Calibres
    story.append(_banda("II. DISTRIBUCION DE CALIBRE"))
    story.append(Spacer(1, ESPACIO_BANDA_TABLA))
    story.append(_tabla_calibres(calibres_list, tiny))
    story.append(Spacer(1, ESPACIO_SECCION))

    # 5. Defectos
    story.append(_banda("III. MATRIZ DE DEFECTOS POR CATEGORIA"))
    story.append(Spacer(1, ESPACIO_BANDA_TABLA))
    story.append(_tabla_defectos(defectos_list, tiny))
    story.append(Spacer(1, ESPACIO_SECCION))

    # 6. Estimación
    story.append(_banda("IV. ESTIMACION DE FRUTA EXPORTABLE"))
    story.append(Spacer(1, ESPACIO_BANDA_TABLA))
    story.append(_bloque_estimacion(valor_estimacion))
    story.append(Spacer(1, ESPACIO_SECCION))

    # 7. Resolución u Observaciones (Cajas separadas pero alineadas perfecto)
    story.append(_banda("V. RESOLUCION DE LOTE Y OBSERVACIONES"))
    story.append(Spacer(1, ESPACIO_BANDA_TABLA))
    bloques_resolucion = _bloque_resolucion(estado_lib, observ, obs_style)
    story.extend(bloques_resolucion)
    story.append(Spacer(1, ESPACIO_SECCION + 1))

    # 8. Firmas con espacio amplio
    story.append(_tabla_firmas())

    # 9. Evidencia fotográfica (si hay fotos cargadas para esta planilla), en
    # página(s) aparte al final, una foto lo más grande y legible posible por
    # bloque, con TODAS las fotos vigentes (sin límite fijo de cantidad).
    if imagenes_list:
        story.append(PageBreak())
        story.extend(_pagina_evidencias(imagenes_list, tiny))

    doc.build(story, onFirstPage=_dibujar_cabecera_y_pie, onLaterPages=_dibujar_cabecera_y_pie)
    buffer.seek(0)
    return buffer.getvalue()

def _banda(texto):
    p = Paragraph(f"<b>{texto}</b>", ParagraphStyle('band', fontSize=6.8, leading=8, textColor=colors.white, fontName='Helvetica-Bold'))
    t = Table([[p]], colWidths=[ANCHO_UTIL], rowHeights=[ALTO_BANDA])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), NEUTRO),
        # Contorno negro completo (arriba/abajo/izq/der), MISMO GROSOR (0.4)
        # que usan todos los demas recuadros del documento (cabecera, tablas,
        # estimacion, resolucion, evidencias), para que ninguno se vea
        # "sin marco" ni con un marco distinto a los demas.
        ('BOX', (0, 0), (-1, -1), 0.4, BORDE),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    return t

def _cabecera_empresa(planilla_id, nombre_fruta, micro, logo_path=None):
    empresa_style = ParagraphStyle('emp', parent=micro, fontSize=5.5, leading=6.5)
    
    company_txt = Paragraph(
        "<b><font size='6'>AGRICOLA SAN OSVALDO SPA</font></b><br/>"
        "Planta Agroindustrial - Ruta D427, Parcela N4<br/>"
        "Las Barrancas - IV Region - Coquimbo - Chile", empresa_style
    )

    izq_cell = company_txt
    if logo_path and os.path.exists(logo_path):
        try:
            iw, ih = ImageReader(logo_path).getSize()
            max_h, max_w = 8.5 * mm, 45 * mm
            ratio = min(max_w / iw, max_h / ih)
            logo = Image(logo_path, width=iw * ratio, height=ih * ratio)
            logo.hAlign = 'LEFT'
            
            izq_cell = Table([[logo], [Spacer(1, 1)], [company_txt]], colWidths=[66*mm])
            izq_cell.setStyle(TableStyle([
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ]))
        except Exception: pass

    tit_style = ParagraphStyle('tit', fontSize=8.5, leading=10, alignment=TA_CENTER, fontName='Helvetica-Bold', textColor=colors.HexColor('#1c2128'))
    subtit_style = ParagraphStyle('subtit', fontSize=7, leading=8.5, alignment=TA_CENTER, fontName='Helvetica-Bold', textColor=VERDE)

    centro = [
        Paragraph("PLANILLA DE CONTROL DE CALIDAD", tit_style),
        Spacer(1, 1),
        Paragraph(f"RECEPCION DE {nombre_fruta}", subtit_style)
    ]

    der = Paragraph(
        f"<para align='right'><b>N° Planilla:</b> "
        f"<font size='7.5'><b>{planilla_id}</b></font><br/>"
        f"<b>Código:</b> POE023 / REG023<br/>"
        f"<b>Versión:</b> 02<br/>"
        f"<b>Fecha Emisión:</b> 03-01-2023</para>", micro
    )

    t = Table([[izq_cell, centro, der]], colWidths=[66*mm, 62*mm, 70*mm])
    t.setStyle(TableStyle([
        # Mismo grosor (0.4) que el resto de los marcos del documento.
        ('BOX', (0, 0), (-1, -1), 0.4, BORDE),
        ('LINEBEFORE', (1, 0), (1, 0), 0.4, GRIS_MED),
        ('LINEBEFORE', (2, 0), (2, 0), 0.4, GRIS_MED),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 1.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5),
    ]))
    return t

def _tabla_encabezado(enc):
    mercado = enc.get('mercado', 1)
    mercado_txt = "EXPORTACION" if mercado == 1 else "INTERNO"

    filas = [
        ['PLANTA:', str(enc.get('planta', '-')), 'PRODUCTOR:', enc.get('productor', '-'), 'VARIEDAD:', enc.get('variedad', '-')],
        ['HUERTO:', enc.get('huerto', '-'), 'CUARTEL/SDP:', enc.get('sdp', '-'), 'GUIA:', str(enc.get('guia', '-'))],
        ['F. COSECHA:', _fmt_fecha_cl(enc.get('f_cosecha')), 'F. RECEPCION:', _fmt_fecha_cl(enc.get('f_recepcion')), 'F. INSPECCION:', _fmt_fecha_cl(enc.get('f_inspeccion'))],
        ['BULTOS:', str(enc.get('tam_lote', 0)), 'KG NETOS:', _fmt_kg_cl(enc.get('kg_neto', 0.0)), 'MERCADO:', mercado_txt],
        ['HORA LLEGADA:', _fmt_hora_cl(enc.get('hora_llegada')), '', '', '', ''],
    ]
    fila_hora = len(filas) - 1
    t = Table(filas, colWidths=[22*mm, 44*mm, 24*mm, 40*mm, 24*mm, 44*mm])
    t.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 5.5),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTNAME', (4, 0), (4, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (0, -1), NEUTRO),
        ('TEXTCOLOR', (2, 0), (2, -1), NEUTRO),
        ('TEXTCOLOR', (4, 0), (4, -1), NEUTRO),
        ('BACKGROUND', (0, 0), (-1, -1), FONDO_SUB),
        ('GRID', (0, 0), (-1, -1), 0.4, BORDE),
        ('SPAN', (1, fila_hora), (5, fila_hora)),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2.5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2.5),
        ('TOPPADDING', (0, 0), (-1, -1), 0.8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0.8),
    ]))
    return t

def _tabla_colores(colores_list, tiny):
    if not colores_list: return Paragraph("<i>Sin colores registrados.</i>", tiny)

    header = ['COLOR']
    fila = ['%']
    total = 0.0
    for nombre, porc in colores_list:
        header.append(nombre)
        try: pf = float(porc)
        except: pf = 0.0
        fila.append(f"{pf:.2f}" if pf > 0 else '-')
        total += pf
    header.append('TOTAL')
    fila.append(f"{total:.2f}")

    n_cols = len(header)
    total_width = ANCHO_UTIL
    first_col_w = 18 * mm
    last_col_w = 18 * mm
    mid_w = (total_width - first_col_w - last_col_w) / max(1, (n_cols - 2))
    col_widths = [first_col_w] + [mid_w] * (n_cols - 2) + [last_col_w]

    t = Table([header, fila], colWidths=col_widths)
    t.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 5.5),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (0, 1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (-1, 0), NEUTRO),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, 1), (0, 1), FONDO_SUB),
        ('BACKGROUND', (-1, 0), (-1, -1), AMARILLO),
        ('TEXTCOLOR', (-1, 1), (-1, 1), colors.black),
        ('FONTNAME', (-1, 1), (-1, 1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.4, BORDE),
        ('TOPPADDING', (0, 0), (-1, -1), 0.8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0.8),
    ]))
    return t

def _tabla_calibres(calibres_list, tiny):
    if not calibres_list: return Paragraph("<i>Sin calibres registrados.</i>", tiny)

    data = [['SIZE / CALIBRE', 'CANTIDAD FRUTOS', 'PORCENTAJE (%)']]
    total_cant = 0
    total_porc = 0.0
    for nombre, porc, cant in calibres_list:
        try: pf = float(porc)
        except: pf = 0.0
        try: cf = int(cant)
        except: cf = 0
        data.append([nombre, str(cf) if cf > 0 else '-', f"{pf:.2f}" if pf > 0 else '-'])
        total_cant += cf
        total_porc += pf

    data.append(['TOTAL', str(total_cant) if total_cant > 0 else '-', f"{total_porc:.2f}"])

    t = Table(data, colWidths=[90*mm, 52*mm, 56*mm])
    t.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 5.5),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (-1, 0), NEUTRO),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, FONDO_SUB]),
        ('BACKGROUND', (0, -1), (-1, -1), AMARILLO),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.4, BORDE),
        ('LEFTPADDING', (0, 0), (0, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 0.6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0.6),
    ]))
    return t

def _tabla_defectos(defectos_list, tiny):
    if not defectos_list: return Paragraph("<i>Sin defectos registrados.</i>", tiny)

    data = [['DEFECTO', 'FANCY (%)', 'CHOICE (%)', 'COMERCIAL (%)']]
    tot1 = tot2 = totc = 0.0
    factor_rows = []
    current = None

    for d in defectos_list:
        if d['factor'] != current:
            current = d['factor']
            nombre_grupo = 'CALIDAD' if current == 1 else 'CONDICION'
            data.append([nombre_grupo, '', '', ''])
            factor_rows.append(len(data) - 1)

        p1, p2, pcom = d.get('p1', 0), d.get('p2', 0), d.get('pcom', 0)
        data.append([
            d['nombre'],
            f"{p1:.2f}" if p1 > 0 else '-',
            f"{p2:.2f}" if p2 > 0 else '-',
            f"{pcom:.2f}" if pcom > 0 else '-',
        ])
        tot1 += p1; tot2 += p2; totc += pcom

    data.append(['TOTAL DEFECTOS', f"{tot1:.2f}%", f"{tot2:.2f}%", f"{totc:.2f}%"])
    ultima = len(data) - 1

    style = [
        ('FONTSIZE', (0, 0), (-1, -1), 5.0),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (-1, 0), NEUTRO),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.4, BORDE),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (0, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 0.4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0.4),
        ('BACKGROUND', (0, ultima), (-1, ultima), AMARILLO),
        ('FONTNAME', (0, ultima), (-1, ultima), 'Helvetica-Bold'),
    ]
    for fr in factor_rows:
        style.append(('SPAN', (0, fr), (-1, fr)))
        style.append(('BACKGROUND', (0, fr), (-1, fr), GRIS_OSC))
        style.append(('TEXTCOLOR', (0, fr), (-1, fr), colors.white))
        style.append(('FONTNAME', (0, fr), (-1, fr), 'Helvetica-Bold'))
        style.append(('ALIGN', (0, fr), (-1, fr), 'CENTER'))
    if tot1 >= 100: style.append(('TEXTCOLOR', (1, ultima), (1, ultima), ROJO))
    if tot2 >= 100: style.append(('TEXTCOLOR', (2, ultima), (2, ultima), ROJO))
    if totc >= 100: style.append(('TEXTCOLOR', (3, ultima), (3, ultima), ROJO))

    t = Table(data, colWidths=[90*mm, 36*mm, 36*mm, 36*mm])
    t.setStyle(TableStyle(style))
    return t

def _bloque_estimacion(valor):
    try: v = float(valor)
    except: v = 0.0
    par = Paragraph(
        f"<b>Porcentaje estimado de fruta exportable/embalable:</b> "
        f"<font size='9.5' color='#238636'><b>{v:.2f}%</b></font>",
        ParagraphStyle('estim', fontSize=6.8, leading=11, alignment=TA_CENTER)
    )
    t = Table([[par]], colWidths=[ANCHO_UTIL])
    t.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.4, BORDE),
        ('BACKGROUND', (0, 0), (-1, -1), FONDO_SUB),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    return t

def _bloque_resolucion(estado_lib, observ, obs_style):
    est_str = str(estado_lib).strip().upper()
    liberado = est_str in ('A', '1')
    objetado = est_str in ('R', '2')

    check_lib = "[X]" if liberado else "[ ]"
    check_obj = "[X]" if objetado else "[ ]"
    color_lib = VERDE_CLARO if liberado else GRIS_MED
    color_obj = ROJO if objetado else GRIS_MED

    p_lib = Paragraph(
        f"<font size='8' color='{color_lib.hexval()}'><b>{check_lib}</b></font> "
        f"<font size='6.5' color='{color_lib.hexval()}'><b>PRODUCTO LIBERADO</b></font>",
        ParagraphStyle('rl', fontSize=6.5, leading=8, alignment=TA_CENTER)
    )
    p_obj = Paragraph(
        f"<font size='8' color='{color_obj.hexval()}'><b>{check_obj}</b></font> "
        f"<font size='6.5' color='{color_obj.hexval()}'><b>PRODUCTO OBJETADO</b></font>",
        ParagraphStyle('ro', fontSize=6.5, leading=8, alignment=TA_CENTER)
    )

    t_res = Table([[p_lib, p_obj]], colWidths=[99*mm, 99*mm])
    t_res.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.4, BORDE),
        ('LINEBEFORE', (1, 0), (1, 0), 0.4, GRIS_MED),
        ('BACKGROUND', (0, 0), (-1, -1), FONDO_SUB),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 1.2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1.2),
    ]))

    texto_obs = observ.strip() if observ else '<i>(Sin observaciones)</i>'
    titulo_obs = Paragraph("<font color='white'><b>OBSERVACIONES GENERALES:</b></font>", ParagraphStyle('obst', fontSize=6.5, leading=8, textColor=colors.white))
    contenido_obs = Paragraph(texto_obs, obs_style)

    t_obs = Table([[titulo_obs], [contenido_obs]], colWidths=[ANCHO_UTIL])
    t_obs.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.4, BORDE),
        ('BACKGROUND', (0, 0), (0, 0), GRIS_OSC),
        ('BACKGROUND', (0, 1), (0, 1), colors.white),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (0, 0), 1),
        ('BOTTOMPADDING', (0, 0), (0, 0), 1),
        ('TOPPADDING', (0, 1), (0, 1), 1.2),
        ('BOTTOMPADDING', (0, 1), (0, 1), 1.2),
    ]))

    return [t_res, Spacer(1, ESPACIO_SECCION), t_obs]

def _pagina_evidencias(imagenes_list, tiny):
    """
    Arma el bloque de evidencia fotográfica: TODAS las fotos vigentes que
    tenga la planilla (sin límite fijo de cantidad), en una grilla de 2
    columnas por fila. Se ven varias fotos por página (no una gigante sola),
    pero siguen siendo lo bastante grandes como para distinguirse bien.
    ReportLab va acomodando solo cuántas filas entran en cada página y sigue
    en la siguiente automáticamente, así que no hace falta calcular a mano
    cuántas fotos caben por hoja.

    imagenes_list: lista de dicts con 'imagen' (bytes del binario de la foto),
    'nombre' (str) y 'fecha' (str, ya formateada como dd-mm-aaaa).
    """
    flow = []
    total = len(imagenes_list)
    titulo = f"VI. EVIDENCIA FOTOGRAFICA ({total} foto{'s' if total != 1 else ''})"
    flow.append(_banda(titulo))
    flow.append(Spacer(1, ESPACIO_SECCION))

    caption_style = ParagraphStyle(
        'evid_cap', parent=tiny, fontSize=6, leading=7.2,
        alignment=TA_CENTER, textColor=NEUTRO
    )

    columnas = 2
    espacio_entre = 3 * mm
    ancho_celda = (ANCHO_UTIL - espacio_entre * (columnas - 1)) / columnas
    alto_max_foto = 45 * mm  # más chicas todavía: entran más por hoja, se siguen viendo bien

    def _celda_foto(foto):
        celda = []
        contenido_bytes = foto.get('imagen')
        if not contenido_bytes:
            celda.append(Paragraph("<i>No se pudo cargar esta imagen.</i>", tiny))
        else:
            try:
                buf_img = BytesIO(contenido_bytes)
                iw, ih = ImageReader(buf_img).getSize()
                ratio = min(ancho_celda / iw, alto_max_foto / ih)
                ancho_final = iw * ratio
                alto_final = ih * ratio

                buf_img.seek(0)
                img = Image(buf_img, width=ancho_final, height=alto_final)
                img.hAlign = 'CENTER'
                celda.append(img)
            except Exception:
                celda.append(Paragraph("<i>Imagen dañada o en un formato no soportado.</i>", tiny))

        nombre = foto.get('nombre') or '-'
        fecha = foto.get('fecha') or '-'
        celda.append(Spacer(1, 1))
        celda.append(Paragraph(f"<b>{nombre}</b><br/>Cargada: {fecha}", caption_style))
        return celda

    # Una fila (Table) de 2 columnas por cada par de fotos. Se van agregando
    # como flowables sueltos al story, para que ReportLab las reparta entre
    # páginas de forma automática según lo que vaya entrando.
    for i in range(0, total, columnas):
        par = imagenes_list[i:i + columnas]
        celdas = [_celda_foto(foto) for foto in par]
        while len(celdas) < columnas:
            celdas.append('')  # última fila incompleta (número impar de fotos)

        fila = Table([celdas], colWidths=[ancho_celda] * columnas)
        fila.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            # Mismo grosor (0.4) que el resto de los marcos del documento.
            ('BOX', (0, 0), (-1, -1), 0.4, BORDE),
            ('INNERGRID', (0, 0), (-1, -1), 0.4, BORDE),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        flow.append(fila)
        flow.append(Spacer(1, 2))

    return flow

def _tabla_firmas():
    t = Table([
        ['', ''],
        ['_______________________________', '_______________________________'],
        ['Nombre y Firma Responsable', 'Nombre y Firma Verificador'],
    ], colWidths=[99*mm, 99*mm], rowHeights=[16*mm, 3.5*mm, 3.5*mm])
    t.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 6),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    return t

def _pie_pagina(canvas, doc):
    from datetime import datetime
    canvas.saveState()
    canvas.setFont('Helvetica', 5.5)
    canvas.setFillColor(GRIS_MED)
    fecha = datetime.now().strftime('%d-%m-%Y %H:%M')
    canvas.drawString(6*mm, 3*mm, f"Generado: {fecha}  |  SUIZASOFT - Sistema de Control de Calidad")
    canvas.drawRightString(A4[0] - 6*mm, 3*mm, f"Página {doc.page}")
    canvas.setStrokeColor(BORDE)
    canvas.setLineWidth(0.4)
    canvas.line(6*mm, 5*mm, A4[0] - 6*mm, 5*mm)
    canvas.restoreState()