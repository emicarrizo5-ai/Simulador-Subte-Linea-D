import random
import numpy as np
import pandas as pd
import simpy
import streamlit as st

from config import (
    LISTA_ESTACIONES_NORTE,
    LISTA_ESTACIONES_SUR,
    TIEMPO_CALENTAMIENTO_SEG,
    TIEMPO_TOTAL_SIM,
    INTERVALO_LAMBDA_SEG,
)


class Anden:
    def __init__(self, env, nombre_estacion, direccion, tiempo_calentamiento):
        self.env = env
        self.nombre = f"{nombre_estacion}_{direccion}"
        self.direccion = direccion
        self.estacion_nombre = nombre_estacion
        self.tiempo_calentamiento = tiempo_calentamiento
        self.cola_pasajeros = simpy.Store(env)
        # Only populated after warm-up
        self.metricas_tiempo_espera = []
        self.metricas_cola_por_tren = []
        self.pasajeros_subidos = 0

    def add_pasajero(self, pasajero):
        pasajero['tiempo_llegada_anden'] = self.env.now
        return self.cola_pasajeros.put(pasajero)

    def tren_llega_a_anden(self, tren, dwell_time):
        pasajeros_en_cola = len(self.cola_pasajeros.items)
        if self.env.now >= self.tiempo_calentamiento:
            self.metricas_cola_por_tren.append(pasajeros_en_cola)

        while tren['pasajeros_actuales'] < tren['capacidad'] and len(self.cola_pasajeros.items) > 0:
            pasajero = yield self.cola_pasajeros.get()
            if self.env.now >= self.tiempo_calentamiento:
                self.metricas_tiempo_espera.append(self.env.now - pasajero['tiempo_llegada_anden'])
                self.pasajeros_subidos += 1
            tren['pasajeros_actuales'] += 1

        yield self.env.timeout(dwell_time)


def generador_pasajeros(env, anden, df_lambda_anden, intervalo_seg):
    """Infinite-loop generator: repeats the 4×15 min peak schedule for the full simulation."""
    intervalos = ['08:00:00', '08:15:00', '08:30:00', '08:45:00']
    while True:
        for intervalo_hora in intervalos:
            lambda_actual = 0.0
            try:
                lambda_actual = float(df_lambda_anden.loc[intervalo_hora, 'pasajeros_PROMEDIO_lambda'])
            except KeyError:
                pass
            if lambda_actual > 0:
                tasa = lambda_actual / intervalo_seg
                inicio = env.now
                while env.now < inicio + intervalo_seg:
                    yield env.timeout(random.expovariate(tasa))
                    if env.now < inicio + intervalo_seg:
                        yield anden.add_pasajero({'id': f"pax_{random.randint(1000, 9999)}"})
            else:
                yield env.timeout(intervalo_seg)


def proceso_tren(env, tren_id, lista_recorrido, tiempo_viaje, dwell_time,
                 capacidad, mundo_andenes, tasas_descenso):
    tren = {'id': tren_id, 'capacidad': capacidad, 'pasajeros_actuales': 0}
    direccion_viaje = "Hacia Congreso" if lista_recorrido == LISTA_ESTACIONES_NORTE else "Hacia Catedral"
    for i, nombre_estacion in enumerate(lista_recorrido):
        if i > 0:
            yield env.timeout(tiempo_viaje)
        if tren['pasajeros_actuales'] > 0:
            tasa = tasas_descenso[nombre_estacion]
            bajan = np.random.binomial(tren['pasajeros_actuales'], tasa)
            tren['pasajeros_actuales'] -= bajan
        yield env.process(
            mundo_andenes[f"{nombre_estacion}_{direccion_viaje}"].tren_llega_a_anden(tren, dwell_time)
        )


def generador_trenes(env, direccion, lista_recorrido, min_freq, max_freq, tiempo_viaje,
                     dwell_time, capacidad, mundo_andenes, tasas_descenso):
    tren_counter = 0
    while True:
        yield env.timeout(random.uniform(min_freq, max_freq))
        tren_counter += 1
        env.process(proceso_tren(
            env, f"Tren_{direccion}_{tren_counter}", lista_recorrido,
            tiempo_viaje, dwell_time, capacidad, mundo_andenes, tasas_descenso
        ))


