import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id

from config import *
from TimeModule import *
from VkBot import *
from ai import *

# Логгирование
import logging
logging.basicConfig(format = u'%(filename)s[LINE:%(lineno)d]# %(levelname)-8s [%(asctime)s]  %(message)s', level = logging.INFO, filename = directory + 'vktestbot.log')

# Хранилище данных о сессиях
sessionStorage = {}

# Хранилище данных о возможных записях в бассейн
poolRecords = {}

def make_keyb(my_keyb, user_id, answer, col = 1):
    keyboard = VkKeyboard(one_time = False)
    last = True
    for i in range(min(8 * col, len(my_keyb))):
        keyboard.add_button(my_keyb[i]['label'], color=my_keyb[i]['color'], payload=my_keyb[i]['payload'])
        if (i + 1) % col == 0:
            keyboard.add_line()
            last = True
        else:
            last = False
    if len(my_keyb) > 8 * col:
        sessionStorage[user_id]._KEYB = my_keyb
        sessionStorage[user_id]._PAGE = 0
        sessionStorage[user_id]._COL = col
        keyboard.add_button('Далее ->', color=VkKeyboardColor.PRIMARY, payload={'action': 'bot.next_page', 'text': answer})
        keyboard.add_line()
    if not last:
        keyboard.add_line()
    keyboard.add_button('Отмена', color=VkKeyboardColor.PRIMARY, payload={'action': 'bot.cancel'})  
    return keyboard.get_keyboard()

def get_user_info(user_id):
    return vk.users.get(user_ids=user_id)

def get_keyboard(step):
    try:
        keyboard = KDICT[step]
    except Exception:
        keyboard = KDICT['#all']
    return keyboard
    
def write_msg(user_id, message, msg_id = None, keyboard = None):
    try:
        vk.messages.send(
            user_id=user_id,
            reply_to=msg_id,
            message=message,
            random_id=get_random_id(),
            keyboard=keyboard
        )
    except Exception:
        logging.error('Sending message to %d failed', user_id)
        print('ERROR: Sending message to %d failed', user_id)

# Авторизуемся как сообщество
vk_session = vk_api.VkApi(token=TOKEN)
vk = vk_session.get_api()

# Работа с сообщениями
longpoll = VkLongPoll(vk_session)

# ID для уведомлений о новых записях
notif_ids = []

logging.info('Server started')
print('Server started')

step_actions = {
        'mainUS': ['bot.reg', 'bot.admin'],
        'main': ['pool.show', 'pool.add', 'pool.del', 'bot.out'],
        'mainUS_admin': ['admin.show', 'admin.add', 'admin.del', 'admin.notif', 'admin.out'],
        'mainUS_admin_show': ['admin.show.num'],
        'mainUS_admin_add': ['admin.add.mon', 'admin.add.day', 'admin.add.hour', 'admin.add.min', 'admin.add.count'],
        'mainUS_admin_del': ['admin.del.num'],
        'main_add': ['pool.add.num'],
        'main_del': ['pool.del.num']
    }

def wrong_step(step, action):
    if action == None:
        return False
    if action in ['bot.next_page', 'bot.prev_page', 'bot.cancel'] and step not in ['mainUS', 'main', 'mainUS_admin']:
        return False
    if action not in step_actions.get(step):
        return True
    return False

def main():
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            
            logging.info('longpoll [%s]: New message: {%s}', str(event.user_id), event.text.encode('utf-8'))

            user_id = event.user_id
            if sessionStorage.get(user_id) == None:
                sessionStorage[user_id] = VkBot(user_id, get_user_info(user_id))

            msg_handler(event)
            continue

