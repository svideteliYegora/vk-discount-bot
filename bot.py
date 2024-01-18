from vk_api import VkApi
from vk_api.utils import get_random_id
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import json
import gspread
from dotenv import load_dotenv
import os


load_dotenv('venv/.env')

GROUP_ID = os.environ.get('GROUP_ID')
GROUP_TOKEN = os.environ.get('GROUP_TOKEN')
API_VERSION = os.environ.get('API_VERSION')
CALLBACK_TYPES = ('show_snackbar', 'open_link', 'open_app', 'text')

# Получение данных с гугл таблицы.
gs = gspread.service_account(filename="venv/calm-vine-332204-924334d7332a.json")
sht2 = gs.open_by_url('https://docs.google.com/spreadsheets/d/1nCGk8r3ILS7VbuArDtIgiMhDhgr1kk4UHlRVyjtt2EQ')
worksheet = sht2.sheet1
list_of_lists = worksheet.get_all_values()
size_list_of_lists = (len(list_of_lists))

instruction_text = '''
1. Для начала работы нажмите : "запустить бота"
2. Выберите нужную Вам  категорию, если не нашли на первой странице, нажмите : "далее"
Затем введите номер нужной услуги и отправьте сообщением боту. 
3. Также вы всегда можете найти актуальный перечень всех акций и предложений нажав кнопку : "таблица со всеми промокодами"
4. Чтобы всегда оставаться на связи, подпишитесь на нас в телеграмм канале, нажав кнопку : "Мы в Телеграме"
'''

# Словарь, где ключи - уникальные номера (идентификаторы), значения - категории соответствующие идентификаторам.
id_category_dict = {}

# Словарь, где ключи - категории, значения - словари, где ключи - уникальные номера, значения - торговые марки.
category_brand_dict = {}

# Заполняем: id_category_dict, category_brand_dict.
counter = 0
added_brands = []
for row in list_of_lists[1:]:
    category = row[8]
    brand = row[0]
    if not category_brand_dict.get(category):
        category_brand_dict[category] = {counter: brand}
        added_brands.append(brand)
    else:
        if brand in added_brands:
            continue
        category_brand_dict[category][counter] = brand
        added_brands.append(brand)
    id_category_dict[counter] = category
    counter += 1

del counter, added_brands

# Словарь, где клчюи - торговые марки, значения - списки с промокодами, ссылками, сроками действия и тд.
brand_discount_info = {}
for row in list_of_lists[1:]:
    text = f"Название: *{row[0]}*" \
           f"\nСкидка: {row[3]}" \
           f"\nОписание: {row[4]}" \
           f"\nДействует до: {row[5]}" \
           f"\nРегион: {row[6]}" \
           f"\nСсылка: {row[7]}"
    if row[2] != None and row[2] != "":
        text += f"\nПромокод: {row[2]}"
    else:
        text += "\nДействует только по ссылке"

    if not brand_discount_info.get(row[0]):
        brand_discount_info[row[0]] = [text]
    else:
        brand_discount_info[row[0]].append(text)

# список уникальных торговых марок.
unique_brand_list = list(brand_discount_info.keys())

# Cписок уникальных категорий.
unique_category_list = list(category_brand_dict.keys())

# Для статистических данных.
brand_visit_statistics = [0 for i in range(len(unique_brand_list))]    # Список колличества посещений по торговым маркам. Изначально заполнен 0-ми.
active_user_ids = set()    # Уникальные id пользователей бота.
function_calls_count = 0    # Количество вызовов функций.

# Список содержащий ключевые слова приветствия.
greetings_keywords = ["start", "Start", "начать", "Начало", "Начать", "начало", "Бот", "бот", "Старт", "старт", "скидки", "Скидки"]

# Запускаем бот.
vk_session = VkApi(token=GROUP_TOKEN, api_version=API_VERSION)
vk = vk_session.get_api()
longpoll = VkBotLongPoll(vk_session, group_id=GROUP_ID)

# Основное меню
kb_main_menu = VkKeyboard(one_time=False, inline=False)
kb_main_menu.add_callback_button(label='Таблица со всеми промокодами!', color=VkKeyboardColor.POSITIVE, payload={"type": "open_link", "link": "https://docs.google.com/spreadsheets/d/1FhYGE5IODqbtXSfQGBs0BGUaUJYAWBGAC2SRWqYzf6M"})
kb_main_menu.add_line()
kb_main_menu.add_button(label='Запустить бота!', color=VkKeyboardColor.NEGATIVE, payload={"type": "text"})
kb_main_menu.add_line()
kb_main_menu.add_callback_button(label='Мы в Телеграме!', color=VkKeyboardColor.PRIMARY, payload={"type": "open_link", "link": "https://t.me/skidkinezagorami"})

# Возврат в меню категорий
kb_back_to_category_menu = VkKeyboard(one_time=False, inline=True)
kb_back_to_category_menu.add_button(label="Меню!", color=VkKeyboardColor.PRIMARY, payload={"type": "text"})


