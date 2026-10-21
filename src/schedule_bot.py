import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# --- Настройки ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
GROUP_NAME = "НТТС2-261-ОС"
SCHEDULE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "schedule.json")
MSK = ZoneInfo("Europe/Moscow")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s")
log = logging.getLogger("bot")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=None))
dp = Dispatcher()

# --- Загрузка расписания ---
def load_schedule():
    try:
        with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.error(f"Ошибка загрузки расписания: {e}")
        return {}

# --- Клавиатуры ---
def get_main_keyboard():
    """Создаёт главное меню с кнопками."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 Сегодня", callback_data="schedule_today"),
            InlineKeyboardButton(text="📆 Завтра", callback_data="schedule_tomorrow")
        ],
        [
            InlineKeyboardButton(text="🗓 Выбрать дату", callback_data="select_month")
        ],
        [
            InlineKeyboardButton(text="📊 На неделю", callback_data="schedule_week")
        ]
    ])
    return keyboard

def get_month_keyboard():
    """Создаёт клавиатуру для выбора месяца."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    
    months = [
        ("Январь", "01"), ("Февраль", "02"), ("Март", "03"),
        ("Апрель", "04"), ("Май", "05"), ("Июнь", "06"),
        ("Июль", "07"), ("Август", "08"), ("Сентябрь", "09"),
        ("Октябрь", "10"), ("Ноябрь", "11"), ("Декабрь", "12")
    ]
    
    current_year = datetime.now(MSK).year
    
    # Создаём сетку 3x4
    row = []
    for i, (name, num) in enumerate(months):
        row.append(InlineKeyboardButton(text=name, callback_data=f"month_{current_year}_{num}"))
        if (i + 1) % 3 == 0:
            keyboard.inline_keyboard.append(row)
            row = []
    
    if row:
        keyboard.inline_keyboard.append(row)
    
    # Кнопка назад
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")
    ])
    
    return keyboard

