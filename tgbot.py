from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup
from PIL import Image
import requests
import datetime
import random
import io
import os
from dotenv import load_dotenv
import cfcode as cf
import database as db

load_dotenv()

# Токен телеграм бота
BOT_TOKEN = os.getenv('BOT_TOKEN')
bot = Bot(BOT_TOKEN)
uri = f'https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id='
uri_img = f'https://api.telegram.org/file/bot{BOT_TOKEN}/'
dp = Dispatcher(bot)


# Функция для создания ReplyKeyboardMarkup
def make_keyboard(arr):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for elem in arr:
        keyboard.add(elem)
    return keyboard


# Функция, вызываемая при запуске бота
async def on_startup(_):
    #await db.delete_tables()
    await db.create_tables()


# Кнопка /start
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.answer(f'Привет, это бот, с помощью которого ты сможешь считывать и генерировать CF-кода\n'
                         f'Данный проект является лишь небольшим прототипом, основной концепции, в соответствии с чем '
                         f'далек от идеала и имеет возможность претерпевать различные изменения\nПри использовании, '
                         f'помни, что я всего на всего бедный школьник с незаурядными знаниями в программировании, '
                         f'будь вежлив и милосерден\nВыбери действие, чтобы продолжить',
                         reply_markup=make_keyboard(['Считать CF-код', 'Мои CF-кода']))


