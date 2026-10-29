# CI/CD: тесты и деплой на локальный сервер

Workflow: [.github/workflows/ci-cd.yml](.github/workflows/ci-cd.yml)

## Как это работает

```
push / PR в main
      │
      ▼
 job "test"  ── ubuntu-latest (облако GitHub) ── pytest
      │ успех
      ▼
 job "deploy" ── self-hosted runner на вашем сервере
      ├─ checkout кода
      ├─ создание .env из GitHub Secrets
      ├─ docker compose up -d --build
      └─ проверка http://localhost:8888/api/health
```

GitHub-раннеры в облаке не видят сервер в вашей локальной сети, поэтому на сервер
ставится **self-hosted runner**: он сам подключается к GitHub (исходящее HTTPS),
забирает задачи и выполняет их локально. Белый IP и проброс портов не нужны.

## Что нужно на сервере

Пример для Ubuntu 22.04/24.04.

### 1. Docker и Docker Compose

```bash
curl -fsSL https://get.docker.com | sudo sh
docker compose version   # должен быть Compose v2
```

PostgreSQL отдельно ставить не нужно: он поднимается в контейнере из `docker-compose.yml`.

### 2. Пользователь для раннера

```bash
sudo useradd -m -s /bin/bash github-runner
sudo usermod -aG docker github-runner   # чтобы запускать docker без sudo
```

### 3. Self-hosted runner

В репозитории на GitHub: **Settings → Actions → Runners → New self-hosted runner → Linux**.
GitHub покажет команды со ссылкой на актуальную версию и токен. Выполните их от имени `github-runner`:

```bash
sudo -iu github-runner
mkdir actions-runner && cd actions-runner
curl -o actions-runner.tar.gz -L <ССЫЛКА_С_СТРАНИЦЫ_GITHUB>
tar xzf actions-runner.tar.gz
./config.sh --url https://github.com/<ВАШ_АККАУНТ>/taskboard --token <ТОКЕН>
exit
```

Workflow использует `runs-on: [self-hosted, linux]` — эти метки GitHub присваивает
любому Linux-раннеру автоматически.

Установите раннер как сервис (автозапуск после перезагрузки):

```bash
cd /home/github-runner/actions-runner
sudo ./svc.sh install github-runner
sudo ./svc.sh start
sudo ./svc.sh status
```

После этого раннер появится в **Settings → Actions → Runners** со статусом `Idle`.

### 4. curl

Нужен для проверки healthcheck (обычно уже установлен): `sudo apt install -y curl`.

## Что нужно настроить в GitHub

**Settings → Secrets and variables → Actions**:

| Тип      | Имя                 | Пример       |
|----------|---------------------|--------------|
| Secret   | `POSTGRES_DB`       | `taskboard`  |
| Secret   | `POSTGRES_USER`     | `taskboard`  |
| Secret   | `POSTGRES_PASSWORD` | сложный пароль |
| Variable | `APP_NAME`          | `TaskBoard` (необязательно) |

Пароль используется внутри `DATABASE_URL`, поэтому не используйте в нем символы `@ : / ? #`
(или экранируйте их в URL-формате).

Файл `.env` из репозитория не нужен на сервере — workflow создает его сам из секретов
и удаляет после деплоя.

Environment `production` создается автоматически при первом запуске. В
**Settings → Environments → production** можно включить ручное подтверждение деплоя
(Required reviewers).

## Проверка

1. Сделайте push в `main` (или запустите вручную: **Actions → CI/CD → Run workflow**).
2. Во вкладке **Actions** должны пройти обе job: `Tests` и `Deploy to local server`.
3. На сервере:

```bash
docker ps                                 # taskboard_postgres и fastapi_app
curl http://localhost:8888/api/health     # {"status":"ok","service":"TaskBoard"}
```

Приложение доступно на `http://192.168.188.143:8888/`.

## Запуск тестов локально

```bash
pip install -r requirements-dev.txt
pytest -v
```

Тесты используют SQLite в памяти, PostgreSQL для них не нужен.

## Важно про деплой из Pull Request

По заданию деплой выполняется и при PR в `main`. Это значит, что на сервер попадет код
из ветки PR **до** его слияния, а следующий PR или push перезапишет его.
PR из форков не деплоятся — иначе чужой код выполнялся бы на вашем сервере.
Если деплой из PR не нужен, уберите `pull_request` из `on:` или замените условие `if` у
job `deploy` на `github.event_name == 'push'`.

Также рекомендуется сделать репозиторий **приватным** или оставить ограничение на форки:
self-hosted runner в публичном репозитории — известный вектор атаки.

## Частые проблемы

| Симптом | Причина / решение |
|---|---|
| Deploy висит в статусе `Queued` | Раннер офлайн или метки не совпадают с `runs-on` |
| `permission denied ... docker.sock` | Пользователь раннера не в группе `docker`; после `usermod` перезапустите сервис раннера |
| Healthcheck failed, в логах ошибка подключения к БД | Неверные секреты; если меняли пароль после первого запуска — старый пароль уже записан в volume `taskboard_data`. Для учебного стенда: `docker compose -p taskboard down -v` (удалит данные) |
| `port is already allocated` | Порт 8888 занят другим процессом |