def admin_menu(event):
    user_id = event.user_id
    text = event.text
    msg_id = event.message_id
    step = sessionStorage[user_id]._STEP
    if 'payload' in dir(event):
        payload = eval(event.payload)
    else:
        payload = None
    action = None
    if payload:
        action = payload.get('action')

    if action == None and step == 'mainUS_admin_delconf':
        num = sessionStorage[user_id]._ADMIN_DATA.pop('num')
        if text == 'УДАЛИТЬ':
            poolRecords[num]._LOCK.acquire() # Блокируем доступ
            for ids in poolRecords[num]._IDS:
                sessionStorage[ids]._REC.remove(num)
            poolRecords.pop(num)
            answer = 'Сеанс удален'
        else:
            answer = 'Действие отменено'
            
        sessionStorage[user_id].prev_step()
        keyboard = get_keyboard(sessionStorage[user_id]._STEP)
        write_msg(event.user_id, answer, keyboard=keyboard)
        return

    elif action == 'admin.show':
        sessionStorage[user_id].next_step('show')
        answer = 'Список сеансов:\n\n'
        my_keyb = []
        #my_keyb.append({'label': 'Показать все', 'color': VkKeyboardColor.PRIMARY, 'payload': {'action': 'admin.show.all'}})
        for sec in sorted(poolRecords):
            try:
                date = poolRecords[sec].get_day() + ' ' + poolRecords[sec].get_time()
                color = VkKeyboardColor.PRIMARY
                my_keyb.append({'label': date, 'color': color, 'payload': {'action': 'admin.show.num', 'num': sec}})
                answer += str(poolRecords[sec]) + '\n'
            except KeyError: # Сеанс удален
                pass
        if len(my_keyb) == 0:
            answer = 'Сеансов не найдено'
            sessionStorage[user_id].prev_step()
            keyboard = get_keyboard(sessionStorage[user_id]._STEP)
        else:
            answer += '\nВыберите сеанс'
            keyboard = make_keyb(my_keyb, user_id, 'Выберите сеанс')
        write_msg(event.user_id, answer, keyboard=keyboard)
        return

    #elif action == 'admin.show.all': ###
    #    answer = 'pass'
    #    sessionStorage[user_id].prev_step()
    #    keyboard = get_keyboard(sessionStorage[user_id]._STEP)
    #    write_msg(event.user_id, answer, keyboard=keyboard)
    #    return

    elif action == 'admin.show.num':
        num = payload['num']
        try:
            answer = poolRecords[num].get_show_data() + 'Список участников:\n'
            for ids in poolRecords[num]._IDS:
                answer += sessionStorage[ids].get_name() + ' ' + sessionStorage[ids].get_link() + '\n'
            if len(poolRecords[num]._IDS) == 0:
                answer += 'Участников нет'
        except KeyError: # Сеанс удален
            answer = 'Извините, сеанс удален'
        sessionStorage[user_id].prev_step()
        keyboard = get_keyboard(sessionStorage[user_id]._STEP)
        write_msg(event.user_id, answer, keyboard=keyboard)
        return

    elif action == 'admin.add':
        sessionStorage[user_id].next_step('add')
        data = get_session_data()
        my_keyb = []
        for i in range(len(data)):
            label = month_im[data[i][1]] + ' ' + str(data[i][0])
            color = VkKeyboardColor.PRIMARY
            my_keyb.append({'label': label, 'color': color, 'payload': {'action': 'admin.add.mon', 'num': i}})
        sessionStorage[user_id]._ADMIN_DATA['add'] = data
        answer = 'Выберите месяц'
        keyboard = make_keyb(my_keyb, user_id, answer)
        write_msg(event.user_id, answer, keyboard=keyboard)
        return

    elif action == 'admin.add.mon': 
        num = payload['num']
        data = sessionStorage[user_id]._ADMIN_DATA['add'][num]
        my_keyb = []
        for i in range(data[2], data[3] + 1):
            label = str(i)
            color = VkKeyboardColor.PRIMARY
            my_keyb.append({'label': label, 'color': color, 'payload': {'action': 'admin.add.day', 'num': i}})
        sessionStorage[user_id]._ADMIN_DATA['add'] = data
        answer = 'Выберите дату'
        keyboard = make_keyb(my_keyb, user_id, answer, 4)
        write_msg(event.user_id, answer, keyboard=keyboard)
        return

    elif action == 'admin.add.day': 
        day = payload['num']
        sessionStorage[user_id]._ADMIN_DATA['add'].pop()
        sessionStorage[user_id]._ADMIN_DATA['add'].pop()
        sessionStorage[user_id]._ADMIN_DATA['add'].append(day)
        my_keyb = []
        for i in range(6, 22):
            label = str(i)
            color = VkKeyboardColor.PRIMARY
            my_keyb.append({'label': label, 'color': color, 'payload': {'action': 'admin.add.hour', 'num': i}})
        answer = 'Выберите время (часы)'
        keyboard = make_keyb(my_keyb, user_id, answer, 2)
        write_msg(event.user_id, answer, keyboard=keyboard)
        return

    elif action == 'admin.add.hour': 
        hour = payload['num']
        sessionStorage[user_id]._ADMIN_DATA['add'].append(hour)
        my_keyb = []
        for i in range(0, 60, 5):
            label = str(i)
            color = VkKeyboardColor.PRIMARY
            my_keyb.append({'label': label, 'color': color, 'payload': {'action': 'admin.add.min', 'num': i}})
        answer = 'Выберите время (минуты)'
        keyboard = make_keyb(my_keyb, user_id, answer, 2)
        write_msg(event.user_id, answer, keyboard=keyboard)
        return

    elif action == 'admin.add.min': 
        mn = payload['num']
        sessionStorage[user_id]._ADMIN_DATA['add'].append(mn)
        my_keyb = []
        for i in range(32, 0, -1):
            label = str(i)
            color = VkKeyboardColor.PRIMARY
            my_keyb.append({'label': label, 'color': color, 'payload': {'action': 'admin.add.count', 'num': i}})
        answer = 'Выберите количество свободных мест'
        keyboard = make_keyb(my_keyb, user_id, answer, 4)
        write_msg(event.user_id, answer, keyboard=keyboard)
        return

    elif action == 'admin.add.count': 
        count = payload['num']
        sessionStorage[user_id]._ADMIN_DATA['add'].append(count)
        elem = sessionStorage[user_id]._ADMIN_DATA.pop('add')
        t = PoolTime(elem[0], elem[1], elem[2], elem[3], elem[4], elem[5])
        poolRecords[t.get_sec()] = t
        answer = 'Сеанс ' + str(t) + ' добавлен'
        sessionStorage[user_id].prev_step()
        keyboard = get_keyboard(sessionStorage[user_id]._STEP)
        write_msg(event.user_id, answer, keyboard=keyboard)
        return

    elif action == 'admin.del':
        sessionStorage[user_id].next_step('del')
        my_keyb = []
        for sec in sorted(poolRecords):
            try:
                date = str(poolRecords[sec])
                color = VkKeyboardColor.PRIMARY
                my_keyb.append({'label': date, 'color': color, 'payload': {'action': 'admin.del.num', 'num': sec}})
            except KeyError: # Сеанс удален
                pass
        if len(my_keyb) == 0:
            answer = 'Сеансов не найдено'
            sessionStorage[user_id].prev_step()
            keyboard = get_keyboard(sessionStorage[user_id]._STEP)
        else:
            answer = 'Выберите сеанс, который хотите удалить'
            keyboard = make_keyb(my_keyb, user_id, answer)
        write_msg(event.user_id, answer, keyboard=keyboard)
        return

    elif action == 'admin.del.num':
        sessionStorage[user_id].prev_step()
        sessionStorage[user_id].next_step('delconf')
        num = payload['num']
        try:
            answer = poolRecords[num].get_show_data()
            answer += 'Вы уверены, что хотите удалить сеанс? Отмена невозможна!\n'
            answer += 'Подтвердите удаление, написав УДАЛИТЬ'
            sessionStorage[user_id]._ADMIN_DATA['num'] = num
            keyboard = make_keyb([], user_id, '')
        except KeyError: # Сеанс удален
            answer = 'Сеанс уже удален'
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

    elif action == 'admin.notif': 
        if user_id in notif_ids:
            notif_ids.remove(user_id)
            answer = 'Уведомления о новых записях выключены'
        else:
            notif_ids.append(user_id)
            answer = 'Уведомления о новых записях включены'
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
    step = sessionStorage[user_id]._STEP
    if 'payload' in dir(event):
        payload = eval(event.payload)
    else:
        payload = None

    action = None

    if payload:
        action = payload.get('action')

    if wrong_step(step, action):
        return

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

    if action == 'bot.next_page': # НЕДОДЕЛАНО: Колонки
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

    elif action == 'bot.prev_page': # НЕДОДЕЛАНО: Колонки
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
                answer = 'Регистрация не удалась(((\nОбратитесь к администратору'

            keyboard = get_keyboard(sessionStorage[user_id]._STEP)
            write_msg(event.user_id, answer, keyboard=keyboard)
            return

        elif action == 'bot.admin':
            sessionStorage[user_id].next_step('admin')
            if user_id not in admin_ids:
                answer = 'Доступ запрещен'
                sessionStorage[user_id].prev_step()
            else:
                answer = 'Добро пожаловать!'
                sessionStorage[user_id]._ADMIN = True
            keyboard = get_keyboard(sessionStorage[user_id]._STEP)
            write_msg(event.user_id, answer, keyboard=keyboard)
            return

        elif action == 'bot.auth': # НЕДОДЕЛАНО: Регистрация
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
            try:
                answer += poolRecords[sec].get_show_data()
            except KeyError: # Сеанс удален
                pass
        if len(sessionStorage[user_id]._REC) == 0:
            answer = 'У вас нет записей'
        
        keyboard = get_keyboard(sessionStorage[user_id]._STEP)
        write_msg(event.user_id, answer, keyboard=keyboard)
        return

    elif action == 'pool.add': # main
        sessionStorage[user_id].next_step('add')
        my_keyb = []
        for sec in sorted(poolRecords):
            try:
                if len(poolRecords[sec]) > 0 and (sec not in sessionStorage[user_id]._REC):
                    date = str(poolRecords[sec])
                    color = VkKeyboardColor.NEGATIVE
                    if len(poolRecords[sec]) > 10:
                        color = VkKeyboardColor.POSITIVE
                    elif len(poolRecords[sec]) > 5:
                        color = VkKeyboardColor.DEFAULT
                    my_keyb.append({'label': date, 'color': color, 'payload': {'action': 'pool.add.num', 'num': sec}})
            except KeyError: # Сеанс удален
                pass
        if len(my_keyb) == 0:
            answer = 'Доступных записей нет'
            sessionStorage[user_id].prev_step()
            keyboard = get_keyboard(sessionStorage[user_id]._STEP)
        else:
            answer = 'Выберите доступное время'
            keyboard = make_keyb(my_keyb, user_id, answer)
                
        write_msg(event.user_id, answer, keyboard=keyboard)
        return

    elif action == 'pool.del': # main
        sessionStorage[user_id].next_step('del')
        my_keyb = []
        for sec in sessionStorage[user_id]._REC:
            try:
                date = poolRecords[sec].get_day() + ' ' + poolRecords[sec].get_time()
                color = VkKeyboardColor.DEFAULT
                my_keyb.append({'label': date, 'color': color, 'payload': {'action': 'pool.del.num', 'num': sec}})
            except KeyError: # Сеанс удален
                pass
        if len(my_keyb) == 0:
            answer = 'У вас нет ни одной записи'
            sessionStorage[user_id].prev_step()
            keyboard = get_keyboard(sessionStorage[user_id]._STEP)
        else:
            answer = 'Выберите запись, которую хотите удалить'
            keyboard = make_keyb(my_keyb, user_id, answer)
                
        write_msg(event.user_id, answer, keyboard=keyboard)
        return

    elif action == 'pool.add.num': # main_add
        num = int(payload['num'])
        success = False
        try:
            poolRecords[num]._LOCK.acquire() # Блокируем доступ
            if len(poolRecords[num]) > 0:
                poolRecords[num].add(user_id)
                sessionStorage[user_id]._REC.append(num)
                answer = 'Вы записаны в бассейн ' + poolRecords[num].get_day() + ' в ' + poolRecords[num].get_time()
                answer_notif = 'Пользователь ' + sessionStorage[user_id].get_name() + \
                               ' ' + sessionStorage[user_id].get_link() + \
                               ' записан в бассейн ' +  \
                               poolRecords[num].get_day() + ' в ' + poolRecords[num].get_time()
                success = True
            else:
                answer = 'Извините, мест больше нет(('
            poolRecords[num]._LOCK.release() # Разблокируем доступ
        except KeyError: # Сеанс удален
            answer = 'Извините, мест больше нет(('

        sessionStorage[user_id].prev_step()

        keyboard = get_keyboard(sessionStorage[user_id]._STEP)
        write_msg(event.user_id, answer, keyboard=keyboard)
        if success:
            for ids in notif_ids:
                write_msg(ids, answer_notif)
        return

    elif action == 'pool.del.num': # main_del
        num = int(payload['num'])
        try:
            poolRecords[num]._LOCK.acquire() # Блокируем доступ
            poolRecords[num].delete(user_id)
            sessionStorage[user_id]._REC.remove(num)
            answer = 'Запись в бассейн ' + poolRecords[num].get_day() + ' в ' + poolRecords[num].get_time() + ' удалена'
            poolRecords[num]._LOCK.release() # Разблокируем доступ
        except KeyError: # Сеанс удален
            sessionStorage[user_id]._REC.remove(num)
            answer = 'Запись в бассейн удалена'

        sessionStorage[user_id].prev_step()

        keyboard = get_keyboard(sessionStorage[user_id]._STEP)
        write_msg(event.user_id, answer, keyboard=keyboard)
        return

    elif action == 'bot.out': # Восстановление данных
        sessionStorage[user_id].out()
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
        (2020, 2, 25, 15, 00, 24),
        (2020, 2, 25, 19, 00, 2),
        (2020, 2, 29, 15, 00, 13),
        (2020, 2, 29, 19, 00, 4),
        (2020, 3, 1, 15, 00, 4),
        (2020, 3, 2, 19, 00, 2),
        (2020, 3, 3, 15, 00, 3),
        (2020, 3, 4, 19, 00, 1),
        (2020, 3, 5, 15, 00, 2),
        (2020, 3, 6, 15, 00, 1),
        (2020, 3, 6, 19, 00, 1)
    ]

for elem in base_data:
    t = PoolTime(elem[0], elem[1], elem[2], elem[3], elem[4], elem[5])
    poolRecords[t.get_sec()] = t
    
if __name__ == '__main__':
    main()

