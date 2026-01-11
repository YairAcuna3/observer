"""
Módulo de monitoreo de actividad - Detecta uso de teclado y mouse.
Usa pynput para escuchar eventos de entrada.
"""

import threading
import time
from typing import Callable, Optional

from pynput import mouse, keyboard


class ActivityMonitor:
    """
    Monitor de actividad del usuario.
    Detecta eventos de teclado y mouse para determinar si el usuario está activo.
    """
    
    def __init__(
        self,
        on_activity: Callable[[], None],
        on_inactivity: Callable[[], None],
        inactivity_threshold: float = 3.0
    ):
        """
        Args:
            on_activity: Callback cuando se detecta actividad
            on_inactivity: Callback cuando se detecta inactividad
            inactivity_threshold: Segundos sin actividad para considerar inactivo
        """
        self.on_activity = on_activity
        self.on_inactivity = on_inactivity
        self.inactivity_threshold = inactivity_threshold
        
        # Estado interno
        self.last_activity_time = time.time()
        self.is_active = False
        self.running = False
        
        # Listeners de pynput
        self.mouse_listener: Optional[mouse.Listener] = None
        self.keyboard_listener: Optional[keyboard.Listener] = None
        
        # Hilo para verificar inactividad
        self.check_thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()
    
    def start(self):
        """Inicia el monitoreo de actividad."""
        if self.running:
            return
        
        self.running = True
        self.last_activity_time = time.time()
        
        # Iniciar listeners de mouse
        self.mouse_listener = mouse.Listener(
            on_move=self._on_input,
            on_click=self._on_input,
            on_scroll=self._on_input
        )
        self.mouse_listener.start()
        
        # Iniciar listener de teclado
        self.keyboard_listener = keyboard.Listener(
            on_press=self._on_input,
            on_release=self._on_input
        )
        self.keyboard_listener.start()
        
        # Iniciar hilo de verificación de inactividad
        self.check_thread = threading.Thread(target=self._check_inactivity, daemon=True)
        self.check_thread.start()
        
        print("[ActivityMonitor] Monitoreo iniciado")
    
    def stop(self):
        """Detiene el monitoreo de actividad."""
        self.running = False
        
        if self.mouse_listener:
            self.mouse_listener.stop()
            self.mouse_listener = None
        
        if self.keyboard_listener:
            self.keyboard_listener.stop()
            self.keyboard_listener = None
        
        print("[ActivityMonitor] Monitoreo detenido")
    
    def _on_input(self, *args):
        """Callback para cualquier evento de entrada."""
        with self.lock:
            self.last_activity_time = time.time()
            
            if not self.is_active:
                self.is_active = True
                # Ejecutar callback en hilo separado para no bloquear el listener
                threading.Thread(target=self.on_activity, daemon=True).start()
    
    def _check_inactivity(self):
        """Hilo que verifica periódicamente si hay inactividad."""
        while self.running:
            time.sleep(0.5)  # Verificar cada 500ms
            
            with self.lock:
                elapsed = time.time() - self.last_activity_time
                
                if self.is_active and elapsed >= self.inactivity_threshold:
                    self.is_active = False
                    # Ejecutar callback en hilo separado
                    threading.Thread(target=self.on_inactivity, daemon=True).start()
