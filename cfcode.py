from PIL import Image, ImageDraw, ImageFont
import cv2 as cv
import numpy as np
import database as db


# Функция для перевода из одной системы счисления в другую
async def convert_to(n, base_from, base_to):
    alph = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-_'
    m = 0
    for i in range(len(n) - 1, -1, -1):
        m += alph.find(n[i]) * base_from ** (len(n) - i - 1)
    result = ''
    while m != 0:
        result += alph[m % base_to]
        m //= base_to
    return result[::-1]


# Функция уменьшения размера изображения для удобства отображения при отладке
async def rescale_frame(frame, scale=0.5):
    width = int(frame.shape[1] * scale)
    height = int(frame.shape[0] * scale)
    return cv.resize(frame, (width, height), interpolation=cv.INTER_AREA)


# Функция пикселизирования изображения
async def pixelate(image, pixel_size=16):
    image = image.resize((image.size[0] // pixel_size, image.size[1] // pixel_size), Image.NEAREST)
    result = ''
    colors = {'0, 0, 0': 0, '0, 0, 255': 1, '0, 255, 255': 2, '0, 255, 0': 3, '255, 255, 0': 4, '255, 0, 0': 5, '255, 0, 255': 6, '255, 255, 255': 2}
    image = np.array(image)
    r, g, b = cv.split(image)
    _, image_b = cv.threshold(b, 120, 255, cv.THRESH_BINARY)
    _, image_g = cv.threshold(g, 120, 255, cv.THRESH_BINARY)
    _, image_r = cv.threshold(r, 120, 255, cv.THRESH_BINARY)
    for i in range(0, image.shape[0]):
        for j in range(0, image.shape[1]):
            color = colors[f'{image_b[i, j]}, {image_g[i, j]}, {image_r[i, j]}']
            result += str(color)
    return await convert_to(result, 7, 64), image.shape[0], image.shape[1]


# Считывание CF-кода с изображения
async def detect_code(image, x, y):
    image = cv.cvtColor(np.array(image), cv.COLOR_RGB2BGR)
    min_p = (150, 150, 150)
    max_p = (255, 255, 255)
    image_g = cv.inRange(image, min_p, max_p)
    kernel = np.ones((5, 5), np.uint8)
    erosion = cv.erode(image_g, kernel, iterations=1)
    canny = cv.Canny(erosion, 125, 200)

    contours, hierarchy = cv.findContours(canny, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
    boxcf = []

    for contour in contours:
        rect = cv.minAreaRect(contour)
        area = int(rect[1][0] * rect[1][1])
        box = cv.boxPoints(rect)
        box = np.int0(box)

        if boxcf == []:
            boxcf = [box, area, rect]
        elif area > boxcf[1]:
            boxcf = [box, area, rect]

    box = boxcf[0]
    main_box = []
    #cv.drawContours(image, [box], 0, (0, 0, 255), 10)
    #cv.imshow('image', image)
    #cv.waitKey()

    for elem in box:
        main_box.append([int(elem[0]), int(elem[1])])
    main_box = sorted(main_box)

    if main_box[0][1] < main_box[1][1]:
        top_left = main_box[0]
        bottom_left = main_box[1]
    else:
        top_left = main_box[1]
        bottom_left = main_box[0]
    if main_box[2][1] < main_box[3][1]:
        top_right = main_box[2]
        bottom_right = main_box[3]
    else:
        top_right = main_box[3]
        bottom_right = main_box[2]

    result = ''
    colors = {'0, 0, 0': 0, '0, 0, 255': 1, '0, 255, 255': 2, '0, 255, 0': 3, '255, 255, 0': 4, '255, 0, 0': 5, '255, 0, 255': 6, '255, 255, 255': 7}
    colors_name = {0: 'black', 1: 'red', 2: 'yellow', 3: 'green', 4: 'cian', 5: 'blue', 6: 'pink', 7: 'white'}
    for i in range(y):
        for j in range(x):
            coords = [round(top_left[0] + (top_right[0] - top_left[0]) / x * j + (top_right[0] - top_left[0]) / x / 2 + (bottom_left[0] - top_left[0]) / y * i), round(top_left[1] + (bottom_left[1] - top_left[1]) / y * i + (bottom_left[1] - top_left[1]) / y / 2 + (top_right[1] - top_left[1]) / x * j)]
            img = image[coords[1] - 3: coords[1] + 3, coords[0] - 3: coords[0] + 3]
            img = cv.blur(img, (10, 10))
            b, g, r = cv.split(img)
            _, img_b = cv.threshold(b, 120, 255, cv.THRESH_BINARY)
            _, img_g = cv.threshold(g, 120, 255, cv.THRESH_BINARY)
            _, img_r = cv.threshold(r, 120, 255, cv.THRESH_BINARY)
            color = colors[f'{img_b[img.shape[0] // 2, img.shape[1] // 2]}, {img_g[img.shape[0] // 2, img.shape[1] // 2]}, {img_r[img.shape[0] // 2, img.shape[1] // 2]}']
            #cv.circle(image, coords, radius=10, color=(255, 255, 255), thickness=-1)
            result += str(color)
            #print(colors_name[color])
            #cv.imshow('img', img)
            #cv.imshow('image', image)
            #cv.waitKey(0)
    return await convert_to(result, 7, 64), y, x


# Генерация CF-кода
async def generate_code(n, h, w, borders, gaps=False, user_id=None, convert=True, pixelate=0):
    image_shape = [h, w]
    if not borders and convert:
        n = await convert_to(n, 64, 7)
    if len(n) < h * w:
        n = '0' * (h * w - len(n)) + n

    if h * w < 100:
        square = 80
        if square * max(h, w) // 10 > 160:
            border = square * max(h, w) // 10
        else:
            border = 80
        if square * h // 10 > 80:
            num = square * h // 10
        else:
            num = 80
        if gaps:
            grid_gap = 8
        else:
            grid_gap = 0
    else:
        square = 20
        if square * max(h, w) // 10 > 40:
            border = square * max(h, w) // 10
        else:
            border = 40
        if square * h // 10 > 20:
            num = square * h // 10
        else:
            num = 20
        if gaps:
            grid_gap = 2
        else:
            grid_gap = 0
    num_gap = num // 2

    colors = {'0': (0, 0, 0), '1': (0, 0, 255), '2': (0, 190, 255), '3': (0, 255, 0), '4': (255, 255, 0), '5': (255, 0, 0), '6': (255, 0, 255), '7': (255, 255, 255)}
    image = Image.new('RGB', (border * 2 + grid_gap * (image_shape[1] - 1) + square * image_shape[1], border * 2 + grid_gap * (image_shape[0] - 1) + square * image_shape[0] + num_gap + num), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    font_size = round(num / 4 * 3)
    font = ImageFont.truetype('Roboto-Bold.ttf', font_size)
    for i in range(image_shape[0]):
        for j in range(image_shape[1]):
            x1 = border + j * (square + grid_gap)
            y1 = border + i * (square + grid_gap)
            x2 = border + (j + 1) * square + j * grid_gap
            y2 = border + (i + 1) * square + i * grid_gap
            if borders:
                if i * image_shape[1] + j == str(n).find('7'):
                    draw.rectangle((x1, y1, x2, y2), fill=colors[n[i * image_shape[1] + j]][::-1], outline=(0, 255, 0), width=10)
                else:
                    draw.rectangle((x1, y1, x2, y2), fill=colors[n[i * image_shape[1] + j]][::-1], outline=(0, 0, 0), width=10)
            else:
                draw.rectangle((x1, y1, x2, y2), fill=colors[n[i * image_shape[1] + j]][::-1])
    draw.text((image.size[0] // 2, image.size[1] - border - num // 2), f'{w} x {h}', fill='black', font=font, anchor='mm')
    if borders:
        image.save(f'images//{user_id}.png')
        return True
    elif pixelate:
        image.save(f'images//pixelate {pixelate} {user_id}.png')
        return f'{h} {w} {await convert_to(n, 7, 64)}'
    else:
        cfcode = await db.get_cfcode_by_id(f'{h} {w} {await convert_to(n, 7, 64)}')
        image.save(f'images//{cfcode["cfcode_num"]}.png')
        return cfcode["cfcode_num"]
