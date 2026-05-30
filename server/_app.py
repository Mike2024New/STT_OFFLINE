from datetime import datetime
from fastapi import FastAPI, status, Request, APIRouter
from app import message_bus
from app.main import app as component
from app import settings_manager, Settings
from app.routers import router
from utils.message_bus_manager.message_bus_manager import Message
from server._server import Server
from config.moduls import STT_INFO

app = FastAPI()
app.include_router(router)
server = Server(application=app)

__all__ = ['server']  # объект для управления сервером

info_routers = APIRouter(tags=['info'])
settings_routers = APIRouter(tags=['settings'])
manager_routers = APIRouter(tags=['manager'])


@info_routers.get('/')
@info_routers.get('/health/')
@info_routers.get('/status/')
def component_status():
    """
    Проверка состояния сервера. Проверка запущен ли компонент сервера (component_is_run).
    """
    return {
        'msg': 'Основная информация о сервере.',
        'component_is_run': component.is_running,
        'timestamp': datetime.now().isoformat(),
    }


@info_routers.get('/info/')
def info(request: Request):
    info_data = {}
    port = request.url.port
    for engine in STT_INFO:
        info_data[engine] = {}
        for model in STT_INFO[engine]:
            info_data[engine][model] = {
                'urls': [],
            }
            url = f'http://localhost:{port}/start/?engine={engine}&model={model}'
            info_data[engine][model]['urls'].append(url)

    return {'info': info_data}


@info_routers.get(
    '/messages/',
    response_model=dict[str, list[Message] | str],
    status_code=status.HTTP_200_OK,
    summary='Получение данных из шины сообщений',
)
def get_messages_all():
    messages = message_bus.get_all()
    return {
        'msg': 'Накопленные сообщения из шины сообщений',
        'messages': [m.model_dump() for m in messages],
    }


@manager_routers.get(
    '/start/',
    summary='Информацию о движках и моделях можно посмотреть в `/info/`, там же можно получить url для запуска приложения',
)
def component_start(engine: str, model: str):
    component.stop()  # идемпотентно прервать работающую модель
    component.start(engine=engine, model=model, print_result_console=True)
    return {
        'msg': f'Компонент `{component.name}` запущен.',
    }


@manager_routers.get(
    '/stop/',
    summary='Остановка приложения в режиме сервера',
)
def component_stop():
    component.stop()
    return {
        'msg': f'Компонент `{component.name}` остановлен.',
    }


@manager_routers.get(
    '/shutdown/',
    response_model=dict[str, str],
    status_code=status.HTTP_200_OK,
    summary='Остановка сервера (и приложения если оно запущено)'
)
def shutdown():
    """Остановка сервера"""
    # сперва остановить компонент если он запущен
    if component.is_running:
        component.stop()
    # остановить сервер
    server.stop()
    return {
        'msg': 'сервер остановлен.'
    }


@settings_routers.get('/settings-schema/')
def settings_schema() -> dict:
    return Settings.model_json_schema()


@settings_routers.get(
    '/settings/',
    response_model=dict[str, Settings],
    status_code=status.HTTP_200_OK,
    summary='Информация о текущих настройках',
)
def settings_get():
    return {'settings': settings_manager.settings}


@settings_routers.post(
    '/settings-edit/',
    response_model=dict[str, Settings],
    status_code=status.HTTP_200_OK,
    summary='Изменение настроек',
)
def settings_update(new_settings: Settings):
    settings_manager.apply_new_settings(settings=new_settings)
    return {'settings': settings_manager.settings}


@settings_routers.delete(
    '/settings-edit/',
    response_model=dict[str, Settings],
    status_code=status.HTTP_200_OK,
    summary='Сбросить все настройки к заводским',
)
def settings_reset():
    settings_manager.reset()
    return {'settings': settings_manager.settings}


# добавление роутеров (разделено для удобного отображения в swagger ui)
app.include_router(info_routers)
app.include_router(settings_routers)
app.include_router(manager_routers)

if __name__ == '__main__':
    print(f'/shutdown/ для остановки сервера')
    server.start()
