import uvicorn
from fastapi import FastAPI
from typing import Literal
from app import message_bus, Message, ComponentMetadata

SUBCOMPONENT = 'server'


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

    def start(self, port: int = 8000, log_level: Literal['debug', 'info', 'warning', 'error'] = 'warning'):
        try:
            host = 'localhost'
            config = uvicorn.Config(app=self._application, host=host, port=port, log_level=log_level)
            self._server = uvicorn.Server(config)
            message_bus.add(
                Message(
                    component_id=ComponentMetadata.ID,
                    component=ComponentMetadata.NAME,
                    subcomponent=SUBCOMPONENT,
                    level='start',
                    data={'host': host, 'port': port, 'log_level': log_level}
                )
            )
            self._server.run()  # работает до тех пор пока self.server.shoud_exit=False
            message_bus.add(
                Message(
                    component_id=ComponentMetadata.ID,
                    component=ComponentMetadata.NAME,
                    subcomponent=SUBCOMPONENT,
                    level='stop',
                )
            )
        except Exception as err:
            message_bus.add(
                Message(
                    component_id=ComponentMetadata.ID,
                    component=ComponentMetadata.NAME,
                    subcomponent=SUBCOMPONENT,
                    level='error',
                    message='Ошибка запуска сервера',
                    event='server is not running',
                    error=err,
                )
            )

    def stop(self):
        self._server.should_exit = True
