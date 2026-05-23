from time import sleep
import threading
from app import message_bus
from app.main import app as component
from app.stt import STT_INFO
from rich import print

stop_polling_message_bus = threading.Event()
stop_stt_component = threading.Event()


def interactive():
    """
    Запуск приложения в интерактивном режиме [yellow]run[/yellow]
    """

    def help_info():
        print(
            f'[green]'
            f'Функции (введите это в консоль):\n'
            f'  [cyan]@info[/cyan] - просмотр доступных движков распознавания речи (выводит команды запуска).\n'
            f'  [cyan]@params[/cyan] - текущее состояние stt, включен ли, какой движок и модель используются.\n'
            f'  [cyan]@start <engine> <model>[/cyan] - запустить новый движок (см. список stt в `@info` ).\n'
            f'  [cyan]@stop[/cyan] - остановить текущий движок.\n'
            f'  [cyan]@exit[/cyan] - завершить работу приложения.\n'
            f'  [cyan]@help[/cyan] - получить справку о командах.\n'
            f'  [/green]'
        )

    def get_result_from_message_bus():
        """Получение результата из шины сообщений, работает в своем отдельном потоке"""
        for msg in message_bus.stream():
            if stop_stt_component.is_set():
                break
            if msg.result.get('text'):
                print(msg.result.get('text'))

    def start_app(engine_in: str, model_in: str):
        """Запуск движка stt и ожидание распознавания речи, работает в своем отдельном потоке"""
        nonlocal current_engine, current_model
        current_engine = engine_in
        current_model = model_in
        try:
            component.start(engine=engine_in, model=model_in, print_result_console=False)
            print(f'[green]Модуль запущен[/green]')
            threading.Thread(target=get_result_from_message_bus).start()
            while not stop_stt_component.is_set():
                sleep(0.1)
            component.stop()
            current_engine = None
            current_model = None
            print(f'[green]Модуль остановлен[/green]')
        except Exception as err:
            print(f'Модуль не запущен. Ошибка: {err}')

    current_engine = None
    current_model = None
    print(f'[green]Приложение запущено[/green]')
    help_info()
    print(f'[yellow]Выберите stt движок в @info, и запустите его вставив команду в терминал[/yellow]')

    while True:
        user_input = input()

        if user_input == '@params':
            print(
                f'[cyan]'
                f'Параметры:\n'
                f'  STT: {"[green]ON[/green]" if current_engine else "[red]OFF[/red]"}\n'
                f'  engine : [yellow]{current_engine}[/yellow]\n'
                f'  model : [yellow]{current_model}[/yellow]\n'
                f'[/cyan]'
            )

        elif user_input == '@help':
            help_info()

        elif user_input.startswith('@start'):
            """Запуск модели распознавания текста. Формат @start <engine> <model>"""
            engine, model = user_input.replace('@start', '').split()  # noqa
            # остановить предыдущий движок если он запущен
            stop_stt_component.set()
            sleep(0.2)  # лучше заменить на обратный статус остановки движка
            stop_stt_component.clear()
            current_engine = engine
            current_model = model
            threading.Thread(target=start_app, kwargs={"engine_in": engine, "model_in": model}).start()  # запуск stt


        elif user_input == '@stop':
            """Остановка записи микрофона"""
            stop_stt_component.set()

        elif user_input == '@info':
            """Выбор движков и моделей"""
            print(f'[cyan][bold]Доступные модели:[/bold][cyan]')
            for engine in STT_INFO:
                for model in STT_INFO[engine]:
                    print(f'[yellow]@start {engine} {model}[/yellow]')

        elif user_input == '@exit':
            """Полный выход из приложения"""
            stop_stt_component.set()
            break
