import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, InputTextMessageContent, InlineQueryResultArticle
import json
from datetime import datetime
import os
from urllib.parse import quote
import uuid
import time
from telebot import types

# Инициализация бота
bot = telebot.TeleBot('7366514318:AAFNSvdBe5L9RM27mY9OnBEwRIH2dmizUVs')

# Хранение активных сессий просмотра
active_sessions = {}

class StreamSession:
    def __init__(self, url, creator_id, creator_name, title):
        self.url = url
        self.creator_id = creator_id
        self.creator_name = creator_name
        self.title = title
        self.viewers = {}  # {user_id: {'name': name, 'joined_at': time, 'last_active': time}}
        self.stream_start_time = int(time.time())  # Время начала трансляции
        self.is_active = True
        self.created_at = time.time()

    def add_viewer(self, user_id, user_name):
        """Добавляет зрителя в сессию"""
        if user_id not in self.viewers:
            self.viewers[user_id] = {
                'name': user_name,
                'joined_at': datetime.now().strftime("%H:%M:%S"),
                'last_active': time.time()
            }
            return True
        return False

    def remove_viewer(self, user_id):
        """Удаляет зрителя из сессии"""
        if user_id in self.viewers:
            del self.viewers[user_id]

    def get_current_stream_time(self):
        """Возвращает текущее время потока"""
        if not self.is_active:
            return 0
        return time.time() - self.stream_start_time

    def get_viewers_info(self):
        """Возвращает информацию о зрителях"""
        return [{'id': uid, 'name': info['name'], 'joined_at': info['joined_at']} 
                for uid, info in self.viewers.items()]

    def end_stream(self):
        """Завершает поток"""
        self.is_active = False
        return json.dumps({
            'type': 'stream_ended'
        })

    def deactivate(self):
        self.is_active = False

def create_invite_link(session_id):
    """Создает пригласительную ссылку для сессии"""
    return f"https://t.me/swensaiii_bot?start=join_{session_id}"

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

def create_watch_markup(session_id, user_id):
    """Создает клавиатуру для просмотра"""
    session = active_sessions[session_id]
    
    # Проверяем, активна ли сессия
    if not session.is_active:
        return None
    
    current_time = session.get_current_stream_time()
    
    webapp = WebAppInfo(
        url=f"{WEBAPP_URL}?session={session_id}&url={quote(session.url)}&st={session.stream_start_time}"
    )
    
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton(
            text="▶️ Открыть плеер",
            web_app=webapp
        )
    )
    
    # Добавляем кнопку для приглашения друзей
    markup.row(
        InlineKeyboardButton(
            text="📨 Отправить друзьям",
            switch_inline_query=f"share_{session_id}"
        )
    )
    
    # Добавляем кнопку завершения только для создателя
    if user_id == session.creator_id:
        markup.row(
            InlineKeyboardButton(
                text="🛑 Завершить трансляцию",
                callback_data=f"end_stream_{session_id}"
            )
        )
    
    return markup

# URL вашего веб-приложения
WEBAPP_URL = "https://swensi17.github.io/films-friends/player.html"

def broadcast_viewer_count(session_id):
    """Отправляет всем зрителям обновленное количество зрителей"""
    session = active_sessions[session_id]
    try:
        viewer_count = len(session.viewers)
        sync_message = json.dumps({
            'type': 'viewer_update',
            'count': viewer_count
        })
        
        for viewer_id in session.viewers:
            try:
                bot.send_message(
                    viewer_id,
                    sync_message,
                    parse_mode='HTML'
                )
            except Exception as e:
                print(f"Error sending viewer update to {viewer_id}: {e}")
    except Exception as e:
        print(f"Error broadcasting viewer count: {e}")

