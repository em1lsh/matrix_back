import asyncio

from sqlalchemy import select
from sqlalchemy.inspection import inspect

from app.account import Account
from app.db import SessionLocal, models


async def main():
    """
    Авторизация аккаунта
    """
    async with SessionLocal() as db_session:
        result = await db_session.execute(select(models.User).order_by(models.User.id.desc()).limit(10))
        users = result.scalars().all()

        if not users:
            print("Таблица users пуста.\n")
        else:
            mapper = inspect(models.User)
            column_names = [column.key for column in mapper.columns]

            for user in users:
                row_data = {name: getattr(user, name) for name in column_names}
                row_str = ", ".join(f"{k}={v}" for k, v in row_data.items())
                print(row_str)

        phone = input("Номер телефона >>> ")
        user_id = int(input("ID пользователя >>> "))

        user = await db_session.execute(select(models.User).where(models.User.id == user_id))
        user = user.scalar_one()
        account_model = await Account.create_account_by_phone(phone, user, db_session)
        account = Account(account_model)

        code = int(input("Код из телеграмма >>> "))
        name = input("Имя аккаунта >>> ")
        password = input("Пароль от аккаунта >>> ")

        await account.approve_auth(code, name, db_session, password)

    print("Аккаунт был создан!")


if __name__ == "__main__":
    asyncio.run(main())