# Обработка получаемых изображений
@dp.message_handler(content_types=['photo'])
async def cmd_photo(message: types.Message):
    # Получение информации о пользователе из базы данных
    user = await db.get_user_by_id(message.chat.id)
    # Занесение пользователя в базу данных, если его там нет
    if user is False:
        await db.add_new_user(message.chat.id)
        user = await db.get_user_by_id(message.chat.id)

    # Считать CF-код на изображении
    if user['step'].split()[:2] == ['read', 'image'] and len(user['step'].split()) == 4:
        res = requests.get(uri + message.photo[-1].file_id)
        img_path = res.json()['result']['file_path']
        img = requests.get(uri_img + img_path)
        img = Image.open(io.BytesIO(img.content))
        res = await cf.detect_code(img, int(user['step'].split()[2]), int(user['step'].split()[3]))
        if res is None:
            await message.answer('Не удалось считать CF-код, попробуй сделать другую фотографию', reply_markup=make_keyboard(['Меню', 'Назад']))
        else:
            result = await db.get_cfcode_by_id(f'{res[1]} {res[2]} {res[0]}')
            if result is not None:
                await db.view_cfcode(f'{res[1]} {res[2]} {res[0]}')
                await message.answer(result['text'], reply_markup=make_keyboard(['Меню', 'Назад']))
                return
            await message.answer('Не удалось найти CF-код в базе данных', reply_markup=make_keyboard(['Меню', 'Назад']))

    # Загрузить готовое изображение
    elif user['step'].split()[:2] == ['import', 'image'] and len(user['step'].split()) == 4:
        res = requests.get(uri + message.photo[-1].file_id)
        img_path = res.json()['result']['file_path']
        img = requests.get(uri_img + img_path)
        img = Image.open(io.BytesIO(img.content))
        res = await cf.detect_code(img, int(user['step'].split()[2]), int(user['step'].split()[3]))
        if res is None:
            await message.answer('Не удалось считать CF-код, попробуй отправить другую фотографию')
        elif await db.get_cfcode_by_id(f'{res[1]} {res[2]} {res[0]}') is None:
            offset = datetime.timezone(datetime.timedelta(hours=3))
            date = datetime.datetime.now(offset)
            await db.add_new_cfcode(message.chat.id, f'{res[1]} {res[2]} {res[0]}', 0, user['text'], str(date)[:19])
            await db.increase_cfcode_num(message.chat.id)
            cfcode_num = await cf.generate_code(res[0], res[1], res[2], False)
            await db.update_user_step(message.chat.id, '')
            await db.update_user_text(message.chat.id, '')
            photo = open(f'images//{cfcode_num}.png', 'rb')
            await bot.send_photo(message.chat.id, photo=photo, caption='CF-код добавлен, убедитесь в правильности считывания', reply_markup=make_keyboard(['Считать CF-код', 'Мои CF-кода']))
            photo.close()
        else:
            await message.answer('Данный CF-код уже использован, попробуй другой', reply_markup=make_keyboard(['Меню', 'Назад']))

    # Пикселизировать изображение
    elif user['step'] == 'pixelate image':
        await db.update_user_step(message.chat.id, 'pixelate choose')
        res = requests.get(uri + message.photo[-1].file_id)
        img_path = res.json()['result']['file_path']
        img = requests.get(uri_img + img_path)
        img = Image.open(io.BytesIO(img.content))
        img16 = await cf.pixelate(img, 16)
        img24 = await cf.pixelate(img, 24)
        img32 = await cf.pixelate(img, 32)
        await cf.generate_code(img16[0], img16[1], img16[2], False, user_id=message.chat.id, pixelate=16)
        await cf.generate_code(img24[0], img24[1], img24[2], False, user_id=message.chat.id, pixelate=24)
        await cf.generate_code(img32[0], img32[1], img32[2], False, user_id=message.chat.id, pixelate=32)
        photo16 = open(f'images//pixelate {16} {message.chat.id}.png', 'rb')
        if await db.get_cfcode_by_id(f'{message.chat.id} {img16[1]} {img16[2]} {img16[0]}') is not None:
            await db.delete_cfcode(message.chat.id, f'{message.chat.id} {img16[1]} {img16[2]} {img16[0]}')
        await db.add_new_cfcode(message.chat.id, f'{message.chat.id} {img16[1]} {img16[2]} {img16[0]}', 16, user['text'], '0')
        await bot.send_photo(message.chat.id, photo=photo16, caption='1 уровень пикселизации', reply_markup=make_keyboard(['1', '2', '3']))
        photo24 = open(f'images//pixelate {24} {message.chat.id}.png', 'rb')
        if await db.get_cfcode_by_id(f'{message.chat.id} {img24[1]} {img24[2]} {img24[0]}') is not None:
            await db.delete_cfcode(message.chat.id, f'{message.chat.id} {img24[1]} {img24[2]} {img24[0]}')
        await db.add_new_cfcode(message.chat.id, f'{message.chat.id} {img24[1]} {img24[2]} {img24[0]}', 24, user['text'], '0')
        await bot.send_photo(message.chat.id, photo=photo24, caption='2 уровень пикселизации', reply_markup=make_keyboard(['1', '2', '3']))
        photo32 = open(f'images//pixelate {32} {message.chat.id}.png', 'rb')
        if await db.get_cfcode_by_id(f'{message.chat.id} {img32[1]} {img32[2]} {img32[0]}') is not None:
            await db.delete_cfcode(message.chat.id, f'{message.chat.id} {img32[1]} {img32[2]} {img32[0]}')
        await db.add_new_cfcode(message.chat.id, f'{message.chat.id} {img32[1]} {img32[2]} {img32[0]}', 32, user['text'], '0')
        await bot.send_photo(message.chat.id, photo=photo32, caption='3 уровень пикселизации', reply_markup=make_keyboard(['1', '2', '3']))
        await message.answer('Выбери уровень пикселизации', reply_markup=make_keyboard(['1', '2', '3', 'Меню', 'Назад']))
        photo16.close()
        photo24.close()
        photo32.close()

    else:
        await message.answer('Неизвестная команда', reply_markup=make_keyboard(['Меню', 'Назад']))


