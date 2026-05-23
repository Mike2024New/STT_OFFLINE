import uvicorn
from fastapi import FastAPI


class Server:
    """
    Управление сервером, запуск остановка
    на вход при создании подать приложение fastapi
    start(port) по умолчанию 8000
    stop() остановка из внешних приложений
    ---------------------------------------------
    В реализации backend (или в cli) нужно вызывать метод server.stop()
    """

    def __init__(self, application: FastAPI):
        self._application = application
        self._server = None

    def start(self, port: int = 8000):
        config = uvicorn.Config(app=self._application, host='localhost', port=port)
        self._server = uvicorn.Server(config)
        self._server.run()  # работает до тех пор пока self.server.shoud_exit=False

    def stop(self):
        self._server.should_exit = True
