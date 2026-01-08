from app.db.models import Account
from app.utils.logger import get_logger


class AccountBase:
    """
    База для функционала аккаунта
    """

    def __init__(self, model: Account):
        self.model = model
        self.logger = get_logger(f"Account({model.id})")
