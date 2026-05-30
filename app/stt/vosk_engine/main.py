import atexit
from app import message_bus, Message, ComponentMetadata, settings_manager
from app.stt.vosk_engine._core import SttCore
from app.stt._audio_input import AudioInput
from app.stt.vosk_engine import SUBCOMPONENT_NAME

__all__ = ['Stt', ]


class Stt:
    def __init__(self, print_result_console: bool = False):
        self._audio_input: AudioInput = AudioInput()
        self._stt = SttCore(print_result_console=print_result_console)
        self._print_result_console = print_result_console
        self.speech_active = False
        atexit.register(self.stop)

    def _audio_callback(self, indata, _frames, _time, _status):
        self.speech_active = self._stt.speech_active  # проброс speech_active (статус речь сейчас или нет)
        if self._stt is not None:
            self._stt.transcribate(audio=indata[:, 0].copy())

    def start(self, model_name: str | None = None) -> None:  # noqa
        model_name = model_name or settings_manager.settings.stt.vosk_model
        try:
            self._stt.start(model_name=model_name)
            # слушатель аудио подключается в последнюю очередь (из за callback)
            self._audio_input.start(callback=self._audio_callback)
        except Exception as err:
            message_bus.add(
                Message(
                    component_id=ComponentMetadata.ID,
                    component=ComponentMetadata.NAME,
                    subcomponent=SUBCOMPONENT_NAME,
                    level='error',
                    event=f'{SUBCOMPONENT_NAME} is not runned',
                    message=f'{SUBCOMPONENT_NAME} не удалось запустить.',
                    error=err,
                )
            )
            raise RuntimeError(f'{SUBCOMPONENT_NAME} не удалось запустить. Причина: {err}')

    def stop(self):
        # порядок отключения важен!
        if self._audio_input is not None:
            self._audio_input.stop()
            self._audio_input = None

        if self._stt is not None:
            self._stt.stop()
            self._stt = None


if __name__ == '__main__':
    stt = Stt(print_result_console=True)
    stt.start()
    input()
    stt.stop()
