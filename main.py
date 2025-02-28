import asyncio
import os
from langdetect import detect
from openai import OpenAI, BadRequestError, RateLimitError, APIConnectionError
from logs.logger_config import logger
from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

bot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher(bot=bot)

CHANGE_LANGUAGE_BUTTON = "🌍 Change Language"
LOADING_MESSAGE = "⏳ Translating your text, please wait..."
DEFAULT_LANGUAGE = "English"

SUPPORTED_LANGUAGES = ["English", "Russian", "Uzbek", "Spanish", "French", "German"]
LANGUAGE_CODES = {
    "English": "en",
    "Russian": "ru",
    "Uzbek": "uz",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
}


def generate_prompt(target_language):
    return (f"You are a professional translator fluent in multiple languages. Your task is to accurately translate user"
            f" input into {target_language}.")


def main_keyboard():
    buttons = [[KeyboardButton(text=CHANGE_LANGUAGE_BUTTON)]]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


@dp.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    await state.update_data(language=DEFAULT_LANGUAGE, prompt=generate_prompt(DEFAULT_LANGUAGE))
    logger.info(f"User {message.from_user.id} initiated the /start command.")
    await message.answer(f"👋 Hello! Send any text, and I'll translate it.\n"
                         f"🌍 Default language: <b>{DEFAULT_LANGUAGE}</b>.\n"
                         f"🔄 Use 'Change Language' to switch.",
                         reply_markup=main_keyboard(), parse_mode="HTML")


@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer("🆘 <b>How to use me:</b>\n\n"
                         "📌 Send any text, and I'll translate it to your preferred language.\n"
                         "🌍 Use the <b>Change Language</b> button to switch languages.\n"
                         "❓ If you have issues, try restarting the bot with /start.", parse_mode="HTML")


@dp.message(F.text == CHANGE_LANGUAGE_BUTTON)
async def change_language(message: types.Message):
    logger.info(f"User {message.from_user.id} requested to change language.")

    buttons = [
        InlineKeyboardButton(text=lang, callback_data=f"language_{lang}") for lang in SUPPORTED_LANGUAGES
    ]

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        buttons[i:i + 2] for i in range(0, len(buttons), 2)
    ])

    await message.answer("🌍 Choose a language for translation:", reply_markup=keyboard)


@dp.callback_query(F.data.startswith("language_"))
async def set_language(callback_query: types.CallbackQuery, state: FSMContext):
    language = callback_query.data.split("_")[1]
    logger.info(f"User {callback_query.message.from_user.id} selected language: {language}")
    await state.update_data(language=language, prompt=generate_prompt(language))
    await callback_query.message.edit_text(f"✅ Translation language set to <b>{language}</b>.", parse_mode="HTML")


@dp.message(lambda message: message.text and message.text not in [CHANGE_LANGUAGE_BUTTON])
async def translate(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    current_language = user_data.get("language", DEFAULT_LANGUAGE)
    prompt = user_data.get("prompt", generate_prompt(current_language))

    detected_language = detect(message.text)
    current_language_code = LANGUAGE_CODES.get(current_language, "en")
    if detected_language == current_language_code:
        await message.answer("⚠️ You are trying to translate a text that is already in the target language.")
        return

    if not message.text.strip():
        await message.answer("⚠️ Please enter some text to translate.")
        return

    if current_language == "Uzbek":
        prompt += f"Use only the official Latin script of {current_language}."

    logger.info(f"User {message.from_user.id} requested translation: {message.text}")
    in_progress_message = await message.answer(LOADING_MESSAGE)

    try:
        response = await asyncio.to_thread(client.chat.completions.create,
                                           model="gpt-4",
                                           temperature=0,
                                           messages=[
                                               {"role": "system", "content": prompt},
                                               {"role": "user", "content": message.text}
                                           ])
        translated_text = response.choices[0].message.content
        logger.info(f"Translation successful for user {message.from_user.id}: {translated_text}")
        await in_progress_message.edit_text(translated_text)
    except BadRequestError:
        logger.error(f"Bad request error for user {message.from_user.id}.")
        await in_progress_message.edit_text("❌ Invalid request. Please try again.")
    except RateLimitError:
        logger.error(f"Rate limit reached for user {message.from_user.id}.")
        await in_progress_message.edit_text("⚠️ Too many requests. Please wait a few moments.")
    except APIConnectionError:
        logger.error(f"Connection error for user {message.from_user.id}.")
        await in_progress_message.edit_text("🔌 Connection error. Please check your internet connection.")
    except Exception as e:
        logger.error(f"Unexpected error for user {message.from_user.id}: {e}")
        await in_progress_message.edit_text("❌ An error occurred. Please try again later.")


async def main() -> None:
    logger.info("Bot started polling.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
