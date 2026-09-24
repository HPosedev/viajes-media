# 🚄 Escapadas en Tren (Media Distancia) & Alojamientos 🏨

Aplicación modular en Python para descubrir escapadas de fin de semana en tren de **Media Distancia (Renfe / Feve / Regionales / Avant)** según el tiempo máximo de viaje disponible y encontrar alojamiento optimizado (hoteles y apartamentos) directamente en los destinos alcanzables.

---

## 📋 Características Principales

1. **Entrada Flexible de Usuario:**
   * **Estación de origen:** Búsqueda por nombre, ciudad o alias (ej. *"Santiago de Compostela"*, *"Santiago"*, *"Madrid-Atocha"*, *"Atocha"*, *"Sevilla"*).
   * **Umbral de tiempo:** Soporta formatos naturales (`"hasta 2 horas y 30 minutos"`, `"1 hora y media"`, `"2h 30m"`, `"2h30"`, `"150"`, `"2:30"`, `"2.5"`, `"2,5"`).
   * **Tipo de alojamiento:** Filtrado por `Hoteles`, `Apartamentos` o `Ambos`.
   * **Criterios de ordenación:** `Relación calidad/precio` (fórmula de scoring ponderada), `Mejor nota`, `Precio más bajo` o `Precio más alto`.
   * **Rango de presupuesto y calificación mínima opcional.**
   * **Selección de fechas exactas de estancia:** Selección de fecha de entrada (check-in) y salida (check-out) con cálculo dinámico de tarifas reales según estacionalidad, suplemento de fin de semana, cálculo de precio total de la estancia y enlaces directos preconfigurados.

2. **Módulo Ferroviario (Media Distancia):**
   * Motor de grafos dirigido ponderado (`networkx`).
   * Detección de **rutas directas** y **rutas con enlace simple (1 transbordo)** con margen de conexión realista (15-60 min).
   * Desduplicación automática de destinos seleccionando el trayecto óptimo.
   * Dataset de semilla precalculado (`data/seed_routes.json`) con las principales líneas de Media Distancia en España (Galicia, Madrid/Castilla, Andalucía, Cataluña, Levante, Cornisa Cantábrica).
   * Ingestor estándar GTFS (`GTFSRailProvider`) para cargar feeds oficiales del MITMA o Renfe Open Data (`.zip` o carpeta, configurable con `GTFS_PATH`). Genera un trayecto directo por cada par de paradas servidas por un mismo tren, con la duración más rápida y la frecuencia diaria estimada; si el feed no es válido vuelve automáticamente a la red semilla.

3. **Módulo de Alojamientos:**
   * Patrón **Provider / Strategy** desacoplado (`AccommodationProvider`).
   * **`MockAccommodationProvider`:** Colección local curada de hoteles y apartamentos realistas en destinos españoles (Paradores, hoteles boutique, apartamentos céntricos) con fallback sintético determinista para desarrollo offline instantáneo sin consumo de cuotas. Los precios son estimaciones. Los alojamientos reales enlazan a una búsqueda de Booking por su nombre exacto y tus fechas (nunca a fichas `/hotel/...` adivinadas, que dan 404). Los orientativos se marcan como *ejemplo* y enlazan a la búsqueda de toda la localidad. Para precios y fichas reales usa el proveedor `rapidapi`.
   * **`RapidApiBookingProvider`:** Conexión a endpoints de Booking.com y agregadores vía RapidAPI con fallback automático si no hay clave.
   * **`ScraperAccommodationProvider`:** Esqueleto preparado para un futuro scraper; de momento delega siempre en el proveedor mock.
   * Algoritmo de scoring **Relación Calidad/Precio**:
     $$\text{Score} = \left(\frac{\text{Rating}}{10}\right) \times \left(1 - \frac{\text{Precio} - \text{Mín}}{\text{Máx} - \text{Mín}} \times 0.55\right) \times \text{FactorConfianza}(\text{Reseñas}) \times 10$$

4. **Persistencia & Caché:**
   * Caché local en **SQLite (`data/cache.db`)** con expiración configurable (TTL) para evitar saturación de consultas a proveedores externos.

