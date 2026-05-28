from typing import Literal
from pydantic import BaseModel, Field, field_validator
import numpy as np

__all__ = ['settings', 'table_change_events', 'reboot_fileds', 'Settings']


class AudioInput(BaseModel):
    model_config = {'validate_default': True}
    samplerate: int = 16000
    blocksize: int = Field(default=640, ge=320, le=16000)
    channels: int = 1
    aec_filter: bool = True
    dtype_str: Literal['float32', 'int16', 'float64'] = 'float32'

    @field_validator('blocksize')  # noqa
    @classmethod
    def round_to_160(cls, v: int) -> int:
        """Округляет до ближайшего кратного 160."""
        result = 160 * round(v / 160)
        return max(result, 160)

    @property
    def dtype(self):
        return getattr(np, self.dtype_str)


class VadRough(BaseModel):
    sensitivity: int = Field(default=50, ge=0, le=100)  # 0..100 → порог RMS
    zrc: int = Field(default=60, ge=0, le=100)  # 0..100 → ширина ZCR коридора
    burst_filter: int = Field(default=80, ge=0, le=100)  # 0..100 → фильтр резких звуков
    silence_time: float = Field(default=0.8, ge=0.0, le=60.0)  # максимальная пауза (пробелы между словами)

    @property
    def rms_thresh(self) -> float:
        """0 → ~0.05, 100 → ~0.0 (не фильтрует тишину)"""
        return (100 - self.sensitivity) / 100 * 0.05

    @property
    def zcr_bounds(self) -> tuple[float, float]:
        """
        0 → (0.0, 1.0) — пропускаем всё
        100 → узкий речевой коридор вокруг ~0.15
        """
        center = 0.15  # типичный ZCR речи при 16 кГц
        half_width = (100 - self.zrc) / 100 * 0.5
        half_width = max(half_width, 0.02)  # не сужаем до нуля
        return max(0.0, center - half_width), min(1.0, center + half_width)

    @property
    def crest_max(self) -> float:
        """0 → 20 (пропускаем всё), 100 → 5 (жёстко режем хлопки)"""
        return 20.0 - (self.burst_filter / 100) * 15.0


class WhisperVad(BaseModel):
    threshold: float = 0.5
    min_speech_duration_ms: int = 250
    min_silence_duration_ms: int = 500
    speech_pad_ms: int = 400


class Stt(BaseModel):
    pre_buffer_max_len: int = 30
    whisper_model: str = 'medium'
    whisper_translate_eng: bool = False
    whisper_vad: WhisperVad
    vosk_model: str = 'vosk_engine-model-small-ru-0.22'
    vosk_real_time_render: bool = True


class Settings(BaseModel):
    stt: Stt
    audio_input: AudioInput
    vad_rough: VadRough


# значения требующие перезагрузки
reboot_fileds = [
    # audioinput
    "audio_input.samplerate",
    "audio_input.blocksize",
    "audio_input.channels",
    "audio_input.dtype_str",
    # VadRough
    "vad_rough.silence_time",
    # Stt
    "stt.pre_buffer_max_len",
    "stt.whisper_model",
    "stt.vosk_model",
]

table_change_events = []

settings = Settings(audio_input=AudioInput(), vad_rough=VadRough(), stt=Stt(whisper_vad=WhisperVad()))

#
if __name__ == '__main__':
    # print(settings.stt.whisper_vad.model_dump())
    print(settings.audio_input.blocksize)
