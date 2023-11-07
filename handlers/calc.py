import io
from typing import BinaryIO

from aiogram import Dispatcher, types, Router, Bot, F
from aiogram.enums import ContentType
from aiogram.filters import Command, CommandStart, StateFilter, BaseFilter
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message, URLInputFile, BufferedInputFile

from aiogram.fsm.context import FSMContext

from config_data.bot_conf import get_my_loggers
from database.db import User, Item, Order
from handlers.user_handlers import FSMUser
from keyboards.keyboards import start_kb, custom_kb, cart_kb
from services.func import get_or_create_user, get_order_confirm_text, get_bucket_text, get_cart_delete_kb_btn, \
    delete_order, update_pay_confirm, update_user, send_orders_to_manager, get_item, calc_cost

logger, err_log = get_my_loggers()

router: Router = Router()


class FSMCalc(StatesGroup):
    selected = State()
    order_cost = State()


@router.callback_query(F.data == 'calc')
async def order_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    btn = Item().menu_btn()
    await state.set_state(FSMCalc.selected)
    text = '\n\nВыберите тип товара:'
    await callback.message.answer(text, reply_markup=custom_kb(1, btn))


@router.callback_query(F.data.startswith('item_'), StateFilter(FSMCalc.selected))
async def order_item_selected(callback: CallbackQuery, state: FSMContext):
    data = callback.data
    item_id = int(data.split('item_')[-1])
    await state.update_data(item_id=item_id)
    await callback.message.edit_text('Укажите цену')
    await state.set_state(FSMCalc.order_cost)


@router.message(StateFilter(FSMCalc.order_cost))
async def order_cost(message: Message, state: FSMContext, bot: Bot):
    try:
        data = await state.get_data()
        item_id = data.get('item_id')
        cost = float(message.text.strip())
        user = get_or_create_user(message.from_user)
        item = get_item(item_id)
        calc = calc_cost(user, cost, item.shipping)
        await message.delete()
        text = item.name
        text += f'\nСтоимость товара: {cost} ¥'
        text += f'\n\nИтог: {calc} руб.'
        await message.answer(text, reply_markup=start_kb)

    except Exception as err:
        logger.error(err)
