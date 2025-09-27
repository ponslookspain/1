# Telegram FanPay Listing Bot

Этот проект предоставляет Telegram-бота, который собирает данные лота у пользователя и создаёт объявление на FanPay, используя авторизационные cookie вашего аккаунта.

## Возможности

- Пошаговое общение в Telegram: бот спрашивает название, описание, цену и количество.
- Проверка введённых данных и подтверждение перед созданием лота.
- Отправка запроса на FanPay с использованием заранее сохранённого cookie-файла.

## Предварительные требования

1. Python 3.10+
2. Токен Telegram-бота
3. Cookie-файл сессии FanPay в формате Netscape (его можно экспортировать, например, через расширение EditThisCookie)

## Установка

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Переменные окружения

- `TELEGRAM_BOT_TOKEN` — токен вашего Telegram-бота
- `FANPAY_COOKIE_FILE` — путь к cookie-файлу FanPay
- `FANPAY_BASE_URL` (опционально) — если нужно переопределить базовый URL (по умолчанию `https://funpay.com`)

## Запуск

```bash
export TELEGRAM_BOT_TOKEN="<ваш токен>"
export FANPAY_COOKIE_FILE="/path/to/cookies.txt"
python -m bot.telegram_bot
```

## Настройка FanPay

API FanPay не задокументирован, поэтому в файле `bot/fanpay.py` реализован базовый POST-запрос на эндпоинт `/api/listings`. Если на FanPay используется другой URL или требуется дополнительный CSRF-токен, обновите метод `create_listing` в соответствии с фактическим API.

## Лицензия

Проект распространяется по лицензии MIT.