def broadcast_stream_end(session_id):
    """Отправляет всем зрителям сообщение о завершении стрима"""
    session = active_sessions[session_id]
    try:
        sync_message = json.dumps({
            'type': 'stream_ended'
        })
        
        for viewer_id in session.viewers:
            try:
                bot.send_message(
                    viewer_id,
                    "⚠️ Трансляция завершена!"
                )
                bot.send_message(
                    viewer_id,
                    sync_message,
                    parse_mode='HTML'
                )
            except Exception:
                pass
    except Exception as e:
        print(f"Error broadcasting stream end: {e}")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Проверяем, есть ли параметр присоединения к сессии
    args = message.text.split()
    if len(args) > 1 and args[1].startswith('join_'):
        session_id = args[1].replace('join_', '')
        if session_id in active_sessions:
            session = active_sessions[session_id]
            if not session.is_active:
                bot.reply_to(message, "❌ Эта сессия больше не активна. Попросите создателя отправить новую ссылку!")
                return
            if session.add_viewer(message.from_user.id, message.from_user.first_name):
                current_time = session.get_current_stream_time()
                webapp = WebAppInfo(
                    url=f"{WEBAPP_URL}?session={session_id}&url={quote(session.url)}&st={session.stream_start_time}"
                )
                
                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton(
                    text="▶️ Открыть плеер",
                    web_app=webapp
                ))
                
                response_text = (
                    f"✅ Вы присоединились к просмотру!\n"
                    f"👤 Создатель: {session.creator_name}\n"
                    f"👥 Зрителей: {len(session.viewers)}"
                )
                bot.reply_to(message, response_text, reply_markup=markup)
                
                # Уведомляем всех о новом зрителе
                broadcast_viewer_count(session_id)
            else:
                bot.reply_to(message, "❌ Вы уже присоединились к этой сессии")
        else:
            bot.reply_to(message, "❌ Сессия не найдена или устарела")
    else:
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
                f"🎥 {session.title}\n"
                f"👥 Зрителей: {len(session.viewers)}\n\n"
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
                if session.is_active:
                    markup.add(InlineKeyboardButton(
                        f"📺 {session.title} ({session.creator_name}) - 👥 {len(session.viewers)}",
                        callback_data=f"join_{session_id}"
                    ))
            bot.send_message(call.message.chat.id, "Доступные сессии:", reply_markup=markup)
        else:
            bot.send_message(call.message.chat.id, "🚫 Активных сессий пока нет")

    elif call.data.startswith("join_"):
        session_id = call.data.split("_")[1]
        if session_id in active_sessions:
            session = active_sessions[session_id]
            if session.add_viewer(call.from_user.id, call.from_user.first_name):
                markup = create_watch_markup(session_id, call.from_user.id)
                if markup is None:
                    bot.send_message(call.message.chat.id, "❌ Эта сессия больше не активна. Попросите создателя отправить новую ссылку!")
                    return
                bot.send_message(
                    call.message.chat.id,
                    f"✅ Вы присоединились к просмотру!\n🎬 {session.title}",
                    reply_markup=markup
                )
                # Уведомляем всех о новом зрителе
                broadcast_viewer_count(session_id)
            else:
                bot.send_message(call.message.chat.id, "❌ Вы уже присоединились к этой сессии")

    elif call.data.startswith("end_stream_"):
        session_id = call.data.split("_")[2]
        if session_id in active_sessions:
            session = active_sessions[session_id]
            if call.from_user.id == session.creator_id:
                end_message = session.end_stream()
                # Уведомляем всех зрителей
                for viewer_id in session.viewers:
                    try:
                        bot.send_message(viewer_id, end_message)
                    except Exception as e:
                        print(f"Error sending end message to {viewer_id}: {e}")
                
                bot.answer_callback_query(
                    call.id,
                    "✅ Трансляция успешно завершена"
                )
            else:
                bot.answer_callback_query(
                    call.id,
                    "❌ Только создатель может завершить трансляцию"
                )

