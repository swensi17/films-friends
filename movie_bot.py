import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import json
from datetime import datetime
import os
from urllib.parse import quote

# Инициализация бота
bot = telebot.TeleBot('7366514318:AAFNSvdBe5L9RM27mY9OnBEwRIH2dmizUVs')

# Хранение активных сессий просмотра
active_sessions = {}

# URL вашего веб-приложения
WEBAPP_URL = "https://swensi17.github.io/films-friends/player.html"

def create_invite_link(session_id):
    """Создает пригласительную ссылку для сессии"""
    return f"https://t.me/your_bot_username?start=join_{session_id}"

def create_main_markup():
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton("🎬 Создать просмотр", callback_data="create_watch"),
        InlineKeyboardButton("🔗 Присоединиться", callback_data="join_watch"),
        InlineKeyboardButton("📋 Активные сессии", callback_data="list_sessions"),
        InlineKeyboardButton("ℹ️ Помощь", callback_data="help")
    )
    return markup

def create_watch_markup(session_id):
    markup = InlineKeyboardMarkup()
    session = active_sessions.get(session_id)
    if session:
        webapp = WebAppInfo(url=f"{WEBAPP_URL}?session={session_id}&url={quote(session['url'])}")
        markup.add(InlineKeyboardButton(
            text="▶️ Открыть плеер",
            web_app=webapp
        ))
        markup.add(
            InlineKeyboardButton("📨 Пригласить друзей", callback_data=f"invite_{session_id}"),
            InlineKeyboardButton("💬 Чат просмотра", callback_data=f"chat_{session_id}")
        )
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Проверяем, есть ли параметр присоединения к сессии
    args = message.text.split()
    if len(args) > 1 and args[1].startswith('join_'):
        session_id = args[1].replace('join_', '')
        if session_id in active_sessions:
            session = active_sessions[session_id]
            if message.from_user.id not in session['viewers']:
                session['viewers'].append(message.from_user.id)
            
            # Отправляем информацию о сессии
            response_text = (
                f"🎉 Вы присоединились к просмотру!\n"
                f"🎬 Название: {session['title']}\n"
                f"👤 Создатель: {session['creator_name']}\n"
                f"👥 Зрителей: {len(session['viewers'])}"
            )
            bot.send_message(message.chat.id, response_text, reply_markup=create_watch_markup(session_id))
            
            # Уведомляем создателя о новом зрителе
            bot.send_message(
                session['creator_id'],
                f"👋 {message.from_user.first_name} присоединился к просмотру!"
            )
            return

    welcome_text = (
        "👋 Привет! Я бот для совместного просмотра фильмов и сериалов.\n\n"
        "🎯 Что я умею:\n"
        "• Создавать комнаты для совместного просмотра\n"
        "• Синхронизировать просмотр с друзьями\n"
        "• Отправлять приглашения друзьям\n"
        "• Общаться в чате во время просмотра\n\n"
        "Выберите действие:"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=create_main_markup())

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if call.data == "create_watch":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, 
            "🎬 Отправьте ссылку на фильм или сериал, который хотите посмотреть")
    
    elif call.data.startswith("invite_"):
        session_id = call.data.split("_")[1]
        if session_id in active_sessions:
            session = active_sessions[session_id]
            invite_link = create_invite_link(session_id)
            share_text = (
                f"🎬 Приглашение на совместный просмотр\n\n"
                f"Присоединяйся ко мне! Мы смотрим:\n"
                f"🎥 {session['title']}\n"
                f"👥 Зрителей: {len(session['viewers'])}\n\n"
                f"🔗 Ссылка для присоединения:\n{invite_link}"
            )
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(
                "📤 Поделиться приглашением",
                switch_inline_query=share_text
            ))
            bot.send_message(
                call.message.chat.id,
                f"📨 Отправьте это приглашение друзьям:\n\n{share_text}",
                reply_markup=markup
            )
            
    elif call.data == "join_watch":
        bot.answer_callback_query(call.id)
        if active_sessions:
            markup = InlineKeyboardMarkup()
            for session_id, session in active_sessions.items():
                markup.add(InlineKeyboardButton(
                    f"📺 {session['title']} ({session['creator_name']}) - 👥 {len(session['viewers'])}",
                    callback_data=f"join_{session_id}"
                ))
            bot.send_message(call.message.chat.id, "Доступные сессии:", reply_markup=markup)
        else:
            bot.send_message(call.message.chat.id, "🚫 Активных сессий пока нет")

    elif call.data.startswith("join_"):
        session_id = call.data.split("_")[1]
        if session_id in active_sessions:
            session = active_sessions[session_id]
            if call.from_user.id not in session['viewers']:
                session['viewers'].append(call.from_user.id)
            markup = create_watch_markup(session_id)
            bot.send_message(
                call.message.chat.id,
                f"✅ Вы присоединились к просмотру!\n🎬 {session['title']}",
                reply_markup=markup
            )
            # Уведомляем создателя
            bot.send_message(
                session['creator_id'],
                f"👋 {call.from_user.first_name} присоединился к просмотру!"
            )

@bot.message_handler(content_types=['web_app_data'])
def handle_webapp_data(message):
    try:
        data = json.loads(message.web_app_data.data)
        session_id = data.get('session_id')
        action = data.get('action')
        
        if action == 'sync':
            current_time = data.get('currentTime')
            if session_id in active_sessions:
                session = active_sessions[session_id]
                for viewer_id in session['viewers']:
                    if viewer_id != message.from_user.id:
                        bot.send_message(
                            viewer_id,
                            f"⏱ Синхронизация времени: {current_time} секунд"
                        )
        
        elif action == 'chat_message':
            if session_id in active_sessions:
                session = active_sessions[session_id]
                for viewer_id in session['viewers']:
                    if viewer_id != message.from_user.id:
                        bot.send_message(
                            viewer_id,
                            f"💬 {message.from_user.first_name}: {data.get('message')}"
                        )

    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка обработки данных: {str(e)}")

@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    if message.text.startswith(('http://', 'https://')):
        session_id = str(len(active_sessions) + 1)
        active_sessions[session_id] = {
            'url': message.text,
            'creator_id': message.from_user.id,
            'creator_name': message.from_user.first_name,
            'title': f"Сессия #{session_id}",
            'created_at': datetime.now().strftime("%H:%M:%S"),
            'viewers': [message.from_user.id]
        }
        
        markup = create_watch_markup(session_id)
        
        response_text = (
            f"🎉 Сессия создана!\n"
            f"🔗 Ссылка: {message.text[:50]}...\n"
            f"👤 Создатель: {message.from_user.first_name}\n"
            f"⏰ Время создания: {active_sessions[session_id]['created_at']}\n\n"
            f"📨 Нажмите 'Пригласить друзей', чтобы позвать других зрителей!"
        )
        
        bot.reply_to(message, response_text, reply_markup=markup)
    else:
        bot.reply_to(message, "❌ Пожалуйста, отправьте корректную ссылку на видео")

# Запуск бота
bot.infinity_polling()
