# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd

from config import DATA_URL, MAPAS_DESCENSO, PRESETS, TIEMPO_CALENTAMIENTO_SEG, TIEMPO_TOTAL_SIM
from data import load_and_prepare_data
from simulation import run_montecarlo_simulation
from analysis import (
    calcular_estadisticas,
    build_chart_colas,
    build_chart_espera,
    build_chart_colas_grouped,
    build_chart_espera_grouped,
    build_heatmap,
    build_histograma_doble,
    build_comparison_chart,
    build_linea_diagram,
    build_gauge_throughput,
)

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Simulador Subte Línea D",
    layout="wide",
    page_icon="🚇",
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
.stApp { background-color: #f0f2f6; }
.main .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }

section[data-testid="stSidebar"] {
    background: linear-gradient(160deg, #0d1b2a 0%, #1b2a3b 100%);
    border-right: 3px solid #E31837;
}
section[data-testid="stSidebar"] * { color: #dce3ed !important; opacity: 1 !important; }
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 { color: #ffffff !important; font-weight: 700 !important; }
section[data-testid="stSidebar"] hr { border-color: #E31837 !important; opacity: 0.5 !important; }

/* Expanders en sidebar — fondo oscuro y texto visible */
section[data-testid="stSidebar"] details,
section[data-testid="stSidebar"] [data-testid="stExpander"] {
    background-color: rgba(255,255,255,0.07) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 8px !important;
}
section[data-testid="stSidebar"] details summary,
section[data-testid="stSidebar"] details summary *,
section[data-testid="stSidebar"] details summary p,
section[data-testid="stSidebar"] details summary div {
    background-color: transparent !important;
    color: #ffffff !important;
    opacity: 1 !important;
    font-weight: 600 !important;
}
/* Selectbox y inputs dentro del sidebar */
section[data-testid="stSidebar"] [data-baseweb="select"] > div,
section[data-testid="stSidebar"] [data-baseweb="input"] > div {
    background-color: rgba(255,255,255,0.1) !important;
    border-color: rgba(255,255,255,0.25) !important;
}

.stButton > button[kind="primary"] {
    background-color: #E31837 !important;
    color: white !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.6rem 1.5rem !important;
    transition: all 0.2s ease;
}
.stButton > button[kind="primary"]:hover {
    background-color: #c01530 !important;
    box-shadow: 0 4px 16px rgba(227,24,55,0.35) !important;
    transform: translateY(-1px);
}

.stTabs [data-baseweb="tab-list"] {
    background-color: white;
    border-radius: 10px 10px 0 0;
    gap: 4px;
    padding: 4px 8px 0 8px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.06);
}
.stTabs [data-baseweb="tab"] {
    font-weight: 600;
    border-radius: 6px 6px 0 0;
    padding: 0.6rem 1.2rem;
    color: #555 !important;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background-color: #E31837 !important;
    color: white !important;
}
.stTabs [data-baseweb="tab-panel"] {
    background: white;
    border-radius: 0 10px 10px 10px;
    padding: 1.5rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}
[data-testid="metric-container"] {
    background: white;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    border-left: 5px solid #E31837;
    box-shadow: 0 2px 10px rgba(0,0,0,0.07);
}

/* ── Dataframe outer wrapper ── */
[data-testid="stDataFrame"] {
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 2px 10px rgba(0,0,0,0.08);
    border: 1px solid #e0e0e0;
}
</style>
""", unsafe_allow_html=True)


# ─── Helpers ─────────────────────────────────────────────────────────────────
def kpi_card(label, value, sub=None, color="#E31837", icon=""):
    sub_html = f'<p style="margin:0;font-size:.78rem;color:#888;">{sub}</p>' if sub else ""
    return f"""
    <div style="background:white;border-radius:10px;padding:16px 18px;
                border-top:4px solid {color};
                box-shadow:0 2px 12px rgba(0,0,0,0.07);min-height:100px;
                display:flex;flex-direction:column;justify-content:space-between;">
        <span style="font-size:.7rem;color:#999;text-transform:uppercase;
                     letter-spacing:1px;font-weight:600;">{icon}&nbsp;{label}</span>
        <span style="font-size:1.5rem;font-weight:800;color:#1a1a2e;line-height:1.2;">{value}</span>
        {sub_html}
    </div>"""


def style_tabla_resumen(df):
    """Aplica gradientes de color a las columnas numéricas de la tabla de resumen."""
    cols_red   = [c for c in ['Cola_Max_Media', 'Cola_Max_Max', 'Cola_CI95'] if c in df.columns]
    cols_ora   = [c for c in ['Espera_Media_Seg', 'Espera_Max_Seg', 'Espera_P95_Media_Seg'] if c in df.columns]
    cols_green = [c for c in ['Throughput_Media'] if c in df.columns]
    cols_blue  = [c for c in ['Cola_Max_Min', 'N'] if c in df.columns]

    fmt = {}
    for c in cols_red + cols_ora + cols_blue:
        fmt[c] = '{:.1f}'
    for c in cols_green:
        fmt[c] = '{:.1f}%'

    styled = (
        df.style
        .format(fmt, na_rep='—')
        .background_gradient(subset=cols_red,   cmap='Reds',    vmin=0)
        .background_gradient(subset=cols_ora,   cmap='YlOrBr',  vmin=0)
        .background_gradient(subset=cols_green, cmap='Greens',  vmin=50, vmax=100)
        .background_gradient(subset=cols_blue,  cmap='Blues',   vmin=0)
        .set_properties(**{
            'font-size': '0.84rem',
            'font-weight': '500',
            'color': '#111',
            'border': '1px solid #e8e8e8',
        })
        .set_table_styles([{
            'selector': 'th',
            'props': [
                ('background-color', '#1a1a2e'),
                ('color', 'white'),
                ('font-size', '0.78rem'),
                ('text-transform', 'uppercase'),
                ('letter-spacing', '0.5px'),
                ('border-bottom', '3px solid #E31837'),
                ('padding', '8px 10px'),
            ],
        }, {
            'selector': 'tr:hover td',
            'props': [('background-color', '#ffeef1 !important')],
        }])
    )
    return styled


def style_tabla_simple(df):
    """Gradiente básico para tablas de comparación (solo cola + espera)."""
    cols_red = [c for c in ['Cola Prom', 'Cola_Max_Media'] if c in df.columns]
    cols_ora = [c for c in ['Espera (min)', 'Espera_Media_Seg'] if c in df.columns]

    styled = df.style
    if cols_red:
        styled = styled.background_gradient(subset=cols_red, cmap='Reds', vmin=0)
    if cols_ora:
        styled = styled.background_gradient(subset=cols_ora, cmap='YlOrBr', vmin=0)
    styled = styled.set_properties(**{'font-size': '0.84rem', 'color': '#111'})
    styled = styled.set_table_styles([{
        'selector': 'th',
        'props': [
            ('background-color', '#1a1a2e'),
            ('color', 'white'),
            ('font-size', '0.78rem'),
            ('border-bottom', '3px solid #E31837'),
        ],
    }])
    return styled


def scenario_label(multiplicador):
    if multiplicador == 1.0:
        return "info", "📊 Escenario: **Demanda Base** (sin multiplicador)"
    elif multiplicador <= 1.5:
        return "warning", f"📊 Escenario: **Evento Especial** (×{multiplicador:.1f})"
    elif multiplicador <= 2.5:
        return "warning", f"📊 Escenario: **Alta Demanda** (×{multiplicador:.1f})"
    else:
        return "error", f"⚠️ Escenario: **Estrés Extremo** (×{multiplicador:.1f})"


# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown("""
<div style="background:linear-gradient(90deg,#E31837 0%,#a01025 100%);
            border-radius:12px;padding:22px 28px;margin-bottom:1rem;
            display:flex;align-items:center;gap:16px;">
    <span style="font-size:2.5rem;">🚇</span>
    <div>
        <h1 style="margin:0;color:white;font-size:1.9rem;font-weight:800;line-height:1.1;">
            Simulador Subte Línea D
        </h1>
        <p style="margin:0;color:rgba(255,255,255,0.82);font-size:.88rem;">
            Simulación de Eventos Discretos · Hora Pico 08–09 hs · Buenos Aires · Enero 2025
        </p>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── Session state init (must run on every reload) ────────────────────────────
preset_keys = list(PRESETS.keys())
_defaults = {
    'current_preset': preset_keys[0],
    'esc_a': None,
    'esc_b': None,
    'esc_a_label': 'Escenario A',
    'esc_b_label': 'Escenario B',
    'esc_a_params': {},
    'esc_b_params': {},
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


def _on_preset_change():
    st.session_state['current_preset'] = st.session_state['_preset_sel']


# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Parámetros")

    st.selectbox(
        "Preset de escenario", preset_keys,
        index=preset_keys.index(st.session_state['current_preset']),
        key='_preset_sel',
        on_change=_on_preset_change,
    )
    preset_nombre = st.session_state['current_preset']

    params = PRESETS[preset_nombre].copy()
    st.markdown("---")

    with st.expander("1. Configuración General", expanded=True):
        n_replicaciones = st.slider("N° de Corridas (Montecarlo)", 1, 100, params["n_replicaciones"], 1,
                                    help="Réplicas con distintas semillas para el análisis estadístico.")

    with st.expander("2. Parámetros de Oferta (Tren)", expanded=True):
        capacidad = st.slider("Capacidad del Tren (pax)", 1000, 2000, params["capacidad"], 50)
        dwell_time = st.slider("Dwell Time (seg)", 15, 60, params["dwell_time"], 1)
        tiempo_viaje = st.slider("Tiempo entre estaciones (seg)", 60, 180, params["tiempo_viaje"], 5)

    with st.expander("3. Frecuencia de Trenes", expanded=False):
        min_freq = st.slider("Frecuencia Mínima (seg)", 60, 300, params["min_freq"], 10)
        max_freq = st.slider("Frecuencia Máxima (seg)", 120, 360, params["max_freq"], 10)
        params_validos = min_freq < max_freq
        if not params_validos:
            st.warning("⚠️ Mínima debe ser < Máxima.")
    params_validos = min_freq < max_freq

    with st.expander("4. Tasas de Descenso", expanded=False):
        st.caption("1.0 = sin cambio · 1.5 = +50% pasajeros bajando")
        multiplicador_catedral = st.slider("Descenso H. Catedral", 0.5, 2.0, 1.0, 0.05)
        multiplicador_congreso = st.slider("Descenso H. Congreso", 0.5, 2.0, 1.0, 0.05)

    with st.expander("5. Multiplicador de Demanda (λ)", expanded=True):
        st.write("**Escenarios sugeridos:**")
        st.write("1.0 = Base · 1.5 = Evento · 2.5 = Alta demanda · 5.0 = Estrés extremo")
        multiplicador_demanda = st.slider("Multiplicador λ", 1.0, 5.0, 1.0, 0.1,
                                          help="Multiplica la tasa de llegada de pax en todos los andenes.")
        st.info(f"📊 Aprox. {multiplicador_demanda * 8000:.0f} pax/hora con este multiplicador")

    st.markdown("---")
    st.markdown(
        '<p style="font-size:.72rem;text-align:center;opacity:.4;">Línea D · SBASE · Ene 2025<br>'
        f'Calentamiento: {TIEMPO_CALENTAMIENTO_SEG//3600}h · Medición: {TIEMPO_TOTAL_SIM//3600 - 1}h</p>',
        unsafe_allow_html=True,
    )

# ─── Data loading ─────────────────────────────────────────────────────────────
df_linea_d, df_lambda, error = load_and_prepare_data(DATA_URL)
if error:
    st.error(f"No se pudieron cargar los datos: {error}")
    st.stop()

# ─── Tabs ─────────────────────────────────────────────────────────────────────
tab_sim, tab_analisis, tab_dist, tab_comparar = st.tabs([
    "🚇  Simulación",
    "📊  Análisis de Andenes",
    "📈  Distribución y Datos",
    "⚖️  Comparar Escenarios",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — SIMULACIÓN
# ══════════════════════════════════════════════════════════════════════════════
with tab_sim:
    with st.expander("📂 Ver muestra de datos de demanda (λ)"):
        st.dataframe(df_lambda.head(12), use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if not params_validos:
        st.warning("Corregí la frecuencia en el sidebar antes de ejecutar.")
    else:
        if st.button("▶️  Correr Simulación", type="primary", use_container_width=True):
            df_global, df_kpis = run_montecarlo_simulation(
                n_replicaciones, min_freq, max_freq, capacidad,
                dwell_time, tiempo_viaje, df_lambda, MAPAS_DESCENSO,
                multiplicador_catedral, multiplicador_congreso, multiplicador_demanda,
            )
            df_resumen = calcular_estadisticas(df_global)
            st.session_state.update({
                'df_global': df_global,
                'df_resumen': df_resumen,
                'df_kpis': df_kpis,
                'last_mult_demanda': multiplicador_demanda,
                'last_params': {
                    'n_rep': n_replicaciones, 'cap': capacidad,
                    'min_f': min_freq, 'max_f': max_freq,
                    'dwell': dwell_time, 't_viaje': tiempo_viaje,
                    'mult_cat': multiplicador_catedral, 'mult_con': multiplicador_congreso,
                    'mult_dem': multiplicador_demanda,
                },
            })
            st.success("✅ Simulación completada.")

    if 'df_resumen' in st.session_state:
        df_resumen = st.session_state['df_resumen']
        df_global = st.session_state['df_global']
        df_kpis = st.session_state['df_kpis']

        # Scenario badge
        lvl, msg = scenario_label(st.session_state.get('last_mult_demanda', 1.0))
        getattr(st, lvl)(msg)

        # Compute KPIs
        peor = df_resumen.iloc[0]
        kpi_avg_pax = df_kpis['Total_Pasajeros_Embarcados'].mean()
        kpi_avg_long = df_kpis['Pasajeros_Espera_Larga'].mean()
        service_level = (kpi_avg_pax - kpi_avg_long) / kpi_avg_pax * 100 if kpi_avg_pax > 0 else 100.0
        espera_max_min = df_resumen['Espera_Media_Seg'].max() / 60
        peor_nombre = peor['Anden'].replace('_Hacia ', ' →\n')
        svc_color = "#4CAF50" if service_level >= 90 else "#FF9800" if service_level >= 70 else "#E31837"

        # KPI cards
        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(kpi_card("Andén más cargado", peor_nombre,
                             f"Cola prom: {peor['Cola_Max_Media']:.0f} pax",
                             color="#E31837", icon="🔴"), unsafe_allow_html=True)
        c2.markdown(kpi_card("Nivel de servicio", f"{service_level:.1f}%",
                             "Pasajeros con espera < 5 min",
                             color=svc_color, icon="✅"), unsafe_allow_html=True)
        c3.markdown(kpi_card("Espera máxima", f"{espera_max_min:.1f} min",
                             "Andén más lento (promedio)",
                             color="#FF9800", icon="⏱"), unsafe_allow_html=True)
        c4.markdown(kpi_card("Pax embarcados / hora", f"{kpi_avg_pax:,.0f}",
                             f"Espera larga (>5 min): {kpi_avg_long:.0f} pax",
                             color="#2196F3", icon="👥"), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Subway diagram
        st.plotly_chart(build_linea_diagram(df_resumen), use_container_width=True, config={'scrollZoom': False})

        st.markdown("<br>", unsafe_allow_html=True)

        # Quick bar charts + gauge
        col_colas, col_espera, col_gauge = st.columns([5, 5, 3])
        with col_colas:
            st.plotly_chart(build_chart_colas(df_resumen), use_container_width=True, config={'scrollZoom': False})
        with col_espera:
            st.plotly_chart(build_chart_espera(df_resumen), use_container_width=True, config={'scrollZoom': False})
        with col_gauge:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.plotly_chart(build_gauge_throughput(service_level), use_container_width=True, config={'scrollZoom': False})

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — ANÁLISIS DE ANDENES
# ══════════════════════════════════════════════════════════════════════════════
with tab_analisis:
    if 'df_resumen' not in st.session_state:
        st.info("Ejecutá la simulación primero (tab 🚇 Simulación).")
    else:
        df_resumen = st.session_state['df_resumen']

        # Full stats table
        st.subheader("Resumen Estadístico por Andén (IC 95%)")
        _cols = ['Anden', 'Cola_Max_Media', 'Cola_Max_Min', 'Cola_Max_Max', 'Cola_CI95',
                 'Espera_Media_Seg', 'Espera_Max_Seg', 'Espera_P95_Media_Seg', 'Throughput_Media', 'N']
        st.dataframe(
            style_tabla_resumen(df_resumen[_cols].copy()),
            use_container_width=True, height=420,
        )

        st.download_button(
            "⬇️ Descargar CSV",
            df_resumen.to_csv(index=True).encode('utf-8'),
            "resultados_simulacion.csv", "text/csv",
        )

        st.divider()

        # Top 10 / Bottom 10 toggle
        st.subheader("Cuellos de Botella")
        chart_mode = st.radio(
            "Rango de andenes:",
            ["Top 10 (Peores)", "Bottom 10 (Mejores)"],
            horizontal=True,
        )

        if chart_mode == "Top 10 (Peores)":
            df_top_cola = df_resumen.sort_values('Cola_Max_Media', ascending=False).head(10)
            df_top_espera = df_resumen.sort_values('Espera_Media_Seg', ascending=False).head(10)
            suffix = "Top 10 Peores"
        else:
            df_top_cola = df_resumen[df_resumen['Cola_Max_Media'] > 0].sort_values('Cola_Max_Media').head(10)
            df_top_espera = df_resumen[df_resumen['Espera_Media_Seg'] > 0].sort_values('Espera_Media_Seg').head(10)
            suffix = "Bottom 10 Mejores"

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.plotly_chart(build_chart_colas_grouped(df_top_cola, suffix), use_container_width=True, config={'scrollZoom': False})
        with col_g2:
            st.plotly_chart(build_chart_espera_grouped(df_top_espera, suffix), use_container_width=True, config={'scrollZoom': False})

        st.divider()
        st.plotly_chart(build_heatmap(df_resumen), use_container_width=True, config={'scrollZoom': False})

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — DISTRIBUCIÓN Y DATOS CRUDOS
# ══════════════════════════════════════════════════════════════════════════════
with tab_dist:
    if 'df_global' not in st.session_state:
        st.info("Ejecutá la simulación primero (tab 🚇 Simulación).")
    else:
        df_global = st.session_state['df_global']
        df_kpis = st.session_state['df_kpis']

        st.subheader("Distribución de Resultados por Andén")
        st.write(f"Seleccioná un andén para analizar la variabilidad entre las {st.session_state.get('last_params', {}).get('n_rep', '?')} réplicas.")

        anden_sel = st.selectbox(
            "Andén a analizar:",
            sorted(df_global['Anden'].unique().tolist()),
        )
        st.plotly_chart(build_histograma_doble(df_global, anden_sel), use_container_width=True, config={'scrollZoom': False})

        st.divider()
        st.subheader("KPIs Globales por Réplica")
        st.write("Pasajeros embarcados y esperas largas (>5 min) en cada corrida.")
        st.dataframe(
            df_kpis.style
            .background_gradient(subset=['Total_Pasajeros_Embarcados'], cmap='Greens', vmin=0)
            .background_gradient(subset=['Pasajeros_Espera_Larga'], cmap='Reds', vmin=0)
            .format({'Total_Pasajeros_Embarcados': '{:,.0f}', 'Pasajeros_Espera_Larga': '{:,.0f}'})
            .set_properties(**{'font-size': '0.84rem', 'color': '#111'})
            .set_table_styles([{'selector': 'th', 'props': [
                ('background-color', '#1a1a2e'), ('color', 'white'),
                ('font-size', '0.78rem'), ('border-bottom', '3px solid #E31837'),
            ]}]),
            use_container_width=True,
        )

        st.download_button(
            "⬇️ Descargar KPIs por réplica (CSV)",
            df_kpis.to_csv(index=False).encode('utf-8'),
            "kpis_por_replica.csv", "text/csv",
        )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — COMPARAR ESCENARIOS
# ══════════════════════════════════════════════════════════════════════════════
with tab_comparar:
    st.subheader("Comparación de escenarios")
    st.write("Corré una simulación → **Guardar A** → cambiá parámetros → correla → **Guardar B** → comparar.")

    esc_a_ok = st.session_state['esc_a'] is not None
    esc_b_ok = st.session_state['esc_b'] is not None

    # Estado visual de cada escenario
    st_col_a, st_col_b = st.columns(2)
    with st_col_a:
        if esc_a_ok:
            st.success("✅ **Escenario A** guardado")
        else:
            st.warning("⏳ **Escenario A** — pendiente")
        if st.button("💾 Guardar simulación actual como A", use_container_width=True):
            if 'df_resumen' in st.session_state:
                st.session_state['esc_a'] = st.session_state['df_resumen'].copy()
                st.session_state['esc_a_params'] = st.session_state.get('last_params', {}).copy()
                st.rerun()
            else:
                st.error("Corré la simulación primero.")
    with st_col_b:
        if esc_b_ok:
            st.success("✅ **Escenario B** guardado")
        else:
            st.warning("⏳ **Escenario B** — pendiente")
        if st.button("💾 Guardar simulación actual como B", use_container_width=True):
            if 'df_resumen' in st.session_state:
                st.session_state['esc_b'] = st.session_state['df_resumen'].copy()
                st.session_state['esc_b_params'] = st.session_state.get('last_params', {}).copy()
                st.rerun()
            else:
                st.error("Corré la simulación primero.")

    if esc_a_ok or esc_b_ok:
        if st.button("🗑 Limpiar comparación", type="secondary"):
            st.session_state['esc_a'] = None
            st.session_state['esc_b'] = None
            st.rerun()

    if esc_a_ok and esc_b_ok:
        st.divider()
        col_la, col_lb = st.columns(2)
        with col_la:
            label_a = st.text_input("Nombre Escenario A", "Escenario A", key="lbl_a")
        with col_lb:
            label_b = st.text_input("Nombre Escenario B", "Escenario B", key="lbl_b")

        st.plotly_chart(
            build_comparison_chart(st.session_state['esc_a'], st.session_state['esc_b'], label_a, label_b),
            use_container_width=True,
            config={'scrollZoom': False},
        )

        st.divider()
        st.subheader("Top 10 andenes — cola máxima")
        col_t1, col_t2 = st.columns(2)

        def _top10(df):
            t = df[['Anden', 'Cola_Max_Media', 'Espera_Media_Seg']].head(10).copy()
            t['Espera (min)'] = (t['Espera_Media_Seg'] / 60).round(2)
            t['Cola Prom'] = t['Cola_Max_Media'].round(1)
            return t[['Anden', 'Cola Prom', 'Espera (min)']]

        with col_t1:
            st.markdown(f"**{label_a}**")
            st.dataframe(style_tabla_simple(_top10(st.session_state['esc_a'])), use_container_width=True)
        with col_t2:
            st.markdown(f"**{label_b}**")
            st.dataframe(style_tabla_simple(_top10(st.session_state['esc_b'])), use_container_width=True)
    elif not esc_a_ok and not esc_b_ok:
        st.info("Guardá ambos escenarios para ver la comparación.")