def run_montecarlo_simulation(
    n_replicaciones, min_freq, max_freq, capacidad, dwell_time, tiempo_viaje,
    df_lambda, mapas_descenso_base,
    multiplicador_catedral=1.0, multiplicador_congreso=1.0, multiplicador_demanda=1.0
):
    """Returns (df_global, df_kpis_globales).

    df_global: per-andén per-replica metrics.
    df_kpis_globales: per-replica global KPIs (boarded pax, long waits).
    """
    mapas_descenso = {
        "Hacia Catedral": {
            est: min(tasa * multiplicador_catedral, 1.0)
            for est, tasa in mapas_descenso_base["Hacia Catedral"].items()
        },
        "Hacia Congreso": {
            est: min(tasa * multiplicador_congreso, 1.0)
            for est, tasa in mapas_descenso_base["Hacia Congreso"].items()
        },
    }
    df_lambda_ajustado = df_lambda.copy()
    df_lambda_ajustado['pasajeros_PROMEDIO_lambda'] = (
        df_lambda_ajustado['pasajeros_PROMEDIO_lambda'] * multiplicador_demanda
    )

    resultados = []
    kpis_globales = []
    progress_bar = st.progress(0, text="Iniciando simulación...")

    for i in range(n_replicaciones):
        semilla = i + 1
        random.seed(semilla)
        np.random.seed(semilla)

        env = simpy.Environment()
        mundo_andenes = {}
        for estacion in LISTA_ESTACIONES_NORTE:
            for dir_label in ["Hacia Congreso", "Hacia Catedral"]:
                a = Anden(env, estacion, dir_label, TIEMPO_CALENTAMIENTO_SEG)
                mundo_andenes[a.nombre] = a

        for anden_obj in mundo_andenes.values():
            lambda_anden = df_lambda_ajustado[
                (df_lambda_ajustado['ESTACION'] == anden_obj.estacion_nombre) &
                (df_lambda_ajustado['DIRECCION'] == anden_obj.direccion)
            ].set_index('DESDE')
            env.process(generador_pasajeros(env, anden_obj, lambda_anden, INTERVALO_LAMBDA_SEG))

        env.process(generador_trenes(
            env, "Norte", LISTA_ESTACIONES_NORTE,
            min_freq, max_freq, tiempo_viaje, dwell_time, capacidad,
            mundo_andenes, mapas_descenso["Hacia Congreso"]
        ))
        env.process(generador_trenes(
            env, "Sur", LISTA_ESTACIONES_SUR,
            min_freq, max_freq, tiempo_viaje, dwell_time, capacidad,
            mundo_andenes, mapas_descenso["Hacia Catedral"]
        ))

        env.run(until=TIEMPO_TOTAL_SIM)

        total_embarcados = 0
        total_espera_larga = 0

        for anden_obj in mundo_andenes.values():
            t_espera = anden_obj.metricas_tiempo_espera
            l_cola = anden_obj.metricas_cola_por_tren
            pasajeros_varados = len(anden_obj.cola_pasajeros.items)
            total_embarcados += anden_obj.pasajeros_subidos
            total_espera_larga += sum(1 for t in t_espera if t > 300)  # >5 min

            resultados.append({
                'Anden': anden_obj.nombre,
                'Estacion': anden_obj.estacion_nombre,
                'Direccion': anden_obj.direccion,
                'Replica': semilla,
                'Tiempo_Espera_Promedio_Seg': np.mean(t_espera) if t_espera else 0.0,
                'Tiempo_Espera_P95_Seg': float(np.percentile(t_espera, 95)) if t_espera else 0.0,
                'Cola_Maxima': int(np.max(l_cola)) if l_cola else 0,
                'Pasajeros_Subidos': anden_obj.pasajeros_subidos,
                'Pasajeros_Varados': pasajeros_varados,
            })

        kpis_globales.append({
            'Replica': semilla,
            'Total_Pasajeros_Embarcados': total_embarcados,
            'Pasajeros_Espera_Larga': total_espera_larga,
        })

        progress_bar.progress((i + 1) / n_replicaciones, text=f"Réplica {i + 1}/{n_replicaciones}...")

    progress_bar.empty()
    return pd.DataFrame(resultados), pd.DataFrame(kpis_globales)
