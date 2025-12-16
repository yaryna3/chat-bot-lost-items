import discord
from discord.ext import commands
import pymysql
import os

# ------------------------------
# Конфігурація
# ------------------------------
BOT_TOKEN = "MTQ0MTQyMzk3NzQ4MTUwMjc3MA.Gl9p8i.5brFApE3NaCfyzwSXgVXhvQMrvuhzg77nvaVc0"
DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "yaryna23",
    "database": "lost_items_db",
    "port": 3306
}

CITIES = ["Київ", "Львів", "Одеса", "Харків", "Дніпро", "Інше"]
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
# Ініціалізація бота
# ------------------------------
intents = discord.Intents.default()
intents.messages = True
intents.dm_messages = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ------------------------------
# Допоміжні функції для бази
# ------------------------------
def insert_item(name, location, category, description, contact, photo_url):
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO items (name, location, category, description, contact, photo) VALUES (%s,%s,%s,%s,%s,%s)",
                (name, location, category, description, contact, photo_url)
            )
            conn.commit()
    finally:
        conn.close()

def search_database(city, category, keyword=None):
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cursor:
            query = "SELECT name, location, category, description, contact, photo FROM items WHERE 1"
            params = []
            if city != "Усі міста":
                query += " AND location=%s"
                params.append(city)
            if category != "Усі категорії":
                query += " AND category=%s"
                params.append(category)
            if keyword:
                query += " AND name LIKE %s"
                params.append(f"%{keyword}%")
            cursor.execute(query, tuple(params))
            return cursor.fetchall()
    finally:
        conn.close()

# ------------------------------
# Події
# ------------------------------
@bot.event
async def on_ready():
    print(f"Бот {bot.user} підключений!")
    await bot.tree.sync()

# ------------------------------
# Команда /add
# ------------------------------
@bot.tree.command(name="add", description="Додати загублену річ")
async def add(interaction: discord.Interaction):
    user = interaction.user
    await interaction.response.send_message("Починаємо додавати річ через DM...", ephemeral=True)

    try:
        def check_msg(m): return m.author.id == user.id and isinstance(m.channel, discord.DMChannel)

        # 1️⃣ Назва
        await user.send("Введіть назву речі:")
        name_msg = await bot.wait_for("message", check=check_msg, timeout=180)
        name = name_msg.content.strip()

        # 2️⃣ Місто
        options = [discord.SelectOption(label=city) for city in CITIES]
        select = discord.ui.Select(placeholder="Оберіть місто", options=options, custom_id="city_select")
        view = discord.ui.View()
        view.add_item(select)
        await user.send("Оберіть місто:", view=view)

        def check_inter_city(interaction2):
            return interaction2.user.id == user.id and interaction2.data["custom_id"] == "city_select"
        interaction2 = await bot.wait_for("interaction", check=check_inter_city, timeout=120)
        city = interaction2.data["values"][0]
        await interaction2.response.send_message(f"Місто обране: {city}", ephemeral=True)

        # 3️⃣ Категорія
        options = [discord.SelectOption(label=cat) for cat in CATEGORIES]
        select = discord.ui.Select(placeholder="Оберіть категорію", options=options, custom_id="category_select")
        view = discord.ui.View()
        view.add_item(select)
        await user.send("Оберіть категорію:", view=view)

        def check_inter_cat(interaction3):
            return interaction3.user.id == user.id and interaction3.data["custom_id"] == "category_select"
        interaction3 = await bot.wait_for("interaction", check=check_inter_cat, timeout=120)
        category = interaction3.data["values"][0]
        await interaction3.response.send_message(f"Категорія обрана: {category}", ephemeral=True)

        # 4️⃣ Опис
        await user.send("Введіть опис речі:")
        desc_msg = await bot.wait_for("message", check=check_msg, timeout=180)
        description = desc_msg.content.strip()

        # 5️⃣ Контакт
        await user.send("Введіть контакт (можна пропустити):")
        contact_msg = await bot.wait_for("message", check=check_msg, timeout=180)
        contact = contact_msg.content.strip() if contact_msg.content.strip() else None

        # 6️⃣ Фото (URL або файл)
        await user.send("Надішліть фото (URL або файл) або напишіть 'Ні':")
        photo_msg = await bot.wait_for("message", check=check_msg, timeout=180)

        photo = None
        photo_file_path = None

        # URL
        if photo_msg.content.strip().lower() != "ні" and len(photo_msg.attachments) == 0:
            photo = photo_msg.content.strip()
        # Файл
        elif len(photo_msg.attachments) > 0:
            attachment = photo_msg.attachments[0]
            photo_file_path = f"temp_{user.id}_{attachment.filename}"
            await attachment.save(photo_file_path)

        # Збереження в БД: зберігаємо URL або None (файл відправлятимо тільки при перегляді)
        insert_item(name, city, category, description, contact, photo)

        await user.send(f"✅ Річ '{name}' успішно додана!")

        # Якщо був файл, його можна видаляти після збереження або залишити для подальшого перегляду
        if photo_file_path and os.path.exists(photo_file_path):
            os.remove(photo_file_path)

    except Exception as e:
        await user.send(f"❌ Сталася помилка: {e}")

