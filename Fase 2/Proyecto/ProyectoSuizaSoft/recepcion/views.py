import os
import logging
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
import pyodbc
from datetime import date, datetime
import json
import traceback
from .pdf_planilla import construir_pdf_planilla

logger = logging.getLogger(__name__)

def obtener_conexion_maestra():
    return pyodbc.connect("DSN=Desarrollo;UID=plc_sag;PWD=suiza;")

def _buscar_hora_llegada(columnas, row):
    """
    Ubica la 'hora de llegada' guardada en ctlcalrecepcionfrutasenca.

    CONFIRMADO revisando el codigo real del stored procedure
    Movil_Recep_CreaPlanilla (05-09-2026): la columna correcta es
    'ccre_hordes' ("hora descarga" del camion = Hora Llegada del
    formulario). El procedimiento SI recibia el parametro @llegada, pero
    lo ignoraba por completo -- tenia "ccre_hordes" = null puesto a mano
    tanto en el INSERT como en el UPDATE. Se corrigio el procedimiento
    (ver sp_creaplanilla_fix.sql) para que use @llegada en vez de null.
    Se deja 'ccre_horing' como respaldo por si en algun momento se usa
    esa columna en su lugar, pero 'ccre_hordes' es la que corresponde.
    """
    cols_lower = [str(c).lower() for c in columnas]
    for nombre_exacto in ('ccre_hordes', 'ccre_horing'):
        if nombre_exacto in cols_lower:
            i = cols_lower.index(nombre_exacto)
            valor = row[i]
            if valor not in (None, ''):
                return str(valor).strip()
    return ''

def limpiar_kilos_float(val):
    """
    Limpia y convierte cualquier cadena de kilos (ej: '7.830', '7.830,00', '7830.0', '7.830 KG')
    en un número float válido para Sybase sin perder decimales ni multiplicar por mil.
    """
    if not val:
        return 0.0
    s = str(val).upper().replace('KG', '').strip()
    if not s:
        return 0.0
    
    if '.' in s and ',' in s:
        s = s.replace('.', '').replace(',', '.')
    elif ',' in s:
        s = s.replace(',', '.')
    elif '.' in s:
        parts = s.split('.')
        if len(parts) == 2 and len(parts[1]) == 3 and len(parts[0]) <= 3:
            s = s.replace('.', '')
        elif len(parts) > 2:
            s = s.replace('.', '')
    try:
        return float(s)
    except:
        return 0.0

def get_int_safe(val, default=0):
    if val is None: return default
    s = str(val).strip().lower()
    if s in ['', 'none', 'null', 'undefined']: return default
    try: return int(float(s.replace(',', '.')))
    except: return default

def seguro_texto(val):
    if val is None: return ""
    s = str(val).strip()
    if s.lower() in ['none', 'null', '']: return ""
    return s

def obtener_imagen_fruta(nombre_fruta):
    """
    Mapea el nombre de la fruta al archivo PNG correspondiente en static/img/frutas/.
    Los PNG los guarda el jefe en esa carpeta. Si no hay coincidencia devuelve '' y
    el template cae al fallback (icono generico).
    """
    if not nombre_fruta:
        return ''
    n = nombre_fruta.strip().upper()
    if 'LIM' in n:      return 'limon.png'
    if 'NARAN' in n:    return 'naranja.png'
    if 'CLEMEN' in n:   return 'clementina.png'
    if 'MANDA' in n:    return 'mandarina.png'
    if 'POMEL' in n or 'TORONJ' in n: return 'pomelo.png'
    return ''

def login_app(request):
    if request.method == 'POST':
        u, c = request.POST.get('usuario'), request.POST.get('clave')
        try:
            conexion = obtener_conexion_maestra()
            cursor = conexion.cursor()
            cursor.execute('SELECT * FROM "DBA"."usersde" WHERE usrs_usrnam = ? AND usrs_psword = ?', (u, c))
            usuario = cursor.fetchone()
            conexion.close() 
            if usuario:
                request.session['usuario_activo'] = u
                return redirect('seleccion_frutas') 
            return render(request, 'index.html', {'error': 'Usuario o contraseña incorrectos.'})
        except Exception as e: 
            return render(request, 'index.html', {'error': f'Error Sybase: {str(e)}'})
    return render(request, 'index.html')

def seleccion_frutas(request):
    if 'usuario_activo' not in request.session: return redirect('login_app')
    especies_list = []
    try:
        conexion = obtener_conexion_maestra()
        cursor = conexion.cursor()
        cursor.execute('{CALL "DBA"."Movil_muestra_especies"()}')
        for fila in cursor.fetchall(): especies_list.append({'id': fila[0], 'nombre': fila[1]})
        conexion.close()
    except: pass
    return render(request, 'Seleccion_Frutas.html', {'especies': especies_list})

def recepcion_dinamica(request, especie_id):
    if 'usuario_activo' not in request.session: return redirect('login_app')
    exp, plant, var_db, nom_f = [], [], [], "FRUTA"
    fecha_hoy = date.today().strftime('%Y-%m-%d')
    try:
        conexion = obtener_conexion_maestra()
        cursor = conexion.cursor()
        cursor.execute('{CALL "DBA"."Movil_muestra_especies"()}')
        for f in cursor.fetchall():
            if str(f[0]) == str(especie_id): nom_f = f[1].upper(); break
        cursor.execute('{CALL "DBA"."Movil_muestra_clienteprod"()}')
        for f in cursor.fetchall():
            cid = str(f[0]).split('.')[0].strip()
            exp.append({'id': cid, 'nombre': f"[{cid}] {f[1]}"})
        cursor.execute('{CALL "DBA"."Movil_muestra_Plantas"(?)}', 1)
        for f in cursor.fetchall():
            pid = str(f[0]).split('.')[0].strip()
            plant.append({'id': pid, 'nombre': f"{pid} / {str(f[2]).strip()} - {f[1]}"})
        cursor.execute('{CALL "DBA"."Movil_muestra_Variedades"(?)}', especie_id)
        for f in cursor.fetchall():
            vid = str(f[0]).split('.')[0].strip()
            var_db.append({'id': vid, 'nombre': f"[{vid}] {f[1]}"})
        conexion.close()
    except: pass

    config_calidad = { 'colores': [], 'parametros': [], 'categorias': ['Fancy', 'Choice', 'Comercial'], 'defectos': [], 'calibres': [] }
    imagen_fruta = obtener_imagen_fruta(nom_f)
    return render(request, 'recepcion_dinamica.html', {'exportadores_db': exp, 'plantas_db': plant, 'variedades_db': var_db, 'especie_id': especie_id, 'nombre_fruta': nom_f, 'imagen_fruta': imagen_fruta, 'fecha_hoy': fecha_hoy, 'config_calidad_json': json.dumps(config_calidad)})

def obtener_productores(request, exportador_id):
    lista = []
    try:
        conexion = obtener_conexion_maestra()
        cursor = conexion.cursor()
        cursor.execute('{CALL "DBA"."Movil_muestra_productores"(?)}', exportador_id)
        for f in cursor.fetchall(): pid = str(f[0]).split('.')[0].strip(); lista.append({'id': pid, 'nombre': f"[{pid}] {f[1]}"})
        conexion.close()
    except: pass
    return JsonResponse({'estado': 'Exito', 'productores': lista})

def obtener_predios(request, productor_id):
    lista = []
    try:
        conexion = obtener_conexion_maestra()
        cursor = conexion.cursor()
        cursor.execute('{CALL "DBA"."Movil_muestra_predios"(?)}', productor_id)
        for f in cursor.fetchall(): pid = str(f[0]).split('.')[0].strip(); lista.append({'id': pid, 'nombre': f"[{pid} / {str(f[2]).strip()}] {f[1]}"})
        conexion.close()
    except: pass
    return JsonResponse({'estado': 'Exito', 'predios': lista})

def obtener_cuarteles(request, productor_id, predio_id, especie_id):
    lista = []
    try:
        conexion = obtener_conexion_maestra()
        cursor = conexion.cursor()
        cursor.execute('{CALL "DBA"."Movil_muestra_cuarteles"(?, ?, ?)}', (productor_id, predio_id, especie_id))
        for f in cursor.fetchall():
            cid = str(f[0]).split('.')[0].strip()
            sdp = str(f[2]).strip() if f[2] is not None else 'N/A'
            vid = str(f[5]).split('.')[0].strip() if f[5] is not None else ''
            lista.append({'id': cid, 'nombre': f"[{cid}] SDP: {sdp}", 'v_id': vid})
        conexion.close()
    except: pass
    return JsonResponse({'estado': 'Exito', 'cuarteles': lista})

