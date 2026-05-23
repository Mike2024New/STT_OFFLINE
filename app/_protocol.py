from typing import Protocol


class AppProtocol(Protocol):
    """
    Подключаемый класс компонента.
    В классе должны быть реализованы:
    is_running - поле состояния компонента
    start - метод запуска приложения (запускающий все потоки)
    stop - метод остановки приложения (убивающий все потоки внутри)
    """
    is_running: bool

    # запуск движка (например stt/tts/llm модуля).
    # engine в этом модуле выбор движка распознавания речи, например vosk_engine, whisper_engine
    # модель движка например vosk-model-small-ru-0.22 для vosk
    # print_result_console показывать результат в консоль (не исключает шину сообщений)
    def start(self, engine: str, model: str, print_result_console: bool = False, *args, **kwargs) -> bool: ...

    # остановка движка (например stt/tts/llm модуля)
    def stop(self) -> bool: ...
