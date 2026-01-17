import subprocess
import sys
import time
import os
import signal
import importlib.util
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BAILEYS_DIR = os.path.join(BASE_DIR, "baileys-server")
FASTAPI_DIR = os.path.join(BASE_DIR, "fastapi-server")

processes = []

# -----------------------------
# Python dependency management
# -----------------------------

REQUIRED_PY_PACKAGES = [
    "fastapi",
    "uvicorn",
    "requests",
    "psycopg2-binary",
    "python-dotenv",
]


def is_python_package_installed(pkg: str) -> bool:
    return importlib.util.find_spec(pkg) is not None


def ensure_python_packages():
    missing = [p for p in REQUIRED_PY_PACKAGES if not is_python_package_installed(p)]

    if not missing:
        print(" Python dependencies already installed")
        return

    print(f" Installing missing Python packages: {', '.join(missing)}")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", *missing]
    )


# -----------------------------
# Node / npm checks & install
# -----------------------------

def command_exists(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def ensure_node_installed():
    if command_exists("node") and command_exists("npm"):
        print(" Node.js and npm already installed")
        return

    print("[WARN] Node.js or npm not found")

    if sys.platform == "win32" and command_exists("winget"):
        print(" Installing Node.js LTS via winget...")
        subprocess.check_call(
            ["winget", "install", "-e", "--id", "OpenJS.NodeJS.LTS"]
        )
        print(" Please restart this script after Node.js installation")
        sys.exit(0)

    print("\n Automatic Node.js install not supported on this OS.")
    print(" Please install Node.js LTS manually:")
    print("   https://nodejs.org/")
    sys.exit(1)


def ensure_node_modules():
    node_modules = os.path.join(BAILEYS_DIR, "node_modules")

    if os.path.isdir(node_modules):
        print(" Node dependencies already installed")
        return

    print(" Installing Node dependencies (npm install)...")
    subprocess.check_call(
        ["npm", "install"],
        cwd=BAILEYS_DIR,
        shell=True
    )


# -----------------------------
# Process management
# -----------------------------

def start_process(cmd, cwd, name, env=None):
    print(f" Starting {name}...")
    return subprocess.Popen(
        cmd,
        cwd=cwd,
        shell=True,
        env=env,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        if sys.platform == "win32"
        else 0,
    )


def stop_all():
    for p in processes:
        try:
            if sys.platform == "win32":
                p.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                p.terminate()
        except Exception:
            pass


# -----------------------------
# Main
# -----------------------------


def main():
    try:
        print(" First-time environment check...\n")

        ensure_node_installed()
        ensure_python_packages()
        ensure_node_modules()

        try:
            from dotenv import load_dotenv  # type: ignore

            env_path = os.path.join(BASE_DIR, ".env")
            if os.path.isfile(env_path):
                load_dotenv(env_path)
                print(f" Loaded environment from {env_path}")
        except Exception:
            pass

        node_port = os.getenv("NODE_PORT", "3000")
        fastapi_host = os.getenv("FASTAPI_HOST", "127.0.0.1")
        fastapi_port = os.getenv("FASTAPI_PORT", "3002")

        print("\n Starting services...\n")
        print(f" Baileys on port {node_port}")
        print(f" FastAPI on {fastapi_host}:{fastapi_port}\n")

        env_node = os.environ.copy()
        env_node["NODE_PORT"] = node_port
        env_node["FASTAPI_HOST"] = fastapi_host
        env_node["FASTAPI_PORT"] = fastapi_port

        baileys = start_process(
            "npm start",
            BAILEYS_DIR,
            "Baileys WhatsApp Server",
            env=env_node,
        )
        processes.append(baileys)

        time.sleep(3)

        fastapi_cmd = (
            f'"{sys.executable}" -m uvicorn main:app '
            f'--host {fastapi_host} --port {fastapi_port} --reload'
        )

        fastapi = start_process(
            fastapi_cmd,
            FASTAPI_DIR,
            "FastAPI Server",
            env=os.environ.copy(),
        )
        processes.append(fastapi)

        print("\n All services started")
        print(" Press CTRL+C to stop everything\n")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n Shutting down services...")
        stop_all()
        sys.exit(0)


if __name__ == "__main__":
    main()
