"""
Módulo del System Tray - Icono y menú en la bandeja del sistema.
Usa pystray para el icono y tkinter para la ventana de configuración.
"""

import threading
from typing import Callable
from pathlib import Path
from PIL import Image
import pystray
from pystray import MenuItem as Item
import tkinter as tk
from tkinter import ttk


# Ruta del icono para el .exe
ICON_PATH = Path(__file__).parent / "media" / "icon.ico"
# Carpeta de expresiones para el tray
EXPRESSIONS_PATH = Path(__file__).parent / "media" / "expresions"


class ConfigWindow:
    """Ventana de configuración separada que corre en su propio hilo."""
    
    def __init__(self, config, save_callback):
        self.config = config
        self.save_callback = save_callback
        self.window = None
    
    def show(self):
        """Muestra la ventana de configuración."""
        if self.window is not None:
            try:
                self.window.lift()
                self.window.focus_force()
                return
            except tk.TclError:
                self.window = None
        
        # Crear ventana en hilo principal de tkinter
        self.window = tk.Tk()
        self.window.title("Observer - Configuración")
        self.window.geometry("450x420")
        self.window.resizable(False, False)
        
        # Centrar ventana
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() - 450) // 2
        y = (self.window.winfo_screenheight() - 420) // 2
        self.window.geometry(f"+{x}+{y}")
        
        # Forzar foco
        self.window.lift()
        self.window.attributes('-topmost', True)
        self.window.after(100, lambda: self.window.attributes('-topmost', False))
        
        self._build_ui()
        self.window.mainloop()
    
    def _build_ui(self):
        """Construye la interfaz de usuario."""
        window = self.window
        
        # Frame principal con padding
        main_frame = ttk.Frame(window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Título
        title_label = tk.Label(
            main_frame,
            text="⚙️ Configuración",
            font=("Segoe UI", 14, "bold")
        )
        title_label.pack(pady=(0, 15))
        
        # Frame para tiempos
        time_frame = tk.LabelFrame(main_frame, text="Tiempos (minutos)", padx=10, pady=10)
        time_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Tiempo de trabajo
        work_frame = tk.Frame(time_frame)
        work_frame.pack(fill=tk.X, pady=5)
        tk.Label(work_frame, text="⏱️ Trabajo:").pack(side=tk.LEFT)
        self.work_var = tk.StringVar(value=str(self.config.work_minutes))
        work_entry = tk.Entry(work_frame, textvariable=self.work_var, width=10)
        work_entry.pack(side=tk.RIGHT)
        
        # Tiempo de descanso
        rest_frame = tk.Frame(time_frame)
        rest_frame.pack(fill=tk.X, pady=5)
        tk.Label(rest_frame, text="🧘 Descanso:").pack(side=tk.LEFT)
        self.rest_var = tk.StringVar(value=str(self.config.rest_minutes))
        rest_entry = tk.Entry(rest_frame, textvariable=self.rest_var, width=10)
        rest_entry.pack(side=tk.RIGHT)
        
        # Tiempo AFK para descanso automático
        auto_rest_frame = tk.Frame(time_frame)
        auto_rest_frame.pack(fill=tk.X, pady=5)
        tk.Label(auto_rest_frame, text="💤 AFK para reiniciar:").pack(side=tk.LEFT)
        self.auto_rest_var = tk.StringVar(value=str(self.config.auto_rest_minutes))
        auto_rest_entry = tk.Entry(auto_rest_frame, textvariable=self.auto_rest_var, width=10)
        auto_rest_entry.pack(side=tk.RIGHT)
        
        # Frame para mensajes
        msg_frame = tk.LabelFrame(main_frame, text="Mensajes de notificación", padx=10, pady=10)
        msg_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Mensaje de descanso
        tk.Label(msg_frame, text="🔔 Aviso de descanso:").pack(anchor=tk.W)
        self.msg_rest_var = tk.StringVar(value=self.config.msg_rest)
        msg_rest_entry = tk.Entry(msg_frame, textvariable=self.msg_rest_var, width=50)
        msg_rest_entry.pack(fill=tk.X, pady=(0, 10))
        
        # Mensaje de trabajo
        tk.Label(msg_frame, text="💻 Aviso de trabajo:").pack(anchor=tk.W)
        self.msg_work_var = tk.StringVar(value=self.config.msg_work)
        msg_work_entry = tk.Entry(msg_frame, textvariable=self.msg_work_var, width=50)
        msg_work_entry.pack(fill=tk.X)
        
        # Botones
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(15, 0))
        
        save_btn = tk.Button(btn_frame, text="Guardar", command=self._save, width=12)
        save_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        cancel_btn = tk.Button(btn_frame, text="Cancelar", command=self._cancel, width=12)
        cancel_btn.pack(side=tk.RIGHT)
        
        # Manejar cierre de ventana
        window.protocol("WM_DELETE_WINDOW", self._cancel)
    
    def _save(self):
        """Guarda la configuración y cierra."""
        try:
            new_config = {
                "work_minutes": int(self.work_var.get()),
                "rest_minutes": int(self.rest_var.get()),
                "auto_rest_minutes": int(self.auto_rest_var.get()),
                "msg_rest": self.msg_rest_var.get(),
                "msg_work": self.msg_work_var.get()
            }
            self.save_callback(new_config)
        except ValueError as e:
            print(f"[Config] Error en valores: {e}")
        finally:
            self._close()
    
    def _cancel(self):
        """Cierra sin guardar."""
        self._close()
    
    def _close(self):
        """Cierra la ventana."""
        if self.window:
            self.window.quit()
            self.window.destroy()
            self.window = None


