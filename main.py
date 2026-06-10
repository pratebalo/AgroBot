from decouple import config
from bot_base.main import main

from src.gasoil import get_conv_handler
from src.expenses import get_expense_conv_handler


def add_handlers(app):
    app.add_handler(get_expense_conv_handler())
    app.add_handler(get_conv_handler())


if __name__ == "__main__":
    main(
        id_logs=config("ID_LOGS"),
        thread_id=config("THREAD_ID"),
        name=config("NAME"),
        token=config("TOKEN"),
        add_handlers=add_handlers,
        commands=[
            ("gasto", "Añade un gasto"),
            ("gasofa", "Registra fecha y precio/l del repostaje"),
        ],
    )
