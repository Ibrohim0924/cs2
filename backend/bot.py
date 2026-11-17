import asyncio

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

from app.core.config import settings


async def main() -> None:
    if not settings.telegram_bot_token:
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN to run the Telegram bot")
    if not settings.telegram_bot_username:
        raise RuntimeError("Set TELEGRAM_BOT_USERNAME to create referral links")
    bot = Bot(settings.telegram_bot_token)
    dispatcher = Dispatcher()

    @dispatcher.message(CommandStart())
    async def start(message: Message) -> None:
        parts = (message.text or "").split(maxsplit=1)
        referral = parts[1] if len(parts) > 1 else ""
        launch_url = f"{settings.webapp_url.rstrip('/')}?startapp={referral}" if referral else settings.webapp_url
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Open your collection", web_app=WebAppInfo(url=launch_url))],
        ])
        await message.answer(
            "Welcome to CS2 OPEN CASE BOT.\n"
            "Explore fixed, published rewards in free cases — no paid spins or randomized prizes.",
            reply_markup=markup,
        )

    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
