import redis
import functools

from environs import Env
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Filters, Updater
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler
from moltin_funcs import (
    get_access_token,
    get_all_products,
    get_product_by_id,
    get_product_inventory,
    get_product_image_url,
    create_cart,
    add_product_to_cart,
    get_cart_items,
    get_cart,
    delete_item_from_cart
)

_database = None


def start(bot, update, products):
    """
    Хэндлер для состояния START.

    Бот отвечает пользователю фразой "Привет!" и переводит его в состояние ECHO.
    Теперь в ответ на его команды будет запускаеться хэндлер echo.
    """
    keyboard = [
        [
            InlineKeyboardButton(f"{product['attributes']['name']}", callback_data=f"{product['id']}")
            for product in products['data']
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(text='Привет!', reply_markup=reply_markup)
    return "HANDLE_DESCRIPTION"


def handle_menu(bot, update, products):
    user_chat_id = update.callback_query.from_user.id

    keyboard = [
        [
            InlineKeyboardButton(f"{product['attributes']['name']}", callback_data=f"{product['id']}")
            for product in products['data']
        ],
        [
            InlineKeyboardButton('Корзина', callback_data='cart')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    bot.send_message(chat_id=user_chat_id, text='Снова меню', reply_markup=reply_markup)
    return "HANDLE_DESCRIPTION"


def handle_description(bot, update, moltin_token, cart_id):
    user_chat_id = update.callback_query.from_user.id

    callback_split = update.callback_query.data.split()

    product_id = callback_split[-1]

    product = get_product_by_id(moltin_token, product_id)
    product_inventory_full = get_product_inventory(moltin_token, product_id)
    product_image_url = get_product_image_url(moltin_token, product_id)

    product_available_inventory = product_inventory_full['data']['available']
    product_name = product["data"]["attributes"]["name"]
    product_description = product["data"]["attributes"]["description"]
    product_price = product['data']['meta']['display_price']['without_tax']['formatted']

    product_message = f'{product_name}\n{product_description}\navailable: {product_available_inventory}\nprice: {product_price}'
    if 'pressed' in callback_split:
        add_product_to_cart(moltin_token, cart_id, product_id, quantity=int(callback_split[1]))
        keyboard = [
            [
                InlineKeyboardButton('1 кг', callback_data=update.callback_query.data),
                InlineKeyboardButton('5 кг', callback_data=update.callback_query.data),
                InlineKeyboardButton('10 кг', callback_data=update.callback_query.data)
            ],
            [
                InlineKeyboardButton('Назад', callback_data='back'),
                InlineKeyboardButton('Корзина', callback_data='cart')
            ]
        ]
    else:
        keyboard = [
            [
                InlineKeyboardButton('1 кг', callback_data=f'pressed 1 {update.callback_query.data}'),
                InlineKeyboardButton('5 кг', callback_data=f'pressed 5 {update.callback_query.data}'),
                InlineKeyboardButton('10 кг', callback_data=f'pressed 10 {update.callback_query.data}')
            ],
            [
                InlineKeyboardButton('Назад', callback_data='back'),
                InlineKeyboardButton('Корзина', callback_data='cart')
            ]
        ]

    bot.delete_message(user_chat_id, update.callback_query.message.message_id)
    reply_markup = InlineKeyboardMarkup(keyboard)

    bot.send_photo(user_chat_id, product_image_url, caption=product_message, reply_markup=reply_markup)

    return 'HANDLE_DESCRIPTION'


def handle_cart(bot, update, auth_token, cart_id):

    if update.callback_query.data != 'cart':
        delete_item_from_cart(auth_token, cart_id, update.callback_query.data)

    user_chat_id = update.callback_query.from_user.id
    cart_items = get_cart_items(auth_token, cart_id)['data']
    cart_message = 'No items in cart yet'
    keyboard = [
        [
            InlineKeyboardButton('В меню', callback_data='back'),
            InlineKeyboardButton('Оплатить', callback_data='email')
        ],
    ]
    if cart_items:
        cart = get_cart(auth_token,cart_id)

        products_in_cart = [
            '\n'.join([
                    item['name'],
                    item['description'],
                    f"{item['quantity']} кг",
            ])
            for item in cart_items
        ]
        products_in_cart.append(
            f"Total price: {cart['data']['meta']['display_price']['with_tax']['formatted']}"
        )
        cart_message = '\n\n'.join(products_in_cart)
        products_buttons = [
            InlineKeyboardButton(f"Убрать {product['name']}", callback_data=f"{product['id']}")
            for product in cart_items
        ]
        keyboard.insert(0, products_buttons)

    reply_markup = InlineKeyboardMarkup(keyboard)

    bot.send_message(user_chat_id, cart_message, reply_markup=reply_markup)

    return 'HANDLE_CART'


def get_email(bot, update):
    user_id = update.callback_query.from_user.id
    bot.send_message(user_id, 'Пришлите ваш email')
    email = update.message.text
    print(email)

    return 'WAITING_EMAIL'


def handle_users_reply(bot, update, db_connect, products, moltin_token, cart_id):
    """
    Функция, которая запускается при любом сообщении от пользователя и решает как его обработать.
    Эта функция запускается в ответ на эти действия пользователя:
        * Нажатие на inline-кнопку в боте
        * Отправка сообщения боту
        * Отправка команды боту
    Она получает стейт пользователя из базы данных и запускает соответствующую функцию-обработчик (хэндлер).
    Функция-обработчик возвращает следующее состояние, которое записывается в базу данных.
    Если пользователь только начал пользоваться ботом, Telegram форсит его написать "/start",
    поэтому по этой фразе выставляется стартовое состояние.
    Если пользователь захочет начать общение с ботом заново, он также может воспользоваться этой командой.
    """
    start_with_products = functools.partial(start, products=products)
    handle_menu_with_products = functools.partial(handle_menu, products=products)
    handle_description_with_token_cart = functools.partial(
        handle_description,
        moltin_token=moltin_token,
        cart_id=cart_id
    )
    handle_cart_with_token = functools.partial(
        handle_cart,
        auth_token=moltin_token,
        cart_id=cart_id
    )
    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif len(update.callback_query.data.split()) == 1:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    elif len(update.callback_query.data.split()) > 1:
        query_results = update.callback_query.data.split()
        user_reply = query_results[2]
        chat_id = update.callback_query.message.chat_id
    else:
        return
    if user_reply == '/start':
        user_state = 'START'
    elif update.callback_query.data == 'back':
        user_state = 'HANDLE_MENU'
    elif update.callback_query.data == 'cart':
        user_state = 'HANDLE_CART'
    elif update.callback_query == 'email':
        user_state = 'WAITING_EMAIL'
    else:
        user_state = db_connect.get(chat_id).decode("utf-8")

    states_functions = {
        'START': start_with_products,
        'HANDLE_MENU': handle_menu_with_products,
        'HANDLE_DESCRIPTION': handle_description_with_token_cart,
        'HANDLE_CART': handle_cart_with_token,
        'WAITING_EMAIL': get_email
    }

    state_handler = states_functions[user_state]
    # Если вы вдруг не заметите, что python-telegram-bot перехватывает ошибки.
    # Оставляю этот try...except, чтобы код не падал молча.
    # Этот фрагмент можно переписать.
    try:
        next_state = state_handler(bot, update)
        db_connect.set(chat_id, next_state)
    except Exception as err:
        print(err)


def get_database_connection(host, password, port):
    """
    Возвращает конекшн с базой данных Redis, либо создаёт новый, если он ещё не создан.
    """
    global _database
    if _database is None:
        database_password = password
        database_host = host
        database_port = port
        _database = redis.Redis(
            host=database_host,
            port=database_port,
            password=database_password,
        )
    return _database


if __name__ == '__main__':
    env = Env()
    env.read_env()
    telega_token = env("TELEGRAM_TOKEN")
    redis_host = env("REDIS_HOST")
    redis_password = env("REDIS_PASSWORD")
    redis_port = env("REDIS_PORT")
    moltin_token = get_access_token(env('MOLTIN_SECRET_KEY'))
    products = get_all_products(moltin_token)
    user_cart = create_cart(moltin_token)


    db_connect = get_database_connection(redis_host, redis_password, redis_port)

    handle_users_reply_with_connections = functools.partial(
        handle_users_reply,
        db_connect=db_connect,
        products=products,
        moltin_token=moltin_token,
        cart_id=user_cart['data']['id']
    )

    updater = Updater(telega_token)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply_with_connections))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply_with_connections))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply_with_connections))

    updater.start_polling()
    updater.idle()