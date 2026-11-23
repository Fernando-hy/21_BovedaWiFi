"""Controles de acceso y configuración del perfil de escritorio."""
import os
import tempfile
from pathlib import Path
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, filedialog

import identidad
import utils_crypto as crypto


class Patron(simpledialog.Dialog):
    def body(self, frame):
        self.puntos = []
        self.estado = tk.StringVar(value="Selecciona de 4 a 9 puntos distintos, en orden.")
        ttk.Label(frame, textvariable=self.estado).grid(columnspan=3, pady=8)
        for i in range(9):
            ttk.Button(frame, text=str(i+1), width=4, command=lambda n=i+1: self.punto(n)).grid(row=1+i//3, column=i%3)
        ttk.Button(frame, text="Empezar de nuevo", command=self.limpiar).grid(row=4, columnspan=3)
    def limpiar(self):
        self.puntos.clear()
        self.estado.set("Selecciona el primer punto.")
    def punto(self, n):
        if n not in self.puntos:
            self.puntos.append(n)
            self.estado.set("Puntos seleccionados: " + str(len(self.puntos)))
    def validate(self):
        return len(self.puntos) >= 4
    def apply(self):
        self.result = "".join(map(str, self.puntos))


class Acceso:
    def preguntar(self, titulo, mensaje, oculto=True):
        valor = simpledialog.askstring(titulo, mensaje, parent=self, show="•" if oculto else "")
        if valor is None:
            raise ValueError("Operación cancelada.")
        return valor

    def dedo(self):
        messagebox.showinfo("Huella dactilar", "Al cerrar este aviso, toca el lector con un dedo registrado en tu cuenta del sistema.", parent=self)
        identidad.verificar_huella()

    def introducir_patron(self):
        return Patron(self, "Patrón de acceso").result

    def pedir_totp(self):
        return self.preguntar("Verificación en dos pasos", "Código de 6 dígitos del autenticador:")

    def alta_totp(self):
        seed = identidad.nueva_semilla()
        valor = self.preguntar("Vincular autenticador", "En la app del teléfono, añade una clave de configuración.\n"
              "Cuenta: Bóveda WiFi · Basada en tiempo · 6 dígitos\n\n" + seed + "\n\nEscribe aquí el código mostrado por el teléfono:")
        return seed, identidad.validar_codigo(seed, valor, -1)

    def autenticar_perfil(self, password):
        return self.perfil.abrir(password, self.pedir_totp, self.introducir_patron, self.dedo)

    def vista_acceso(self):
        existe = self.perfil.existe()
        self.titulo("Acceso a Bóveda WiFi", "Un perfil local por cuenta del sistema operativo.")
        panel = self.tarjeta()
        self.texto(panel, "Iniciar sesión" if existe else "Configurar primer acceso", 18, negrita=True)
        self.texto(panel, "Contraseña" if existe else "Crea una contraseña de al menos 12 caracteres.")
        entrada = ttk.Entry(panel, show="•", width=36); entrada.pack(anchor="w")
        entrada.focus_set()
        if not existe:
            self.texto(panel, "Segundo factor obligatorio", 12, negrita=True)
            metodo = tk.StringVar(value="huella")
            for nombre, valor in [("Huella dactilar del sistema", "huella"), ("Código del autenticador del teléfono", "totp")]:
                ttk.Radiobutton(panel, text=nombre, variable=metodo, value=valor).pack(anchor="w")
        def acceder():
            try:
                password = entrada.get()
                entrada.delete(0, "end")
                if existe:
                    _, _, policy = self.autenticar_perfil(password)
                else:
                    if len(password) < 12:
                        raise ValueError("Usa al menos 12 caracteres.")
                    if password != self.preguntar("Confirmar contraseña", "Repite tu nueva contraseña:"):
                        raise ValueError("Las contraseñas no coinciden.")
                    policy = {"huella":metodo.get()=="huella", "totp":None, "patron":None}
                    ultimo = -1
                    if policy["huella"]:
                        self.dedo()
                    else:
                        policy["totp"], ultimo = self.alta_totp()
                    self.perfil.crear(password, policy, ultimo)
                self.factores = {k: bool(v) for k,v in policy.items()}
                self.autorizado = True
                self.estado_sistema.set("Sesión local autorizada")
                self.mostrar("Inicio")
            except Exception as error:
                self.mensaje_acceso.set(str(error))
        ttk.Button(panel, text="Acceder" if existe else "Crear perfil", command=acceder).pack(anchor="w", pady=12)
        entrada.bind("<Return>", lambda e: acceder())
        ttk.Label(panel, textvariable=self.mensaje_acceso, wraplength=650).pack(anchor="w")

    def vista_seguridad(self):
        self.titulo("Seguridad", "Los cambios requieren confirmar la contraseña y los factores actuales.")
        panel = self.tarjeta()
        self.texto(panel, "Factores de acceso", 17, negrita=True)
        self.texto(panel, "Conserva al menos una huella o un autenticador. El patrón añade una comprobación de conocimiento.")
        ttk.Button(panel, text="Cambiar contraseña", command=self.cambiar_password).pack(anchor="w", pady=4)
        for metodo, nombre in [("huella","Huella dactilar"), ("totp","Autenticador de dos pasos"), ("patron","Patrón de puntos")]:
            ttk.Button(panel, text=nombre + (" · Activo" if self.factores[metodo] else " · Inactivo"), command=lambda m=metodo: self.cambiar_factor(m)).pack(anchor="w", pady=4)
        panel = self.tarjeta()
        self.texto(panel, "Equipo autorizado para intercambiar archivos", 15, negrita=True)
        try:
            par = crypto.huella_publica(crypto.cargar_rsa(self.config_actual.claves / "par_publica.pem"))
        except (OSError, ValueError):
            par = "Ningún equipo vinculado."
        self.texto(panel, par, 10)
        ttk.Button(panel, text="Vincular clave pública del otro equipo", command=self.vincular).pack(anchor="w")

    def cambiar_password(self):
        try:
            sesion = self.confirmar()
            nueva = self.preguntar("Cambiar contraseña", "Nueva contraseña de al menos 12 caracteres:")
            if nueva != self.preguntar("Confirmar", "Repite la nueva contraseña:"):
                raise ValueError("Las contraseñas no coinciden.")
            self.perfil.cambiar_password(sesion, nueva)
            messagebox.showinfo("Seguridad", "Contraseña actualizada.", parent=self)
        except Exception as error:
            messagebox.showerror("Seguridad", str(error), parent=self)

    def confirmar(self):
        return self.autenticar_perfil(self.preguntar("Confirmar identidad", "Introduce tu contraseña. Si usas TOTP, espera un código nuevo."))

    def cambiar_factor(self, metodo):
        try:
            sesion = self.confirmar()
            policy = sesion[2].copy()
            ultimo = None
            if policy[metodo]:
                if not messagebox.askyesno("Factor activo", "Este factor está activo. ¿Deseas desactivarlo?", parent=self):
                    return
                policy[metodo] = None
            elif metodo == "huella":
                self.dedo()
                policy[metodo] = True
            elif metodo == "totp":
                policy[metodo], ultimo = self.alta_totp()
            else:
                primero = self.introducir_patron()
                if not primero or primero != self.introducir_patron():
                    raise ValueError("Los patrones no coinciden.")
                policy[metodo] = primero
            self.perfil.actualizar(sesion, policy, ultimo)
            self.factores = {k: bool(v) for k,v in policy.items()}
            self.mostrar("Seguridad")
            messagebox.showinfo("Seguridad", "Configuración de acceso guardada.", parent=self)
        except Exception as error:
            messagebox.showerror("Seguridad", str(error), parent=self)

    def vincular(self):
        if self.receptor_activo or self.ocupado:
            messagebox.showinfo("Equipo vinculado", "Primero detén la recepción y espera el envío.", parent=self)
            return
        try:
            self.confirmar()
            archivo = filedialog.askopenfilename(title="Selecciona la clave pública del otro equipo", filetypes=[("Clave pública", "*.pem")])
            if not archivo:
                return
            publica = crypto.cargar_rsa(Path(archivo))
            esperada = self.preguntar("Verificar equipo", "Introduce los 64 caracteres de la huella SHA-256 que muestra\nel OTRO equipo en Configuración. Usa un canal independiente.", False)
            if esperada.strip().lower() != crypto.huella_publica(publica):
                raise ValueError("La huella no coincide. Se conserva el vínculo anterior.")
            carpeta = self.config_actual.claves
            carpeta.mkdir(exist_ok=True, parents=True, mode=0o700)
            with tempfile.NamedTemporaryFile(dir=carpeta, delete=False) as f:
                nombre = f.name
                f.write(crypto.pem(publica))
            try:
                os.replace(nombre, carpeta / "par_publica.pem")
            finally:
                Path(nombre).unlink(missing_ok=True)
            self.mostrar("Seguridad")
        except Exception as error:
            messagebox.showerror("Equipo vinculado", str(error), parent=self)
