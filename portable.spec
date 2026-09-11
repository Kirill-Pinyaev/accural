import os

from PyInstaller.utils.hooks import collect_submodules


os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings_portable"
os.environ["ACCRUAL_DATA_DIR"] = os.path.abspath("build/portable-data")
os.environ["ACCRUAL_SECRET_KEY"] = "build-only-secret"


hiddenimports = []
for package in ("config", "core", "payroll", "users"):
    hiddenimports += collect_submodules(package)

a = Analysis(
    ["portable_launcher.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("templates", "templates"),
        ("payroll/static", "payroll/static"),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["psycopg", "gunicorn"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="AccrualPortable",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
