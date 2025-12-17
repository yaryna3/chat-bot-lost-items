import logging
import pymysql
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters
)

# ------------------------------
# Налаштування бази даних
# ------------------------------
DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "yaryna23",
    "database": "lost_items_db",
    "port": 3306
}

# ------------------------------
# Токен твого бота
# ------------------------------
BOT_TOKEN = "7246204564:AAGUFuWxGBhRFpMiU3vVytUcM39T4d9pLuU"

# ------------------------------
# Логування
# ------------------------------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ------------------------------
# Стани ConversationHandler
# ------------------------------
CHOOSING, ADD_NAME, ADD_LOCATION, ADD_CATEGORY, ADD_DESCRIPTION, ADD_CONTACT, ADD_PHOTO, SEARCH, VIEW_CATEGORY = range(9)

# ------------------------------
# Список міст
# ------------------------------
CITIES = ["Київ", "Львів", "Одеса", "Харків", "Дніпро", "Інше"]

# ------------------------------
# Список категорій
# ------------------------------
CATEGORIES = [
    "Документи",
    "Гаманці / гроші",
    "Ключі",
    "Телефони",
    "Електроніка",
    "Тварини",
    "Одяг",
    "Прикраси",
    "Інше"
]

# ------------------------------
# Стартове меню
# ------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("Додати річ"), KeyboardButton("Знайти річ")],
        [KeyboardButton("Переглянути всі речі")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        "👋 Привіт! Вибери дію:",
        reply_markup=reply_markup
    )
    return CHOOSING

# ------------------------------
# Обробка вибору дії
# ------------------------------
async def choose_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Якщо ми у процесі перегляду всіх речей
    if context.user_data.get('step_view'):
        return await view_all(update, context)
    # Якщо ми у процесі пошуку
    if context.user_data.get('step') in ['city', 'keyword', 'search']:
        return await search_item(update, context)

    choice = update.message.text
    if choice == "Додати річ":
        await update.message.reply_text("Введи назву речі:", reply_markup=ReplyKeyboardRemove())
        return ADD_NAME
    elif choice == "Знайти річ":
        context.user_data['step'] = 'city'
        return await search_item(update, context)
    elif choice == "Переглянути всі речі":
        context.user_data['step_view'] = True
        return await view_all(update, context)
    else:
        await update.message.reply_text("Будь ласка, обери одну з кнопок.")
        return CHOOSING

# ------------------------------
# Додавання назви речі
# ------------------------------
async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    keyboard = [[KeyboardButton(city)] for city in CITIES]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        "Вибери місто, де загублена річ:",
        reply_markup=reply_markup
    )
    return ADD_LOCATION

# ------------------------------
# Додавання місця (місто)
# ------------------------------
async def add_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['location'] = update.message.text
    keyboard = [[KeyboardButton(cat)] for cat in CATEGORIES]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        "Вибери категорію речі:",
        reply_markup=reply_markup
    )
    return ADD_CATEGORY

# ------------------------------
# Додавання категорії
# ------------------------------
async def add_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['category'] = update.message.text
    await update.message.reply_text("Введи опис речі:", reply_markup=ReplyKeyboardRemove())
    return ADD_DESCRIPTION

# ------------------------------
# Додавання опису
# ------------------------------
async def add_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['description'] = update.message.text
    await update.message.reply_text("Введи контакт (можеш пропустити):")
    return ADD_CONTACT

# ------------------------------
# Додавання контакту
# ------------------------------
async def add_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    context.user_data['contact'] = text if text else None
    await update.message.reply_text("Хочеш додати фото? Якщо так, надішли його, якщо ні — напиши 'Ні'.")
    return ADD_PHOTO

# ------------------------------
# Додавання фото та збереження у базу
# ------------------------------
async def add_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = None
    if update.message.photo:
        photo_file = await update.message.photo[-1].get_file()
        photo = photo_file.file_id
    elif update.message.text.lower() == "ні":
        photo = None
    else:
        await update.message.reply_text("Будь ласка, надішли фото або напиши 'Ні'.")
        return ADD_PHOTO

    context.user_data['photo'] = photo

    try:
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO items (name, location, category, description, contact, photo)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    context.user_data['name'],
                    context.user_data['location'],
                    context.user_data['category'],
                    context.user_data['description'],
                    context.user_data['contact'],
                    context.user_data['photo']
                )
            )
            conn.commit()
        await update.message.reply_text(f"✅ Річ '{context.user_data['name']}' додано!")
    except Exception as e:
        await update.message.reply_text(f"❌ Помилка: {e}")
    finally:
        conn.close()
    return await start(update, context)

