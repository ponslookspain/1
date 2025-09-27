"""Telegram bot that collects listing data and creates a FanPay listing."""
from __future__ import annotations

import logging
import os
from decimal import Decimal, InvalidOperation

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from .fanpay import FanPayClient, FanPayError, Listing

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NAME, DESCRIPTION, PRICE, QUANTITY, CONFIRM = range(5)


def _build_application(token: str) -> Application:
    return Application.builder().token(token).build()


def start_factory(token: str, fanpay_client: FanPayClient) -> Application:
    """Create and configure the Telegram application instance."""

    app = _build_application(token)

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        await update.message.reply_text(
            "Здравствуйте! Отправьте название нового лота.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return NAME

    async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        await update.message.reply_text(
            "Создание лота отменено.", reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    async def ask_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        context.user_data["name"] = update.message.text.strip()
        await update.message.reply_text("Введите описание лота.")
        return DESCRIPTION

    async def ask_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        context.user_data["description"] = update.message.text.strip()
        await update.message.reply_text("Введите цену в рублях (например, 150.00).")
        return PRICE

    async def ask_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        try:
            price = Decimal(update.message.text.replace(",", ".").strip())
        except (InvalidOperation, AttributeError):
            await update.message.reply_text(
                "Не удалось распознать цену. Попробуйте еще раз, например 150 или 150.00."
            )
            return PRICE

        if price <= 0:
            await update.message.reply_text(
                "Цена должна быть больше нуля. Попробуйте еще раз."
            )
            return PRICE

        context.user_data["price"] = float(price)
        await update.message.reply_text("Введите количество товара (целое число).")
        return QUANTITY

    async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        try:
            qty = int(update.message.text.strip())
        except (ValueError, AttributeError):
            await update.message.reply_text(
                "Количество должно быть целым числом. Попробуйте снова."
            )
            return QUANTITY

        if qty <= 0:
            await update.message.reply_text(
                "Количество должно быть положительным. Попробуйте снова."
            )
            return QUANTITY

        context.user_data["quantity"] = qty
        summary = (
            f"Название: {context.user_data['name']}\n"
            f"Описание: {context.user_data['description']}\n"
            f"Цена: {context.user_data['price']}\n"
            f"Количество: {context.user_data['quantity']}\n\n"
            "Создать лот?"
        )
        await update.message.reply_text(
            summary,
            reply_markup=ReplyKeyboardMarkup(
                [["Да"], ["Нет"]], one_time_keyboard=True, resize_keyboard=True
            ),
        )
        return CONFIRM

    async def create_listing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        answer = update.message.text.strip().lower()
        if answer not in {"да", "yes"}:
            await update.message.reply_text(
                "Создание лота отменено.", reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END

        listing = Listing(
            name=context.user_data["name"],
            description=context.user_data["description"],
            price=context.user_data["price"],
            quantity=context.user_data["quantity"],
        )
        try:
            response = fanpay_client.create_listing(listing)
        except FanPayError as exc:
            logger.exception("Failed to create FanPay listing")
            await update.message.reply_text(
                f"Не удалось создать лот: {exc}", reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END

        await update.message.reply_text(
            "Лот успешно создан на FanPay!",
            reply_markup=ReplyKeyboardRemove(),
        )
        await update.message.reply_text(f"Ответ FanPay: {response}")
        return ConversationHandler.END

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_description)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_price)],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_quantity)],
            QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm)],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_listing)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("cancel", cancel))
    return app


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    cookie_path = os.environ.get("FANPAY_COOKIE_FILE")

    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is required")
    if not cookie_path:
        raise RuntimeError("FANPAY_COOKIE_FILE environment variable is required")

    base_url = os.environ.get("FANPAY_BASE_URL", "https://funpay.com")
    fanpay_client = FanPayClient(
        base_url=base_url,
        cookie_file=os.fspath(cookie_path),
    )
    application = start_factory(token, fanpay_client)
    application.run_polling()


if __name__ == "__main__":
    main()
