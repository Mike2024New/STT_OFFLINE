"""
Можно модульно подключать и отключать модели
"""

INSTALL_DEPENDS = {'add_data': [], 'add_binary': [], 'excluded': []}  # добавление пакетов и бинарников для Pyinstaller
STT_INFO = {}
STT_REGISTRY = {}
__all__ = ['STT_REGISTRY', 'STT_INFO', 'INSTALL_DEPENDS']


def add_vosk(enabled: bool = False):
    if enabled:
        from app.stt.vosk_engine.main import Stt as VoskSTT
        from app.stt.vosk_engine import VOSK_MODELS_LIST

        STT_REGISTRY['vosk'] = {
            'module': VoskSTT,
            'models_list': VOSK_MODELS_LIST,
        }
        INSTALL_DEPENDS['add_binary'].append('vosk')
        STT_INFO['vosk'] = VOSK_MODELS_LIST
        return

    # Если модуль не подключается, то убрать хвосты
    # Не нужно теперь отключать хвосты так как vosk используется как vad для whisper
    # INSTALL_DEPENDS['excluded'].extend([
    #     'vosk',
    #     'vosk_transcriber',
    #     'vosk_text',
    #     'kaldi_recognizer',
    #     'srt',
    #     'ffmpeg_python',
    #     'pydub',
    # ])


def add_whisper(enabled: bool = False):
    if enabled:
        from app.stt.whisper_engine.main import Stt as WhisperSTT
        from app.stt.whisper_engine import WHISPER_MODELS_LIST
        from pathlib import Path

        STT_REGISTRY['whisper'] = {
            'module': WhisperSTT,
            'models_list': WHISPER_MODELS_LIST,
        }
        INSTALL_DEPENDS['add_data'].append(Path('faster_whisper') / 'assets')
        STT_INFO['whisper'] = WHISPER_MODELS_LIST
        return

    # Если модуль не подключается, то убрать хвосты
    INSTALL_DEPENDS['excluded'].extend([
        'faster_whisper',
        'whisper',
        'ctranslate2',
        'onnxruntime',
        'tensorflow',
        'torch',
        'torchvision',
        'torchaudio',
        'av',
        'tiktoken',
        'openai_whisper',
        'whisper_timestamped',
        'stable_whisper',
        'whisperx',
    ])


add_vosk(enabled=True)
add_whisper(enabled=True)
# print(INSTALL_DEPENDS)
