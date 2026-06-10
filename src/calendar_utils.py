from calendar import monthrange
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def month_name(year: int, month: int) -> str:
    """Retorna el nombre del mes y año en formato 'Month Year'"""
    return datetime(year, month, 1).strftime("%B %Y")


def build_calendar(
        year: int,
        month: int,
        selected_day: int | None = None,
        prefix: str = "cal"
) -> InlineKeyboardMarkup:
    """
    Construye un calendario interactivo reutilizable.

    Args:
        year: Año del calendario
        month: Mes del calendario
        selected_day: Día a destacar (opcional)
        prefix: Prefijo para los callback_data (ej: 'exp', 'gasofa', 'cal')

    Returns:
        InlineKeyboardMarkup con el calendario
    """
    keyboard = [[
        InlineKeyboardButton("<<", callback_data=f"{prefix}_prev_month"),
        InlineKeyboardButton(month_name(year, month), callback_data=f"{prefix}_noop"),
        InlineKeyboardButton(">>", callback_data=f"{prefix}_next_month"),
    ]]

    weekday_labels = ["L", "M", "X", "J", "V", "S", "D"]
    keyboard.append([InlineKeyboardButton(d, callback_data=f"{prefix}_noop") for d in weekday_labels])

    first_weekday, num_days = monthrange(year, month)
    day = 1
    for week in range(6):
        row = []
        for wd in range(7):
            if week == 0 and wd < first_weekday:
                row.append(InlineKeyboardButton(" ", callback_data=f"{prefix}_noop"))
            elif day > num_days:
                row.append(InlineKeyboardButton(" ", callback_data=f"{prefix}_noop"))
            else:
                label = f"[{day}]" if selected_day == day else str(day)
                row.append(InlineKeyboardButton(label, callback_data=f"{prefix}_day_{day}"))
                day += 1
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("Cancelar", callback_data=f"{prefix}_cancel")])
    return InlineKeyboardMarkup(keyboard)