def buscar_lote(request, especie_id):
    lote_buscado = request.GET.get('lote', '').strip() 
    planta = request.GET.get('planta', '0')
    cliente = request.GET.get('cliente', '0')
    productor = request.GET.get('productor', '-1')
    tipo = int(request.GET.get('tipo', 1))
    try:
        conexion = obtener_conexion_maestra()
        cursor = conexion.cursor()
        cursor.execute('{CALL "DBA"."Ctlcal_Busca_LotesFrutaGranel"(?, ?, ?, ?, ?, ?)}', (int(planta), int(especie_id), -1, int(productor), tipo, int(cliente)))
        rows = cursor.fetchall()
        if lote_buscado:
            for f in rows:
                if str(f[20]).strip() == lote_buscado or str(f[2]).strip() == lote_buscado: 
                    return JsonResponse({'estado': 'Exito', 'datos': {
                        'lote': str(f[20]).strip() if f[20] else str(f[2]).strip(), 'lote_id': int(f[2]), 'variedad_id': str(f[3]).split('.')[0].strip(), 'productor_id': str(f[5]).split('.')[0].strip(), 'predio_id': str(f[12]).split('.')[0].strip(), 'cuartel_id': str(f[13]).split('.')[0].strip(),
                        'guia': str(f[14]).strip() if f[14] is not None else '', 'fecha_cosecha': str(f[15])[:10] if f[15] else '', 'fecha_recepcion': str(f[11])[:10] if f[11] else '', 'bultos': int(f[16]) if f[16] is not None else 0, 'kg_neto': float(f[22]) if f[22] is not None else 0
                    }})
            return JsonResponse({'estado': 'Error', 'mensaje': 'Lote no encontrado'})
        else:
            lotes_list = []
            for f in rows: lotes_list.append({'lote': str(f[20]).strip() if f[20] else str(f[2]).strip(), 'lote_id': int(f[2]), 'variedad_nombre': str(f[4]).strip(), 'guia': str(f[14]).strip() if f[14] is not None else '-', 'fecha_recepcion': str(f[11])[:10] if f[11] else '', 'bultos': int(f[16]) if f[16] is not None else 0, 'kg_neto': float(f[22]) if f[22] is not None else 0, 'variedad_id': str(f[3]).split('.')[0].strip(), 'productor_id': str(f[5]).split('.')[0].strip(), 'predio_id': str(f[12]).split('.')[0].strip(), 'cuartel_id': str(f[13]).split('.')[0].strip(), 'fecha_cosecha': str(f[15])[:10] if f[15] else ''})
            return JsonResponse({'estado': 'Exito', 'lotes': lotes_list})
    except Exception as e: return JsonResponse({'estado': 'Error', 'mensaje': str(e)})

def guardar_planilla(request, especie_id):
    if request.method == 'POST':
        
        try:
            cliente = get_int_safe(request.POST.get('exportador_id'))
            planta = get_int_safe(request.POST.get('planta_id'))
            planilla = get_int_safe(request.POST.get('nro_planilla'))
            productor = get_int_safe(request.POST.get('productor_id'))
            predio = get_int_safe(request.POST.get('predio_id'))
            cuartel = get_int_safe(request.POST.get('cuartel_id'))
            variedad = get_int_safe(request.POST.get('variedad_id'), -1)

            if cliente == 0 or planta == 0 or productor == 0:
                return JsonResponse({'estado': 'Error', 'mensaje': '⚠️ Faltan datos obligatorios.'})

            f_rec = request.POST.get('fecha_recepcion') or date.today().strftime('%Y-%m-%d')
            f_cosecha = request.POST.get('fecha_cosecha') or f_rec
            h_insp = datetime.now().strftime('%H:%M:%S')
            # Este valor se manda como parametro @llegada al stored procedure
            # (ver el CALL mas abajo), que ahora si lo graba en "ccre_hordes"
            # (se corrigio el procedimiento -- antes tenia esa columna
            # fijada a null a mano e ignoraba este parametro por completo).
            h_llegada = request.POST.get('hora_llegada') or h_insp
            lote_interno = get_int_safe(request.POST.get('lote_id_hidden'))
            mercado = get_int_safe(request.POST.get('mercado'))
            if mercado not in [1, 2]: mercado = 2
            bultos = get_int_safe(request.POST.get('bultos'))
            
            kilos_raw = request.POST.get('kg_neto', '0')
            kilos = limpiar_kilos_float(kilos_raw)
            
            guia = get_int_safe(request.POST.get('guia_despacho'))
            usuario = request.session.get('usuario_activo', 'admin')[:25]

            conexion = obtener_conexion_maestra()
            cursor = conexion.cursor()
            
            params = (cliente, planta, planilla, especie_id, variedad, f_rec, f_rec, h_insp, h_llegada, productor, predio, cuartel, f_cosecha, lote_interno, mercado, bultos, kilos, guia, usuario)
            cursor.execute('{CALL "DBA"."Movil_Recep_CreaPlanilla"(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)}', params)

            planilla_generada = planilla
            if planilla == 0:
                cursor.execute('SELECT MAX(ccre_numero) FROM "DBA"."ctlcalrecepcionfrutasenca" WHERE clie_codigo=? AND plde_codigo=? AND espe_codigo=?', (cliente, planta, especie_id))
                row = cursor.fetchone()
                planilla_generada = int(row[0]) if row and row[0] else 0
                

            conexion.commit()

            # 🎯 Inicializar filas vacías de colores/calibres en Sybase
            try:
                cursor.execute('{CALL "DBA"."Movil_Recep_detalleColor"(?, ?, ?, ?)}',
                               (cliente, planta, planilla_generada, int(especie_id)))
                conexion.commit()
            except Exception as e:
                print("Error creando registros base de colores:", e)

            conexion.close()  
            return JsonResponse({'estado': 'Exito', 'mensaje': f'Planilla N° {planilla_generada} guardada correctamente.', 'planilla_id': planilla_generada})  # ← línea que ya existe
        except Exception as e:
            print("Error creando registros base de colores:", e)
            return JsonResponse({'estado': 'Exito', 'mensaje': f'Planilla N° {planilla_generada} guardada correctamente.', 'planilla_id': planilla_generada})
        except Exception as e: return JsonResponse({'estado': 'Error', 'mensaje': f'Fallo en Sybase: {str(e)}'})
    return JsonResponse({'estado': 'Error', 'mensaje': 'Método no permitido'})

def guardar_colores(request, especie_id):
    if request.method == 'POST':
        cliente = get_int_safe(request.POST.get('exportador_id'))
        planta = get_int_safe(request.POST.get('planta_id'))
        planilla = get_int_safe(request.POST.get('nro_planilla'))

        if planilla == 0: return JsonResponse({'estado': 'Error', 'mensaje': 'Debe guardar el Encabezado primero.'})
        
        try:
            conexion = obtener_conexion_maestra()
            cursor = conexion.cursor()
            procesados = 0
            for key, value in request.POST.items():
                if key.startswith('col_') and value.strip() != '':
                    codigo_color = int(key.split('_')[1]) 
                    valor_porcentaje = float(value.replace(',', '.'))
                    cursor.execute('{CALL "DBA"."Movil_Recep_Actuliza_DetalleColor"(?, ?, ?, ?, ?, ?)}', 
                                   (cliente, planta, planilla, especie_id, codigo_color, valor_porcentaje))
                    procesados += 1
            
            if procesados == 0: return JsonResponse({'estado': 'Error', 'mensaje': 'No se enviaron datos numéricos.'})
            conexion.commit()
            conexion.close()
            return JsonResponse({'estado': 'Exito', 'mensaje': '✅ ¡Colores guardados con éxito!'})
        except Exception as e: return JsonResponse({'estado': 'Error', 'mensaje': str(e)})
    return JsonResponse({'estado': 'Error', 'mensaje': 'Método no válido'})

