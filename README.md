# Bóveda WiFi 2.0 · Grupo 21
Aplicación de escritorio para intercambiar archivos en una LAN privada. Cada laptop tiene una identidad RSA propia, un perfil del sistema y el registro de la clave pública de su único par. Ambas pueden enviar o recibir. Versión basada en https://github.com/Fernando-hy/21_BovedaWiFi (a5c49c773cd3678cff458856f724d3aae32bcc2e). El protocolo BVW2 requiere esta misma versión en ambos extremos.

## Instalar en cada laptop
Descomprime en una carpeta privada y con permiso de escritura, fuera de carpetas sincronizadas. Usa Python 3.12 de 64 bits, con Tk. Se necesita Internet para instalar paquetes o una colección local de ruedas compatibles. Durante el uso bastan los dos equipos y una LAN. Usa Windows con escritorio o Linux con sesión gráfica. Los archivos recibidos pueden requerir hasta 100 MiB cada uno; reserva espacio para el original, un temporal y el destino. El contenido se procesa en memoria.

Windows (CMD dentro de la carpeta del proyecto):
```bat
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m tkinter
copy .env.example .env
iniciar_windows.bat
```
Cierra la ventana de prueba de Tk antes de continuar. En Ubuntu 24.04 instala python3-venv, python3-tk y, si usarás biometría, fprintd. En Linux:
```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m tkinter
cp -n .env.example .env
bash iniciar_linux.sh
```
En una actualización conserva tu .env. Para una primera migración desde 1.0 usa una carpeta nueva y genera dos identidades nuevas. Guarda tus originales y archivos anteriores aparte. La edición 1.0 aceptaba una clave pública de destino bajo el nombre que ahora representa la pública propia.

## Registrar el acceso
1. Accede al sistema operativo con tu cuenta personal. Para usar huella, registra el dedo en las opciones biométricas de Windows o con fprintd-enroll en Linux. En Linux comprueba fprintd-verify. En Windows el lector, su controlador y las políticas deben permitir Windows Biometric Framework (WBF) a aplicaciones de escritorio. La compatibilidad de Windows Hello por sí sola no acredita acceso WBF.
2. Abre la aplicación. Crea y confirma una contraseña de al menos 12 caracteres. Elige huella y toca el sensor al cerrar el aviso. Si careces de lector compatible, puedes elegir autenticador en el alta y añadir la huella en Seguridad cuando dispongas de él.
3. Para TOTP, configura en tu teléfono una nueva cuenta basada en tiempo, SHA-1, 6 dígitos, período de 30 segundos. Escribe la semilla que aparece una sola vez y confirma un código. Mantén la hora automática. Un código aceptado no puede repetirse; espera al siguiente antes de confirmar cambios.
4. En Seguridad puedes añadir TOTP y patrón además de huella. Para activar o desactivar un factor, pulsa su botón y confirma los factores actuales. Para el patrón, selecciona de 4 a 9 puntos distintos y repite el orden. Los factores activos se acumulan. Guarda los medios de acceso. La aplicación no tiene restablecimiento remoto.

## Vincular las laptops A y B
1. En cada laptop abre Configuración → Generar / comprobar mis claves. Se generan claves/receptor_privada.pem y claves/receptor_publica.pem. Ambas son locales y distintas por equipo.
2. Lleva solamente la pública de A a B y la pública de B a A por un medio conocido. Guárdalas en una carpeta de intercambio fuera de claves/ para no sobrescribir la pública local.
3. En A abre Seguridad → Vincular clave pública del otro equipo. Confirma tu identidad, selecciona la pública de B e introduce la huella SHA-256 completa que B muestra en su pantalla de Configuración. Repite el procedimiento en B con los datos de A. El programa instala claves/par_publica.pem tras comparar. Una vinculación nueva sustituye al par previo.
4. Para probar con una laptop, vincula su propia pública y usa 127.0.0.1. Antes de la demostración física, vuelve a vincular cada laptop con la otra.

