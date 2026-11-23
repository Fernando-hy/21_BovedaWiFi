"""Perfil por usuario del sistema. La contraseña abre la política local cifrada."""
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import struct
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def nueva_semilla():
    return base64.b32encode(secrets.token_bytes(20)).decode()


def codigo(semilla, paso):
    digest = hmac.digest(base64.b32decode(semilla), struct.pack(">Q", paso), "sha1")
    offset = digest[-1] & 15
    numero = int.from_bytes(digest[offset:offset+4], "big") & 0x7fffffff
    return f"{numero % 1000000:06d}"


def validar_codigo(semilla, entrada, ultimo):
    ahora = int(time.time()) // 30
    for paso in (ahora, ahora-1, ahora+1):
        if paso > ultimo and hmac.compare_digest(codigo(semilla, paso).encode(), (entrada or "").encode()):
            return paso
    raise ValueError("Código incorrecto o utilizado. Espera el siguiente código.")


def verificar_huella():
    if sys.platform == "win32":
        from huella_windows import verificar
        verificar()
        return
    elif sys.platform.startswith("linux"):
        args = ["/usr/bin/fprintd-verify"]
    else:
        raise ValueError("Esta plataforma no tiene un adaptador de huella compatible.")
    try:
        p = subprocess.run(args, capture_output=True, timeout=50, env={**os.environ, "LC_ALL":"C"})
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError("Lector sin respuesta. Comprueba el controlador y la huella registrada.") from exc
    if p.returncode or (sys.platform != "win32" and not re.search(rb"(?m)^Verify result: verify-match(?: \(done\))?\s*$", p.stdout)):
        raise ValueError("Huella sin verificar. Comprueba el dedo, el lector y el registro del sistema.")


def derivar(password, salt):
    return hashlib.scrypt(password.encode(), salt=salt, n=2**16, r=8, p=1, dklen=32, maxmem=128*1024**2)


def sellar(key, policy):
    nonce = secrets.token_bytes(12)
    return nonce + AESGCM(key).encrypt(nonce, json.dumps(policy).encode(), b"perfil-v2")


class Perfil:
    def __init__(self, ruta=None):
        self.ruta = ruta or Path.home() / ".bovedawifi" / "perfil.sqlite3"
        self.ruta.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with self.db() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS perfil
                (id INTEGER PRIMARY KEY CHECK(id=1), salt BLOB, caja BLOB,
                intentos INTEGER, espera INTEGER, ultimo INTEGER)""")

    @contextmanager
    def db(self):
        conn = sqlite3.connect(self.ruta, timeout=8)
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def existe(self):
        with self.db() as conn:
            return bool(conn.execute("SELECT 1 FROM perfil").fetchone())

    def crear(self, password, policy, ultimo):
        if len(password) < 12:
            raise ValueError("Usa una contraseña de al menos 12 caracteres.")
        if not policy["huella"] and not policy["totp"]:
            raise ValueError("Activa huella o autenticador.")
        salt = secrets.token_bytes(16)
        key = derivar(password, salt)
        with self.db() as conn:
            conn.execute("INSERT INTO perfil VALUES(1,?,?,0,0,?)", (salt, sellar(key, policy), ultimo))

    def abrir(self, password, pedir_codigo, pedir_patron, pedir_huella=verificar_huella):
        with self.db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            salt, caja, fallos, espera, ultimo = conn.execute("SELECT salt,caja,intentos,espera,ultimo FROM perfil WHERE id=1").fetchone()
            ahora = int(time.time())
            if espera > ahora:
                raise ValueError(f"Acceso en pausa. Espera {espera-ahora} segundos.")
            fallos = 1 if espera else fallos + 1
            conn.execute("UPDATE perfil SET intentos=?,espera=?", (fallos, ahora+60 if fallos >= 5 else 0))
        key = derivar(password or "", salt)
        try:
            policy = json.loads(AESGCM(key).decrypt(caja[:12], caja[12:], b"perfil-v2"))
        except InvalidTag as exc:
            raise ValueError("Credenciales incorrectas.") from exc
        if policy["huella"]:
            pedir_huella()
        if policy["patron"] and not hmac.compare_digest(policy["patron"].encode(), (pedir_patron() or "").encode()):
            raise ValueError("Patrón incorrecto.")
        paso = validar_codigo(policy["totp"], pedir_codigo(), ultimo) if policy["totp"] else ultimo
        with self.db() as conn:
            ok = conn.execute("UPDATE perfil SET intentos=0,espera=0,ultimo=? WHERE caja=? AND ultimo=?", (paso, caja, ultimo))
            if ok.rowcount != 1:
                raise ValueError("El perfil cambió. Vuelve a acceder.")
        return key, caja, policy

    def actualizar(self, sesion, policy, ultimo=None):
        key, anterior, _ = sesion
        if not policy["huella"] and not policy["totp"]:
            raise ValueError("Conserva al menos un segundo factor.")
        with self.db() as conn:
            ok = conn.execute("UPDATE perfil SET caja=?,ultimo=COALESCE(?,ultimo) WHERE caja=?",
                              (sellar(key, policy), ultimo, anterior))
            if ok.rowcount != 1:
                raise ValueError("El perfil cambió. Vuelve a acceder.")


    def cambiar_password(self, sesion, password):
        if len(password) < 12:
            raise ValueError("Usa una contraseña de al menos 12 caracteres.")
        _, anterior, policy = sesion
        salt = secrets.token_bytes(16)
        nueva = sellar(derivar(password, salt), policy)
        with self.db() as conn:
            ok = conn.execute("UPDATE perfil SET salt=?,caja=? WHERE caja=?", (salt, nueva, anterior))
            if ok.rowcount != 1:
                raise ValueError("El perfil cambió. Vuelve a acceder.")
