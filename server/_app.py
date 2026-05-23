from fastapi import FastAPI, status
from app import message_bus
from app.main import app as component
from utils.message_bus_manager.message_bus_manager import Message
from app.routers import router
from app import settings_manager, Settings
from server._server import Server

app = FastAPI()
app.include_router(router)
server = Server(application=app)

__all__ = ['server']  # объект для управления сервером


@app.get('/')
@app.get('/status/')
def component_status():
    """
    Основная информация о состоянии компонента
    """
    return {
        'msg': 'Состояние компонента',
        'is_running': component.is_running,
    }


@app.get(
    '/start/',
    summary='Запуск приложения в режиме сервера',
)
def component_start(engine: str, model: str):
    component.start(engine=engine, model=model, print_result_console=True)
    return {
        'msg': f'Компонент `{component.name}` запущен.',
    }


@app.get(
    '/stop/',
    summary='Остановка приложения в режиме сервера',
)
def component_stop():
    component.stop()
    return {
        'msg': f'Компонент `{component.name}` остановлен.',
    }


@app.get(
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


@app.get(
    '/settings/',
    response_model=dict[str, Settings],
    status_code=status.HTTP_200_OK,
    summary='Информация о текущих настройках',
)
def settings_get():
    return {'settings': settings_manager.settings}


@app.post(
    '/settings-edit/',
    response_model=dict[str, Settings],
    status_code=status.HTTP_200_OK,
    summary='Изменение настроек',
)
def settings_update(new_settings: Settings):
    settings_manager.apply_new_settings(settings=new_settings)
    return {'settings': settings_manager.settings}


@app.delete(
    '/settings-edit/',
    response_model=dict[str, Settings],
    status_code=status.HTTP_200_OK,
    summary='Сбросить все настройки к заводским',
)
def settings_reset():
    settings_manager.reset()
    return {'settings': settings_manager.settings}


@app.get(
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


if __name__ == '__main__':
    print(f'/shutdown/ для остановки сервера')
    server.start()
