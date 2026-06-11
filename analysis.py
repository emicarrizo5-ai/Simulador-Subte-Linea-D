import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats

from config import LISTA_ESTACIONES_NORTE, COLOR_LINEA_D

# Colores base para texto y grillas
_TEXT = '#1a1a2e'
_GRID = '#ebebeb'

# Layout base que aplica a todos los gráficos
_BASE_LAYOUT = dict(
    plot_bgcolor='white',
    paper_bgcolor='white',
    font=dict(color=_TEXT, family='Arial, sans-serif'),
)


def _axis(title='', angle=0):
    return dict(
        title=title,
        title_font=dict(color=_TEXT, size=12),
        tickfont=dict(color=_TEXT, size=11),
        tickangle=angle,
        showgrid=True,
        gridcolor=_GRID,
        zeroline=False,
    )


def _queue_color(value, max_val):
    if max_val == 0:
        return '#4CAF50'
    r = value / max_val
    if r < 0.33:
        return '#4CAF50'
    elif r < 0.66:
        return '#FF9800'
    return COLOR_LINEA_D


def _ci95_halfwidth(std, n):
    if n <= 1 or std == 0 or np.isnan(std):
        return 0.0
    _, hi = stats.t.interval(0.95, df=n - 1, loc=0, scale=std / np.sqrt(n))
    return float(hi)


def calcular_estadisticas(df_global):
    agg = (
        df_global
        .groupby('Anden')
        .agg(
            Estacion=('Estacion', 'first'),
            Direccion=('Direccion', 'first'),
            Cola_Max_Media=('Cola_Maxima', 'mean'),
            Cola_Max_Std=('Cola_Maxima', 'std'),
            Cola_Max_Min=('Cola_Maxima', 'min'),
            Cola_Max_Max=('Cola_Maxima', 'max'),
            Espera_Media_Seg=('Tiempo_Espera_Promedio_Seg', 'mean'),
            Espera_Std_Seg=('Tiempo_Espera_Promedio_Seg', 'std'),
            Espera_P95_Media_Seg=('Tiempo_Espera_P95_Seg', 'mean'),
            Espera_Max_Seg=('Tiempo_Espera_Promedio_Seg', 'max'),
            N=('Replica', 'count'),
        )
        .reset_index()
    )

    tp = df_global.groupby('Anden').apply(
        lambda g: g['Pasajeros_Subidos'].sum() /
                  (g['Pasajeros_Subidos'].sum() + g['Pasajeros_Varados'].sum()) * 100
        if (g['Pasajeros_Subidos'].sum() + g['Pasajeros_Varados'].sum()) > 0 else 100.0
    ).rename('Throughput_Media')
    agg = agg.merge(tp.reset_index(), on='Anden', how='left')

    agg['Cola_CI95'] = agg.apply(lambda r: _ci95_halfwidth(r['Cola_Max_Std'], r['N']), axis=1)
    agg['Espera_CI95_Seg'] = agg.apply(lambda r: _ci95_halfwidth(r['Espera_Std_Seg'], r['N']), axis=1)

    return agg.sort_values('Cola_Max_Media', ascending=False).reset_index(drop=True)


def build_chart_colas(df_resumen):
    fig = go.Figure(go.Bar(
        y=df_resumen['Anden'],
        x=df_resumen['Cola_Max_Media'],
        error_x=dict(type='data', array=df_resumen['Cola_CI95'].fillna(0).tolist(),
                     visible=True, color='rgba(0,0,0,0.35)'),
        orientation='h',
        marker_color=COLOR_LINEA_D,
        hovertemplate='<b>%{y}</b><br>Cola prom: %{x:.1f} pax<extra></extra>',
    ))
    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text='Cola Máxima Promedio por Andén (± IC 95%)', font=dict(color=_TEXT, size=14)),
        xaxis=_axis('Pasajeros en cola al llegar el tren'),
        yaxis={**_axis(), 'autorange': 'reversed', 'showgrid': False},
        height=520,
        margin=dict(l=10, r=30, t=50, b=40),
    )
    return fig


def build_chart_espera(df_resumen):
    df = df_resumen.copy()
    df['Espera_Media_Min'] = df['Espera_Media_Seg'] / 60
    df['Espera_CI95_Min'] = df['Espera_CI95_Seg'] / 60
    df = df.sort_values('Espera_Media_Min', ascending=False)

    fig = go.Figure(go.Bar(
        y=df['Anden'],
        x=df['Espera_Media_Min'],
        error_x=dict(type='data', array=df['Espera_CI95_Min'].fillna(0).tolist(),
                     visible=True, color='rgba(0,0,0,0.35)'),
        orientation='h',
        marker_color=COLOR_LINEA_D,
        hovertemplate='<b>%{y}</b><br>Espera prom: %{x:.2f} min<extra></extra>',
    ))
    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text='Tiempo de Espera Promedio por Andén (± IC 95%)', font=dict(color=_TEXT, size=14)),
        xaxis=_axis('Tiempo de espera (minutos)'),
        yaxis={**_axis(), 'autorange': 'reversed', 'showgrid': False},
        height=520,
        margin=dict(l=10, r=30, t=50, b=40),
    )
    return fig


