"""Servidor TCP local: descifrado, integridad y limpieza de temporales."""

import hmac
import os
import socket
import sys
import time
import uuid

from Crypto.Random import get_random_bytes

import utils_crypto as crypto


def guardar_archivo(config, nombre, datos):
    config.recibidos.mkdir(parents=True, exist_ok=True, mode=0o700)
    destino = config.recibidos / (uuid.uuid4().hex + "_" + nombre)
    creado = False
    try:
        descriptor = os.open(destino, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        creado = True
        with os.fdopen(descriptor, "wb") as archivo:
            archivo.write(datos)
            archivo.flush()
            os.fsync(archivo.fileno())
    except BaseException:
        if creado:
            destino.unlink(missing_ok=True)
        raise
    return destino


def recibir_archivo(conexion, config, privada):
    fin = time.monotonic() + config.timeout
    desafio = crypto.MAGIA + get_random_bytes(32)
    crypto.enviar_bloque(conexion, desafio, fin)
    with crypto.carpeta_temporal(config, "receptor") as carpeta:
        protegida = crypto.recibir_bloque(conexion, crypto.RSA_BITS // 8, fin)
        clave = crypto.recuperar_clave(protegida, privada)
        limite = config.maximo + crypto.MAX_CABECERA + 4 + 28
        cifrado = crypto.recibir_bloque(conexion, limite, fin)
        temporal = carpeta / "recepcion.cifrado"
        temporal.write_bytes(cifrado)
        paquete = crypto.descifrar_aes(temporal.read_bytes(), clave, desafio + b"/ARCHIVO")
        nombre, esperado, datos = crypto.desempaquetar_archivo(paquete, config.maximo)
        calculado = crypto.sha256(datos)
        if not hmac.compare_digest(esperado, calculado):
            raise ValueError("Verificacion SHA-256 fallida; archivo descartado.")
        print("[OK] AES-256-GCM y SHA-256 verificados.")
        print("[OK] SHA-256:", calculado)
        destino = guardar_archivo(config, nombre, datos)
        print("[OK] Archivo final guardado:", destino)
    # La confirmacion solo se envia despues de guardar y limpiar correctamente.
    respuesta = crypto.cifrar_aes(b"OK" + bytes.fromhex(calculado), clave, desafio + b"/ACK")
    crypto.enviar_bloque(conexion, respuesta, fin)
    print("[OK] Confirmacion cifrada enviada.")
    return destino


def ejecutar(config):
    privada = crypto.cargar_rsa(config.claves / "receptor_privada.pem", privada=True)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        if os.name == "nt" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            servidor.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        elif os.name != "nt":
            servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        servidor.bind((config.host, config.puerto))
        servidor.listen(5)
        servidor.settimeout(1)
        print("[LISTO] Receptor escuchando en " + config.host + ":" + str(config.puerto))
        print("Use Ctrl+C para detener el receptor.")
        while True:
            try:
                conexion, direccion = servidor.accept()
            except socket.timeout:
                continue
            with conexion:
                try:
                    crypto.validar_ip(direccion[0])
                    recibir_archivo(conexion, config, privada)
                except (OSError, ValueError, TypeError) as error:
                    print("[ERROR] Transferencia no confirmada:", error)


def main():
    try:
        ejecutar(crypto.configuracion())
        return 0
    except (OSError, ValueError, TypeError) as error:
        print("[ERROR]", error, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nReceptor detenido.")
        return 0


if __name__ == "__main__":
    sys.exit(main())