import apiai
import json

import threading
import time

import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id

from config import *

# Логгирование
import logging
logging.basicConfig(format = u'%(filename)s[LINE:%(lineno)d]# %(levelname)-8s [%(asctime)s]  %(message)s', level = logging.INFO, filename = directory + 'vktestbot.log')

# Хранилище данных о сессиях
sessionStorage = {}

# Хранилище данных о возможных записях в бассейн
poolRecords = {}

# Замок для доступа к ресурсу
lock = threading.Lock()

# ID ВК для админов
admin_ids = [] # Я, Оля, Эдгар, Леша

def make_keyb(my_keyb, user_id, answer):
    keyboard = VkKeyboard(one_time = False)
    for i in range(min(8, len(my_keyb))):
        keyboard.add_button(my_keyb[i]['label'], color=my_keyb[i]['color'], payload=my_keyb[i]['payload'])
        keyboard.add_line()
    if len(my_keyb) > 8:
        sessionStorage[user_id]._KEYB = my_keyb
        sessionStorage[user_id]._PAGE = 0
        keyboard.add_button('Далее ->', color=VkKeyboardColor.PRIMARY, payload={'action': 'bot.next_page', 'text': answer})
        keyboard.add_line()
    keyboard.add_button('Отмена', color=VkKeyboardColor.PRIMARY, payload={'action': 'bot.cancel'})  
    return keyboard.get_keyboard()

def get_ai_answer(text, session_id):

    ai_action, ai_parameters, ai_contexts, ai_response = '#no_answer', '', {}, []
    
    # DIALOGFLOW_START

    logging.debug('Connecting to DialogFlow')
    ai_request = apiai.ApiAI(TOKEN_AI).text_request() # Токен API к Dialogflow
    logging.debug('Connected')
    ai_request.lang = 'ru' # На каком языке будет послан запрос
    ai_request.session_id = session_id # ID Сессии диалога (нужно, чтобы потом учить бота)
    logging.debug('Sending text to DialogFlow')
    ai_request.query = text # Посылаем запрос к ИИ с сообщением от юзера
    logging.debug('Sent')
    logging.debug('Getting result from DialogFlow')
    responseJson = json.loads(ai_request.getresponse().read().decode('utf-8'))
    logging.debug('Got')
    ai_response = responseJson['result']['fulfillment']['speech'] # Разбираем JSON и вытаскиваем ответ

    if 'action' in responseJson['result']:
        ai_action = responseJson['result']['action']
    if 'parameters' in responseJson['result']:
        ai_parameters = responseJson['result']['parameters']
    if 'contexts' in responseJson['result']:
        ai_contexts = responseJson['result']['contexts']
            
    # Если есть ответ от бота - присылаем юзеру, если нет - бот его не понял
    if not ai_response:
        ai_response = '#no_answer'

    # DIALOGFLOW_FINISH

    return ai_action, ai_parameters, ai_contexts, ai_response

def get_user_info(user_id):
    return vk.users.get(user_ids=user_id)

def get_keyboard(step):
    try:
        keyboard = KDICT[step]
    except Exception:
        keyboard = KDICT['#all']
    
    return keyboard

