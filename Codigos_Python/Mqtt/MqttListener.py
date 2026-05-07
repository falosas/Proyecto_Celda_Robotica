import json
import paho.mqtt.client as mqtt
from robodk import robolink

RDK = robolink.Robolink()

# ---------------- CONFIGURACIÓN DE RED ----------------
broker = "10.22.33.82"
port = 1883
sensor_topic = "celda/seguridad/eventos"

# ---------------- DISPOSITIVOS AUTORIZADOS ----------------
dispositivos_autorizados = [
    "puerta_jaula",
    "seta_emergencia",
    "sistema_seguridad",
    "boton_marcha",
    "barrera_luz"
]


def on_message(mqttc, obj, msg):
    payload = msg.payload.decode("utf-8")
    print(f"[{msg.topic}] -> {payload}")

    try:
        datos = json.loads(payload)

        dispositivo = datos.get("dispositivo")
        evento = datos.get("evento")
        alarma = datos.get("alarma")

        if dispositivo not in dispositivos_autorizados:
            print(f"Dispositivo no autorizado: {dispositivo}")
            return

        # --------------------------------------------------
        # CASO 1: ALARMA
        # --------------------------------------------------
        if alarma == True:
            RDK.setParam("ESTADO_SISTEMA", "ALARMA")
            print("ESTADO_SISTEMA cambiado a ALARMA.")

            if dispositivo == "seta_emergencia":
                print("PARO CRÍTICO: seta de emergencia activada.")
            elif dispositivo == "puerta_jaula":
                print("PARO DE EMERGENCIA: puerta de jaula abierta.")
            elif dispositivo == "barrera_luz":
                print("PARO POR INTRUSIÓN: barrera de luz activada.")
            else:
                print("ALARMA DE SEGURIDAD ACTIVADA.")

        # --------------------------------------------------
        # CASO 2: RESET / REARME
        # --------------------------------------------------
        elif alarma == False and evento == "reset":
            RDK.setParam("ESTADO_SISTEMA", "ESPERA")
            print("REARME ACEPTADO. Sistema en ESPERA.")

        # --------------------------------------------------
        # CASO 3: BOTÓN DE MARCHA
        # --------------------------------------------------
        elif alarma == False and evento == "inicio":
            RDK.setParam("ESTADO_SISTEMA", "MARCHA")
            print("ORDEN DE MARCHA RECIBIDA. Sistema en MARCHA.")

        else:
            print("Evento recibido, pero no reconocido.")

    except json.JSONDecodeError:
        print("ERROR: Mensaje JSON inválido.")

    except Exception as e:
        print(f"ERROR GENERAL EN LISTENER: {e}")


# ---------------- INICIALIZACIÓN MQTT ----------------
mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqttc.on_message = on_message

print(f"Conectando al broker MQTT en {broker}:{port}...")
mqttc.connect(broker, port, 60)

mqttc.subscribe(sensor_topic, 0)

print("MqttListener iniciado. Escuchando eventos...")
mqttc.loop_forever()