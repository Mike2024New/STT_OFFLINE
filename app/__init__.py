import sys
from pathlib import Path
from utils.message_bus_manager.message_bus_manager import MessageBus, Message
from utils.settings_manager import get_settings_manager
from app.schemas import settings, table_change_events, reboot_fileds, Settings

__all__ = [
    'settings_manager', 'Settings',
    'message_bus', 'Message',
    'COMPONENT_NAME',
    'reboot_fileds', 'MODELS_DIR'
]

COMPONENT_NAME = 'STT'
SUBCOMPONENT_NAME = 'init'

# определение текущего метода исполнения (для exe, или из pycharm)
EXE_MODE = getattr(sys, 'frozen', False)

# поиск путей к папкам
JSON_SETTINGS_PATH = Path.cwd() / 'settings.json' if EXE_MODE else Path(__file__).parent.parent / 'settings.json'
MODELS_DIR = Path.cwd() / 'resources' / 'models' if EXE_MODE else Path(__file__).parent.parent / 'resources' / 'models'
MODELS_DIR.mkdir(exist_ok=True, parents=True)  # создание папки с моделями

message_bus = MessageBus(print_message=False)  # шина сообщений
settings_manager = get_settings_manager(
    settings_model=settings,
    json_file_path=JSON_SETTINGS_PATH,
)  # менеджер настроек
