import os

import requests
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import filters, FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from dotenv import load_dotenv

import config

load_dotenv()

bot = Bot(token=os.getenv('BOT_TOKEN'), parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot, storage=MemoryStorage())


class ExchangeForm(StatesGroup):
    currency = State()
    amount = State()
    address = State()


def get_current_price(string_mode: bool = True):
    response = requests.get(config.CMC_API_URL, headers={
        'X-CMC_PRO_API_KEY': os.getenv('API_KEY')
    }, params={
        'symbol': 'TON',
        'convert': 'UZS'
    })
    data = response.json()

    if response.status_code != 200:
        raise Exception(data.get('status', {}).get('error_message', 'Неизвестная ошибка'))

    price = int(data['data']['TON']['quote']['UZS']['price'])

    if string_mode:
        return '{:,.0f}'.format(price)
    return price


@dp.message_handler(filters.Text(equals=['/start', config.TO_MAIN]))
async def start_handler(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(row_width=2)
    keyboard.add(*config.MAIN_KEYBOARD.values())
    await message.answer(config.START, reply_markup=keyboard)


@dp.message_handler(filters.Text(equals=config.MAIN_KEYBOARD['exchange']))
async def exchange_handler(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    keyboard.add(*config.EXCHANGE_OPTIONS_KEYBOARD)
    await message.answer('Укажите нужный тип обмена:', reply_markup=keyboard)


@dp.message_handler(filters.Text(equals=config.EXCHANGE_OPTIONS_KEYBOARD[0]))
async def exchange_options_handler(message: types.Message):
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for key, value in config.EXCHANGE_EXTRA_KEYBOARD.items():
        keyboard.add(types.InlineKeyboardButton(value, callback_data=key))
    await message.answer(config.EXCHANGE_EXTRA_MESSAGE, reply_markup=keyboard)


@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('in_'))
async def inline_keyboard_callback_handler(callback_query: types.CallbackQuery, state: FSMContext):
    currency = callback_query.data[3:]
    examples = ', '.join(config.CURRENCY_AMOUNT_EXAMPLES[currency])
    await callback_query.message.edit_reply_markup(reply_markup=None)
    await callback_query.message.answer(f'❗️ Введите желаемую сумму в {currency}:\n(Например: {examples})')
    await state.update_data(currency=currency)
    await ExchangeForm.amount.set()


@dp.message_handler(state=ExchangeForm.amount)
async def amount_processing_handler(message: types.Message, state: FSMContext):
    await message.answer('Введите адрес своего TON кошелька:')
    await state.update_data(amount=message.text)
    await ExchangeForm.address.set()


@dp.message_handler(state=ExchangeForm.address)
async def address_processing_handler(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        # currency = data.get('currency')
        amount = float(data.get('amount'))
        address = message.text

        price = get_current_price(string_mode=False)

        if amount and address:
            await message.answer(config.INVOICE_PAYMENT.format(amount, '{:,.0f}'.format(int(amount * price)), address))
            await state.finish()
        else:
            await message.answer('Что-то пошло не так, пожалуйста, попробуйте ещё раз.')


@dp.message_handler(filters.Text(equals=config.MAIN_KEYBOARD['price_calculator']))
async def price_calculator_handler(message: types.Message):
    price = get_current_price()
    await message.answer(config.PRICE_CALCULATOR.format(price))


@dp.message_handler(filters.Text(equals=config.MAIN_KEYBOARD['roulette']))
async def roulette_handler(message: types.Message):
    await message.answer(config.ROULETTE)


@dp.message_handler(filters.Text(equals=config.MAIN_KEYBOARD['bonus_account']))
async def bonus_account_handler(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    keyboard.add(*config.BONUS_ACCOUNT_KEYBOARD.values())
    await message.answer(config.BONUS_ACCOUNT, reply_markup=keyboard)


@dp.message_handler(filters.Text(equals=config.BONUS_ACCOUNT_KEYBOARD['promo_code']))
async def promo_code_handler(message: types.Message):
    await message.answer('Вы должны совершить хотя бы 1 обмен, чтобы ввести промокод.')


@dp.message_handler(filters.Text(equals=config.BONUS_ACCOUNT_KEYBOARD['withdraw_funds']))
async def withdraw_funds_handler(message: types.Message):
    await message.answer('Введите сумму, которую хотите вывести:\n\n(Минимальная сумма для вывода: 5000 UZS)')


@dp.message_handler(filters.Text(equals=config.MAIN_KEYBOARD['transaction_history']))
async def transaction_history_handler(message: types.Message):
    document = types.InputFile('history.xlsx')
    await bot.send_document(message.from_user.id, document=document)


@dp.message_handler(filters.Text(equals=config.MAIN_KEYBOARD['referral_program']))
async def referral_program_handler(message: types.Message):
    await message.answer(config.REFERRAL_PROGRAM.format(message.from_user.id))


@dp.message_handler(filters.Text(equals=config.MAIN_KEYBOARD['instructions']))
async def instructions_handler(message: types.Message):
    await message.answer(config.INSTRUCTIONS)


@dp.message_handler(filters.Text(equals=config.MAIN_KEYBOARD['support_service']))
async def support_service_handler(message: types.Message):
    await message.answer('@support')


@dp.message_handler(filters.Text(equals=config.MAIN_KEYBOARD['channel']))
async def channel_handler(message: types.Message):
    await message.answer('@channel')


@dp.message_handler(filters.Text(equals=config.MAIN_KEYBOARD['chat']))
async def chat_handler(message: types.Message):
    await message.answer('@chat')


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=False)
