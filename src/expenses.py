from datetime import date
from decimal import Decimal, InvalidOperation

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from utils.database import insert_into_table
from .calendar_utils import build_calendar
from .users import USERS

SELECT_PAYER, ENTER_CONCEPT, SELECT_DATE, ENTER_AMOUNT, SELECT_ATTACHMENT_MODE, WAIT_ATTACHMENT = range(6)


def _build_payers_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for name in USERS:
        buttons.append([InlineKeyboardButton(name, callback_data=f"exp_payer_{name}")])

    buttons.append([InlineKeyboardButton("Cancelar", callback_data="exp_cancel")])
    return InlineKeyboardMarkup(buttons)


def _build_attachment_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("No adjuntar nada", callback_data="exp_attach_none")],
        [InlineKeyboardButton("Cancelar", callback_data="exp_cancel")],
    ])


async def add_expense(update: Update, context: CallbackContext):
    context.user_data.pop("expense", None)
    context.user_data["expense"] = {}
    context.user_data.pop("expense_msg_id", None)

    text = "¿Quién ha pagado el gasto?"
    markup = _build_payers_keyboard()

    if update.message:
        msg = await update.message.reply_text(text=text, reply_markup=markup)
        context.user_data["expense_msg_id"] = msg.message_id
    else:
        await update.callback_query.edit_message_text(text=text, reply_markup=markup)

    return SELECT_PAYER