## Enviar, comprobar y detener
1. Conecta A y B a la misma WiFi privada con comunicación entre clientes. En B ejecuta ipconfig (Windows) o ip -4 addr (Linux). Identifica la IPv4 de su adaptador WiFi. En ambas apps introduce esa IP en Configuración y pulsa Aplicar a la sesión. Por defecto, TCP 5001, espera 60 s, límite 20 MiB. El receptor escucha en su propia IP.
2. En el cortafuegos de B autoriza una regla entrante para ese puerto, en el perfil privado y limitada a la IP de A. Usa únicamente redes donde tengas permiso. No hace falta abrir puertos en el router. Comprueba con PowerShell desde A: Test-NetConnection IP_DE_B -Port 5001 (con receptor en escucha). Esta comprobación abre y cierra un socket sin enviar un archivo, por lo que puede aparecer un cierre de conexión en Actividad.
3. En B abre Recibir archivos → Iniciar receptor. En A elige Enviar archivo → Buscar archivo → Cifrar y enviar. Espera «Envío confirmado». En B mira Actividad y Abrir carpeta recibidos. El prefijo aleatorio evita sobrescrituras. Compara los hashes. En Windows usa Get-FileHash -Algorithm SHA256 "ruta"; en Linux usa sha256sum "ruta".
4. Se conservan el original y la copia verificada en recibidos/. Los temporales cifrados se eliminan al salir normalmente del bloque de transferencia, también ante errores controlados. El borrado es lógico. Ante un corte de energía revisa los temporales después de detener todas las instancias. Si se pierde el acuse, verifica la copia en B antes de repetir. Un reintento es un nuevo envío y puede crear otra copia.
5. Detén el receptor antes de salir. Para invertir el sentido, usa la IP de A en ambas apps y autoriza el puerto en A. La vinculación ya sirve para ambos sentidos.

## Configuración persistente
Edita .env con la app cerrada. HOST es la IP privada del receptor o 127.0.0.1. PUERTO admite 1024–65535, TIMEOUT_SEGUNDOS 1–600 y MAX_ARCHIVO_MB 1–100 (MiB). DIRECTORIO_CLAVES, DIRECTORIO_RECIBIDOS y DIRECTORIO_TEMPORALES se resuelven desde la carpeta del proyecto salvo si indicas rutas absolutas. Los cambios de red por interfaz duran la sesión. El perfil de autenticación se crea automáticamente en .bovedawifi/perfil.sqlite3 dentro de la carpeta personal del usuario. No hay servidor SQL, servicio web, API remota ni URL de acceso. Los archivos, llaves, perfil y .env reales no deben publicarse.

## Verificar la instalación
Dentro del entorno virtual: python -m unittest discover -s tests -v. Se usan perfiles, claves y archivos temporales independientes. Consulta evidencias/ para la ejecución de referencia y manuales/ para los procedimientos con capturas. Ejecuta python frontend.py para abrir la aplicación. emisor.py y receptor.py son módulos internos, sin acceso de terminal independiente.

## Límites para la evaluación
La sesión protege el uso normal de la aplicación por el operador. Los permisos de la cuenta del sistema protegen el código, la base de perfil, la clave privada local PEM y los archivos finales. Una cuenta comprometida puede leerlos o modificarlos. Se recomienda cifrado del disco. El receptor atiende una transferencia cada vez y puede permanecer ocupado hasta el timeout. RSA estática no proporciona secreto hacia adelante. No hay revocación remota, garantía de entrega exactamente una vez ni borrado forense. Los nombres saneados se guardan con un identificador único. Detén la escucha cuando termines.

## Material académico
La memoria, los manuales y los resultados distinguen las pruebas ejecutadas de las que requieren hardware. Para completar la entrega, incorpora el formato oficial de cesión firmado por los cinco integrantes y publica en el repositorio del grupo el mismo árbol de la versión entregada, excluyendo toda credencial y archivo de prueba personal.

## Incorporar exactamente esta revisión al repositorio
El ZIP incluye, junto a la carpeta del proyecto, BovedaWiFi_v2.bundle. Contiene el commit de la entrega sobre el commit base indicado arriba. En un clon normal del repositorio original y con los cambios personales guardados, puedes crear una rama local con la versión exacta:
```sh
git bundle verify "/ruta/al/BovedaWiFi_v2.bundle"
git fetch "/ruta/al/BovedaWiFi_v2.bundle" refs/heads/entrega-v2:refs/heads/boveda-v2
git switch boveda-v2
git rev-parse HEAD
```
En Windows sustituye la ruta por la ubicación real del bundle. El equipo puede revisar y publicar esa rama desde su cuenta de GitHub. Para instalar desde el ZIP no necesitas usar Git ni abrir el bundle.
