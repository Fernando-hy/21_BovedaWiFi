# Proyecto: Bóveda WiFi - Grupo 21

## Descripción

Bóveda WiFi es un sistema cliente-servidor de escritorio con interfaz gráfica y ejecución alternativa mediante terminal, para transferir archivos de forma segura entre dispositivos conectados a una misma red WiFi local. También permite ejecutar el emisor y el receptor en un solo equipo mediante localhost.

La comunicación se realiza directamente mediante TCP/IP y sockets, sin depender de servicios externos de almacenamiento ni servidores en la nube durante la transferencia.

El sistema utiliza AES-256-GCM para cifrar el archivo, RSA-OAEP para proteger la clave AES y SHA-256 para verificar la integridad. Al terminar, elimina las copias temporales generadas por la aplicación y conserva el archivo original y la copia final verificada.

**En esta versión, la autenticación mediante huella dactilar está simulada mediante botones en la interfaz gráfica o una opción en terminal. No se captura una huella real ni se requiere un sensor biométrico.**

## Integrantes - Sección B

- Ccma Palomino, Leao Darwin
- Hinostroza Yauri, Fernando Jesús
- Hualpa Arias, Andy Richardson
- Machaca Orosco, Anthony Jhayr
- Rivera Carbajal, Rodrigo Yazid

## Tecnologías

- Python 3.
- Tkinter y ttk para la interfaz gráfica de escritorio.
- WiFi, TCP/IP y sockets IPv4.
- PyCryptodome 3.23.0: AES-256-GCM y RSA de 3072 bits con OAEP/SHA-256.
- python-dotenv 1.0.1 para cargar las variables de entorno, según requirements.txt.
- SHA-256 para verificar la integridad.
- Windows / Linux.
- Visual Studio Code y Wireshark como herramientas opcionales.

## Seguridad

- Cifrado del contenido y sus metadatos mediante AES-256-GCM.
- Protección de la clave AES mediante RSA-OAEP con SHA-256.
- Verificación de la etiqueta GCM y del hash SHA-256 antes de guardar el archivo final.
- Control de acceso simulado en la interfaz y simulación biométrica previa al envío en terminal.
- Eliminación automática de copias temporales cifradas.
- Confirmación cifrada del receptor después de guardar el archivo y limpiar sus temporales.
- Claves RSA generadas localmente: no se incluyen claves ni credenciales reales en el repositorio.

La simulación biométrica no autentica una identidad real ni al emisor remoto. El borrado de temporales es lógico y no constituye un borrado forense. El archivo final recibido se conserva, sin caducidad automática.

## Requisitos

### Hardware

- Un PC o laptop para una prueba en localhost.
- Dos PC o laptops para una prueba entre dispositivos.
- Un router o punto de acceso WiFi para la prueba en LAN.
- Adaptador o tarjeta WiFi en cada equipo, según disponibilidad.
- Se recomiendan 2 GB de RAM y 500 MB libres, además del espacio para los archivos recibidos.

El sensor de huella, controlador, cables y fuente de alimentación del diseño original corresponden a una futura integración biométrica real; no son necesarios para ejecutar este prototipo.

### Software

- Windows 11 o Linux con un entorno gráfico para abrir el frontend.
- Python 3.10 o superior; recomendado Python 3.12 de 64 bits.
- pip y venv.
- Tkinter, normalmente incluido en Python para Windows. En Linux puede requerir instalar el paquete correspondiente a la versión de Python utilizada.
- Git para clonar el repositorio.
- Dependencias indicadas en requirements.txt.
- Visual Studio Code y Wireshark, opcionales.

No se requiere base de datos ni servidor web. El puerto predeterminado es TCP 5001. El límite por archivo es 20 MiB, configurable entre 1 y 100 MiB.

## Archivos principales

