"""Cliente de terminal: simulacion biometrica y envio seguro."""

import argparse
import hmac
import socket
import sys
import time
from pathlib import Path

import utils_crypto as crypto


def autenticar_simulacion():
    print("[SIMULACION] No se captura ni valida una huella real.")
    opcion = input("1 = simular huella autorizada; 2 = denegar: ").strip()
    if opcion != "1":
        raise PermissionError("Acceso denegado por la simulacion biometrica.")
    print("[OK] Autenticacion biometrica SIMULADA aprobada.")


def enviar_archivo(ruta, config):
    autenticar_simulacion()
    if not ruta.is_file():
        raise ValueError("La ruta debe corresponder a un archivo existente.")
    with ruta.open("rb") as archivo:
        datos = archivo.read(config.maximo + 1)
    if len(datos) > config.maximo:
        raise ValueError("Archivo superior al limite configurado.")
    publica = crypto.cargar_rsa(config.claves / "receptor_publica.pem")
    print("Huella publica confiada:", crypto.huella_publica(publica))
    resumen = crypto.sha256(datos)
    with crypto.carpeta_temporal(config, "emisor") as carpeta:
        with socket.create_connection((config.host, config.puerto), config.timeout) as conexion:
            fin = time.monotonic() + config.timeout
            desafio = crypto.recibir_bloque(conexion, 36, fin)
            if len(desafio) != 36 or not desafio.startswith(crypto.MAGIA):
                raise ValueError("Receptor incompatible con el protocolo BVW1.")
            clave = crypto.generar_clave_aes()
            paquete = crypto.empaquetar_archivo(ruta.name, datos)
            cifrado = crypto.cifrar_aes(paquete, clave, desafio + b"/ARCHIVO")
            protegida = crypto.proteger_clave(clave, publica)
            temporal = carpeta / "envio.cifrado"
            temporal.write_bytes(cifrado)
            print("[OK] Archivo cifrado con AES-256-GCM; clave protegida con RSA-OAEP.")
            crypto.enviar_bloque(conexion, protegida, fin)
            crypto.enviar_bloque(conexion, temporal.read_bytes(), fin)
            respuesta = crypto.recibir_bloque(conexion, 62, fin)
            confirmacion = crypto.descifrar_aes(respuesta, clave, desafio + b"/ACK")
            if not hmac.compare_digest(confirmacion, b"OK" + bytes.fromhex(resumen)):
                raise ValueError("La confirmacion del receptor no coincide.")
            print("[OK] Receptor confirmo SHA-256 y limpieza de sus temporales.")
    print("[OK] Transferencia completada. SHA-256:", resumen)


def main():
    parser = argparse.ArgumentParser(description="Emisor de Boveda WiFi.")
    parser.add_argument("archivo", type=Path, help="Ruta del archivo que desea enviar.")
    args = parser.parse_args()
    try:
        enviar_archivo(args.archivo.expanduser().resolve(), crypto.configuracion())
        return 0
    except (OSError, ValueError, TypeError, EOFError) as error:
        print("[ERROR]", error, file=sys.stderr)
        print("No se obtuvo confirmacion de exito; revise la terminal del receptor.")
        return 1
    except KeyboardInterrupt:
        print("\nEnvio cancelado. Revise el receptor si el envio ya habia comenzado.")
        return 130


if __name__ == "__main__":
    sys.exit(main())