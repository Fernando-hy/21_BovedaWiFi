"""Verificación de la huella de la cuenta interactiva mediante Windows Biometric Framework."""
import ctypes as ct
from ctypes import wintypes as wt
import threading


def verificar():
    bio = ct.WinDLL("winbio.dll")
    adv = ct.WinDLL("advapi32.dll", use_last_error=True)
    kernel = ct.WinDLL("kernel32.dll", use_last_error=True)

    def api(dll, nombre, tipo, *args):
        funcion = getattr(dll, nombre)
        funcion.restype, funcion.argtypes = tipo, args
        return funcion

    puntero = ct.c_void_p
    ulong = wt.DWORD
    p32 = ct.POINTER(ulong)
    actual = api(kernel,"GetCurrentProcess",wt.HANDLE)
    cerrar = api(kernel,"CloseHandle",wt.BOOL,wt.HANDLE)
    abrir_token = api(adv,"OpenProcessToken",wt.BOOL,wt.HANDLE,ulong,ct.POINTER(wt.HANDLE))
    info = api(adv,"GetTokenInformation",wt.BOOL,wt.HANDLE,ct.c_int,puntero,ulong,p32)
    longitud = api(adv,"GetLengthSid",ulong,puntero)
    token = wt.HANDLE()
    if not abrir_token(actual(), 8, ct.byref(token)):  # TOKEN_QUERY
        raise ct.WinError(ct.get_last_error())
    try:
        size = ulong()
        info(token, 1, None, 0, ct.byref(size))  # TokenUser
        buffer = ct.create_string_buffer(size.value)
        if not info(token, 1, buffer, size, ct.byref(size)):
            raise ct.WinError(ct.get_last_error())
        sid = puntero.from_buffer(buffer).value
        largo = longitud(sid)
        if not 0 < largo <= 68:
            raise ValueError("El SID de la cuenta no es válido.")
        class Identidad(ct.Structure):
            _fields_ = [("tipo",ulong),("longitud",ulong),("sid",ct.c_ubyte*68)]
        identidad = Identidad(3,largo)
        ct.memmove(identidad.sid,sid,largo)
    finally:
        cerrar(token)
    abrir = api(bio,"WinBioOpenSession",ct.c_long,ulong,ulong,ulong,puntero,ct.c_size_t,puntero,p32)
    validar = api(bio,"WinBioVerify",ct.c_long,ulong,puntero,ct.c_ubyte,p32,ct.POINTER(ct.c_ubyte),p32)
    cancelar = api(bio,"WinBioCancel",ct.c_long,ulong)
    fin = api(bio,"WinBioCloseSession",ct.c_long,ulong)
    sesion, unidad, razon, match = ulong(), ulong(), ulong(), ct.c_ubyte()
    # Huella, grupo del sistema, opciones por defecto, WINBIO_DB_DEFAULT.
    hr = abrir(8,1,0,None,0,puntero(1),ct.byref(sesion))
    if hr:
        raise ValueError(f"Lector WBF no disponible (0x{hr & 0xffffffff:08X}).")
    timer = threading.Timer(45,cancelar,args=(sesion,))
    try:
        timer.start()
        hr = validar(sesion,ct.byref(identidad),255,ct.byref(unidad),ct.byref(match),ct.byref(razon))
        if hr or not match.value:
            raise ValueError(f"Huella sin verificar (0x{hr & 0xffffffff:08X}).")
    finally:
        timer.cancel()
        timer.join()
        fin(sesion)
