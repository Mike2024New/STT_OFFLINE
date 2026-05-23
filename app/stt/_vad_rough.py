import numpy as np
from app import message_bus, Message, settings_manager, COMPONENT_NAME

SUBCOMPONENT_NAME = 'vad_rough'


class VadRough:
    def __init__(self):
        self.is_speech = False  # флаг текущего состояния

    @staticmethod
    def start():
        """Заглушка — нечего загружать"""
        message_bus.add(
            Message(
                component=COMPONENT_NAME,
                subcomponent=SUBCOMPONENT_NAME,
                message=f'запущен',
                level='info'
            )
        )

    @staticmethod
    def process(audio: np.ndarray) -> bool:
        """Три быстрых проверки, ~микросекунды"""
        # 1. RMS — громкость
        rms = np.sqrt(np.mean(audio ** 2))
        if rms < settings_manager.settings.vad_rough.rms_thresh:
            return False

        # 2. Crest Factor — речь vs хлопки/тоны
        peak = np.max(np.abs(audio))
        crest = peak / (rms + 1e-10)  # +1e-10 чтобы не делить на ноль
        if crest > settings_manager.settings.vad_rough.crest_max:
            return False

        # 3. Zero-Crossing Rate — речевой рисунок
        zcr = np.sum(np.diff(np.sign(audio)) != 0) / len(audio)
        zcr_min, zcr_max = settings_manager.settings.vad_rough.zcr_bounds
        if not (zcr_min <= zcr <= zcr_max):
            return False

        return True

    def reset(self):
        """Заглушка"""
        pass

    @staticmethod
    def stop():
        """Заглушка — нечего выгружать"""
        message_bus.add(
            Message(
                component=COMPONENT_NAME,
                subcomponent=SUBCOMPONENT_NAME,
                message=f'остановлен',
                level='info'
            )
        )
