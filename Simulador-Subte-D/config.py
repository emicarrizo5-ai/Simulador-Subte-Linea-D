DATA_URL = "https://github.com/petergiaco0-art/Simulador-Subte-D/releases/download/v1.0/202501_D.csv"

TIEMPO_CALENTAMIENTO_SEG = 3600   # 1 hour warm-up (steady-state)
TIEMPO_MEDICION_SEG = 3600        # 1 hour measurement window
TIEMPO_TOTAL_SIM = TIEMPO_CALENTAMIENTO_SEG + TIEMPO_MEDICION_SEG

LISTA_ESTACIONES_NORTE = [
    'Catedral', '9 de Julio', 'Tribunales', 'Callao', 'Facultad de Medicina',
    'Agüero', 'Pueyrredon.D', 'Bulnes', 'Plaza Italia', 'Ministro Carranza',
    'Olleros', 'Jose Hernandez', 'Juramento', 'Congreso de Tucuman'
]
LISTA_ESTACIONES_SUR = LISTA_ESTACIONES_NORTE[::-1]

TIEMPO_SIMULACION_SEG = 3600
INTERVALO_LAMBDA_SEG = 900

TASAS_DESCENSO_HACIA_CATEDRAL = {
    'Congreso de Tucuman': 0.0, 'Juramento': 0.05, 'Jose Hernandez': 0.05,
    'Olleros': 0.05, 'Ministro Carranza': 0.20, 'Plaza Italia': 0.05,
    'Bulnes': 0.05, 'Pueyrredon.D': 0.25, 'Agüero': 0.10,
    'Facultad de Medicina': 0.15, 'Callao': 0.20, 'Tribunales': 0.30,
    '9 de Julio': 0.40, 'Catedral': 1.0,
}
TASAS_DESCENSO_HACIA_CONGRESO = {
    'Catedral': 0.0, '9 de Julio': 0.30, 'Tribunales': 0.25, 'Callao': 0.25,
    'Facultad de Medicina': 0.20, 'Agüero': 0.20, 'Pueyrredon.D': 0.35,
    'Bulnes': 0.25, 'Plaza Italia': 0.35, 'Ministro Carranza': 0.35,
    'Olleros': 0.25, 'Jose Hernandez': 0.25, 'Juramento': 0.30,
    'Congreso de Tucuman': 1.0,
}
MAPAS_DESCENSO = {
    "Hacia Catedral": TASAS_DESCENSO_HACIA_CATEDRAL,
    "Hacia Congreso": TASAS_DESCENSO_HACIA_CONGRESO,
}

COLOR_LINEA_D = "#E31837"

DEFAULT_PARAMS = {
    "n_replicaciones": 50,
    "capacidad": 1500,
    "min_freq": 120,
    "max_freq": 180,
    "dwell_time": 30,
    "tiempo_viaje": 120,
}

PRESETS = {
    "Típico (Ene 2025)": {
        "n_replicaciones": 50,
        "capacidad": 1500,
        "min_freq": 120,
        "max_freq": 180,
        "dwell_time": 30,
        "tiempo_viaje": 120,
    },
    "Alta Demanda": {
        "n_replicaciones": 30,
        "capacidad": 1500,
        "min_freq": 180,
        "max_freq": 300,
        "dwell_time": 45,
        "tiempo_viaje": 130,
    },
    "Frecuencia Reducida": {
        "n_replicaciones": 30,
        "capacidad": 1500,
        "min_freq": 240,
        "max_freq": 360,
        "dwell_time": 30,
        "tiempo_viaje": 120,
    },
    "Servicio Óptimo": {
        "n_replicaciones": 30,
        "capacidad": 2000,
        "min_freq": 60,
        "max_freq": 120,
        "dwell_time": 20,
        "tiempo_viaje": 100,
    },
}
