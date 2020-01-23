import apiai
import json

import threading

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
poolRecords = [] # Date, time, count

# Замок для доступа к ресурсу
lock = threading.Lock()

poolRecords = [
        ['25 февраля 2020', '15:00', 24],
        ['25 февраля 2020', '19:00', 2],
        ['29 февраля 2020', '15:00', 13],
        ['29 февраля 2020', '19:00', 4],
        ['1 марта 2020', '15:00', 4],
        ['2 марта 2020', '19:00', 2],
        ['3 марта 2020', '15:00', 3],
        ['4 марта 2020', '19:00', 1],
        ['5 марта 2020', '15:00', 2],
        ['6 марта 2020', '15:00', 1],
        ['6 марта 2020', '19:00', 1]
    ]

def prev_step(text):
    text = text.split('_')
    text.pop()
    text = '_'.join(text)
    return text

def make_keyb(my_keyb, user_id, msg_id, answer):
    keyboard = VkKeyboard(one_time = False)
    for i in range(min(8, len(my_keyb))):
        keyboard.add_button(my_keyb[i]['label'], color=my_keyb[i]['color'], payload=my_keyb[i]['payload'])
        keyboard.add_line()
    if len(my_keyb) > 8:
        sessionStorage[user_id]._KEYB = my_keyb
        sessionStorage[user_id]._PAGE = 0
        keyboard.add_button('Далее ->', color=VkKeyboardColor.PRIMARY, payload={'msg_id': msg_id, 'action': 'bot.next_page', 'text': answer})
        keyboard.add_line()
    keyboard.add_button('Отмена', color=VkKeyboardColor.PRIMARY, payload={'msg_id': msg_id, 'action': 'bot.cancel'})  
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

def get_keyboard(step, auth, msg_id):
    try:
        keyboard = KDICT[step]
    except Exception:
        keyboard = KDICT['#all']
    
    return keyboard

class VkBot:

    def __init__(self, user_id):
        logging.info('class VkBot [%s]: Created', str(user_id))

        user_info = get_user_info(user_id)

        self._USER_ID = user_id
        self._FIRST_NAME = user_info[0]['first_name']
        self._LAST_NAME = user_info[0]['last_name']
        self._STEP = 'mainUS'
        self._AUTH = False

        self._REC = []

        self._KEYB = []
        self._PAGE = 1

    def __str__(self):
        answer = 'User ID: ' + str(self._USER_ID) + '\n'
        answer += 'User: ' + self._FIRST_NAME + ' ' + self._LAST_NAME + '\n'
        answer += 'Step: ' + self._STEP + '\n'
        answer += 'Auth: ' + str(self._AUTH) + '\n'
        return answer

    def auth(self):
        self._AUTH = True
        self._STEP = 'main'
        return self._AUTH
    
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

