# Sistema de Control de Calidad de Recepción de Fruta

Aplicación web para el control de calidad en la recepción de fruta, implementando el formato oficial.

Permite registrar planillas completas de recepción con distribución de color y madurez, calibre, matriz de defectos por categoría, estimación de fruta exportable, resolución del lote y generación de PDF con formato oficial.

---

## 📦 Tecnologías

- **Backend:** Django 4.2 (Python 3.10+)
- **Base de datos:** Sybase SQL Anywhere 16 (vía pyodbc)
- **Frontend:** HTML5 + JavaScript + Bootstrap 5
- **Generación de PDF:** ReportLab
- **Autenticación:** Contra tabla de usuarios corporativos

---

## 🎯 Módulos del sistema

- **Login** con validación contra la tabla de usuarios corporativos
- **Selección de especie** (limones, naranjas, clementinas, etc.)
- **Recepción y liberación de lotes**:
  - Encabezado del lote (productor, huerto/predio, cuartel, planta, guía, kilos, bultos, fechas)
  - Distribución de Color y Madurez (%)
  - Distribución de Calibre (cantidad de frutos con % autocalculado)
  - Matriz de defectos por categoría (Fancy / Choice / Comercial), agrupados en Calidad y Condición
  - Estimación de fruta exportable
  - Resolución del lote (Liberado / Objetado) y observaciones
- **Generación de PDF** con formato oficial POE023 / REG023 en 1 página
- **Consulta de planillas existentes** para carga y edición

---

## 📋 Requisitos para probar el sistema

Para instalar y probar el sistema en un ambiente local (PC del evaluador) se necesita:

