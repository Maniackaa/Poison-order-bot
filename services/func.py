import asyncio
import datetime
import math
from typing import Sequence

from aiogram import Bot
from aiogram.types import BufferedInputFile, InputMediaPhoto
from sqlalchemy import select, delete

from config_data.bot_conf import get_my_loggers
from database.db import Session, User, Order, BotSettings, Faq

logger, err_log = get_my_loggers()


def check_user(id):
    """Возвращает найденных пользователей по tg_id"""
    logger.debug(f'Ищем юзера {id}')
    with Session() as session:
        user: User = session.query(User).filter(User.tg_id == str(id)).first()
        logger.debug(f'Результат: {user}')
        return user


def get_or_create_user(user) -> User:
    """Из юзера ТГ возвращает сущестующего User ли создает его"""
    try:
        tg_id = user.id
        username = user.username
        logger.debug(f'username {username}')
        old_user = check_user(tg_id)
        if old_user:
            logger.debug('Пользователь есть в базе')
            return old_user
        logger.debug('Добавляем пользователя')
        with Session() as session:
            new_user = User(tg_id=tg_id,
                            username=username,
                            register_date=datetime.datetime.now()
                            )
            session.add(new_user)
            session.commit()
            logger.debug(f'Пользователь создан: {new_user}')
        return new_user
    except Exception as err:
        err_log.error('Пользователь не создан', exc_info=True)


def update_user(user: User, data: dict):
    try:
        logger.debug(f'Обновляем {user}: {data}')
        session = Session()
        with session:
            user: User = session.query(User).filter(User.id == user.id).first()
            for key, val in data.items():
                setattr(user, key, val)
            session.commit()
            logger.debug(f'Юзер обновлен {user}')
    except Exception as err:
        err_log.error(f'Ошибка обновления юзера {user}: {err}')


def get_order_confirm_text(order: Order) -> str:
    msg = (
        f'Ссылка: {order.link}\n'
        f'Размер: {order.size}\n'
        f'Стоимость: {order.cost}\n'
    )
    return msg


def get_cny_to_rub():
    cny = 12.71
    cny = cny + 0.5
    cny = cny * 10
    cny = math.ceil(cny)
    cny = cny / 10
    return cny


def read_bot_settings(name: str) -> str:
    session = Session()
    with session:
        q = select(BotSettings).where(BotSettings.name == name).limit(1)
        result = session.execute(q).scalars().one_or_none()
    return result.value


def get_tax(user: User) -> int:
    tax1 = int(read_bot_settings('tax1'))
    tax2 = int(read_bot_settings('tax2'))
    return tax1 if user.is_newbie else tax2


def get_total_cost(user: User) -> float:
    """
    Расчет стоимости корзины
    """
    session = Session()
    with session:
        q = select(Order).where(Order.user_id == user.id).where(Order.status == 'temp')
        orders: Sequence = session.execute(q).scalars().all()
        if not orders:
            return 0
        rub_cny = get_cny_to_rub()
        tax = get_tax(user)
        total_cost = 0
        for order in orders:
            total_cost += order.cost * rub_cny * 1.01
            shipping = order.item.shipping
            total_cost += shipping
            total_cost += tax
        return round(total_cost, 2)


def get_bucket_text(user: User) -> str:
    """
    Формирование текста Инфо о корзине
    """
    session = Session()
    with session:
        q = select(Order).where(Order.user_id == user.id).where(Order.status == 'temp')
        orders = session.execute(q).scalars().all()
        logger.debug(f'Заказы {user}: {orders}')
        if orders:
            total_cost = get_total_cost(user)
            text = f'Итоговая стоимость: {total_cost}\n\n'
            for num, order in enumerate(orders, 1):
                text += f'{num}. {order.item.name}\n'
                text += f'{order.link}\n'
                text += f'Размер: {order.size}\n'
                text += f'Стоимость: {order.cost}\n'
                text += f'Доставка: {order.item.shipping}\n'
                text += f'Номер: {order.id}\n\n'
            text += f'Доставка по адресу:\n{user.address}\n'
            text += f'Фио получателя:\n{user.fio}\n'
            text += f'Номер получателя:\n{user.phone}\n\n'
            text += 'Реквизиты для оплаты:\nLSKJDHNGV\n\n'
            text += 'После оплаты пришите чек'
            return text
        else:
            text = 'Ваша корзина пуста'
            return text


