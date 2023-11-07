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
    delete_order, update_pay_confirm, update_user, send_orders_to_manager

logger, err_log = get_my_loggers()

router: Router = Router()


class FSMOrder(StatesGroup):
    selected = State()
    order_photo = State()
    order_link = State()
    order_size = State()
    order_cost = State()
    delete = State()
    pay_confirm = State()


@router.callback_query(F.data == 'cart')
async def order_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    user = get_or_create_user(callback.from_user)
    text = get_bucket_text(user)
    await callback.message.answer(text, reply_markup=cart_kb)


@router.callback_query(F.data == 'order')
async def order_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    btn = Item().menu_btn()
    await state.set_state(FSMOrder.selected)
    # text = get_bucket_text(get_or_create_user(callback.from_user))
    text = '\n\nВыберите тип товара:'
    await callback.message.answer(text, reply_markup=custom_kb(1, btn))


@router.callback_query(F.data.startswith('item_'), StateFilter(FSMOrder.selected))
async def order_item_selected(callback: CallbackQuery, state: FSMContext):
    data = callback.data
    item_id = int(data.split('item_')[-1])
    order = Order(item_id=item_id)
    await state.update_data(order=order)
    await callback.message.edit_text('Вставьте фото товара')
    await state.set_state(FSMOrder.order_photo)


@router.message(F.content_type.in_({ContentType.PHOTO}), FSMOrder.order_photo)
async def order_send_photo(message: Message, state: FSMContext, bot: Bot):
    photo = message.photo
    photo_id = photo[2].file_id
    mem_photo = io.BytesIO()
    await bot.download(file=photo_id, destination=mem_photo)
    data = await state.get_data()
    order = data['order']
    bytes_photo = mem_photo.read()
    order.photo = bytes_photo
    await state.update_data(order=order)
    # photo = BufferedInputFile(mem_photo.read(), filename='photo_name')
    # await message.answer_photo(photo=photo, caption='caption')
    await message.answer('Укажите ссылку на товар')
    await state.set_state(FSMOrder.order_link)


@router.message(StateFilter(FSMOrder.order_link))
async def order_link(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    order = data['order']
    order.link = message.text
    await state.update_data(order=order)
    await message.answer('Укажите размер товара (если есть) или напишите "нет"')
    await state.set_state(FSMOrder.order_size)


@router.message(StateFilter(FSMOrder.order_size))
async def order_size(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    order = data['order']
    order.size = message.text
    await state.update_data(order=order)
    await message.answer('Укажите стоимость')
    await state.set_state(FSMOrder.order_cost)


@router.message(StateFilter(FSMOrder.order_cost))
async def order_cost(message: Message, state: FSMContext, bot: Bot):
    try:
        data = await state.get_data()
        order = data['order']
        cost = float(message.text.strip())
        order.cost = cost
        await state.update_data(order=order)
        text = 'Всё ли указано верно?\n\n'
        text += get_order_confirm_text(order)
        photo = BufferedInputFile(order.photo, filename='photo_name')
        confirm_btn = {
            'Изменить': 'cart',
            'Верно!': 'order_confirm'
        }
        await message.answer_photo(photo=photo, caption=text, reply_markup=custom_kb(2, confirm_btn))
    except Exception as err:
        logger.error(err)
        await message.answer('Введите корректную стоимость')


@router.callback_query(StateFilter(FSMOrder.order_cost), F.data == 'order_confirm')
async def order_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.message.delete()
    data = await state.get_data()
    order = data['order']
    user = get_or_create_user(callback.from_user)
    order.user_id = user.id
    order.save()
    text = get_bucket_text(user)
    await callback.message.answer(text, reply_markup=cart_kb)


@router.callback_query(F.data == 'cart_del')
async def del_select(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.message.delete()
    user = get_or_create_user(callback.from_user)
    btn = get_cart_delete_kb_btn(user)
    text = get_bucket_text(user)
    text += '\nКакой товар удалить?'
    await callback.message.answer(text, reply_markup=custom_kb(1, btn))


@router.callback_query(F.data.startswith('cartdel_'))
async def cart_del(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    data = callback.data
    order_id = int(data.split('cartdel_')[-1])
    delete_order(order_id)
    text = get_bucket_text(get_or_create_user(callback.from_user))
    await callback.message.answer(text, reply_markup=cart_kb)


@router.callback_query(F.data == 'pay_confirm')
async def pay_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot):
    user = get_or_create_user(callback.from_user)
    if user.fio and user.phone and user.address:
        await callback.message.delete()
        await callback.message.answer('Пришлите, пожалуйста, чек')
        await state.set_state(FSMOrder.pay_confirm)
    else:
        await callback.message.answer('У вас не заполнен профиль. Укажите ФИО:')
        await callback.message.delete()
        await state.set_state(FSMUser.fio)


@router.message(F.content_type.in_({ContentType.PHOTO}), FSMOrder.pay_confirm)
async def order_pay_confirm(message: Message, state: FSMContext, bot: Bot):
    print('confirm')
    try:
        photo = message.photo
        photo_id = photo[2].file_id
        mem_photo = io.BytesIO()
        await bot.download(file=photo_id, destination=mem_photo)
        user = get_or_create_user(message.from_user)
        text = 'Ваш заказ оформлен:\n'
        text += get_bucket_text(user)
        await message.answer(text)
        bytes_photo = mem_photo.read()
        update_pay_confirm(user, bytes_photo)
        await message.answer('Спасибо за покупку!\nНаш менеджер подтвердит оплату в течение 24 часов, и пришлёт скриншот выкупа.',
                             reply_markup=start_kb)
        # Действия после оплаты
        update_user(user, {'is_newbie': 0})
        await send_orders_to_manager(user, bot)
        await state.clear()

    except Exception as err:
        logger.error(f'Ошибка при оплате: {err}')