| Archivo | Función |
| --- | --- |
| frontend.py | Interfaz gráfica: acceso, inicio, envío, recepción, actividad, configuración y ayuda. |
| emisor.py | Envío seguro, utilizado por la interfaz y por la terminal. |
| receptor.py | Recepción segura, utilizada por la interfaz y por la terminal. |
| utils_crypto.py | Criptografía, configuración y protocolo TCP. |
| requirements.txt | Dependencias del proyecto. |
| .env.example | Plantilla de configuración local. |
| .gitignore | Exclusión de claves, configuración local y archivos de trabajo. |
| iniciar_windows.bat | Iniciador de la interfaz para Windows. |
| iniciar_linux.sh | Iniciador de la interfaz para Linux. |

frontend.py, emisor.py, receptor.py y utils_crypto.py deben estar en la misma carpeta. Utilizar las versiones de emisor.py y receptor.py adaptadas al frontend. No se necesitan carpetas docs ni tests para ejecutar la aplicación.

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/Fernando-hy/21_BovedaWiFi.git
cd 21_BovedaWiFi
```

También puede descargarse el ZIP del repositorio, descomprimirlo y abrir una terminal dentro de la carpeta que contiene frontend.py.

### 2. Crear y activar un entorno virtual

Windows CMD, con Python 3.12 instalado:

```bat
py -3.12 --version
py -3.12 -m venv .venv
.venv\Scripts\activate.bat
```

Linux Bash, con Python 3.12 instalado:

```bash
python3.12 --version
python3.12 -m venv .venv
source .venv/bin/activate
```

Si ya existe un entorno compatible, basta con activarlo. Si se creó con una versión antigua de Python, salir con deactivate y renombrar o conservar su carpeta antes de crear el nuevo entorno.

En los pasos siguientes, ejecutar python con el entorno virtual activado. Comprobar la versión utilizada:

```bash
python --version
```

### 3. Instalar las dependencias

Actualizar las herramientas de instalación:

```bash
python -m pip install --upgrade pip setuptools wheel
```

Instalar las dependencias y verificar su consistencia:

```bash
python -m pip install --only-binary=pycryptodome -r requirements.txt
python -m pip check
```

La opción --only-binary=pycryptodome solicita una distribución precompilada para esa dependencia. Si no encuentra una compatible, revisar la versión y arquitectura de Python y comprobar que pip esté actualizado. Para esta instalación se recomienda Python 3.12 de 64 bits.

Comprobar las importaciones:

```bash
python -c "from Crypto.Cipher import AES; import dotenv; import tkinter; print('Dependencias disponibles')"
```

En Ubuntu/Debian, si falta Tkinter, instalar el paquete python3-tk correspondiente al intérprete utilizado mediante el gestor de paquetes del sistema.

### 4. Configurar las variables de entorno

En una instalación nueva, copiar .env.example a .env. Si ya existe .env, conservarlo y revisar su configuración.

Windows CMD:

```bat
if not exist .env copy .env.example .env
```

Linux Bash:

```bash
[ -f .env ] || cp .env.example .env
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

Para dos equipos en la misma WiFi, configurar HOST en ambos con la IPv4 privada real del receptor y mantener el mismo puerto. Permitir TCP 5001 en el firewall del receptor para la LAN. La red debe permitir comunicación entre sus dispositivos.

Las rutas relativas se resuelven respecto de la carpeta del proyecto. Las variables definidas en el sistema tienen prioridad sobre .env.

No subir .env a GitHub; publicar únicamente .env.example. Tampoco subir el entorno virtual, claves, archivos recibidos ni temporales.

### 5. Comprobar la sintaxis

```bash
python -m py_compile frontend.py utils_crypto.py emisor.py receptor.py
```

El comando debe finalizar sin errores. Python no requiere una compilación de despliegue previa.

## Ejecución del frontend

### 1. Abrir la interfaz gráfica

Desde la carpeta del proyecto, con el entorno virtual activado:

```bash
python frontend.py
```

Después de instalar las dependencias, también puede abrirse mediante iniciar_windows.bat en Windows o mediante el siguiente comando en Linux:

```bash
bash iniciar_linux.sh
```

### 2. Acceder al sistema