def get_cart_delete_kb_btn(user: User) -> dict:
    """
    Кнопки для удаления из корзины
    """
    session = Session()
    with session:
        q = select(Order).where(Order.user_id == user.id).where(Order.status == 'temp')
        orders = session.execute(q).scalars().all()
        buttons = {}
        for num, order in enumerate(orders, 1):
            buttons[f'{num}. Номер {order.id}'] = f'cartdel_{order.id}'
        return buttons


def delete_order(pk):
    try:
        session = Session()
        with session:
            q = delete(Order).where(Order.id == pk)
            session.execute(q)
            session.commit()
            logger.debug(f'Заказ {pk} удален')
    except Exception as err:
        logger.error(f'Ошибка при удалении заказа {pk}: {err}')


def update_pay_confirm(user: User, pay):
    logger.debug('Сохраняем чек')
    session = Session()
    with session:
        q = select(Order).where(Order.user_id == user.id).where(Order.status == 'temp')
        orders: Sequence = session.execute(q).scalars().all()
        for order in orders:
            order.pay_confirm = pay
            order.pay_date = datetime.datetime.now()
        session.commit()
        logger.debug('Чек сохранен')


def get_manager_order_text(user: User, order: Order) -> str:
    """
    Формирование текста по заказу для менеджера
    """

    text = f'{order.pay_date}\n'
    text += f'@{user.username}\n'
    text += f'{order.link}\n'
    text += f'Размер: {order.size}\n'
    text += f'Стоимость: {order.cost}\n'
    text += f'Номер: {order.id}\n'
    text += f'Фио: {user.fio}\n'
    text += f'Телефон: {user.phone}\n'
    text += f'Доставка по адресу:\n{user.address}\n'
    return text


async def send_orders_to_manager(user, bot: Bot):
    """
    Отправка менеджеру. Смена статуса.
    """
    try:
        logger.debug('Отправка менеджеру')
        session = Session()
        with session:
            q = select(Order).where(Order.user_id == user.id).where(Order.status == 'temp')
            orders: Sequence = session.execute(q).scalars().all()
            order_ids = []
            manager_id = read_bot_settings('manager_id')
            if orders:
                for num, order in enumerate(orders):
                    try:
                        item_photo = order.photo
                        photo = BufferedInputFile(item_photo, filename='item_photo_name')
                        order_text = get_manager_order_text(user, order)
                        msg = await bot.send_photo(chat_id=manager_id, photo=photo, caption=order_text)
                        order_ids.append(order.id)
                        order.status = 'payed'
                        order.manager_msg_id = msg.message_id
                        session.commit()
                        logger.debug(f'Сообщение {msg.message_id}')
                    except Exception as err:
                        logger.error(err)
                pay_photo = BufferedInputFile(order.pay_confirm, filename='pay_photo_name')
                pay_caption = f'Платеж к заказам {order_ids}'
                await bot.send_photo(chat_id=manager_id, photo=pay_photo, caption=pay_caption)
    except Exception as err:
        raise err


def get_order(order_id) -> Order:
    """
    Возвращает Order по id
    """
    session = Session()
    with session:
        q = select(Order).where(Order.id == order_id)
        order = session.execute(q).scalars().one_or_none()
        logger.debug(f'Найден заказ {order}')
        return order


def cancel_order(order_id) -> bool:
    """
    Меняет статус заказа на отмененный
    """
    session = Session()
    with session:
        q = select(Order).where(Order.id == order_id)
        order = session.execute(q).scalars().one_or_none()
        if order:
            order.status = 'canceled'
            session.commit()
            logger.debug(f'Статус заказа {order} изменен на "canceled"')
            return True
        return False


def order_buy(order_id) -> bool:
    """
    Меняет статус заказа на купленный
    """
    session = Session()
    with session:
        q = select(Order).where(Order.id == order_id)
        order = session.execute(q).scalars().one_or_none()
        if order:
            order.status = 'buyed'
            session.commit()
            logger.debug(f'Статус заказа {order} изменен на "buyed"')
            return True
        return False


def get_order_from_msg(msg_id):
    session = Session()
    with session:
        q = select(Order).where(Order.manager_msg_id == msg_id)
        order = session.execute(q).scalars().one_or_none()
        logger.debug(f'Найден заказ {order}')
        return order


def get_faq(faq_id):
    session = Session()
    with session:
        q = select(Faq).where(Faq.id == faq_id)
        faq = session.execute(q).scalars().one_or_none()
        return faq