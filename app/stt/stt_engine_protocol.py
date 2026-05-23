from typing import Protocol


class STTEngine(Protocol):
    def start(self) -> bool: ...

    def stop(self) -> bool: ...
