import json
import numpy as np
from vosk import Model, KaldiRecognizer
from app.stt.vosk_engine import VOSK_MODELS_DIR
from app import message_bus, ComponentMetadata, Message, settings_manager
from app.stt.vosk_engine import SUBCOMPONENT_NAME
from utils.shut_up_external_logs import shut_up_external_logs
from time import monotonic


class SttCore:
    def __init__(self, print_result_console: bool = False):
        self.model = None
        self.model_name = None
        self.speech_active = False  # говорят ли сейчас (статус для внешних api)
        self.recoginizer = None
        self._print_result_console = print_result_console
        self._start_time_speech = None
        self._end_time_speech = None

    @shut_up_external_logs(enable=True)
    def special_start(self, model_name: str, samplerate: int):
        self.model = Model(model_path=str(VOSK_MODELS_DIR / model_name))
        self.recoginizer = KaldiRecognizer(
            self.model,
            samplerate,
        )

    def start(self, model_name: str):
        self.model_name = model_name
        samplerate = settings_manager.settings.audio_input.samplerate

        if settings_manager.settings.stt.voskOther.vosk_original_logs_print_console:

            self.model = Model(model_path=str(VOSK_MODELS_DIR / model_name))
            self.recoginizer = KaldiRecognizer(self.model, samplerate)
        else:
            self.special_start(model_name=model_name, samplerate=samplerate)

        message_bus.add(
            Message(
                component_id=ComponentMetadata.ID,
                component=ComponentMetadata.NAME,
                subcomponent=SUBCOMPONENT_NAME,
                level='start'
            )
        )

    def stop(self):
        if self.model is not None:
            del self.model
            self.model = None
        if self.recoginizer is not None:
            del self.recoginizer
            self.recoginizer = None
        message_bus.add(
            Message(
                component_id=ComponentMetadata.ID,
                component=ComponentMetadata.NAME,
                subcomponent=SUBCOMPONENT_NAME,
                level='stop'
            )
        )

    def transcribate(self, audio):
        # для безопасного выхода из приложения
        if not hasattr(self, 'recoginizer'):
            return

        render_mode = settings_manager.settings.stt.voskOther.vosk_real_time_render
        if audio.dtype != np.int16:
            audio_int16 = (audio * 32767).astype(np.int16)
        else:
            audio_int16 = audio

        rms = np.sqrt(np.mean(audio ** 2))
        rms_threshold = settings_manager.settings.stt.voskOther.vosk_rms_threshold
        if self.speech_active and rms < rms_threshold and self._end_time_speech is None:
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

            # self.speech_active = False

        if self.recoginizer.AcceptWaveform(audio_int16.tobytes()):
            # vosk_engine определил что фраза завершена
            result = json.loads(self.recoginizer.Result())
            text = result['text']
            if text != '':
                # говорить закончили
                if render_mode:
                    # print(flush=True)  # можно сделать чтобы это удалило последнее сообщение?
                    print('\r' + ' ' * 80 + '\r', end='', flush=True)
                if self._print_result_console:
                    # результат в консоль
                    print(result['text'])

                current_time_metric = round(monotonic() - self._start_time_speech, 2)
                recognized_time = round(monotonic() - self._end_time_speech, 2) if self._end_time_speech else None
                message_bus.add(
                    Message(
                        component_id=ComponentMetadata.ID,
                        component=ComponentMetadata.NAME,
                        subcomponent=SUBCOMPONENT_NAME,
                        level='process',
                        message='Получен распознанный текст.',
                        event='text_recognized',
                        result={
                            'text': result['text'],
                            'model': self.model_name,
                        },
                        data={
                            'current_timestamp': current_time_metric,
                            'recognized_time': recognized_time,
                        }
                    )
                )
                self.speech_active = False

        else:
            if self.recoginizer is None:
                return
            partial = json.loads(self.recoginizer.PartialResult())
            partial_text = partial.get('partial', '')
            if partial_text and not self.speech_active:
                # начали говорить
                self._end_time_speech = None
                self.speech_active = True
                self._start_time_speech = monotonic()
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

            if partial_text:
                # есть частичный результат значит говорят
                if render_mode:
                    print(f'\r{partial_text}', end='', flush=True)
