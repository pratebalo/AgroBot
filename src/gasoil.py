from datetime import date
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler, ConversationHandler, MessageHandler, filters

from utils.database import insert_into_table
from .calendar_utils import build_calendar
from .users import USERS

# Estados de conversación
SELECT_USER, SELECT_DATE, ENTER_PRICE = range(3)


def _build_users_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for name in USERS:
        buttons.append([InlineKeyboardButton(name, callback_data=f"gasofa_user_{name}")])

    buttons.append([InlineKeyboardButton("Cancelar", callback_data="gasofa_cancel")])
    return InlineKeyboardMarkup(buttons)


async def gasoil(update: Update, context: CallbackContext):
    context.user_data.pop("gasofa", None)
    context.user_data["gasofa"] = {}

    text = "¿Quién ha metido el repostaje?"
    reply_markup = _build_users_keyboard()

    if update.message:
        await update.message.delete()
        await update.effective_chat.send_message(text=text, reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup)

    return SELECT_USER


async def gasofa_user_selected(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "gasofa_cancel":
        await query.edit_message_text("Operación cancelada")
        return ConversationHandler.END

    if not data.startswith("gasofa_user_"):
        return SELECT_USER

    user_name = data.replace("gasofa_user_", "", 1)
    context.user_data["gasofa"]["user_name"] = user_name

    today = date.today()
    context.user_data["gasofa_year"] = today.year
    context.user_data["gasofa_month"] = today.month
    context.user_data["gasofa_day"] = today.day

    reply_markup = build_calendar(today.year, today.month, selected_day=today.day, prefix="gasofa")
    text = f"Usuario: {user_name}\n\nSelecciona la fecha del repostaje"

    await query.edit_message_text(text=text, reply_markup=reply_markup)
    return SELECT_DATE


async def gasofa_date_picker(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "gasofa_cancel":
        await query.edit_message_text("Operación cancelada")
        return ConversationHandler.END

    year = context.user_data.get("gasofa_year", date.today().year)
    month = context.user_data.get("gasofa_month", date.today().month)

    if data == "gasofa_prev_month":
        if month == 1:
            year -= 1
            month = 12
        else:
            month -= 1
        context.user_data["gasofa_year"] = year
        context.user_data["gasofa_month"] = month
        await query.edit_message_reply_markup(reply_markup=build_calendar(year, month, context.user_data.get("gasofa_day"), prefix="gasofa"))
        return SELECT_DATE

    if data == "gasofa_next_month":
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
        context.user_data["gasofa_year"] = year
        context.user_data["gasofa_month"] = month
        await query.edit_message_reply_markup(reply_markup=build_calendar(year, month, context.user_data.get("gasofa_day"), prefix="gasofa"))
        return SELECT_DATE

    if data.startswith("gasofa_day_"):
        day = int(data.replace("gasofa_day_", ""))
        context.user_data["gasofa_day"] = day

        selected_date = date(context.user_data["gasofa_year"], context.user_data["gasofa_month"], day)
        context.user_data["gasofa_date"] = selected_date

        await query.edit_message_text(
            f"Fecha seleccionada: {selected_date.strftime('%d/%m/%Y')}\n\n"
            "Ahora introduce el precio/l (ej: 1.569)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancelar", callback_data="gasofa_cancel")]]),
        )
        return ENTER_PRICE

    return SELECT_DATE


async def gasofa_price(update: Update, context: CallbackContext):
    raw_price = update.message.text.strip()
    normalized = re.sub(r"[^\d.]", "", raw_price.replace(",", ".").replace("'", ".").replace("´", "."))

    try:
        price = float(normalized)
        if price <= 0:
            raise ValueError
    except ValueError:
        await update.message.delete()
        await update.effective_chat.send_message("Precio no válido. Introduce un número mayor que 0 (ej: 1.569)")
        return ENTER_PRICE

    selected_date = context.user_data.get("gasofa_date", date.today())
    user_name = context.user_data.get("gasofa", {}).get("user_name")
    saved_fuel = insert_into_table("fuel", date=selected_date, price=round(price, 3), user_name=user_name)
    if saved_fuel is None:
        await update.message.delete()
        await update.effective_chat.send_message("No se ha podido guardar en BBDD. Vuelve a introducir el precio para reintentarlo.")
        return ENTER_PRICE

    await update.message.delete()
    await update.effective_chat.send_message(
        f"OK, guardado:\nUsuario: {user_name}\nFecha: {selected_date.strftime('%d/%m/%Y')}\nPrecio/l: {price:.3f} €"
    )

    return ConversationHandler.END


async def gasofa_cancel(update: Update, _: CallbackContext):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Operación cancelada")
    elif update.message:
        await update.message.reply_text("Operación cancelada")
    return ConversationHandler.END


def get_conv_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("gasofa", gasoil)],
        states={
            SELECT_USER: [
                CallbackQueryHandler(gasofa_user_selected, pattern=r"^gasofa_(user_.+|cancel)$"),
            ],
            SELECT_DATE: [
                CallbackQueryHandler(gasofa_date_picker, pattern=r"^gasofa_(prev_month|next_month|day_\d+|noop|cancel)$"),
            ],
            ENTER_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, gasofa_price),
                CallbackQueryHandler(gasofa_cancel, pattern=r"^gasofa_cancel$"),
            ],
        },
        fallbacks=[CommandHandler("gasofa", gasoil), CommandHandler("cancel", gasofa_cancel)],
    )