def guardar_calibres(request, especie_id):
    if request.method == 'POST':
        cliente = get_int_safe(request.POST.get('exportador_id'))
        planta = get_int_safe(request.POST.get('planta_id'))
        planilla = get_int_safe(request.POST.get('nro_planilla'))
        variedad = get_int_safe(request.POST.get('variedad_id'), -1)

        if planilla == 0: return JsonResponse({'estado': 'Error', 'mensaje': 'Debe guardar el Encabezado primero.'})
        
        try:
            conexion = obtener_conexion_maestra()
            cursor = conexion.cursor()
            procesados = 0

            for key, value in request.POST.items():
                # Solo procesar cal_<numero> (porcentaje). Ignorar cal_cant_<numero>.
                if not key.startswith('cal_'):
                    continue
                resto = key[4:]  # quita "cal_"
                if not resto.isdigit():
                    continue  # ignora cal_cant_X
                if value.strip() == '':
                    continue

                secuencia = int(resto)
                porcentaje = float(value.replace(',', '.'))

                # 1) Guardar el porcentaje usando el SP existente
                cursor.execute('{CALL "DBA"."Movil_Recep_Actuliza_DetalleCalibre"(?, ?, ?, ?, ?, ?, ?)}',
                               (cliente, planta, planilla, especie_id, variedad, secuencia, porcentaje))

                # 2) Guardar la cantidad de frutos (cidc_cantid) con UPDATE directo.
                # El SP del jefe solo actualiza cidc_porcen; para la cantidad
                # se hace UPDATE a la misma fila.
                cantidad_str = request.POST.get(f'cal_cant_{secuencia}', '').strip()
                if cantidad_str != '':
                    try:
                        cantidad = int(float(cantidad_str.replace(',', '.')))
                        cursor.execute(
                            'UPDATE "DBA"."ctlcalinspdistribcaldet" '
                            'SET cidc_cantid = ? '
                            'WHERE clie_codigo = ? AND plde_codigo = ? AND ccre_numero = ? '
                            'AND espe_codigo = ? AND ccdc_secuen = ?',
                            (cantidad, cliente, planta, planilla, int(especie_id), secuencia)
                        )
                    except Exception as e_cant:
                        print(f"⚠️ No se pudo guardar cantidad para calibre {secuencia}: {e_cant}")

                procesados += 1

            if procesados == 0: return JsonResponse({'estado': 'Error', 'mensaje': 'No se enviaron calibres.'})
            conexion.commit()
            conexion.close()
            return JsonResponse({'estado': 'Exito', 'mensaje': '✅ ¡Calibres guardados correctamente!'})
        except Exception as e: return JsonResponse({'estado': 'Error', 'mensaje': str(e)})
    return JsonResponse({'estado': 'Error', 'mensaje': 'Método no válido'})

def guardar_defectos(request, especie_id):
    """
    ✅ VERSIÓN MEJORADA - Con validaciones y manejo robusto de errores
    """
    if request.method == 'POST':
        cliente = get_int_safe(request.POST.get('exportador_id'))
        planta = get_int_safe(request.POST.get('planta_id'))
        planilla = get_int_safe(request.POST.get('nro_planilla'))
        
        if planilla == 0: 
            return JsonResponse({'estado': 'Error', 'mensaje': '⚠️ Debe guardar el Encabezado primero.'})

        if not cliente or not planta:
            return JsonResponse({'estado': 'Error', 'mensaje': '⚠️ Faltan cliente o planta.'})

        try:
            conexion = obtener_conexion_maestra()
            cursor = conexion.cursor()

            # Recolectar datos como listas
            factores = request.POST.getlist('defectos_factor')
            cod_defectos = request.POST.getlist('defectos_codigo')
            cant1_list = request.POST.getlist('defectos_cant1')
            porc1_list = request.POST.getlist('defectos_porc1')
            cant2_list = request.POST.getlist('defectos_cant2')
            porc2_list = request.POST.getlist('defectos_porc2')
            cantcom_list = request.POST.getlist('defectos_cantcom')
            porccom_list = request.POST.getlist('defectos_porccom')
            totales_list = request.POST.getlist('defectos_total')

            def safe_float(v):
                """Convierte string a float de forma segura, con redondeo a 2 decimales"""
                if not v or v.strip() == '': 
                    return 0.0
                try: 
                    val = float(str(v).replace(',', '.'))
                    return round(val, 2)  # ⭐ IMPORTANTE: Redondear
                except: 
                    return 0.0

            # Validar que hay datos
            if len(cod_defectos) == 0:
                return JsonResponse({'estado': 'Error', 'mensaje': '⚠️ No hay defectos para guardar.'})

            procesados = 0
            errores = []

            # Procesar cada fila
            for i in range(len(cod_defectos)):
                try:
                    factor = int(factores[i]) if factores[i] else 0
                    defecto = int(cod_defectos[i]) if cod_defectos[i] else 0
                    
                    # Validaciones de rango
                    if defecto == 0:
                        errores.append(f"Fila {i+1}: Defecto inválido")
                        continue
                    
                    c1 = safe_float(cant1_list[i] if i < len(cant1_list) else 0)
                    p1 = safe_float(porc1_list[i] if i < len(porc1_list) else 0)
                    c2 = safe_float(cant2_list[i] if i < len(cant2_list) else 0)
                    p2 = safe_float(porc2_list[i] if i < len(porc2_list) else 0)
                    ccom = safe_float(cantcom_list[i] if i < len(cantcom_list) else 0)
                    pcom = safe_float(porccom_list[i] if i < len(porccom_list) else 0)
                    tot = safe_float(totales_list[i] if i < len(totales_list) else 0)

                    # Llamar SP (Opción 2 = Grabar)
                    cursor.execute(
                        '{CALL "DBA"."Movil_Recep_Defectos"(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)}',
                        (2, cliente, planta, planilla, int(especie_id), 
                         factor, defecto, c1, p1, c2, p2, ccom, pcom, tot)
                    )
                    procesados += 1
                except Exception as e:
                    errores.append(f"Fila {i+1}: {str(e)}")
                    continue

            conexion.commit()
            conexion.close()

            if errores:
                msg = f'⚠️ Guardados: {procesados}, Errores: {len(errores)}. ' + ' | '.join(errores[:3])
                return JsonResponse({'estado': 'Parcial', 'mensaje': msg})
            
            return JsonResponse({
                'estado': 'Exito', 
                'mensaje': f'✅ ¡{procesados} defectos guardados exitosamente!'
            })

        except Exception as e: 
            print(f"❌ ERROR EN guardar_defectos:\n{traceback.format_exc()}")
            return JsonResponse({'estado': 'Error', 'mensaje': f'❌ Error Sybase: {str(e)}'})
    
    return JsonResponse({'estado': 'Error', 'mensaje': 'Método no válido'})

def guardar_evaluaciones(request, especie_id):
    """
    ✅ VERSIÓN MEJORADA - Con validación de rango
    """
    if request.method == 'POST':
        cliente = get_int_safe(request.POST.get('exportador_id'))
        planta = get_int_safe(request.POST.get('planta_id'))
        planilla = get_int_safe(request.POST.get('nro_planilla'))
        
        if planilla == 0: 
            return JsonResponse({'estado': 'Error', 'mensaje': '⚠️ Debe guardar el Encabezado primero.'})

        cod_eval = get_int_safe(request.POST.get('cod_evaluacion'), 1)
        
        # Convertir valor con seguridad
        try: 
            valor = float(str(request.POST.get('valor_estimacion', '0')).replace(',', '.'))
            valor = round(valor, 2)  # ⭐ Redondear
            
            # Validar rango (0-100)
            if valor < 0 or valor > 100:
                return JsonResponse({
                    'estado': 'Error', 
                    'mensaje': '⚠️ El porcentaje debe estar entre 0 y 100.'
                })
        except: 
            valor = 0.0

        try:
            conexion = obtener_conexion_maestra()
            cursor = conexion.cursor()
            
            # Opción 2 = Grabar
            cursor.execute(
                '{CALL "DBA"."Movil_Recep_Gestiona_Evaluaciones"(?, ?, ?, ?, ?, ?, ?)}',
                (2, cliente, planta, planilla, int(especie_id), cod_eval, valor)
            )
            
            conexion.commit()
            conexion.close()
            
            return JsonResponse({
                'estado': 'Exito', 
                'mensaje': f'✅ ¡Estimación {valor}% guardada!'
            })
        except Exception as e: 
            print(f"❌ ERROR EN guardar_evaluaciones:\n{traceback.format_exc()}")
            return JsonResponse({'estado': 'Error', 'mensaje': f'❌ Error: {str(e)}'})
    
    return JsonResponse({'estado': 'Error', 'mensaje': 'Método no válido'})

