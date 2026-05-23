import queue
import threading
from collections import deque
import numpy as np
import atexit
from app.stt._audio_input import AudioInput
from app.stt._vad_rough import VadRough
from app.stt.whisper_engine._core import SttCore
from app import settings_manager, message_bus, Message, COMPONENT_NAME
from app.stt.whisper_engine import SUBCOMPONENT_NAME, WHISPER_MODELS_LIST

__all__ = ['Stt', ]


class Stt:
    def __init__(self, print_result_console: bool = False):
        self._audio_input: AudioInput | None = None
        self._vads = []
        self._stt: SttCore | None = None
        # предбуфер который обновляется каждые maxlen чанков
        self._pre_buffer = deque(maxlen=settings_manager.settings.stt.pre_buffer_max_len)
        self._speech_buffer = []  # буфер для накопления фраз
        self.speech_active = False
        self._silence_counter = 0
        # Отдельный поток для transcribe
        self._stt_queue = queue.Queue()  # очередь аудиобуферов
        self._stt_thread = threading.Thread(target=self._stt_worker, daemon=True)
        self._print_result_console = print_result_console

        atexit.register(self.stop)

    def _stt_worker(self):
        """Отдельный поток — только распознавание, не блокирует аудио"""
        while True:
            full_audio = self._stt_queue.get()  # ждёт буфер
            if full_audio is None:  # стоп-сигнал
                break
            text = self._stt.transcribe(audio=full_audio)
            if text:
                # на прямую печать результата в консоль (для cli.py и промежуточных запусков модулей)
                if self._print_result_console:
                    print(text)
                message_bus.add(
                    Message(
                        component=COMPONENT_NAME,
                        subcomponent=SUBCOMPONENT_NAME,
                        level='info',
                        message=f'Распознаный текст.',
                        result={
                            'text': text,
                            'model': settings_manager.settings.stt.whisper_model,
                        },
                    )
                )

    def _audio_callback(self, indata, _frames, _time, _status):
        pcm = indata[:, 0].copy()
        self._pre_buffer.append(pcm)
        chunk_is_speech = all(vad.process(pcm) for vad in self._vads)

        if chunk_is_speech:
            # если речь в текущем моменте
            if not self.speech_active:  # начало речи
                self._speech_buffer = list(self._pre_buffer)  # добавление тишины (чтобы речь не была рваной)
            self.speech_active = True
            self._silence_counter = 0
            self._speech_buffer.append(pcm)

        elif self.speech_active:
            # если тишина, но ещё не истёк silence_time (не прошло время тишины)
            self._silence_counter += settings_manager.settings.audio_input.blocksize / settings_manager.settings.audio_input.samplerate
            self._speech_buffer.append(pcm)

            if self._silence_counter > settings_manager.settings.vad_rough.silence_time:
                self.speech_active = False
                post_silence = list(self._pre_buffer)[-5:]  # для 1024 ~ 300 мс
                self._speech_buffer.extend(post_silence)  # добавление тишины в конец буфера (лучше распознается tts)
                full_audio = np.concatenate(self._speech_buffer)
                self._on_speech_end(
                    full_audio=full_audio)  # отправка полученного фрагмента разговора в whisper_engine / vosk_engine
                for vad in self._vads:
                    vad.reset()
                self._speech_buffer = []  # сброс буфера
                self._pre_buffer.clear()  # очистка предбуфера

    def _on_speech_end(self, full_audio: np.ndarray):
        self._stt_queue.put(full_audio.copy())

    def start(self, model_name: str | None = None):
        model_name = model_name or settings_manager.settings.stt.whisper_model
        if model_name not in WHISPER_MODELS_LIST:
            raise RuntimeError(
                f'Не удалось запустить whisper, так как указана не существующая модель `{model_name}`. Выберите из {WHISPER_MODELS_LIST}')
        try:
            # инициализация
            self._audio_input = AudioInput()
            # регистрация vad систем (здесь можно устанавливать множество фильтров)
            self._vads.append(VadRough())
            # регистрация stt
            self._stt = SttCore()
            self._stt.start(model_name=model_name)
            # запуск подсистем
            for vad in self._vads:
                vad.start()  # запуск каждого vad
            self._audio_input.start(callback=self._audio_callback)
            self._stt_thread.start()  # запуск воркера который контролирует запуск аудио
        except Exception as err:
            message_bus.add(
                Message(
                    component=COMPONENT_NAME,
                    subcomponent=SUBCOMPONENT_NAME,
                    level='error',
                    message=f'whisper не удалось запустить. Причина: {err}'
                )
            )
            raise RuntimeError(f'whisper не удалось запустить. Причина: {err}')

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
    stt.start(model_name='medium')
    input()
    stt.stop()
