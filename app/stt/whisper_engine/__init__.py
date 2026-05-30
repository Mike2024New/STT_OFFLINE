SUBCOMPONENT_NAME = 'whisper_engine'

from app import MODELS_DIR

WHISPER_MODELS_DIR = MODELS_DIR / 'whisper'
VOSK_MODELS_DIR_FOR_VAD = MODELS_DIR / 'vosk'  # vosk используется как vad

# создание необходимых папок
WHISPER_MODELS_DIR.mkdir(parents=True, exist_ok=True)
VOSK_MODELS_DIR_FOR_VAD.mkdir(parents=True, exist_ok=True)

# получение списка моделей
WHISPER_MODELS_LIST = []
for mod in WHISPER_MODELS_DIR.iterdir():
    if not mod.is_dir():
        continue
    model_name = mod.parts[-1]
    if 'faster-whisper' in model_name:
        model_name = model_name.split('-faster-whisper-')
        WHISPER_MODELS_LIST.append(model_name[-1])