def guardar_liberacion(request, especie_id):
    if request.method == 'POST':
        cliente = get_int_safe(request.POST.get('exportador_id'))
        planta = get_int_safe(request.POST.get('planta_id'))
        planilla = get_int_safe(request.POST.get('nro_planilla'))
        
        if planilla == 0: 
            return JsonResponse({'estado': 'Error', 'mensaje': '⚠️ Debe guardar el Encabezado primero.'})

        # Compatible tanto con 'reslot_radio' como con 'ccre_reslot'
        estado_raw = request.POST.get('ccre_reslot') or request.POST.get('reslot_radio') or ''
        estado_letra = seguro_texto(estado_raw).upper()
        
        if estado_letra not in ['A', 'R', '1', '2']:
            return JsonResponse({'estado': 'Error', 'mensaje': '⚠️ Debe seleccionar Aprobado o Rechazado.'})
        
        # 1=Aprobado ('A'), 2=Rechazado ('R')
        if estado_letra in ['A', '1']:
            estado_num = 1
            estado_letra = 'A'
        else:
            estado_num = 2
            estado_letra = 'R'

        observacion = seguro_texto(request.POST.get('ccre_observ') or request.POST.get('observacion') or '')[:600]

        # 📸 La foto de evidencia ya NO viaja pegada a este guardado: ahora se sube
        # aparte y al toque con subir_evidencia() / se ve y borra con
        # listar_evidencias() y borrar_evidencia(), sin depender de este botón.

        try:
            conexion = obtener_conexion_maestra()
            cursor = conexion.cursor()

            cursor.execute(
                '{CALL "DBA"."Movil_Recep_Gestiona_Liberacion"(?, ?, ?, ?, ?, ?)}',
                (2, cliente, planta, planilla, estado_num, observacion)
            )
            conexion.commit()
            conexion.close()

            estado_txt = "Producto Liberado ✅" if estado_letra == 'A' else "Producto Objetado ❌"
            return JsonResponse({'estado': 'Exito', 'mensaje': f'✅ ¡Lote {estado_txt}!'})
        except Exception as e:
            return JsonResponse({'estado': 'Error', 'mensaje': f'❌ Error: {str(e)}'})

    return JsonResponse({'estado': 'Error', 'mensaje': 'Método no válido'})


# ==============================================================
# EVIDENCIA FOTOGRÁFICA: ahora se puede cargar MÁS DE UNA foto por
# planilla, verlas todas y borrar la(s) que sobren. Cada foto es una
# fila independiente en "ctlcalrecepcionfrutasenca_imagenes"
# (ccri_codigo autoincremental = su identificador único).
# ==============================================================

def subir_evidencia(request, especie_id):
    """Agrega UNA foto más a la planilla (no reemplaza las anteriores)."""
    if request.method != 'POST':
        return JsonResponse({'estado': 'Error', 'mensaje': 'Método no válido'})

    cliente = get_int_safe(request.POST.get('exportador_id'))
    planta = get_int_safe(request.POST.get('planta_id'))
    planilla = get_int_safe(request.POST.get('nro_planilla'))

    if planilla == 0:
        return JsonResponse({'estado': 'Error', 'mensaje': '⚠️ Debe guardar el Encabezado primero.'})

    foto = request.FILES.get('evidencia_foto')
    if not foto:
        return JsonResponse({'estado': 'Error', 'mensaje': '⚠️ No se recibió ninguna foto.'})

    try:
        contenido = foto.read()
        nombre_bd = (foto.name or 'evidencia.jpg')[:40]
        hoy = date.today()

        conexion = obtener_conexion_maestra()
        cursor = conexion.cursor()
        cursor.execute(
            'INSERT INTO "DBA"."ctlcalrecepcionfrutasenca_imagenes" '
            '("clie_codigo", "plde_codigo", "ccre_numero", "espe_codigo", '
            '"ccri_imagen", "ccri_nomarc", "ccri_estado", "ccre_feccar") '
            'VALUES (?, ?, ?, ?, ?, ?, 1, ?)',
            (cliente, planta, planilla, int(especie_id), pyodbc.Binary(contenido), nombre_bd, hoy)
        )
        # Recuperamos el código autoincremental recién asignado para esta fila.
        cursor.execute('SELECT @@IDENTITY')
        row_id = cursor.fetchone()
        codigo_nuevo = int(row_id[0]) if row_id and row_id[0] is not None else None

        conexion.commit()
        conexion.close()

        evidencia = None
        if codigo_nuevo is not None:
            evidencia = {
                'codigo': codigo_nuevo,
                'nombre': nombre_bd,
                'fecha': hoy.strftime('%d-%m-%Y'),
                'url': f'/api/imagen-evidencia/{especie_id}/?codigo={codigo_nuevo}&cliente={cliente}&planta={planta}&planilla={planilla}'
            }

        return JsonResponse({'estado': 'Exito', 'mensaje': '✅ Foto agregada.', 'evidencia': evidencia})
    except Exception as e:
        print(f"❌ ERROR EN subir_evidencia:\n{traceback.format_exc()}")
        return JsonResponse({'estado': 'Error', 'mensaje': f'❌ Error: {str(e)}'})


def listar_evidencias(request, especie_id):
    """Lista las fotos VIGENTES (no borradas) de una planilla. Las borradas no se listan."""
    cliente = get_int_safe(request.GET.get('cliente'))
    planta = get_int_safe(request.GET.get('planta'))
    planilla = get_int_safe(request.GET.get('planilla'))

    if planilla == 0:
        return JsonResponse({'estado': 'Exito', 'evidencias': []})

    try:
        conexion = obtener_conexion_maestra()
        cursor = conexion.cursor()
        cursor.execute(
            'SELECT "ccri_codigo", "ccri_nomarc", "ccre_feccar" '
            'FROM "DBA"."ctlcalrecepcionfrutasenca_imagenes" '
            'WHERE "clie_codigo" = ? AND "plde_codigo" = ? AND "ccre_numero" = ? '
            'AND "espe_codigo" = ? AND "ccri_estado" = 1 '
            'ORDER BY "ccri_codigo" DESC',
            (cliente, planta, planilla, int(especie_id))
        )
        evidencias = []
        for f in cursor.fetchall():
            codigo = int(f[0])
            evidencias.append({
                'codigo': codigo,
                'nombre': seguro_texto(f[1]),
                'fecha': str(f[2])[:10] if f[2] else '',
                'url': f'/api/imagen-evidencia/{especie_id}/?codigo={codigo}&cliente={cliente}&planta={planta}&planilla={planilla}'
            })
        conexion.close()
        return JsonResponse({'estado': 'Exito', 'evidencias': evidencias})
    except Exception as e:
        print(f"❌ ERROR EN listar_evidencias:\n{traceback.format_exc()}")
        return JsonResponse({'estado': 'Error', 'mensaje': str(e)})


def borrar_evidencia(request, especie_id):
    """
    Borrado lógico de UNA foto puntual, TODO dentro de la misma tabla que ya
    armaron ("ctlcalrecepcionfrutasenca_imagenes"), sin agregar columnas ni
    usar otra tabla:
      - ccri_estado pasa a 2 (borrada), igual que antes.
      - ccre_feccar (que mientras la foto está vigente = 1 guarda la fecha en
        que se cargó) se reescribe con la fecha/hora en que se borra. Una vez
        borrada la foto, esa columna deja de importar como "fecha de carga"
        y pasa a ser la "fecha de eliminación" de esa fila puntual — así
        queda el dato guardado sin tocar la estructura de la tabla.

    Filtramos también por ccri_codigo para borrar SOLO esta foto puntual, no
    todas las de la planilla (una planilla puede tener varias evidencias).
    """
    if request.method != 'POST':
        return JsonResponse({'estado': 'Error', 'mensaje': 'Método no válido'})

    cliente = get_int_safe(request.POST.get('exportador_id'))
    planta = get_int_safe(request.POST.get('planta_id'))
    planilla = get_int_safe(request.POST.get('nro_planilla'))
    codigo = get_int_safe(request.POST.get('ccri_codigo'))

    if codigo == 0:
        return JsonResponse({'estado': 'Error', 'mensaje': '⚠️ Falta indicar qué foto borrar.'})

    try:
        conexion = obtener_conexion_maestra()
        cursor = conexion.cursor()

        # 🟢 Soft delete en la MISMA tabla: marcamos ccri_estado=2 y
        # reescribimos ccre_feccar con la fecha de borrado.
        cursor.execute('''
            UPDATE "DBA"."ctlcalrecepcionfrutasenca_imagenes"
            SET ccri_estado = 2,
                ccre_feccar = GETDATE()
            WHERE clie_codigo = ?
              AND plde_codigo = ?
              AND ccre_numero = ?
              AND espe_codigo = ?
              AND ccri_codigo = ?
              AND ccri_estado = 1
        ''', (cliente, planta, planilla, int(especie_id), codigo))

        filas_afectadas = cursor.rowcount
        conexion.commit()
        conexion.close()

        if filas_afectadas == 0:
            return JsonResponse({'estado': 'Error', 'mensaje': 'No se encontró esa foto (¿ya estaba borrada?).'})

        return JsonResponse({'estado': 'Exito', 'mensaje': 'Evidencia eliminada correctamente de la base de datos.'})
    except Exception as e:
        print(f"❌ ERROR EN borrar_evidencia:\n{traceback.format_exc()}")
        return JsonResponse({'estado': 'Error', 'mensaje': f'❌ Error al borrar en Sybase: {str(e)}'})


