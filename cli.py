import os
import subprocess
import threading
import typer
from rich import print
from rich.prompt import Prompt
import platform
from app.main import app as component
from app import settings_manager

COMPONENT = 'CLI'
SUBCOMPONENT_NAME = 'CLI'

app = typer.Typer(no_args_is_help=True)
stop_polling_message_bus = threading.Event()
stop_stt_component = threading.Event()
is_windows = platform.system() == "Windows"


@app.callback()
def main():
    """описание модуля"""


@app.command()
def run():
    """
    Запуск приложения в интерактивном режиме [yellow]run[/yellow]
    """

    from cli_addon import interactive
    interactive()


@app.command()
def settings_view():
    """Просмотреть текущие настройки [yellow]settings_view[/yellow]"""
    print(settings_manager.settings)


@app.command()
def settings_edit():
    """
    Открыть настройки json, для редактирования параметров в приложении по умолчанию [yellow]settings_edit[/yellow]
    """
    if is_windows:
        os.startfile(settings_manager.json_file_path)
        return

    try:
        subprocess.call(["nano", settings_manager.json_file_path])
    except Exception:  # noqa
        subprocess.call(['xdg-open', settings_manager.json_file_path])


@app.command()
def settings_reset():
    """Сброс параметров к заводским настройкам [yellow]settings-reset[/yellow]"""
    user_input = Prompt.ask('[yellow]Вы точно хотите сбросить настройки параметров к исходным(Y/n)?[/yellow]')
    if user_input != 'Y':
        return
    settings_manager.reset()


@app.command()
def run_server(
        port: int = typer.Option(8000, '--port', '-p')
):
    """
    Запуск сервера для работы с api приложения. [yellow]run-server[/yellow]
    Опции:
        --port или -p номер порта на котором будет запущено приложение
    """
    from server import server
    url = f'http://localhost:{port}/docs/'
    print(f'🟢 Сервер запущен url: `{url}`')

    try:
        server.start(port=port)
    except KeyboardInterrupt:
        component.stop()
        server.stop()
    finally:
        component.stop()
        server.stop()
        print(f'🔴 Сервер завершил работу. url: `{url}`')


if __name__ == '__main__':
    app()