# ------------------------------
# Команда /search
# ------------------------------
@bot.tree.command(name="search", description="Пошук загублених речей")
async def search(interaction: discord.Interaction):
    user = interaction.user
    await interaction.response.send_message("Починаємо пошук через DM...", ephemeral=True)

    try:
        def check_msg(m): return m.author.id == user.id and isinstance(m.channel, discord.DMChannel)

        # Місто
        options = [discord.SelectOption(label=city) for city in CITIES + ["Усі міста"]]
        select = discord.ui.Select(placeholder="Оберіть місто", options=options, custom_id="search_city_select")
        view = discord.ui.View()
        view.add_item(select)
        await user.send("Оберіть місто:", view=view)

        def check_inter_city(interaction2):
            return interaction2.user.id == user.id and interaction2.data["custom_id"] == "search_city_select"
        interaction2 = await bot.wait_for("interaction", check=check_inter_city, timeout=120)
        city = interaction2.data["values"][0]
        await interaction2.response.send_message(f"Місто обране: {city}", ephemeral=True)

        # Категорія
        options = [discord.SelectOption(label=cat) for cat in CATEGORIES + ["Усі категорії"]]
        select = discord.ui.Select(placeholder="Оберіть категорію", options=options, custom_id="search_category_select")
        view = discord.ui.View()
        view.add_item(select)
        await user.send("Оберіть категорію:", view=view)

        def check_inter_cat(interaction3):
            return interaction3.user.id == user.id and interaction3.data["custom_id"] == "search_category_select"
        interaction3 = await bot.wait_for("interaction", check=check_inter_cat, timeout=120)
        category = interaction3.data["values"][0]
        await interaction3.response.send_message(f"Категорія обрана: {category}", ephemeral=True)

        # Ключове слово
        await user.send("Введіть ключове слово для пошуку (можна пропустити):")
        keyword_msg = await bot.wait_for("message", check=check_msg, timeout=180)
        keyword = keyword_msg.content.strip() if keyword_msg.content.strip() else None

        # Пошук
        results = search_database(city, category, keyword)
        if results:
            for name, loc, cat, desc, contact, photo in results:
                embed = discord.Embed(title=name, description=desc, color=discord.Color.blue())
                embed.add_field(name="Місто", value=loc, inline=True)
                embed.add_field(name="Категорія", value=cat, inline=True)
                if contact:
                    embed.add_field(name="Контакт", value=contact, inline=True)
                if photo and (photo.startswith("http://") or photo.startswith("https://")):
                    embed.set_image(url=photo)
                await user.send(embed=embed)
        else:
            await user.send("😔 Нічого не знайдено.")

    except Exception as e:
        await user.send(f"❌ Сталася помилка: {e}")

# ------------------------------
# Команда /view
# ------------------------------
@bot.tree.command(name="view", description="Переглянути всі додані речі")
async def view(interaction: discord.Interaction):
    user = interaction.user
    await interaction.response.send_message("Починаємо перегляд всіх речей через DM...", ephemeral=True)

    try:
        # Місто
        options = [discord.SelectOption(label=city) for city in CITIES + ["Усі міста"]]
        select = discord.ui.Select(placeholder="Оберіть місто", options=options, custom_id="view_city_select")
        view_ui = discord.ui.View()
        view_ui.add_item(select)
        await user.send("Оберіть місто для перегляду:", view=view_ui)

        def check_inter_city(interaction2):
            return interaction2.user.id == user.id and interaction2.data["custom_id"] == "view_city_select"
        interaction2 = await bot.wait_for("interaction", check=check_inter_city, timeout=120)
        city = interaction2.data["values"][0]
        await interaction2.response.send_message(f"Місто обране: {city}", ephemeral=True)

        # Категорія
        options = [discord.SelectOption(label=cat) for cat in CATEGORIES + ["Усі категорії"]]
        select = discord.ui.Select(placeholder="Оберіть категорію", options=options, custom_id="view_category_select")
        view_ui = discord.ui.View()
        view_ui.add_item(select)
        await user.send("Оберіть категорію для перегляду:", view=view_ui)

        def check_inter_cat(interaction3):
            return interaction3.user.id == user.id and interaction3.data["custom_id"] == "view_category_select"
        interaction3 = await bot.wait_for("interaction", check=check_inter_cat, timeout=120)
        category = interaction3.data["values"][0]
        await interaction3.response.send_message(f"Категорія обрана: {category}", ephemeral=True)

        # Витяг із бази
        results = search_database(city, category)
        if results:
            for name, loc, cat, desc, contact, photo in results:
                embed = discord.Embed(title=name, description=desc, color=discord.Color.green())
                embed.add_field(name="Місто", value=loc, inline=True)
                embed.add_field(name="Категорія", value=cat, inline=True)
                if contact:
                    embed.add_field(name="Контакт", value=contact, inline=True)
                if photo and (photo.startswith("http://") or photo.startswith("https://")):
                    embed.set_image(url=photo)
                await user.send(embed=embed)
        else:
            await user.send("📭 Поки що немає доданих речей у цій категорії та місті.")

    except Exception as e:
        await user.send(f"❌ Сталася помилка: {e}")

# ------------------------------
# Запуск бота
# ------------------------------
bot.run(BOT_TOKEN)
