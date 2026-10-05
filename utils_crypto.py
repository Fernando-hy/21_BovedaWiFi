"""Criptografia, configuracion y tramas TCP de Boveda WiFi."""

import argparse
import hashlib
import ipaddress
import json
import os
import re
import struct
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
from dotenv import load_dotenv

BASE = Path(__file__).resolve().parent
MAGIA = b"BVW1"
RSA_BITS = 3072
MAX_CABECERA = 4096
REDES = tuple(ipaddress.ip_network(red) for red in (
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "127.0.0.0/8"
))


def validar_ip(host):
    host = "127.0.0.1" if host == "localhost" else host
    ip = ipaddress.ip_address(host)
    if ip.version != 4 or not any(ip in red for red in REDES):
        raise ValueError("Use localhost o una IPv4 privada de la LAN.")
    return str(ip)


def configuracion():
    load_dotenv(BASE / ".env", override=False)

    def entero(nombre, defecto, minimo, maximo):
        valor = int(os.getenv(nombre, str(defecto)))
        if not minimo <= valor <= maximo:
            raise ValueError("Valor fuera de rango: " + nombre)
        return valor

    def ruta(nombre, defecto):
        return (BASE / os.getenv(nombre, defecto)).resolve()

    return SimpleNamespace(
        host=validar_ip(os.getenv("HOST", "127.0.0.1")),
        puerto=entero("PUERTO", 5001, 1024, 65535),
        timeout=entero("TIMEOUT_SEGUNDOS", 60, 1, 600),
        maximo=entero("MAX_ARCHIVO_MB", 20, 1, 100) * 1024 * 1024,
        claves=ruta("DIRECTORIO_CLAVES", "claves"),
        recibidos=ruta("DIRECTORIO_RECIBIDOS", "recibidos"),
        temporales=ruta("DIRECTORIO_TEMPORALES", "temporales"),
    )


def cargar_rsa(ruta, privada=False):
    if not ruta.is_file():
        raise ValueError("Falta la clave local: " + str(ruta))
    clave = RSA.import_key(ruta.read_bytes())
    if clave.size_in_bits() != RSA_BITS or clave.has_private() != privada:
        raise ValueError("Se requiere una clave RSA de 3072 bits del tipo indicado.")
    return clave


