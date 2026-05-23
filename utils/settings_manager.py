import threading
from pathlib import Path
from typing import TypeVar, Generic, Type
from pydantic import BaseModel
import atexit

T = TypeVar('T', bound=BaseModel)

__all__ = ['get_settings_manager']


class SettingsManager(Generic[T]):
    def __init__(
            self,
            json_file_path: Path,
            settings_model: T,
    ):
        # инициализация объектов
        self.json_file_path = json_file_path
        self.settings: T | None = None  # настройки которые будут выгружены из файла
        self._default_settings = settings_model
        self._model_class: Type[T] = type(settings_model)
        atexit.register(self.stop)
        # чтение настроек
        self.read()
        self._exit_observer = threading.Event()

    def read(self) -> None:
        # Игнорируем временный файл, если он "завис"
        # (это бывает редко, но это дешёвая страховка)
        tmp_path = self.json_file_path.with_suffix('.tmp')
        if tmp_path.exists():
            tmp_path.unlink()  # Удаляем его без лишнего шума

        # Дальше всё как обычно
        if not self.json_file_path.exists():
            self.reset()
            return

        try:
            with open(file=self.json_file_path, mode='r', encoding='utf-8') as f:
                settings = f.read()
                self.settings = self._model_class.model_validate_json(settings)
        except Exception:  # noqa
            self.reset()

    def save(self) -> None:
        """Сохраняет настройки атомарно через временный файл."""
        settings = self.settings if self.settings is not None else self._default_settings

        # Создаём временный файл в той же папке
        tmp_path = self.json_file_path.with_suffix('.tmp')

        # Пишем настройки во временный файл
        with open(file=tmp_path, mode='w', encoding='utf-8') as f:
            f.write(settings.model_dump_json(ensure_ascii=True, indent=2))
            f.flush()  # Принудительно сбрасываем на диск

        # Атомарная замена: tmp мгновенно становится основным файлом
        tmp_path.replace(self.json_file_path)

    def apply_new_settings(self, settings: T) -> None:
        try:
            # обновление настроек с проверкой
            new_settings = self._model_class.model_validate(settings)
            self.settings = new_settings
        except Exception as err:
            raise f"Ошибка изменения настроек: {err}"
        self.save()

    def reset(self) -> None:
        """сброс и сохранение настроек"""
        self.settings = None
        self.save()
        self.read()  # прочитать записанные настройки

    def stop(self):
        """Остановка обсервера"""
        if hasattr(self, '_exit_observer'):
            self._exit_observer.set()


def get_settings_manager(
        json_file_path: Path,
        settings_model: T,
) -> SettingsManager[T]:
    """
    :param json_file_path: путь и имя файла сохранения настроек, например settings.json
    :param settings_model: класс с настройками на базе pydantic схемы
    :return: класс управленец настройками. Настройки в приложениях можно снимать через ключ settings
    """
    return SettingsManager[T](
        json_file_path=json_file_path,
        settings_model=settings_model,
    )


if __name__ == '__main__':
    # Пример использования класса
    # вложенная модель с настройками
    class AudioInputSettings(BaseModel):
        samplerate: int = 16000
        blocksize: int = 1024


    # главная модель с настройками
    class SttSettings(BaseModel):
        stt_model: str = 'whisper_engine'
        audio_settings: AudioInputSettings


    # в schemas модуля (файле где объявлены схемы) создать экземпляр настроек с всеми вложенными моделями
    demo_settings = SttSettings(audio_settings=AudioInputSettings())

    # получение менеджера с настройками
    settings_manager = get_settings_manager(
        json_file_path=Path('settings.json'),
        settings_model=demo_settings,
    )
    print(settings_manager.settings)
    try:
        input(f'enter чтобы выйти')
    except KeyboardInterrupt:
        settings_manager.stop()
