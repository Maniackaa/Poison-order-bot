import asyncio
import datetime

from aiogram import Bot, Dispatcher

from config_data.bot_conf import conf, get_my_loggers

from handlers import user_handlers, orders, echo, manager

logger, err_log = get_my_loggers()


async def main():
    logger.info('Starting bot')
    bot: Bot = Bot(token=conf.tg_bot.token, parse_mode='HTML')
    dp: Dispatcher = Dispatcher()

    # Регистрируем
    dp.include_router(user_handlers.router)
    dp.include_router(orders.router)
    dp.include_router(manager.router)
    dp.include_router(echo.router)

    await bot.delete_webhook(drop_pending_updates=True)
    try:
        if conf.tg_bot.admin_ids:
            await bot.send_message(
                conf.tg_bot.admin_ids[0], f'Бот запущен.\n{datetime.datetime.now()}')
    except Exception:
        err_log.error(f'Не могу отравить сообщение {conf.tg_bot.admin_ids[0]}')
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info('Bot stopped!')