def msg_handler(event):
    user_id = event.user_id
    text = event.text.lower()
    msg_id = event.message_id
    if 'payload' in dir(event):
        payload = eval(event.payload)
    else:
        payload = None

    ai_ans = False
    ai_response = '#no_answer'
    ai_action = ''
    ai_parameters = {}
    ai_contexts = []

    action = None

    if payload:
        action = payload.get('action')

    #if not action:
    #    try:
    #        ai_action, ai_parameters, ai_contexts, ai_response = get_ai_answer(text, msg_id)
    #        ai_ans = True
    #    except Exception as e:
    #        err = '\nAI_RESPONSE ERROR:\n' + str(e) + '\n'
    #        logging.error(err)
    #        print(err)

    # ANSWER

    if user_id == 154785330:

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

    if not sessionStorage[user_id]._AUTH:

        if action == 'bot.reg': # mainUS
            if sessionStorage[user_id].auth():
                answer = 'Вы зарегистрированы!'
            else:
                answer = 'Регистрация не удалась((('

            keyboard = get_keyboard(sessionStorage[user_id]._STEP, sessionStorage[user_id]._AUTH, msg_id)
            write_msg(event.user_id, answer, keyboard=keyboard)
            return
        
        else:
            answer = 'Я вас не понимаю((\nПожалуйста, воспользуйтесь клавиатурой'
            if sessionStorage[user_id]._STEP == 'mainUS' or sessionStorage[user_id]._STEP == 'main':
                keyboard = get_keyboard(sessionStorage[user_id]._STEP, sessionStorage[user_id]._AUTH, msg_id)
                write_msg(event.user_id, answer, keyboard=keyboard)
            else:
                write_msg(event.user_id, answer)
            return

    elif action == 'pool.show': # main
        answer = 'Количество записей: ' + str(len(sessionStorage[user_id]._REC)) + '\n\n'
        
        for i in sessionStorage[user_id]._REC:
            answer += 'Дата: ' + poolRecords[i][0] + '\n'
            answer += 'Время: ' + poolRecords[i][1] + '\n'
            answer += '\n'
        if len(sessionStorage[user_id]._REC) == 0:
            answer = 'У вас нет записей'
        
        keyboard = get_keyboard(sessionStorage[user_id]._STEP, sessionStorage[user_id]._AUTH, msg_id)
        write_msg(event.user_id, answer, keyboard=keyboard)
        return

    elif action == 'pool.add': # main
        keyboard = VkKeyboard(one_time = False)
        my_keyb = []
        for i in range(len(poolRecords)):
            if poolRecords[i][2] > 0 and (i not in sessionStorage[user_id]._REC):
                date = poolRecords[i][0] + ' ' + poolRecords[i][1] + ' (свободно ' + str(poolRecords[i][2]) + ')'
                color = VkKeyboardColor.NEGATIVE
                if poolRecords[i][2] > 10:
                    color = VkKeyboardColor.POSITIVE
                elif poolRecords[i][2] > 5:
                    color = VkKeyboardColor.DEFAULT
                my_keyb.append({'label': date, 'color': color, 'payload': {'msg_id': msg_id, 'action': 'pool.add.num', 'add_num': i}})
        if len(my_keyb) == 0:
            answer = 'Доступных записей нет'
            keyboard = get_keyboard(sessionStorage[user_id]._STEP, sessionStorage[user_id]._AUTH, msg_id)
        else:
            answer = 'Выберите доступное время'
            keyboard = make_keyb(my_keyb, user_id, msg_id, answer)
            sessionStorage[user_id]._STEP += '_add'
                
        write_msg(event.user_id, answer, keyboard=keyboard)
        return

    elif action == 'pool.del': # main
        my_keyb = []
        for i in sessionStorage[user_id]._REC:
            date = poolRecords[i][0] + ' ' + poolRecords[i][1]
            color = VkKeyboardColor.DEFAULT
            my_keyb.append({'label': date, 'color': color, 'payload': {'msg_id': msg_id, 'action': 'pool.del.num', 'del_num': i}})
        if len(my_keyb) == 0:
            answer = 'У вас нет ни одной записи'
            keyboard = get_keyboard(sessionStorage[user_id]._STEP, sessionStorage[user_id]._AUTH, msg_id)
        else:
            answer = 'Выберите запись, которую хотите удалить'
            keyboard = make_keyb(my_keyb, user_id, msg_id, answer)
            sessionStorage[user_id]._STEP += '_del'
                
        write_msg(event.user_id, answer, keyboard=keyboard)
        return

    elif action == 'bot.next_page':
        keyboard = VkKeyboard(one_time = False)
        answer = payload['text']
        sessionStorage[user_id]._PAGE += 1
        k = sessionStorage[user_id]._PAGE * 8
        my_keyb = sessionStorage[user_id]._KEYB
        for i in range(k, k + min(8, len(my_keyb) - k)):
            keyboard.add_button(my_keyb[i]['label'], color=my_keyb[i]['color'], payload=my_keyb[i]['payload'])
            keyboard.add_line()
        keyboard.add_button('<- Назад', color=VkKeyboardColor.PRIMARY, payload={'msg_id': msg_id, 'action': 'bot.prev_page', 'text': answer})
        if len(my_keyb) - k > 8:
            keyboard.add_button('Далее ->', color=VkKeyboardColor.PRIMARY, payload={'msg_id': msg_id, 'action': 'bot.next_page', 'text': answer})
        keyboard.add_line()
        keyboard.add_button('Отмена', color=VkKeyboardColor.PRIMARY, payload={'msg_id': msg_id, 'action': 'bot.cancel'})
            
        keyboard = keyboard.get_keyboard()
        write_msg(event.user_id, answer, keyboard=keyboard)

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
            keyboard.add_button('<- Назад', color=VkKeyboardColor.PRIMARY, payload={'msg_id': msg_id, 'action': 'bot.prev_page', 'text': answer})
        keyboard.add_button('Далее ->', color=VkKeyboardColor.PRIMARY, payload={'msg_id': msg_id, 'action': 'bot.next_page', 'text': answer})
        keyboard.add_line()
        keyboard.add_button('Отмена', color=VkKeyboardColor.PRIMARY, payload={'msg_id': msg_id, 'action': 'bot.cancel'})
            
        keyboard = keyboard.get_keyboard()
        write_msg(event.user_id, answer, keyboard=keyboard)

    elif action == 'bot.cancel':
        answer = 'Действие отменено'
        sessionStorage[user_id]._STEP = prev_step(sessionStorage[user_id]._STEP)
        keyboard = get_keyboard(sessionStorage[user_id]._STEP, sessionStorage[user_id]._AUTH, msg_id)
        write_msg(event.user_id, answer, keyboard=keyboard)

    elif action == 'pool.add.num': # main_add
        num = int(payload['add_num'])

        lock.acquire() # Блокируем доступ
        if poolRecords[num][2] > 0:
            poolRecords[num][2] -= 1
            sessionStorage[user_id]._REC.append(num)
            answer = 'Вы записаны в бассейн ' + poolRecords[num][0] + ' в ' + poolRecords[num][1]
        else:
            answer = 'Извините, мест больше нет(('
        lock.release() # Разблокируем доступ

        sessionStorage[user_id]._STEP = prev_step(sessionStorage[user_id]._STEP)

        keyboard = get_keyboard(sessionStorage[user_id]._STEP, sessionStorage[user_id]._AUTH, msg_id)
        write_msg(event.user_id, answer, keyboard=keyboard)
        return

    elif action == 'pool.del.num': # main_del
        num = int(payload['del_num'])

        poolRecords[num][2] += 1
        sessionStorage[user_id]._REC.pop(sessionStorage[user_id]._REC.index(num))
        answer = 'Записьв бассейн ' + poolRecords[num][0] + ' в ' + poolRecords[num][1] + ' удалена'

        sessionStorage[user_id]._STEP = prev_step(sessionStorage[user_id]._STEP)

        keyboard = get_keyboard(sessionStorage[user_id]._STEP, sessionStorage[user_id]._AUTH, msg_id)
        write_msg(event.user_id, answer, keyboard=keyboard)
        return

    else:
        answer = 'Я вас не понимаю((\nПожалуйста, воспользуйтесь клавиатурой'
        if sessionStorage[user_id]._STEP == 'mainUS' or sessionStorage[user_id]._STEP == 'main':
            keyboard = get_keyboard(sessionStorage[user_id]._STEP, sessionStorage[user_id]._AUTH, msg_id)
            write_msg(event.user_id, answer, keyboard=keyboard)
        else:
            write_msg(event.user_id, answer)
        return
    
if __name__ == '__main__':
    main()