def obtener_planillas_creadas(request, especie_id):
    cliente = get_int_safe(request.GET.get('cliente'))
    planta = get_int_safe(request.GET.get('planta'))
    planillas = []
    try:
        conexion = obtener_conexion_maestra()
        cursor = conexion.cursor()
        cursor.execute('SELECT ccre_numero, lote_codigo, ccre_fecrec, lote_totnet FROM "DBA"."ctlcalrecepcionfrutasenca" WHERE clie_codigo=? AND plde_codigo=? AND espe_codigo=? ORDER BY ccre_numero DESC', (cliente, planta, especie_id))
        for f in cursor.fetchall():
            lote_val = str(f[1]).strip() if f[1] is not None else ''
            if lote_val in ['None', '']: lote_val = 'Sin Lote'
            planillas.append({'planilla': int(f[0]), 'lote': lote_val, 'fecha': str(f[2])[:10] if f[2] else '-', 'kilos': float(f[3]) if f[3] else 0.0})
        conexion.close()
        return JsonResponse({'estado': 'Exito', 'planillas': planillas})
    except Exception as e: return JsonResponse({'estado': 'Error', 'mensaje': str(e)})

def obtener_lote_por_planilla(request, especie_id):
    planilla = get_int_safe(request.GET.get('planilla'))
    try:
        conexion = obtener_conexion_maestra()
        cursor = conexion.cursor()
        cursor.execute('SELECT clie_codigo, plde_codigo, lote_codigo, prod_codigo, prbr_codpre, prcc_codigo, vari_codigo, ccre_feccos, ccre_fecrec, ccre_noguia, ccre_tamlot, lote_totnet FROM "DBA"."ctlcalrecepcionfrutasenca" WHERE ccre_numero=? AND espe_codigo=?', (planilla, especie_id))
        row = cursor.fetchone()
        if not row: conexion.close(); return JsonResponse({'estado': 'Error', 'mensaje': 'Planilla no encontrada'})

        cliente, planta = seguro_texto(row[0]), seguro_texto(row[1])
        lote_real = str(row[2]).strip() if row[2] is not None else ''
        if lote_real == 'None': lote_real = ''
        productor, predio, cuartel, variedad = seguro_texto(row[3]), seguro_texto(row[4]), seguro_texto(row[5]), seguro_texto(row[6])

        # Hora de llegada guardada para ESTA planilla puntual (consulta aparte
        # por nombre de columna, igual que en verificar_planilla_lote).
        hora_llegada = ''
        try:
            cursor.execute(
                'SELECT * FROM "DBA"."ctlcalrecepcionfrutasenca" '
                'WHERE ccre_numero=? AND espe_codigo=?', (planilla, especie_id)
            )
            row_hora = cursor.fetchone()
            if row_hora:
                columnas_hora = [d[0] for d in cursor.description]
                hora_llegada = _buscar_hora_llegada(columnas_hora, row_hora)
        except Exception as e:
            logger.warning(f"[hora_llegada] Error buscando hora en obtener_lote_por_planilla: {e}")

        lista_prod, lista_pred, lista_cuar = [], [], []
        if cliente:
            try:
                cursor.execute('{CALL "DBA"."Movil_muestra_productores"(?)}', int(cliente))
                for f in cursor.fetchall(): lista_prod.append({'id': seguro_texto(f[0]), 'nombre': f"[{seguro_texto(f[0])}] {f[1]}"})
            except: pass
        if productor:
            try:
                cursor.execute('{CALL "DBA"."Movil_muestra_predios"(?)}', int(productor))
                for f in cursor.fetchall(): lista_pred.append({'id': seguro_texto(f[0]), 'nombre': f"[{seguro_texto(f[0])} / {str(f[2]).strip()}] {f[1]}"})
            except: pass
        if productor and predio:
            try:
                cursor.execute('{CALL "DBA"."Movil_muestra_cuarteles"(?, ?, ?)}', (int(productor), int(predio), int(especie_id)))
                for f in cursor.fetchall(): lista_cuar.append({'id': seguro_texto(f[0]), 'nombre': f"[{seguro_texto(f[0])}] SDP: {str(f[2]).strip()}"})
            except: pass

        conexion.close()
        return JsonResponse({'estado': 'Exito', 'datos': { 'cliente': cliente, 'planta': planta, 'lote': lote_real, 'productor': productor, 'predio': predio, 'cuartel': cuartel, 'variedad': variedad, 'f_cosecha': str(row[7])[:10] if row[7] else '', 'f_recepcion': str(row[8])[:10] if row[8] else '', 'guia': str(row[9]).strip() if row[9] else '', 'bultos': int(row[10]) if row[10] else 0, 'kg': float(row[11]) if row[11] else 0.0, 'hora_llegada': hora_llegada }, 'listas': {'productores': lista_prod, 'predios': lista_pred, 'cuarteles': lista_cuar}})
    except Exception as e: return JsonResponse({'estado': 'Error', 'mensaje': str(e)})

