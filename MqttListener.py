import json
import paho.mqtt.client as mqtt
from robodk import robolink    

RDK = robolink.Robolink()

# Configuración de Red
broker = "192.168.1.100"
port = 1883
sensor_topic = celda/seguridad/eventos

def on_message(mqttc, obj, msg):
    payload = msg.payload.decode('utf-8')
    print(f"[{msg.topic}] -> {payload}")
    
    try:
        datos = json.loads(payload)
        dispositivo = datos.get("dispositivo")
        
       # 1. AMPLIAMOS LA LISTA DE RECEPTORES AUTORIZADOS
        if dispositivo in ["puerta_jaula", "seta_emergencia", "sistema_seguridad", "boton_marcha", "barrera_luz"]:
            
            activos_celda = ["Soldador 1", "Soldador 2", "UR10e", "Positioner", "Cinta 1", "Cinta 2"]

            # --- CASO 1: DISPARO DE ALARMAS ---
            if datos.get("alarma") == True:
                # 1. Escribimos en memoria el estado de ALARMA
                RDK.setParam("ESTADO_SISTEMA", "ALARMA")
                
                # 2. Parada instantanea
                for nombre_activo in activos_celda:
                    item = RDK.Item(nombre_activo)
                    if item.Valid():
                        item.Stop() 
                
                if dispositivo == "seta_emergencia":
                    print("¡PARO CRÍTICO! Seta golpeada.")
                elif dispositivo == "puerta_jaula":
                    print("¡PARO DE EMERGENCIA! Puerta abierta.")
                elif dispositivo == "barrera_luz":
                    print("¡PARO POR INTRUSIÓN! Sombra detectada.")
            
            # --- CASO 2: REARME (RESET) ---
            elif datos.get("alarma") == False and datos.get("evento") == "reset":
                # El sistema está sano, pero NO arranca. Pasa a ESPERA.
                RDK.setParam("ESTADO_SISTEMA", "ESPERA")
                print("REARME ACEPTADO. Esperando pulsación de MARCHA...")
            
            # --- CASO 3: INICIO DE PRODUCCIÓN (MARCHA) ---
            elif datos.get("alarma") == False and datos.get("evento") == "inicio":
                # Solo cambiamos la variable. El Orquestador se encargará del resto.
                RDK.setParam("ESTADO_SISTEMA", "MARCHA")
                print("ORDEN DE MARCHA: Autorizando producción.")

    except json.JSONDecodeError:
        print("Error: Mensaje JSON inválido.")

# Inicialización del cliente MQTT
mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqttc.on_message = on_message

print(f"Conectando al broker en {broker}...")
mqttc.connect(broker, port, 60)

# Suscripción a la alarma
mqttc.subscribe(sensor_topic, 0)

print("Sistema armado. Escuchando eventos de seguridad...")
mqttc.loop_forever()