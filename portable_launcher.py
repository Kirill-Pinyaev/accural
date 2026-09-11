import json
import os
import secrets
import socketserver
import string
import sys
import tempfile
import threading
import urllib.request
from pathlib import Path
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server


APP_NAME = "Начисление"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
CONFIG_NAME = "launcher.json"
DATA_DIR_NAME = "AccrualData"


def app_directory():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def load_or_create_config(data_dir):
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / CONFIG_NAME
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))

    alphabet = string.ascii_letters + string.digits
    config = {
        "username": "admin",
        "password": "".join(secrets.choice(alphabet) for _ in range(14)),
        "secret_key": secrets.token_urlsafe(48),
    }
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    os.replace(temporary, path)
    return config


def configure_django(data_dir, config):
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings_portable"
    os.environ["ACCRUAL_DATA_DIR"] = str(data_dir)
    os.environ["ACCRUAL_SECRET_KEY"] = config["secret_key"]


def prepare_database(config):
    import django
    from django.core.management import call_command

    django.setup()
    call_command("migrate", interactive=False, verbosity=0)

    from django.contrib.auth import get_user_model

    user_model = get_user_model()
    user, _ = user_model.objects.get_or_create(username=config["username"])
    user.is_active = True
    user.is_staff = True
    user.is_superuser = True
    if hasattr(user, "role"):
        user.role = user_model.Role.ADMIN
    user.set_password(config["password"])
    user.save()


class ThreadingWSGIServer(socketserver.ThreadingMixIn, WSGIServer):
    daemon_threads = True
    allow_reuse_address = True


class QuietRequestHandler(WSGIRequestHandler):
    def log_message(self, format, *args):  # noqa: A002
        return


class AppServer:
    def __init__(self, data_dir, config, host=DEFAULT_HOST, port=DEFAULT_PORT):
        self.data_dir = data_dir
        self.config = config
        self.host = host
        self.port = port
        self.httpd = None
        self.thread = None

    @property
    def url(self):
        return f"http://{self.host}:{self.port}"

    @property
    def running(self):
        return self.thread is not None and self.thread.is_alive()

    def start(self):
        if self.running:
            return
        configure_django(self.data_dir, self.config)
        prepare_database(self.config)

        from django.contrib.staticfiles.handlers import StaticFilesHandler
        from django.core.wsgi import get_wsgi_application

        application = StaticFilesHandler(get_wsgi_application())
        self.httpd = make_server(
            self.host,
            self.port,
            application,
            server_class=ThreadingWSGIServer,
            handler_class=QuietRequestHandler,
        )
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        if self.httpd is not None:
            self.httpd.shutdown()
            self.httpd.server_close()
        if self.thread is not None:
            self.thread.join(timeout=3)
        self.httpd = None
        self.thread = None


class LauncherWindow:
    def __init__(self, server):
        import tkinter as tk
        from tkinter import messagebox, ttk

        self.tk = tk
        self.ttk = ttk
        self.messagebox = messagebox
        self.server = server
        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.geometry("780x430")
        self.root.minsize(700, 390)
        self.root.resizable(True, True)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        style = ttk.Style(self.root)
        style.configure(".", font=("Segoe UI", 12))
        style.configure("TButton", padding=(14, 9))

        frame = ttk.Frame(self.root, padding=32)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)
        ttk.Label(frame, text=APP_NAME, font=("Segoe UI", 26, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 22)
        )

        ttk.Label(frame, text="Статус:").grid(row=1, column=0, sticky="w")
        self.status = ttk.Label(frame, text="Выключен", foreground="#a33")
        self.status.grid(row=1, column=1, columnspan=2, sticky="w")

        buttons = ttk.Frame(frame)
        buttons.grid(row=2, column=0, columnspan=3, sticky="w", pady=20)
        self.start_button = ttk.Button(
            buttons, text="Включить", command=self.start, width=14
        )
        self.start_button.grid(row=0, column=0, padx=(0, 8))
        self.stop_button = ttk.Button(
            buttons,
            text="Выключить",
            command=self.stop,
            state="disabled",
            width=14,
        )
        self.stop_button.grid(row=0, column=1)

        ttk.Label(
            frame,
            text="Скопируйте ссылку и вставьте её в адресную строку браузера:",
        ).grid(row=3, column=0, columnspan=3, sticky="w", pady=(4, 10))
        self._copy_row(frame, 4, "Ссылка", server.url)
        self._copy_row(frame, 5, "Логин", server.config["username"])
        self._copy_row(frame, 6, "Пароль", server.config["password"])

    def _copy_row(self, parent, row, label, value):
        self.ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=5)
        variable = self.tk.StringVar(value=value)
        entry = self.ttk.Entry(parent, textvariable=variable, state="readonly")
        entry.grid(row=row, column=1, padx=12, pady=7, sticky="ew")
        self.ttk.Button(
            parent, text="Копировать", command=lambda: self.copy(value)
        ).grid(row=row, column=2, pady=5)

    def copy(self, value):
        self.root.clipboard_clear()
        self.root.clipboard_append(value)
        self.root.update()

    def start(self):
        self.status.config(text="Запускается…", foreground="#875c00")
        self.start_button.config(state="disabled")
        threading.Thread(target=self._start_worker, daemon=True).start()

    def _start_worker(self):
        try:
            self.server.start()
        except Exception as error:
            self.root.after(0, self._start_failed, str(error))
        else:
            self.root.after(0, self._started)

    def _started(self):
        self.status.config(text="Включен", foreground="#18752c")
        self.stop_button.config(state="normal")

    def _start_failed(self, error):
        self.status.config(text="Ошибка запуска", foreground="#a33")
        self.start_button.config(state="normal")
        self.messagebox.showerror(APP_NAME, error)

    def stop(self):
        self.server.stop()
        self.status.config(text="Выключен", foreground="#a33")
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")

    def close(self):
        self.server.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def self_test():
    with tempfile.TemporaryDirectory(prefix="accrual-portable-") as temporary:
        data_dir = Path(temporary)
        config = load_or_create_config(data_dir)
        assert load_or_create_config(data_dir) == config
        server = AppServer(data_dir, config, port=8765)
        server.start()
        try:
            with urllib.request.urlopen(
                f"{server.url}/accounts/login/", timeout=15
            ) as response:
                assert response.status == 200
                assert "Вход" in response.read().decode("utf-8")
            with urllib.request.urlopen(
                f"{server.url}/static/payroll/auto_submit.js", timeout=15
            ) as response:
                assert response.status == 200

            from django.contrib.auth import get_user_model

            user = get_user_model().objects.get(username=config["username"])
            assert user.is_superuser
            assert user.check_password(config["password"])
            assert (data_dir / "accrual.sqlite3").exists()
        finally:
            server.stop()
            from django.db import connections

            connections.close_all()
    print("portable self-test: OK")


def main():
    if "--self-test" in sys.argv:
        self_test()
        return
    data_dir = app_directory() / DATA_DIR_NAME
    config = load_or_create_config(data_dir)
    LauncherWindow(AppServer(data_dir, config)).run()


if __name__ == "__main__":
    main()
