import sys
import subprocess
import platform
from pathlib import Path

is_windows = platform.system().lower() == 'windows'
separator = ";" if is_windows else ":"
ext = ".dll" if is_windows else ".so"
python_lib = f"Lib\\site-packages" if is_windows else f"lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages"
python_lib = Path('.venv') / python_lib


def build(
        name: str = 'component',
        add_binary: list[str] | None = None,
        add_data: list[Path] | None = None
):
    print('[green]Сборка приложения[/green]')

    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--onefile',
        '--console',
        '--name', name,
        '--exclude-module', Path(__file__).stem,
        '--icon=icon.ico',
    ]

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
    from app.stt import STT_REGISTRY

    # Подхватывание пакетов для сборки в .exe (например .dll для whisper)
    # позволяет сделать например облегченную сборку которая работает только с whisper или c vosk (вкл/выкл модуль можно в app.stt.__init__)
    add_binary_app = []
    add_data_app = []
    for engine in STT_REGISTRY:
        binary_app = STT_REGISTRY[engine]['add_binary']
        data_app = STT_REGISTRY[engine]['add_data']
        if binary_app:
            add_binary_app.append(*binary_app)
        if data_app:
            add_data_app.append(*data_app)

    build(
        name='stt',
        add_binary=add_binary_app,
        add_data=add_data_app,
    )
