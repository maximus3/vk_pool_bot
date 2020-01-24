from vk_api.keyboard import VkKeyboard, VkKeyboardColor

TOKEN = 'TOKEN'

#directory = '/root/vk_bot/'
directory = ''

version = '0.2.0 Beta'

# ID ВК для админов
admin_ids = []

# Keyboards

keyboard_main = VkKeyboard(one_time = False)
keyboard_main.add_button('Мои записи', color=VkKeyboardColor.DEFAULT, payload={'action': 'pool.show'})
keyboard_main.add_line()
keyboard_main.add_button('Записаться в бассейн', color=VkKeyboardColor.POSITIVE, payload={'action': 'pool.add'})
keyboard_main.add_line()
keyboard_main.add_button('Удалить запись', color=VkKeyboardColor.NEGATIVE, payload={'action': 'pool.del'})
keyboard_main.add_line()
keyboard_main.add_button('Выход', color=VkKeyboardColor.PRIMARY, payload={'action': 'bot.out'})
keyboard_main = keyboard_main.get_keyboard()

keyboard_uns = VkKeyboard(one_time = False)
keyboard_uns.add_button('Регистрация', color=VkKeyboardColor.DEFAULT, payload={'action': 'bot.reg'})
keyboard_uns.add_line()
keyboard_uns.add_button('Админ-панель', color=VkKeyboardColor.PRIMARY, payload={'action': 'bot.admin'})
keyboard_uns = keyboard_uns.get_keyboard()

keyboard_admin = VkKeyboard(one_time = False)
keyboard_admin.add_button('Просмотр сеансов', color=VkKeyboardColor.PRIMARY, payload={'action': 'admin.show'})
keyboard_admin.add_line()
keyboard_admin.add_button('Добавить сеанс', color=VkKeyboardColor.PRIMARY, payload={'action': 'admin.add'})
keyboard_admin.add_line()
keyboard_admin.add_button('Удалить сеанс', color=VkKeyboardColor.PRIMARY, payload={'action': 'admin.del'})
keyboard_admin.add_line()
keyboard_admin.add_button('Уведомления (вкл/выкл)', color=VkKeyboardColor.PRIMARY, payload={'action': 'admin.notif'})
keyboard_admin.add_line()
keyboard_admin.add_button('Выход', color=VkKeyboardColor.PRIMARY, payload={'action': 'admin.out'})
keyboard_admin = keyboard_admin.get_keyboard()

KDICT = {'mainUS_admin': keyboard_admin, 'main': keyboard_main, 'mainUS': keyboard_uns, '#all': VkKeyboard(one_time = True).get_empty_keyboard()}