def build_heatmap(df_resumen):
    pivot = df_resumen.pivot_table(
        index='Estacion', columns='Direccion', values='Cola_Max_Media', aggfunc='mean'
    )
    order = [s for s in LISTA_ESTACIONES_NORTE if s in pivot.index]
    pivot = pivot.reindex(order)

    z = pivot.values
    # White text on colored cells — readable on all intensity levels
    text = [[f'{v:.0f}' if not np.isnan(v) else '' for v in row] for row in z]

    fig = go.Figure(go.Heatmap(
        z=z,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        colorscale='Reds',
        text=text,
        texttemplate='<b>%{text}</b>',
        textfont=dict(size=13, color='white', family='Arial Black'),
        hoverongaps=False,
        colorbar=dict(
            title=dict(text='Cola Máx.', font=dict(color=_TEXT, size=12)),
            tickfont=dict(color=_TEXT, size=11),
        ),
        hovertemplate='<b>%{y}</b> — %{x}<br>Cola Máx. Prom.: %{z:.1f} pax<extra></extra>',
    ))
    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text='Mapa de Calor — Cola Máxima Promedio por Estación y Dirección',
                   font=dict(color=_TEXT, size=14)),
        xaxis=dict(tickfont=dict(color=_TEXT, size=12), title_font=dict(color=_TEXT)),
        yaxis=dict(tickfont=dict(color=_TEXT, size=11), title_font=dict(color=_TEXT), autorange='reversed'),
        height=500,
        margin=dict(l=10, r=10, t=50, b=10),
    )
    return fig


def build_histograma_esperas(df_global, anden_name):
    df_sel = df_global[df_global['Anden'] == anden_name]
    fig = px.histogram(
        df_sel, x='Tiempo_Espera_Promedio_Seg', nbins=20,
        title=f'Distribución del Tiempo de Espera Promedio — {anden_name}',
        labels={'Tiempo_Espera_Promedio_Seg': 'Tiempo de espera prom. por réplica (seg)'},
        color_discrete_sequence=[COLOR_LINEA_D],
    )
    fig.update_layout(
        **_BASE_LAYOUT,
        title_font=dict(color=_TEXT, size=14),
        showlegend=False,
        xaxis=_axis('Tiempo de espera prom. por réplica (seg)'),
        yaxis=_axis('Frecuencia (réplicas)'),
        margin=dict(l=10, r=10, t=50, b=40),
    )
    return fig


def build_comparison_chart(df_a, df_b, label_a, label_b):
    merged = (
        df_a[['Anden', 'Cola_Max_Media']].rename(columns={'Cola_Max_Media': label_a})
        .merge(df_b[['Anden', 'Cola_Max_Media']].rename(columns={'Cola_Max_Media': label_b}),
               on='Anden', how='outer')
        .sort_values(label_a, ascending=False)
    )
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name=label_a, x=merged['Anden'], y=merged[label_a],
        marker_color=COLOR_LINEA_D,
        hovertemplate='<b>%{x}</b><br>' + label_a + ': %{y:.1f}<extra></extra>',
    ))
    fig.add_trace(go.Bar(
        name=label_b, x=merged['Anden'], y=merged[label_b],
        marker_color='#2196F3',
        hovertemplate='<b>%{x}</b><br>' + label_b + ': %{y:.1f}<extra></extra>',
    ))
    fig.update_layout(
        **_BASE_LAYOUT,
        barmode='group',
        title=dict(text='Comparación de Cola Máxima: Escenario A vs B', font=dict(color=_TEXT, size=14)),
        xaxis={**_axis('Andén'), 'tickangle': 45},
        yaxis=_axis('Cola Máxima Promedio (pax)'),
        height=460,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1,
                    font=dict(color=_TEXT)),
        margin=dict(l=10, r=10, t=70, b=80),
    )
    return fig


