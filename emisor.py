"""Cliente TCP de la aplicación de escritorio."""

import hmac
import socket
import time

import utils_crypto as crypto


def enviar_archivo(ruta, config, autenticar, notificar=None):
    """La interfaz comprueba la sesión antes de iniciar el envío."""
    autenticar()
    emitir = notificar or (lambda mensaje: None)
    emitir("Leyendo archivo y clave pública...")
    if not ruta.is_file():
        raise ValueError("La ruta debe corresponder a un archivo existente.")
    with ruta.open("rb") as archivo:
        datos = archivo.read(config.maximo + 1)
    if len(datos) > config.maximo:
        raise ValueError("Archivo superior al limite configurado.")
    publica = crypto.cargar_rsa(config.claves / "par_publica.pem")
    print("Huella publica confiada:", crypto.huella_publica(publica))
    privada = crypto.cargar_rsa(config.claves / "receptor_privada.pem", privada=True)
    resumen = crypto.sha256(datos)
    emitir("Conectando con el receptor...")
    with crypto.carpeta_temporal(config, "emisor") as carpeta:
        with socket.create_connection((config.host, config.puerto), config.timeout) as conexion:
            fin = time.monotonic() + config.timeout
            desafio = crypto.recibir_bloque(conexion, 36, fin)
            if len(desafio) != 36 or not desafio.startswith(crypto.MAGIA):
                raise ValueError("Receptor incompatible con el protocolo BVW2.")
            clave = crypto.generar_clave_aes()
            paquete = crypto.empaquetar_archivo(ruta.name, datos)
            cifrado = crypto.cifrar_aes(paquete, clave, desafio + b"/ARCHIVO")
            protegida = crypto.proteger_clave(clave, publica)
            temporal = carpeta / "envio.cifrado"
            temporal.write_bytes(cifrado)
            emitir("Archivo cifrado. Enviando y esperando confirmación...")
            print("[OK] Archivo cifrado con AES-256-GCM; clave protegida con RSA-OAEP.")
            firma = privada.sign(desafio + protegida, crypto.PSS, crypto.hashes.SHA256())
            crypto.enviar_bloque(conexion, firma, fin)
            crypto.enviar_bloque(conexion, protegida, fin)
            crypto.enviar_bloque(conexion, temporal.read_bytes(), fin)
            respuesta = crypto.recibir_bloque(conexion, 62, fin)
            confirmacion = crypto.descifrar_aes(respuesta, clave, desafio + b"/ACK")
            if not hmac.compare_digest(confirmacion, b"OK" + bytes.fromhex(resumen)):
                raise ValueError("La confirmacion del receptor no coincide.")
            print("[OK] Receptor confirmo SHA-256 y limpieza de sus temporales.")
    print("[OK] Transferencia completada. SHA-256:", resumen)
    return {"nombre": ruta.name, "bytes": len(datos), "sha256": resumen,
            "estado": "Envío confirmado", "detalle": "Confirmación cifrada válida. Temporales de ambos extremos eliminados."}


