from typing import Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict
import numpy as np

__all__ = ['settings', 'table_change_events', 'reboot_fileds', 'Settings']


class AudioInput(BaseModel):
    model_config = ConfigDict(
        validate_default=True,
        title='Настройки аудиовхода — запись с микрофона'
    )
    samplerate: int = Field(
        default=16000,
        ge=1024,
        le=192000,
        description='Частота дискретизации в Гц. 16000 — стандарт для речи'
    )
    blocksize: int = Field(
        default=640,
        ge=320,
        le=16000,
        description='Размер аудиоблока в сэмплах. Кратен 160 (если указано не кратное значение то выполняется автоподгонка). Меньше — быстрее реакция, но выше нагрузка'
    )
    channels: int = Field(
        default=1,
        ge=1,
        description='Количество каналов. 1 — моно (достаточно для речи). Не рекомендуется менять.'
    )
    aec_filter: bool = Field(
        default=True,
        description='Эхоподавление: AEC вычитает звук колонок из микрофона, чтобы ассистент не слышал сам себя'
    )
    dtype_str: Literal['float32', 'int16', 'float64'] = Field(
        default='float32',
        description='Тип данных аудио. float32 — стандарт, менять не рекомендуется'
    )

    @field_validator('blocksize')  # noqa
    @classmethod
    def round_to_160(cls, v: int) -> int:
        """Округляет до ближайшего кратного 160."""
        result = 160 * round(v / 160)
        return max(result, 160)

    @property
    def dtype(self):
        return getattr(np, self.dtype_str)


class WhisperVad(BaseModel):
    model_config = ConfigDict(title='Whisper: встроенный VAD (детектор речи)')
    threshold: float = Field(
        default=0.5,
        ge=0,
        le=1,
        description='Порог чувствительности: 0 — ловит всё, 1 — почти ничего. 0.5 — баланс'
    )
    min_speech_duration_ms: int = Field(
        default=250,
        ge=50,
        le=1000,
        description='Минимальная длительность речи в мс. Короче — не считается речью'
    )
    min_silence_duration_ms: int = Field(
        default=500,
        ge=50,
        le=1000,
        description='Минимальная пауза в мс, после которой фраза считается законченной'
    )
    speech_pad_ms: int = Field(
        default=400,
        ge=50,
        le=1000,
        description='Добавить тишины до и после речи в мс, чтобы не обрезало начало/конец фразы'
    )


class WhisperTranscribe(BaseModel):
    model_config = ConfigDict(title='Whisper : настройки транскрибации (распознавания текста).')

    language: Literal['ru', 'en'] | None = Field(
        default=None,
        description='Язык. None — автоопределение (медленнее, но универсально)'
    )
    beam_size: int = Field(
        default=1,
        ge=1,
        le=10,
        description='Ширина луча поиска. 1 — быстро, >1 — точнее, но медленно'
    )
    best_of: int = Field(
        default=1,
        ge=1,
        le=5,
        description='Число прогонов beam search. >1 не даст эффекта при temperature=(0,0)'
    )
    patience: float = Field(
        default=0.5,
        ge=0,
        le=1,
        description='Терпение beam search. 0.5 — баланс скорости и точности'
    )
    compression_ratio_threshold: float = Field(
        default=2.4,
        ge=0,
        le=5,
        description='Порог подавления галлюцинаций. Ниже — агрессивнее фильтр'
    )
    temperature: tuple[float, float] = Field(
        default=(0, 0),
        description='Креативность модели. (0,0) — детерминизм, без случайностей'
    )
    without_timestamps: bool = Field(
        default=True,
        description='Без временных меток — быстрее'
    )
    vad_filter: bool = Field(
        default=True,
        description='Встроенный VAD Whisper. Настройки — в WhisperVad'
    )


class WhisperOther(BaseModel):
    model_config = ConfigDict(title='Whisper : прочие настройки.')
    whisper_pre_buffer_max_len: int = Field(
        default=30,
        ge=10,
        le=1000,
        description='Длина предбуфера в чанках. Хранит аудио до начала речи, чтобы не обрезало первые слова'
    )
    whisper_translate_eng: bool = Field(
        default=False,
        description='Переводить на английский. True — распознать и перевести, False — просто распознать'
    )
    whisper_rms_threshold: float = Field(
        default=0.003,
        ge=0,
        le=0.1,
        description='Порог громкости для Whisper. Ниже — считается тишиной. 0.003 — стандарт'
    )
    whisper_silence_time: float = Field(
        default=0.8,
        ge=0,
        le=10,
        description='Пауза в секундах, после которой Whisper считает фразу законченной'
    )


class VoskOther(BaseModel):
    vosk_rms_threshold: float = Field(
        default=0.003,
        ge=0,
        le=0.1,
        description='Порог громкости для Vosk. Ниже — считается тишиной. 0.003 — стандарт'
    )
    vosk_real_time_render: bool = Field(
        default=True,
        description='Показывать частичный результат распознавания в реальном времени'
    )
    vosk_original_logs_print_console: bool = Field(
        default=False,
        description='Показывать оригинальные логи Vosk в консоли (для отладки). По умолчанию скрыты'
    )


class Stt(BaseModel):
    model_config = ConfigDict(title='Общие настройки распознавания речи')
    whisper_vad: WhisperVad = Field(description='Настройки встроенного VAD Whisper (детектор речи внутри модели)')
    whisper_transcribe: WhisperTranscribe = Field(description='Настройки транскрибации (распознавания текста) Whisper')
    whisperOther: WhisperOther = Field(description='Прочие настройки whisper')
    voskOther: VoskOther = Field(description='Прочие настройки vosk')


class Settings(BaseModel):
    stt: Stt = Field(description='Настройки распознавателя речи.')
    audio_input: AudioInput = Field(description='Настройки аудиовхода - записи звука с микрофона.')
    messages_print_console: bool = Field(default=False, description='Печатать шину сообщений прямо в терминал/')


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
    "stt.whisper_pre_buffer_max_len",
]

table_change_events = []

settings = Settings(
    audio_input=AudioInput(),
    stt=Stt(
        whisper_vad=WhisperVad(),
        whisper_transcribe=WhisperTranscribe(),
        whisperOther=WhisperOther(),
        voskOther=VoskOther(),
    )
)

#
if __name__ == '__main__':
    # print(settings.stt.whisper_vad.model_dump())
    # print(settings.audio_input.blocksize)
    print(Settings.model_json_schema())