@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    if message.text.startswith(('http://', 'https://')):
        # Деактивируем все старые сессии с этим URL
        for old_session_id, old_session in list(active_sessions.items()):
            if old_session.url == message.text:
                old_session.deactivate()
                # Немедленно завершаем старый стрим
                broadcast_stream_end(old_session_id)
                # Удаляем старую сессию
                active_sessions.pop(old_session_id, None)
                
                # Уведомляем всех участников старой сессии, кроме создателя новой сессии
                for viewer_id in old_session.viewers:
                    if viewer_id != message.from_user.id:  # Не отправляем создателю
                        try:
                            bot.send_message(
                                viewer_id,
                                "⚠️ Эта сессия завершена, так как создана новая. Присоединитесь к новой сессии!"
                            )
                        except Exception:
                            pass
        
        session_id = str(uuid.uuid4())
        session = StreamSession(
            url=message.text,
            creator_id=message.from_user.id,
            creator_name=message.from_user.first_name,
            title="Прямой эфир"
        )
        session.add_viewer(message.from_user.id, message.from_user.first_name)
        active_sessions[session_id] = session
        
        markup = create_watch_markup(session_id, message.from_user.id)
        invite_link = create_invite_link(session_id)
        
        response_text = (
            f"🎉 Стрим создан!\n"
            f"👤 Создатель: {session.creator_name}\n"
            f"👥 Зрителей: {len(session.viewers)}\n\n"
            f"🔗 Ссылка для приглашения друзей:\n{invite_link}"
        )
        
        bot.reply_to(message, response_text, reply_markup=markup)
        broadcast_viewer_count(session_id)
    elif message.text.startswith('/start'):
        args = message.text.split()
        if len(args) > 1 and args[1].startswith('join_'):
            session_id = args[1].replace('join_', '')
            if session_id in active_sessions:
                session = active_sessions[session_id]
                
                # Проверяем, не является ли пользователь создателем
                if message.from_user.id == session.creator_id:
                    markup = create_watch_markup(session_id, message.from_user.id)
                    bot.reply_to(
                        message,
                        "✅ Это ваш стрим. Нажмите кнопку ниже, чтобы открыть плеер:",
                        reply_markup=markup
                    )
                    return
                
                if not session.is_active:
                    bot.reply_to(message, "❌ Эта сессия больше не активна. Попросите создателя отправить новую ссылку!")
                    return
                if session.add_viewer(message.from_user.id, message.from_user.first_name):
                    markup = create_watch_markup(session_id, message.from_user.id)
                    
                    response_text = (
                        f"✅ Вы присоединились к просмотру!\n"
                        f"👤 Создатель: {session.creator_name}\n"
                        f"👥 Зрителей: {len(session.viewers)}\n\n"
                        f"Нажмите кнопку ниже, чтобы начать просмотр:"
                    )
                    bot.reply_to(message, response_text, reply_markup=markup)
                    
                    # Уведомляем всех о новом зрителе
                    broadcast_viewer_count(session_id)
                else:
                    bot.reply_to(message, "❌ Вы уже присоединились к этой сессии")
            else:
                bot.reply_to(message, "❌ Сессия не найдена или устарела")
        else:
            welcome_text = (
                "👋 Привет! Я бот для совместного просмотра видео.\n\n"
                "🎯 Что я умею:\n"
                "• Создавать комнаты для совместного просмотра\n"
                "• Синхронизировать просмотр с друзьями\n"
                "• Приглашать друзей в комнату\n\n"
                "📝 Как начать:\n"
                "1. Отправьте мне ссылку на видео\n"
                "2. Поделитесь ссылкой с друзьями\n"
                "3. Смотрите вместе в реальном времени!"
            )
            bot.reply_to(message, welcome_text)
    else:
        bot.reply_to(message, "❌ Пожалуйста, отправьте ссылку на видео для создания стрима")

@bot.message_handler(content_types=['web_app_data'])
def handle_webapp_data(message):
    """Обработка данных от веб-приложения"""
    try:
        data = json.loads(message.web_app_data.data)
        session_id = data.get('session_id')
        
        if not session_id or session_id not in active_sessions:
            return
        
        session = active_sessions[session_id]
        
        if data.get('type') == 'viewer_joined':
            if session.add_viewer(message.from_user.id, message.from_user.first_name):
                broadcast_viewer_count(session_id)
                # Отправляем время синхронизации
                sync_message = json.dumps({
                    'type': 'sync_time',
                    'server_time': time.time(),
                    'stream_start_time': session.stream_start_time
                })
                bot.send_message(
                    message.from_user.id,
                    sync_message,
                    parse_mode='HTML'
                )
        
        elif data.get('type') == 'viewer_left':
            if message.from_user.id in session.viewers:
                del session.viewers[message.from_user.id]
                broadcast_viewer_count(session_id)
        
        elif data.get('type') == 'viewer_active':
            if message.from_user.id in session.viewers:
                session.viewers[message.from_user.id]['last_active'] = time.time()
                broadcast_viewer_count(session_id)
    
    except Exception as e:
        print(f"Error handling webapp data: {e}")
        bot.reply_to(message, "❌ Произошла ошибка при обработке данных")

@bot.inline_handler(lambda query: query.query.startswith('share_'))
def share_session_inline(inline_query):
    try:
        session_id = inline_query.query.replace('share_', '')
        if session_id in active_sessions:
            session = active_sessions[session_id]
            if session.is_active:
                invite_link = create_invite_link(session_id)
                
                # Создаем текст приглашения
                share_text = (
                    f"🎬 Приглашаю тебя посмотреть видео вместе!\n"
                    f"👤 Создатель: {session.creator_name}\n"
                    f"👥 Зрителей: {len(session.viewers)}\n\n"
                    f"🔗 Присоединяйся: {invite_link}"
                )
                
                # Создаем результат для инлайн-режима
                result = InlineQueryResultArticle(
                    id=session_id,
                    title="Отправить приглашение",
                    description=f"Создатель: {session.creator_name} | Зрителей: {len(session.viewers)}",
                    input_message_content=InputTextMessageContent(share_text),
                    thumb_url="https://img.icons8.com/color/48/000000/cinema-.png",
                    reply_markup=InlineKeyboardMarkup().add(
                        InlineKeyboardButton("👋 Присоединиться", url=invite_link)
                    )
                )
                
                bot.answer_inline_query(
                    inline_query.id,
                    [result],
                    cache_time=0
                )
    except Exception as e:
        print(f"Error in share_session_inline: {e}")

# Запуск бота
bot.infinity_polling()
