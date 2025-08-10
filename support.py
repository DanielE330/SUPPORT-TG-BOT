import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

file = open("ADMIN_ID.txt")
ADMIN_ID = int(file.read())
file.close()

TG_TOKEN = open("TG_TOKEN.txt")
bot = Bot(TG_TOKEN.read())
TG_TOKEN.close()

dp = Dispatcher()

support_chats = {}

def get_start_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="Помощь по возврату", callback_data="refund"),
        InlineKeyboardButton(text="Написать в поддержку", callback_data="support")
    )
    builder.adjust(1)
    return builder.as_markup()

def get_refund_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="Ozon", callback_data="ozon"),
        InlineKeyboardButton(text="Wildberries", callback_data="wb")
    )
    builder.adjust(1)
    return builder.as_markup()

@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "Добро пожаловать в поддержку! Выберите действие:",
        reply_markup=get_start_keyboard()
    )

@dp.callback_query(F.data == "refund")
async def process_refund(callback_query: CallbackQuery):
    await callback_query.message.edit_text(
        text="Выберите маркетплейс:",
        reply_markup=get_refund_keyboard()
    )

@dp.callback_query(F.data.in_(["ozon", "wb"]))
async def process_option_choice(callback_query: CallbackQuery):
    platform = "Ozon" if callback_query.data == "ozon" else "Wildberries"
    response_text = f"Инструкция по возврату для {platform}:\n\n1. Зайдите в личный кабинет\n2. Найдите раздел 'Возвраты'\n3. Следуйте инструкциям"
    await callback_query.message.edit_text(text=response_text)

@dp.callback_query(F.data == "support")
async def start_support_chat(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    support_chats[user_id] = {"status": "waiting_message"}
    await callback_query.message.edit_text(
        text="Напишите ваш вопрос в ответ на это сообщение:"
    )

@dp.message(
    F.reply_to_message,
    F.reply_to_message.text == "Напишите ваш вопрос в ответ на это сообщение:",
    lambda message: message.from_user.id in support_chats
)
async def process_user_question(message: types.Message):
    user_id = message.from_user.id
    support_chats[user_id] = {
        "status": "active",
        "user_message_id": message.message_id
    }
    
    builder = InlineKeyboardBuilder()
    builder.button(text="Ответить", callback_data=f"reply_{user_id}")
    
    admin_message = await bot.send_message(
        ADMIN_ID,
        f"Новый вопрос от @{message.from_user.username} (ID: {user_id}):\n\n{message.text}",
        reply_markup=builder.as_markup()
    )
    
    support_chats[user_id]["admin_message_id"] = admin_message.message_id
    
    await message.reply("✅ Ваш вопрос отправлен в поддержку. Ожидайте ответа.")

@dp.callback_query(F.data.startswith("reply_"))
async def prepare_admin_reply(callback_query: CallbackQuery):
    user_id = int(callback_query.data.split("_")[1])
    await callback_query.message.reply(
        f"✍️ Ответьте на это сообщение, чтобы отправить ответ пользователю {user_id}"
    )

@dp.message(
    F.from_user.id == ADMIN_ID,
    F.reply_to_message,
    lambda message: "Ответьте на это сообщение" in message.reply_to_message.text
)
async def send_admin_reply(message: types.Message):
    user_id = int(message.reply_to_message.text.split()[-1])
    
    if user_id in support_chats:
        await bot.send_message(
            user_id,
            f"📩 Ответ поддержки:\n\n{message.text}\n\nВы можете продолжить диалог, отвечая на это сообщение."
        )
        
        support_chats[user_id]["status"] = "waiting_user_reply"
        
        await message.reply("✅ Ваш ответ отправлен пользователю.")

@dp.message(
    F.reply_to_message,
    lambda message: "📩 Ответ поддержки:" in message.reply_to_message.text,
    lambda message: message.from_user.id in support_chats
)
async def process_user_followup(message: types.Message):
    user_id = message.from_user.id
    
    builder = InlineKeyboardBuilder()
    builder.button(text="Ответить", callback_data=f"reply_{user_id}")
    
    await bot.send_message(
        ADMIN_ID,
        f"🔹 Пользователь @{message.from_user.username} (ID: {user_id}) ответил:\n\n{message.text}",
        reply_markup=builder.as_markup()
    )
    
    await message.reply("✅ Ваше сообщение отправлено в поддержку.")

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())