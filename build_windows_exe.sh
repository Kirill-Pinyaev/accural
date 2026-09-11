#!/usr/bin/env bash
set -euo pipefail

installer="python-3.13.15-amd64.exe"
python_exe='C:\Python313\python.exe'

if [[ ! -f "$installer" ]]; then
  curl -fL "https://www.python.org/ftp/python/3.13.15/$installer" -o "$installer"
fi

if [[ ! -f /home/kot/.wine/drive_c/Python313/python.exe ]]; then
  wine "$installer" /quiet InstallAllUsers=0 TargetDir='C:\Python313' \
    Include_launcher=0 Include_test=0 Include_tcltk=1
fi

wine "$python_exe" -m pip install --disable-pip-version-check -r requirements-portable.txt
wine "$python_exe" -m PyInstaller --noconfirm --clean portable.spec

echo "Готово: dist/AccrualPortable.exe"
