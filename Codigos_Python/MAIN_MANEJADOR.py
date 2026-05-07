from robolink import *
import time
import json
import paho.mqtt.publish as publish

from bd_trazabilidad import (
    inicializar_bd,
    generar_id_pieza,
    guardar_pieza,
    guardar_pausa
)

RDK = Robolink()

# --- CONFIGURACIÓN ---
BROKER_MQTT = "10.22.33.82"
TOPIC_TRAZABILIDAD = "celda/seguridad/eventos"

NOMBRE_PROGRAMA_MAIN = "MAIN"

RDK.setParam("ESTADO_SISTEMA", "ESPERA")
print("MAIN_MANEJADOR iniciado.")

inicializar_bd()

prog_main = RDK.Item(NOMBRE_PROGRAMA_MAIN, ITEM_TYPE_PROGRAM)

ciclo_lanzado = False
simulacion_pausada = False

while True:
    estado_actual = RDK.getParam("ESTADO_SISTEMA")

    # --------------------------------------------------
    # ESTADO ESPERA
    # --------------------------------------------------
    if estado_actual == "ESPERA":
        time.sleep(0.2)
        continue

    # --------------------------------------------------
    # ESTADO ALARMA → CONGELAR SIMULACIÓN
    # --------------------------------------------------
    if estado_actual == "ALARMA":
        if not simulacion_pausada:
            print("[ALARMA] Congelando simulación en el punto actual...")
            RDK.setSimulationSpeed(0)
            simulacion_pausada = True

        time.sleep(0.2)
        continue

    # --------------------------------------------------
    # ESTADO MARCHA → REANUDAR O LANZAR
    # --------------------------------------------------
    if estado_actual == "MARCHA":

        if not prog_main.Valid():
            print("ERROR: No existe el programa MAIN en RoboDK.")
            RDK.setParam("ESTADO_SISTEMA", "ESPERA")
            time.sleep(0.5)
            continue

        # Si estaba pausado, reanuda desde el punto donde se quedó
        if simulacion_pausada:
            print("[MARCHA] Reanudando simulación desde el punto de parada...")
            RDK.setSimulationSpeed(1)
            simulacion_pausada = False

        # Si todavía no se había lanzado el ciclo, lo lanzamos
        if not ciclo_lanzado and not prog_main.Busy():
            id_pieza = generar_id_pieza()

            hora_inicio_dt = datetime.now()
            hora_inicio = hora_inicio_dt.strftime("%Y-%m-%d %H:%M:%S")

            pausas = []
            
            print("[MARCHA] Lanzando ciclo de producción MAIN...")
            print(f"ID pieza: {id_pieza}")
            print(f"Hora de inicio: {hora_inicio}")
            ciclo_lanzado = True
            RDK.setSimulationSpeed(1)
            prog_main.RunProgram()

        # Vigilar mientras el programa está en ejecución
        while prog_main.Busy():
            estado_vigilancia = RDK.getParam("ESTADO_SISTEMA")

            if estado_vigilancia == "ALARMA":
                if not simulacion_pausada:
                    print("[ALARMA] Congelando simulación durante el ciclo...")
                    
                    inicio_pausa_dt = datetime.now()
                    hora_inicio_pausa = inicio_pausa_dt.strftime("%Y-%m-%d %H:%M:%S")

                    RDK.setSimulationSpeed(0)
                    simulacion_pausada = True

                    print(f"Inicio pausa: {hora_inicio_pausa}")

                # Esperar hasta que vuelva MARCHA
               while RDK.getParam("ESTADO_SISTEMA") != "MARCHA":
                    time.sleep(0.2)

                fin_pausa_dt = datetime.now()
                hora_fin_pausa = fin_pausa_dt.strftime("%Y-%m-%d %H:%M:%S")

                duracion_pausa = (fin_pausa_dt - inicio_pausa_dt).total_seconds()

                pausas.append(duracion_pausa)

                guardar_pausa(
                    id_pieza,
                    hora_inicio_pausa,
                    hora_fin_pausa,
                    duracion_pausa
                )

                print(f"Fin pausa: {hora_fin_pausa}")
                print(f"Duración pausa: {duracion_pausa:.2f} segundos")

                print("[MARCHA] Reanudando ciclo desde el punto de parada...")
                RDK.setSimulationSpeed(1)
                simulacion_pausada = False

            time.sleep(0.1)

        # Cuando el programa termina
        if ciclo_lanzado and not prog_main.Busy():
             hora_fin_dt = datetime.now()
            hora_fin = hora_fin_dt.strftime("%Y-%m-%d %H:%M:%S")

            duracion_total = (hora_fin_dt - hora_inicio_dt).total_seconds()
            numero_pausas = len(pausas)
            duracion_total_pausas = sum(pausas)
            hubo_pausas = 1 if numero_pausas > 0 else 0

            guardar_pieza(
                id_pieza,
                hora_inicio,
                hora_fin,
                duracion_total,
                hubo_pausas,
                numero_pausas,
                duracion_total_pausas
            )

            print("Pieza guardada en la base de datos.")
            print(f"ID pieza: {id_pieza}")
            print(f"Hora inicio: {hora_inicio}")
            print(f"Hora fin: {hora_fin}")
            print(f"Pausas: {numero_pausas}")
            print(f"Duración total pausas: {duracion_total_pausas:.2f} segundos")

            payload_mes = {
                "evento": "ciclo_completado",
                "id_pieza": id_pieza,
                "hora_inicio": hora_inicio,
                "hora_fin": hora_fin,
                "hubo_pausas": bool(hubo_pausas),
                "numero_pausas": numero_pausas,
                "duracion_total_pausas_segundos": duracion_total_pausas,
                "cantidad_consumida": 1,
                "estacion": "celda_yaskawa_ur10e"
            }

            try:
                publish.single(
                    TOPIC_TRAZABILIDAD,
                    payload=json.dumps(payload_mes),
                    hostname=BROKER_MQTT
                )
                print("Trazabilidad enviada correctamente por MQTT.")
            except Exception as e:
                print(f"ERROR DE RED: {e}")

            ciclo_lanzado = False
            RDK.setParam("ESTADO_SISTEMA", "ESPERA")

    time.sleep(0.1)