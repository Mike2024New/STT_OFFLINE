from server._app import server
from app.main import app as component

component.name = "COMPONENT"
__all__ = ["server", "component"]  # управление сервером во внешних приложениях start(port)/stop()
