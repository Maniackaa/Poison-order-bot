import asyncio

from aiogram import Dispatcher, types, Router, Bot, F
from aiogram.filters import Command, CommandStart, StateFilter, BaseFilter
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message, URLInputFile

from aiogram.fsm.context import FSMContext

from config_data.bot_conf import get_my_loggers
from database.db import User, Faq
from keyboards.keyboards import start_kb, cart_kb, custom_kb
from services.func import get_or_create_user, update_user, get_bucket_text, get_faq

logger, err_log = get_my_loggers()

router: Router = Router()


class FSMUser(StatesGroup):
    fio = State()
    phone = State()
    address = State()


@router.callback_query(F.data == 'menu')
async def start(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await state.clear()
    tg_user = callback.from_user
    user: User = get_or_create_user(tg_user)
    text = 'Выберите действие:'
    await callback.message.delete()
    await callback.message.answer(text, reply_markup=start_kb)


@router.message(Command(commands=["start"]))
async def process_start_command(message: Message, state: FSMContext):
    await state.clear()
    tg_user = message.from_user
    user: User = get_or_create_user(tg_user)
    text = 'Выберите действие:'
    await message.answer(text, reply_markup=start_kb)


@router.callback_query(F.data == 'user_update')
async def user_update(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.message.delete()
    await callback.message.answer('Укажите ФИО')
    await state.set_state(FSMUser.fio)


@router.message(StateFilter(FSMUser.fio))
async def fio(message: Message, state: FSMContext, bot: Bot):
    fio = message.text.strip()
    await state.update_data(fio=fio)
    await message.answer('Введите номер телефона')
    await state.set_state(FSMUser.phone)


@router.message(StateFilter(FSMUser.phone))
async def phone(message: Message, state: FSMContext, bot: Bot):
    phone = message.text.strip()
    await state.update_data(phone=phone)
    await message.answer('Введите адрес')
    await state.set_state(FSMUser.address)


@router.message(StateFilter(FSMUser.address))
async def address(message: Message, state: FSMContext, bot: Bot):
    address = message.text.strip()
    await state.update_data(address=address)
    data = await state.get_data()
    user = get_or_create_user(message.from_user)
    update_user(user, data)
    await state.clear()
    text = get_bucket_text(get_or_create_user(message.from_user))
    await message.answer(text, reply_markup=cart_kb)


@router.callback_query(F.data == 'faq')
async def faq(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.message.delete()
    btn = Faq().menu_btn()
    await callback.message.answer('Выберите вопроc:', reply_markup=custom_kb(1, btn))


@router.callback_query(F.data.startswith('answer_'))
async def answer(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = callback.data
    question_id = int(data.split('answer_')[-1])
    my_faq: Faq = get_faq(question_id)
    text = f'{my_faq.question}\n\n{my_faq.answer}'
    await callback.message.edit_text(text, reply_markup=custom_kb(1, Faq().menu_btn()))
