# Начисление

Веб-приложение-помощник бухгалтера для расчета начислений и учета выплат.

## Стек

- Python
- Django
- PostgreSQL
- openpyxl
- Docker Compose для локального и серверного запуска

## Быстрый старт через Docker

```bash
cp .env.example .env
docker compose up --build
```

В отдельном терминале:

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

Приложение будет доступно по адресу:

```text
http://localhost:8000
```

## Портативная версия для Windows

Готовый файл: `dist/AccrualPortable.exe`. На другом компьютере с Windows 10/11
x64 достаточно скопировать только этот файл в обычную доступную для записи
папку, например на рабочий стол. Python, Docker, PostgreSQL и установка не
нужны.

1. Запустить `AccrualPortable.exe`.
2. Нажать «Включить» и дождаться статуса «Включен».
3. Скопировать показанную ссылку в адресную строку браузера.
4. Скопировать показанные логин и пароль на странице входа.

При первом запуске рядом с EXE создаётся папка `AccrualData` с чистой базой
SQLite и постоянными учётными данными. Код, шаблоны и статика находятся внутри
EXE, но изменяемая база не может храниться внутри неизменяемого исполняемого
файла. Для резервной копии достаточно скопировать всю папку `AccrualData` при
выключенном сервисе. Закрытие окна лаунчера также выключает сервис.

Сборка на Linux через Wine:

```bash
./build_windows_exe.sh
wine dist/AccrualPortable.exe --self-test
```

## Локальный запуск без Docker

Нужен запущенный PostgreSQL.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
POSTGRES_HOST=localhost .venv/bin/python manage.py migrate
POSTGRES_HOST=localhost .venv/bin/python manage.py createsuperuser
POSTGRES_HOST=localhost .venv/bin/python manage.py runserver
```

## Проверка проекта

В Docker с PostgreSQL:

```bash
docker compose exec web python manage.py test
docker compose exec web python manage.py check
docker compose exec web python manage.py makemigrations --check --dry-run
```

Без Docker, на временной SQLite-базе:

```bash
DJANGO_SETTINGS_MODULE=config.settings_test .venv/bin/python manage.py test
DJANGO_SETTINGS_MODULE=config.settings_test .venv/bin/python manage.py check
DJANGO_SETTINGS_MODULE=config.settings_test .venv/bin/python manage.py makemigrations --check --dry-run
```

## Импорт табеля

Загружается широкий файл `.xlsx`. Система просматривает первые 20 строк всех
листов и ищет заголовки `Сотрудник`, `Дни`, `Часы`; порядок и номера колонок не
важны. `Дни` и `Часы` используются как итоговые значения. Колонки дат
(`01.06`, `01.06 Пн` или Excel-дата) сохраняются только как расшифровка.

Дополнительно поддерживаются `Должность`, `Организация`, `Проект`, заголовок,
начинающийся со `Статус`, `Ставка ₽/час` и `Ставка ₽/день`. Перед применением
администратор обязательно проверяет предпросмотр; импорт выполняется одной
транзакцией.

В фильтре начислений должности берутся только из поля `Должность` строк текущего
периода и режима отображения: должности нулевых сотрудников появляются при
включении нулевых строк. После редактирования карточки список обновляется.
Нулевые строки можно показать вместе с остальными либо отдельно. В форме
выплаты сотрудника можно выбрать из списка или найти, начав вводить ФИО.

## Документы

- [ТЗ_Система_Начисление_MVP.md](ТЗ_Система_Начисление_MVP.md)
- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)
