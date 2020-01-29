class VkBot:

    def __init__(self, user_id, user_info):

        self._USER_ID = user_id # ID ользователя ВК
        self._FIRST_NAME = user_info[0]['first_name'] # Имя
        self._LAST_NAME = user_info[0]['last_name'] # Фамилия
        self._STEP = 'mainUS' # Шаг
        self._AUTH = False ###
        self._ADMIN = False # Админ-панель

        self._REC = [] # Записи

        self._KEYB = [] # Клавиши для клавиатуры
        self._PAGE = 1 # Страница клавиатуры
        self._COL = 1 # Колонки клавиатуры

        # ADMIN
        self._ADMIN_DATA = {} # Файлы для админов
        self._NOTIF = False

    def __str__(self):
        answer = 'User ID: ' + str(self._USER_ID) + '\n'
        answer += 'User: ' + self._FIRST_NAME + ' ' + self._LAST_NAME + '\n'
        answer += 'Step: ' + self._STEP + '\n'
        answer += 'Auth: ' + str(self._AUTH) + '\n'
        answer += 'Admin: ' + str(self._ADMIN) + '\n'
        answer += 'Link: @id' + str(self._USER_ID) + '\n'
        return answer

    def add_rec(self, sec):
        self._REC.append(sec)

    def get_name(self):
        return self._FIRST_NAME + ' ' + self._LAST_NAME

    def get_link(self):
        return '@id' + str(self._USER_ID)

    def get_backup_data(self):
        return [self._USER_ID, self._FIRST_NAME.encode('utf-8'), self._LAST_NAME.encode('utf-8'), self._STEP, self._AUTH, self._ADMIN, self._NOTIF]

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

    def notif(self):
        self._NOTIF = not self._NOTIF

    def out(self):
        self._AUTH = False
        self.set_step('mainUS')
        
