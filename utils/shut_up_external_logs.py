import os


def shut_up_external_logs(func=None, *, enable: bool = True):
    """
    Универсальный декоратор для подавления логов сторонних C/C++ библиотек.

    Можно использовать с параметром или без:
        @shut_up_external_logs           # enable=True по умолчанию
        @shut_up_external_logs()         # то же самое
        @shut_up_external_logs(enable=False)  # отключить подавление

    Иногда оказывается 🤷‍♂️, что некоторые библиотеки пишут свои логи и засоряют консоль.
    Например Kaldi от vosk, этот декоратор делает 🧙‍♂️ и убирает лишние логи.
    """

    # Если вызвали без скобок, func будет передан напрямую
    if func is not None:
        return _decorator(func, enable)

    # Если вызвали с параметрами, возвращаем декоратор
    return lambda f: _decorator(f, enable)


def _decorator(func, enable: bool):
    def wrapper(*args, **kwargs):
        if not enable:
            return func(*args, **kwargs)

        # сохранение оригинальных дескрипторов
        old_stdout = os.dup(1)
        old_stderr = os.dup(2)

        # Открыть /dev/null
        devnull = os.open(os.devnull, os.O_WRONLY)

        # Подмена дескрипторов
        os.dup2(devnull, 1)
        os.dup2(devnull, 2)
        try:
            res = func(*args, **kwargs)
        finally:
            # Восстановить оригинальные дескрипторы
            os.dup2(old_stdout, 1)
            os.dup2(old_stderr, 2)
            os.close(devnull)
            os.close(old_stdout)
            os.close(old_stderr)

        return res

    return wrapper