import json
import numpy as np
from vosk import Model, KaldiRecognizer
from app.stt.vosk_engine import VOSK_MODELS_DIR
from app import message_bus, COMPONENT_NAME, Message, settings_manager
from app.stt.vosk_engine import SUBCOMPONENT_NAME


class SttCore:
    def __init__(self, print_result_console: bool = False):
        self.model = None
        self.speech_active = False  # говорят ли сейчас (статус для внешних api)
        self.recoginizer = None
        self._print_result_console = print_result_console

    def start(self, model_name: str):
        self.model = Model(model_path=str(VOSK_MODELS_DIR / model_name))

        self.recoginizer = KaldiRecognizer(
            self.model,
            settings_manager.settings.audio_input.samplerate,
        )
        message_bus.add(
            Message(
                component=COMPONENT_NAME,
                subcomponent=SUBCOMPONENT_NAME,
                message=f'запущен. Модель `{model_name}`',
                level='info'
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
                component=COMPONENT_NAME,
                subcomponent=SUBCOMPONENT_NAME,
                message=f'stop',
                level='info'
            )
        )

    def transcribate(self, audio):
        # для безопасного выхода из приложения
        if not hasattr(self, 'recoginizer'):
            return

        render_mode = settings_manager.settings.stt.vosk_real_time_render
        if audio.dtype != np.int16:
            audio_int16 = (audio * 32767).astype(np.int16)
        else:
            audio_int16 = audio

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
                message_bus.add(
                    Message(
                        component=COMPONENT_NAME,
                        subcomponent=SUBCOMPONENT_NAME,
                        level='info',
                        message=f'Распознаный текст.',
                        result={
                            'text': result['text'],
                            'model': settings_manager.settings.stt.vosk_model,
                        },
                    )
                )
                self.speech_active = False
        else:
            partial = json.loads(self.recoginizer.PartialResult())
            partial_text = partial.get('partial', '')
            if partial_text and not self.speech_active:
                # начали говорить
                self.speech_active = True

            if partial_text:
                # есть частичный результат значит говорят
                if render_mode:
                    print(f'\r{partial_text}', end='', flush=True)
