import csv
import pandas as pd
import streamlit as st


def _asignar_direccion(row):
    estacion = row['ESTACION']
    molinete = str(row['MOLINETE'])
    if estacion == 'Catedral':
        return 'Hacia Congreso'
    if estacion == 'Congreso de Tucuman':
        return 'Hacia Catedral'
    if estacion == '9 de Julio':
        return 'Ponderar'
    if '_N_' in molinete or '_Oeste_' in molinete or '_O_' in molinete:
        return 'Hacia Congreso'
    if '_S_' in molinete or '_SO_' in molinete or '_Este_' in molinete or '_E_' in molinete:
        return 'Hacia Catedral'
    return 'Ponderar'


@st.cache_data(show_spinner="Descargando y procesando datos (primera vez puede tardar unos minutos)...")
def load_and_prepare_data(url):
    """Downloads the CSV from GitHub, cleans it and computes the lambda demand table.

    Returns (df_linea_d, df_lambda, error_msg). On success, error_msg is None.
    """
    try:
        df = pd.read_csv(
            url,
            sep=';',
            encoding='utf-8-sig',
            quoting=csv.QUOTE_NONE,
            low_memory=False,
        )
    except Exception as e:
        return None, None, str(e)

    df.columns = df.columns.str.replace('"', '', regex=False).str.strip()

    required_cols = ['FECHA', 'pax_TOTAL', 'ESTACION', 'LINEA', 'MOLINETE', 'DESDE']
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        return None, None, f"Columnas requeridas faltantes: {missing}"

    for col in ['FECHA', 'pax_TOTAL', 'LINEA', 'ESTACION']:
        df[col] = df[col].astype(str).str.replace('"', '', regex=False).str.strip()

    df_d = df[df['LINEA'] == 'LineaD'].copy()
    df_d['ESTACION'] = df_d['ESTACION'].replace({'9 de julio': '9 de Julio', 'AgÃ¼ero': 'Agüero'})
    df_d['FECHA'] = pd.to_datetime(df_d['FECHA'], format='%d/%m/%Y', errors='coerce')
    df_d['pax_TOTAL'] = pd.to_numeric(df_d['pax_TOTAL'], errors='coerce')
    df_d.dropna(subset=['pax_TOTAL'], inplace=True)
    df_d['pax_TOTAL'] = df_d['pax_TOTAL'].astype(int)

    # Direction inference
    df_d = df_d.copy()
    df_d['DIRECCION'] = df_d.apply(_asignar_direccion, axis=1)

    df_dir = df_d[df_d['DIRECCION'] != 'Ponderar'].copy()
    df_pond = df_d[df_d['DIRECCION'] == 'Ponderar'].copy()

    df_cat = df_pond.copy()
    df_cat['DIRECCION'] = 'Hacia Catedral'
    df_cat['pax_TOTAL'] = (df_cat['pax_TOTAL'] * 0.5).astype(float)

    df_con = df_pond.copy()
    df_con['DIRECCION'] = 'Hacia Congreso'
    df_con['pax_TOTAL'] = (df_con['pax_TOTAL'] * 0.5).astype(float)

    df_full = pd.concat([df_dir, df_cat, df_con], ignore_index=True)
    df_full['pax_TOTAL'] = pd.to_numeric(df_full['pax_TOTAL'], errors='coerce')
    df_full.dropna(subset=['pax_TOTAL'], inplace=True)

    mask_pico = (df_full['DESDE'] >= '08:00:00') & (df_full['DESDE'] < '09:00:00')
    df_pico = df_full[mask_pico].copy()

    df_lambda = (
        df_pico
        .groupby(['ESTACION', 'DIRECCION', 'DESDE'])['pax_TOTAL']
        .mean()
        .reset_index()
        .rename(columns={'pax_TOTAL': 'pasajeros_PROMEDIO_lambda'})
    )

    return df_d, df_lambda, None
