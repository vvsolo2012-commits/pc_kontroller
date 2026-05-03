# PC Controller (Kivy + Python)

Простая утилита для управления ПК с телефона в одной Wi‑Fi сети:
- вкладка 1: выключение ПК;
- вкладка 2: управление громкостью;
- вкладка 3: тачпад (движение мыши и клики).

## Что в проекте

- `pc_server.py` — сервер на Windows ПК.
- `main.py` — приложение Kivy для телефона (3 вкладки).

## 1) Запуск сервера на ПК (Windows)

1. Установите Python 3.10+.
2. В папке проекта выполните:

```powershell
python pc_server.py --host 0.0.0.0 --port 8765 --token "my_secret_token"
```

3. Разрешите Python в Windows Firewall для локальной сети.
4. Узнайте IP вашего ПК (например, `192.168.0.10`).

## 2) Запуск Kivy приложения на телефоне

Для Android обычно используют Buildozer (сборка APK) или Pydroid.

Минимальные зависимости:

```bash
pip install kivy
```

После запуска приложения введите:
- URL сервера: `http://IP_ПК:8765`
- Token: тот же, что при запуске `pc_server.py`

## 3) Сборка APK под Android (Pixel 7 Pro)

В проект уже добавлен `buildozer.spec` с настройками:
- API 34 (подходит для Android 14),
- архитектура `arm64-v8a` (подходит для Pixel 7 Pro),
- разрешение `INTERNET`.

### Вариант A: через WSL2 (рекомендуется на Windows)

1. Установите WSL2 + Ubuntu.
2. В Ubuntu:

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv git zip unzip openjdk-17-jdk
pip3 install --user --upgrade cython buildozer
```

3. Перейдите в проект (если проект на диске `H:`):

```bash
cd /mnt/h/pckontroller
```

4. Запустите сборку:

```bash
~/.local/bin/buildozer android debug
```

5. Готовый APK будет в папке `bin/` (например, `bin/pccremote-0.1.0-arm64-v8a-debug.apk`).

### Вариант B: если WSL недоступен

Соберите APK на Linux-машине (или CI, например GitHub Actions) из этого же проекта — `buildozer.spec` уже готов.

### Вариант C: GitHub Actions (без WSL, одной кнопкой)

В проект добавлен workflow: `.github/workflows/android-apk.yml`.

Шаги:

1. Создайте репозиторий на GitHub и загрузите туда этот проект.
2. Откройте вкладку `Actions`.
3. Выберите workflow `Build Android APK`.
4. Нажмите `Run workflow` -> `Run workflow`.
5. Дождитесь завершения (обычно 15-40 минут при первой сборке).
6. Откройте успешный запуск и скачайте артефакт `pccremote-debug-apk`.
7. Распакуйте архив, внутри будет файл `.apk`.
8. Скопируйте APK на Pixel 7 Pro и установите.

Если Android блокирует установку:
- включите установку из неизвестных источников для приложения, через которое открываете APK (Files/Chrome/Telegram и т.д.),
- повторите установку.

## API (внутренне)

- `POST /shutdown` body `{"delay": 10}`
- `POST /cancel_shutdown` body `{}`
- `POST /volume` body `{"command": "up|down|mute", "steps": 2}`
- `POST /touchpad/move` body `{"dx": 5, "dy": -3, "sensitivity": 1.2}`
- `POST /touchpad/click` body `{"button": "left|right|middle", "double": false}`

## Важно

- Приложение и ПК должны быть в одной сети.
- Обязательно поменяйте токен по умолчанию.
- Сервер сейчас рассчитан на Windows (shutdown/мышь/клавиши громкости).
- APK должен устанавливаться на телефон с включенной установкой из неизвестных источников.
