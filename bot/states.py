from aiogram.fsm.state import State, StatesGroup


class Reg(StatesGroup):
    waiting_nickname = State()
    waiting_age = State()
    waiting_fantasy = State()


class Chat(StatesGroup):
    active = State()


class AdminSearch(StatesGroup):
    waiting_query = State()