def generar_claves(carpeta):
    carpeta.mkdir(parents=True, exist_ok=True, mode=0o700)
    privada = carpeta / "receptor_privada.pem"
    publica = carpeta / "receptor_publica.pem"
    if privada.exists() or publica.exists():
        a = cargar_rsa(privada, privada=True)
        b = cargar_rsa(publica)
        if a.publickey().export_key(format="DER") != b.export_key(format="DER"):
            raise ValueError("El par RSA existente no coincide; no se sobrescribe.")
        print("[OK] Claves existentes conservadas.")
        return
    clave = RSA.generate(RSA_BITS)
    creadas = []
    try:
        for ruta, contenido in (
            (privada, clave.export_key(format="PEM", pkcs=8)),
            (publica, clave.publickey().export_key(format="PEM")),
        ):
            descriptor = os.open(ruta, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            creadas.append(ruta)
            with os.fdopen(descriptor, "wb") as archivo:
                archivo.write(contenido)
    except BaseException:
        for ruta in creadas:
            ruta.unlink(missing_ok=True)
        raise
    print("[OK] Claves RSA locales generadas.")


def sha256(datos):
    return hashlib.sha256(datos).hexdigest()


def huella_publica(clave):
    return sha256(clave.publickey().export_key(format="DER"))


def generar_clave_aes():
    return get_random_bytes(32)


def cifrar_aes(datos, clave, asociados):
    if len(clave) != 32:
        raise ValueError("AES-256 requiere una clave de 32 bytes.")
    nonce = get_random_bytes(12)
    cifrador = AES.new(clave, AES.MODE_GCM, nonce=nonce, mac_len=16)
    cifrador.update(asociados)
    cifrado, etiqueta = cifrador.encrypt_and_digest(datos)
    return nonce + etiqueta + cifrado


def descifrar_aes(paquete, clave, asociados):
    if len(clave) != 32 or len(paquete) < 28:
        raise ValueError("Paquete AES invalido.")
    cifrador = AES.new(clave, AES.MODE_GCM, nonce=paquete[:12], mac_len=16)
    cifrador.update(asociados)
    return cifrador.decrypt_and_verify(paquete[28:], paquete[12:28])


def proteger_clave(clave_aes, publica):
    return PKCS1_OAEP.new(publica, hashAlgo=SHA256).encrypt(clave_aes)


def recuperar_clave(clave_protegida, privada):
    clave = PKCS1_OAEP.new(privada, hashAlgo=SHA256).decrypt(clave_protegida)
    if len(clave) != 32:
        raise ValueError("Longitud incorrecta de clave AES.")
    return clave


def empaquetar_archivo(nombre, datos):
    cabecera = json.dumps({"nombre": nombre, "sha256": sha256(datos)},
                          ensure_ascii=True).encode("utf-8")
    if not 0 < len(cabecera) <= MAX_CABECERA:
        raise ValueError("Cabecera demasiado grande.")
    return struct.pack("!I", len(cabecera)) + cabecera + datos


def desempaquetar_archivo(paquete, maximo):
    if len(paquete) < 4:
        raise ValueError("Cabecera incompleta.")
    longitud = struct.unpack("!I", paquete[:4])[0]
    if not 0 < longitud <= MAX_CABECERA or len(paquete) < 4 + longitud:
        raise ValueError("Longitud de cabecera invalida.")
    try:
        cabecera = json.loads(paquete[4:4 + longitud].decode("utf-8"))
    except (ValueError, RecursionError) as error:
        raise ValueError("Cabecera JSON invalida.") from error
    if not isinstance(cabecera, dict) or set(cabecera) != {"nombre", "sha256"}:
        raise ValueError("Campos de cabecera invalidos.")
    nombre, resumen = cabecera["nombre"], cabecera["sha256"]
    if not isinstance(nombre, str) or not 1 <= len(nombre) <= 255:
        raise ValueError("Nombre de archivo invalido.")
    if not isinstance(resumen, str) or re.fullmatch(r"[0-9a-f]{64}", resumen) is None:
        raise ValueError("SHA-256 invalido.")
    datos = paquete[4 + longitud:]
    if len(datos) > maximo:
        raise ValueError("Archivo superior al limite configurado.")
    nombre = re.sub(r"[^A-Za-z0-9._-]", "_", nombre)[:100].strip(".")
    return nombre or "archivo.bin", resumen, datos


def ajustar_timeout(conexion, fin):
    restante = fin - time.monotonic()
    if restante <= 0:
        raise TimeoutError("Tiempo total de transferencia agotado.")
    conexion.settimeout(restante)


def recibir_exacto(conexion, cantidad, fin):
    datos = bytearray()
    while len(datos) < cantidad:
        ajustar_timeout(conexion, fin)
        bloque = conexion.recv(min(65536, cantidad - len(datos)))
        if not bloque:
            raise ConnectionError("Conexion cerrada antes de completar la trama.")
        datos.extend(bloque)
    return bytes(datos)


def enviar_bloque(conexion, datos, fin):
    ajustar_timeout(conexion, fin)
    conexion.sendall(struct.pack("!I", len(datos)))
    ajustar_timeout(conexion, fin)
    conexion.sendall(datos)


def recibir_bloque(conexion, maximo, fin):
    longitud = struct.unpack("!I", recibir_exacto(conexion, 4, fin))[0]
    if not 0 < longitud <= maximo:
        raise ValueError("Longitud de trama no permitida.")
    return recibir_exacto(conexion, longitud, fin)


@contextmanager
def carpeta_temporal(config, rol):
    config.temporales.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporal = tempfile.TemporaryDirectory(prefix=rol + "-", dir=config.temporales)
    try:
        with temporal as nombre:
            yield Path(nombre)
    finally:
        if not Path(temporal.name).exists():
            print("[OK] Temporales del " + rol + " eliminados.")


def main():
    parser = argparse.ArgumentParser(description="Preparacion local de claves RSA.")
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--generar-claves", action="store_true")
    grupo.add_argument("--huella", action="store_true")
    args = parser.parse_args()
    try:
        config = configuracion()
        if args.generar_claves:
            generar_claves(config.claves)
        publica = cargar_rsa(config.claves / "receptor_publica.pem")
        print("Huella SHA-256 de la clave publica:", huella_publica(publica))
        return 0
    except (OSError, ValueError, TypeError) as error:
        print("[ERROR]", error, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nOperacion cancelada.")
        return 130


if __name__ == "__main__":
    sys.exit(main())