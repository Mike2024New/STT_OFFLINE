import sounddevice as sd
from typing import Callable
from app import COMPONENT_NAME, settings_manager, message_bus, Message

SUB_COMPONENT_NAME = 'audio_input'


class AudioInput:
    def __init__(self):
        """
        Общение с звуковой картой, получает входной pcm
        и выполняет с ним действия прописанные в callback.
        Инициализатор облегченный, привод выполняется через start
        """
        self.stream = None  # итератор для получения pcm (input/output)
        self.running = False  # защита от повторного запуска

    def start(self, callback: Callable):
        """
        Запуск опроса звуковой карты вход (микрофон)
        Выполнение callback с pcm данными
        """
        if self.running:
            return
        self.running = True

        try:
            self.stream = sd.InputStream(
                samplerate=settings_manager.settings.audio_input.samplerate,
                blocksize=settings_manager.settings.audio_input.blocksize,
                channels=settings_manager.settings.audio_input.channels,
                dtype=settings_manager.settings.audio_input.dtype,
                callback=callback
            )
            polling_time = settings_manager.settings.audio_input.blocksize / settings_manager.settings.audio_input.samplerate
            message_bus.add(
                Message(
                    component=COMPONENT_NAME,
                    level='info',
                    message=f'модуль подключен. Опрос микрофона раз в {polling_time} секунд.',
                    subcomponent=SUB_COMPONENT_NAME,
                )
            )
            self.stream.start()
        except Exception as err:
            raise RuntimeError(f'Не удалось инициализировать аудио стирминг. Ошибка:{err}.')

    def stop(self):
        """Прекратить опрос аудиокарты, высвободить ресурсы."""
        self.running = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        message_bus.add(
            Message(
                component=COMPONENT_NAME,
                level='info',
                message=f'микрофон остановлен',
                subcomponent=SUB_COMPONENT_NAME,
            )
        )


if __name__ == '__main__':
    import numpy as np


    def audio_callback(indata, _frames, _time, _status):
        pcm = indata[:, 0].copy()
        rms = np.sqrt(np.mean(pcm ** 2))
        print(rms)


    audio_input = AudioInput()
    audio_input.start(callback=audio_callback)
    input()
