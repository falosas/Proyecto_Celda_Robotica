import os
import sqlite3
from datetime import datetime

try:
    CARPETA_SCRIPT = os.path.dirname(os.path.abspath(__file__))
except:
    CARPETA_SCRIPT = os.getcwd()

RUTA_BD = os.path.join(CARPETA_SCRIPT, "trazabilidad_piezas.db")


def inicializar_bd():
    conexion = sqlite3.connect(RUTA_BD)
    cursor = conexion.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS piezas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_pieza TEXT,
            hora_inicio TEXT,
            hora_fin TEXT,
            duracion_total_segundos REAL,
            hubo_pausas INTEGER,
            numero_pausas INTEGER,
            duracion_total_pausas_segundos REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pausas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_pieza TEXT,
            hora_inicio_pausa TEXT,
            hora_fin_pausa TEXT,
            duracion_pausa_segundos REAL
        )
    """)

    conexion.commit()
    conexion.close()

    print(f"Base de datos preparada en: {RUTA_BD}")


def generar_id_pieza():
    fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"PIEZA_{fecha}"


def guardar_pieza(
    id_pieza,
    hora_inicio,
    hora_fin,
    duracion_total,
    hubo_pausas,
    numero_pausas,
    duracion_total_pausas
):
    conexion = sqlite3.connect(RUTA_BD)
    cursor = conexion.cursor()

    cursor.execute("""
        INSERT INTO piezas (
            id_pieza,
            hora_inicio,
            hora_fin,
            duracion_total_segundos,
            hubo_pausas,
            numero_pausas,
            duracion_total_pausas_segundos
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        id_pieza,
        hora_inicio,
        hora_fin,
        duracion_total,
        hubo_pausas,
        numero_pausas,
        duracion_total_pausas
    ))

    conexion.commit()
    conexion.close()


def guardar_pausa(
    id_pieza,
    hora_inicio_pausa,
    hora_fin_pausa,
    duracion_pausa
):
    conexion = sqlite3.connect(RUTA_BD)
    cursor = conexion.cursor()

    cursor.execute("""
        INSERT INTO pausas (
            id_pieza,
            hora_inicio_pausa,
            hora_fin_pausa,
            duracion_pausa_segundos
        )
        VALUES (?, ?, ?, ?)
    """, (
        id_pieza,
        hora_inicio_pausa,
        hora_fin_pausa,
        duracion_pausa
    ))

    conexion.commit()
    conexion.close()