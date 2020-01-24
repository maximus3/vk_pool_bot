import time
import threading

from datetime import datetime, timedelta
from calendar import monthrange

month = {1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля', 5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа', 9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'}
month_im = {1: 'Январь', 2: 'Февраль', 3: 'Март', 4: 'Апрель', 5: 'Май', 6: 'Июнь', 7: 'Июль', 8: 'Август', 9: 'Сентябрь', 10: 'Октябрь', 11: 'Ноябрь', 12: 'Декабрь'}

def get_session_data():
    ans = []
    t = datetime.today()
    ans.append([t.year, t.month, t.day, monthrange(t.year, t.month)[1]])
    t -= timedelta(t.day - 1)
    t += timedelta(32)
    ans.append([t.year, t.month, 1, monthrange(t.year, t.month)[1]])
    t += timedelta(32)
    ans.append([t.year, t.month, 1, monthrange(t.year, t.month)[1]])
    return ans

class PoolTime:

    def __init__(self, year, mon, day, hour, mn, count):
        self._TIME = time.localtime(time.mktime((year, mon, day, hour, mn, 0, 0, 0, 0)))
        self._COUNT = count
        self._IDS = []

        # Замок для доступа к ресурсу
        self._LOCK = threading.Lock()

    def __len__(self):
        return self._COUNT

    def __str__(self):
        return self.get_day() + ' ' + self.get_time() + ' (свободно ' + str(self._COUNT) + ')'

    def get_day(self):
        return str(self._TIME.tm_mday) + ' ' + month[self._TIME.tm_mon] + ' ' + str(self._TIME.tm_year)

    def get_time(self):
        return time.strftime("%H:%M", self._TIME)

    def get_sec(self):
        return time.mktime(self._TIME)

    def get_show_data(self):
        answer = 'Дата: ' + self.get_day() + '\n'
        answer += 'Время: ' + self.get_time() + '\n'
        answer += '\n'
        return answer

    def add(self, user_id):
        self._IDS.append(user_id)
        self._COUNT -= 1

    def delete(self, user_id):
        self._COUNT += 1
        self._IDS.pop(self._IDS.index(user_id))
