import sqlite3 as sq

db = sq.connect('cfcode.db')
cursor = db.cursor()


# Удаление таблиц из базы данных
async def delete_tables():
    cursor.execute("DROP TABLE IF EXISTS users")
    cursor.execute("DROP TABLE IF EXISTS cfcodes")
    db.commit()


# Создание таблиц в базе данных
async def create_tables():
    # Создание таблицы пользователей
    cursor.execute("CREATE TABLE IF NOT EXISTS users("
                   "user_id INTEGER PRIMARY_KEY, "  # Telegram id пользователя
                   "step TEXT, "  # Шаг, на котором находится пользователь
                   "page INTEGER, "  # Страница CF-кодов, которую пользователь просматривает
                   "text TEXT, "  # Текст, который будет сохранён в CF-коде
                   "cfcode_id TEXT, "  # Id CF-кода, с которым взаимодействует пользователь
                   "cfcode_num INTEGER)")  # Количество CF-кодов, созданных пользователем

    # Создание таблицы CF-кодов
    cursor.execute("CREATE TABLE IF NOT EXISTS cfcodes("
                   "cfcode_id TEXT PRIMARY KEY, "  # Id CF-кода
                   "cfcode_num INTEGER, " # Номер CF-кода, под которым он будет сохранен как изображение
                   "pixelate INTEGER, " # Уровень пикселизации изображения
                   "owner_id INTEGER, "  # Telegram id пользователя, создавшего CF-код
                   "text TEXT, "  # Текст CF-кода
                   "date TEXT, "  # Дата и время создания CF-кода
                   "views INTEGER)")  # Количество использований CF-кода
    db.commit()


# Добавление нового пользователя в базу данных
async def add_new_user(user_id):
    cursor.execute(f"INSERT INTO users (user_id, step, page, text, cfcode_id, cfcode_num) VALUES ({user_id}, '', 1, '', '', 0)")
    db.commit()


# Поиск пользователя в базе данных по его telegram id
async def get_user_by_id(user_id):
    user = cursor.execute(f"SELECT * FROM users WHERE user_id == {user_id}").fetchone()
    if user is None:
        return False
    res = {'user_id': None, 'step': None, 'page': None, 'text': None, 'cfcode_id': None, 'cfcode_num': None}
    res_keys = list(res.keys())
    for i in range(len(user)):
        res[res_keys[i]] = user[i]
    return res


# Изменение шага, на котором находится пользователь
async def update_user_step(user_id, step):
    cursor.execute(f"UPDATE users SET step = '{step}' WHERE user_id == {user_id}")
    db.commit()


# Изменение страницы CF-кодов пользователя
async def update_user_page(user_id, page):
    cursor.execute(f"UPDATE users SET page = {page} WHERE user_id == {user_id}")
    db.commit()


# Изменение текста, который будет сохранен в CF-коде
async def update_user_text(user_id, text):
    cursor.execute(f"UPDATE users SET text = '{text}' WHERE user_id == {user_id}")
    db.commit()


# Изменение id CF-кода, с которым взаимодействует пользователь
async def update_user_cfcode_id(user_id, cfcode_id):
    cursor.execute(f"UPDATE users SET cfcode_id = '{cfcode_id}' WHERE user_id == {user_id}")
    db.commit()


# Добавление нового CF-кода в базу данных
async def add_new_cfcode(owner_id, cfcode_id, pixelate, text, date):
    cfcode_num = cursor.execute(f"SELECT MAX(cfcode_num) FROM cfcodes").fetchone()[0]
    if cfcode_num is None:
        cfcode_num = 0
    cursor.execute(f"INSERT INTO cfcodes (cfcode_id, cfcode_num, pixelate, owner_id, text, date, views) VALUES ('{cfcode_id}', {int(cfcode_num) + 1}, {pixelate}, {owner_id}, '{text}', '{date}', 0)")
    db.commit()


# Увеличение количества CF-кодов пользователя
async def increase_cfcode_num(user_id):
    cfcode_num = cursor.execute(f"SELECT cfcode_num FROM users WHERE user_id == {user_id}").fetchone()
    cursor.execute(f"UPDATE users SET cfcode_num = {int(cfcode_num[0]) + 1} WHERE user_id == {user_id}")
    db.commit()


# Поиск CF-кода по его id
async def get_cfcode_by_id(cfcode_id):
    cfcode = cursor.execute(f"SELECT * FROM cfcodes WHERE cfcode_id == '{cfcode_id}'").fetchone()
    #print(cfcode)
    if cfcode is None:
        return None
    res = {'cfcode_id': None, 'cfcode_num': None, 'pixelate': None, 'owner_id': None, 'text': None, 'date': None, 'views': None}
    res_keys = ['cfcode_id', 'cfcode_num', 'pixelate', 'owner_id', 'text', 'date', 'views']
    for i in range(len(cfcode)):
        res[res_keys[i]] = cfcode[i]
    return res


# Поиск всех CF-кодов пользователя в базе данных по его telegram id
async def get_users_cfcodes(user_id):
    cfcodes = cursor.execute(f"SELECT * FROM cfcodes WHERE owner_id == {user_id}").fetchall()
    if cfcodes == []:
        return None
    res = []
    for cfcode in cfcodes:
        res.append({'cfcode_id': cfcode[0], 'cfcode_num': cfcode[1], 'owner_id': cfcode[3], 'text': cfcode[4], 'date': cfcode[5], 'views': cfcode[6]})
    return res


# Поиск пикселизированных CF-кодов пользователя
async def get_user_pixelate_cfcode(user_id, pixelate):
    cfcode = cursor.execute(f"SELECT * FROM cfcodes WHERE owner_id == {user_id} AND pixelate == {pixelate}").fetchone()
    if cfcode is None:
        return False
    res = {'cfcode_id': cfcode[0], 'cfcode_num': cfcode[1], 'pixelate': cfcode[2], 'owner_id': cfcode[3], 'text': cfcode[4], 'date': cfcode[5], 'views': cfcode[6]}
    return res


# Увеличение количества просмотров CF-кода
async def view_cfcode(cfcode_id):
    views = cursor.execute(f"SELECT views FROM cfcodes WHERE cfcode_id == '{cfcode_id}'").fetchone()[0]
    cursor.execute(f"UPDATE cfcodes SET views = {views + 1} WHERE cfcode_id == '{cfcode_id}'")
    db.commit()


# Изменение текста CF-кода
async def update_cfcode_text(cfcode_id, text):
    cursor.execute(f"UPDATE cfcodes SET text = '{text}' WHERE cfcode_id == '{cfcode_id}'")
    db.commit()


# Удаление CF-кода из базы данных
async def delete_cfcode(user_id, cfcode_id):
    cursor.execute(f"DELETE FROM cfcodes WHERE cfcode_id == '{cfcode_id}'")
    user = await get_user_by_id(user_id)
    cursor.execute(f'UPDATE users SET cfcode_num == {user["cfcode_num"] - 1}')
    db.commit()