class TrayApp:
    """Aplicación del system tray con menú de configuración."""
    
    def __init__(
        self,
        on_quit: Callable[[], None],
        get_config: Callable,
        save_config: Callable[[dict], None],
        get_state: Callable[[], dict]
    ):
        self.on_quit = on_quit
        self.get_config = get_config
        self.save_config = save_config
        self.get_state = get_state
        
        self.icon = None
        self._update_thread = None
        self._running = False
        self._last_state = None
    
    def _load_expression_icon(self, state: str) -> Image.Image:
        """Carga el icono de expresión según el estado actual."""
        expression_file = EXPRESSIONS_PATH / f"{state}.png"
        
        if expression_file.exists():
            try:
                img = Image.open(expression_file)
                img = img.convert("RGBA")
                img = img.resize((64, 64), Image.Resampling.LANCZOS)
                return img
            except Exception as e:
                print(f"[Tray] Error cargando expresión {state}: {e}")
        
        # Fallback al icono por defecto
        return self._create_default_icon()
    
    def _create_default_icon(self) -> Image.Image:
        """Crea un icono por defecto si no hay archivos disponibles."""
        from PIL import ImageDraw
        size = 64
        image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.ellipse([4, 4, size-4, size-4], fill=(76, 175, 80, 255))
        draw.ellipse([16, 16, size-16, size-16], fill=(129, 199, 132, 255))
        return image
    
    def _update_icon_for_state(self):
        """Actualiza el icono del tray según el estado actual."""
        if not self.icon:
            return
        
        state_info = self.get_state()
        current_state = state_info["state"]
        
        # Solo actualizar si el estado cambió
        if current_state != self._last_state:
            self._last_state = current_state
            new_icon = self._load_expression_icon(current_state)
            self.icon.icon = new_icon
    
    def _get_status_text(self) -> str:
        """Genera texto de estado para mostrar en el menú."""
        state_info = self.get_state()
        state = state_info["state"]
        
        state_names = {
            "idle": "⏸️ Esperando actividad",
            "working": "💻 Trabajando",
            "paused": "⏯️ Trabajo pausado",
            "wait_rest": "🔔 Esperando descanso",
            "resting": "🧘 Descansando"
        }
        
        status = state_names.get(state, state)
        
        if state == "working":
            elapsed = int(state_info["work_elapsed"])
            total = int(state_info["work_total"])
            remaining = max(0, total - elapsed)
            mins, secs = divmod(remaining, 60)
            status += f" ({mins}:{secs:02d})"
        elif state == "resting":
            elapsed = int(state_info["rest_elapsed"])
            total = int(state_info["rest_total"])
            remaining = max(0, total - elapsed)
            mins, secs = divmod(remaining, 60)
            status += f" ({mins}:{secs:02d})"
        
        return status
    
    def _open_config_window(self):
        """Abre la ventana de configuración en un hilo separado."""
        def run_config():
            config = self.get_config()
            config_win = ConfigWindow(config, self.save_config)
            config_win.show()
        
        # Ejecutar en hilo separado para no bloquear el tray
        thread = threading.Thread(target=run_config, daemon=True)
        thread.start()
    
    def _create_menu(self):
        """Crea el menú del system tray."""
        return pystray.Menu(
            Item(lambda text: self._get_status_text(), None, enabled=False),
            pystray.Menu.SEPARATOR,
            Item("⚙️ Configuración", lambda: self._open_config_window()),
            pystray.Menu.SEPARATOR,
            Item("❌ Salir", self._quit)
        )
    
    def _quit(self):
        """Cierra la aplicación."""
        if self.icon:
            self.icon.stop()
        self.on_quit()
    
    def _update_menu_loop(self):
        """Hilo que actualiza el menú y el icono cada segundo."""
        import time
        while self._running:
            try:
                if self.icon:
                    # Actualizar el icono según el estado
                    self._update_icon_for_state()
                    # Actualizar el menú para refrescar el estado
                    self.icon.update_menu()
            except Exception as e:
                print(f"[Tray] Error actualizando: {e}")
            time.sleep(1)
    
    def run(self):
        """Inicia el icono del system tray."""
        # Cargar icono inicial según estado actual
        state_info = self.get_state()
        self._last_state = state_info["state"]
        image = self._load_expression_icon(self._last_state)
        
        self.icon = pystray.Icon(
            name="Observer",
            icon=image,
            title="Observer",
            menu=self._create_menu()
        )
        
        # Iniciar hilo de actualización del menú
        self._running = True
        self._update_thread = threading.Thread(target=self._update_menu_loop, daemon=True)
        self._update_thread.start()
        
        print("[Tray] Icono del system tray iniciado")
        self.icon.run()
    
    def stop(self):
        """Detiene el icono del tray."""
        self._running = False
        if self._update_thread:
            self._update_thread.join(timeout=2)
        if self.icon:
            self.icon.stop()