- Pulsar **Simular huella autorizada** para abrir el panel principal.
- Pulsar **Simular acceso denegado** para comprobar el bloqueo del acceso.

Esta acción es una simulación; no se verifica una identidad biométrica real.

### 3. Configurar la conexión y las claves

Abrir **Configuración** y revisar la IP del receptor, el puerto, el tiempo de espera y el límite por archivo. Pulsar **Aplicar a la sesión** para utilizar los cambios.

Para una prueba en un solo equipo, usar 127.0.0.1 y el puerto 5001. Pulsar **Generar / comprobar claves del receptor** para preparar el par RSA. Si existe un par válido, se conserva.

Para dos equipos, generar las claves únicamente en el receptor. Copiar solo claves/receptor_publica.pem al emisor por un medio confiable y comparar las huellas SHA-256 de las claves públicas por un canal independiente. La clave privada permanece en el receptor.

Los parámetros modificados en la interfaz duran la sesión actual. Para conservar la configuración al reiniciar, modificar el archivo .env local.

### 4. Iniciar la recepción

En el equipo receptor, abrir **Recibir archivos** y pulsar **Iniciar receptor**. La IP de escucha debe pertenecer a ese equipo. Esperar a que aparezca el estado de escucha.

Cuando se utiliza el receptor desde la interfaz, no iniciar además receptor.py en otra terminal con el mismo puerto.

### 5. Enviar un archivo

En el emisor:

1. Abrir **Enviar archivo**.
2. Pulsar **Buscar archivo** y seleccionar el archivo.
3. Revisar el destino y el límite de tamaño.
4. Pulsar **Cifrar y enviar**.
5. Esperar el resultado de la operación.

Para localhost, puede iniciarse el receptor y realizarse el envío desde la misma ventana. Entre dos equipos, abrir el frontend en ambos, iniciar la recepción en uno y enviar desde el otro.

### 6. Verificar el resultado

En **Actividad**, seleccionar la operación para consultar su resultado y el hash SHA-256. En una recepción verificada también se muestra la ruta del archivo final.

- **Envío confirmado:** el emisor recibió y validó la confirmación cifrada del receptor.
- **Recepción verificada:** el archivo se guardó después de validar su integridad, se limpiaron los temporales y se envió la confirmación.
- **Envío no confirmado:** revisar el motivo y comprobar el receptor antes de repetir, porque podría haber guardado el archivo aunque no llegara la confirmación al emisor.

El original permanece en el emisor y la copia final verificada se conserva en recibidos. El historial se mantiene en memoria y se borra al cerrar la sesión.

### 7. Finalizar

En **Recibir archivos**, pulsar **Detener receptor**. Si existe una transferencia activa, el cierre espera a que termine o venza su tiempo de espera. Esperar también que finalice cualquier envío antes de cerrar la sesión o salir.

## Ejecución alternativa mediante terminal

La interfaz gráfica y los comandos de terminal comparten las funciones de transferencia. Para trabajar por terminal, detener primero el receptor de la interfaz si utiliza el mismo puerto.

### 1. Preparar las claves en el receptor

```bash
python utils_crypto.py --generar-claves
python utils_crypto.py --huella
```

Se crean claves/receptor_privada.pem y claves/receptor_publica.pem. En dos equipos, copiar solo la pública al emisor y comparar las huellas antes de transferir.

### 2. Iniciar el receptor

En una terminal con el entorno activado:

```bash
python receptor.py
```

Debe aparecer el mensaje de escucha con la IP y el puerto configurados. Mantener esa terminal abierta.

### 3. Iniciar el emisor

En otra terminal con el entorno activado:

```bash
python emisor.py "ruta/al/archivo.pdf"
```

Introducir 1 y Enter para simular una huella autorizada. Cualquier otra entrada deniega el envío.

### 4. Verificar y finalizar

Comprobar los mensajes de integridad, guardado, limpieza de temporales y transferencia completada. Los hashes impresos por ambos procesos deben coincidir.

Si se pierde la confirmación, revisar el receptor antes de repetir el envío. Detener el receptor con Ctrl+C.