month = {1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля', 5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа', 9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'}

def get_str_time(t):
    return str(t.tm_hour) + ' ' + str(t.tm_min)

class PoolTime:

    def __init__(self, day, mon, year, hour, mn, count):
        self._TIME = time.localtime(time.mktime((year, mon, day, hour, mn, 0, 0, 0, 0)))
        self._COUNT = count
        self._IDS = []

    def __len__(self):
        return self._COUNT

    def __str__(self):
        return self.get_day() + ' ' + self.get_time() + ' (свободно ' + str(self._COUNT) + ')'

    def get_day(self):
        return str(self._TIME.tm_mday) + ' ' + month[self._TIME.tm_mon] + ' ' + str(self._TIME.tm_year)

    def get_time(self):
        return time.strftime("%H:%M", self._TIME)
        return get_str_time(self._TIME)

    def get_sec(self):
        return time.mktime(self._TIME)

    def get_show_data(self):
        answer = 'Дата: ' + self.get_day() + '\n'
        answer += 'Время: ' + self.get_time() + '\n'
        answer += '\n'
        return answer

    def add(self, user_id):
        self._IDS.append(user_id)

class VkBot:

    def __init__(self, user_id):
        logging.info('class VkBot [%s]: Created', str(user_id))

        user_info = get_user_info(user_id)

        self._USER_ID = user_id # ID ользователя ВК
        self._FIRST_NAME = user_info[0]['first_name'] # Имя ВК
        self._LAST_NAME = user_info[0]['last_name'] # Фамилия ВК
        self._STEP = 'mainUS' # Шаг
        self._AUTH = False 
        self._ADMIN = False # Админ-панель

        self._REC = [] # Записи

        self._KEYB = [] # Клавиши для клавиатуры
        self._PAGE = 1 # Страница клавиатуры

    def __str__(self):
        answer = 'User ID: ' + str(self._USER_ID) + '\n'
        answer += 'User: ' + self._FIRST_NAME + ' ' + self._LAST_NAME + '\n'
        answer += 'Step: ' + self._STEP + '\n'
        answer += 'Auth: ' + str(self._AUTH) + '\n'
        answer += 'Admin: ' + str(self._ADMIN) + '\n'
        answer += 'Link: @id' + str(self._USER_ID) + '\n'
        return answer

    def auth(self):
        self._AUTH = True
        self._STEP = 'main'
        return self._AUTH

    def prev_step(self):
        if '_' not in self._STEP:
            return
        text = self._STEP
        text = text.split('_')
        text.pop()
        text = '_'.join(text)
        self._STEP = text

    def next_step(self, step):
        self._STEP += '_' + step

    def set_step(self, step):
        self._STEP = step
    
def write_msg(user_id, message, msg_id = None, keyboard = None):
    vk.messages.send(
        user_id=user_id,
        reply_to=msg_id,
        message=message,
        random_id=get_random_id(),
        keyboard=keyboard
    )

# Авторизуемся как сообщество
vk_session = vk_api.VkApi(token=TOKEN)
vk = vk_session.get_api()

# Работа с сообщениями
longpoll = VkLongPoll(vk_session)

logging.info('Server started')
print('Server started')


def main():
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            
            logging.info('longpoll [%s]: New message: {%s}', str(event.user_id), event.text.encode('utf-8'))

            user_id = event.user_id
            if sessionStorage.get(user_id) == None:
                sessionStorage[user_id] = VkBot(user_id)

            msg_handler(event)
            continue

def admin_menu(event):
    user_id = event.user_id
    text = event.text.lower()
    msg_id = event.message_id
    if 'payload' in dir(event):
        payload = eval(event.payload)
    else:
        payload = None

    action = None

    if payload:
        action = payload.get('action')

    if action == 'admin.show':
        answer = 'Список сеансов:\n\n'
        my_keyb = []
        my_keyb.append({'label': 'Показать все', 'color': VkKeyboardColor.PRIMARY, 'payload': {'action': 'admin.show.all'}})
        for sec in poolRecords:
            date = poolRecords[sec].get_day() + ' ' + poolRecords[sec].get_time()
            color = VkKeyboardColor.PRIMARY
            my_keyb.append({'label': date, 'color': color, 'payload': {'action': 'admin.show.num', 'num': sec}})
            answer += str(poolRecords[sec]) + '\n'
        if len(my_keyb) == 0:
            answer = 'Сеансов не найдено'
            keyboard = get_keyboard(sessionStorage[user_id]._STEP)
        else:
            answer += '\nВыберите сеанс'
            keyboard = make_keyb(my_keyb, user_id, 'Выберите сеанс')
            sessionStorage[user_id].next_step('show')
        write_msg(event.user_id, answer, keyboard=keyboard)
        return

    elif action == 'admin.show.all': ###
        answer = 'pass'
        sessionStorage[user_id].prev_step()
        keyboard = get_keyboard(sessionStorage[user_id]._STEP)
        write_msg(event.user_id, answer, keyboard=keyboard)
        return

    elif action == 'admin.show.num': ###
        answer = 'pass'
        sessionStorage[user_id].prev_step()
        keyboard = get_keyboard(sessionStorage[user_id]._STEP)
        write_msg(event.user_id, answer, keyboard=keyboard)
        return

    elif action == 'admin.add': ###
        answer = 'pass'
        keyboard = get_keyboard(sessionStorage[user_id]._STEP)
        write_msg(event.user_id, answer, keyboard=keyboard)
        return

    elif action == 'admin.del':
        my_keyb = []
        for sec in poolRecords:
            date = str(poolRecords[sec])
            color = VkKeyboardColor.PRIMARY
            my_keyb.append({'label': date, 'color': color, 'payload': {'action': 'admin.del.num', 'num': sec}})
        if len(my_keyb) == 0:
            answer = 'Сеансов не найдено'
            keyboard = get_keyboard(sessionStorage[user_id]._STEP)
        else:
            answer = 'Выберите сеанс, который хотите удалить'
            keyboard = make_keyb(my_keyb, user_id, answer)
            sessionStorage[user_id].next_step('del')
        write_msg(event.user_id, answer, keyboard=keyboard)
        return

    elif action == 'admin.del.num': ###
        answer = 'pass'
        sessionStorage[user_id].prev_step()
        keyboard = get_keyboard(sessionStorage[user_id]._STEP)
        write_msg(event.user_id, answer, keyboard=keyboard)
        return

    elif action == 'admin.out':
        sessionStorage[user_id].prev_step()
        sessionStorage[user_id]._ADMIN = False
        answer = 'Выход выполнен'
        keyboard = get_keyboard(sessionStorage[user_id]._STEP)
        write_msg(event.user_id, answer, keyboard=keyboard)
        return

    else:
        answer = 'Я вас не понимаю((\nПожалуйста, воспользуйтесь клавиатурой'
        if sessionStorage[user_id]._STEP == 'main_admin':
            keyboard = get_keyboard(sessionStorage[user_id]._STEP)
            write_msg(event.user_id, answer, keyboard=keyboard)
        else:
            write_msg(event.user_id, answer)
        return
    

def msg_handler(event):
    user_id = event.user_id
    text = event.text.lower()
    msg_id = event.message_id
    if 'payload' in dir(event):
        payload = eval(event.payload)
    else:
        payload = None

    action = None

    if payload:
        action = payload.get('action')

    #ai_ans = False
    #ai_response = '#no_answer'
    #ai_action = ''
    #ai_parameters = {}
    #ai_contexts = []

    #if not action:
    #    try:
    #        ai_action, ai_parameters, ai_contexts, ai_response = get_ai_answer(text)
    #        ai_ans = True
    #    except Exception as e:
    #        err = '\nAI_RESPONSE ERROR:\n' + str(e) + '\n'
    #        logging.error(err)
    #        print(err)

    # ANSWER

    if action == 'bot.next_page':
        keyboard = VkKeyboard(one_time = False)
        answer = payload['text']
        sessionStorage[user_id]._PAGE += 1
        k = sessionStorage[user_id]._PAGE * 8
        my_keyb = sessionStorage[user_id]._KEYB
        for i in range(k, k + min(8, len(my_keyb) - k)):
            keyboard.add_button(my_keyb[i]['label'], color=my_keyb[i]['color'], payload=my_keyb[i]['payload'])
            keyboard.add_line()
        keyboard.add_button('<- Назад', color=VkKeyboardColor.PRIMARY, payload={'action': 'bot.prev_page', 'text': answer})
        if len(my_keyb) - k > 8:
            keyboard.add_button('Далее ->', color=VkKeyboardColor.PRIMARY, payload={'action': 'bot.next_page', 'text': answer})
        keyboard.add_line()
        keyboard.add_button('Отмена', color=VkKeyboardColor.PRIMARY, payload={'action': 'bot.cancel'})
            
        keyboard = keyboard.get_keyboard()
        write_msg(event.user_id, answer, keyboard=keyboard)
        return

    elif action == 'bot.prev_page':
        keyboard = VkKeyboard(one_time = False)
        answer = payload['text']
        sessionStorage[user_id]._PAGE -= 1
        k = sessionStorage[user_id]._PAGE * 8
        my_keyb = sessionStorage[user_id]._KEYB
        for i in range(k, k + 8):
            keyboard.add_button(my_keyb[i]['label'], color=my_keyb[i]['color'], payload=my_keyb[i]['payload'])
            keyboard.add_line()
        if sessionStorage[user_id]._PAGE != 0:
            keyboard.add_button('<- Назад', color=VkKeyboardColor.PRIMARY, payload={'action': 'bot.prev_page', 'text': answer})
        keyboard.add_button('Далее ->', color=VkKeyboardColor.PRIMARY, payload={'action': 'bot.next_page', 'text': answer})
        keyboard.add_line()
        keyboard.add_button('Отмена', color=VkKeyboardColor.PRIMARY, payload={'action': 'bot.cancel'})
            
        keyboard = keyboard.get_keyboard()
        write_msg(event.user_id, answer, keyboard=keyboard)
        return

    elif action == 'bot.cancel':
        answer = 'Действие отменено'
        sessionStorage[user_id].prev_step()
        keyboard = get_keyboard(sessionStorage[user_id]._STEP)
        write_msg(event.user_id, answer, keyboard=keyboard)
        return

    if user_id in admin_ids:

        if text == 'print':
            answer = str(sessionStorage[user_id])
            write_msg(event.user_id, answer)
            return

        if text == 'print all':
            answer = ''
            for elem in sessionStorage:
                answer += str(sessionStorage[elem]) + '\n'
            write_msg(event.user_id, answer)
            return

        if sessionStorage[user_id]._ADMIN:
            admin_menu(event)
            return

    if not sessionStorage[user_id]._AUTH: # mainUS

        if action == 'bot.reg': 
            if sessionStorage[user_id].auth():
                answer = 'Вы зарегистрированы!'
            else:
                answer = 'Регистрация не удалась((('

            keyboard = get_keyboard(sessionStorage[user_id]._STEP)
            write_msg(event.user_id, answer, keyboard=keyboard)
            return

        elif action == 'bot.admin':
            if user_id not in admin_ids:
                answer = 'Доступ запрещен'
            else:
                answer = 'Добро пожаловать!'
                sessionStorage[user_id]._ADMIN = True
                sessionStorage[user_id].next_step('admin')
            keyboard = get_keyboard(sessionStorage[user_id]._STEP)
            write_msg(event.user_id, answer, keyboard=keyboard)
            return

        elif action == 'bot.auth': ###
            answer = 'pass'
            keyboard = get_keyboard(sessionStorage[user_id]._STEP)
            write_msg(event.user_id, answer, keyboard=keyboard)
            return
        
        else:
            answer = 'Я вас не понимаю((\nПожалуйста, воспользуйтесь клавиатурой'
            if sessionStorage[user_id]._STEP == 'mainUS' or sessionStorage[user_id]._STEP == 'main':
                keyboard = get_keyboard(sessionStorage[user_id]._STEP)
                write_msg(event.user_id, answer, keyboard=keyboard)
            else:
                write_msg(event.user_id, answer)
            return

    elif action == 'pool.show': # main
        answer = 'Количество записей: ' + str(len(sessionStorage[user_id]._REC)) + '\n\n'
        
        for sec in sessionStorage[user_id]._REC:
            answer += poolRecords[sec].get_show_data()
        if len(sessionStorage[user_id]._REC) == 0:
            answer = 'У вас нет записей'
        
        keyboard = get_keyboard(sessionStorage[user_id]._STEP)
        write_msg(event.user_id, answer, keyboard=keyboard)
        return

    elif action == 'pool.add': # main
        my_keyb = []
        for sec in poolRecords:
            if len(poolRecords[sec]) > 0 and (sec not in sessionStorage[user_id]._REC):
                date = str(poolRecords[sec])
                color = VkKeyboardColor.NEGATIVE
                if len(poolRecords[sec]) > 10:
                    color = VkKeyboardColor.POSITIVE
                elif len(poolRecords[sec]) > 5:
                    color = VkKeyboardColor.DEFAULT
                my_keyb.append({'label': date, 'color': color, 'payload': {'action': 'pool.add.num', 'num': sec}})
        if len(my_keyb) == 0:
            answer = 'Доступных записей нет'
            keyboard = get_keyboard(sessionStorage[user_id]._STEP)
        else:
            answer = 'Выберите доступное время'
            keyboard = make_keyb(my_keyb, user_id, answer)
            sessionStorage[user_id].next_step('add')
                
        write_msg(event.user_id, answer, keyboard=keyboard)
        return

    elif action == 'pool.del': # main
        my_keyb = []
        for sec in sessionStorage[user_id]._REC:
            date = poolRecords[sec].get_day() + ' ' + poolRecords[sec].get_time()
            color = VkKeyboardColor.DEFAULT
            my_keyb.append({'label': date, 'color': color, 'payload': {'action': 'pool.del.num', 'num': sec}})
        if len(my_keyb) == 0:
            answer = 'У вас нет ни одной записи'
            keyboard = get_keyboard(sessionStorage[user_id]._STEP)
        else:
            answer = 'Выберите запись, которую хотите удалить'
            keyboard = make_keyb(my_keyb, user_id, answer)
            sessionStorage[user_id].next_step('del')
                
        write_msg(event.user_id, answer, keyboard=keyboard)
        return

    elif action == 'pool.add.num': # main_add
        num = int(payload['num'])

        lock.acquire() # Блокируем доступ
        if len(poolRecords[num]) > 0:
            poolRecords[num]._COUNT -= 1
            sessionStorage[user_id]._REC.append(num)
            answer = 'Вы записаны в бассейн ' + poolRecords[num].get_day() + ' в ' + poolRecords[num].get_time()
        else:
            answer = 'Извините, мест больше нет(('
        lock.release() # Разблокируем доступ

        sessionStorage[user_id].prev_step()

        keyboard = get_keyboard(sessionStorage[user_id]._STEP)
        write_msg(event.user_id, answer, keyboard=keyboard)
        return

    elif action == 'pool.del.num': # main_del
        num = int(payload['num'])

        poolRecords[num]._COUNT += 1
        sessionStorage[user_id]._REC.pop(sessionStorage[user_id]._REC.index(num))
        answer = 'Записьв бассейн ' + poolRecords[num].get_day() + ' в ' + poolRecords[num].get_time() + ' удалена'

        sessionStorage[user_id].prev_step()

        keyboard = get_keyboard(sessionStorage[user_id]._STEP)
        write_msg(event.user_id, answer, keyboard=keyboard)
        return

    elif action == 'bot.out': # Восстановление данных
        sessionStorage[user_id] = VkBot(user_id)
        answer = 'Выход выполнен'
        keyboard = get_keyboard(sessionStorage[user_id]._STEP)
        write_msg(event.user_id, answer, keyboard=keyboard)
        return

    else:
        answer = 'Я вас не понимаю((\nПожалуйста, воспользуйтесь клавиатурой'
        if sessionStorage[user_id]._STEP == 'mainUS' or sessionStorage[user_id]._STEP == 'main':
            keyboard = get_keyboard(sessionStorage[user_id]._STEP)
            write_msg(event.user_id, answer, keyboard=keyboard)
        else:
            write_msg(event.user_id, answer)
        return

# Базовые данные о сеансах
base_data = [
        (25, 2, 2020, 15, 00, 24),
        (25, 2, 2020, 19, 00, 2),
        (29, 2, 2020, 15, 00, 13),
        (29, 2, 2020, 19, 00, 4),
        (1, 3, 2020, 15, 00, 4),
        (2, 3, 2020, 19, 00, 2),
        (3, 3, 2020, 15, 00, 3),
        (4, 3, 2020, 19, 00, 1),
        (5, 3, 2020, 15, 00, 2),
        (6, 3, 2020, 15, 00, 1),
        (6, 3, 2020, 19, 00, 1)
    ]

for elem in base_data:
    t = PoolTime(elem[0], elem[1], elem[2], elem[3], elem[4], elem[5])
    poolRecords[t.get_sec()] = t
    
if __name__ == '__main__':
    main()

