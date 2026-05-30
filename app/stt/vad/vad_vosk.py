from vosk import Model, KaldiRecognizer
import numpy as np
import json
from app import MODELS_DIR, message_bus, Message, ComponentMetadata, settings_manager
from utils.shut_up_external_logs import shut_up_external_logs

SUBCOMPONENT = 'VAD.vosk'

# Важно проконтролировать чтобы модель SMALL была загружена (ну либо выставить галочку self._is_passed - "пробитый конденсатор")
VOSK_MODEL_PATH = MODELS_DIR / 'vosk' / 'vosk-model-small-ru-0.22'


class VadVosk:
    def __init__(self):
        self.model = None
        self.recognizer = None
        self.is_speech = False
        self._is_passed = False

    @shut_up_external_logs(enable=True)
    def _special_start(self, samplerate):
        """Вынес в отдельный метод чтобы подавить оригинальные логи vosk"""
        self.model = Model(model_path=str(VOSK_MODEL_PATH))
        self.recognizer = KaldiRecognizer(self.model, samplerate)

    def start(self):
        try:
            samplerate = settings_manager.settings.audio_input.samplerate

            if settings_manager.settings.stt.voskOther.vosk_original_logs_print_console:
                self.model = Model(model_path=str(VOSK_MODEL_PATH))
                self.recognizer = KaldiRecognizer(self.model, samplerate)
            else:
                self._special_start(samplerate=samplerate)

            message_bus.add(
                message=Message(
                    component_id=ComponentMetadata.ID,
                    component=ComponentMetadata.NAME,
                    subcomponent=SUBCOMPONENT,
                    level='start',
                    data={'samplerate': samplerate},
                )
            )
        except Exception as err:
            import traceback

            if not VOSK_MODEL_PATH.exists():
                message_bus.add(
                    message=Message(
                        component_id=ComponentMetadata.ID,
                        component=ComponentMetadata.NAME,
                        subcomponent=SUBCOMPONENT,
                        level='error',
                        message=f'Не удалось запустить компонент {SUBCOMPONENT}',
                        event=f'{SUBCOMPONENT} not runned',
                        error=err,
                    )
                )
                self._is_passed = True

    def process(self, pcm) -> bool:
        if self._is_passed:  # если случились ошибки внутри то пробрасывать True наружу, чтобы приложение не валилось
            return True

        if not hasattr(self, 'recognizer'):
            return False

        if not hasattr(self.recognizer, 'AcceptWaveform'):
            return False

        audio_int16 = (pcm * 32767).astype(np.int16)

        if self.recognizer.AcceptWaveform(audio_int16.tobytes()):
            result = json.loads(self.recognizer.Result())
            text = result['text']
            if text:
                self.is_speech = False
        else:
            if self.recognizer is None:
                self.is_speech = False

            partial = json.loads(self.recognizer.PartialResult())
            partial_text = partial.get('partial', '')
            if partial_text:
                self.is_speech = True
        return self.is_speech

    def reset(self):
        pass

    def stop(self):
        self.is_speech = False
        if self.recognizer:
            del self.recognizer
            self.recognizer = None
        if self.model:
            del self.model
            self.model = None

        message_bus.add(
            message=Message(
                component_id=ComponentMetadata.ID,
                component=ComponentMetadata.NAME,
                subcomponent=SUBCOMPONENT,
                level='stop',
            )
        )
