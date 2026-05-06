from robolink import *
import time
import json
import paho.mqtt.publish as publish # Usamos la versión simplificada de publicación puntual

RDK = Robolink()

# --- CONFIGURACIÓN DE INTEGRACIÓN MES/ERP ---
BROKER_MQTT = "192.168.1.100" # Pon la IP real de tu ordenador/bróker
TOPIC_TRAZABILIDAD = "celda/produccion/trazabilidad"

# Inicializamos el sistema en ESPERA
RDK.setParam("ESTADO_SISTEMA", "ESPERA")
print("MAIN_ORQUESTADOR (Modo Integración ERP) Iniciado.")

# Flag para evitar lanzar el programa múltiples veces
ciclo_en_curso = False 

while True:
    estado_actual = RDK.getParam("ESTADO_SISTEMA")

    if estado_actual == "ALARMA" or estado_actual == "ESPERA":
        ciclo_en_curso = False
        time.sleep(0.2)
        continue

    elif estado_actual == "MARCHA":
        prog_main = RDK.Item("MAIN", robolink.ITEM_TYPE_PROGRAM)
        
        if prog_main.Valid():
            if not prog_main.Busy() and not ciclo_en_curso:
                print("Lanzando ciclo de producción MAIN...")
                ciclo_en_curso = True
                
                # 1. Disparamos el programa de la celda
                prog_main.RunProgram()
                
                # 2. BUCLE DE VIGILANCIA (El núcleo de la trazabilidad)
                # Nos quedamos atrapados aquí mientras los robots trabajen
                while prog_main.Busy():
                    # Si el script supervisor de seguridad cambia el estado a ALARMA, rompemos la vigilancia
                    if RDK.getParam("ESTADO_SISTEMA") == "ALARMA":
                        print("AVISO: Ciclo abortado por sistema de seguridad. Pieza no descontada.")
                        break
                    time.sleep(0.1)
                
                # 3. EVALUACIÓN POST-CICLO
                # Si el bucle terminó, los robots han parado. 
                # Evaluamos si pararon porque acabaron, o porque hubo un E-Stop.
                if RDK.getParam("ESTADO_SISTEMA") == "MARCHA" and not prog_main.Busy():
                    print("ÉXITO: Ciclo de soldadura completado limpiamente. Reportando al ERP...")
                    
                    # Construimos el contrato de datos para la Base de Datos
                    payload_mes = {
                        "evento": "ciclo_completado",
                        "id_pieza": "TRV-001",
                        "cantidad_consumida": 1,
                        "estacion": "celda_yaskawa_ur10e"
                    }
                    
                    try:
                        # Publicamos un único mensaje y nos desconectamos
                        publish.single(TOPIC_TRAZABILIDAD, payload=json.dumps(payload_mes), hostname=BROKER_MQTT)
                        print("-> Datos de trazabilidad inyectados en la red.")
                    except Exception as e:
                        print(f"ERROR DE RED CRÍTICO: Imposible reportar al ERP. {e}")
                
                ciclo_en_curso = False

        else:
            print("ERROR: No existe un programa llamado 'MAIN' en el árbol.")
            RDK.setParam("ESTADO_SISTEMA", "ESPERA") 

    time.sleep(0.1)