def obtener_detalle_planilla(request, planilla_id):
    especie_id = request.GET.get('especie_id')
    cliente = get_int_safe(request.GET.get('cliente'))
    planta = get_int_safe(request.GET.get('planta'))
    variedad = get_int_safe(request.GET.get('variedad'), -1)

    detalles, calibres = [], []
    defectos_list = []
    evaluacion_dict = {'codigo': 1, 'valor': ''}
    liberacion_dict = {'estado': '', 'observacion': ''}

    try:
        conexion = obtener_conexion_maestra()
        cursor = conexion.cursor()
        
        cursor.execute('{CALL "DBA"."Movil_Recep_detalleColor"(?, ?, ?, ?)}', (cliente, planta, planilla_id, especie_id))
        for f in cursor.fetchall():
            if len(f) >= 7:
                cod, desc, val = f[4], f[5], f[6]
                if cod is not None:
                    try: valor_final = float(val) if val is not None else ''
                    except: valor_final = ''
                    detalles.append({'codigo': int(cod), 'nombre': str(desc).strip() if desc else f"Color {cod}", 'valor': valor_final})
        
        cursor.execute('SELECT ccdc_secuen, vaca_calibr, ccdc_milime, ccdc_calibr FROM "DBA"."ctlcaldistcalibre" WHERE espe_codigo = ? ORDER BY ccdc_ordena', (int(especie_id),))
        maestros = cursor.fetchall()
        
        # #7: traemos TAMBIEN la cantidad (cidc_cantid), no solo el %, para poder recuperar
        # las cajas de cantidad en pantalla (igual que ya lo hace el PDF).
        cursor.execute('SELECT ccdc_secuen, cidc_porcen, cidc_cantid FROM "DBA"."ctlcalinspdistribcaldet" WHERE clie_codigo=? AND plde_codigo=? AND ccre_numero=? AND espe_codigo=?', (cliente, planta, planilla_id, int(especie_id)))
        guardados = {}
        for row in cursor.fetchall():
            pct = float(row[1]) if row[1] is not None else ''
            cant = int(row[2]) if row[2] is not None else 0
            guardados[int(row[0])] = {'porcentaje': pct, 'cantidad': cant}

        calibres_unicos = {}
        for m in maestros:
            secuen = int(m[0])
            if secuen not in calibres_unicos: 
                nombre_base = seguro_texto(m[1])
                rango = seguro_texto(m[3]) if len(m) > 3 and m[3] else seguro_texto(m[2])
                if not rango or rango == nombre_base: rango = ""
                
                # NOTA: Si Sybase entrega el rango vacio o '0', se muestra solo el nombre base.
                # Si el DBA rellena ccdc_milime o ccdc_calibr en el maestro, aparecera automatico.

                display_nombre = f"{nombre_base} ({rango})" if rango else nombre_base
                g = guardados.get(secuen, {'porcentaje': '', 'cantidad': 0})
                calibres_unicos[secuen] = {'codigo': secuen, 'nombre': display_nombre, 'valor': g['porcentaje'], 'cantidad': g['cantidad']}
        calibres = list(calibres_unicos.values())

        def safe_float(v):
            # Ocultar ceros de la BD para mostrar vacío en la UI
            if v is None: return ''
            try: 
                val = float(v)
                return '' if val == 0 else val
            except: return ''

        try:
            # LLAMADO 1: Traer defectos guardados de esta planilla
            cursor.execute('{CALL "DBA"."Movil_Recep_Defectos"(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)}', (1, cliente, planta, int(planilla_id), int(especie_id), 0, 0, 0, 0, 0, 0, 0, 0, 0))
            filas_defectos = cursor.fetchall()
            
            # LLAMADO 2: Si no hay datos, traer la matriz maestra vacía (planilla=0)
            if not filas_defectos:
                cursor.execute('{CALL "DBA"."Movil_Recep_Defectos"(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)}', (1, cliente, planta, 0, int(especie_id), 0, 0, 0, 0, 0, 0, 0, 0, 0))
                filas_defectos = cursor.fetchall()

            for f in filas_defectos:
                defectos_list.append({
                    'factor': int(f[0]), 
                    'defecto': int(f[1]), 
                    'nombre_defecto': str(f[2]).strip() if f[2] else f"Defecto #{int(f[1])}",
                    'cant1': safe_float(f[3]), 'porc1': safe_float(f[4]),
                    'cant2': safe_float(f[5]), 'porc2': safe_float(f[6]),
                    'cantcom': safe_float(f[7]), 'porccom': safe_float(f[8]),
                    'total': safe_float(f[9])
                })
        except Exception: 
            try: cursor.rollback()
            except: pass

        try:
            cursor.execute('{CALL "DBA"."Movil_Recep_Gestiona_Evaluaciones"(?, ?, ?, ?, ?, ?, ?)}', (1, cliente, planta, int(planilla_id), int(especie_id), 0, 0))
            eval_row = cursor.fetchone()
            if eval_row: evaluacion_dict = {'codigo': int(eval_row[0]), 'valor': safe_float(eval_row[1])}
            print(f"🔍 DEBUG EVAL: planilla={planilla_id}, eval_row={eval_row}, dict={evaluacion_dict}")
        except Exception as e: 
            print(f"🔴 ERROR EVAL SP: {e}")
            try: cursor.rollback()
            except: pass

        try:
            cursor.execute('{CALL "DBA"."Movil_Recep_Gestiona_Liberacion"(?, ?, ?, ?, ?, ?)}', (1, cliente, planta, int(planilla_id), '', ''))
            lib_row = cursor.fetchone()
            if lib_row:
                # ccre_reslot es numérico: 1=Liberado(A), 2=Objetado(R)
                estado_raw = seguro_texto(lib_row[0])
                if estado_raw == '1': estado_raw = 'A'
                elif estado_raw == '2': estado_raw = 'R'
                liberacion_dict = {'estado': estado_raw, 'observacion': seguro_texto(lib_row[1])}
            print(f"🔍 DEBUG LIB: planilla={planilla_id}, lib_row={lib_row}, dict={liberacion_dict}")
        except Exception as e:
            print(f"🔴 ERROR LIB SP: {e}")
            try: cursor.rollback()
            except: pass

        conexion.close()
        return JsonResponse({'estado': 'Exito', 'detalles': detalles, 'calibres': calibres, 'defectos': defectos_list, 'evaluacion': evaluacion_dict, 'liberacion': liberacion_dict})
    except Exception as e: return JsonResponse({'estado': 'Error', 'mensaje': str(e)})


def obtener_imagen_evidencia(request, especie_id):
    """
    Devuelve el binario de UNA foto de evidencia puntual (por su "ccri_codigo"),
    para mostrarla como <img src="..."> en la galería. Solo se sirve si sigue
    vigente (ccri_estado=1); una foto borrada devuelve 404, ya no se muestra.
    """
    codigo = get_int_safe(request.GET.get('codigo'))
    cliente = get_int_safe(request.GET.get('cliente'))
    planta = get_int_safe(request.GET.get('planta'))
    planilla_id = get_int_safe(request.GET.get('planilla'))

    if codigo == 0:
        return HttpResponse("Falta el codigo de la evidencia.", status=400)

    try:
        conexion = obtener_conexion_maestra()
        cursor = conexion.cursor()
        cursor.execute(
            'SELECT "ccri_imagen", "ccri_nomarc" FROM "DBA"."ctlcalrecepcionfrutasenca_imagenes" '
            'WHERE "ccri_codigo" = ? AND "clie_codigo" = ? AND "plde_codigo" = ? '
            'AND "ccre_numero" = ? AND "espe_codigo" = ? AND "ccri_estado" = 1',
            (codigo, cliente, planta, planilla_id, int(especie_id))
        )
        row = cursor.fetchone()
        conexion.close()

        if not row or not row[0]:
            return HttpResponse("Esa evidencia no existe o fue borrada.", status=404)

        contenido = bytes(row[0])
        nombre = seguro_texto(row[1]) or 'evidencia.jpg'
        ext = nombre.split('.')[-1].lower() if '.' in nombre else 'jpg'
        content_type = 'image/png' if ext == 'png' else 'image/jpeg'

        return HttpResponse(contenido, content_type=content_type)
    except Exception as e:
        return HttpResponse(f"Error obteniendo evidencia: {e}", status=500)


def _obtener_imagenes_evidencia_pdf(cliente, planta, planilla_id, especie_id):
    """
    Trae TODAS las fotos vigentes (ccri_estado=1) de una planilla, con su
    binario y su fecha de carga, para incrustarlas en el PDF. Se ordenan por
    "ccri_codigo" ASC para que salgan en el mismo orden en que se cargaron
    (la más antigua primero). No se listan las borradas.
    Devuelve una lista de dicts: {'imagen': bytes, 'nombre': str, 'fecha': str}.
    Si algo falla, devuelve lista vacía (no debe romper la generación del PDF).
    """
    if planilla_id == 0:
        return []
    try:
        conexion = obtener_conexion_maestra()
        cursor = conexion.cursor()
        cursor.execute(
            'SELECT "ccri_imagen", "ccri_nomarc", "ccre_feccar" '
            'FROM "DBA"."ctlcalrecepcionfrutasenca_imagenes" '
            'WHERE "clie_codigo" = ? AND "plde_codigo" = ? AND "ccre_numero" = ? '
            'AND "espe_codigo" = ? AND "ccri_estado" = 1 '
            'ORDER BY "ccri_codigo" ASC',
            (cliente, planta, planilla_id, int(especie_id))
        )
        imagenes = []
        for f in cursor.fetchall():
            if not f[0]:
                continue
            fecha_raw = str(f[2])[:10] if f[2] else ''
            fecha_fmt = ''
            if fecha_raw and '-' in fecha_raw:
                partes = fecha_raw.split('-')
                if len(partes) == 3 and len(partes[0]) == 4:
                    fecha_fmt = f"{partes[2]}-{partes[1]}-{partes[0]}"
            imagenes.append({
                'imagen': bytes(f[0]),
                'nombre': seguro_texto(f[1]) or 'evidencia.jpg',
                'fecha': fecha_fmt or fecha_raw or '-',
            })
        conexion.close()
        return imagenes
    except Exception:
        print(f"❌ ERROR EN _obtener_imagenes_evidencia_pdf:\n{traceback.format_exc()}")
        return []


