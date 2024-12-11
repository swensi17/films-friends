import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import json
from datetime import datetime
import os
from urllib.parse import quote
import uuid

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
        self.created_at = datetime.now().strftime("%H:%M:%S")
        self.viewers = {}  # {user_id: {'name': name, 'joined_at': time}}
        self.current_time = 0
        self.start_timestamp = datetime.now().timestamp()
        self.is_active = True

    def add_viewer(self, user_id, user_name):
        """Добавляет зрителя в сессию"""
        if user_id not in self.viewers:
            self.viewers[user_id] = {
                'name': user_name,
                'joined_at': datetime.now().strftime("%H:%M:%S")
            }

    def remove_viewer(self, user_id):
        """Удаляет зрителя из сессии"""
        if user_id in self.viewers:
            del self.viewers[user_id]

    def get_current_stream_time(self):
        """Возвращает текущее время потока"""
        if not self.is_active:
            return self.current_time
        elapsed = datetime.now().timestamp() - self.start_timestamp
        return elapsed

    def get_viewers_info(self):
        """Возвращает информацию о зрителях"""
        return [{'id': uid, 'name': info['name'], 'joined_at': info['joined_at']} 
                for uid, info in self.viewers.items()]

    def end_stream(self):
        """Завершает поток"""
        self.is_active = False
        self.current_time = self.get_current_stream_time()

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
    markup = InlineKeyboardMarkup()
    session = active_sessions.get(session_id)
    if session:
        webapp = WebAppInfo(url=f"{WEBAPP_URL}?session={session_id}&url={quote(session.url)}&t={session.current_time}")
        markup.add(InlineKeyboardButton(
            text="▶️ Открыть плеер",
            web_app=webapp
        ))
        markup.add(
            InlineKeyboardButton("📨 Пригласить друзей", callback_data=f"invite_{session_id}"),
            InlineKeyboardButton("💬 Чат просмотра", callback_data=f"chat_{session_id}")
        )
        # Добавляем кнопки управления только для создателя
        if session.creator_id == user_id:
            markup.add(
                InlineKeyboardButton("⏯️ Пауза/Продолжить", callback_data=f"toggle_play_{session_id}"),
                InlineKeyboardButton("🔄 Перезапустить", callback_data=f"restart_{session_id}"),
                InlineKeyboardButton("🛑️ Завершить поток", callback_data=f"end_stream_{session_id}")
            )
    return markup

# URL вашего веб-приложения
WEBAPP_URL = "https://swensi17.github.io/films-friends/player.html"

