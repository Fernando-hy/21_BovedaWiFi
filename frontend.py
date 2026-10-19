"""Interfaz de escritorio de Boveda WiFi. Ejecutar: python frontend.py."""

import copy
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import emisor
import receptor
import utils_crypto as crypto

FONDO = "#f3f6fa"
TEXTO = "#17253d"
AZUL = "#245eea"
GRIS = "#58677e"


class BovedaApp(tk.Tk):
    def __init__(self, config=None):
        super().__init__()
        self.title("Bóveda WiFi | Grupo 21")
        self.geometry("1140x800")
        self.minsize(1040, 760)
        self.configure(bg=FONDO)
        self.config_actual = config or crypto.configuracion()
        self.autorizado = False
        self.archivo = None
        self.historial = []
        self.eventos = queue.Queue()
        self.ocupado = False
        self.receptor_activo = False
        self.detener = threading.Event()
        self.vista_actual = ""
        self.estado_receptor = "Receptor detenido"
        self.mensaje_acceso = tk.StringVar(value="Elige una opción para probar el control de acceso.")
        self.estado_envio = tk.StringVar(value="Selecciona un archivo para comenzar.")
        self.estado_sistema = tk.StringVar(value="Sesión local · Sin servicios en la nube")
        self._estilo()
        self.lateral = tk.Frame(self, bg="#111e34", width=225)
        self.lateral.pack(side="left", fill="y")
        self.lateral.pack_propagate(False)
        tk.Label(self.lateral, text="BÓVEDA WiFi", bg="#111e34", fg="white",
                 font=("DejaVu Sans", 16, "bold")).pack(anchor="w", padx=20, pady=(30, 5))
        tk.Label(self.lateral, text="TRANSFERENCIA LOCAL SEGURA", bg="#111e34", fg="#98add0",
                 font=("DejaVu Sans", 8)).pack(anchor="w", padx=20, pady=(0, 30))
        self.botones_menu = {}
        for nombre in ("Inicio", "Enviar archivo", "Recibir archivos", "Actividad", "Configuración", "Ayuda"):
            boton = tk.Button(self.lateral, text=nombre, anchor="w", padx=20, pady=13,
                              bd=0, bg="#111e34", fg="#c0cee4", activebackground="#233b5f",
                              activeforeground="white", font=("DejaVu Sans", 10),
                              command=lambda n=nombre: self.mostrar(n))
            boton.pack(fill="x", padx=12, pady=3)
            self.botones_menu[nombre] = boton
        tk.Button(self.lateral, text="Cerrar sesión", command=self.cerrar_sesion,
                  bg="#233b5f", fg="white", bd=0, pady=10).pack(side="bottom", fill="x", padx=20, pady=20)
        tk.Label(self.lateral, text="GRUPO 21  /  SECCIÓN B\nPrototipo académico", justify="left",
                 bg="#111e34", fg="#98add0", font=("DejaVu Sans", 9)).pack(side="bottom", anchor="w", padx=20)
        self.derecha = tk.Frame(self, bg=FONDO)
        self.derecha.pack(side="right", fill="both", expand=True)
        tk.Label(self.derecha, textvariable=self.estado_sistema, bg="white", fg=GRIS,
                 anchor="w", padx=28, pady=17, font=("DejaVu Sans", 10)).pack(fill="x")
        self.cuerpo = tk.Frame(self.derecha, bg=FONDO)
        self.cuerpo.pack(fill="both", expand=True, padx=28, pady=22)
        self.protocol("WM_DELETE_WINDOW", self.cerrar)
        self.mostrar("Acceso")
        self.after(80, self.procesar_eventos)

    def _estilo(self):
        self.option_add("*Font", ("DejaVu Sans", 10))
        estilo = ttk.Style(self)
        estilo.theme_use("clam")
        estilo.configure("TButton", padding=(14, 10), font=("DejaVu Sans", 10))
        estilo.configure("Principal.TButton", background=AZUL, foreground="white", borderwidth=0)
        estilo.map("Principal.TButton", background=[("active", "#194bc2"), ("disabled", "#b5c4df")])
        estilo.configure("TEntry", padding=8)
        estilo.configure("Treeview", rowheight=34, font=("DejaVu Sans", 9))
        estilo.configure("Treeview.Heading", font=("DejaVu Sans", 9, "bold"), padding=8)

    def texto(self, padre, texto, tam=11, color=TEXTO, negrita=False):
        label = tk.Label(padre, text=texto, bg=padre["bg"], fg=color, anchor="w", justify="left",
                         wraplength=760, font=("DejaVu Sans", tam, "bold" if negrita else "normal"))
        label.pack(anchor="w", pady=(0, 10), fill="x")
        return label

    def tarjeta(self):
        panel = tk.Frame(self.cuerpo, bg="white", padx=22, pady=18, highlightthickness=1,
                         highlightbackground="#e1e7f0")
        panel.pack(fill="x", pady=(0, 16))
        return panel

    def boton(self, padre, texto, accion, principal=False):
        b = ttk.Button(padre, text=texto, command=accion,
                       style="Principal.TButton" if principal else "TButton")
        b.pack(side="left", padx=(0, 10), pady=4)
        return b

    def titulo(self, titulo, subtitulo):
        self.texto(self.cuerpo, titulo, 24, negrita=True)
        self.texto(self.cuerpo, subtitulo, 10, GRIS)

    def mostrar(self, vista):
        if not self.autorizado and vista != "Acceso":
            return
        self.vista_actual = vista
        for hijo in self.cuerpo.winfo_children():
            hijo.destroy()
        for nombre, boton in self.botones_menu.items():
            boton.configure(bg="#233b5f" if nombre == vista else "#111e34",
                            state="normal" if self.autorizado else "disabled")
        {"Acceso": self.vista_acceso, "Inicio": self.vista_inicio,
         "Enviar archivo": self.vista_envio, "Recibir archivos": self.vista_recepcion,
         "Actividad": self.vista_actividad, "Configuración": self.vista_configuracion,
         "Ayuda": self.vista_ayuda}[vista]()

    def vista_acceso(self):
        self.titulo("Tu información, en tu red.", "Bóveda WiFi · Acceso al prototipo de escritorio")
        panel = self.tarjeta()
        self.texto(panel, "◈", 64, AZUL)
        self.texto(panel, "Control de acceso simulado", 20, negrita=True)
        self.texto(panel, "Prueba el acceso antes de enviar o recibir archivos en tu red local.", 11, GRIS)
        self.texto(panel, "SIMULACIÓN BIOMÉTRICA", 10, "#9b620d", True)
        self.texto(panel, "Esta versión no captura huellas ni verifica una identidad real.\n"
                   "La integración del sensor corresponde a una etapa posterior del proyecto.", 11)
        fila = tk.Frame(panel, bg="white"); fila.pack(anchor="w", pady=12)
        self.boton(fila, "Simular huella autorizada", lambda: self.autenticar(True), True)
        self.boton(fila, "Simular acceso denegado", lambda: self.autenticar(False))
        tk.Label(panel, textvariable=self.mensaje_acceso, bg="white", fg="#9b620d",
                 wraplength=740, justify="left").pack(anchor="w", pady=12)
        self.texto(self.cuerpo, "AES-256-GCM     /     RSA-OAEP     /     SHA-256", 11, GRIS)

    def autenticar(self, aprobar):
        if aprobar:
            self.autorizado = True
            self.mensaje_acceso.set("Acceso simulado aprobado.")
            self.mostrar("Inicio")
        else:
            self.mensaje_acceso.set("Acceso denegado. No se habilitaron las funciones de transferencia.")

    def vista_inicio(self):
        self.titulo("Comparte con tranquilidad", "Transferencia directa entre equipos de la misma red local.")
        panel = self.tarjeta()
        self.texto(panel, "Conexión configurada", 11, GRIS)
        c = self.config_actual
        self.texto(panel, c.host + " : " + str(c.puerto), 25, AZUL, True)
        self.texto(panel, self.estado_receptor + " · Límite: " + str(c.maximo // 1048576) + " MiB", 11)
        self.texto(panel, "La dirección configurada no confirma que el equipo remoto esté disponible.", 10, GRIS)
        panel = self.tarjeta()
        self.texto(panel, "¿Qué necesitas hacer?", 17, negrita=True)
        self.texto(panel, "Envía un archivo o habilita este equipo para recibirlo.", 11, GRIS)
        fila = tk.Frame(panel, bg="white"); fila.pack(anchor="w")
        self.boton(fila, "Enviar archivo  →", lambda: self.mostrar("Enviar archivo"), True)
        self.boton(fila, "Recibir archivos", lambda: self.mostrar("Recibir archivos"))
        panel = self.tarjeta()
        self.texto(panel, "Protección durante todo el proceso", 15, negrita=True)
        self.texto(panel, "1. AES cifra el archivo.  2. RSA protege su clave.\n"
                   "3. SHA-256 verifica su integridad.  4. Se eliminan las copias temporales.", 11)
        self.texto(panel, "Se conservan el original y el archivo final recibido.", 10, GRIS)

    def vista_envio(self):
        self.titulo("Enviar archivo", "El receptor debe estar iniciado y utilizar la misma configuración de red.")
        panel = self.tarjeta()
        self.texto(panel, "01   Selecciona el archivo", 15, negrita=True)
        self.texto(panel, self.archivo.name if self.archivo else "Ningún archivo seleccionado", 16, AZUL)
        if self.archivo:
            self.texto(panel, str(self.archivo), 9, GRIS)
        fila = tk.Frame(panel, bg="white"); fila.pack(anchor="w")
        self.boton_seleccion = self.boton(fila, "Buscar archivo…", self.seleccionar)
        self.boton_seleccion.configure(state="disabled" if self.ocupado else "normal")
        panel = self.tarjeta()
        self.texto(panel, "02   Revisa el destino y envía", 15, negrita=True)
        c = self.config_actual
        self.texto(panel, "Receptor: " + c.host + ":" + str(c.puerto) + "   /   Máximo: " + str(c.maximo // 1048576) + " MiB")
        self.texto(panel, "Comprueba previamente la huella de la clave pública en Configuración.", 10, GRIS)
        fila = tk.Frame(panel, bg="white"); fila.pack(anchor="w")
        self.boton_enviar = self.boton(fila, "Cifrar y enviar", self.enviar, True)
        self.boton_enviar.configure(state="normal" if self.archivo and not self.ocupado else "disabled")
        self.barra = ttk.Progressbar(panel, mode="indeterminate"); self.barra.pack(fill="x", pady=15)
        if self.ocupado:
            self.barra.start(15)
        tk.Label(panel, textvariable=self.estado_envio, bg="white", fg=AZUL,
                 justify="left", wraplength=735).pack(anchor="w")
        self.texto(self.cuerpo, "La actividad muestra el resultado y el hash de la transferencia.", 10, GRIS)

    def seleccionar(self):
        ruta = filedialog.askopenfilename(title="Seleccionar archivo para enviar")
        if ruta:
            self.archivo = Path(ruta)
            self.estado_envio.set("Archivo seleccionado. Listo para enviar.")
            self.mostrar("Enviar archivo")

    def autorizado_para_enviar(self):
        if not self.autorizado:
            raise PermissionError("La sesión no está autorizada.")

    def enviar(self):
        if self.ocupado or not self.autorizado or not self.archivo:
            return
        ruta, config = self.archivo, copy.copy(self.config_actual)
        self.ocupado = True
        self.estado_envio.set("Preparando la transferencia…")
        self.mostrar("Enviar archivo")
        def tarea():
            try:
                resultado = emisor.enviar_archivo(ruta, config, self.autorizado_para_enviar,
                                                  lambda texto: self.eventos.put(("avance", texto)))
                self.eventos.put(("enviado", resultado))
            except Exception as error:
                self.eventos.put(("error_envio", {"nombre": ruta.name, "bytes": 0,
                                  "estado": "Envío no confirmado", "detalle": str(error) +
                                  ". Si la transferencia comenzó, revisa el receptor antes de reintentar."}))
        threading.Thread(target=tarea, daemon=True).start()

    def vista_recepcion(self):
        self.titulo("Recibir archivos", "Activa la escucha en este equipo para aceptar transferencias locales.")
        panel = self.tarjeta()
        self.texto(panel, self.estado_receptor, 19, AZUL, True)
        c = self.config_actual
        self.texto(panel, "Escucha local: " + c.host + ":" + str(c.puerto))
        self.texto(panel, "En modo receptor, HOST debe ser una IP de este equipo.", 10, GRIS)
        fila = tk.Frame(panel, bg="white"); fila.pack(anchor="w", pady=12)
        self.boton_iniciar = self.boton(fila, "Iniciar receptor", self.iniciar_receptor, True)
        self.boton_detener = self.boton(fila, "Detener receptor", self.parar_receptor)
        self.boton_iniciar.configure(state="disabled" if self.receptor_activo or self.ocupado else "normal")
        self.boton_detener.configure(state="normal" if self.receptor_activo and not self.detener.is_set() else "disabled")
        panel = self.tarjeta()
        self.texto(panel, "Destino de los archivos verificados", 15, negrita=True)
        self.texto(panel, str(c.recibidos), 10, GRIS)
        fila = tk.Frame(panel, bg="white"); fila.pack(anchor="w")
        self.boton(fila, "Abrir carpeta recibidos", self.abrir_recibidos)
        self.texto(panel, "El archivo se guarda después de verificar AES-GCM y SHA-256.\n"
                   "Al detener, se espera el cierre de la transferencia activa y su limpieza.", 10, GRIS)
        self.texto(self.cuerpo, "La simulación de acceso controla esta interfaz; no autentica al emisor remoto.", 10, GRIS)

    def iniciar_receptor(self):
        if self.receptor_activo or self.ocupado or not self.autorizado:
            return
        config = copy.copy(self.config_actual)
        self.detener.clear()
        self.receptor_activo = True
        self.estado_receptor = "Iniciando receptor…"
        self.mostrar("Recibir archivos")
        def tarea():
            try:
                receptor.ejecutar(config, self.detener, lambda tipo, datos: self.eventos.put((tipo, datos)))
            except Exception as error:
                self.eventos.put(("error_recepcion", str(error)))
            finally:
                self.eventos.put(("detenido", None))
        threading.Thread(target=tarea, daemon=True).start()

    def parar_receptor(self):
        self.detener.set()
        self.estado_receptor = "Deteniendo; esperando la operación activa…"
        self.mostrar("Recibir archivos")

    def abrir_recibidos(self):
        try:
            carpeta = self.config_actual.recibidos
            carpeta.mkdir(parents=True, exist_ok=True)
            if sys.platform == "win32":
                os.startfile(str(carpeta))
            else:
                subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(carpeta)])
        except OSError as error:
            messagebox.showerror("Carpeta recibidos", str(error), parent=self)

    def vista_actividad(self):
        self.titulo("Actividad de la sesión", "Resultados reales de envío y recepción. El registro se conserva solo en memoria.")
        panel = self.tarjeta()
        tabla = ttk.Treeview(panel, columns=("hora", "archivo", "estado"), show="headings", height=5)
        for col, titulo, ancho in (("hora", "Hora", 85), ("archivo", "Archivo", 330), ("estado", "Resultado", 250)):
            tabla.heading(col, text=titulo); tabla.column(col, width=ancho, minwidth=60)
        barra = ttk.Scrollbar(panel, orient="vertical", command=tabla.yview)
        tabla.configure(yscrollcommand=barra.set)
        tabla.pack(side="left", fill="x", expand=True); barra.pack(side="right", fill="y")
        detalle = self.tarjeta()
        self.texto(detalle, "Detalle de la operación", 15, negrita=True)
        self.detalle = tk.Text(detalle, height=9, wrap="word", bg="#f6f8fc", fg=TEXTO,
                               relief="flat", padx=12, pady=10, font=("DejaVu Sans", 10))
        self.detalle.pack(fill="x")
        def mostrar_detalle(evento=None):
            self.detalle.configure(state="normal"); self.detalle.delete("1.0", "end")
            if tabla.selection():
                item = self.historial[int(tabla.selection()[0])]
                lineas = [item["estado"], "Archivo: " + item["nombre"], item["detalle"]]
                if item.get("sha256"):
                    lineas.extend(["SHA-256:", item["sha256"]])
                if item.get("ruta"):
                    lineas.extend(["Guardado en:", item["ruta"]])
                self.detalle.insert("1.0", "\n".join(lineas))
            else:
                self.detalle.insert("1.0", "Todavía no hay operaciones en esta sesión.")
            self.detalle.configure(state="disabled")
        for indice, item in enumerate(self.historial):
            tabla.insert("", "end", iid=str(indice), values=(item["hora"], item["nombre"], item["estado"]))
        tabla.bind("<<TreeviewSelect>>", mostrar_detalle)
        if self.historial:
            tabla.selection_set(str(len(self.historial) - 1)); tabla.see(str(len(self.historial) - 1))
        mostrar_detalle()

    def vista_configuracion(self):
        self.titulo("Configuración", "Los cambios se aplican a esta sesión. Al reiniciar se carga .env o sus valores predeterminados.")
        panel = self.tarjeta()
        self.campos = {}
        c = self.config_actual
        for etiqueta, clave, valor in (("IP del receptor", "host", c.host), ("Puerto TCP (1024–65535)", "puerto", c.puerto),
                                     ("Espera (1–600 segundos)", "timeout", c.timeout), ("Máximo por archivo (1–100 MiB)", "maximo", c.maximo // 1048576)):
            fila = tk.Frame(panel, bg="white"); fila.pack(fill="x", pady=3)
            tk.Label(fila, text=etiqueta, bg="white", fg=TEXTO, width=34, anchor="w").pack(side="left")
            campo = ttk.Entry(fila, width=27); campo.insert(0, str(valor)); campo.pack(side="left")
            self.campos[clave] = campo
        fila = tk.Frame(panel, bg="white"); fila.pack(anchor="w", pady=8)
        b = self.boton(fila, "Aplicar a la sesión", self.aplicar_configuracion, True)
        b.configure(state="disabled" if self.ocupado or self.receptor_activo else "normal")
        panel = self.tarjeta()
        self.texto(panel, "Claves RSA y confianza", 15, negrita=True)
        self.texto(panel, "Carpeta: " + str(c.claves), 9, GRIS)
        try:
            huella = crypto.huella_publica(crypto.cargar_rsa(c.claves / "receptor_publica.pem"))
        except (OSError, ValueError, TypeError):
            huella = "No hay una clave pública válida. Genera las claves en el receptor o copia su clave pública al emisor."
        self.texto(panel, "Huella SHA-256 de la clave pública:", 10, GRIS)
        self.texto(panel, huella, 10)
        fila = tk.Frame(panel, bg="white"); fila.pack(anchor="w")
        b = self.boton(fila, "Generar / comprobar claves del receptor", self.generar_claves)
        b.configure(state="disabled" if self.ocupado or self.receptor_activo else "normal")
        self.texto(panel, "Copia solo la clave pública al emisor. Compara las huellas por un canal independiente.", 10, GRIS)

    def aplicar_configuracion(self):
        if self.ocupado or self.receptor_activo:
            return
        try:
            nuevo = copy.copy(self.config_actual)
            nuevo.host = crypto.validar_ip(self.campos["host"].get().strip())
            for clave, minimo, maximo in (("puerto", 1024, 65535), ("timeout", 1, 600), ("maximo", 1, 100)):
                valor = int(self.campos[clave].get())
                if not minimo <= valor <= maximo:
                    raise ValueError("Valor fuera de rango: " + clave)
                setattr(nuevo, clave, valor * 1048576 if clave == "maximo" else valor)
            self.config_actual = nuevo
            self.estado_sistema.set("Configuración aplicada a esta sesión · " + nuevo.host + ":" + str(nuevo.puerto))
        except ValueError as error:
            messagebox.showerror("Configuración inválida", str(error), parent=self)

    def generar_claves(self):
        if self.ocupado or self.receptor_activo:
            return
        self.ocupado = True
        self.estado_sistema.set("Preparando claves RSA…")
        self.mostrar("Configuración")
        carpeta = self.config_actual.claves
        def tarea():
            try:
                crypto.generar_claves(carpeta)
                self.eventos.put(("claves", "Claves del receptor comprobadas. Compara la huella antes de enviar."))
            except Exception as error:
                self.eventos.put(("claves", "No se prepararon las claves: " + str(error)))
        threading.Thread(target=tarea, daemon=True).start()

    def vista_ayuda(self):
        self.titulo("Ayuda y alcance", "Guía de uso · Bóveda WiFi · Grupo 21 / Sección B")
        panel = self.tarjeta()
        self.texto(panel, "En un solo equipo", 16, negrita=True)
        self.texto(panel, "1. Usa 127.0.0.1 y el mismo puerto.\n2. Genera las claves en Configuración.\n"
                   "3. Inicia el receptor y abre Enviar archivo.\n4. Selecciona el archivo y pulsa Cifrar y enviar.")
        self.texto(panel, "En dos equipos de la misma WiFi", 16, negrita=True)
        self.texto(panel, "Configura en ambos la IP privada del receptor. Genera las claves solo allí.\n"
                   "Copia su clave pública al emisor y compara las huellas. Permite el puerto\n"
                   "TCP en el firewall del receptor e inicia la escucha antes del envío.")
        panel = self.tarjeta()
        self.texto(panel, "Cómo interpretar los resultados", 15, negrita=True)
        self.texto(panel, "Envío confirmado: se validó la respuesta cifrada del receptor.\n"
                   "Envío no confirmado: revisa el receptor antes de repetir; podría haberse guardado.\n"
                   "Recepción verificada: archivo guardado, temporales eliminados y confirmación enviada.", 10)
        self.texto(panel, "El original y la copia final permanecen. El borrado temporal es lógico.\n"
                   "La huella dactilar está simulada; no hay cuentas ni roles administrativos.", 10, GRIS)

    def registrar(self, datos):
        datos["hora"] = datetime.now().strftime("%H:%M:%S")
        self.historial.append(datos)

    def procesar_eventos(self):
        while not self.eventos.empty():
            tipo, datos = self.eventos.get_nowait()
            if tipo == "avance":
                self.estado_envio.set(datos)
            elif tipo in ("enviado", "error_envio"):
                self.ocupado = False
                self.registrar(datos)
                self.estado_envio.set(datos["estado"] + ": " + datos["detalle"])
                self.estado_sistema.set(datos["estado"])
                if self.vista_actual == "Enviar archivo":
                    self.mostrar("Enviar archivo")
            elif tipo == "escuchando":
                self.estado_receptor = "Escuchando en " + datos
                self.estado_sistema.set(self.estado_receptor)
            elif tipo == "actividad":
                self.estado_receptor = datos
            elif tipo == "recibido":
                self.registrar(datos)
                self.estado_receptor = "Recepción verificada · Esperando otro archivo"
            elif tipo == "error_recepcion":
                self.registrar({"nombre": "Recepción", "estado": "Recepción no confirmada", "detalle": datos})
                self.estado_sistema.set("Error de recepción: " + datos)
                self.estado_receptor = "Transferencia no confirmada; consulta Actividad"
            elif tipo == "detenido":
                self.receptor_activo = False
                self.estado_receptor = "Receptor detenido"
            elif tipo == "claves":
                self.ocupado = False
                self.estado_sistema.set(datos)
                if self.vista_actual == "Configuración":
                    self.mostrar("Configuración")
            if tipo not in ("avance", "claves") and self.vista_actual in ("Actividad", "Recibir archivos", "Inicio"):
                self.mostrar(self.vista_actual)
        self.after(80, self.procesar_eventos)

    def cerrar_sesion(self):
        if self.ocupado or self.receptor_activo:
            messagebox.showinfo("Operación activa", "Espera el envío y detén el receptor antes de cerrar la sesión.", parent=self)
            return
        self.autorizado = False
        self.archivo = None
        self.historial.clear()
        self.estado_envio.set("Selecciona un archivo para comenzar.")
        self.mensaje_acceso.set("Sesión cerrada. Elige una opción para acceder.")
        self.mostrar("Acceso")

    def cerrar(self):
        if self.ocupado or self.receptor_activo:
            messagebox.showinfo("Operación activa", "Espera el envío y detén el receptor antes de salir.", parent=self)
            return
        self.destroy()


def main():
    try:
        app = BovedaApp()
        app.mainloop()
    except (OSError, ValueError, TypeError) as error:
        print("[ERROR] No se pudo abrir la interfaz:", error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