5. **Doble Interfaz de Usuario:**
   * **CLI Interactiva (`Typer` + `Rich`):** Asistente paso a paso en consola con tablas coloreadas, insignias y enlaces directos de reserva.
   * **Web UI Dashboard (`Streamlit`):** Cuadro de mandos visual con selectores, deslizadores de tiempo y fichas detalladas de destino y hotel.

---

## 🏗️ Estructura del Proyecto

```
viajes/
├── .env.example                  # Plantilla de variables de entorno
├── .gitignore                    # Exclusiones de Git (venv, caché, etc.)
├── README.md                     # Documentación del proyecto
├── requirements.txt              # Dependencias de producción y desarrollo
├── pytest.ini                    # Configuración de pruebas unitarias
├── data/
│   ├── seed_routes.json          # Red ferroviaria de Media Distancia en España
│   └── cache.db                  # Base de datos SQLite (autogenerada para caché)
├── src/
│   ├── __init__.py
│   ├── config.py                 # Configuración centralizada vía Pydantic Settings
│   ├── core/                     # Lógica de dominio y reglas de negocio puras
│   │   ├── __init__.py
│   │   ├── models.py             # Modelos Pydantic (Station, RouteOption, Accommodation)
│   │   ├── router.py             # Motor de enrutamiento por grafos y transbordos
│   │   ├── sorter.py             # Algoritmos de ordenación, filtros y scoring
│   │   └── cache.py              # Repositorio de caché SQLite con TTL
│   ├── providers/                # Adaptadores de integración externa
│   │   ├── __init__.py
│   │   ├── base.py               # Interfaces abstractas (RailDataProvider, AccommodationProvider)
│   │   ├── rail/
│   │   │   ├── __init__.py
│   │   │   ├── local_graph.py    # Proveedor de red basado en JSON local
│   │   │   └── gtfs_provider.py  # Ingestor de feeds oficiales GTFS
│   │   └── accommodation/
│   │       ├── __init__.py
│   │       ├── mock_provider.py  # Proveedor offline realista de alojamientos
│   │       ├── rapidapi.py       # Cliente RapidAPI Booking.com con fallback
│   │       └── scraper.py        # Adaptador web scraping controlado
│   ├── cli/
│   │   ├── __init__.py
│   │   └── main.py               # Interfaz CLI con Rich y Typer
│   └── web/
│       ├── __init__.py
│       └── app.py                # Cuadro de mandos web en Streamlit
└── tests/
    ├── __init__.py
    ├── conftest.py               # Fixtures de prueba
    ├── test_router.py            # Tests de umbrales, parsing de tiempo y transbordos
    ├── test_accommodation.py     # Tests de filtros, ordenación, calidad/precio y RapidAPI
    ├── test_cache.py             # Tests de almacenamiento y expiración en SQLite
    ├── test_gtfs.py              # Tests del ingestor GTFS (carpeta, zip y fallback)
    └── test_cli.py               # Tests de validación de fechas de la CLI
```

---

## 🚀 Instalación y Puesta en Marcha

### 1. Prerrequisitos
* Python 3.10 o superior instalado en el sistema.