def get_day_keyboard(year, month):
    """Создаёт клавиатуру для выбора дня в месяце."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    
    # Получаем количество дней в месяце
    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)
    last_day = (next_month - timedelta(days=1)).day
    
    # Создаём сетку 7x5 (дни недели)
    row = []
    for day in range(1, last_day + 1):
        date_str = f"{year}-{month:02d}-{day:02d}"
        row.append(InlineKeyboardButton(text=str(day), callback_data=f"day_{date_str}"))
        
        if day % 7 == 0:
            keyboard.inline_keyboard.append(row)
            row = []
    
    if row:
        keyboard.inline_keyboard.append(row)
    
    # Кнопка назад
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="select_month")
    ])
    
    return keyboard

# --- Форматирование расписания ---
def format_schedule_for_date(date_str: str, schedule_data: dict):
    """Форматирует расписание для конкретной даты."""
    if date_str not in schedule_data:
        return f"📅 На {date_str} пар нет или расписание не загружено."
    
    lessons = schedule_data[date_str]
    if not lessons:
        return f"📅 На {date_str} пар нет. 🎉"
    
    lines = [f"📅 Расписание на {date_str}:"]
    for lesson in lessons:
        time = lesson.get("time", "")
        subject = lesson.get("subject", "")
        room = lesson.get("room", "")
        teacher = lesson.get("teacher", "")
        
        parts = [f"⏰ {time}", subject]
        if room:
            parts.append(f"📍 {room}")
        if teacher:
            parts.append(f"👤 {teacher}")
        
        lines.append(" | ".join(parts))
    
    return "\n".join(lines)

def format_schedule_for_week(schedule_data: dict):
    """Форматирует расписание на неделю."""
    today = datetime.now(MSK)
    monday = today - timedelta(days=today.weekday())
    
    lines = [f"📅 Расписание на неделю (с {monday.strftime('%d.%m.%Y')}):"]
    
    for i in range(7):
        date = monday + timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        day_name = date.strftime("%A")
        
        if date_str in schedule_data:
            lessons = schedule_data[date_str]
            if lessons:
                lines.append(f"\n📆 {date_str} ({day_name}):")
                for lesson in lessons:
                    time = lesson.get("time", "")
                    subject = lesson.get("subject", "")
                    room = lesson.get("room", "")
                    lines.append(f"  {time} | {subject} | {room}")
            else:
                lines.append(f"\n📆 {date_str} ({day_name}): пар нет")
        else:
            lines.append(f"\n📆 {date_str} ({day_name}): нет данных")
    
    return "\n".join(lines)

# --- Обработчики команд ---
@dp.message(CommandStart())
async def cmd_start(msg: types.Message):
    await msg.answer(
        f"👋 Привет! Я бот расписания для группы {GROUP_NAME}.\n\n"
        "Выберите действие:",
        reply_markup=get_main_keyboard()
    )

@dp.message(Command("menu"))
async def cmd_menu(msg: types.Message):
    """Показать главное меню."""
    await msg.answer("Главное меню:", reply_markup=get_main_keyboard())

@dp.message(Command("today"))
async def cmd_today(msg: types.Message):
    today = datetime.now(MSK).strftime("%Y-%m-%d")
    schedule = load_schedule()
    await msg.answer(format_schedule_for_date(today, schedule), reply_markup=get_main_keyboard())

@dp.message(Command("tomorrow"))
async def cmd_tomorrow(msg: types.Message):
    tomorrow = (datetime.now(MSK) + timedelta(days=1)).strftime("%Y-%m-%d")
    schedule = load_schedule()
    await msg.answer(format_schedule_for_date(tomorrow, schedule), reply_markup=get_main_keyboard())

@dp.message(Command("week"))
async def cmd_week(msg: types.Message):
    schedule = load_schedule()
    await msg.answer(format_schedule_for_week(schedule), reply_markup=get_main_keyboard())

@dp.message(Command("date"))
async def cmd_date(msg: types.Message):
    """Показать календарь для выбора даты."""
    await msg.answer("Выберите месяц:", reply_markup=get_month_keyboard())

@dp.message(Command("update"))
async def cmd_update(msg: types.Message):
    """Команда для обновления расписания (перезагрузка из файла)."""
    ADMIN_ID = os.getenv("ADMIN_ID")
    if ADMIN_ID and str(msg.from_user.id) != ADMIN_ID:
        await msg.answer("❌ У вас нет прав для этой команды.")
        return
    
    try:
        schedule = load_schedule()
        await msg.answer(f"✅ Расписание обновлено. Загружено {len(schedule)} дней.", reply_markup=get_main_keyboard())
    except Exception as e:
        await msg.answer(f"❌ Ошибка обновления: {e}")

# --- Обработчики callback кнопок ---
@dp.callback_query()
async def callback_handler(query: CallbackQuery):
    """Обработчик всех callback кнопок."""
    data = query.data
    schedule = load_schedule()
    
    if data == "schedule_today":
        date_str = datetime.now(MSK).strftime("%Y-%m-%d")
        await query.message.edit_text(format_schedule_for_date(date_str, schedule), reply_markup=get_main_keyboard())
    elif data == "schedule_tomorrow":
        date_str = (datetime.now(MSK) + timedelta(days=1)).strftime("%Y-%m-%d")
        await query.message.edit_text(format_schedule_for_date(date_str, schedule), reply_markup=get_main_keyboard())
    elif data == "schedule_week":
        await query.message.edit_text(format_schedule_for_week(schedule), reply_markup=get_main_keyboard())
    elif data == "select_month":
        await query.message.edit_text("Выберите месяц:", reply_markup=get_month_keyboard())
    elif data.startswith("month_"):
        _, year, month = data.split("_")
        await query.message.edit_text(f"Выберите день ({month}.{year}):", reply_markup=get_day_keyboard(int(year), int(month)))
    elif data.startswith("day_"):
        date_str = data.split("_")[1]
        await query.message.edit_text(format_schedule_for_date(date_str, schedule), reply_markup=get_main_keyboard())
    elif data == "back_to_main":
        await query.message.edit_text("Главное меню:", reply_markup=get_main_keyboard())
    
    await query.answer()

# --- Запуск бота ---
async def main():
    log.info("Бот расписания запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
