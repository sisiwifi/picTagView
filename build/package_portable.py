from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD_DIR = REPO_ROOT / "build"
FRONTEND_DIR = REPO_ROOT / "frontend"
BACKEND_DIR = REPO_ROOT / "backend"
INITIAL_TAG_EXPORT = BUILD_DIR / "tags_export.json"
CURRENT_ENV_DIR = Path(sys.prefix)
CURRENT_BASE_PYTHON_DIR = Path(sys.base_prefix)
CURRENT_SITE_PACKAGES_DIR = CURRENT_ENV_DIR / "Lib" / "site-packages"
BASE_RUNTIME_DIRS = ("DLLs", "Lib", "libs")
BASE_RUNTIME_FILES = (
    "python.exe",
    "pythonw.exe",
    "python3.dll",
    f"python{sys.version_info.major}{sys.version_info.minor}.dll",
    "vcruntime140.dll",
    "vcruntime140_1.dll",
)
RUNTIME_IMPORT_PROBE = (
    "import cv2, fastapi, numpy, PIL, sqlmodel, uvicorn, xxhash;"
    "print('runtime-ready')"
)
DEFAULT_BACKEND_PORT = 8000


def run(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    subprocess.run(command, cwd=str(cwd), check=True, env=env)


def log(message: str) -> None:
    print(f"[package] {message}")


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def ensure_empty_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def create_staging_run_dir(staging_base_dir: Path) -> Path:
    staging_base_dir.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="portable_staging_", dir=staging_base_dir))


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\r\n")


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def build_frontend() -> None:
    npm_command = shutil.which("npm.cmd") or shutil.which("npm")
    if not npm_command:
        raise RuntimeError("npm was not found. Install Node.js and ensure npm is available in PATH.")
    log("Building frontend dist...")
    run([npm_command, "run", "build"], cwd=FRONTEND_DIR)


def build_portable_runtime_from_current_environment(runtime_target: Path) -> None:
    if not (CURRENT_BASE_PYTHON_DIR / "python.exe").is_file():
        raise FileNotFoundError(f"Base Python executable not found: {CURRENT_BASE_PYTHON_DIR / 'python.exe'}")
    if not CURRENT_SITE_PACKAGES_DIR.is_dir():
        raise FileNotFoundError(f"Current site-packages directory not found: {CURRENT_SITE_PACKAGES_DIR}")

    runtime_target.mkdir(parents=True, exist_ok=True)

    log(f"Copying Python runtime files from {CURRENT_BASE_PYTHON_DIR}...")
    for file_name in BASE_RUNTIME_FILES:
        source_file = CURRENT_BASE_PYTHON_DIR / file_name
        if source_file.is_file():
            copy_file(source_file, runtime_target / file_name)

    for dir_name in BASE_RUNTIME_DIRS:
        source_dir = CURRENT_BASE_PYTHON_DIR / dir_name
        if source_dir.is_dir():
            copy_tree(source_dir, runtime_target / dir_name)

    target_site_packages = runtime_target / "Lib" / "site-packages"
    if target_site_packages.exists():
        shutil.rmtree(target_site_packages)

    log(f"Copying project dependencies from {CURRENT_SITE_PACKAGES_DIR}...")
    copy_tree(CURRENT_SITE_PACKAGES_DIR, target_site_packages)


def validate_runtime(runtime_target: Path) -> None:
    runtime_python = runtime_target / "python.exe"
    if not runtime_python.is_file():
        raise FileNotFoundError(f"Portable runtime executable not found: {runtime_python}")

    env = dict(os.environ)
    env["PYTHONHOME"] = str(runtime_target)
    env.pop("PYTHONPATH", None)
    log("Validating bundled Python runtime...")
    run([str(runtime_python), "-c", RUNTIME_IMPORT_PROBE], cwd=REPO_ROOT, env=env)


