from app import MODELS_DIR

SUBCOMPONENT_NAME = 'vosk_engine'

VOSK_MODELS_DIR = MODELS_DIR / 'vosk'

# создание необходимых папок
if not VOSK_MODELS_DIR.exists():
    VOSK_MODELS_DIR.mkdir(parents=True, exist_ok=True)

# получение списка моделей
VOSK_MODELS_LIST = [i.parts[-1] for i in VOSK_MODELS_DIR.iterdir() if i.is_dir()]