def build_chart_colas_grouped(df_filtered, title_suffix):
    x = df_filtered['Anden'].tolist()
    fig = go.Figure()
    fig.add_trace(go.Bar(name='Mínimo', x=x, y=df_filtered['Cola_Max_Min'],
                         marker_color='#4CAF50',
                         hovertemplate='<b>%{x}</b><br>Mín: %{y:.1f} pax<extra></extra>'))
    fig.add_trace(go.Bar(name='Promedio', x=x, y=df_filtered['Cola_Max_Media'],
                         marker_color='#FF9800',
                         hovertemplate='<b>%{x}</b><br>Prom: %{y:.1f} pax<extra></extra>'))
    fig.add_trace(go.Bar(name='Máximo', x=x, y=df_filtered['Cola_Max_Max'],
                         marker_color=COLOR_LINEA_D,
                         hovertemplate='<b>%{x}</b><br>Máx: %{y:.1f} pax<extra></extra>'))
    fig.update_layout(
        **_BASE_LAYOUT,
        barmode='group',
        title=dict(text=f'Rango de Cola Máxima — {title_suffix}', font=dict(color=_TEXT, size=14)),
        xaxis={**_axis(), 'tickangle': 50},
        yaxis=_axis('Pasajeros en cola'),
        height=460,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1,
                    font=dict(color=_TEXT)),
        margin=dict(l=10, r=10, t=70, b=110),
    )
    return fig


def build_chart_espera_grouped(df_filtered, title_suffix):
    df = df_filtered.copy()
    df['Espera_Media_Min_'] = df['Espera_Media_Seg'] / 60
    df['Espera_Max_Min_'] = df['Espera_Max_Seg'] / 60
    x = df['Anden'].tolist()
    fig = go.Figure()
    fig.add_trace(go.Bar(name='Promedio de promedios', x=x, y=df['Espera_Media_Min_'],
                         marker_color='#2196F3',
                         hovertemplate='<b>%{x}</b><br>Prom: %{y:.2f} min<extra></extra>'))
    fig.add_trace(go.Bar(name='Máximo observado', x=x, y=df['Espera_Max_Min_'],
                         marker_color='#9C27B0',
                         hovertemplate='<b>%{x}</b><br>Máx: %{y:.2f} min<extra></extra>'))
    fig.update_layout(
        **_BASE_LAYOUT,
        barmode='group',
        title=dict(text=f'Rango de Tiempo de Espera — {title_suffix}', font=dict(color=_TEXT, size=14)),
        xaxis={**_axis(), 'tickangle': 50},
        yaxis=_axis('Minutos'),
        height=460,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1,
                    font=dict(color=_TEXT)),
        margin=dict(l=10, r=10, t=70, b=110),
    )
    return fig


def build_histograma_doble(df_global, anden_name):
    df_sel = df_global[df_global['Anden'] == anden_name]
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=['Cola Máxima por réplica (pax)', 'Espera Promedio por réplica (seg)'],
    )
    fig.add_trace(
        go.Histogram(x=df_sel['Cola_Maxima'], nbinsx=15,
                     marker_color=COLOR_LINEA_D, opacity=0.85, showlegend=False,
                     hovertemplate='Cola: %{x} pax · Frec: %{y}<extra></extra>'),
        row=1, col=1,
    )
    fig.add_trace(
        go.Histogram(x=df_sel['Tiempo_Espera_Promedio_Seg'], nbinsx=15,
                     marker_color='#2196F3', opacity=0.85, showlegend=False,
                     hovertemplate='Espera: %{x:.1f} seg · Frec: %{y}<extra></extra>'),
        row=1, col=2,
    )
    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text=f'Distribución de Resultados — {anden_name}', font=dict(size=14, color=_TEXT)),
        height=380,
        margin=dict(l=20, r=20, t=80, b=40),
    )
    # Fix subplot title colors (they're annotations)
    for ann in fig.layout.annotations:
        ann.font = dict(color=_TEXT, size=13)
    fig.update_xaxes(showgrid=True, gridcolor=_GRID, tickfont=dict(color=_TEXT))
    fig.update_yaxes(showgrid=True, gridcolor=_GRID, tickfont=dict(color=_TEXT))
    fig.update_yaxes(title_text='Frecuencia (réplicas)', title_font=dict(color=_TEXT), col=1)
    return fig


