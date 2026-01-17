import threading
import time
import json
import os
from pathlib import Path

from activity_monitor import ActivityMonitor
from notifications import NotificationManager
from tray_app import TrayApp
from config import Config


class Observer:
    """Clase principal que coordina todos los componentes de la aplicación."""
    
    # Estados posibles del ciclo
    STATE_IDLE = "idle"              # Esperando actividad inicial
    STATE_WORKING = "working"        # Contando tiempo de trabajo
    STATE_WORK_PAUSED = "paused"     # Trabajo pausado por inactividad
    STATE_WAIT_REST = "wait_rest"    # Esperando que inicie el descanso
    STATE_RESTING = "resting"        # Contando tiempo de descanso
    
    def __init__(self):
        self.config = Config()
        self.state = self.STATE_IDLE
        self.state_lock = threading.Lock()
        
        # Tiempo acumulado de trabajo (en segundos)
        self.work_elapsed = 0
        self.rest_elapsed = 0
        
        # Tiempo de pausa acumulado para detectar descanso automático
        self.pause_elapsed = 0
        
        # Tiempo de inactividad durante el descanso
        self.rest_inactivity_elapsed = 0
        
        # Flag para rastrear si el usuario está actualmente inactivo
        self.is_currently_inactive = False
        
        # Componentes
        self.notifications = NotificationManager()
        self.activity_monitor = ActivityMonitor(
            on_activity=self._on_activity,
            on_inactivity=self._on_inactivity,
            inactivity_threshold=3.0  # 3 segundos sin actividad = inactivo
        )
        
        # Timer para el bucle principal
        self.running = False
        self.main_thread = None
        
        # Tray app (se inicializa después)
        self.tray = None
    
    def start(self):
        """Inicia la aplicación."""
        print("[Observer] Iniciando aplicación...")
        self.running = True
        
        # Iniciar monitor de actividad
        self.activity_monitor.start()
        
        # Iniciar bucle principal en hilo separado
        self.main_thread = threading.Thread(target=self._main_loop, daemon=True)
        self.main_thread.start()
        
        # Iniciar tray (bloquea hasta que se cierre)
        self.tray = TrayApp(
            on_quit=self.stop,
            get_config=lambda: self.config,
            save_config=self._save_config,
            get_state=self._get_state_info
        )
        self.tray.run()
    
    def stop(self):
        """Detiene la aplicación."""
        print("[Observer] Deteniendo aplicación...")
        self.running = False
        self.activity_monitor.stop()
        self.notifications.cleanup()  # Limpiar recursos de audio
        if self.tray:
            self.tray.stop()
    
    def _save_config(self, new_config: dict):
        """Guarda la nueva configuración y reinicia el ciclo."""
        self.config.update(new_config)
        self.config.save()
        # Reiniciar ciclo con nueva configuración
        with self.state_lock:
            self.state = self.STATE_IDLE
            self.work_elapsed = 0
            self.rest_elapsed = 0
            self.pause_elapsed = 0
            self.rest_inactivity_elapsed = 0
            self.is_currently_inactive = False
        print(f"[Config] Configuración actualizada: {new_config}")
        
        # Forzar detección de actividad después de un breve delay
        # para que si el usuario está activo, inicie el ciclo automáticamente
        def force_activity_check():
            import time
            time.sleep(0.5)  # Esperar medio segundo
            # Simular actividad para forzar transición si el usuario está activo
            if self.activity_monitor and hasattr(self.activity_monitor, 'last_activity_time'):
                import time
                current_time = time.time()
                # Si hubo actividad reciente (últimos 5 segundos), forzar transición
                if current_time - self.activity_monitor.last_activity_time < 5.0:
                    self._on_activity()
        
        # Ejecutar en hilo separado para no bloquear
        threading.Thread(target=force_activity_check, daemon=True).start()
    
    def _get_state_info(self) -> dict:
        """Retorna información del estado actual para mostrar en UI."""
        with self.state_lock:
            work_total = self.config.work_minutes * 60
            rest_total = self.config.rest_minutes * 60
            return {
                "state": self.state,
                "work_elapsed": self.work_elapsed,
                "work_total": work_total,
                "rest_elapsed": self.rest_elapsed,
                "rest_total": rest_total
            }
    
    def _on_activity(self):
        """Callback cuando se detecta actividad del usuario."""
        with self.state_lock:
            self.is_currently_inactive = False
            self.rest_inactivity_elapsed = 0  # Resetear contador de inactividad durante descanso
            
            if self.state == self.STATE_IDLE:
                # Iniciar ciclo de trabajo
                self.state = self.STATE_WORKING
                self.work_elapsed = 0
                print("[Estado] IDLE -> WORKING (actividad detectada)")
            
            elif self.state == self.STATE_WORK_PAUSED:
                # Reanudar trabajo
                self.state = self.STATE_WORKING
                self.pause_elapsed = 0  # Resetear contador de pausa
                print(f"[Estado] PAUSED -> WORKING (reanudando, {self.work_elapsed}s acumulados)")
            
            elif self.state == self.STATE_WAIT_REST:
                # El usuario siguió activo después de la notificación - reiniciar ciclo
                self.state = self.STATE_WORKING
                self.work_elapsed = 0
                print("[Estado] WAIT_REST -> WORKING (usuario ignoró descanso, reiniciando ciclo)")
            
            elif self.state == self.STATE_RESTING:
                # El usuario volvió durante el descanso - reiniciar ciclo de trabajo
                self.state = self.STATE_WORKING
                self.work_elapsed = 0
                self.rest_elapsed = 0
                self.rest_inactivity_elapsed = 0
                print("[Estado] RESTING -> WORKING (usuario volvió, reiniciando ciclo)")
    
    def _on_inactivity(self):
        """Callback cuando se detecta inactividad del usuario."""
        with self.state_lock:
            self.is_currently_inactive = True
            
            if self.state == self.STATE_WORKING:
                # Pausar trabajo
                self.state = self.STATE_WORK_PAUSED
                self.pause_elapsed = 0  # Iniciar contador de pausa
                print(f"[Estado] WORKING -> PAUSED (inactividad, {self.work_elapsed}s acumulados)")
            
            elif self.state == self.STATE_WAIT_REST:
                # ¡El usuario se levantó! Iniciar descanso
                self.state = self.STATE_RESTING
                self.rest_elapsed = 0
                self.rest_inactivity_elapsed = 0
                print("[Estado] WAIT_REST -> RESTING (descanso iniciado)")
    
    def _main_loop(self):
        """Bucle principal que maneja los temporizadores."""
        last_tick = time.time()
        
        while self.running:
            time.sleep(1)  # Tick cada segundo
            
            current_time = time.time()
            delta = current_time - last_tick
            last_tick = current_time
            
            with self.state_lock:
                if self.state == self.STATE_WORKING:
                    self.work_elapsed += delta
                    work_target = self.config.work_minutes * 60
                    
                    # Debug cada 60 segundos
                    if int(self.work_elapsed) % 60 == 0 and delta < 1.5:
                        remaining = work_target - self.work_elapsed
                        print(f"[Trabajo] {int(self.work_elapsed)}s / {work_target}s ({int(remaining)}s restantes)")
                    
                    if self.work_elapsed >= work_target:
                        # Tiempo de trabajo completado
                        self.state = self.STATE_WAIT_REST
                        self.work_elapsed = 0  # Resetear para evitar notificaciones duplicadas
                        self.notifications.notify_rest(
                            title="¡Hora de descansar!",
                            message=self.config.msg_rest
                        )
                        print("[Estado] WORKING -> WAIT_REST (notificación enviada)")
                
                elif self.state == self.STATE_WORK_PAUSED:
                    # Contar tiempo de pausa para detectar descanso automático
                    self.pause_elapsed += delta
                    auto_rest_threshold = self.config.auto_rest_minutes * 60
                    
                    if self.pause_elapsed >= auto_rest_threshold:
                        # Pausa larga = iniciar descanso automático
                        self.state = self.STATE_RESTING
                        self.work_elapsed = 0
                        self.pause_elapsed = 0
                        self.rest_elapsed = 0
                        self.notifications.notify_auto_rest(
                            title="Descanso automático",
                            message="Has estado inactivo. Iniciando descanso automático."
                        )
                        print(f"[Estado] PAUSED -> RESTING (descanso automático tras {int(self.pause_elapsed)}s)")
                
                elif self.state == self.STATE_RESTING:
                    self.rest_elapsed += delta
                    
                    # Si el usuario está inactivo durante el descanso, contar tiempo de inactividad
                    if self.is_currently_inactive:
                        self.rest_inactivity_elapsed += delta
                    
                    rest_target = self.config.rest_minutes * 60
                    
                    if self.rest_elapsed >= rest_target:
                        # Descanso completado - siempre notificar
                        self.state = self.STATE_IDLE
                        self.work_elapsed = 0
                        self.rest_elapsed = 0
                        self.rest_inactivity_elapsed = 0
                        self.notifications.notify_work(
                            title="¡Descanso terminado!",
                            message=self.config.msg_work
                        )
                        if self.is_currently_inactive:
                            print("[Estado] RESTING -> IDLE (descanso completado, usuario inactivo)")
                        else:
                            print("[Estado] RESTING -> IDLE (descanso completado, usuario activo)")


def main():
    """Punto de entrada de la aplicación."""
    app = Observer()
    try:
        app.start()
    except KeyboardInterrupt:
        app.stop()


if __name__ == "__main__":
    main()
