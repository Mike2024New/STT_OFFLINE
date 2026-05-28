import threading
from app import COMPONENT_NAME, message_bus, Message
from app._protocol import AppProtocol
from config.moduls import STT_REGISTRY
from app.stt.stt_engine_protocol import STTEngine

__all__ = ['app']


class App(AppProtocol):
    def __init__(self):
        self.name = COMPONENT_NAME
        self._exit_flag = threading.Event()
        self.is_running = False
        self._stt_module: STTEngine | None = None

    def start(self, engine: str, model: str, print_result_console: bool = False, *args, **kwargs):
        if engine not in STT_REGISTRY:
            message_bus.add(
                Message(
                    component=COMPONENT_NAME,
                    subcomponent=COMPONENT_NAME,
                    message=f'`{COMPONENT_NAME}` не запущен,не найден движок stt `{engine}`.',
                    level='error',
                )
            )
            raise RuntimeError(f'`{COMPONENT_NAME}` не запущен,не найден движок stt `{engine}`.')
        engine = STT_REGISTRY.get(engine)['module']
        self.is_running = True
        self._stt_module = engine(print_result_console=print_result_console)
        if self._stt_module:
            self._stt_module.start(model_name=model)

    def stop(self):
        self.is_running = False
        if self._stt_module:
            try:
                self._stt_module.stop()
            except Exception as err:
                f'`{COMPONENT_NAME}` ошибка во время остановки, err: {err}'


app = App()

if __name__ == '__main__':
    app.name = 'app'
    try:
        app.start(engine='vosk', model='vosk-model-small-ru-0.22', print_result_console=True)
        # app.start(engine='whisper', model='large-v3', print_result_console=True)
        input()
        app.stop()
    except KeyboardInterrupt:
        app.stop()
