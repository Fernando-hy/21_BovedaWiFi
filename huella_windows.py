"""Identificación con el lector de Windows y comprobación de la cuenta local."""
import ctypes as ct
from ctypes import wintypes as wt
import threading

DWORD = ct.c_uint32
HRESULT = ct.c_int32
PUNTERO = ct.c_void_p
PDWORD = ct.POINTER(DWORD)
SID_MAX = 68
TIPO_SID = 3

ERRORES_LECTURA = {
    0x80098003: "Windows no reconoció una huella registrada para este lector.",
    0x80098004: "La lectura se canceló o se agotó el tiempo. Vuelve a intentarlo.",
    0x80098005: "Windows no encontró una coincidencia para la huella.",
    0x80098008: "El lector no pudo capturar bien la huella. Vuelve a colocar el dedo.",
}


class IdentidadBiometrica(ct.Structure):
    # Tamaño y desplazamientos de WINBIO_IDENTITY cuando Value contiene AccountSid.
    _fields_ = [("tipo", DWORD), ("longitud", DWORD), ("datos", ct.c_ubyte * SID_MAX)]


def _api(dll, nombre, resultado, *argumentos):
    funcion = getattr(dll, nombre)
    funcion.restype = resultado
    funcion.argtypes = argumentos
    return funcion


def _sid_de_la_cuenta():
    advapi = ct.WinDLL("advapi32.dll", use_last_error=True)
    kernel = ct.WinDLL("kernel32.dll", use_last_error=True)
    actual = _api(kernel, "GetCurrentProcess", wt.HANDLE)
    cerrar = _api(kernel, "CloseHandle", wt.BOOL, wt.HANDLE)
    abrir = _api(advapi, "OpenProcessToken", wt.BOOL, wt.HANDLE, DWORD, ct.POINTER(wt.HANDLE))
    info = _api(advapi, "GetTokenInformation", wt.BOOL, wt.HANDLE, ct.c_int, PUNTERO, DWORD, PDWORD)
    longitud = _api(advapi, "GetLengthSid", DWORD, PUNTERO)
    token = wt.HANDLE()
    if not abrir(actual(), 8, ct.byref(token)):  # TOKEN_QUERY
        raise ct.WinError(ct.get_last_error())
    try:
        size = DWORD()
        info(token, 1, None, 0, ct.byref(size))  # TokenUser
        if not size.value:
            raise ct.WinError(ct.get_last_error())
        buffer = ct.create_string_buffer(size.value)
        if not info(token, 1, buffer, size, ct.byref(size)):
            raise ct.WinError(ct.get_last_error())
        sid = PUNTERO.from_buffer(buffer).value
        largo = longitud(sid) if sid else 0
        if not 8 <= largo <= SID_MAX:
            raise ValueError("Windows no devolvió un SID válido para esta cuenta.")
        return ct.string_at(sid, largo)
    finally:
        cerrar(token)


def _validar_identidad(identidad, sid_actual):
    if (identidad.tipo != TIPO_SID or identidad.longitud != len(sid_actual)
            or bytes(identidad.datos[:identidad.longitud]) != sid_actual):
        raise ValueError("La huella identificada no pertenece a la cuenta de Windows que abrió Bóveda WiFi.")


def verificar():
    sid_actual = _sid_de_la_cuenta()
    bio = ct.WinDLL("winbio.dll")
    abrir = _api(bio, "WinBioOpenSession", HRESULT, DWORD, DWORD, DWORD, PUNTERO, ct.c_size_t, PUNTERO, PDWORD)
    identificar = _api(bio, "WinBioIdentify", HRESULT, DWORD, PDWORD,
                       ct.POINTER(IdentidadBiometrica), ct.POINTER(ct.c_ubyte), PDWORD)
    cancelar = _api(bio, "WinBioCancel", HRESULT, DWORD)
    cerrar = _api(bio, "WinBioCloseSession", HRESULT, DWORD)
    sesion, unidad, rechazo = DWORD(), DWORD(), DWORD()
    identidad, dedo = IdentidadBiometrica(), ct.c_ubyte()
    # Huella, grupo del sistema, opciones por defecto y base predeterminada del sistema.
    hr = abrir(8, 1, 0, None, 0, None, ct.byref(sesion))
    if hr:
        raise ValueError(f"Lector biométrico de Windows no disponible (0x{hr & 0xffffffff:08X}).")
    timer = threading.Timer(45, cancelar, args=(sesion,))
    try:
        timer.start()
        hr = identificar(sesion, ct.byref(unidad), ct.byref(identidad), ct.byref(dedo), ct.byref(rechazo))
        if hr:
            codigo = hr & 0xffffffff
            mensaje = ERRORES_LECTURA.get(codigo, "Windows no pudo completar la identificación.")
            if codigo == 0x80098008:
                mensaje += f" Detalle de captura: {rechazo.value}."
            raise ValueError(f"{mensaje} (0x{codigo:08X})")
        _validar_identidad(identidad, sid_actual)
    finally:
        timer.cancel()
        if timer.ident is not None:
            timer.join()
        cerrar(sesion)
