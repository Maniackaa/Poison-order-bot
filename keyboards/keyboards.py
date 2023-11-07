from aiogram.types import KeyboardButton, ReplyKeyboardMarkup,\
    InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def custom_kb(width: int, buttons_dict: dict) -> InlineKeyboardMarkup:
    kb_builder: InlineKeyboardBuilder = InlineKeyboardBuilder()
    buttons = []
    for key, val in buttons_dict.items():
        callback_button = InlineKeyboardButton(
            text=key,
            callback_data=val)
        buttons.append(callback_button)
    kb_builder.row(*buttons, width=width)
    return kb_builder.as_markup()


start_kb_b = {
    'Ответы на частые вопросы': 'faq',
    'Товары в наличии': 'items',
    'Поддержка': 'support',
    'Калькулятор стоимости': 'calc',
    'Оформить заказ': 'cart',
}

start_kb = custom_kb(1, start_kb_b)

cart_kb_b = {
    'Удалить товар из корзины': 'cart_del',
    'Подтвердить оплату': 'pay_confirm',
    'Проблема с оплатой': 'pay_problem',
    'Добавить товар в корзину': 'order',
    'Изменить контактную информацию': 'user_update',
}

cart_kb = custom_kb(1, cart_kb_b)
