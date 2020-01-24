import apiai
import json

TOKEN_AI = 'TOKEN_AI'

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
