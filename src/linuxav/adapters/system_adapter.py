import subprocess
import platform
import logging
from typing import Dict


class SystemAdapter:
    def __init__(self):
        self.logger = logging.getLogger("linuxav.system_adapter")

    def get_system_info(self) -> Dict:
        return {
            "os": platform.system(),
            "os_version": platform.version(),
            "architecture": platform.machine(),
            "python_version": platform.python_version()
        }

    def get_disk_usage(self, path: str = "/") -> Dict:
        try:
            result = subprocess.run(
                ["df", "-h", path],
                capture_output=True,
                text=True
            )
            lines = result.stdout.strip().split("\n")
            if len(lines) > 1:
                parts = lines[1].split()
                return {
                    "total": parts[1],
                    "used": parts[2],
                    "available": parts[3],
                    "percent": parts[4]
                }
        except Exception as e:
            self.logger.error(f"Error obteniendo info de disco: {e}")
        return {}

    def get_memory_info(self) -> Dict:
        try:
            result = subprocess.run(
                ["free", "-h"],
                capture_output=True,
                text=True
            )
            return {"output": result.stdout}
        except Exception:
            return {}

    def notify_user(self, title: str, message: str):
        try:
            subprocess.run(
                ["notify-send", title, message],
                capture_output=True
            )
        except Exception as e:
            self.logger.warning(f"No se pudo enviar notificación: {e}")