# ------------------------------
# Пошук речі
# ------------------------------
# ------------------------------
# Пошук речі (оновлений)
# ------------------------------
async def search_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get('step')

    if step == 'city':
        # Вибір міста
        keyboard = [[KeyboardButton(city)] for city in CITIES] + [[KeyboardButton("Усі міста")]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("Оберіть місто для пошуку:", reply_markup=reply_markup)
        context.user_data['step'] = 'category'  # далі обираємо категорію
        return SEARCH

    elif step == 'category':
        context.user_data['selected_city'] = update.message.text
        keyboard = [[KeyboardButton(cat)] for cat in CATEGORIES] + [[KeyboardButton("Усі категорії")]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("Оберіть категорію:", reply_markup=reply_markup)
        context.user_data['step'] = 'keyword'
        return SEARCH

    elif step == 'keyword':
        context.user_data['selected_category'] = update.message.text
        await update.message.reply_text("Введіть ключове слово для пошуку (можна пропустити):", reply_markup=ReplyKeyboardRemove())
        context.user_data['step'] = 'search'
        return SEARCH

    elif step == 'search':
        keyword = update.message.text.strip() if update.message.text.strip() else None
        city = context.user_data.get('selected_city', "Усі міста")
        category = context.user_data.get('selected_category', "Усі категорії")

        context.user_data.pop('step', None)
        context.user_data.pop('selected_city', None)
        context.user_data.pop('selected_category', None)

        words = keyword.split() if keyword else []
        query_parts = []
        params = []

        for w in words:
            query_parts.append("name LIKE %s")
            params.append(f"%{w}%")

        where_clause = " AND ".join(query_parts) if query_parts else "1"

        try:
            conn = pymysql.connect(**DB_CONFIG)
            with conn.cursor() as cursor:
                query = f"""
                    SELECT name, location, category, description, contact, photo
                    FROM items
                    WHERE (location=%s OR %s='Усі міста') AND (category=%s OR %s='Усі категорії') AND {where_clause}
                """
                params_query = [city, city, category, category] + params
                cursor.execute(query, tuple(params_query))
                results = cursor.fetchall()

            if results:
                for name, loc, cat, desc, contact, photo in results:
                    text = f"📦 {name}\n📍 {loc}\n📂 {cat}\n📝 {desc}"
                    if contact:
                        text += f"\n☎️ {contact}"
                    if photo:
                        await update.message.reply_photo(photo=photo, caption=text)
                    else:
                        await update.message.reply_text(text)
            else:
                await update.message.reply_text("😔 Нічого не знайдено.")
        finally:
            conn.close()

        return await start(update, context)

# ------------------------------
# Перегляд усіх речей
# ------------------------------
async def view_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('step_view') is True:
        keyboard = [[KeyboardButton(city)] for city in CITIES] + [[KeyboardButton("Усі міста")]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("Оберіть місто для перегляду речей:", reply_markup=reply_markup)
        context.user_data['step_view'] = "city_chosen"
        return CHOOSING

    if context.user_data.get('step_view') == "city_chosen":
        selected_city = update.message.text
        context.user_data['selected_city_view'] = selected_city

        keyboard = [[KeyboardButton(cat)] for cat in CATEGORIES] + [[KeyboardButton("Усі категорії")]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("Оберіть категорію:", reply_markup=reply_markup)
        context.user_data['step_view'] = "category_chosen"
        return CHOOSING

    if context.user_data.get('step_view') == "category_chosen":
        selected_category = update.message.text
        city = context.user_data.get('selected_city_view')
        context.user_data.pop('step_view', None)
        context.user_data.pop('selected_city_view', None)

        try:
            conn = pymysql.connect(**DB_CONFIG)
            with conn.cursor() as cursor:
                query = "SELECT name, location, category, description, contact, photo FROM items WHERE 1"
                params = []
                if city != "Усі міста":
                    query += " AND location=%s"
                    params.append(city)
                if selected_category != "Усі категорії":
                    query += " AND category=%s"
                    params.append(selected_category)

                cursor.execute(query, tuple(params))
                results = cursor.fetchall()

            if results:
                for name, loc, cat, desc, contact, photo in results:
                    text = f"📦 {name}\n📍 {loc}\n📂 {cat}\n📝 {desc}"
                    if contact:
                        text += f"\n☎️ {contact}"
                    if photo:
                        await update.message.reply_photo(photo=photo, caption=text)
                    else:
                        await update.message.reply_text(text)
            else:
                await update.message.reply_text("📭 Поки що немає доданих речей.")
        except Exception as e:
            await update.message.reply_text(f"❌ Помилка: {e}")
        finally:
            conn.close()

        return await start(update, context)

# ------------------------------
# Основна функція
# ------------------------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, choose_action)],
        states={
            CHOOSING: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_action)],
            ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
            ADD_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_location)],
            ADD_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_category)],
            ADD_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_description)],
            ADD_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_contact)],
            ADD_PHOTO: [MessageHandler((filters.PHOTO | filters.TEXT) & ~filters.COMMAND, add_photo)],
            SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_item)],
            VIEW_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, view_all)],
        },
        fallbacks=[MessageHandler(filters.COMMAND, start)]
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
