import queue
import threading
from collections import deque
import numpy as np
import atexit
from app.stt._audio_input import AudioInput
from app.stt.vad.vad_vosk import VadVosk
from app.stt.whisper_engine._core import SttCore
from app import settings_manager, message_bus, Message, ComponentMetadata
from app.stt.whisper_engine import SUBCOMPONENT_NAME, WHISPER_MODELS_LIST
from time import monotonic

__all__ = ['Stt', ]


class Stt:
    def __init__(self, print_result_console: bool = False):
        self._audio_input: AudioInput | None = None
        self._vads = []
        self._stt: SttCore | None = None
        # предбуфер который обновляется каждые maxlen чанков
        self._pre_buffer = deque(maxlen=settings_manager.settings.stt.whisperOther.whisper_pre_buffer_max_len)
        self._speech_buffer = []  # буфер для накопления фраз
        self.speech_active = False
        self._silence_counter = 0
        # Отдельный поток для transcribe
        self._stt_queue = queue.Queue()  # очередь аудиобуферов
        self._stt_thread = threading.Thread(target=self._stt_worker, daemon=True)
        self._print_result_console = print_result_console

        self._start_time_speech = None
        self._end_time_speech = None
        self.start_speech = False

        atexit.register(self.stop)

    def _stt_worker(self):
        """Отдельный поток — только распознавание, не блокирует аудио"""
        while True:
            full_audio = self._stt_queue.get()  # ждёт буфер
            if full_audio is None:  # стоп-сигнал
                break

            self._end_time_speech = monotonic()
            message_bus.add(
                Message(
                    component_id=ComponentMetadata.ID,
                    component=ComponentMetadata.NAME,
                    subcomponent=SUBCOMPONENT_NAME,
                    level='process',
                    message=f'Закончили говорить.',
                    event='speech_ended',
                    data={
                        'current_timestamp': round(monotonic() - self._start_time_speech, 2),
                        'recognized_time': None,
                    }
                )
            )

            text = self._stt.transcribe(audio=full_audio)
            if text:
                # на прямую печать результата в консоль (для cli.py и промежуточных запусков модулей)
                if self._print_result_console:
                    print(text)
                current_time_metric = round(monotonic() - self._start_time_speech, 2)
                recognized_time = round(monotonic() - self._end_time_speech, 2)
                message_bus.add(
                    Message(
                        component_id=ComponentMetadata.ID,
                        component=ComponentMetadata.NAME,
                        subcomponent=SUBCOMPONENT_NAME,
                        level='process',
                        message='Получен распознанный текст.',
                        event='text_recognized',
                        result={
                            'text': text,
                        },
                        data={
                            'current_timestamp': current_time_metric,
                            'recognized_time': recognized_time,
                        }
                    )
                )

    def _audio_callback(self, indata, _frames, _time, _status):
        pcm = indata[:, 0].copy()
        self._pre_buffer.append(pcm)
        chunk_is_speech = all(vad.process(pcm) for vad in self._vads)

        # проверка через RMS фильтр, так как vosk VAD уходит в Recoginizer и это дает временную задержку
        # RMS видит тишину и дает отсечку не дожидаясь Recoginizer
        if chunk_is_speech:
            if not self.start_speech:
                self.start_speech = True
                chunk_is_speech = True
            else:
                rms = np.sqrt(np.mean(pcm ** 2))
                rms_threshold = settings_manager.settings.stt.whisperOther.whisper_rms_threshold
                chunk_is_speech = True if rms > rms_threshold else False
        else:
            if self.start_speech:
                self.start_speech = False
                chunk_is_speech = False

        if chunk_is_speech:
            # если чанк был распознан как речь (то есть vad утверждают что сейчас говорят)
            if not self.speech_active:  # начало речи
                message_bus.add(
                    Message(
                        component_id=ComponentMetadata.ID,
                        component=ComponentMetadata.NAME,
                        subcomponent=SUBCOMPONENT_NAME,
                        level='process',
                        event='speech_started',
                        message=f'Начали говорить',
                        data={
                            'current_timestamp': 0.0,
                            'recognized_time': None,
                        }
                    )
                )

                self._start_time_speech = monotonic()
                self._speech_buffer = list(self._pre_buffer)  # добавление тишины (чтобы речь не была рваной)
            self.speech_active = True
            self._silence_counter = 0
            self._speech_buffer.append(pcm)

        elif self.speech_active:
            # если тишина, но ещё не истёк silence_time (не прошло время тишины)
            self._silence_counter += settings_manager.settings.audio_input.blocksize / settings_manager.settings.audio_input.samplerate
            self._speech_buffer.append(pcm)

            if self._silence_counter > settings_manager.settings.stt.whisperOther.whisper_silence_time:  # вынести в конфиг
                self.speech_active = False

                post_silence = list(self._pre_buffer)[-5:]  # для 1024 ~ 300 мс
                self._speech_buffer.extend(post_silence)  # добавление тишины в конец буфера (лучше распознается tts)
                full_audio = np.concatenate(self._speech_buffer)
                # отправка полученного фрагмента разговора в whisper_engine / vosk_engine
                self._on_speech_end(full_audio=full_audio)
                for vad in self._vads:
                    vad.reset()
                self._speech_buffer = []  # сброс буфера
                self._pre_buffer.clear()  # очистка предбуфера

    def _on_speech_end(self, full_audio: np.ndarray):
        self._stt_queue.put(full_audio.copy())

    def start(self, model_name: str | None = None) -> None:
        model_name = model_name or settings_manager.settings.stt.whisper_model
        if model_name not in WHISPER_MODELS_LIST:
            raise RuntimeError(
                f'Не удалось запустить whisper, так как указана не существующая модель `{model_name}`. Выберите из {WHISPER_MODELS_LIST}')
        try:
            # инициализация
            self._audio_input = AudioInput()
            # регистрация vad систем (здесь можно устанавливать множество фильтров)
            self._vads.append(VadVosk())
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

        if self._stt is not None:
            self._stt.stop()
            self._stt = None

        if self._vads:
            for vad in self._vads:
                if vad is not None:
                    vad.stop()
            self._vads = []


if __name__ == '__main__':
    stt = Stt(print_result_console=True)
    stt.start(model_name='large-v3')
    input()
    stt.stop()