- **Python 3.10 o superior** — [python.org/downloads](https://www.python.org/downloads/)
- **Sybase SQL Anywhere 16** con acceso a la base de datos corporativa
- **DSN ODBC (64 bits)** configurado apuntando a la base de datos
- **Git** — [git-scm.com/downloads](https://git-scm.com/downloads) (opcional)

---

## 🚀 Instalación para pruebas

### 1. Clonar el repositorio

```bash
git clone https://github.com/jonathanbenjamin69/ProyectoSuizaFost.git
cd ProyectoSuizaFost
```

Alternativa: descargar el proyecto como ZIP desde GitHub y extraerlo.

### 2. Crear entorno virtual e instalar dependencias

**Windows (PowerShell):**
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**Linux / Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configurar variables de entorno

Copiar el archivo de plantilla:

```bash
copy .env.example .env
```

Editar `.env` con los valores del ambiente:

```env
SYBASE_DSN=nombre_del_dsn
SYBASE_USER=usuario_de_base_de_datos
SYBASE_PWD=contraseña
SECRET_KEY=clave_secreta_larga_y_aleatoria
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

> ⚠️ El archivo `.env` está en `.gitignore` y no se sube al repositorio. Cada persona/ambiente configura el suyo con sus propios valores.

### 4. Verificar el DSN ODBC

Antes de correr, verificar que el DSN esté configurado:

- Windows: **Panel de control → Administrador de orígenes de datos ODBC (64 bits)**
- El nombre del DSN debe coincidir con el valor de `SYBASE_DSN` en `.env`

### 5. Correr el servidor de desarrollo

```bash
python manage.py runserver
```

Abrir en el navegador: **http://127.0.0.1:8000**

### 6. Ingresar al sistema

Cada usuario ingresa con sus **credenciales corporativas** (las mismas que utiliza para otros sistemas internos de la empresa).

---

## 🚀 Despliegue en producción

El despliegue en el servidor de producción es responsabilidad del área de sistemas de la empresa, según las políticas y la infraestructura interna.

El sistema es una aplicación **Django estándar** y puede desplegarse con cualquiera de los métodos habituales:

- **Windows Server + IIS + wfastcgi**
- **Linux + Nginx + Gunicorn**
- **Linux + Apache + mod_wsgi**
- **Docker / contenedores**

Requisitos generales para producción, independientemente del método elegido:

- Python 3.10+ instalado en el servidor
- Acceso al servidor Sybase corporativo (DSN configurado)
- Archivo `.env` con las credenciales de producción
- `DEBUG=False` en `.env`
- `ALLOWED_HOSTS` configurado con el dominio/IP del servidor
- Recolección de estáticos con `python manage.py collectstatic`
- Se recomienda HTTPS con certificado SSL

Si el equipo de sistemas necesita orientación específica sobre alguno de estos métodos, contactar al desarrollador.

---

## 📂 Estructura del proyecto

```
ProyectoSuizaFost/
├── manage.py                 # Punto de entrada Django
├── requirements.txt          # Dependencias Python
├── .env.example              # Plantilla de variables de entorno
├── .gitignore
├── README.md
├── nucleo_suizasoft/         # Configuración principal Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── recepcion/                # App principal del sistema
    ├── views.py              # Lógica de negocio y endpoints
    ├── urls.py               # Rutas de la app
    ├── pdf_planilla.py       # Generador de PDF POE023
    ├── templates/            # Plantillas HTML
    └── static/
        ├── js/               # JavaScript del frontend
        └── img/frutas/       # Imágenes de las especies
```

---

## 🔒 Consideraciones sobre la base de datos

Este sistema **respeta la integridad de la base de datos corporativa**:

- **No modifica datos maestros** (productores, predios, calibres, defectos, colores). Únicamente los consulta.
- **Escribe solo en tablas operativas** de recepción (`ctlcalrecepcionfrutasenca` y sus tablas detalle).
- **Utiliza los Stored Procedures existentes** en la base de datos (`Movil_Recep_CreaPlanilla`, `Movil_Recep_Actuliza_DetalleColor`, `Movil_Recep_Actuliza_DetalleCalibre`, etc.).
- **No requiere modificaciones al esquema** de la base de datos.

---

## 📝 Notas técnicas

### Sobre las imágenes de frutas

Las imágenes PNG con fondo transparente van en `recepcion/static/img/frutas/`:
- `limon.png`
- `naranja.png`
- `clementina.png`

El mapeo por nombre de especie se resuelve en `views.py` → función `obtener_imagen_fruta()`.

### Sobre la autenticación

El sistema **no usa** el módulo de autenticación de Django. Valida credenciales contra la tabla de usuarios corporativos existente, para que cada persona ingrese con las mismas credenciales que usa en el resto de sistemas internos.

---

## 🐛 Solución de problemas comunes

**"Data source name not found"**  
El DSN especificado en `.env` no existe o está en ODBC de 32 bits. Configurarlo en el Administrador ODBC de 64 bits.

**"Login failed for user"**  
Las credenciales en `.env` no son válidas o el usuario no tiene permisos para acceder a la base.

**El botón "GENERAR PDF" está deshabilitado**  
Es necesario presionar primero **"GUARDAR PLANILLA COMPLETA"**. Si algún dato del formulario cambia después, el botón se deshabilita nuevamente hasta volver a guardar.

**"ImportError: no module named 'reportlab'"**  
Faltan dependencias. Ejecutar `pip install -r requirements.txt` con el entorno virtual activado.

**"DisallowedHost at /"**  
El dominio/IP desde el cual se accede no está listado en `ALLOWED_HOSTS`. Agregarlo en el `.env`.

**Los colores/calibres no aparecen en planillas antiguas**  
Algunas planillas creadas antes del sistema pueden no tener todas las filas base en la BD. Se resuelve creando una planilla nueva o agregando manualmente los registros faltantes en Sybase.

---

## 👤 Desarrollo y contacto

Sistema desarrollado por **Jonathan Benjamín** como servicio de desarrollo externo.

Para consultas técnicas sobre el código, instalación o funcionalidades, contactar al desarrollador a través del canal acordado.