def build_linea_diagram(df_resumen):
    stations = LISTA_ESTACIONES_NORTE
    n = len(stations)
    x = list(range(n))

    datos = {}
    for _, row in df_resumen.iterrows():
        datos[(row['Estacion'], row['Direccion'])] = row['Cola_Max_Media']

    colas_cong = [datos.get((s, 'Hacia Congreso'), 0) for s in stations]
    colas_cat = [datos.get((s, 'Hacia Catedral'), 0) for s in stations]
    all_vals = colas_cong + colas_cat
    max_val = max(all_vals) if any(v > 0 for v in all_vals) else 1

    fig = go.Figure()

    for y_pos in [1.0, 0.0]:
        fig.add_trace(go.Scatter(
            x=x, y=[y_pos] * n, mode='lines',
            line=dict(color='#CFD8DC', width=8),
            showlegend=False, hoverinfo='skip',
        ))

    fig.add_trace(go.Scatter(
        x=x, y=[1.0] * n, mode='markers+text',
        marker=dict(size=30, color=[_queue_color(c, max_val) for c in colas_cong],
                    line=dict(color='white', width=2.5)),
        text=[f'{c:.0f}' for c in colas_cong],
        textfont=dict(size=9, color='white', family='Arial Black'),
        textposition='middle center',
        customdata=stations,
        hovertemplate='<b>%{customdata}</b><br>→ Congreso<br>Cola: %{text} pax<extra></extra>',
        name='→ Hacia Congreso de Tucumán',
    ))

    fig.add_trace(go.Scatter(
        x=x, y=[0.0] * n, mode='markers+text',
        marker=dict(size=30, color=[_queue_color(c, max_val) for c in colas_cat],
                    line=dict(color='white', width=2.5)),
        text=[f'{c:.0f}' for c in colas_cat],
        textfont=dict(size=9, color='white', family='Arial Black'),
        textposition='middle center',
        customdata=stations,
        hovertemplate='<b>%{customdata}</b><br>→ Catedral<br>Cola: %{text} pax<extra></extra>',
        name='→ Hacia Catedral',
    ))

    for label, color in [('Bajo', '#4CAF50'), ('Medio', '#FF9800'), ('Alto', COLOR_LINEA_D)]:
        fig.add_trace(go.Scatter(x=[None], y=[None], mode='markers',
                                 marker=dict(size=12, color=color),
                                 name=label, showlegend=True))

    for x_pos, y_pos, txt, anchor in [
        (-0.6, 1.0, '<b>Catedral</b>', 'right'),
        (n - 0.4, 1.0, '<b>Congreso</b>', 'left'),
        (-0.6, 0.0, '<b>Congreso</b>', 'right'),
        (n - 0.4, 0.0, '<b>Catedral</b>', 'left'),
    ]:
        fig.add_annotation(x=x_pos, y=y_pos, text=txt, showarrow=False,
                           font=dict(size=10, color=_TEXT), xanchor=anchor)

    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text='Diagrama Línea D — Congestión por Estación', font=dict(size=15, color=_TEXT)),
        xaxis=dict(
            tickvals=x,
            ticktext=[s.replace(' de ', '<br>de ').replace(' ', '<br>', 1) if len(s) > 10 else s
                      for s in stations],
            tickangle=0,
            tickfont=dict(size=9, color=_TEXT),
            showgrid=False, zeroline=False, showline=False,
            range=[-1.2, n + 0.2],
        ),
        yaxis=dict(visible=False, range=[-0.6, 1.7]),
        height=330,
        margin=dict(l=90, r=90, t=55, b=70),
        legend=dict(
            orientation='h', yanchor='top', y=-0.12, xanchor='center', x=0.5,
            font=dict(size=11, color=_TEXT),
            title=dict(text='Nivel de cola:  ', font=dict(size=11, color=_TEXT)),
        ),
    )
    return fig


def build_gauge_throughput(value):
    if value >= 90:
        bar_color = '#4CAF50'
    elif value >= 70:
        bar_color = '#FF9800'
    else:
        bar_color = COLOR_LINEA_D

    fig = go.Figure(go.Indicator(
        mode='gauge+number',
        value=value,
        number={'suffix': '%', 'font': {'size': 38, 'color': bar_color}},
        title={'text': '% Pasajeros que abordaron', 'font': {'size': 13, 'color': _TEXT}},
        gauge={
            'axis': {
                'range': [0, 100],
                'tickwidth': 1,
                'tickfont': {'size': 10, 'color': _TEXT},
                'tickcolor': _TEXT,
            },
            'bar': {'color': bar_color, 'thickness': 0.28},
            'bgcolor': 'white',
            'borderwidth': 0,
            'steps': [
                {'range': [0, 70], 'color': '#FFEBEE'},
                {'range': [70, 90], 'color': '#FFF8E1'},
                {'range': [90, 100], 'color': '#E8F5E9'},
            ],
            'threshold': {
                'line': {'color': bar_color, 'width': 3},
                'thickness': 0.75,
                'value': value,
            },
        },
        domain={'x': [0, 1], 'y': [0, 1]},
    ))
    fig.update_layout(
        height=230,
        margin=dict(l=20, r=20, t=50, b=10),
        paper_bgcolor='white',
        font=dict(color=_TEXT),
    )
    return fig
