import atexit
from app import message_bus, Message, COMPONENT_NAME, settings_manager
from app.stt.vosk_engine._core import SttCore
from app.stt._audio_input import AudioInput
from app.stt._vad_rough import VadRough
from app.stt.vosk_engine import SUBCOMPONENT_NAME

__all__ = ['Stt', ]


class Stt:
    def __init__(self, print_result_console: bool = False):
        self._audio_input: AudioInput = AudioInput()
        self._stt = SttCore(print_result_console=print_result_console)
        self._vads = []
        self._print_result_console = print_result_console
        self.speech_active = False
        atexit.register(self.stop)

    def _audio_callback(self, indata, _frames, _time, _status):
        self.speech_active = self._stt.speech_active  # проброс speech_active (статус речь сейчас или нет)
        self._stt.transcribate(
            audio=indata[:, 0].copy(),
        )

    def start(self, model_name: str | None = None) -> bool:  # noqa
        model_name = model_name or settings_manager.settings.stt.vosk_model
        try:
            self._stt.start(model_name=model_name)
            self._vads.append(VadRough())
            for vad in self._vads:
                vad.start()  # запуск каждого vad
            # слушатель аудио подключается в последнюю очередь (из за callback)
            self._audio_input.start(callback=self._audio_callback)
        except Exception as err:
            message_bus.add(
                Message(
                    component=COMPONENT_NAME,
                    subcomponent=SUBCOMPONENT_NAME,
                    level='error',
                    message=f'vosk_stt не удалось запустить. {err}'
                )
            )
            return False
        return True

    def stop(self):
        # порядок отключения важен!
        if self._audio_input is not None:
            self._audio_input.stop()

        if self._stt:
            self._stt.stop()

        for vad in self._vads:
            if vad is not None:
                vad.stop()


if __name__ == '__main__':
    stt = Stt(print_result_console=True)
    stt.start()
    input()
