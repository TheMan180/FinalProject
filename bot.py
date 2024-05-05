import telebot
from telebot import TeleBot
from yandex_gpt import ask_gpt
from creds import get_bot_token
from validators import *
from database import add_message, select_n_last_messages
from speechkit import speech_to_text, text_to_speech
from config import COUNT_LAST_MSG

bot = TeleBot(get_bot_token())



def create_keyboard(keyboard_list):
    keyboard = telebot.types.ReplyKeyboardMarkup(True, True)
    for row in keyboard_list:
        keyboard.row(*row)
    return keyboard

@bot.message_handler(commands=['start'])
def start(message):
    keyboard1 = create_keyboard([['Начать']])
    bot.send_message(message.chat.id, 'Добро пожаловать! Нажмите "Начать", чтобы продолжить.', reply_markup=keyboard1)
keyboard1 = telebot.types.ReplyKeyboardMarkup(True,True)
keyboard1.row("Начать")


@bot.message_handler(func=lambda: True)
def handler(message):
    bot.send_message(message.from_user.id, "Отправь мне голосовое или текстовое сообщение, и я тебе отвечу")
@bot.message_handler(content_types=['text'])
def handle_text(message):
    try:
        user_id = message.from_user.id
        status_check_users, error_message = check_number_of_users(user_id)
        if not status_check_users:
            bot.send_message(user_id, error_message)
            return

        full_user_message = [message.text, 'user', 0, 0, 0]
        add_message(user_id=user_id, full_message=full_user_message)
        last_messages, total_spent_tokens = select_n_last_messages(user_id, COUNT_LAST_MSG)
        total_gpt_tokens, error_message = is_gpt_token_limit(last_messages, total_spent_tokens)
        if error_message:
            bot.send_message(user_id, error_message)
            return

        status_gpt, answer_gpt, tokens_in_answer = ask_gpt(last_messages)
        if not status_gpt:
            bot.send_message(user_id, answer_gpt)
            return
        total_gpt_tokens += tokens_in_answer

        full_gpt_message = [answer_gpt, 'assistant', total_gpt_tokens, 0, 0]
        add_message(user_id=user_id, full_message=full_gpt_message)

        bot.send_message(user_id, answer_gpt, reply_to_message_id=message.id)
    except Exception as e:
        logging.error(e)
        bot.send_message(message.from_user.id, "Не получилось ответить. Попробуй написать другое сообщение")
@bot.message_handler(content_types=['voice'])
def handle_voice(message: telebot.types.Message, user_id):
    try:
        user_id = message.from_user.id

        file_id = message.voice.file_id
        file_info = bot.get_file(file_id)
        file = bot.download_file(file_info.file_path)
        status_stt, stt_text = speech_to_text(file)
        if not status_stt:
            bot.send_message(user_id, stt_text)
            return

        last_messages, total_spent_tokens = select_n_last_messages(user_id, COUNT_LAST_MSG)
        total_gpt_tokens, error_message = is_gpt_token_limit(last_messages, total_spent_tokens)
        if error_message:
            bot.send_message(user_id, error_message)
            return

        status_gpt, answer_gpt, tokens_in_answer = ask_gpt(last_messages)
        if not status_gpt:
            bot.send_message(user_id, answer_gpt)
            return
        total_gpt_tokens += tokens_in_answer

        if error_message:
            bot.send_message(user_id, error_message)
            return

        status_tts, voice_response = text_to_speech(answer_gpt)
        if status_tts:
            bot.send_voice(user_id, voice_response, reply_to_message_id=message.id)
        else:
            bot.send_message(user_id, answer_gpt, reply_to_message_id=message.id)
    except Exception as e:
        logging.error(e)
        bot.send_message(user_id, "Не получилось ответить. Попробуй записать другое сообщение")
@bot.message_handler(content_types=["text"])
def txt(message):

    messages = [
        {"role": "user", "text": message.text}
    ]

    status, answer = ask_gpt(messages)
    if status:
        bot.send_message(message.from_user.id, answer)
    else:
        bot.send_message(message.from_user.id, "Ошибка(")

bot.polling()
