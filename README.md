# Proyecto: Bóveda WiFi - Grupo 21

El repositorio se denomina **`21_BovedaWiFi`**, siguiendo la estructura `NumeroGrupo_TituloProyecto`.

## Descripción

Bóveda WiFi es un sistema cliente-servidor de escritorio, operado mediante terminal, para transferir archivos de forma segura entre dispositivos conectados a una misma red WiFi local. También permite ejecutar el emisor y el receptor en un solo equipo mediante localhost.

La comunicación se realiza directamente mediante TCP/IP y sockets, sin depender de servicios externos de almacenamiento ni servidores en la nube durante la transferencia.

El sistema utiliza AES-256-GCM para cifrar el archivo, RSA-OAEP para proteger la clave AES y SHA-256 para verificar la integridad. Al terminar, elimina las copias temporales generadas por la aplicación y conserva el archivo original y la copia final verificada.

**En esta versión, la autenticación mediante huella dactilar está simulada en terminal. No se captura una huella real ni se requiere un sensor biométrico.**

## Integrantes - Sección B

- Ccma Palomino, Leao Darwin
- Hinostroza Yauri, Fernando Jesús
- Hualpa Arias, Andy Richardson
- Machaca Orosco, Anthony Jhayr
- Rivera Carbajal, Rodrigo Yazid

## Tecnologías

- Python 3.
- WiFi, TCP/IP y sockets IPv4.
- PyCryptodome 3.23.0: AES-256-GCM y RSA de 3072 bits con OAEP/SHA-256.
- python-dotenv 1.2.1 para cargar las variables de entorno.
- SHA-256 para verificar la integridad.
- Windows / Linux.
- Visual Studio Code y Wireshark como herramientas opcionales.

## Seguridad

- Cifrado del contenido y sus metadatos mediante AES-256-GCM.
- Protección de la clave AES mediante RSA-OAEP con SHA-256.
- Verificación de la etiqueta GCM y del hash SHA-256 antes de guardar el archivo final.
- Simulación biométrica previa al envío.
- Eliminación automática de copias temporales cifradas.
- Confirmación cifrada del receptor después de guardar el archivo y limpiar sus temporales.
- Claves RSA generadas localmente: no se incluyen claves ni credenciales reales en el repositorio.

La simulación biométrica no autentica una identidad real. El borrado de temporales es lógico y no constituye un borrado forense. El archivo final recibido se conserva, sin caducidad automática.

## Requisitos

### Hardware

- Un PC o laptop para una prueba en localhost.
- Dos PC o laptops para una prueba entre dispositivos.
- Un router o punto de acceso WiFi para la prueba en LAN.
- Adaptador o tarjeta WiFi en cada equipo, según disponibilidad.
- Se recomiendan 2 GB de RAM y 500 MB libres, además del espacio para los archivos recibidos.

El sensor de huella, controlador, cables y fuente de alimentación del diseño original corresponden a una futura integración biométrica real; no son necesarios para ejecutar este prototipo.

### Software

- Windows 11 o Linux.
- Python 3.10 o superior; recomendado Python 3.12.
- pip y venv.
- Git para clonar el repositorio.
- Dependencias indicadas en `requirements.txt`.
- Visual Studio Code y Wireshark, opcionales.

No se requiere base de datos ni servidor web. El puerto predeterminado es TCP 5001. El límite por archivo es 20 MiB, configurable entre 1 y 100 MiB.

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/Fernando-hy/21_BovedaWiFi.git
cd 21_BovedaWiFi
```

### 2. Crear y activar un entorno virtual

Windows CMD:

```bat
python --version
python -m venv .venv
.venv\Scripts\activate.bat
```

Linux Bash:

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
```

En los pasos siguientes, ejecutar `python` y `pip` con el entorno virtual activado.

### 3. Instalar las dependencias

```bash
pip install -r requirements.txt
python -m pip check
```

### 4. Configurar las variables de entorno

En una instalación nueva, renombrar `.env.example` a `.env`. Si ya existe `.env`, conservarlo y revisar su configuración.

Windows CMD:

```bat
ren .env.example .env
```

Linux Bash:

