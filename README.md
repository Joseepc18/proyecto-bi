# Proyecto BI — Mercado Laboral Tech en Ecuador

Plataforma de Inteligencia de Negocios para comparar salarios, modalidad de trabajo
(remoto/presencial/híbrido) y tecnologías más demandadas en los roles de **Desarrollador
de Software**, **Analista/Científico de Datos** y **QA Tester**, integrando portales de
empleo ecuatorianos, agregadores internacionales y estadísticas oficiales del INEC.

## Equipo
- José Eduardo Ponce Carlos
- Dayron Adrian Quiñonez Valencia

Proyecto de la asignatura **BI Inteligencia de Negocios** — Ingeniería de
Software, UPSE.

## ¿De dónde salen los datos?

Trabajamos con 7 fuentes de 3 tipos distintos (datos heterogéneos):

- **Web scraping (4):** Computrabajo, Multitrabajos, Buscojobs y LinkedIn.
- **APIs (2):** Jooble y Remotive (referencia internacional).
- **Archivo oficial (1):** ENEMDU del INEC (salario promedio nacional del sector
  "Información y comunicación").

## Cómo está organizado el repo

```
proyecto-bi/
├── src/
│   ├── scraping/      # un script por portal (computrabajo, multitrabajos, buscojobs, linkedin)
│   ├── apis/          # jooble.py, remotive.py
│   ├── etl/           # staging.py, transformacion.py, validacion.py, inec.py
│   └── utils_log.py   # registro de errores compartido por todo el pipeline
├── data/
│   ├── raw/           # datos crudos tal como llegan (no se modifican)
│   ├── staging/       # datos homologados y la referencia del INEC
│   ├── processed/     # datos transformados, validados y el reporte de calidad
│   └── logs/          # bitácora de errores del pipeline
└── requirements.txt
```

Un detalle sobre los datos: en el repositorio solo va el **código**, el archivo del
**INEC** que usamos (`data/raw/inec/.../4_2_1.csv`) y la **bitácora de errores**. Las ofertas
crudas y los archivos de staging/processed **no se versionan** (se generan al correr el
pipeline). Así el repo se mantiene liviano; al ejecutar los scripts, las carpetas de `data/`
se crean y se llenan solas.

## Antes de empezar: preparar el entorno

Necesitas **Python 3.11 o superior**. Verifica con:

```bash
python --version
```

### 1. Clonar el repositorio

```bash
git clone <url-del-repo>
cd proyecto-bi
```

### 2. (Recomendado) Crear un entorno virtual

Así las dependencias del proyecto no se mezclan con las de tu sistema.

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / Mac
source venv/bin/activate
```

### 3. Instalar las dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar la clave de la API de Jooble

Jooble pide una API key gratuita. En el repo dejamos un archivo `.env.example` como
plantilla; cópialo a `.env` y pon tu clave real ahí:

```bash
# Windows
copy .env.example .env

# Linux / Mac
cp .env.example .env
```

Luego abre el `.env` y reemplaza el valor:

```
JOOBLE_API_KEY=tu_clave_aqui
```

 La api key la puedes sacar registrándote en https://jooble.org/api/about.

## Cómo correr el pipeline completo

El pipeline va por etapas y cada una deja su resultado en `data/`. La idea es correrlo en
orden: primero se recolectan los datos crudos, luego se limpian, transforman y validan.

### Paso 1 — Recolectar los datos (zona RAW)

Cada extractor se ejecuta por separado y guarda su archivo crudo en `data/raw/<fuente>/`.

```bash
python src/scraping/computrabajo.py
python src/scraping/multitrabajos.py
python src/scraping/buscojobs.py
python src/scraping/linkedin.py
python src/apis/jooble.py
python src/apis/remotive.py
```


### Paso 2 — Procesar los datos (Staging → Transformación → Validación)

Corre estos cuatro scripts **en este orden**:

```bash
python src/etl/staging.py          # 1. homologa las 6 fuentes a un formato común
python src/etl/transformacion.py   # 2. salario a número, modalidad, rol y tecnologías
python src/etl/validacion.py       # 3. controles de calidad + reporte de métricas
python src/etl/inec.py             # 4. extrae el salario nacional de referencia (INEC)
```

Cada script lee automáticamente el archivo más reciente de la etapa anterior, así que no
tienes que pasarle nada a mano.

### ¿Qué queda al final?

Después de correr todo, vas a tener:

| Archivo | Qué contiene |
|---|---|
| `data/staging/staging_AAAA-MM-DD.csv` | Las ofertas de las 6 fuentes ya homologadas |
| `data/staging/staging_inec_AAAA-MM-DD.csv` | El salario nacional de referencia del INEC |
| `data/processed/transformacion_AAAA-MM-DD.csv` | Las ofertas con los campos derivados |
| `data/processed/validado_AAAA-MM-DD.csv` | El dataset final, limpio y listo para el Data Warehouse |
| `data/processed/reporte_calidad_AAAA-MM-DD.md` | Reporte consolidado de métricas de calidad |
| `data/logs/registro_errores.csv` | Bitácora de errores y anomalías del pipeline |

El archivo `validado_AAAA-MM-DD.csv` es el que alimenta el Data Warehouse en la siguiente
etapa del proyecto.

## Estado del proyecto

- [x] E1 — Definición del problema y diseño conceptual
- [x] E2 — Arquitectura y modelo dimensional (esquema estrella)
- [x] E3 — Pipeline de extracción, limpieza, transformación y controles de calidad
- [ ] E4 — Data Warehouse y consultas analíticas
- [ ] E5 — Dashboard e insights


