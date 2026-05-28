import sys
import subprocess
import platform
from pathlib import Path
from config.moduls import INSTALL_DEPENDS

is_windows = platform.system().lower() == 'windows'
separator = ";" if is_windows else ":"
ext = ".dll" if is_windows else ".so"
python_lib = f"Lib\\site-packages" if is_windows else f"lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages"
python_lib = Path('.venv') / python_lib


def build(name: str = 'component'):
    add_data = INSTALL_DEPENDS['add_data']
    add_binary = INSTALL_DEPENDS['add_binary']
    exclude_modules = INSTALL_DEPENDS['excluded']

    print('[green]Сборка приложения[/green]')

    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--onefile',
        '--console',
        '--name', name,
        '--icon=icon.ico',
        '--exclude-module', Path(__file__).stem,
    ]

    # исключаемые модули
    if exclude_modules is not None:
        for e in exclude_modules:
            cmd.extend(['--exclude-module', e])

    # сборка бинарных файлов (.dll, библиотек)
    if add_binary is not None:
        for binary in add_binary:
            binary_path = python_lib / binary
            # сборка .dll или .so файлов
            for f in binary_path.iterdir():
                if str(f).endswith(ext):
                    cmd.extend(['--add-binary', f'{f}{separator}{binary}'])

    # сборка data
    if add_data is not None:
        for d in add_data:
            data_path = python_lib / d
            cmd.extend(['--add-data', f'{str(data_path)}{separator}{d}'])

    cmd.append('cli.py')

    distributive_path = Path(__file__).parent / 'dist'
    subprocess.run(cmd, shell=is_windows)
    print(f'[green]Приложение собрано. {distributive_path.parent}[/green]')


if __name__ == '__main__':
    # теперь дополнительные материалы подхватываются из конфигурации. Лишнее больше не ставится.
    build(name='STT')