def copy_runtime_python(runtime_source: Path, runtime_target: Path) -> None:
    if not runtime_source.is_dir():
        raise FileNotFoundError(
            f"Portable Python runtime directory not found: {runtime_source}\n"
            "Provide an embeddable Python directory with python.exe and the stdlib files."
        )
    log(f"Copying provided portable runtime from {runtime_source}...")
    copy_tree(runtime_source, runtime_target)


def stage_package(staging_root: Path, runtime_source: Path | None) -> Path:
    package_root = staging_root / "picTagView-portable"
    ensure_empty_dir(package_root)

    if not INITIAL_TAG_EXPORT.is_file():
        raise FileNotFoundError(f"Initial tag export not found: {INITIAL_TAG_EXPORT}")

    log("Copying backend application...")
    copy_tree(BACKEND_DIR / "app", package_root / "backend" / "app")
    shutil.copy2(BACKEND_DIR / "requirements.txt", package_root / "backend" / "requirements.txt")
    copy_file(INITIAL_TAG_EXPORT, package_root / "tags_export.json")

    frontend_dist = FRONTEND_DIR / "dist"
    if not frontend_dist.is_dir():
        raise FileNotFoundError(f"Frontend build output not found: {frontend_dist}")
    log("Copying frontend dist...")
    copy_tree(frontend_dist, package_root / "frontend" / "dist")

    runtime_target = package_root / "runtime" / "python"
    if runtime_source is not None:
        copy_runtime_python(runtime_source, runtime_target)
    else:
        build_portable_runtime_from_current_environment(runtime_target)
    validate_runtime(runtime_target)

    write_text(
        package_root / "frontend" / "dist" / "runtime-config.js",
        "window.__PTV_API_BASE__ = window.location.origin;\n",
    )

    write_text(
        package_root / "config.json",
        json.dumps(
            {
                "backend_port": DEFAULT_BACKEND_PORT,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
    )

    write_text(
        package_root / "launcher.py",
            "from __future__ import annotations\r\n"
            "\r\n"
            "import ctypes\r\n"
            "import json\r\n"
            "import os\r\n"
            "import shutil\r\n"
            "import socket\r\n"
            "import subprocess\r\n"
            "import time\r\n"
            "from pathlib import Path\r\n"
            "\r\n"
            f"DEFAULT_BACKEND_PORT = {DEFAULT_BACKEND_PORT}\r\n"
            "ROOT = Path(__file__).resolve().parent\r\n"
            "CONFIG_FILE = ROOT / 'config.json'\r\n"
            "BROWSER_PROFILE_DIR = ROOT / '.browser-profile'\r\n"
            "BROWSER_CANDIDATES = [\r\n"
            "    ('msedge.exe', [\r\n"
            "        Path(os.environ.get('ProgramFiles(x86)', '')) / 'Microsoft' / 'Edge' / 'Application' / 'msedge.exe',\r\n"
            "        Path(os.environ.get('ProgramFiles', '')) / 'Microsoft' / 'Edge' / 'Application' / 'msedge.exe',\r\n"
            "    ]),\r\n"
            "    ('chrome.exe', [\r\n"
            "        Path(os.environ.get('ProgramFiles', '')) / 'Google' / 'Chrome' / 'Application' / 'chrome.exe',\r\n"
            "        Path(os.environ.get('ProgramFiles(x86)', '')) / 'Google' / 'Chrome' / 'Application' / 'chrome.exe',\r\n"
            "        Path(os.environ.get('LocalAppData', '')) / 'Google' / 'Chrome' / 'Application' / 'chrome.exe',\r\n"
            "    ]),\r\n"
            "]\r\n"
            "\r\n"
            "\r\n"
            "def show_message(message: str, title: str = 'picTagView') -> None:\r\n"
            "    try:\r\n"
            "        ctypes.windll.user32.MessageBoxW(None, message, title, 0x10)\r\n"
            "    except Exception:\r\n"
            "        pass\r\n"
            "\r\n"
            "\r\n"
            "def fail(message: str) -> int:\r\n"
            "    print(message)\r\n"
            "    show_message(message)\r\n"
            "    return 1\r\n"
            "\r\n"
            "\r\n"
            "def load_backend_port() -> int:\r\n"
            "    try:\r\n"
            "        payload = json.loads(CONFIG_FILE.read_text(encoding='utf-8'))\r\n"
            "    except FileNotFoundError:\r\n"
            "        return DEFAULT_BACKEND_PORT\r\n"
            "    except Exception as exc:\r\n"
            "        print(f'Failed to read config.json: {exc}')\r\n"
            "        return DEFAULT_BACKEND_PORT\r\n"
            "\r\n"
            "    try:\r\n"
            "        port = int(payload.get('backend_port', DEFAULT_BACKEND_PORT))\r\n"
            "    except Exception:\r\n"
            "        return DEFAULT_BACKEND_PORT\r\n"
            "\r\n"
            "    if 1 <= port <= 65535:\r\n"
            "        return port\r\n"
            "    return DEFAULT_BACKEND_PORT\r\n"
            "\r\n"
            "\r\n"
            "def find_browser_executable() -> Path | None:\r\n"
            "    for exe_name, candidate_paths in BROWSER_CANDIDATES:\r\n"
            "        resolved = shutil.which(exe_name)\r\n"
            "        if resolved:\r\n"
            "            return Path(resolved)\r\n"
            "        for candidate in candidate_paths:\r\n"
            "            if candidate and candidate.is_file():\r\n"
            "                return candidate\r\n"
            "    return None\r\n"
            "\r\n"
            "\r\n"
            "def wait_for_server(host: str, port: int, timeout_seconds: float = 15.0) -> bool:\r\n"
            "    deadline = time.time() + timeout_seconds\r\n"
            "    while time.time() < deadline:\r\n"
            "        try:\r\n"
            "            with socket.create_connection((host, port), timeout=1.0):\r\n"
            "                return True\r\n"
            "        except OSError:\r\n"
            "            time.sleep(0.25)\r\n"
            "    return False\r\n"
            "\r\n"
            "\r\n"
            "def is_port_listening(host: str, port: int) -> bool:\r\n"
            "    try:\r\n"
            "        with socket.create_connection((host, port), timeout=1.0):\r\n"
            "            return True\r\n"
            "    except OSError:\r\n"
            "        return False\r\n"
            "\r\n"
            "\r\n"
            "def stop_backend_process(process: subprocess.Popen[str]) -> None:\r\n"
            "    if process.poll() is not None:\r\n"
            "        return\r\n"
            "    try:\r\n"
            "        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], check=False, capture_output=True)\r\n"
            "        process.wait(timeout=10)\r\n"
            "    except Exception:\r\n"
            "        try:\r\n"
            "            process.kill()\r\n"
            "        except Exception:\r\n"
            "            pass\r\n"
            "\r\n"
            "\r\n"
            "def launch_managed_browser(url: str) -> subprocess.Popen[str]:\r\n"
            "    browser_exe = find_browser_executable()\r\n"
            "    if browser_exe is None:\r\n"
            "        raise RuntimeError('No supported browser was found. Install Microsoft Edge or Google Chrome.')\r\n"
            "\r\n"
            "    BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)\r\n"
            "    command = [\r\n"
            "        str(browser_exe),\r\n"
            "        f'--app={url}',\r\n"
            "        f'--user-data-dir={BROWSER_PROFILE_DIR}',\r\n"
            "        '--no-first-run',\r\n"
            "        '--no-default-browser-check',\r\n"
            "        '--window-size=1440,960',\r\n"
            "    ]\r\n"
            "    creationflags = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)\r\n"
            "    return subprocess.Popen(command, cwd=str(ROOT), creationflags=creationflags)\r\n"
            "\r\n"
            "\r\n"
            "def main() -> int:\r\n"
            "    python_home = ROOT / 'runtime' / 'python'\r\n"
            "    python_exe = python_home / 'python.exe'\r\n"
            "    backend_dir = ROOT / 'backend'\r\n"
            "    backend_entry = backend_dir / 'app' / 'main.py'\r\n"
            "    host = '127.0.0.1'\r\n"
            "    port = load_backend_port()\r\n"
            "    url = f'http://{host}:{port}/'\r\n"
            "\r\n"
            "    if not python_exe.is_file():\r\n"
            "        return fail(f'Portable Python runtime not found: {python_exe}')\r\n"
            "    if not backend_entry.is_file():\r\n"
            "        return fail(f'Backend entry not found: {backend_entry}')\r\n"
            "    if is_port_listening(host, port):\r\n"
            "        return fail(f'Configured backend port {port} is already in use. Change config.json or stop the existing service first.')\r\n"
            "\r\n"
            "    env = dict(os.environ)\r\n"
            "    env['PYTHONHOME'] = str(python_home)\r\n"
            "    env.pop('PYTHONPATH', None)\r\n"
            "\r\n"
            "    command = [\r\n"
            "        str(python_exe),\r\n"
            "        '-m',\r\n"
            "        'uvicorn',\r\n"
            "        'app.main:app',\r\n"
            "        '--host',\r\n"
            "        host,\r\n"
            "        '--port',\r\n"
            "        str(port),\r\n"
            "    ]\r\n"
            "\r\n"
            "    creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0) | getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)\r\n"
            "    startupinfo = None\r\n"
            "    if os.name == 'nt' and hasattr(subprocess, 'STARTUPINFO'):\r\n"
            "        startupinfo = subprocess.STARTUPINFO()\r\n"
            "        startupinfo.dwFlags |= getattr(subprocess, 'STARTF_USESHOWWINDOW', 0)\r\n"
            "        startupinfo.wShowWindow = 0\r\n"
            "    try:\r\n"
            "        backend_process = subprocess.Popen(command, cwd=str(backend_dir), env=env, creationflags=creationflags, startupinfo=startupinfo)\r\n"
            "    except Exception as exc:\r\n"
            "        return fail(f'Failed to start backend: {exc}')\r\n"
            "\r\n"
            "    if not wait_for_server(host, port):\r\n"
            "        show_message(f'Backend process started but port {port} did not respond within 15 seconds.')\r\n"
            "        stop_backend_process(backend_process)\r\n"
            "        return 1\r\n"
            "\r\n"
            "    try:\r\n"
            "        browser_process = launch_managed_browser(url)\r\n"
            "    except Exception as exc:\r\n"
            "        show_message(f'Failed to open managed UI window: {exc}')\r\n"
            "        stop_backend_process(backend_process)\r\n"
            "        return 1\r\n"
            "\r\n"
            "    try:\r\n"
            "        browser_process.wait()\r\n"
            "    finally:\r\n"
            "        stop_backend_process(backend_process)\r\n"
            "\r\n"
            "    return 0\r\n"
            "\r\n"
            "\r\n"
            "if __name__ == '__main__':\r\n"
            "    raise SystemExit(main())\r\n",
            )

    write_text(
        package_root / "start.vbs",
        "Dim shell, fso, root, pythonwPath, pythonPath, launcherPath, command\r\n"
        "Set shell = CreateObject(\"WScript.Shell\")\r\n"
        "Set fso = CreateObject(\"Scripting.FileSystemObject\")\r\n"
        "root = fso.GetParentFolderName(WScript.ScriptFullName)\r\n"
        "pythonwPath = root & \"\\runtime\\python\\pythonw.exe\"\r\n"
        "pythonPath = root & \"\\runtime\\python\\python.exe\"\r\n"
        "launcherPath = root & \"\\launcher.py\"\r\n"
        "If fso.FileExists(pythonwPath) Then\r\n"
        "  command = Chr(34) & pythonwPath & Chr(34) & \" \" & Chr(34) & launcherPath & Chr(34)\r\n"
        "Else\r\n"
        "  command = Chr(34) & pythonPath & Chr(34) & \" \" & Chr(34) & launcherPath & Chr(34)\r\n"
        "End If\r\n"
        "shell.Run command, 0, False\r\n",
    )

    write_text(
        package_root / "start.bat",
        "@echo off\r\n"
        "setlocal\r\n"
        "set \"ROOT=%~dp0\"\r\n"
        "if not exist \"%ROOT%start.vbs\" (\r\n"
        "  echo start.vbs not found.\r\n"
        "  pause\r\n"
        "  exit /b 1\r\n"
        ")\r\n"
        "wscript.exe \"%ROOT%start.vbs\"\r\n"
        "endlocal & exit /b 0\r\n",
    )

    write_text(
        package_root / "README.txt",
        "picTagView portable package\r\n"
        "\r\n"
        "使用方法\r\n"
        "本项目可识别文件名格式为yande.re和danbooru.donmai.us的文件。 \r\n"
        "1. 如需修改后端端口，请先编辑根目录的 config.json，把 backend_port 改成目标端口。\r\n"
        "2. 推荐双击 start.vbs 静默启动程序；如果需要兼容批处理入口，也可以双击 start.bat。\r\n"
        "3. 启动器会读取 config.json，并在后端启动成功后打开独立管理窗口。\r\n"
        "4. 这个便携包只包含程序本身，不包含 media、temp、cache、数据库等运行内容。\r\n"
        "5. 首次运行时，程序会自动创建 backend/data、backend/temp、backend/data/cache、media、trash 等运行目录。\r\n"
        "6. 如果关闭管理窗口，启动器会同步停止后端服务。\r\n"
        "7. 如果端口被占用，请关闭占用该端口的程序，或修改 config.json 后重新启动。\r\n"
        "8. 便携包根目录已附带 tags_export.json；如需导入初始标签，请按需通过程序里的标签导入功能手动导入。\r\n"
        "\r\n"
        "配置文件示例\r\n"
        "{\r\n"
        "  \"backend_port\": 8000\r\n"
        "}\r\n",
    )

    return package_root


def zip_package(package_root: Path, output_zip: Path) -> None:
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    if output_zip.exists():
        output_zip.unlink()

    log(f"Writing ZIP to {output_zip}...")
    with ZipFile(output_zip, "w", compression=ZIP_DEFLATED) as archive:
        for file_path in package_root.rglob("*"):
            if file_path.is_file():
                archive.write(file_path, file_path.relative_to(package_root.parent))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a portable ZIP package for picTagView.")
    parser.add_argument(
        "--runtime-python-dir",
        type=Path,
        help="Path to a portable Python runtime directory that contains python.exe.",
    )
    parser.add_argument(
        "--staging-dir",
        type=Path,
        default=BUILD_DIR / "portable_staging",
        help="Temporary staging directory used before zipping.",
    )
    parser.add_argument(
        "--output-zip",
        type=Path,
        default=BUILD_DIR / "picTagView-portable.zip",
        help="Final ZIP file path.",
    )
    args = parser.parse_args()

    try:
        build_frontend()
        staging_run_dir = create_staging_run_dir(args.staging_dir)
        package_root = stage_package(staging_run_dir, args.runtime_python_dir)
        zip_package(package_root, args.output_zip)
    except subprocess.CalledProcessError as exc:
        print(f"Packaging error: command failed with exit code {exc.returncode}")
        return exc.returncode or 1
    except Exception as exc:
        print(f"Packaging error: {exc}")
        return 1

    print(f"Portable package created at: {args.output_zip}")
    print(f"Staged package directory: {package_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())