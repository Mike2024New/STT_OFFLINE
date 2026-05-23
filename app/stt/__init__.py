"""
Можно модульно подключать и отключать модели
"""

STT_REGISTRY = {}

### ПОДКЛЮЧЕНИЕ ДВИЖКОВ
# I.Подключение моделей VOSK (можно закоментировать/раскомментировать 3 строки ниже, чтобы отключить/включить)
from app.stt.vosk_engine.main import Stt as VoskSTT
from app.stt.vosk_engine import VOSK_MODELS_LIST

STT_REGISTRY['vosk'] = {
    'module': VoskSTT,
    'models_list': VOSK_MODELS_LIST,
    'add_binary': ['vosk'],  # бинарники которые должен подхватить пакет при установке в builder.py
    'add_data': [],  # данные которые должен подхватить пакет при установке в builder.py
}

# II. Подключение моделей WHISPER (можно закоментировать/раскомментировать 3 строки ниже, чтобы отключить/включить)
from app.stt.whisper_engine.main import Stt as WhisperSTT
from app.stt.whisper_engine import WHISPER_MODELS_LIST
from pathlib import Path

STT_REGISTRY['whisper'] = {
    'module': WhisperSTT,
    'models_list': WHISPER_MODELS_LIST,
    'add_binary': ['vosk'],  # бинарники которые должен подхватить пакет при установке в builder.py
    'add_data': [Path('faster_whisper') / 'assets'],  # данные которые должен подхватить пакет при уст. в builder.py
}

### ПОЛУЧЕНИЕ ИНФОРМАЦИИ О ДВИЖКАХ И ЭКСПОРТ
STT_INFO = {engine: STT_REGISTRY[engine]['models_list'] for engine in STT_REGISTRY}

__all__ = ['STT_REGISTRY', 'STT_INFO']