def verificar_planilla_lote(request, especie_id):
    cliente = get_int_safe(request.GET.get('cliente'))
    planta = get_int_safe(request.GET.get('planta'))
    lote_interno = get_int_safe(request.GET.get('lote_id'))
    variedad = get_int_safe(request.GET.get('variedad'), -1)

    try:
        conexion = obtener_conexion_maestra()
        cursor = conexion.cursor()
        cursor.execute('SELECT * FROM "DBA"."ctlcalrecepcionfrutasenca" WHERE clie_codigo=? AND plde_codigo=? AND lote_codigo=? AND espe_codigo=?', (cliente, planta, lote_interno, int(especie_id)))
        row = cursor.fetchone()

        if row:
            columnas = [d[0] for d in cursor.description]
            planilla_id_val = row[columnas.index('ccre_numero')]
            hora_llegada_val = _buscar_hora_llegada(columnas, row)
            conexion.close()
            return JsonResponse({'estado': 'Exito', 'planilla_id': planilla_id_val, 'hora_llegada': hora_llegada_val})
        
        colores_maestros = []
        cursor.execute('{CALL "DBA"."Movil_Recep_detalleColor"(?, ?, ?, ?)}', (cliente, planta, 0, int(especie_id)))
        for f in cursor.fetchall():
            if len(f) >= 7:
                cod, desc, val = f[4], f[5], f[6]
                try: valor_final = float(val) if val is not None else ''
                except: valor_final = ''
                if cod is not None:
                    colores_maestros.append({'codigo': int(cod), 'nombre': str(desc).strip() if desc else f"Color {cod}", 'valor': valor_final})
        
        cursor.execute('SELECT ccdc_secuen, vaca_calibr, ccdc_milime, ccdc_calibr FROM "DBA"."ctlcaldistcalibre" WHERE espe_codigo = ? ORDER BY ccdc_ordena', (int(especie_id),))
        calibres_unicos = {}
        for m in cursor.fetchall():
            secuen = int(m[0])
            if secuen not in calibres_unicos:
                nombre_base = seguro_texto(m[1])
                rango = seguro_texto(m[3]) if len(m) > 3 and m[3] else seguro_texto(m[2])
                if not rango or rango == nombre_base: rango = ""
                
                # NOTA: Si Sybase entrega el rango vacio o '0', se muestra solo el nombre base.
                # Si el DBA rellena ccdc_milime o ccdc_calibr en el maestro, aparecera automatico.

                display_nombre = f"{nombre_base} ({rango})" if rango else nombre_base
                calibres_unicos[secuen] = {'codigo': secuen, 'nombre': display_nombre, 'valor': ''}

        calibres_maestros = list(calibres_unicos.values())

        defectos_maestros = []
        try:
            cursor.execute('{CALL "DBA"."Movil_Recep_Defectos"(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)}', (1, cliente, planta, 0, int(especie_id), 0, 0, 0, 0, 0, 0, 0, 0, 0))
            for f in cursor.fetchall():
                defectos_maestros.append({
                    'factor': int(f[0]), 
                    'defecto': int(f[1]), 
                    'nombre_defecto': str(f[2]).strip() if f[2] else f"Defecto #{int(f[1])}",
                    'cant1': '', 'porc1': '', 'cant2': '', 'porc2': '', 'cantcom': '', 'porccom': '', 'total': ''
                })
        except: 
            try: cursor.rollback()
            except: pass

        conexion.close()
        return JsonResponse({'estado': 'Nuevo', 'colores': colores_maestros, 'calibres': calibres_maestros, 'defectos': defectos_maestros}) 
    except Exception as e: return JsonResponse({'estado': 'Error', 'mensaje': str(e)})

def anular_planilla(request, especie_id):
    return JsonResponse({'estado': 'Exito', 'mensaje': 'Planilla anulada'})

def logout_app(request):
    request.session.flush()
    return redirect('login_app')

# ==============================================================
# GENERACION DE PDF 
# Uso: /api/pdf-planilla/<especie_id>/?planilla=<numero>&cliente=..&planta=..&variedad=..
# ==============================================================
def generar_pdf_planilla(request, especie_id):
    planilla_id = get_int_safe(request.GET.get('planilla'))
    cliente = get_int_safe(request.GET.get('cliente'))
    planta = get_int_safe(request.GET.get('planta'))
    variedad = get_int_safe(request.GET.get('variedad'), -1)

    if planilla_id == 0:
        return HttpResponse("Falta el numero de planilla.", status=400)

    enc = _datos_encabezado_pdf(planilla_id, especie_id)
    if enc.get('error'):
        return HttpResponse(enc['error'], status=enc.get('status', 500))
    if cliente == 0: cliente = enc['cliente']
    if planta == 0: planta = enc['planta']
    if variedad == -1: variedad = enc['variedad_id']

    detalle = obtener_detalle_planilla_dict(planilla_id, especie_id, cliente, planta, variedad)
    if detalle.get('estado') != 'Exito':
        return HttpResponse(f"Error obteniendo detalle: {detalle.get('mensaje', 'desconocido')}", status=500)

    def _num(v):
        try: return float(v)
        except (TypeError, ValueError): return 0.0

    # 🔍 Búsqueda flexible de la imagen en static/img/
    logo_path = None
    posibles_nombres = [
        'san_osvaldo.jpeg',
        'san_osvaldo.jpg',
        'san_osvaldo.png',
        'imagen poner pdf.jpeg'
    ]
    for nombre in posibles_nombres:
        ruta_test = os.path.join(settings.BASE_DIR, 'static', 'img', nombre)
        if os.path.exists(ruta_test):
            logo_path = ruta_test
            break

    datos = {
        'nombre_fruta': enc['nombre_fruta'],
        'planilla_id': planilla_id,
        'especie_id': especie_id,
        'logo_path': logo_path,
        'encabezado': {
            'planta': planta,
            'variedad': enc['nombre_var'],
            'productor': enc['nombre_prod'],
            'huerto': enc['nombre_huerto'],
            'sdp': enc['nombre_sdp'],
            'f_cosecha': enc['f_cosecha'],
            'f_recepcion': enc['f_recepcion'],
            'f_inspeccion': enc['f_recepcion'],
            'guia': enc['guia'],
            'tam_lote': enc['tam_lote'],
            'kg_neto': enc['kg_neto'],
            'mercado': enc['mercado'],
            'hora_llegada': enc.get('hora_llegada', ''),
        },
        'colores': [(c['nombre'], _num(c['valor'])) for c in detalle.get('detalles', [])],
        'calibres': [(c['nombre'], _num(c['valor']), int(c.get('cantidad') or 0)) for c in detalle.get('calibres', [])],
        'defectos': [{
            'factor': d['factor'], 'nombre': d['nombre_defecto'],
            'p1': _num(d['porc1']), 'p2': _num(d['porc2']), 'pcom': _num(d['porccom']),
        } for d in detalle.get('defectos', [])],
        'estimacion': _num(detalle.get('evaluacion', {}).get('valor', 0)),
        'liberacion': detalle.get('liberacion', {}).get('estado', ''),
        'observacion': detalle.get('liberacion', {}).get('observacion', ''),
        # 📸 Todas las fotos de evidencia vigentes de esta planilla, para que
        # salgan en una página aparte al final del PDF.
        'imagenes': _obtener_imagenes_evidencia_pdf(cliente, planta, planilla_id, especie_id),
    }

    pdf_bytes = construir_pdf_planilla(datos)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    nombre_limpio = ''.join(ch for ch in enc['nombre_fruta'] if ch.isalnum()) or 'FRUTA'
    response['Content-Disposition'] = f'inline; filename="POE023_Planilla_{planilla_id}_{nombre_limpio}.pdf"'
    return response


