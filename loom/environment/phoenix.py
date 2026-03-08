import logging
import subprocess
import psutil
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential
import requests

logger = logging.getLogger("loom")
VITE_PORT = 5173

class PhoenixServer:
    """Manages the lifecycle of the Vite dev server."""
    
    def __init__(self, port: int = VITE_PORT):
        self.port = port
        self.process: Optional[subprocess.Popen] = None

    def kill(self):
        """Kills any process listening on the target port."""
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                for conn in proc.connections(kind='inet'):
                    if conn.laddr.port == self.port:
                        logger.warning(f"Killing zombie process {proc.name()} (PID: {proc.pid}) on port {self.port}")
                        proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

    def spawn(self):
        """Starts the Vite server in the background."""
        self.kill() # Ensure clean slate
        import os
        logger.info("Spawning Phoenix Server (Vite)...")
        try:
            # Create/clear the error log
            self.log_path = os.path.join("app", "vite.log")
            with open(self.log_path, "w") as f:
                f.write(f"--- Spawned at {psutil.time.time()} ---\n")

            # Using shell=True only on Windows for compatibility with npm.cmd
            with open(self.log_path, "a") as f:
                self.process = subprocess.Popen(
                    ["npm", "run", "dev"], 
                    cwd="app",
                    stdout=f,
                    stderr=f,
                    shell=(os.name == 'nt')
                )
        except Exception as e:
            logger.error(f"Failed to spawn Vite: {e}")
            raise

    def get_logs(self, tail_lines: int = 20) -> str:
        """Reads the last few lines of the Vite log."""
        import os
        log_path = os.path.join("app", "vite.log")
        if not os.path.exists(log_path):
            return "No log file found."
        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                return "".join(lines[-tail_lines:])
        except Exception as e:
            return f"Failed to read logs: {e}"

    @retry(stop=stop_after_attempt(10), wait=wait_exponential(multiplier=1, min=2, max=10))
    def wait_for_ready(self):
        """Polls localhost until it returns 200 OK."""
        url = f"http://127.0.0.1:{self.port}"
        logger.info(f"Waiting for {url}...")
        response = requests.get(url, timeout=2)
        if response.status_code == 200:
            logger.info("Phoenix Server is READY.")
            return True
        raise Exception("Server not ready")
