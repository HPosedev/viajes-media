from datetime import date, timedelta
from html import escape
import sys
from pathlib import Path

# Ensure project root is in sys.path when executed via streamlit run
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import pandas as pd

from src.core.models import (
    AccommodationType,
    FilterParams,
    SortCriterion,
)
from src.core.router import RailRouter
from src.core.sorter import filter_and_sort_accommodations
from src.providers.accommodation import get_accommodation_provider
from src.providers.accommodation.links import airbnb_search_url, booking_search_url
from src.providers.rail import get_rail_provider

# Page setup
st.set_page_config(
    page_title="Escapadas en Tren & Alojamiento",
    page_icon="🚄",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def load_router_and_providers():
    rail_provider = get_rail_provider()
    router = RailRouter(rail_provider=rail_provider)
    acc_provider = get_accommodation_provider()
    stations = rail_provider.get_all_stations()
    return router, acc_provider, stations


router, acc_provider, stations = load_router_and_providers()

# Custom styles with full Dark Mode support
st.html(
    """
    <style>
    /* CSS Variables for Light and Dark mode */
    :root {
        --card-bg: var(--secondary-background-color, #FFFFFF);
        --card-border: rgba(128, 128, 128, 0.2);
        --dest-bg: var(--secondary-background-color, #F8FAFC);
        --dest-border: rgba(128, 128, 128, 0.2);
        --header-color: #1E3A8A;
        --subheader-color: #4B5563;
        --date-box-bg: #F0F9FF;
        --date-box-border: #BAE6FD;
        --date-box-title: #0369A1;
        --date-pill-bg: #F8FAFC;
        --date-pill-border: #E2E8F0;
        --date-pill-color: #475569;
        --text-muted: #64748B;
        --badge-direct-bg: #DEF7EC;
        --badge-direct-text: #03543F;
        --badge-transfer-bg: #FEF08A;
        --badge-transfer-text: #713F12;
    }

    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: var(--header-color);
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: var(--subheader-color);
        margin-bottom: 1.5rem;
    }
    .dest-card {
        padding: 1.2rem;
        border-radius: 10px;
        background-color: var(--dest-bg);
        border: 1px solid var(--dest-border);
        margin-bottom: 0.8rem;
        color: var(--text-color, inherit);
    }
    .dest-card h4 {
        margin: 0 0 0.5rem 0;
        color: var(--text-color, inherit);
    }
    .dest-card p {
        margin: 0.25rem 0;
        color: var(--text-color, inherit);
    }
    .hotel-card {
        padding: 1.2rem;
        border-radius: 12px;
        background-color: var(--card-bg);
        border: 1px solid var(--card-border);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.06);
        margin-bottom: 1rem;
        color: var(--text-color, inherit);
    }
    .hotel-title {
        margin: 0.3rem 0;
        font-size: 1.25rem;
        color: var(--text-color, inherit);
    }
    .hotel-address {
        color: var(--text-muted);
        font-size: 0.9rem;
        margin-bottom: 0.3rem;
    }
    .hotel-reviews {
        color: var(--text-muted);
    }
    .hotel-nightly-price {
        color: var(--text-muted);
        font-size: 0.82rem;
        margin-top: 2px;
    }
    .hotel-stay-total {
        color: #10B981;
        font-weight: 700;
        font-size: 0.85rem;
        margin-top: -2px;
    }
    .date-selector-box {
        background-color: var(--date-box-bg);
        border: 1px solid var(--date-box-border);
        border-radius: 8px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.8rem;
    }
    .date-selector-title {
        margin: 0 0 0.3rem 0;
        color: var(--date-box-title);
        font-size: 1.05rem;
    }
    .date-selector-desc {
        color: var(--text-muted);
        font-size: 0.88rem;
    }
    .badge-direct {
        background-color: var(--badge-direct-bg);
        color: var(--badge-direct-text);
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .badge-transfer {
        background-color: var(--badge-transfer-bg);
        color: var(--badge-transfer-text);
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .rating-badge {
        background-color: #2563EB;
        color: white;
        padding: 4px 8px;
        border-radius: 6px;
        font-weight: bold;
    }
    .price-text {
        font-size: 1.4rem;
        font-weight: bold;
        color: #10B981;
    }
    .total-price-badge {
        background-color: #E0E7FF;
        color: #3730A3;
        font-weight: 600;
        font-size: 0.85rem;
        padding: 3px 8px;
        border-radius: 6px;
        display: inline-block;
        margin-top: 4px;
    }
    .hotel-score {
        color: #7C3AED;
        font-weight: 600;
    }
    .date-pill {
        background-color: var(--date-pill-bg);
        color: var(--date-pill-color);
        font-size: 0.8rem;
        padding: 2px 8px;
        border-radius: 4px;
        border: 1px solid var(--date-pill-border);
        display: inline-block;
    }
    .btn-booking {
        background-color: #003580;
        color: white !important;
        padding: 7px 16px;
        text-decoration: none !important;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.88rem;
        display: inline-block;
        transition: background-color 0.2s;
    }
    .btn-booking:hover {
        background-color: #00224f;
        color: white !important;
        text-decoration: none !important;
    }
    .btn-airbnb {
        background-color: #FF385C;
        color: white !important;
        padding: 7px 16px;
        text-decoration: none !important;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.88rem;
        display: inline-block;
        transition: background-color 0.2s;
    }
    .btn-airbnb:hover {
        background-color: #E00B41;
        color: white !important;
        text-decoration: none !important;
    }
    .btn-booking-secondary {
        background-color: #EFF6FF;
        color: #1D4ED8 !important;
        border: 1px solid #BFDBFE;
        padding: 6px 14px;
        text-decoration: none !important;
        border-radius: 6px;
        font-weight: 500;
        font-size: 0.85rem;
        display: inline-block;
        margin-left: 8px;
        transition: background-color 0.2s;
    }
    .btn-booking-secondary:hover {
        background-color: #DBEAFE;
        color: #1E40AF !important;
        text-decoration: none !important;
    }

    /* DARK MODE - .theme-dark is toggled by the script below from the app background */
    [data-theme="dark"],
    [data-base-mode="dark"],
    .stApp[data-theme="dark"],
    .stApp[data-base-mode="dark"],
    .theme-dark {
        --card-bg: #1E293B !important;
        --dest-bg: #1E293B !important;
        --dest-border: #334155 !important;
        --card-border: #334155 !important;
        --header-color: #60A5FA !important;
        --subheader-color: #94A3B8 !important;
        --date-box-bg: #0F172A !important;
        --date-box-border: #0284C7 !important;
        --date-box-title: #38BDF8 !important;
        --date-pill-bg: #0F172A !important;
        --date-pill-border: #334155 !important;
        --date-pill-color: #CBD5E1 !important;
        --text-muted: #94A3B8 !important;
    }
    [data-theme="dark"] .hotel-title, [data-base-mode="dark"] .hotel-title, .theme-dark .hotel-title { color: #F8FAFC !important; }
    [data-theme="dark"] .hotel-address, [data-base-mode="dark"] .hotel-address, .theme-dark .hotel-address { color: #94A3B8 !important; }
    [data-theme="dark"] .hotel-reviews, [data-base-mode="dark"] .hotel-reviews, .theme-dark .hotel-reviews { color: #94A3B8 !important; }
    [data-theme="dark"] .hotel-nightly-price, [data-base-mode="dark"] .hotel-nightly-price, .theme-dark .hotel-nightly-price { color: #94A3B8 !important; }
    [data-theme="dark"] .hotel-stay-total, [data-base-mode="dark"] .hotel-stay-total, .theme-dark .hotel-stay-total { color: #34D399 !important; }
    [data-theme="dark"] .hotel-score, [data-base-mode="dark"] .hotel-score, .theme-dark .hotel-score { color: #C084FC !important; }
    [data-theme="dark"] .dest-card, [data-base-mode="dark"] .dest-card, .theme-dark .dest-card {
        background-color: #1E293B !important;
        border-color: #334155 !important;
        color: #F8FAFC !important;
    }
    [data-theme="dark"] .dest-card h4, [data-theme="dark"] .dest-card p, [data-theme="dark"] .dest-card strong,
    [data-base-mode="dark"] .dest-card h4, [data-base-mode="dark"] .dest-card p, [data-base-mode="dark"] .dest-card strong,
    .theme-dark .dest-card h4, .theme-dark .dest-card p, .theme-dark .dest-card strong {
        color: #F8FAFC !important;
    }
    [data-theme="dark"] .hotel-card, [data-base-mode="dark"] .hotel-card, .theme-dark .hotel-card {
        background-color: #1E293B !important;
        border-color: #334155 !important;
        color: #F8FAFC !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.4) !important;
    }
    [data-theme="dark"] .date-selector-box, [data-base-mode="dark"] .date-selector-box, .theme-dark .date-selector-box {
        background-color: #0F172A !important;
        border-color: #0284C7 !important;
    }
    [data-theme="dark"] .date-selector-title, [data-base-mode="dark"] .date-selector-title, .theme-dark .date-selector-title { color: #38BDF8 !important; }
    [data-theme="dark"] .date-selector-desc, [data-base-mode="dark"] .date-selector-desc, .theme-dark .date-selector-desc { color: #94A3B8 !important; }
    [data-theme="dark"] .date-pill, [data-base-mode="dark"] .date-pill, .theme-dark .date-pill {
        background-color: #0F172A !important;
        color: #CBD5E1 !important;
        border-color: #334155 !important;
    }
    [data-theme="dark"] .total-price-badge, [data-base-mode="dark"] .total-price-badge, .theme-dark .total-price-badge {
        background-color: #312E81 !important;
        color: #C7D2FE !important;
    }
    [data-theme="dark"] .badge-direct, [data-base-mode="dark"] .badge-direct, .theme-dark .badge-direct {
        background-color: #064E3B !important;
        color: #A7F3D0 !important;
    }
    [data-theme="dark"] .badge-transfer, [data-base-mode="dark"] .badge-transfer, .theme-dark .badge-transfer {
        background-color: #78350F !important;
        color: #FDE68A !important;
    }
    [data-theme="dark"] .btn-booking-secondary, [data-base-mode="dark"] .btn-booking-secondary, .theme-dark .btn-booking-secondary {
        background-color: #0F172A !important;
        color: #93C5FD !important;
        border-color: #1E40AF !important;
    }
    [data-theme="dark"] .btn-booking-secondary:hover, [data-base-mode="dark"] .btn-booking-secondary:hover, .theme-dark .btn-booking-secondary:hover {
        background-color: #1E3A8A !important;
        color: #FFFFFF !important;
    }
    </style>
    <script>
    (function() {
        function checkTheme() {
            try {
                const app = document.querySelector('.stApp') || document.body;
                if (!app) return;
                const bg = window.getComputedStyle(app).backgroundColor;
                const m = bg.match(/\\d+/g);
                // The app background is the source of truth (it reflects Streamlit's theme
                // setting); the OS preference is only used if it cannot be read.
                let isDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
                if (m && m.length >= 3) {
                    const lum = 0.299 * parseInt(m[0]) + 0.587 * parseInt(m[1]) + 0.114 * parseInt(m[2]);
                    isDark = lum < 130;
                }
                if (isDark) {
                    document.documentElement.classList.add('theme-dark');
                } else {
                    document.documentElement.classList.remove('theme-dark');
                }
            } catch (e) {}
        }
        checkTheme();
        // Keep in sync when the theme is switched from Streamlit's settings menu
        setInterval(checkTheme, 1000);
    })();
    </script>
    """,
    # Static, first-party script: without this flag Streamlit strips it and the
    # manual dark-theme detection above never runs.
    unsafe_allow_javascript=True,
)


def safe_url(url: str) -> str:
    """HTML-escapes a link for an href attribute, dropping non-http(s) schemes from provider data."""
    if not url.lower().startswith(("https://", "http://")):
        return "#"
    return escape(url, quote=True)

st.html('<div class="main-header">🚄 Escapadas en Tren (Media Distancia) & Alojamientos 🏨</div>')
st.html('<div class="sub-header">Descubre destinos según el tiempo de trayecto y encuentra los mejores hoteles y apartamentos.</div>')

# ----------------- SIDEBAR CONTROLS -----------------
with st.sidebar:
    st.header("⚙️ Parámetros del Viaje")

    station_names = [s.name for s in sorted(stations, key=lambda x: x.name)]
    default_origin_index = 0
    for idx, name in enumerate(station_names):
        if "Santiago" in name:
            default_origin_index = idx
            break

    selected_origin_name = st.selectbox(
        "🚉 Estación / Población de Origen",
        options=station_names,
        index=default_origin_index,
        help="Elige la estación de salida de Media Distancia / Regionales"
    )
    origin_station = next(s for s in stations if s.name == selected_origin_name)

    # Reset selected destination index if origin station changes
    if st.session_state.get("prev_origin_station") != origin_station.id:
        st.session_state["prev_origin_station"] = origin_station.id
        st.session_state["selected_dest_idx"] = 0

    # Max travel time slider
    max_travel_minutes = st.slider(
        "⏱️ Límite máximo de tiempo de viaje",
        min_value=20,
        max_value=300,
        value=150,
        step=10,
        format="%d min",
        help="Equivale a 2h 30m por defecto"
    )
    hours = max_travel_minutes // 60
    mins = max_travel_minutes % 60
    st.info(f"⏳ Tiempo límite: **{hours}h {mins:02d}m** ({max_travel_minutes} minutos)")

    allow_transfers = st.checkbox("🔄 Permitir enlace simple (1 transbordo)", value=True)

    st.markdown("---")
    st.header("🏨 Filtros de Alojamiento")

    acc_type_str = st.radio(
        "Tipo de Alojamiento",
        options=["Ambos", "Hoteles", "Apartamentos"],
        index=0
    )
    acc_type = AccommodationType.from_str(acc_type_str)

    sort_criterion_str = st.selectbox(
        "Criterio de Ordenación",
        options=[
            "Relación calidad/precio",
            "Mejor nota",
            "Precio más bajo",
            "Precio más alto"
        ],
        index=0
    )
    sort_criterion = SortCriterion.from_str(sort_criterion_str)

    max_budget = st.slider(
        "Presupuesto máximo (€ por noche)",
        min_value=40,
        max_value=300,
        value=200,
        step=10
    )

    min_rating = st.slider(
        "Puntuación mínima (0 a 10)",
        min_value=0.0,
        max_value=9.5,
        value=8.0,
        step=0.5
    )

# ----------------- ROUTING & RESULTS -----------------
routes = router.find_reachable_destinations(
    origin=origin_station,
    max_duration_minutes=max_travel_minutes,
    allow_transfers=allow_transfers
)

if not routes:
    st.warning(f"No se encontraron destinos de Media Distancia accesibles desde **{origin_station.name}** en menos de {hours}h {mins:02d}m. Prueba aumentando el tiempo límite en la barra lateral.")
else:
    # Key metrics row
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Destinos Alcanzables", len(routes))
    col2.metric("Trayecto más Rápido", routes[0].duration_formatted, routes[0].destination.name)
    col3.metric("Trayecto más Lejano", routes[-1].duration_formatted, routes[-1].destination.name)
    direct_count = sum(1 for r in routes if r.is_direct)
    col4.metric("Rutas Directas", f"{direct_count} de {len(routes)}")

    st.markdown("---")

    # Layout: Left side Destination Selector, Right side Accommodation Results
    dest_col, acc_col = st.columns([1, 1.6])

    with dest_col:
        st.subheader("🎯 Destinos Disponibles")

        # Table data
        table_rows = []
        for r in routes:
            table_rows.append({
                "Destino": r.destination.name,
                "Duración": r.duration_formatted,
                "Tipo": "Directo" if r.is_direct else f"Enlace ({r.transfer_station.name})",
                "Tren": r.train_types_formatted,
                "Frecuencia": f"~{r.estimated_frequency_daily}/día"
            })
        df_routes = pd.DataFrame(table_rows)

        if "selected_dest_idx" not in st.session_state or st.session_state["selected_dest_idx"] >= len(routes):
            st.session_state["selected_dest_idx"] = 0

        st.caption("👆 **Haz clic en una fila para seleccionar el destino:**")
        df_event = st.dataframe(
            df_routes,
            on_select="rerun",
            selection_mode="single-row-required",
            selection_default={"selection": {"rows": [st.session_state["selected_dest_idx"]]}},
            width="stretch",
            hide_index=True,
            key=f"routes_df_selection_{origin_station.id}"
        )

        if df_event:
            selection = getattr(df_event, "selection", None) or (df_event.get("selection") if isinstance(df_event, dict) else None)
            if selection:
                rows = getattr(selection, "rows", None) or (selection.get("rows") if isinstance(selection, dict) else None)
                if rows:
                    st.session_state["selected_dest_idx"] = rows[0]

        curr_idx = min(st.session_state.get("selected_dest_idx", 0), len(routes) - 1)
        selected_route = routes[curr_idx]

        # Route detail box
        st.html(
            f"""
            <div class="dest-card">
                <h4>Detalle de Ruta: {escape(origin_station.name)} ➔ {escape(selected_route.destination.name)}</h4>
                <p><strong>Tiempo total:</strong> {selected_route.duration_formatted} ({selected_route.total_duration_minutes} min)</p>
                <p><strong>Modalidad:</strong> {'Directo sin transbordo' if selected_route.is_direct else f'1 Enlace en {escape(selected_route.transfer_station.name)} (espera aprox. {selected_route.transfer_wait_minutes} min)'}</p>
                <p><strong>Frecuencia:</strong> ~{selected_route.estimated_frequency_daily} trenes diarios</p>
                <p><strong>Línea / Servicio:</strong> {escape(selected_route.train_types_formatted)}</p>
            </div>
            """
        )

    with acc_col:
        st.subheader(f"🏨 Alojamientos en {selected_route.destination.name}")

        # ----------------- APARTADO SELECCIÓN DE FECHAS -----------------
        st.html(
            """
            <div class="date-selector-box">
                <h4 class="date-selector-title">📅 Seleccionar Fechas de Estancia</h4>
                <span class="date-selector-desc">
                    Búsqueda de precios exactos para las fechas elegidas (con estacionalidad, fin de semana y desglose total).
                </span>
            </div>
            """
        )

        today = date.today()
        days_ahead_to_friday = (4 - today.weekday()) % 7
        default_next_friday = today + timedelta(days=days_ahead_to_friday)
        default_next_sunday = default_next_friday + timedelta(days=2)
        default_next_saturday = default_next_friday + timedelta(days=1)

        if "global_date_mode" not in st.session_state:
            st.session_state["global_date_mode"] = "Fin de Semana (Vie - Dom)"
        if "global_cin" not in st.session_state:
            st.session_state["global_cin"] = default_next_friday
        if "global_cout" not in st.session_state:
            st.session_state["global_cout"] = default_next_sunday
        # A long-lived session can keep dates that are already in the past, which
        # date_input(min_value=today) would reject with an exception.
        if st.session_state["global_cin"] < today:
            st.session_state["global_date_mode"] = "Fin de Semana (Vie - Dom)"
            st.session_state["global_cin"] = default_next_friday
            st.session_state["global_cout"] = default_next_sunday

        def on_date_mode_change():
            mode = st.session_state.get("global_date_mode")
            if mode == "Fin de Semana (Vie - Dom)":
                st.session_state["global_cin"] = default_next_friday
                st.session_state["global_cout"] = default_next_sunday
            elif mode == "1 Noche (Sáb - Dom)":
                st.session_state["global_cin"] = default_next_saturday
                st.session_state["global_cout"] = default_next_sunday

        def on_cin_change():
            st.session_state["global_date_mode"] = "Personalizado"
            if st.session_state["global_cout"] <= st.session_state["global_cin"]:
                st.session_state["global_cout"] = st.session_state["global_cin"] + timedelta(days=1)

        def on_cout_change():
            st.session_state["global_date_mode"] = "Personalizado"

        date_tabs = st.radio(
            "Modalidad de fechas:",
            options=["Fin de Semana (Vie - Dom)", "1 Noche (Sáb - Dom)", "Personalizado"],
            key="global_date_mode",
            horizontal=True,
            on_change=on_date_mode_change
        )

        col_d1, col_d2 = st.columns(2)

        with col_d1:
            sel_checkin = st.date_input(
                "📥 Fecha de Entrada (Check-in)",
                key="global_cin",
                min_value=today,
                on_change=on_cin_change
            )

        with col_d2:
            min_checkout = sel_checkin + timedelta(days=1)
            if st.session_state["global_cout"] < min_checkout:
                st.session_state["global_cout"] = min_checkout
            sel_checkout = st.date_input(
                "📤 Fecha de Salida (Check-out)",
                key="global_cout",
                min_value=min_checkout,
                on_change=on_cout_change
            )

        stay_nights = max(1, (sel_checkout - sel_checkin).days)
        is_weekend = any((sel_checkin + timedelta(days=i)).weekday() in (4, 5) for i in range(stay_nights))
        weekend_note = " · 🔥 Tarifa fin de semana" if is_weekend else " · 💼 Tarifa estándar"

        st.info(
            f"🛎️ **Precios para fechas exactas:** **{stay_nights} noche{'s' if stay_nights > 1 else ''}** "
            f"del **{sel_checkin.strftime('%d/%m/%Y')}** al **{sel_checkout.strftime('%d/%m/%Y')}**"
            f"{weekend_note}"
        )

        st.caption(f"Filtro: **{acc_type_str}** | Orden: **{sort_criterion_str}** | Máx. {max_budget}€/noche | Mín. {min_rating}★")

        b_dest_clean = (selected_route.destination.city or selected_route.destination.name).split("-")[0].strip()
        full_booking_live_url = booking_search_url(b_dest_clean, sel_checkin, sel_checkout)
        full_airbnb_live_url = airbnb_search_url(b_dest_clean, sel_checkin, sel_checkout)

        st.html(
            f"""
            <div style="background-color: var(--date-box-bg); border: 1px solid var(--date-box-border); border-radius: 8px; padding: 0.75rem 1rem; margin: 0.8rem 0; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                <div style="font-size: 0.88rem; color: var(--subheader-color);">
                    🌐 <strong>¿Quieres ver todo el catálogo en vivo?</strong> Explora todos los alojamientos disponibles en estas fechas:
                </div>
                <div style="display: flex; gap: 8px;">
                    <a href="{safe_url(full_booking_live_url)}" target="_blank" rel="noopener noreferrer" class="btn-booking" style="padding: 5px 12px; font-size: 0.82rem;">Ver todo en Booking.com ↗</a>
                    <a href="{safe_url(full_airbnb_live_url)}" target="_blank" rel="noopener noreferrer" class="btn-airbnb" style="padding: 5px 12px; font-size: 0.82rem;">Ver todo en Airbnb ↗</a>
                </div>
            </div>
            """
        )

        filter_params = FilterParams(
            accommodation_type=acc_type,
            sort_by=sort_criterion,
            max_price=float(max_budget),
            min_rating=float(min_rating),
            checkin_date=sel_checkin,
            checkout_date=sel_checkout
        )

        raw_accs = acc_provider.search(
            destination_name=selected_route.destination.city or selected_route.destination.name,
            acc_type=acc_type,
            min_rating=min_rating,
            max_price=float(max_budget),
            checkin_date=sel_checkin,
            checkout_date=sel_checkout
        )
        filtered_accs = filter_and_sort_accommodations(raw_accs, filter_params)

        if not filtered_accs:
            st.info("No hay alojamientos que coincidan con los filtros seleccionados. Intenta ampliar el presupuesto o reducir la nota mínima.")
        else:
            if not all(acc.is_live for acc in filtered_accs):
                st.caption(
                    "ℹ️ **Datos de demostración:** los precios son estimaciones y los alojamientos marcados como "
                    "*ejemplo* son orientativos. Los enlaces abren Booking/Airbnb con tus fechas para ver el precio "
                    "y la disponibilidad reales."
                )
            date_range = f"{sel_checkin.strftime('%d/%m')} - {sel_checkout.strftime('%d/%m')}"
            for acc in filtered_accs:
                badge_type_color = "#3B82F6" if acc.type == AccommodationType.HOTEL else "#06B6D4"
                if stay_nights > 1:
                    price_box_html = (
                        f'<div class="price-text">{acc.total_price_formatted}</div>'
                        f'<div class="hotel-stay-total">Total ({stay_nights} noches)</div>'
                        f'<div class="hotel-nightly-price">{acc.price_formatted} / noche</div>'
                    )
                else:
                    price_box_html = (
                        f'<div class="price-text">{acc.price_formatted}</div>'
                        f'<small class="hotel-nightly-price">por 1 noche</small>'
                    )

                is_airbnb = "airbnb" in acc.booking_url.lower()
                provider_name = "Airbnb" if is_airbnb else "Booking.com"
                btn_class = "btn-airbnb" if is_airbnb else "btn-booking"

                example_badge = ""
                if acc.is_example:
                    # Illustrative listing: the link can only be a search of the whole town
                    btn_label = f"Ver alojamientos en {escape(b_dest_clean)} en {provider_name} ({date_range}) ↗"
                    example_badge = (
                        '<span style="background-color: #64748B; color: white; padding: 2px 8px; border-radius: 4px; '
                        'font-size: 0.75rem; font-weight: 600; margin-left: 6px;">Ejemplo orientativo</span>'
                    )
                elif acc.is_live:
                    btn_label = f"Ver oferta en {provider_name} ({date_range}) ↗"
                else:
                    btn_label = f"Ver en {provider_name} ({date_range}) ↗"

                alt_booking_button = ""
                if is_airbnb:
                    booking_alt_url = booking_search_url(b_dest_clean, sel_checkin, sel_checkout, apartments_only=True)
                    alt_booking_button = f'<a href="{safe_url(booking_alt_url)}" target="_blank" rel="noopener noreferrer" class="btn-booking-secondary">Buscar apartamentos en Booking.com ↗</a>'

                card_html = f"""
                <div class="hotel-card">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <span style="background-color: {badge_type_color}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600;">
                                {acc.type.value}
                            </span>{example_badge}
                            <h3 class="hotel-title">{escape(acc.name)}</h3>
                            <p class="hotel-address">📍 {escape(acc.address)}</p>
                            <span class="date-pill">🗓️ {sel_checkin.strftime('%d/%m')} - {sel_checkout.strftime('%d/%m')} ({stay_nights}n)</span>
                        </div>
                        <div style="text-align: right;">
                            {price_box_html}
                        </div>
                    </div>
                    <div style="display: flex; gap: 15px; align-items: center; margin-top: 0.5rem; font-size: 0.9rem;">
                        <div><span class="rating-badge">{acc.rating_formatted}</span> <span class="hotel-reviews">({acc.reviews_count:,} reseñas)</span></div>
                        <div class="hotel-score">📊 Índice Calidad/Precio: {acc.value_score}/10</div>
                    </div>
                    <div style="margin-top: 0.8rem; text-align: right;">
                        <a href="{safe_url(acc.booking_url)}" target="_blank" rel="noopener noreferrer" class="{btn_class}">
                            {btn_label}
                        </a>
                        {alt_booking_button}
                    </div>
                </div>
                """
                st.html(card_html)

