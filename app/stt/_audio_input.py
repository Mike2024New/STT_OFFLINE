import threading
from typing import Callable
import queue
import platform
import warnings
import numpy as np
import soundcard as sc
from aec_audio_processing import AudioProcessor

from app import ComponentMetadata, settings_manager, message_bus, Message

# небольшие единичные пропуски для распознвания не критичны
warnings.filterwarnings('ignore', message='data discontinuity')

SUB_COMPONENT_NAME = 'audio_input'

SYSTEM = platform.system()


class AudioInput:
    def __init__(self):
        self.running = False  # защита от повторного запуска
        self._mic_queue = queue.Queue(maxsize=200)
        self._sys_queue = queue.Queue(maxsize=200)
        self._enable_aec_filter = True
        self._component_stop = threading.Event()  # остановка приложения
        self._samplerate = 16000
        self._blocksize = 960
        # Правильная инициализация AEC
        self._aec: AudioProcessor | None = None
        self._aec_frame_size = 0

    @staticmethod
    def _get_looback_speaker():
        """Получение устройства вывода звука"""
        speaker = sc.default_speaker()

        # windows всё просто выдает сразу через WASAPI
        if SYSTEM == 'Windows':
            return sc.get_microphone(id=speaker.id, include_loopback=True)

        # linux уже ищет через PulseAudio
        all_mics = sc.all_microphones(include_loopback=True)
        # поиск по точному id
        for mic in all_mics:
            if mic.id == speaker.id + '.monitor':
                return mic

        # если не найден id, то искать по имени
        for mic in all_mics:
            if 'monitor' in mic.name.lower() and speaker.name in mic.name:
                return mic

        raise RuntimeError(
            "loopback - устройство вывода аудио (колонки или наушники) не найдено. Вероятно не подключен аудиовывод."
        )

    def _mic_worker(self, audio_input):
        """Получает блок информации с микрофона"""
        with audio_input.recorder(samplerate=self._samplerate, channels=1) as recorder:
            while not self._component_stop.is_set():
                try:
                    data = recorder.record(numframes=self._blocksize)
                    self._mic_queue.put(data, block=False)
                except queue.Full:
                    self._mic_queue.get_nowait()
                    self._mic_queue.put(data, block=False)

    def _sys_worker(self, audio_output):
        """Получает блок информации с аудиовыхода направленного на динамик или наушник"""
        with audio_output.recorder(samplerate=self._samplerate, channels=1) as recorder:
            while not self._component_stop.is_set():
                try:
                    data = recorder.record(numframes=self._blocksize)
                    self._sys_queue.put(data, block=False)
                except queue.Full:
                    self._sys_queue.get_nowait()
                    self._sys_queue.put(data, block=False)

    def _aec_filter(self, input_data, otput_data):
        """Фильтр звука входящего в микрофон от звука исходящего с колонок (чтобы ассистент не слышал сам себя)"""
        try:
            clean_chunks = []
            for i in range(0, self._blocksize, self._aec_frame_size):
                mic_chunk = input_data[i:i + self._aec_frame_size]
                sys_chunk = otput_data[i:i + self._aec_frame_size]

                sys_bytes = (sys_chunk * 32767).astype(np.int16).tobytes()
                mic_bytes = (mic_chunk * 32767).astype(np.int16).tobytes()

                self._aec.process_reverse_stream(sys_bytes)
                clean_bytes = self._aec.process_stream(mic_bytes)
                clean_chunks.append(
                    np.frombuffer(clean_bytes, dtype=np.int16).astype(np.float32) / 32767.0
                )
        # если фильтр не сработал то вернуть оригинал
        except Exception:  # noqa
            return input_data

        return np.concatenate(clean_chunks)

    def _orchestrator_listener(self, callback_input, callback_output):
        while not self._component_stop.is_set():
            mic_data = self._mic_queue.get()  # получение одного pcm float32
            sys_data = self._sys_queue.get()  # получение одного pcm float32

            # применить фильтры
            if self._enable_aec_filter:
                mic_data = self._aec_filter(input_data=mic_data, otput_data=sys_data)

            if callback_input is not None:
                callback_input(mic_data.reshape(-1, 1), self._blocksize, None, 0)
            if callback_output is not None:
                callback_output(sys_data.reshape(-1, 1), self._blocksize, None, 0)

    def start(self, callback: Callable | None = None, callback_output: Callable | None = None):
        if self.running:
            print(f'Приложение уже запущено...')
            return

        try:
            self._samplerate = settings_manager.settings.audio_input.samplerate
            self._blocksize = settings_manager.settings.audio_input.blocksize
            self._enable_aec_filter = settings_manager.settings.audio_input.aec_filter

            self._component_stop.clear()
            audio_input = sc.default_microphone()
            audio_output = self._get_looback_speaker()

            if self._enable_aec_filter:
                try:
                    self._aec = AudioProcessor(enable_aec=True, enable_ns=True, enable_agc=True)
                    self._aec.set_stream_format(self._samplerate, 1)
                    self._aec.set_reverse_stream_format(self._samplerate, 1)  # ← ключевая строка!
                    self._aec_frame_size = self._aec.get_frame_size()  # 160
                except Exception as err:
                    self._aec = None
                    self._enable_aec_filter = False
                    message_bus.add(
                        Message(
                            component_id=ComponentMetadata.ID,
                            component=ComponentMetadata.NAME,
                            subcomponent=SUB_COMPONENT_NAME,
                            level='error',
                            message=f'Не удалось подключить AEC.',
                            error=err,
                        )
                    )

            threading.Thread(target=self._mic_worker, kwargs={'audio_input': audio_input}).start()
            threading.Thread(target=self._sys_worker, kwargs={'audio_output': audio_output}).start()
            threading.Thread(
                target=self._orchestrator_listener,
                kwargs={'callback_input': callback, 'callback_output': callback_output},
            ).start()
            self.running = True
            polling_time = self._blocksize / self._samplerate
            message_bus.add(
                Message(
                    component_id=ComponentMetadata.ID,
                    component=ComponentMetadata.NAME,
                    subcomponent=SUB_COMPONENT_NAME,
                    level='start',
                    data={
                        'samplerate': self._samplerate,
                        'blocksize': self._blocksize,
                        'audio_input_device': audio_input.name,
                        'audio_output_device': audio_output.name,
                        'microphone_polling_interval_sec': polling_time,
                        'AEC_filter_enabled': self._enable_aec_filter,
                    }
                )
            )

        except Exception as err:
            raise RuntimeError(f'Не удалось инициализировать аудио стирминг. Ошибка:{err}.')

    def stop(self):
        if self.running:
            self._component_stop.set()
            self.running = False
            message_bus.add(
                Message(
                    component_id=ComponentMetadata.ID,
                    component=ComponentMetadata.NAME,
                    subcomponent=SUB_COMPONENT_NAME,
                    level='stop',
                )
            )


if __name__ == '__main__':
    def audio_input_callback(indata, _frames, _time, _status):
        pcm = indata[:, 0].copy()
        rms = np.sqrt(np.mean(pcm ** 2))
        if rms > 0.02:
            print(rms)


    audio_in = AudioInput()
    audio_in.start(callback=audio_input_callback)
    input()
    audio_in.stop()
