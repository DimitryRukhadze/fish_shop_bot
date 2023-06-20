import redis
import functools


from requests.exceptions import HTTPError

from environs import Env
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Filters, Updater
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler
from moltin import (
    MoltinToken,
    get_all_products,
    get_product_by_id,
    get_product_inventory,
    get_product_image_url,
    create_cart,
    add_product_to_cart,
    get_cart_items,
    get_cart,
    delete_item_from_cart,
    create_customer
)

_database = None


def start(bot, update, products):

    keyboard = [
        [
            InlineKeyboardButton(f"{product['attributes']['name']}", callback_data=f"{product['id']}")
            for product in products['data']
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(text='Привет!', reply_markup=reply_markup)
    return "HANDLE_DESCRIPTION"


def handle_cart(bot, update, auth_token):
    user_chat_id = update.callback_query.from_user.id

    if update.callback_query.data != 'HANDLE_CART':
        delete_item_from_cart(auth_token, user_chat_id, update.callback_query.data)

    cart_items = get_cart_items(auth_token, user_chat_id)['data']
    cart_message = 'No items in cart yet'
    keyboard = [
        [
            InlineKeyboardButton('В меню', callback_data='HANDLE_MENU'),
            InlineKeyboardButton('Оплатить', callback_data='WAITING_EMAIL')
        ],
    ]
    if cart_items:
        cart = get_cart(auth_token, user_chat_id)

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


def handle_menu(bot, update, products):
    user_chat_id = update.callback_query.from_user.id

    keyboard = [
        [
            InlineKeyboardButton(f"{product['attributes']['name']}", callback_data=f"{product['id']}")
            for product in products['data']
        ],
        [
            InlineKeyboardButton('Корзина', callback_data='HANDLE_CART')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    bot.send_message(
        chat_id=user_chat_id,
        text='Снова меню',
        reply_markup=reply_markup
    )

    return "HANDLE_DESCRIPTION"


def handle_description(bot, update, moltin_token):
    user_chat_id = update.callback_query.from_user.id
    callback_split = update.callback_query.data.split()

    if 'HANDLE_MENU' in callback_split:
        return 'HANDLE_MENU'
    elif 'HANDLE_CART' in callback_split:
        return 'HANDLE_CART'

    product_id = callback_split[-1]

    product = get_product_by_id(moltin_token, product_id)
    product_inventory_full = get_product_inventory(moltin_token, product_id)
    product_image_url = get_product_image_url(moltin_token, product_id)

    product_available_inventory = product_inventory_full['data']['available']
    product_name = product["data"]["attributes"]["name"]
    product_description = product["data"]["attributes"]["description"]
    product_price = product['data']['meta']['display_price']['without_tax']['formatted']

    product_message = f'{product_name}\n{product_description}\navailable: {product_available_inventory}\nprice: {product_price}'

    if len(callback_split) > 1:
        add_product_to_cart(
            moltin_token,
            user_chat_id,
            product_id,
            quantity=int(callback_split[0])
        )

        keyboard = [
            [
                InlineKeyboardButton('1 кг', callback_data=update.callback_query.data),
                InlineKeyboardButton('5 кг', callback_data=update.callback_query.data),
                InlineKeyboardButton('10 кг', callback_data=update.callback_query.data)
            ],
            [
                InlineKeyboardButton('Назад', callback_data='HANDLE_MENU'),
                InlineKeyboardButton('Корзина', callback_data='HANDLE_CART')
            ]
        ]
    else:
        keyboard = [
            [
                InlineKeyboardButton('1 кг', callback_data=f'1 {update.callback_query.data}'),
                InlineKeyboardButton('5 кг', callback_data=f'5 {update.callback_query.data}'),
                InlineKeyboardButton('10 кг', callback_data=f'10 {update.callback_query.data}')
            ],
            [
                InlineKeyboardButton('Назад', callback_data='HANDLE_MENU'),
                InlineKeyboardButton('Корзина', callback_data='HANDLE_CART')
            ]
        ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    bot.send_photo(
        user_chat_id,
        product_image_url,
        caption=product_message,
        reply_markup=reply_markup
    )
    bot.delete_message(user_chat_id, update.callback_query.message.message_id)

    return 'HANDLE_DESCRIPTION'


def get_email(bot, update, token):
    if update.message:
        email = update.message.text
        chat_id = update.message.chat_id
        text = f'Ваш email: {email}'
        try:
            create_customer(token, chat_id, email)
        except HTTPError as httperr:
            if '409' in httperr.args[0].split():
                text = f'У нас есть ваш email: {email}. Спасибо, что вы с нами!'
            elif '422' in httperr.args[0].split():
                text = f'Неверный email: {email}'
        keyboard = [
            [
                InlineKeyboardButton('Вернуться в меню', callback_data='back'),
            ]
        ]
        bot.send_message(
            chat_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return 'HANDLE_MENU'
    user_id = update.callback_query.from_user.id
    bot.send_message(user_id, 'Пришлите ваш email')

    return 'WAITING_EMAIL'


def handle_users_reply(
        bot,
        update,
        db_connect,
        products,
        token_obj,
):
    actual_token = token_obj.check_and_renew()

    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    else:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id

    start_with_products = functools.partial(
        start,
        products=products
    )
    handle_menu_with_products = functools.partial(
        handle_menu,
        products=products
    )
    handle_description_with_token = functools.partial(
        handle_description,
        moltin_token=actual_token,
    )
    handle_cart_with_token = functools.partial(
        handle_cart,
        auth_token=actual_token,
    )
    get_email_with_token = functools.partial(get_email, token=actual_token)

    states_functions = {
        'START': start_with_products,
        'HANDLE_MENU': handle_menu_with_products,
        'HANDLE_DESCRIPTION': handle_description_with_token,
        'HANDLE_CART': handle_cart_with_token,
        'WAITING_EMAIL': get_email_with_token
    }

    if user_reply == '/start':
        user_state = 'START'
    elif user_reply in states_functions.keys():
        user_state = user_reply
    else:
        user_state = db_connect.get(chat_id).decode("utf-8")

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


def main():

    env = Env()
    env.read_env()

    moltin_token_obj = MoltinToken(
        env('MOLTIN_CLIENT_ID'),
        env('MOLTIN_SECRET_KEY')
    )

    telega_token = env("TELEGRAM_TOKEN")
    redis_host = env("REDIS_HOST")
    redis_password = env("REDIS_PASSWORD")
    redis_port = env("REDIS_PORT")

    products = get_all_products(moltin_token_obj.token)

    db_connect = get_database_connection(
        redis_host,
        redis_password,
        redis_port
    )

    handle_users_reply_with_connections = functools.partial(
        handle_users_reply,
        db_connect=db_connect,
        products=products,
        token_obj=moltin_token_obj,
    )

    updater = Updater(telega_token)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(
        CallbackQueryHandler(handle_users_reply_with_connections)
    )
    dispatcher.add_handler(
        MessageHandler(Filters.text, handle_users_reply_with_connections)
    )
    dispatcher.add_handler(
        CommandHandler('start', handle_users_reply_with_connections)
    )

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()