import asyncio
import datetime
import sys


from sqlalchemy import create_engine, ForeignKey, Date, String, DateTime, \
    Float, UniqueConstraint, Integer, LargeBinary, BLOB, select
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils.functions import database_exists, create_database

from config_data.bot_conf import conf, get_my_loggers

logger, err_log = get_my_loggers()

db_url = f"postgresql+psycopg2://{conf.db.db_user}:{conf.db.db_password}@{conf.db.db_host}:{conf.db.db_port}/{conf.db.database}"
engine = create_engine(db_url, echo=False)
Session = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True,
                                    autoincrement=True)
    tg_id: Mapped[str] = mapped_column(String(30))
    username: Mapped[str] = mapped_column(String(100), nullable=True)
    register_date: Mapped[datetime.datetime] = mapped_column(DateTime(), nullable=True)
    fio: Mapped[str] = mapped_column(String(200), nullable=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=True)
    address: Mapped[str] = mapped_column(String(200), nullable=True)
    is_newbie: Mapped[int] = mapped_column(Integer(), default=1)

    def __str__(self):
        return f'{self.id}. {self.tg_id} {self.username or "-"}'

    def __repr__(self):
        return f'{self.id}. {self.tg_id} {self.username or "-"}'


class Item(Base):
    __tablename__ = 'items'
    id: Mapped[int] = mapped_column(primary_key=True,
                                    autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    shipping: Mapped[int] = mapped_column(Integer())

    def __str__(self):
        return f'{self.id}. {self.name} {self.shipping}'

    def __repr__(self):
        return f'{self.__class__.__name__}({self.name}, {self.shipping})'

    @staticmethod
    def menu_btn():
        _session = Session()
        q = select(Item)
        _items = session.execute(q).scalars().all()
        _buttons = {}
        for _item in _items:
            _buttons[f'{_item.name} (Доставка {_item.shipping})'] = f'item_{_item.id}'
        return _buttons


class Order(Base):
    __tablename__ = 'orders'
    id: Mapped[int] = mapped_column(primary_key=True,
                                    autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    user: Mapped["User"] = relationship(lazy='joined')
    item_id:  Mapped[int] = mapped_column(ForeignKey('items.id', ondelete='SET NULL'))
    item: Mapped["Item"] = relationship()
    status: Mapped[str] = mapped_column(String(20), default='temp')
    photo: Mapped[str] = mapped_column(LargeBinary())
    link: Mapped[str] = mapped_column(String(200))
    size: Mapped[str] = mapped_column(String(50))
    cost: Mapped[float] = mapped_column(Float(precision=2))
    pay_confirm: Mapped[str] = mapped_column(LargeBinary(), nullable=True)
    pay_date: Mapped[datetime.datetime] = mapped_column(DateTime(), nullable=True)
    manager_msg_id: Mapped[int] = mapped_column(Integer(), nullable=True)

    def __str__(self):
        return f'{self.__class__.__name__}({self.id}, {self.item_id} {self.status})'

    def __repr__(self):
        return f'{self.__class__.__name__}({self.id}, {self.item_id} {self.status})'

    def save(self):
        try:
            _session = Session()
            with _session:
                order = Order(
                    user_id=self.user_id,
                    item_id=self.item_id,
                    photo=self.photo,
                    link=self.link,
                    size=self.size,
                    cost=self.cost,
                )
                print(order)
                _session.add(order)
                _session.commit()
                logger.debug('Сохранено')
        except Exception as err:
            logger.error(f'{err}')


class BotSettings(Base):
    __tablename__ = 'bot_settings'
    id: Mapped[int] = mapped_column(primary_key=True,
                                    autoincrement=True)
    name: Mapped[str] = mapped_column(String(50))
    value: Mapped[str] = mapped_column(String(255), nullable=True, default='')
    description: Mapped[str] = mapped_column(String(500),
                                             nullable=True,
                                             default='')


class Faq(Base):
    __tablename__ = 'faq'
    id: Mapped[int] = mapped_column(primary_key=True,
                                    autoincrement=True)
    question: Mapped[str] = mapped_column(String(50))
    answer: Mapped[str] = mapped_column(String(2000))

    @staticmethod
    def menu_btn():
        _session = Session()
        q = select(Faq)
        _items = session.execute(q).scalars().all()
        _buttons = {}
        for _item in _items:
            _buttons[f'{_item.question}'] = f'answer_{_item.id}'
        _buttons['Назад'] = 'menu'
        return _buttons


if not database_exists(db_url):
    create_database(db_url)
Base.metadata.create_all(engine)

faq_start = [
    ['Вопрос 1', 'Ответ 1'],
    ['Вопрос 2', 'Ответ 2'],
    ]

session = Session()
with session:
    faqs = session.query(Faq).all()
    if not faqs:
        for item in faq_start:
            faq = Faq(
                question=item[0],
                answer=item[1],
            )
            session.add(faq)
            session.commit()

items_start = [
    ['Кроссовки', 1390],
    ['Ботинки', 1690],
    ['Футболки, шорты, аксессуары, парфюм', 590],
    ['Куртки', 1380],
    ['Джинсы, брюки, толстовки', 790],
    ['Рюкзаки, сумки', 990],
    ['Телефоны', 1690],
]

session = Session()
with session:
    items = session.query(Item).all()
    if not items:
        for item in items_start:
            item = Item(
                name=item[0],
                shipping=item[1],
            )
            session.add(item)
            session.commit()

settings_start = [
    ['tax1', 99, 'Первая комиссия'],
    ['tax2', 249, 'Обычная комиссия'],
    ['manager_id', conf.tg_bot.admin_ids[0], 'id менеджера'],
    ['pay_req', 'Реквизиты для оплаты', 'Реквизиты для оплаты'],
]
with session:
    settings = session.query(BotSettings).all()
    if not settings:
        for setting in settings_start:
            options = BotSettings(
                name=setting[0],
                value=setting[1],
            )
            session.add(options)
            session.commit()