### 2. Clonar el repositorio y crear el entorno virtual
```bash
# Crear entorno virtual
python3 -m venv .venv

# Activar el entorno virtual
# En Fish shell:
source .venv/bin/activate.fish

# En Bash / Zsh:
# source .venv/bin/activate

# En Windows (PowerShell / CMD):
# .venv\Scripts\activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno (opcional)
Copia la plantilla `.env.example` a `.env`:
```bash
cp .env.example .env
```
Por defecto, la aplicación utiliza el proveedor `mock`, que funciona 100% offline sin necesidad de credenciales externas, pero con **precios estimados** que no coinciden con los de Booking.

#### Precios reales de Booking (RapidAPI)
1. Crea una cuenta en [rapidapi.com](https://rapidapi.com) y suscríbete a la API [Booking COM](https://rapidapi.com/DataCrawler/api/booking-com15) (tiene plan gratuito con cuota mensual limitada).
2. Copia tu clave (`X-RapidAPI-Key`) en el archivo `.env` (nunca en `.env.example`: el `.env` está excluido de git):
```env
ACCOMMODATION_PROVIDER=rapidapi
RAPIDAPI_KEY=tu_api_key_aqui
```
Cada destino consulta la API en euros y para tus fechas exactas (si no indicas fechas, se usa el próximo viernes → sábado). Las respuestas se guardan en la caché SQLite (`RAPIDAPI_PRICE_CACHE_HOURS`, 3 h por defecto), así que cambiar filtros no gasta cuota. Si la clave falla o se agota la cuota, la app avisa y muestra datos de demostración.

---

## 💻 Uso de la Aplicación

### Opción A: Interfaz de Línea de Comandos (CLI)

#### 1. Modo Asistente Interactivo (Recomendado):
Ejecuta el asistente guiado:
```bash
python -m src.cli.main interactive
# O simplemente:
python -m src.cli.main
```
El asistente te solicitará interactivamente:
1. Estación de origen (con autocompletado y búsqueda flexible).
2. Tiempo máximo (ej. `"hasta 2 horas y 30 minutos"` o `"90m"`).
3. Tipo de alojamiento (`Hoteles`, `Apartamentos` o `Ambos`).
4. Criterio de ordenación (`Relación calidad/precio`, `Mejor nota`, etc.).
5. Rango de presupuesto opcional.
6. Permite explorar todos los destinos o seleccionar uno en particular.

#### 2. Modo Búsqueda Directa con Argumentos:
```bash
# Ejemplo: Salida desde Santiago de Compostela, máximo 2 horas y media
python -m src.cli.main search --origin "Santiago de Compostela" --max-time "2h 30m" --acc-type "Ambos" --sort "Relación calidad/precio"

# Sin --origin ni --max-time se usan los valores por defecto (València-Nord, 120 min),
# configurables con DEFAULT_ORIGIN_STATION y DEFAULT_MAX_TRAVEL_HOURS en el .env
python -m src.cli.main search

# Ejemplo: Salida desde Madrid-Atocha, máximo 1 hora y media, solo hoteles
python -m src.cli.main search --origin "Madrid-Atocha" --max-time "1h 30m" --acc-type "Hoteles" --sort "Mejor nota"
```

#### 3. Ver todas las estaciones disponibles:
```bash
python -m src.cli.main stations
```

---

### Opción B: Interfaz Web Visual (Streamlit)

Para abrir el panel de control gráfico e interactivo:
```bash
streamlit run src/web/app.py
```
Se abrirá automáticamente en tu navegador (por defecto en `http://localhost:8501`).

---

## 🧪 Ejecución de Tests Unitarios

La suite de pruebas cubre:
* Cálculo y parsing de tiempos de viaje.
* Resolución de nombres y alias de estaciones.
* Cumplimiento estricto del umbral de tiempo y desduplicación de rutas.
* Rutas directas y con enlace simple (transbordo).
* Filtrado por tipo de alojamiento, presupuesto y nota mínima.
* Algoritmos de ordenación y fórmula de relación calidad/precio.
* Persistencia y expiración de caché en SQLite (invalidación automática si cambia la red).
* Ingesta de feeds GTFS y fallback a la red semilla.
* Fallbacks de RapidAPI y validación de fechas de estancia en la CLI.

Ejecuta los tests con `pytest`:
```bash
pytest
```
Para ver la salida detallada:
```bash
pytest -v
```

---

## 🛠️ Extensibilidad y Nuevos Proveedores

* **Añadir un nuevo proveedor de alojamiento:** Implementa la interfaz abstracta `AccommodationProvider` en `src/providers/base.py` y regístrala en la factoría `src/providers/accommodation/__init__.py`.
* **Cargar nuevos datos de trenes:** Puedes extender el archivo `data/seed_routes.json` añadiendo estaciones o aristas, o apuntar `GTFS_PATH` en el `.env` a un feed GTFS oficial (zip o directorio), p. ej. `GTFS_PATH=data/gtfs.zip`. Las rutas relativas se resuelven desde la raíz del proyecto.
