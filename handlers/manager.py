from aiogram import Dispatcher, types, Router, Bot, F
from aiogram.enums import ContentType
from aiogram.filters import Command, CommandStart, StateFilter, BaseFilter
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message, URLInputFile, BufferedInputFile

from aiogram.fsm.context import FSMContext

from config_data.bot_conf import get_my_loggers
from database.db import User, Item, Order
from keyboards.keyboards import start_kb, custom_kb, cart_kb
from services.func import get_or_create_user, get_order_confirm_text, get_bucket_text, get_cart_delete_kb_btn, \
    delete_order, update_pay_confirm, update_user, send_orders_to_manager, get_order, cancel_order, order_buy, \
    get_order_from_msg

logger, err_log = get_my_loggers()

router: Router = Router()


class FSMManager(StatesGroup):
    delete = State()


# Перехват ответа
@router.message(F.reply_to_message, F.text.lower().startswith('отменить '))
async def get_reply(message: Message, state: FSMContext, bot: Bot):
    msg = message.reply_to_message
    raw_order_id = message.text.lower().strip().split('отменить ')[-1]
    order_id = int(raw_order_id.strip())
    order = get_order(order_id)
    if order and order_id == order.id:
        await state.set_state(FSMManager.delete)
        await state.update_data(msg=msg, order_id=order_id)
        await message.answer('Укажите причину отмены')
    else:
        await message.answer('Заказ не найден')


@router.message(StateFilter(FSMManager.delete))
async def delete(message: Message, state: FSMContext, bot: Bot):
    """
    Отменяем заказ
    """
    try:
        reason = message.text
        data = await state.get_data()
        msg = data.get('msg')
        order_id = data.get('order_id')
        order = get_order(order_id)
        if order and order_id == order.id:
            cancel_text = f'Заказ {order_id} отменен:\n{reason}'
            await bot.send_message(chat_id=order.user.tg_id, text=cancel_text)
            cancel_order(order_id)
            await bot.delete_message(chat_id=msg.chat.id, message_id=msg.message_id)
            await message.answer(f'Заказ {order_id} отменен')
        else:
            await message.answer('Заказ не найден')
        await state.clear()
    except Exception as err:
        err_log.error(f'Ошибка при отмене заказа: {err}')
        await message.answer(f'Ошибка: {err}')
        await state.clear()


# Перехват ответа
@router.message(F.reply_to_message,
                F.content_type.in_({ContentType.PHOTO}),
                F.caption.lower().startswith('подтвердить '))
async def get_reply(message: Message, state: FSMContext, bot: Bot):
    logger.debug('Подтвердить')
    msg = message.reply_to_message
    raw_order_id = message.caption.lower().strip().split('подтвердить ')[-1]
    try:
        order_id = int(raw_order_id.strip())
        order = get_order_from_msg(msg.message_id)
        if order and order_id == order.id:
            order_buy(order_id)
            confirm_text = f'Заказ {order.id} выкуплен'
            await bot.send_photo(chat_id=order.user.tg_id, photo=message.photo[2].file_id, caption=confirm_text)
            await bot.delete_message(chat_id=msg.chat.id, message_id=msg.message_id)
            await message.answer(f'Заказ {order.id} подтвержден')
        else:
            await message.answer('Заказ не найден')
    except Exception as err:
        err_log.error(f'Ошибка при подтверждении заказа {raw_order_id}: {err}')
        await message.answer(f'Ошиюка: {err}')



