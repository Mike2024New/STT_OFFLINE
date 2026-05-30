from collections import deque
from typing import Literal, Any, Generator
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import threading

_FMT = '%H:%M %d.%m.%Y'

import traceback


class Message(BaseModel):
    component_id: str = Field(description='Уникальный id компонента, полезно для нескольких экземпляров приложения')
    component: str = Field(description='Публичное название компонента, так его видят другие API, например STT.')
    subcomponent: str = Field(description='Внутреннее название подкомпонетра, например STT.audio_input')
    level: Literal[
        'start', 'stop', 'process',  # уровни компонента, start - запуск, stop - остановка, process - работа компонента
        'debug', 'info', 'warning', 'error', 'critical'  # универсальные логи
    ]
    message: str | None = Field(default=None, description='Человекочитаемое понятное сообщение.')
    event: str | None = Field(default=None, description='Опциональное машиночитаемое событие (для парсеров логов).')
    date: str = Field(default_factory=lambda: datetime.now().strftime(_FMT), description='Время происшествия.')
    error: Any | dict = Field(default_factory=dict,
                              description='Объект err, поствалидатор разберет на ошибку и трассировку.')
    result: dict[str, Any] = Field(default_factory=dict, description=f'если через сообщение передаются результаты.')
    data: dict[str, Any] = Field(default_factory=dict, description=f'Дополнительные даннные, например метрики.')

    @field_validator('error', mode='before')  # noqa
    @classmethod
    def error_extract(cls, err):
        if err is None:
            return {}
        if isinstance(err, dict):
            return err
        if isinstance(err, Exception):
            return {
                'err': str(err),
                'traceback': ''.join(traceback.format_exception(type(err), err, err.__traceback__))
            }
        return {'err': str(err)}


class MessageBus:
    def __init__(self, max_size: int = 1000, print_message: bool = False):
        self._messages = deque(maxlen=max_size)
        self._lock = threading.Lock()  # защита от гонки состояний
        self._message_new_event = threading.Event()  # наблюдатель за появлением сообщений
        self._print_message = print_message

    def add(self, message: Message) -> None:
        """
        Добавить сообщениеe
        :param message: основная информация о сообщении см класс Message
        :return:
        """
        with self._lock:
            self._messages.append(message)
            self._message_new_event.set()  # сигнал о том что сообщение получено
            if self._print_message:
                print(message)

    def get_all(self) -> list[Message]:
        """
        Отдать все накопленные сообщения по прямому запросу
        :return: список Messages
        """
        with self._lock:
            messages = list(self._messages)
            self._messages.clear()
            self._message_new_event.clear()
        return messages

    def stream(self, timeout: float = 0.1) -> Generator[Message, None, None]:
        """
        Для webSocket/CLI - бесконечный поток сообщений с авточисткой. Отдал удалил
        :return: получил сообещние сразу его отдал
        """
        while True:
            self._message_new_event.wait(timeout=timeout)  # возбуждаться на каждый сигнал полученного сообщения
            with self._lock:
                while self._messages:
                    yield self._messages.popleft()
                self._message_new_event.clear()

    def reset(self):
        with self._lock:
            self._messages.clear()
            self._message_new_event.clear()


if __name__ == '__main__':
    msg = Message(
        component_id='Любой идентификатор (но в компоненте он генерится из UUID)',
        component='STT',
        subcomponent='STT.audio_input',
        level='debug',
        message='Компонент запущен'
    )
    print(msg)