# Функция отображения моих CF-кодов
async def pages(message):
    cfcodes = await db.get_users_cfcodes(message.chat.id)
    user = await db.get_user_by_id(message.chat.id)
    if cfcodes is None:
        await message.answer('У тебя еще нет CF-кодов, но ты можешь их сгенерировать', reply_markup=make_keyboard(
            ['Сгенерировать случайный', 'Загрузить изображение', 'Создать CF-код', 'Назад']))
    else:
        for i in range(len(cfcodes[(user['page'] - 1) * 5: user['page'] * 5])):
            photo = open(f'images//{cfcodes[(user["page"] - 1) * 5 + i]["cfcode_num"]}.png', 'rb')
            await bot.send_photo(message.chat.id, photo=photo, caption=f'{(user["page"] - 1) * 5 + i + 1}. Текст: {cfcodes[(user["page"] - 1) * 5 + i]["text"]}\nИспользований: {cfcodes[(user["page"] - 1) * 5 + i]["views"]}\nДата создания: {cfcodes[(user["page"] - 1) * 5 + i]["date"]}')
            photo.close()

        if len(cfcodes) > user['page'] * 5 and user['page'] != 1:
            await message.answer(f'Страница {user["page"]} из {(len(cfcodes) + 4) // 5}', reply_markup=make_keyboard(['Следующая страница', 'Предыдущая страница', 'Редактировать CF-код', 'Создать новый', 'Назад']))
        elif user['page'] != 1:
            await message.answer(f'Страница {user["page"]} из {(len(cfcodes) + 4) // 5}', reply_markup=make_keyboard(['Предыдущая страница', 'Редактировать CF-код', 'Создать новый', 'Назад']))
        elif len(cfcodes) > user['page'] * 5:
            await message.answer(f'Страница {user["page"]} из {(len(cfcodes) + 4) // 5}', reply_markup=make_keyboard(['Следующая страница', 'Редактировать CF-код', 'Создать новый', 'Назад']))
        else:
            await message.answer(f'Страница {user["page"]} из {(len(cfcodes) + 4) // 5}', reply_markup=make_keyboard(['Редактировать CF-код', 'Создать новый', 'Назад']))


commands = ['следующая страница', 'предыдущая страница', 'редактировать CF-код', 'создать новый', 'считать CF-код', 'мои CF-кода', 'меню', 'изменить текст', 'удалить CF-код']


