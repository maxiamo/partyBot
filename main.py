from aiogram import Bot, Dispatcher
from aiogram.types import FSInputFile
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import Message
import asyncio
from database import Database
import re

CHANNEL_USERNAME = "example"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


MAX_TRACKS = 3
hiWord = "" 

db = Database()

def get_track_word_form(count):
    if count == 1:
        return "трек"
    elif 2 <= count <= 4:
        return "трека"
    else:
        return "треков"

def get_track_word_form_r(count):
    if count == 1:
        hiWord = "еще"
        return hiWord, "трек"
    else:
        hiWord = "до"
        return hiWord, "треков"

def extract_track_id(url):
    match = re.search(r'/track/(\d+)', url)
    if match:
        return match.group(1)
    return None

async def check_subscription(user_id):
    try:
        chat_member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return chat_member.status in ["member", "administrator", "creator"]
    except Exception as e:
        #print(f"Ошибка проверки подписки: {e}")
        return False
        
@dp.message(Command("start"))
async def start_command(message: Message):
        
    is_subscribed = await check_subscription(message.from_user.id)
    print(f"Статус подписки для {message.from_user.id}: {is_subscribed}")
    
    if not is_subscribed:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Подписаться", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")]
            ]
        )
        await message.answer(
            f"Чтобы использовать этого бота, подпишитесь на канал {CHANNEL_USERNAME} и попробуйте снова.",
            reply_markup=keyboard
        )
        return
    await message.answer("Вы подписаны на канал.")
    user = db.get_user(message.from_user.id)

    if not user:
        user = db.add_user(message.from_user.id, message.from_user.username)
        remaining_tracks = MAX_TRACKS
    else:
        track_count = user["track_count"]
        remaining_tracks = MAX_TRACKS - track_count
    hiWord, track_word = get_track_word_form_r(remaining_tracks)
    image_path = "./ppg1.jpeg"
    photo = FSInputFile(image_path)
 
    await bot.send_photo(chat_id=message.chat.id, photo=photo, caption=(
        f"Привет, {message.from_user.first_name}!"
                     "\n\n🎧 Этот бот помогает выбрать музыку для нашего мероприятия. "
                    f"\n\nЧтобы предложить трек:"

                    f"\n1. Откройте *Яндекс.Музыку* и найдите ваш любимый трек. "
                     f"\n2. Нажмите на кнопку *Поделиться* (рядом с названием трека). "
                        f"\n3. *Скопируйте ссылку* на трек. "
                        f"\n4. *Вставьте ссылку* и отправьте её в чат. "
                        f"\n\n💡 Каждый пользователь может предложить до 3 треков. "
                        f"\n\n🎉 Трек, который наберёт наибольшее количество предложений, станет победителем!"
                     #f"\n\nВы можете отправить *{hiWord} {remaining_tracks} {track_word}*. "
         ), parse_mode="Markdown")
    
    #await message.answer(f"Привет, {message.from_user.first_name}! "
    #                     f"Вы можете отправить {hiWord} {remaining_tracks} {track_word}. "
     #                    f"Просто пришлите ссылку.")
    
@dp.message(Command("stats"))
async def stats_command(message: Message):
    ADMIN_IDS = [00,00,00] 

    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Команда доступна только администраторам.")
        return

    stats = db.get_most_frequent_tracks()
    if not stats:
        await message.answer("Треков пока нет.")
        return

    response = "Самые популярные треки:\n"
    response += "\n".join(
    [f"https://music.yandex.ru/track/{track[0]} — {track[1]} раз(а)" for track in stats])
    await message.answer(response)
    
    
@dp.message(Command("stats_all"))
async def stats_command(message: Message):
    ADMIN_IDS = [00,00,00] 

    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Команда доступна только администраторам.")
        return

    stats = db.get_most_frequent_tracks_all()
    if not stats:
        await message.answer("Треков пока нет.")
        return

    response = "Самые популярные треки (в том числе неактивные):\n"
    response += "\n".join(
    [f"https://music.yandex.ru/track/{track[0]} — {track[1]} раз(а)" for track in stats])
    await message.answer(response)

@dp.message(Command("reset"))
async def reset_tracks(message: Message):
    ADMIN_IDS = [00,00,00] 

    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Эта команда доступна только администраторам.")
        return

    db.deactivate_all_tracks()

    db.reset_user_track_count()

    await message.answer("Все треки деактивированы, лимиты пользователей сброшены.")
    
@dp.message()
async def handle_track(message: Message):
    is_subscribed = await check_subscription(message.from_user.id)
    
    if not is_subscribed:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Подписаться", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")]
            ]
        )
        await message.answer(
            f"Чтобы использовать этого бота, подпишитесь на канал {CHANNEL_USERNAME} и попробуйте снова.",
            reply_markup=keyboard
        )
        return
    
    yandex_music_pattern = r"https?://music\.yandex\.(ru|com)/.+"
    track_url = message.text.strip()
    if not re.match(yandex_music_pattern, track_url):
        await message.answer("Пожалуйста, отправьте корректную ссылку с сервиса Яндекс.Музыка.")
        return
    
    if "/track" in message.text:
        user_id = message.from_user.id
        track_url = extract_track_id(track_url)
        user = db.get_user(user_id)

        if not user: 
            user = db.add_user(user_id, message.from_user.username)
            track_count = 0
        else:
            track_count = user["track_count"]
            
        remaining_tracks = MAX_TRACKS - track_count

        if remaining_tracks <= 0:
            await message.answer("Вы уже отправили максимальное количество треков. Спасибо!")
            return
        
        if db.is_track_already_sent(user["telegram_id"], track_url):
            await message.answer("Вы уже отправляли этот трек!")
            return
        
        db.add_track(user["telegram_id"], track_url)
        remaining_tracks -= 1
        #print(remaining_tracks)
        track_word = get_track_word_form(remaining_tracks)  
        response = (f"Спасибо! Вы можете отправить еще {remaining_tracks} {track_word}."
                    if remaining_tracks > 0 else "Спасибо! Вы достигли лимита.")
        await message.answer(response)

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
