"""Pruebas locales con dos directorios de claves independientes y TCP real."""
import contextlib
import io
import multiprocessing as mp
import os
import queue
import shutil
import socket
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import emisor
import identidad
import receptor
import utils_crypto as c


def config(base, puerto):
    from types import SimpleNamespace
    return SimpleNamespace(claves=base/"claves", recibidos=base/"recibidos", temporales=base/"temporales",
                           host="127.0.0.1", puerto=puerto, maximo=1048576, timeout=4)


def servidor(conf, stop, cola):
    receptor.ejecutar(conf, stop, lambda nombre, datos: cola.put((nombre, datos)))


class Transporte(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        base = Path(cls.tmp.name)
        cls.a, cls.b = config(base/"a",0), config(base/"b",0)
        for conf in [cls.a, cls.b]:
            c.generar_claves(conf.claves)
        for local, otro in [(cls.a,cls.b),(cls.b,cls.a)]:
            shutil.copy(otro.claves/"receptor_publica.pem",local.claves/"par_publica.pem")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def transferir(self, origen, destino, datos, acepta=True):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1",0))
            origen.puerto = destino.puerto = sock.getsockname()[1]
        archivo = origen.claves.parent/"muestra.bin"
        archivo.write_bytes(datos)
        ctx = mp.get_context("spawn")
        stop, cola = ctx.Event(), ctx.Queue()
        proc = ctx.Process(target=servidor,args=(destino,stop,cola))
        proc.start()
        try:
            self.assertEqual(cola.get(timeout=10)[0],"escuchando")
            if acepta:
                r = emisor.enviar_archivo(archivo, origen, lambda: None)
                self.assertEqual(r["sha256"], c.sha256(datos))
                self.assertEqual(cola.get(timeout=5)[0],"actividad")
                evento, recibo = cola.get(timeout=5)
                self.assertEqual(evento,"recibido")
                self.assertEqual(Path(recibo["ruta"]).read_bytes(), datos)
            else:
                antes = set(destino.recibidos.glob("*"))
                with self.assertRaises((OSError,ValueError)):
                    emisor.enviar_archivo(archivo, origen, lambda: None)
                self.assertEqual(cola.get(timeout=5)[0],"actividad")
                self.assertEqual(cola.get(timeout=5)[0],"error_recepcion")
                self.assertEqual(antes,set(destino.recibidos.glob("*")))
            self.assertEqual(archivo.read_bytes(),datos)
            for conf in (origen,destino):
                self.assertEqual(list(conf.temporales.iterdir()),[])
        finally:
            stop.set()
            proc.join(6)
            if proc.is_alive():
                proc.terminate()
                proc.join()
            cola.close()

    def test_dos_sentidos_y_limite(self):
        self.transferir(self.a,self.b,bytes(range(256))*4096)
        self.transferir(self.b,self.a,b"")

    def test_equipo_no_vinculado(self):
        ruta = self.b.claves/"par_publica.pem"
        anterior = ruta.read_bytes()
        try:
            shutil.copy(self.b.claves/"receptor_publica.pem",ruta)
            self.transferir(self.a,self.b,b"privado",False)
        finally:
            ruta.write_bytes(anterior)

    def test_gcm_rechaza_alteracion(self):
        key = c.generar_clave_aes()
        trama = bytearray(c.cifrar_aes(b"ejemplo",key,b"reto"))
        trama[-1] ^= 1
        with self.assertRaises(ValueError):
            c.descifrar_aes(bytes(trama),key,b"reto")

    def test_limite_antes_de_enviar(self):
        ruta=self.a.claves.parent/"grande.bin"
        ruta.write_bytes(bytes(self.a.maximo+1))
        with self.assertRaisesRegex(ValueError,"limite"):
            emisor.enviar_archivo(ruta,self.a,lambda: None)


class Seguridad(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.p=identidad.Perfil(Path(self.tmp.name)/"perfil.sqlite3")
        self.pw=os.urandom(20).hex()
        self.seed=identidad.nueva_semilla()
        self.p.crear(self.pw,{"huella":False,"totp":self.seed,"patron":"3197"},-1)

    def abrir(self, pw=None, patron="3197"):
        return self.p.abrir(pw or self.pw,lambda:identidad.codigo(self.seed,int(time.time())//30),lambda:patron)

    def test_login_replay_y_patron(self):
        with self.assertRaisesRegex(ValueError,"Patrón"):
            self.abrir(patron="1234")
        with patch("identidad.time.time",return_value=1800000000):
            self.abrir()
            with self.assertRaisesRegex(ValueError,"utilizado"):
                self.abrir()

    def test_bloqueo_persistente(self):
        for _ in range(5):
            with self.assertRaisesRegex(ValueError,"Credenciales"):
                self.abrir("incorrecta")
        self.p=identidad.Perfil(self.p.ruta)
        with self.assertRaisesRegex(ValueError,"pausa"):
            self.abrir()

    def test_vector_rfc(self):
        import base64
        seed=base64.b32encode(b"12345678901234567890").decode()
        self.assertEqual(identidad.codigo(seed,1),"287082")

    def test_factor_obligatorio(self):
        sesion=self.abrir()
        with self.assertRaises(ValueError):
            self.p.actualizar(sesion,{"huella":False,"totp":None,"patron":"3197"})

    def test_fallo_lector_cierra_acceso(self):
        perfil={"huella":True,"totp":None,"patron":None}
        self.p.actualizar(self.abrir(),perfil)
        def sin_lector():
            raise ValueError("sin lector")
        with self.assertRaisesRegex(ValueError,"sin lector"):
            self.p.abrir(self.pw,lambda:None,lambda:None,sin_lector)


if __name__=="__main__":
    unittest.main()