# Обработка получаемых сообщений
@dp.message_handler()
async def cmd_text(message: types.Message):
    # Получение информации о пользователе из базы данных
    user = await db.get_user_by_id(message.chat.id)
    # Занесение пользователя в базу данных, если его там нет
    if user is False:
        await db.add_new_user(message.chat.id)
        user = await db.get_user_by_id(message.chat.id)

    # Кнопка Меню
    if message.text.lower() == 'меню':
        # Обнуление всех переменных, связанных с работой бота
        await db.update_user_step(message.chat.id, '')
        await db.update_user_text(message.chat.id, '')
        await db.update_user_page(message.chat.id, 0)
        await db.update_user_cfcode_id(message.chat.id, '')
        await message.answer('Выбери действие, чтобы продолжить', reply_markup=make_keyboard(['Считать CF-код', 'Мои CF-кода']))

    # Кнопка Назад
    elif message.text.lower() == 'назад':
        if user['step'] == '':
            await message.answer('Выбери действие, чтобы продолжить', reply_markup=make_keyboard(['Считать CF-код', 'Мои CF-кода']))
        elif user['step'] in ['read image size', 'page', 'edit']:
            await db.update_user_step(message.chat.id, '')
            await message.answer('Выбери действие, чтобы продолжить', reply_markup=make_keyboard(['Считать CF-код', 'Мои CF-кода']))
        elif user['step'].split()[:2] == ['read', 'image']:
            await db.update_user_step(message.chat.id, 'read image size')
            await message.answer('Введи размер CF-кода, указанный под ним, разделяя числа пробелом', reply_markup=make_keyboard(['Меню', 'Назад']))
        elif user['step'] == 'read image size':
            await db.update_user_step(message.chat.id, '')
            await message.answer('Выбери действие, чтобы продолжить', reply_markup=make_keyboard(['Считать CF-код', 'Мои CF-кода']))
        elif user['step'] == 'image choose' or user['step'] == 'text':
            await db.update_user_step(message.chat.id, '')
            await message.answer('Выбери действие, чтобы продолжить', reply_markup=make_keyboard(
                ['Сгенерировать случайный', 'Загрузить изображение', 'Создать CF-код', 'Меню', 'Назад']))
        elif user['step'] == 'pixelate choose':
            await db.update_user_step(message.chat.id, 'pixelate image')
            await message.answer('Отправь изображение для пикселизации', reply_markup=make_keyboard(['Меню', 'Назад']))
        elif user['step'] == 'generate random':
            await db.update_user_page(message.chat.id, 1)
            await db.update_user_step(message.chat.id, 'page')
            await pages(message)
        elif user['step'] == 'pixelate image':
            await db.update_user_step(message.chat.id, 'pixelate text')
            await message.answer('Отправь текст, который будет отображаться при сканировании CF-кода', reply_markup=make_keyboard(['Меню', 'Назад']))
        elif user['step'] == 'pixelate text':
            await db.update_user_step(message.chat.id, 'image choose')
            await message.answer('Выбери действие, чтобы продолжить', reply_markup=make_keyboard(['Загрузить готовое', 'Пикселизировать', 'Назад']))
        elif user['step'] == 'editing':
            await db.update_user_step(message.chat.id, 'edit')
            await message.answer('Укажите номер CF-кода для редактирования (номер CF-кода указан под фотографией)')
        elif user['step'] == 'delete':
            cfcode = await db.get_cfcode_by_id(user['cfcode_id'])
            await db.update_user_step(message.chat.id, 'editing')
            photo = open(f'images//{cfcode["cfcode_num"]}.png', 'rb')
            await bot.send_photo(message.chat.id, photo=photo, caption='Выберите действие, чтобы продолжить', reply_markup=make_keyboard(['Изменить текст', 'Удалить CF-код', 'Меню', 'Назад']))
            photo.close()
        elif user['step'].split()[:2] == ['import', 'image']:
            await db.update_user_step(message.chat.id, 'image choose')
            await message.answer('Выбери действие, чтобы продолжить',  reply_markup=make_keyboard(['Загрузить готовое', 'Пикселизировать', 'Назад']))
        elif user['step'] == 'import text':
            await db.update_user_step(message.chat.id, 'image choose')
            await message.answer('Выбери действие, чтобы продолжить', reply_markup=make_keyboard(['Загрузить готовое', 'Пикселизировать', 'Назад']))


    # Кнопка Считать CF-код
    elif message.text.lower() == 'считать cf-код':
        await db.update_user_step(message.chat.id, 'read image size')
        await message.answer('Введи размер CF-кода, указанный под ним, разделяя числа пробелом', reply_markup=make_keyboard(['Меню', 'Назад']))

    # Ввод размера CF-кода
    elif user['step'] == 'read image size' and message.text.lower() not in commands:
        if message.text.count(' ') == 1 and message.text.split()[0].isnumeric() and message.text.split()[1].isnumeric():
            await db.update_user_step(message.chat.id, f'read image {message.text}')
            await message.answer('Отправь изобрежение с CF-кодом, предварительно его обрезав по белой окантовке', reply_markup=make_keyboard(['Меню', 'Назад']))
        else:
            await message.answer('Неверно указан размер, попробуй снова', reply_markup=make_keyboard(['Меню', 'Назад']))

    # Кнопка Мои CF-кода
    elif message.text.lower() == 'мои cf-кода':
        await db.update_user_page(message.chat.id, 1)
        await db.update_user_step(message.chat.id, 'page')
        await pages(message)

    # Кнопка Следующая страница
    elif user['step'] == 'page' and message.text.lower() == 'следующая страница' and user['cfcode_num'] >= user['page'] * 5:
        await db.update_user_page(message.chat.id, user['page'] + 1)
        await pages(message)

    # Кнопка Предыдущая страница
    elif user['step'] == 'page' and message.text.lower() == 'предыдущая страница' and user['page'] - 1 != 0:
        await db.update_user_page(message.chat.id, user['page'] - 1)
        await pages(message)

    # Кнопка Редактировать CF-код
    elif message.text.lower() == 'редактировать cf-код':
        await db.update_user_step(message.chat.id, 'edit')
        await message.answer('Укажи номер CF-кода для редактирования (номер CF-кода указан под фотографией)')

    # Ввод номера CF-кода для редактирования
    elif user['step'] == 'edit' and message.text.lower() not in commands:
        if not (message.text.isnumeric()) or int(message.text) < 1 or int(message.text) > user['cfcode_num']:
            await message.answer('Некорректный номер CF-кода, попробуй снова')
        else:
            cfcode = await db.get_users_cfcodes(message.chat.id)
            cfcode = cfcode[int(message.text) - 1]
            await db.update_user_cfcode_id(message.chat.id, cfcode['cfcode_id'])
            await db.update_user_step(message.chat.id, 'editing')
            photo = open(f'images//{cfcode["cfcode_num"]}.png', 'rb')
            await bot.send_photo(message.chat.id, photo=photo, caption='Выбери действие, чтобы продолжить', reply_markup=make_keyboard(['Изменить текст', 'Удалить CF-код', 'Меню', 'Назад']))
            photo.close()

    # Кнопка Изменить текст
    elif user['step'] == 'editing' and message.text.lower() == 'изменить текст':
        await db.update_user_step(message.chat.id, 'editing text')
        await message.answer('Отправь новый текст, который будет отображаться при сканировании CF-кода')

    # Изменение текста CF-кода
    elif user['step'] == 'editing text' and message.text.lower() not in commands:
        await db.update_cfcode_text(user['cfcode_id'], message.text)
        await db.update_user_step(message.chat.id, '')
        await message.answer('Текст успешно изменен', reply_markup=make_keyboard(['Считать CF-код', 'Мои CF-кода']))

    # Кнопка Удалить CF-код
    elif user['step'] == 'editing' and message.text.lower() == 'удалить cf-код':
        await db.update_user_step(message.chat.id, 'delete')
        await message.answer('Ты уверен, что хочешь удалить CF-код?', reply_markup=make_keyboard(['Да', 'Нет', 'Меню', 'Назад']))

    # Удаление CF-кода
    elif user['step'] == 'delete' and message.text.lower() == 'да':
        cfcode = await db.get_cfcode_by_id(user['cfcode_id'])
        await db.delete_cfcode(message.chat.id, user['cfcode_id'])
        os.remove(f'images//{cfcode["cfcode_num"]}.png')
        await db.update_user_step(message.chat.id, '')
        await message.answer('CF-код удален', reply_markup=make_keyboard(['Считать CF-код', 'Мои CF-кода']))

    elif user['step'] == 'delete' and message.text.lower() == 'нет':
        await db.update_user_step(message.chat.id, '')
        await message.answer('Выберите действие, чтобы продолжить', reply_markup=make_keyboard(['Считать CF-код', 'Мои CF-кода']))

    # Кнопка Создать новый
    elif message.text.lower() == 'создать новый':
        await db.update_user_step(message.chat.id, '')
        await message.answer('Выбери действие, чтобы продолжить', reply_markup=make_keyboard(['Сгенерировать случайный', 'Загрузить изображение', 'Создать CF-код', 'Меню', 'Назад']))

    # Кнопка Сгенерировать случайный
    elif message.text.lower() == 'сгенерировать случайный':
        await db.update_user_step(message.chat.id, 'generate random')
        await message.answer('Отправь текст, который будет отображаться при сканировании CF-кода')

    # Генерация случайного CF-кода
    elif user['step'] == 'generate random' and message.text.lower() not in commands:
        w = random.randint(3, 10)
        h = random.randint(2, w - 1)
        n = "".join(random.choices('0123456', k=h * w))
        while await db.get_cfcode_by_id(n) is not None:
            n = "".join(random.choices('0123456', k=h * w))
        offset = datetime.timezone(datetime.timedelta(hours=3))
        date = datetime.datetime.now(offset)
        await db.add_new_cfcode(message.chat.id, f'{h} {w} {await cf.convert_to(n, 7, 64)}', 0, message.text, str(date)[:19])
        await db.increase_cfcode_num(message.chat.id)
        image = await cf.generate_code(await cf.convert_to(n, 7, 64), h, w, False, None, False)
        photo = open(f'images//{image}.png', 'rb')
        await db.update_user_step(message.chat.id, '')
        await bot.send_photo(message.chat.id, photo=photo, caption='Твой сгенерированный CF-код', reply_markup=make_keyboard(['Считать CF-код', 'Мои CF-кода']))
        photo.close()

    # Кнопка Загрузить изображение
    elif message.text.lower() == 'загрузить изображение':
        await db.update_user_step(message.chat.id, 'image choose')
        await message.answer('Выбери действие, чтобы продолжить', reply_markup=make_keyboard(['Загрузить готовое', 'Пикселизировать', 'Назад']))

    # Кнопка Загрузить готовое
    elif user['step'] == 'image choose' and message.text.lower() == 'загрузить готовое':
        await db.update_user_step(message.chat.id, 'import text')
        await message.answer('Отправь текст, который будет отображаться при сканировании CF-кода', reply_markup=make_keyboard(['Назад']))

    # Ввод текста CF-кода
    elif user['step'] == 'import text' and message.text.lower() not in commands:
        await db.update_user_step(message.chat.id, 'import image')
        await db.update_user_text(message.chat.id, message.text)
        await message.answer('Введи размер CF-кода, указанный под ним, разделяя числа пробелом')

    # Ввод размера CF-кода
    elif user['step'] == 'import image' and message.text.lower() not in commands:
        if message.text.count(' ') == 1 and message.text.split()[0].isnumeric() and message.text.split()[1].isnumeric():
            await db.update_user_step(message.chat.id, f'import image {message.text}')
            await message.answer('Отправь готовое изображение, содержащее CF-код')
        else:
            await message.answer('Неверно указан размер, попробуй снова', reply_markup=make_keyboard(['Назад']))

    # Кнока Пикселизировать
    elif user['step'] == 'image choose' and message.text.lower() == 'пикселизировать':
        await db.update_user_step(message.chat.id, 'pixelate text')
        await message.answer('С помощью этой функции ты сможешь создать CF-код посредством пикселизации своего изображения\nОтправь текст, который будет отображаться при сканировании CF-кода', reply_markup=make_keyboard(['Меню', 'Назад']))

    # Ввод текста CF-кода для пикселизации
    elif user['step'] == 'pixelate text' and message.text.lower() not in commands:
        await db.update_user_step(message.chat.id, 'pixelate image')
        await db.update_user_text(message.chat.id, message.text)
        await message.answer('Отправь изображение для пикселизации', reply_markup=make_keyboard(['Меню', 'Назад']))

    # Выбор нужного пикселизированного изображения
    elif user['step'] == 'pixelate choose' and message.text.lower() not in commands:
        if message.text in ['1', '2', '3']:
            await db.update_user_step(message.chat.id, '')
            await db.increase_cfcode_num(message.chat.id)
            cfcode16 = await db.get_user_pixelate_cfcode(message.chat.id, 16)
            cfcode24 = await db.get_user_pixelate_cfcode(message.chat.id, 24)
            cfcode32 = await db.get_user_pixelate_cfcode(message.chat.id, 32)
            await db.delete_cfcode(message.chat.id, cfcode16['cfcode_id'])
            await db.delete_cfcode(message.chat.id, cfcode24['cfcode_id'])
            await db.delete_cfcode(message.chat.id, cfcode32['cfcode_id'])
            os.remove(f'images//pixelate 16 {message.chat.id}.png')
            os.remove(f'images//pixelate 24 {message.chat.id}.png')
            os.remove(f'images//pixelate 32 {message.chat.id}.png')
            offset = datetime.timezone(datetime.timedelta(hours=3))
            date = datetime.datetime.now(offset)
            if message.text == '1':
                if await db.get_cfcode_by_id(' '.join(cfcode16['cfcode_id'].split()[1:])) is None:
                    await db.add_new_cfcode(message.chat.id, ' '.join(cfcode16['cfcode_id'].split()[1:]), 0, user['text'], str(date)[:19])
                    image = await cf.generate_code(cfcode16['cfcode_id'].split()[-1], int(cfcode16['cfcode_id'].split()[-3]), int(cfcode16['cfcode_id'].split()[-2]), False, None, False)
                    await db.update_user_step(message.chat.id, '')
                    photo16 = open(f'images//{image}.png', 'rb')
                    await bot.send_photo(message.chat.id, photo=photo16, caption='Твой пикселизированный CF-код', reply_markup=make_keyboard(['Считать CF-код', 'Мои CF-кода']))
                    photo16.close()
                else:
                    await db.update_user_step(message.chat.id, 'pixelate image')
                    await message.answer('Данный код уже использован, отправь другое изображение', reply_markup=make_keyboard(['Меню', 'Назад']))
            elif message.text == '2':
                if await db.get_cfcode_by_id(' '.join(cfcode24['cfcode_id'].split()[1:])) is None:
                    await db.add_new_cfcode(message.chat.id, ' '.join(cfcode24['cfcode_id'].split()[1:]), 0, user['text'], str(date)[:19])
                    image = await cf.generate_code(cfcode24['cfcode_id'].split()[-1], int(cfcode24['cfcode_id'].split()[-3]), int(cfcode24['cfcode_id'].split()[-2]), False, None, False)
                    await db.update_user_step(message.chat.id, '')
                    photo24 = open(f'images//{image}.png', 'rb')
                    await bot.send_photo(message.chat.id, photo=photo24, caption='Твой пикселизированный CF-код', reply_markup=make_keyboard(['Считать CF-код', 'Мои CF-кода']))
                    photo24.close()
                else:
                    await db.update_user_step(message.chat.id, 'pixelate image')
                    await message.answer('Данный код уже использован, отправь другое изображение', reply_markup=make_keyboard(['Меню', 'Назад']))
            else:
                if await db.get_cfcode_by_id(' '.join(cfcode32['cfcode_id'].split()[1:])) is None:
                    await db.add_new_cfcode(message.chat.id, ' '.join(cfcode32['cfcode_id'].split()[1:]), 0, user['text'], str(date)[:19])
                    image = await cf.generate_code(cfcode32['cfcode_id'].split()[-1], int(cfcode32['cfcode_id'].split()[-3]), int(cfcode32['cfcode_id'].split()[-2]), False, None, False)
                    await db.update_user_step(message.chat.id, '')
                    photo32 = open(f'images//{image}.png', 'rb')
                    await bot.send_photo(message.chat.id, photo=photo32, caption='Твой пикселизированный CF-код', reply_markup=make_keyboard(['Считать CF-код', 'Мои CF-кода']))
                    photo32.close()
                else:
                    await db.update_user_step(message.chat.id, 'pixelate image')
                    await message.answer('Данный код уже использован, отправь другое изображение', reply_markup=make_keyboard(['Меню', 'Назад']))
        else:
            await message.answer('Неверно указан номер, попробуй снова', reply_markup=make_keyboard(['1', '2', '3', 'Меню', 'Назад']))

    # Кнока Создать CF-код
    elif message.text.lower() == 'создать cf-код':
        await db.update_user_step(message.chat.id, 'text')
        await message.answer('С помощью этой функции ты сможешь создать небольшой CF-код, учти, что процесс этот кропотливый и в случае нетерпеливости ты можешь воспользоваться функцией \'Загрузить изображение\', чтобы продолжить отправь текст, который будет отображаться при сканировании CF-кода')

    # Ввод текста CF-кода
    elif user['step'] == 'text' and message.text.lower() not in commands:
        await db.update_user_step(message.chat.id, 'draw code columns')
        await db.update_user_text(message.chat.id, message.text)
        await message.answer('Введи количество столбцов CF-кода от 2 до 5')

    # Ввод количества столбцов
    elif user['step'] == 'draw code columns' and message.text.lower() not in commands:
        if not (message.text.isnumeric()) or int(message.text) < 2 or int(message.text) > 5:
            await message.answer('Некорректное количество столбцов, попробуй снова')
        else:
            await db.update_user_step(message.chat.id, 'draw code lines')
            await db.update_user_cfcode_id(message.chat.id, message.text)
            await message.answer(f'Введи количество строк от 1 до 5')

    # Ввод количества строк
    elif user['step'] == 'draw code lines' and message.text.lower() not in commands:
        if not (message.text.isnumeric()) or int(message.text) < 1 or int(message.text) > 5:
            await message.answer('Некорректное количество строк, попробуй снова')
        else:
            await db.update_user_step(message.chat.id, 'draw code')
            await db.update_user_cfcode_id(message.chat.id, f"{user['cfcode_id']} {message.text} {'7' * int(user['cfcode_id']) * int(message.text)}")
            await cf.generate_code('7' * int(user['cfcode_id']) * int(message.text), int(message.text), int(user['cfcode_id']), True, user_id=message.chat.id)
            photo = open(f'images//{message.chat.id}.png', 'rb')
            await bot.send_photo(message.chat.id, photo=photo, caption='Выбери цвет квадрата', reply_markup=make_keyboard(['Черный', 'Красный', 'Желтый', 'Зеленый', 'Голубой', 'Синий', 'Розовый', 'Меню']))
            photo.close()

    # Выбор цвета квадрата CF-кода
    elif user['step'] == 'draw code' and message.text.lower() not in commands:
        if message.text not in ['Черный', 'Красный', 'Желтый', 'Зеленый', 'Голубой', 'Синий', 'Розовый']:
            await message.answer('Некорректный цвет, попробуй снова')
        else:
            colors = {'Черный': 0, 'Красный': 1, 'Желтый': 2, 'Зеленый': 3, 'Голубой': 4, 'Синий': 5, 'Розовый': 6}
            n = str(user['cfcode_id']).split()[2]
            i = n.find('7')
            n = n[:i] + str(colors[message.text]) + n[i + 1:]
            await db.update_user_cfcode_id(message.chat.id, f"{str(user['cfcode_id']).split()[0]} {str(user['cfcode_id']).split()[1]} {n}")
            if n.count('7') == 0:
                if await db.get_cfcode_by_id(f'{user["cfcode_id"].split()[1]} {user["cfcode_id"].split()[0]} {await cf.convert_to(n, 7, 64)}') is None:
                    offset = datetime.timezone(datetime.timedelta(hours=3))
                    date = datetime.datetime.now(offset)
                    await db.add_new_cfcode(message.chat.id, f"{int(str(user['cfcode_id']).split()[1])} {int(str(user['cfcode_id']).split()[0])} {await cf.convert_to(n, 7, 64)}", 0, user['text'], str(date)[:19])
                    await db.increase_cfcode_num(message.chat.id)
                    image = await cf.generate_code(n, int(str(user['cfcode_id']).split()[1]), int(str(user['cfcode_id']).split()[0]), False, user_id=message.chat.id, convert=False)
                    photo = open(f'images//{image}.png', 'rb')
                    await bot.send_photo(message.chat.id, photo=photo, caption='CF-код добавлен', reply_markup=make_keyboard(['Считать CF-код', 'Мои CF-кода']))
                    photo.close()
                else:
                    await message.answer('Данный CF-код уже использован, попробуй другой', reply_markup=make_keyboard(['Меню', 'Назад']))
            else:
                await cf.generate_code(n, int(str(user['cfcode_id']).split()[1]), int(str(user['cfcode_id']).split()[0]), True, user_id=message.chat.id)
                photo = open(f'images//{message.chat.id}.png', 'rb')
                await bot.send_photo(message.chat.id, photo=photo, caption='Выбери цвет квадрата', reply_markup=make_keyboard(['Черный', 'Красный', 'Желтый', 'Зеленый', 'Голубой', 'Синий', 'Розовый', 'Меню']))
                photo.close()

    else:
        await message.answer(f'Неизвестная команда, попробуй снова')

if __name__ == '__main__':
    executor.start_polling(dp, on_startup=on_startup, skip_updates=True)
