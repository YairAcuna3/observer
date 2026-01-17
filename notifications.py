"""
Módulo de notificaciones - Envía notificaciones nativas de Windows con audio.
Usa plyer para notificaciones y pygame para reproducción de audio.
"""

from plyer import notification
import threading
import os
# Suprimir mensaje de bienvenida de pygame
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame
from pathlib import Path


# Rutas de los archivos de audio
AUDIO_PATH = Path(__file__).parent / "media" / "audio"
WORK_AUDIO = AUDIO_PATH / "worktime.wav"
REST_AUDIO = AUDIO_PATH / "restime.wav"
AUTO_REST_AUDIO = AUDIO_PATH / "r-u-there.wav"


class NotificationManager:
    """Gestiona las notificaciones del sistema con reproducción de audio."""
    
    def __init__(self):
        self.app_name = "Observer"
        self._init_audio()
    
    def _init_audio(self):
        """Inicializa el sistema de audio."""
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            print("[Audio] Sistema de audio inicializado")
        except Exception as e:
            print(f"[Audio] Error inicializando audio: {e}")
    
    def _play_audio(self, audio_file: Path):
        """
        Reproduce un archivo de audio.
        
        Args:
            audio_file: Ruta al archivo de audio a reproducir
        """
        try:
            if audio_file.exists():
                pygame.mixer.music.load(str(audio_file))
                pygame.mixer.music.play()
                print(f"[Audio] Reproduciendo: {audio_file.name}")
            else:
                print(f"[Audio] Archivo no encontrado: {audio_file}")
        except Exception as e:
            print(f"[Audio] Error reproduciendo {audio_file.name}: {e}")
    
    def notify(self, title: str, message: str, timeout: int = 10, audio_type: str = None):
        """
        Envía una notificación del sistema con audio opcional.
        
        Args:
            title: Título de la notificación
            message: Mensaje de la notificación
            timeout: Duración en segundos (por defecto 10)
            audio_type: Tipo de audio ('work', 'rest', 'auto_rest', o None para sin audio)
        """
        # Ejecutar en hilo separado para no bloquear
        def _send():
            try:
                # Reproducir audio según el tipo
                if audio_type == 'work':
                    self._play_audio(WORK_AUDIO)
                elif audio_type == 'rest':
                    self._play_audio(REST_AUDIO)
                elif audio_type == 'auto_rest':
                    self._play_audio(AUTO_REST_AUDIO)
                
                # Enviar notificación
                notification.notify(
                    title=title,
                    message=message,
                    app_name=self.app_name,
                    timeout=timeout
                )
                print(f"[Notificación] {title}: {message}")
            except Exception as e:
                print(f"[Notificación] Error al enviar: {e}")
        
        threading.Thread(target=_send, daemon=True).start()
    
    def notify_work(self, title: str, message: str, timeout: int = 10):
        """
        Envía una notificación de trabajo con audio correspondiente.
        
        Args:
            title: Título de la notificación
            message: Mensaje de la notificación
            timeout: Duración en segundos (por defecto 10)
        """
        self.notify(title, message, timeout, audio_type='work')
    
    def notify_rest(self, title: str, message: str, timeout: int = 10):
        """
        Envía una notificación de descanso con audio correspondiente.
        
        Args:
            title: Título de la notificación
            message: Mensaje de la notificación
            timeout: Duración en segundos (por defecto 10)
        """
        self.notify(title, message, timeout, audio_type='rest')
    
    def notify_auto_rest(self, title: str, message: str, timeout: int = 10):
        """
        Envía una notificación de descanso automático con audio correspondiente.
        
        Args:
            title: Título de la notificación
            message: Mensaje de la notificación
            timeout: Duración en segundos (por defecto 10)
        """
        self.notify(title, message, timeout, audio_type='auto_rest')
    
    def cleanup(self):
        """Limpia los recursos de audio."""
        try:
            pygame.mixer.quit()
            print("[Audio] Sistema de audio cerrado")
        except:
            pass