def _datos_encabezado_pdf(planilla_id, especie_id):
    """Lee el encabezado de la planilla (datos que no vienen en el detalle)."""
    out = {
        'nombre_fruta': 'FRUTA', 'cliente': 0, 'planta': 0, 'variedad_id': -1,
        'nombre_prod': '-', 'nombre_huerto': '-', 'nombre_sdp': '-', 'nombre_var': '-',
        'lote': '', 'guia': '', 'f_cosecha': '-', 'f_recepcion': '-',
        'tam_lote': 0, 'kg_neto': 0.0, 'mercado': 1, 'hora_llegada': '',
    }
    try:
        conexion = obtener_conexion_maestra()
        cursor = conexion.cursor()

        cursor.execute('{CALL "DBA"."Movil_muestra_especies"()}')
        for f in cursor.fetchall():
            if str(f[0]) == str(especie_id):
                out['nombre_fruta'] = f[1].upper(); break

        cursor.execute(
            'SELECT clie_codigo, plde_codigo, lote_codigo, prod_codigo, prbr_codpre, '
            'prcc_codigo, vari_codigo, ccre_feccos, ccre_fecrec, ccre_noguia, '
            'ccre_tamlot, lote_totnet FROM "DBA"."ctlcalrecepcionfrutasenca" '
            'WHERE ccre_numero=? AND espe_codigo=?', (planilla_id, especie_id)
        )
        row = cursor.fetchone()
        if not row:
            conexion.close()
            return {'error': 'Planilla no encontrada.', 'status': 404}

        out['cliente'] = get_int_safe(row[0])
        out['planta'] = get_int_safe(row[1])
        out['variedad_id'] = get_int_safe(row[6], -1)
        out['lote'] = seguro_texto(row[2])
        out['guia'] = seguro_texto(row[9])
        out['f_cosecha'] = str(row[7])[:10] if row[7] else '-'
        out['f_recepcion'] = str(row[8])[:10] if row[8] else '-'

        # Hora de llegada: consulta aparte (por nombre de columna, no por
        # posicion) para no tocar los indices de la fila de arriba.
        try:
            cursor.execute(
                'SELECT * FROM "DBA"."ctlcalrecepcionfrutasenca" '
                'WHERE ccre_numero=? AND espe_codigo=?', (planilla_id, especie_id)
            )
            row_hora = cursor.fetchone()
            if row_hora:
                columnas_hora = [d[0] for d in cursor.description]
                out['hora_llegada'] = _buscar_hora_llegada(columnas_hora, row_hora)
        except Exception as e:
            logger.warning(f"[hora_llegada] Error buscando hora para PDF: {e}")
        out['tam_lote'] = get_int_safe(row[10])
        out['kg_neto'] = float(row[11]) if row[11] else 0.0
        out['mercado'] = 1

        prod_id, predio_id, cuartel_id, var_id = get_int_safe(row[3]), get_int_safe(row[4]), get_int_safe(row[5]), get_int_safe(row[6])
        try:
            cursor.execute('{CALL "DBA"."Movil_muestra_productores"(?)}', prod_id)
            for f in cursor.fetchall():
                if str(f[0]).split('.')[0].strip() == str(prod_id):
                    out['nombre_prod'] = f[1]; break
        except: pass
        try:
            cursor.execute('{CALL "DBA"."Movil_muestra_predios"(?)}', prod_id)
            for f in cursor.fetchall():
                if str(f[0]).split('.')[0].strip() == str(predio_id):
                    out['nombre_huerto'] = f[1]; break
        except: pass
        try:
            cursor.execute('{CALL "DBA"."Movil_muestra_cuarteles"(?, ?, ?)}', (prod_id, predio_id, int(especie_id)))
            for f in cursor.fetchall():
                if str(f[0]).split('.')[0].strip() == str(cuartel_id):
                    out['nombre_sdp'] = f"SDP: {seguro_texto(f[2])}"; break
        except: pass
        try:
            cursor.execute('{CALL "DBA"."Movil_muestra_Variedades"(?)}', especie_id)
            for f in cursor.fetchall():
                if str(f[0]).split('.')[0].strip() == str(var_id):
                    out['nombre_var'] = f[1]; break
        except: pass

        conexion.close()
        return out
    except Exception as e:
        return {'error': f'Error obteniendo encabezado de Sybase: {str(e)}', 'status': 500}


def obtener_detalle_planilla_dict(planilla_id, especie_id, cliente, planta, variedad=-1):
    """Wrapper que llama obtener_detalle_planilla y devuelve el dict directamente."""
    try:
        conexion = obtener_conexion_maestra()
        cursor = conexion.cursor()
        
        detalles, calibres = [], []
        defectos_list = []
        evaluacion_dict = {'codigo': 1, 'valor': ''}
        liberacion_dict = {'estado': '', 'observacion': ''}

        # COLORES (igual que antes)
        cursor.execute('{CALL "DBA"."Movil_Recep_detalleColor"(?, ?, ?, ?)}', (cliente, planta, planilla_id, especie_id))
        for f in cursor.fetchall():
            if len(f) >= 7:
                cod, desc, val = f[4], f[5], f[6]
                if cod is not None:
                    try: valor_final = float(val) if val is not None else ''
                    except: valor_final = ''
                    detalles.append({'codigo': int(cod), 'nombre': str(desc).strip() if desc else f"Color {cod}", 'valor': valor_final})
        
        # CALIBRES
        cursor.execute('SELECT ccdc_secuen, vaca_calibr, ccdc_milime, ccdc_calibr FROM "DBA"."ctlcaldistcalibre" WHERE espe_codigo = ? ORDER BY ccdc_ordena', (int(especie_id),))
        maestros = cursor.fetchall()
        
        cursor.execute('SELECT ccdc_secuen, cidc_porcen, cidc_cantid FROM "DBA"."ctlcalinspdistribcaldet" WHERE clie_codigo=? AND plde_codigo=? AND ccre_numero=? AND espe_codigo=?', (cliente, planta, planilla_id, int(especie_id)))
        guardados = {}
        for row in cursor.fetchall():
            pct = float(row[1]) if row[1] is not None else ''
            cant = int(row[2]) if row[2] is not None else 0
            guardados[int(row[0])] = {'porcentaje': pct, 'cantidad': cant}

        calibres_unicos = {}
        for m in maestros:
            secuen = int(m[0])
            if secuen not in calibres_unicos: 
                nombre_base = seguro_texto(m[1])
                rango = seguro_texto(m[3]) if len(m) > 3 and m[3] else seguro_texto(m[2])
                if not rango or rango == nombre_base: rango = ""
                
                # NOTA: Si Sybase entrega el rango vacio o '0', se muestra solo el nombre base.
                # Si el DBA rellena ccdc_milime o ccdc_calibr en el maestro, aparecera automatico.

                display_nombre = f"{nombre_base} ({rango})" if rango else nombre_base
                g = guardados.get(secuen, {'porcentaje': '', 'cantidad': 0})
                calibres_unicos[secuen] = {'codigo': secuen, 'nombre': display_nombre, 'valor': g['porcentaje'], 'cantidad': g['cantidad']}
        
        calibres = list(calibres_unicos.values())

        # DEFECTOS
        try:
            cursor.execute('{CALL "DBA"."Movil_Recep_Defectos"(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)}', (1, cliente, planta, int(planilla_id), int(especie_id), 0, 0, 0, 0, 0, 0, 0, 0, 0))
            filas_defectos = cursor.fetchall()
            
            if not filas_defectos:
                cursor.execute('{CALL "DBA"."Movil_Recep_Defectos"(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)}', (1, cliente, planta, 0, int(especie_id), 0, 0, 0, 0, 0, 0, 0, 0, 0))
                filas_defectos = cursor.fetchall()

            for f in filas_defectos:
                defectos_list.append({
                    'factor': int(f[0]), 
                    'defecto': int(f[1]), 
                    'nombre_defecto': str(f[2]).strip() if f[2] else f"Defecto #{int(f[1])}",
                    'cant1': '', 'porc1': float(f[4]) if f[4] else '',
                    'cant2': '', 'porc2': float(f[6]) if f[6] else '',
                    'cantcom': '', 'porccom': float(f[8]) if f[8] else '',
                    'total': ''
                })
        except Exception: pass

        # EVALUACION
        try:
            cursor.execute('{CALL "DBA"."Movil_Recep_Gestiona_Evaluaciones"(?, ?, ?, ?, ?, ?, ?)}', (1, cliente, planta, int(planilla_id), int(especie_id), 0, 0))
            eval_row = cursor.fetchone()
            if eval_row: evaluacion_dict = {'codigo': int(eval_row[0]), 'valor': float(eval_row[1]) if eval_row[1] else ''}
        except Exception: pass

        # LIBERACION
        try:
            cursor.execute('{CALL "DBA"."Movil_Recep_Gestiona_Liberacion"(?, ?, ?, ?, ?, ?)}', (1, cliente, planta, int(planilla_id), '', ''))
            lib_row = cursor.fetchone()
            if lib_row:
                estado_raw = seguro_texto(lib_row[0])
                if estado_raw == '1': estado_raw = 'A'
                elif estado_raw == '2': estado_raw = 'R'
                liberacion_dict = {'estado': estado_raw, 'observacion': seguro_texto(lib_row[1])}
        except Exception: pass

        conexion.close()
        return {'estado': 'Exito', 'detalles': detalles, 'calibres': calibres, 'defectos': defectos_list, 'evaluacion': evaluacion_dict, 'liberacion': liberacion_dict}
    except Exception as e:
        return {'estado': 'Error', 'mensaje': str(e)}