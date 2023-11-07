import re

from aiogram import Router, F, Bot
from aiogram.enums import ContentType
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, BaseFilter
from aiogram.types import Message, CallbackQuery, Chat

from services.func import get_or_create_user

router: Router = Router()


# Последний эхо-фильтр
@router.message()
async def send_echo(message: Message):
    print('echo message:', message.text)
    print(message.content_type)

@router.callback_query()
async def send_echo(callback: CallbackQuery):
    print('echo callback:', callback.data)

