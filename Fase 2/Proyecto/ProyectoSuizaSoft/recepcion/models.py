from django.db import models

# 1. TABLA DE ESPECIES (Lectura desde Sybase)
class Especie(models.Model):
    id_especies = models.IntegerField(primary_key=True)
    nombre = models.CharField(max_length=100)
    codigo_planilla = models.CharField(max_length=20) # Ej: REG023-24

    class Meta:
        managed = False  # MUY IMPORTANTE: Evita que Django modifique la tabla de CIDES
        db_table = 'especies'  # Aquí pondremos el nombre real de la tabla en Sybase
        verbose_name = 'Especies de Fruta'

# 2. TABLA DE RECEPCIONES (Donde guardaremos las planillas)
class PlanillaRecepcion(models.Model):
    # Claves foráneas (Relaciones)
    especies = models.ForeignKey(Especie, on_delete=models.DO_NOTHING, db_column='id_especies')
    
    # Datos del Encabezado
    planta = models.CharField(max_length=100)
    productor = models.CharField(max_length=150)
    lote = models.CharField(max_length=50)
    kilos_netos = models.FloatField()
    
    # Fechas
    fecha_cosecha = models.DateField(null=True, blank=True)
    fecha_recepcion = models.DateField(null=True, blank=True)
    fecha_inspeccion = models.DateField(auto_now_add=True)
    
    # Resultados y Auditoría
    porcentaje_rechazo_total = models.FloatField()
    digitador = models.CharField(max_length=100)

    class Meta:
        managed = False  # Modo seguro activado
        db_table = 'tb_recepciones_calidad' # Tabla destino en Sybase

# 3. TABLA DE DEFECTOS (El detalle de los kilos rechazados)
class DetalleDefecto(models.Model):
    planilla = models.ForeignKey(PlanillaRecepcion, on_delete=models.DO_NOTHING, db_column='id_planilla')
    nombre_defecto = models.CharField(max_length=100) # Ej: "Oleocelosis"
    kilos_rechazados = models.FloatField()
    porcentaje = models.FloatField()

    class Meta:
        managed = False
        db_table = 'tb_detalle_defectos'

# 4. REGISTRO DE EVIDENCIAS FOTOGRÁFICAS ELIMINADAS (auditoría interna)
# Esta tabla NO vive en Sybase: es de la base local de Django (db.sqlite3).
# No se toca ni se le agrega nada a "ctlcalrecepcionfrutasenca_imagenes" (la
# tabla que armaron en Sybase); ahí el borrado sigue siendo solo
# ccri_estado=2, exactamente como ya estaba. Este modelo es aparte, nada más
# para dejar un registro con fecha de cuándo se borró cada foto. No se
# muestra en ninguna pantalla, es solo para tener el dato guardado.
class RegistroEliminacionEvidencia(models.Model):
    clie_codigo = models.IntegerField()
    plde_codigo = models.IntegerField()
    ccre_numero = models.IntegerField()
    espe_codigo = models.IntegerField()
    ccri_codigo = models.IntegerField()  # código de la fila en Sybase que se borró
    nombre_archivo = models.CharField(max_length=100, blank=True, default='')
    fecha_eliminacion = models.DateTimeField(auto_now_add=True)
    usuario = models.CharField(max_length=100, blank=True, default='')

    class Meta:
        managed = True  # esta SÍ la administra Django (vive en db.sqlite3)
        db_table = 'evidencias_eliminadas_log'
        verbose_name = 'Registro de Evidencia Eliminada'
        verbose_name_plural = 'Registros de Evidencias Eliminadas'