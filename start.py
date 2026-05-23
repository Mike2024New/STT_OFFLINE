import sys
import subprocess

"""
Установка зависимостей
"""
try:
    print(f'Установка uv')
    cmd = [sys.executable, '-m', 'pip', 'install', 'uv']
    subprocess.run(cmd, capture_output=False)

    print(f'Установка зависимостей')
    cmd = ['uv', 'sync']
    subprocess.run(cmd, capture_output=False)
except Exception as err:
    print(
        f'Не удалось установить зависимости по причине {err}\n'
        f'Проверьте что у вас создано виртуальное окружение\n'
        f'За тем выполните `pip install uv` (если он не установлен в системе)\n'
        f'`uv sync` - установка зависимых библиотек'
    )