async def expense_payer_selected(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "exp_cancel":
        await query.edit_message_text("Operación cancelada.")
        return ConversationHandler.END

    if not data.startswith("exp_payer_"):
        return SELECT_PAYER

    payer_name = data.replace("exp_payer_", "", 1)

    context.user_data["expense"]["user_name"] = payer_name
    context.user_data["expense_text"] = f"Pagador: {payer_name}"

    text = context.user_data["expense_text"] + "\n\nEscribe el concepto del gasto:"
    await query.edit_message_text(text=text, reply_markup=None)
    return ENTER_CONCEPT


async def expense_attachment_mode(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "exp_cancel":
        await query.edit_message_text("Operación cancelada.")
        return ConversationHandler.END

    if data == "exp_attach_none":
        expense = context.user_data["expense"]
        insert_into_table(
            "expenses",
            concept=expense["concept"],
            date=expense["date"],
            amount=expense["amount"],
            user_name=expense["user_name"],
            attachment_type=None,
            attachment_file_id=None,
            attachment_name=None,
        )

        # Mostrar confirmación final
        success_text = context.user_data["expense_text"] + "\n\n✅ Gasto guardado"
        await query.edit_message_text(success_text)
        return ConversationHandler.END

    return SELECT_ATTACHMENT_MODE


async def expense_concept(update: Update, context: CallbackContext):
    text = (update.message.text or "").strip()
    if not text:
        await update.message.reply_text("El concepto no puede estar vacío. Inténtalo de nuevo:")
        return ENTER_CONCEPT

    await update.message.delete()

    msg_id = context.user_data.get("expense_msg_id")
    await update.effective_chat.delete_message(msg_id)

    context.user_data["expense"]["concept"] = text

    # Añadir concepto al texto acumulado
    context.user_data["expense_text"] += f"\nConcepto: {text}"

    today = date.today()
    context.user_data["expense_year"] = today.year
    context.user_data["expense_month"] = today.month
    context.user_data["expense_day"] = today.day

    accumulated_text = context.user_data["expense_text"] + "\n\nSelecciona la fecha del gasto:"

    msg = await update.message.reply_text(
        text=accumulated_text,
        reply_markup=build_calendar(today.year, today.month, selected_day=today.day, prefix="exp"),
    )
    context.user_data["expense_msg_id"] = msg.message_id
    return SELECT_DATE


async def expense_date_picker(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "exp_cancel":
        await query.edit_message_text("Operación cancelada.")
        return ConversationHandler.END

    year = context.user_data.get("expense_year", date.today().year)
    month = context.user_data.get("expense_month", date.today().month)

    if data == "exp_prev_month":
        if month == 1:
            year -= 1
            month = 12
        else:
            month -= 1
        context.user_data["expense_year"] = year
        context.user_data["expense_month"] = month

        await query.edit_message_text(
            text="Selecciona la fecha del gasto:",
            reply_markup=build_calendar(year, month, context.user_data.get("expense_day"), prefix="exp"),
        )
        return SELECT_DATE

    if data == "exp_next_month":
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
        context.user_data["expense_year"] = year
        context.user_data["expense_month"] = month

        await query.edit_message_text(
            text="Selecciona la fecha del gasto:",
            reply_markup=build_calendar(year, month, context.user_data.get("expense_day"), prefix="exp"),
        )
        return SELECT_DATE

    if data.startswith("exp_day_"):
        day = int(data.replace("exp_day_", ""))
        context.user_data["expense_day"] = day

        selected_date = date(
            context.user_data["expense_year"],
            context.user_data["expense_month"],
            context.user_data["expense_day"],
        )
        context.user_data["expense"]["date"] = selected_date

        # Añadir fecha al texto acumulado
        context.user_data["expense_text"] += f"\nFecha: {selected_date.strftime('%d/%m/%Y')}"

        accumulated_text = context.user_data["expense_text"] + "\n\nAhora escribe el importe:"

        await query.edit_message_text(accumulated_text)
        return ENTER_AMOUNT

    return SELECT_DATE


async def expense_amount(update: Update, context: CallbackContext):
    raw = (update.message.text or "").strip().replace(",", ".")
    try:
        amount = Decimal(raw)
        if amount <= 0:
            raise ValueError("El importe debe ser mayor que 0")
    except (InvalidOperation, ValueError):
        await update.message.reply_text("Importe inválido. Escribe un número válido (ej: 123.45):")
        return ENTER_AMOUNT

    await update.message.delete()

    msg_id = context.user_data.get("expense_msg_id")
    await update.effective_chat.delete_message(msg_id)

    context.user_data["expense"]["amount"] = float(amount.quantize(Decimal("0.01")))
    amount_display = context.user_data["expense"]["amount"]

    # Añadir importe al texto acumulado
    context.user_data["expense_text"] += f"\nImporte: €{amount_display:.2f}"

    accumulated_text = context.user_data["expense_text"] + "\n\n¿Quieres adjuntar algo?"

    msg = await update.message.reply_text(
        accumulated_text,
        reply_markup=_build_attachment_keyboard(),
    )
    context.user_data["expense_msg_id"] = msg.message_id
    return SELECT_ATTACHMENT_MODE


async def expense_attachment_received(update: Update, context: CallbackContext):
    expense = context.user_data["expense"]

    file_id = None
    file_name = None
    attachment_type = None

    # Si envía foto
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        file_name = "photo"
        attachment_type = "photo"

    # Si envía documento
    elif update.message.document:
        file_id = update.message.document.file_id
        file_name = update.message.document.file_name or "document"
        attachment_type = "document"

    # Si envía /cancel o comando, guardar sin adjunto
    elif update.message.text and update.message.text.startswith("/"):
        pass  # Guardar sin adjunto

    # Si envía texto cualquiera, ignorar y pedir de nuevo
    else:
        return WAIT_ATTACHMENT

    insert_into_table(
        "expenses",
        concept=expense["concept"],
        date=expense["date"],
        amount=expense["amount"],
        user_name=expense["user_name"],
        attachment_type=attachment_type,
        attachment_file_id=file_id,
        attachment_name=file_name,
    )

    # Mostrar confirmación final
    success_text = context.user_data["expense_text"]
    if file_name:
        success_text += f"\nAdjunto: {file_name}"
    success_text += "\n\n✅ Gasto guardado"

    await update.message.reply_text(success_text)
    return ConversationHandler.END


async def cancel_expense(update: Update, _: CallbackContext):
    if update.message:
        await update.message.reply_text("Operación cancelada.")
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Operación cancelada.")
    return ConversationHandler.END


def get_expense_conv_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("gasto", add_expense)],
        states={
            SELECT_PAYER: [CallbackQueryHandler(expense_payer_selected, pattern=r"^exp_(payer_.+|cancel)$")],
            ENTER_CONCEPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, expense_concept)],
            SELECT_DATE: [CallbackQueryHandler(expense_date_picker, pattern=r"^exp_(prev_month|next_month|day_\d+|noop|cancel)$")],
            ENTER_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, expense_amount)],
            SELECT_ATTACHMENT_MODE: [
                CallbackQueryHandler(expense_attachment_mode, pattern=r"^exp_(attach_none|cancel)$"),
                MessageHandler(filters.PHOTO, expense_attachment_received),
                MessageHandler(filters.Document.ALL, expense_attachment_received),
            ],
            WAIT_ATTACHMENT: [
                MessageHandler(filters.PHOTO, expense_attachment_received),
                MessageHandler(filters.Document.ALL, expense_attachment_received),
                MessageHandler(filters.COMMAND, expense_attachment_received),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_expense), CallbackQueryHandler(cancel_expense, pattern=r"^exp_cancel$")],
        allow_reentry=True,
    )
