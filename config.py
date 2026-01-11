"""
Módulo de configuración - Maneja la persistencia y valores por defecto.
"""

import json
from pathlib import Path
from dataclasses import dataclass, asdict


# Ruta del archivo de configuración
CONFIG_FILE = Path(__file__).parent / "config.json"


@dataclass
class Config:
    """Configuración de la aplicación con valores por defecto."""
    
    # Tiempos en minutos
    work_minutes: int = 25
    rest_minutes: int = 5
    auto_rest_minutes: int = 5  # Tiempo AFK para considerar descanso automático
    
    # Mensajes de notificación
    msg_rest: str = "Han pasado 25 minutos. Levántate y descansa la vista."
    msg_work: str = "Descanso terminado. Puedes volver a trabajar."
    
    def __post_init__(self):
        """Carga configuración guardada si existe."""
        self.load()
    
    def load(self):
        """Carga la configuración desde archivo JSON."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.work_minutes = data.get("work_minutes", self.work_minutes)
                    self.rest_minutes = data.get("rest_minutes", self.rest_minutes)
                    self.auto_rest_minutes = data.get("auto_rest_minutes", self.auto_rest_minutes)
                    self.msg_rest = data.get("msg_rest", self.msg_rest)
                    self.msg_work = data.get("msg_work", self.msg_work)
                print(f"[Config] Configuración cargada desde {CONFIG_FILE}")
            except Exception as e:
                print(f"[Config] Error al cargar configuración: {e}")
    
    def save(self):
        """Guarda la configuración en archivo JSON."""
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, indent=2, ensure_ascii=False)
            print(f"[Config] Configuración guardada en {CONFIG_FILE}")
        except Exception as e:
            print(f"[Config] Error al guardar configuración: {e}")
    
    def update(self, new_values: dict):
        """Actualiza la configuración con nuevos valores."""
        if "work_minutes" in new_values:
            self.work_minutes = max(1, int(new_values["work_minutes"]))
        if "rest_minutes" in new_values:
            self.rest_minutes = max(1, int(new_values["rest_minutes"]))
        if "auto_rest_minutes" in new_values:
            self.auto_rest_minutes = max(1, int(new_values["auto_rest_minutes"]))
        if "msg_rest" in new_values:
            self.msg_rest = str(new_values["msg_rest"])
        if "msg_work" in new_values:
            self.msg_work = str(new_values["msg_work"])
