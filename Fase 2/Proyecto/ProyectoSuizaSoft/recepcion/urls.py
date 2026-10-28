from django.urls import path
from . import views


urlpatterns = [
    path('', views.login_app, name='login_app'),
    path('seleccion-frutas/', views.seleccion_frutas, name='seleccion_frutas'),
    path('recepcion-dinamica/<int:especie_id>/', views.recepcion_dinamica, name='recepcion_dinamica'),
    path('logout/', views.logout_app, name='logout'),

    # Cascada
    path('api/productores/<int:exportador_id>/', views.obtener_productores),
    path('api/predios/<int:productor_id>/', views.obtener_predios),
    path('api/cuarteles/<int:productor_id>/<int:predio_id>/<int:especie_id>/', views.obtener_cuarteles),

    # Lotes
    path('api/buscar-lote/<int:especie_id>/', views.buscar_lote),
    path('api/verificar-planilla-lote/<int:especie_id>/', views.verificar_planilla_lote),

    # Planillas
    path('guardar-planilla/<int:especie_id>/', views.guardar_planilla),
    
    # ¡AQUÍ ESTABA EL ERROR! AHORA ESTÁN EXACTAMENTE COMO LAS BUSCA JS
    path('guardar-colores/<int:especie_id>/', views.guardar_colores, name='guardar_colores'),
    path('guardar-calibres/<int:especie_id>/', views.guardar_calibres, name='guardar_calibres'),
    
    path('api/detalle-planilla/<int:planilla_id>/', views.obtener_detalle_planilla),
    path('api/planillas-creadas/<int:especie_id>/', views.obtener_planillas_creadas),
    path('api/lote-por-planilla/<int:especie_id>/', views.obtener_lote_por_planilla),

    # Nueva: anular planilla
    path('api/anular-planilla/<int:especie_id>/', views.anular_planilla, name='anular_planilla'),
    path('guardar_defectos/<int:especie_id>/', views.guardar_defectos, name='guardar_defectos'),
    path('guardar_evaluaciones/<int:especie_id>/', views.guardar_evaluaciones, name='guardar_evaluaciones'),
    path('guardar_liberacion/<int:especie_id>/', views.guardar_liberacion, name='guardar_liberacion'),

    # Evidencia fotográfica: se puede cargar más de una foto por planilla,
    # verlas todas y borrar la(s) que sobren.
    path('subir-evidencia/<int:especie_id>/', views.subir_evidencia, name='subir_evidencia'),
    path('api/listar-evidencias/<int:especie_id>/', views.listar_evidencias, name='listar_evidencias'),
    path('borrar-evidencia/<int:especie_id>/', views.borrar_evidencia, name='borrar_evidencia'),
    path('api/imagen-evidencia/<int:especie_id>/', views.obtener_imagen_evidencia, name='imagen_evidencia'),

    # PDF de la planilla (formato POE023 / REG023)
    path('api/pdf-planilla/<int:especie_id>/', views.generar_pdf_planilla, name='pdf_planilla'),
]