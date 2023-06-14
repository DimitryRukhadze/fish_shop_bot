# Описание devman_api_bot_1

Этот бот сделан в учебных целях для курса [devman.org](https://dvmn.org). Пример работающего бота напишите ему в Telegram: `@Devman_hobot_bot`

## Подготовка к работе

Для работы вам нужно создать своего telegram бота, или использовать уже имеющегося. Для создания нового бота следуйте
этим инструкциям: [Как создать нового бота](https://core.telegram.org/bots#6-botfather)

Этот бот пользуется API [elasticpath](https://elasticpath.dev/). Необходимо завести там магазин и получить секретный ключ.

Этот бот пользуется базой данных [redis](https://redis.io/). Перед запуском вам необходимо её завести.

Бот написан на языке python версии 3.9.1. Для работы необходима эта версия языка.

Затем, следует установить необходимые для работы приложения библиотеки с помощью команды в терминале:
```commandline
pip install -r requirements.txt
```

Необходимо создать файл `.env`. В него следует внести ваши токены для API Девмана и бота, как показано ниже.

```dotenv
MOLTIN_SECRET_KEY=ваш ключ от магазина
TELEGRAM_TOKEN=токен бота
REDIS_HOST=хост вашей бд
REDIS_PORT=порт вашей бд
REDIS_PASSWORD=ваш пароль redis
REDIS_USERNAME=default
```

##Описание модулей и запуск
###moltin_funcs.py

Этот модуль содержит функции для работы с API elasticpath

###bot.py

Это основной модуль приложения. Чтобы бот заработал локально, запустите его коммандой `python bot.py`

