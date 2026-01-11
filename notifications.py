"""
Módulo de notificaciones - Envía notificaciones nativas de Windows.
Usa plyer para compatibilidad multiplataforma.
"""

from plyer import notification
import threading


class NotificationManager:
    """Gestiona las notificaciones del sistema."""
    
    def __init__(self):
        self.app_name = "Observer"
    
    def notify(self, title: str, message: str, timeout: int = 10):
        """
        Envía una notificación del sistema.
        
        Args:
            title: Título de la notificación
            message: Mensaje de la notificación
            timeout: Duración en segundos (por defecto 10)
        """
        # Ejecutar en hilo separado para no bloquear
        def _send():
            try:
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
