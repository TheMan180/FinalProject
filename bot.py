import telebot
from telebot import TeleBot
from telebot.types import ReplyKeyboardMarkup
from validators import *
from database import *
from config import *
from yandex_gpt import *
from speechkit import *
import logging


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="w",
    filename="logs.txt"

)

bot = TeleBot(TOKEN)
path_to_db = DB_FILE


def create_keyboard(keyboard_list):
    keyboard = ReplyKeyboardMarkup(True, True)
    for row in keyboard_list:
        keyboard.row(*row)
    return keyboard


@bot.message_handler(commands=['start'])
def start(message):
    keyboard1 = create_keyboard([['Начать']])
    bot.send_message(message.chat.id, 'Добро пожаловать! Нажмите "Начать", чтобы продолжить.', reply_markup=keyboard1)


@bot.message_handler(commands=["debug"])
def send_debug(message):
    user_id = message.from_user.id
    with open("logs.txt", "rb") as f:
        bot.send_document(user_id, f)


@bot.message_handler(commands=['tts'])
def tts_handler(message):
    user_id = message.from_user.id
    bot.send_message(user_id, 'Отправь следующим сообщеним текст, чтобы я его озвучил!')
    bot.register_next_step_handler(message, tts)


def tts(message):
    user_id = message.from_user.id
    text = message.text
    if message.content_type != 'text':
        bot.send_message(user_id, 'Отправь текстовое сообщение')
        return
    status_check_users, error_message = check_number_of_users(user_id)
    if not status_check_users:
        bot.send_message(user_id, error_message)
        return
    tts_symbols, error_message = is_tts_symbol_limit(user_id, text)
    if not error_message:
        full_user_message = [text, 'user_tts', 0, tts_symbols, 0]
        add_message(user_id=user_id, full_message=full_user_message)
        status, content = text_to_speech(text)
        if status:
            bot.send_voice(user_id, content, reply_to_message_id=message.id)
            return
        error_message = content
    bot.send_message(user_id, error_message)


@bot.message_handler(commands=['stt'])
def stt_handler(message):
    user_id = message.from_user.id
    bot.send_message(user_id, 'Отправь голосовое сообщение, чтобы я его распознал!')
    bot.register_next_step_handler(message, stt)


def stt(message):
    user_id = message.from_user.id
    if not message.voice:
        return
    status_check_users, error_message = check_number_of_users(user_id)
    if not status_check_users:
        bot.send_message(user_id, error_message)
        return
    stt_blocks, error_message = is_stt_block_limit(user_id, message.voice.duration)
    if error_message:
        bot.send_message(user_id, error_message)
        return
    file_id = message.voice.file_id
    file_info = bot.get_file(file_id)
    file = bot.download_file(file_info.file_path)
    status_stt, stt_text = speech_to_text(file)
    if not status_stt:
        bot.send_message(user_id, stt_text)
        return
    full_user_message = [stt_text, 'user_stt', 0, 0, stt_blocks]
    add_message(user_id=user_id, full_message=full_user_message)
    bot.send_message(user_id, stt_text, reply_to_message_id=message.id)


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
def handle_voice(message):
    try:
        user_id = message.from_user.id
        status_check_users, error_message = check_number_of_users(user_id)
        if not status_check_users:
            bot.send_message(user_id, error_message)
            return

        stt_blocks, error_message = is_stt_block_limit(user_id, message.voice.duration)
        if error_message:
            bot.send_message(user_id, error_message)
            return

        file_id = message.voice.file_id
        file_info = bot.get_file(file_id)
        file = bot.download_file(file_info.file_path)
        status_stt, stt_text = speech_to_text(file)
        if not status_stt:
            bot.send_message(user_id, stt_text)
            return

        add_message(user_id=user_id, full_message=[stt_text, 'user', 0, 0, stt_blocks])

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

        tts_symbols, error_message = is_tts_symbol_limit(user_id, answer_gpt)

        add_message(user_id=user_id, full_message=[answer_gpt, 'assistant', total_gpt_tokens, tts_symbols, 0])

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


@bot.message_handler(func=lambda: True)
def handler(message):
    bot.send_message(message.from_user.id, "Отправь мне голосовое или текстовое сообщение, и я тебе отвечу")


create_database()
bot.polling()