@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Проверяем, есть ли параметр присоединения к сессии
    args = message.text.split()
    if len(args) > 1 and args[1].startswith('join_'):
        session_id = args[1].replace('join_', '')
        if session_id in active_sessions:
            session = active_sessions[session_id]
            if message.from_user.id not in session.viewers:
                session.add_viewer(message.from_user.id, message.from_user.first_name)
            
            # Отправляем информацию о сессии
            response_text = (
                f"🎉 Вы присоединились к просмотру!\n"
                f"🎬 Название: {session.title}\n"
                f"👤 Создатель: {session.creator_name}\n"
                f"👥 Зрителей: {len(session.viewers)}"
            )
            bot.send_message(message.chat.id, response_text, reply_markup=create_watch_markup(session_id, message.from_user.id))
            
            # Уведомляем создателя о новом зрителе
            bot.send_message(
                session.creator_id,
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
            if call.from_user.id not in session.viewers:
                session.add_viewer(call.from_user.id, call.from_user.first_name)
            markup = create_watch_markup(session_id, call.from_user.id)
            bot.send_message(
                call.message.chat.id,
                f"✅ Вы присоединились к просмотру!\n🎬 {session.title}",
                reply_markup=markup
            )
            # Уведомляем создателя
            bot.send_message(
                session.creator_id,
                f"👋 {call.from_user.first_name} присоединился к просмотру!"
            )

    elif call.data.startswith("toggle_play_"):
        session_id = call.data.split("_")[2]
        if session_id in active_sessions:
            session = active_sessions[session_id]
            if call.from_user.id == session.creator_id:
                session.is_active = not session.is_active
                status = "▶️ Воспроизведение" if session.is_active else "⏸️ Пауза"
                # Уведомляем всех зрителей
                for viewer_id in session.viewers:
                    bot.send_message(
                        viewer_id,
                        f"{status}\n👑 {session.creator_name} {('запустил' if session.is_active else 'поставил на паузу')} видео"
                    )
    
    elif call.data.startswith("restart_"):
        session_id = call.data.split("_")[1]
        if session_id in active_sessions:
            session = active_sessions[session_id]
            if call.from_user.id == session.creator_id:
                session.start_timestamp = datetime.now().timestamp()
                session.is_active = True
                # Уведомляем всех зрителей
                for viewer_id in session.viewers:
                    if viewer_id != session.creator_id:
                        bot.send_message(
                            viewer_id,
                            "🔄 Создатель перезапустил видео с начала"
                        )

    elif call.data.startswith("end_stream_"):
        session_id = call.data.split("_")[2]
        if session_id in active_sessions:
            session = active_sessions[session_id]
            if call.from_user.id == session.creator_id:
                session.end_stream()
                # Уведомляем всех зрителей
                for viewer_id in session.viewers:
                    bot.send_message(
                        viewer_id,
                        "🛑️ Создатель завершил поток"
                    )

@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    if message.text.startswith(('http://', 'https://')):
        # Создаем новую сессию для видео
        session_id = str(uuid.uuid4())
        session = StreamSession(
            url=message.text,
            creator_id=message.from_user.id,
            creator_name=message.from_user.first_name,
            title="Прямой эфир"
        )
        session.add_viewer(message.from_user.id, message.from_user.first_name)
        active_sessions[session_id] = session
        
        # Создаем клавиатуру с кнопками управления
        markup = create_watch_markup(session_id, message.from_user.id)
        
        # Формируем текст сообщения
        response_text = (
            f"🎉 Стрим создан!\n"
            f"👤 Создатель: {session.creator_name}\n"
            f"👥 Зрителей: {len(session.viewers)}\n\n"
            f"📨 Нажмите 'Пригласить друзей', чтобы позвать зрителей!"
        )
        
        bot.reply_to(message, response_text, reply_markup=markup)
    else:
        # Проверяем, является ли сообщение командой присоединения к сессии
        args = message.text.split()
        if len(args) > 1 and args[1].startswith('join_'):
            session_id = args[1].replace('join_', '')
            if session_id in active_sessions:
                session = active_sessions[session_id]
                
                # Добавляем зрителя в сессию
                session.add_viewer(message.from_user.id, message.from_user.first_name)
                
                # Создаем веб-приложение с текущим временем потока
                current_time = session.get_current_stream_time()
                webapp = WebAppInfo(
                    url=f"{WEBAPP_URL}?session={session_id}&url={quote(session.url)}&t={current_time}&st={session.start_timestamp}"
                )
                
                # Создаем клавиатуру
                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton(
                    text="▶️ Открыть плеер",
                    web_app=webapp
                ))
                
                # Отправляем сообщение
                response_text = (
                    f"✅ Вы присоединились к просмотру!\n"
                    f"👤 Создатель: {session.creator_name}\n"
                    f"👥 Зрителей: {len(session.viewers)}"
                )
                bot.reply_to(message, response_text, reply_markup=markup)
                
                # Уведомляем создателя о новом зрителе
                bot.send_message(
                    session.creator_id,
                    f"👋 Новый зритель присоединился!\n"
                    f"👤 {message.from_user.first_name}"
                )
            else:
                bot.reply_to(message, "❌ Сессия не найдена или устарела")
        else:
            bot.reply_to(message, "❌ Пожалуйста, отправьте корректную ссылку на видео")

@bot.message_handler(content_types=['web_app_data'])
def handle_webapp_data(message):
    try:
        data = json.loads(message.web_app_data.data)
        session_id = data.get('session_id')
        action = data.get('action')
        
        if session_id in active_sessions:
            session = active_sessions[session_id]
            
            if action == 'viewer_joined':
                # Добавляем зрителя
                session.add_viewer(message.from_user.id, message.from_user.first_name)
                
                # Отправляем обновленный список зрителей всем участникам
                viewers_info = session.get_viewers_info()
                stream_time = session.get_current_stream_time()
                
                # Отправляем информацию о потоке новому зрителю
                try:
                    bot.send_message(
                        message.from_user.id,
                        json.dumps({
                            'type': 'stream_info',
                            'stream_time': stream_time,
                            'start_timestamp': session.start_timestamp,
                            'is_active': session.is_active
                        })
                    )
                except Exception as e:
                    print(f"Error sending stream info: {e}")

                # Отправляем обновление о зрителях всем
                update_message = json.dumps({
                    'type': 'viewer_update',
                    'viewers': viewers_info,
                    'count': len(session.viewers)
                })
                
                for viewer_id in session.viewers:
                    try:
                        bot.send_message(viewer_id, update_message)
                    except Exception as e:
                        print(f"Error sending viewer update to {viewer_id}: {e}")
            
            elif action == 'end_stream' and message.from_user.id == session.creator_id:
                session.end_stream()
                end_message = json.dumps({
                    'type': 'stream_ended'
                })
                for viewer_id in session.viewers:
                    try:
                        bot.send_message(viewer_id, end_message)
                    except Exception as e:
                        print(f"Error sending stream end message: {e}")

    except Exception as e:
        print(f"Error handling webapp data: {e}")
        bot.reply_to(message, "❌ Произошла ошибка при обработке данных")

# Запуск бота
bot.infinity_polling()
