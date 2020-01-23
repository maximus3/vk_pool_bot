from vk_api.keyboard import VkKeyboard, VkKeyboardColor

TOKEN = 'TOKEN'
TOKEN_AI = 'TOKEN_AI'

#directory = '/root/test_bot/'
directory = ''

version = '0.1.0 Beta'




# Keyboards

keyboard_main = VkKeyboard(one_time = False)
keyboard_main.add_button('Мои записи', color=VkKeyboardColor.DEFAULT, payload={'action': 'pool.show'})
keyboard_main.add_line()
keyboard_main.add_button('Зписаться в бассейн', color=VkKeyboardColor.POSITIVE, payload={'action': 'pool.add'})
keyboard_main.add_line()
keyboard_main.add_button('Удалить запись', color=VkKeyboardColor.NEGATIVE, payload={'action': 'pool.del'})
keyboard_main = keyboard_main.get_keyboard()


keyboard_uns = VkKeyboard(one_time = False)
keyboard_uns.add_button('Регистрация', color=VkKeyboardColor.DEFAULT, payload={'action': 'bot.reg'})
keyboard_uns = keyboard_uns.get_keyboard()

KDICT = {'main': keyboard_main, 'mainUS': keyboard_uns, '#all': VkKeyboard(one_time = True).get_empty_keyboard()}
