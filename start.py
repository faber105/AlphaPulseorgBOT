import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)
from sqlalchemy import desc, select

from api.models.channel_join import ChannelJoinRequest
from api.models.database import AsyncSessionLocal
from api.models.user import User
from config import get_settings

router = Router()
logger = logging.getLogger(__name__)


async def upsert_user(message: Message) -> User:
    tg_user = message.from_user
    if tg_user is None:
        raise ValueError("Telegram user is missing")

    try:
        async with AsyncSessionLocal() as db:
            user = await db.get(User, tg_user.id)
            if user is None:
                user = User(
                    id=tg_user.id,
                    username=tg_user.username,
                    first_name=tg_user.first_name,
                    language_code=tg_user.language_code,
                )
                db.add(user)
            else:
                user.username = tg_user.username
                user.first_name = tg_user.first_name
                user.language_code = tg_user.language_code
            await db.commit()
            await db.refresh(user)
            return user
    except Exception as exc:
        logger.warning("Failed to upsert Telegram user %s: %s", tg_user.id, exc)
        return User(
            id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name,
            language_code=tg_user.language_code,
        )


def main_menu_keyboard() -> InlineKeyboardMarkup:
    settings = get_settings()
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Открыть AlphaPulse",
                    web_app=WebAppInfo(url=settings.mini_app_url),
                )
            ],
            [InlineKeyboardButton(text="Тарифы", callback_data="open_subscriptions")],
            [InlineKeyboardButton(text="Заявка на вход в канал", callback_data="request_join")],
        ]
    )


@router.message(CommandStart())
async def start(message: Message) -> None:
    await upsert_user(message)
    settings = get_settings()
    await message.answer(
        (
            f"<b>{settings.project_name}</b>\n\n"
            "Торговые сигналы Pocket Option, личные сессии, статистика и подписка в Mini App.\n"
            "Открой приложение или выбери тариф, чтобы активировать доступ."
        ),
        reply_markup=main_menu_keyboard(),
    )


@router.message(Command("join"))
@router.callback_query(F.data == "request_join")
async def request_channel_join(event: Message | CallbackQuery) -> None:
    message = event.message if isinstance(event, CallbackQuery) else event
    tg_user = event.from_user
    if message is None or tg_user is None:
        return

    async with AsyncSessionLocal() as db:
        user = await db.get(User, tg_user.id)
        if user is None:
            user = User(id=tg_user.id, username=tg_user.username, first_name=tg_user.first_name)
            db.add(user)
            await db.flush()

        pending = await db.scalar(
            select(ChannelJoinRequest)
            .where(ChannelJoinRequest.user_id == tg_user.id, ChannelJoinRequest.status == "pending")
            .order_by(desc(ChannelJoinRequest.requested_at))
            .limit(1)
        )
        if pending is not None:
            await message.answer("Заявка уже ожидает подтверждения администратора.")
            if isinstance(event, CallbackQuery):
                await event.answer()
            return

        join_request = ChannelJoinRequest(user_id=tg_user.id, username=tg_user.username)
        db.add(join_request)
        await db.commit()
        await db.refresh(join_request)

    admin_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Подтвердить", callback_data=f"join:approve:{join_request.id}"),
                InlineKeyboardButton(text="Отклонить", callback_data=f"join:reject:{join_request.id}"),
            ]
        ]
    )
    admin_text = (
        "Новая заявка на вход в канал\n\n"
        f"ID: <code>{tg_user.id}</code>\n"
        f"Username: @{tg_user.username or '-'}\n"
        f"Имя: {tg_user.first_name or '-'}\n"
        f"Заявка: #{join_request.id}\n"
        f"Время: {datetime.utcnow():%Y-%m-%d %H:%M:%S} UTC"
    )
    await message.bot.send_message(get_settings().admin_telegram_id, admin_text, reply_markup=admin_keyboard)
    await message.answer("Заявка отправлена администратору. Я напишу, когда ее проверят.")
    if isinstance(event, CallbackQuery):
        await event.answer()
