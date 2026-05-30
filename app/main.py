import threading
from app import ComponentMetadata, message_bus, Message
from app._protocol import AppProtocol
from config.moduls import STT_REGISTRY
from app.stt.stt_engine_protocol import STTEngine

__all__ = ['app']
SUBCOMPONENT_NAME = 'main'


class App(AppProtocol):
    def __init__(self):
        self.name = ComponentMetadata.NAME
        self._exit_flag = threading.Event()
        self.is_running = False
        self._stt_module: STTEngine | None = None

    def start(self, engine: str, model: str, print_result_console: bool = False, *args, **kwargs):
        message_bus.add(
            Message(
                component_id=ComponentMetadata.ID,
                component=ComponentMetadata.NAME,
                subcomponent=SUBCOMPONENT_NAME,
                event='application init...',
                message='запуск подсистем приложения это может занять некоторое время.',
                level='start',
            )
        )

        if engine not in STT_REGISTRY:
            err = Exception(f'`{ComponentMetadata.NAME}` не запущен,не найден движок stt `{engine}`.')
            message_bus.add(
                Message(
                    component_id=ComponentMetadata.ID,
                    component=ComponentMetadata.NAME,
                    subcomponent=SUBCOMPONENT_NAME,
                    event='application run error',
                    message='ошибка загрузки приложения',
                    error=err,
                    level='error',
                )
            )
            raise err
        engine = STT_REGISTRY.get(engine)['module']
        self.is_running = True
        self._stt_module = engine(print_result_console=print_result_console)
        if self._stt_module:
            self._stt_module.start(model_name=model)
        message_bus.add(
            Message(
                component_id=ComponentMetadata.ID,
                component=ComponentMetadata.NAME,
                subcomponent=SUBCOMPONENT_NAME,
                event='application runned',
                message='Приложение запущено и готово к работе.',
                level='start',
            )
        )

    def stop(self):
        self.is_running = False
        if self._stt_module:
            try:
                message_bus.add(
                    Message(
                        component_id=ComponentMetadata.ID,
                        component=ComponentMetadata.NAME,
                        subcomponent=SUBCOMPONENT_NAME,
                        event='application stop process...',
                        message='Остановка подсистем приложения это может занять некоторое время не отключайтесь.',
                        level='stop',
                    )
                )
                self._stt_module.stop()
                message_bus.add(
                    Message(
                        component_id=ComponentMetadata.ID,
                        component=ComponentMetadata.NAME,
                        subcomponent=SUBCOMPONENT_NAME,
                        event='application stop',
                        message='Приложение успешно остановлено.',
                        level='stop',
                    )
                )

            except Exception as err:
                f'`{ComponentMetadata.NAME}` ошибка во время остановки, err: {err}'


app = App()

if __name__ == '__main__':
    app.name = 'app'
    try:
        # app.start(engine='vosk', model='vosk-model-small-ru-0.22', print_result_console=True)
        app.start(engine='whisper', model='large-v3', print_result_console=True)
        input()
        app.stop()
    except KeyboardInterrupt:
        app.stop()
