from typing import Protocol


class STTEngine(Protocol):
    speech_active: bool

    def start(self) -> bool: ...

    def stop(self) -> bool: ...