def get_kb_category_menu(buttons_names: [list[str]], page_number: int = 1) -> VkKeyboard:
    '''
    Генерирует клавиатуру для категорий с указанным номером страницы.

    :param buttons_names: Список категорий для названия кнопок.
    :param page_number: Номер страницы.
    :return: экземпляр класса VkKeyboard.
    '''
    kb = VkKeyboard(one_time=False, inline=True)

    buttons_on_page = 5
    start = (page_number - 1) * buttons_on_page
    end = min(page_number * buttons_on_page, len(buttons_names))

    for i in range(start, end):
        kb.add_button(label=buttons_names[i], color=VkKeyboardColor.SECONDARY, payload={"type": "text"})
        kb.add_line()

    if page_number == 1:
        kb.add_callback_button(label='Далее', color=VkKeyboardColor.PRIMARY, payload={"type": f"{page_number + 1}"})
    if page_number > 1:
        kb.add_callback_button(label='Назад', color=VkKeyboardColor.PRIMARY, payload={"type": f"{page_number - 1}"})
        if page_number * buttons_on_page < len(buttons_names):
            kb.add_callback_button(label='Далее', color=VkKeyboardColor.PRIMARY, payload={"type": f"{page_number + 1}"})

    return kb


def send_message(text_message: str, ind: int = None, keyboard: VkKeyboard = None) -> None:
    '''
    Отправка сообщения пользователю VK.

    :param text_message: Текст сообщения.
    :param ind: Индекс для получения названия категории из словаря.
    :param keyboard: Объект VkKeyboard.

    :return: None
    '''
    if not keyboard and ind:
        keyboard = VkKeyboard(one_time=False, inline=True)
        keyboard.add_button(label=id_category_dict[ind], color=VkKeyboardColor.SECONDARY, payload={"type": "text"})
        keyboard.add_line()
        keyboard.add_button(label="Меню!", color=VkKeyboardColor.PRIMARY, payload={"type": "text"})
        keyboard = keyboard.get_keyboard()
    vk.messages.send(user_id=event.obj.message['from_id'],
                     random_id=get_random_id(),
                     peer_id=event.obj.message['from_id'],
                     keyboard=keyboard,
                     message=text_message
                     )


for event in longpoll.listen():
    if event.type == VkBotEventType.MESSAGE_NEW:
        if event.obj.message['text'] == 'Запустить бота!' or event.obj.message['text'] == "Меню!":
            active_user_ids.add(event.obj.message['from_id'])
            send_message('Выбирай категорию (1)', keyboard=get_kb_category_menu(unique_category_list).get_keyboard())

        elif event.obj.message['text'] == 'Инструкция!':
            send_message(instruction_text, keyboard=kb_main_menu.get_keyboard())

        elif event.obj.message['text'] == '/stat1':
            send_message(f"Количество вызовов функций = {str(function_calls_count)}")

        elif event.obj.message['text'] == '/stat2':
            send_message(f"Людей активно использующих бота = {str(len(active_user_ids))}")

        elif event.obj.message['text'] == '/stat3':
            stat_data = "\n".join([f"{str(brand_visit_statistics[i])} {unique_brand_list[i]}" for i in range(len(brand_visit_statistics))])
            send_message(f"Детальная статистика:\n{stat_data}")

        elif event.obj.message['text'] in greetings_keywords:
            text_mess = "Привет-привет, я готов тебе помочь со скидками!\nНажми 'Запустить бота!' \nЕсли клавиатура свернута, нажми на 4 точки в правом нижнем углу!"
            send_message(text_mess, keyboard=kb_main_menu.get_keyboard())

        else:
            if event.obj.message['text'].isdigit():
                if int(event.obj.message['text']) < (len(unique_brand_list)-1):
                    function_calls_count += 1
                    brand_name = unique_brand_list[int(event.obj.message['text'])]
                    num = int(event.obj.message['text'])
                    brand_visit_statistics[num] = brand_visit_statistics[num] + 1
                    for text in brand_discount_info[brand_name]:
                        send_message(text)
                    send_message("Куда отправимся за скидками дальше?", True, num)

            else:
                if event.obj.message['text'] in unique_category_list:
                    text_message = "\n".join([f"{key}. {value}" for key, value in category_brand_dict[event.obj.message['text']].items()])
                    send_message(text_message, keyboard=kb_back_to_category_menu.get_keyboard())

    elif event.type == VkBotEventType.MESSAGE_EVENT:
        if event.object.payload.get('type') in CALLBACK_TYPES:
            vk.messages.sendMessageEventAnswer(
                      event_id=event.object.event_id,
                      user_id=event.object.user_id,
                      peer_id=event.object.peer_id,
                      event_data=json.dumps(event.object.payload))

        elif event.object.payload.get('type').isdigit():
                page_num = int(event.object.payload.get('type'))
                vk.messages.edit(
                      peer_id=event.obj.peer_id,
                      message=f'Выбирай категорию ({page_num})',
                      conversation_message_id=event.obj.conversation_message_id,
                      keyboard=get_kb_category_menu(unique_category_list, page_num).get_keyboard())
