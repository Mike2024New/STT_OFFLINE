import ctranslate2
import numpy as np
from faster_whisper import WhisperModel
from app import COMPONENT_NAME, message_bus, Message, settings_manager
from app.stt.whisper_engine import SUBCOMPONENT_NAME, WHISPER_MODELS_DIR


class SttCore:
    def __init__(self):
        self._model = None

    def start(self, model_name: str = None, samplerate: int = 16000):
        device = 'cuda' if ctranslate2.get_cuda_device_count() > 0 else 'cpu'
        compute_type = 'float16' if device == 'cuda' else 'int8'

        test_audio = np.zeros(samplerate * 2, dtype=np.float32)
        # попытка загрузиться в обычном режиме с переданными в настройках параметрами
        try:
            self._model = WhisperModel(
                model_name,
                device=device,
                compute_type=compute_type,
                download_root=str(WHISPER_MODELS_DIR),
                local_files_only=True,  # только локальные модели
            )
            # проверка что загруженная модель работает корректно (иногда бывает устаревший драйвер cuda)
            self.transcribe(audio=test_audio)
            msg = f'whisper загружен. device={device}, model={model_name}'
        except Exception:  # noqa
            try:
                self._model = WhisperModel(
                    model_name,
                    device='cpu',
                    compute_type='int8',
                    download_root=str(WHISPER_MODELS_DIR),
                    local_files_only=True,
                )
                self.transcribe(audio=test_audio)
                msg = f'whisper загружен. device=cpu, model={model_name}'
            # но если он не загрузится то это фатальная ошибка
            except Exception as err:  # noqa
                raise RuntimeError(f'{err}')

        message_bus.add(
            Message(
                component=COMPONENT_NAME,
                subcomponent=SUBCOMPONENT_NAME,
                level='info',
                message=msg,
            )
        )

    def transcribe(self, audio: np.ndarray) -> str:
        try:
            translate_mode = 'translate' if settings_manager.settings.stt.whisper_translate_eng else 'transcribe'
            segments, _ = self._model.transcribe(
                audio,
                beam_size=5,
                task=translate_mode,
                vad_filter=True,
                vad_parameters=dict(
                    # загрузка настроек из конфигурации
                    settings_manager.settings.stt.whisper_vad
                )
            )
        except Exception as err:
            raise RuntimeError(f'Ошибка транскрибации звука в аудио: {err}')
        full_text = " ".join(segment.text for segment in segments)
        return full_text.strip()

    def stop(self):
        if self._model is not None:
            del self._model
            self._model = None
        message_bus.add(
            Message(
                component=COMPONENT_NAME,
                subcomponent=SUBCOMPONENT_NAME,
                message=f'stop',
                level='info'
            )
        )


if __name__ == '__main__':
    stt = SttCore()
    stt.start()
    stt.stop()