```bash
mv -n .env.example .env
```

Para una prueba en un solo equipo, mantener:

```dotenv
HOST=127.0.0.1
PUERTO=5001
TIMEOUT_SEGUNDOS=60
MAX_ARCHIVO_MB=20
DIRECTORIO_CLAVES=claves
DIRECTORIO_RECIBIDOS=recibidos
DIRECTORIO_TEMPORALES=temporales
```

Para dos equipos en la misma WiFi, configurar `HOST` en ambos con la IPv4 privada real del receptor y mantener el mismo puerto. Permitir TCP 5001 en el firewall del receptor para la LAN. La red debe permitir comunicación entre sus dispositivos.

Las rutas relativas se resuelven respecto de la carpeta del proyecto. Las variables definidas en el sistema tienen prioridad sobre `.env`.

### 5. Generar las claves RSA locales

Ejecutar únicamente en el receptor:

```bash
python utils_crypto.py --generar-claves
python utils_crypto.py --huella
```

Se crean `claves/receptor_privada.pem` y `claves/receptor_publica.pem`. Si existe un par válido, se conserva.

- **Localhost:** los dos procesos utilizan la misma carpeta `claves`.
- **Dos equipos:** copiar únicamente `receptor_publica.pem` a la carpeta `claves` del emisor por un medio confiable. Ejecutar `python utils_crypto.py --huella` en ambos equipos y comparar sus resultados por un canal independiente. Deben coincidir antes de transferir archivos.

La clave privada permanece en el receptor. No subir `.env`, claves, archivos recibidos ni temporales a GitHub; utilizar el `.gitignore` incluido.

### 6. Comprobar la sintaxis

```bash
python -m py_compile utils_crypto.py emisor.py receptor.py
```

El comando debe finalizar sin errores. Python no requiere una compilación de despliegue previa.

## Ejecución

### 1. Iniciar el receptor

En la primera terminal, con el entorno virtual activado:

```bash
python receptor.py
```

Debe aparecer:

```text
[LISTO] Receptor escuchando en 127.0.0.1:5001
```

En una prueba LAN, el mensaje mostrará la IP configurada. Mantener esta terminal abierta.

### 2. Iniciar el emisor

Abrir una segunda terminal en la carpeta del proyecto y activar el entorno virtual con el comando correspondiente del paso 2 de instalación. En una prueba LAN, ejecutar esta parte en el equipo emisor.

Crear y enviar un archivo de prueba:

```bash
python -c "from pathlib import Path; Path('prueba.txt').write_text('Archivo de prueba de Boveda WiFi.\n', encoding='utf-8')"
python emisor.py prueba.txt
```

Para enviar otro archivo, indicar su ruta:

```bash
python emisor.py "ruta/al/archivo.pdf"
```

### 3. Aprobar la simulación biométrica

Cuando aparezca la solicitud en terminal, introducir `1` y Enter para simular una huella autorizada. Introducir `2` o cualquier otra entrada deniega el envío.

### 4. Verificar la transferencia

El receptor debe mostrar:

```text
[OK] AES-256-GCM y SHA-256 verificados.
[OK] Archivo final guardado: ...
[OK] Temporales del receptor eliminados.
[OK] Confirmacion cifrada enviada.
```

El emisor debe mostrar:

```text
[OK] Receptor confirmo SHA-256 y limpieza de sus temporales.
[OK] Temporales del emisor eliminados.
[OK] Transferencia completada. SHA-256: ...
```

Los hashes impresos por ambos procesos deben coincidir. El archivo final se guarda en `recibidos/<identificador>_prueba.txt` y la carpeta `temporales` debe quedar vacía en ambos equipos. El original permanece en el emisor.

Si se pierde la confirmación, revisar la terminal y los archivos del receptor antes de repetir el envío. Detener el receptor con Ctrl+C.

Consultar [Protocolo_de_Implementacion.md](Protocolo_de_Implementacion.md) para los diez pasos de la rúbrica y los detalles del protocolo. La implementación se probó en Linux con Python 3.12.14; la prueba en Windows y entre dos equipos WiFi debe realizarse en el entorno de presentación.
