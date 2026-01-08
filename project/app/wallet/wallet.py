import asyncio
import json

from curl_cffi import requests
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from tonsdk.contract.wallet import Wallets, WalletVersionEnum
from tonsdk.crypto import mnemonic_new
from tonutils.client import ToncenterV3Client
from tonutils.wallet import WalletV4R2
from Tonviewer import Wallet

from app.configs import settings
from app.db import SessionLocal, models
from app.utils.logger import logger


class TonWallet:
    """
    Функционал для работы с TON кошельком
    """

    testnet = False
    wallet_version = "v4r2"
    wallet_workchain = 0

    def __init__(self):
        from app.utils.logger import get_logger

        self.logger = get_logger("TonWallet")

    def init_ton_client(self):
        """
        Инициализация TON клиента
        """
        return ToncenterV3Client(api_key=settings.toncenter_api_key, is_testnet=self.testnet)

    @staticmethod
    def get_wallet_keys(
        mnemonic: list | str | None = None, workchain: int = 0, version: str = "v4r2"
    ) -> tuple[str, str]:
        """
        Отдает tonsdk.contract.wallet.WalletContract кошелька
        """
        if mnemonic is None or mnemonic == [""]:
            mnemonic = mnemonic_new()
        elif isinstance(mnemonic, str):
            mnemonic = mnemonic.split(" ")

        _mnemonics, _pub_k, _priv_k, wallet = Wallets.from_mnemonics(
            mnemonic, getattr(WalletVersionEnum, version), workchain
        )

        return (_pub_k, _priv_k)

    async def send_ton(
        self,
        to_address: str,
        amount: float,
        ton_client: ToncenterV3Client,
        message: str = "",
        is_nano: bool = True,
    ):
        """
        Отправляет TON на указанный адрес
        """
        self.logger.info(f"send {amount/1e9 if is_nano else amount} ton to {to_address} with message '{message}'")

        pub_key, priv_key = TonWallet.get_wallet_keys(settings.output_wallet_mnemonic)

        wallet = WalletV4R2(client=ton_client, public_key=pub_key, private_key=priv_key)

        tx_hash = await wallet.transfer(
            destination=to_address,
            amount=amount / 1e9 if is_nano else amount,
            body=message,
        )

        self.logger.info("Successfully transferred!")
        self.logger.info(f"Transaction hash: {tx_hash}")

    async def request_transactions(self, s: requests.AsyncSession):
        while True:
            try:
                transactions: requests.Response = await s.post(
                    url="https://toncenter.com/api/v2/jsonRPC",
                    json={
                        "id": 1,
                        "jsonrpc": "2.0",
                        "method": "getTransactions",
                        "params": {"address": settings.output_wallet, "limit": 10, "archival": False},
                    },
                )
            except requests.exceptions.Timeout:
                await asyncio.sleep(3)

            try:
                json_data = transactions.json()
                if "result" in json_data:
                    return transactions.json()
                else:
                    await asyncio.sleep(3)
            except json.decoder.JSONDecodeError:
                await asyncio.sleep(3)

    async def check_topups(
        self,
        db_session: AsyncSession,
        # http_client: requests.AsyncSession
    ):
        """
        Проверяет наличие новых пополнений на кошелек
        """
        # self.logger.debug('start check transactions')
        s = requests.AsyncSession()

        transactions = await self.request_transactions(s)

        last_transactions = await db_session.execute(
            select(models.BalanceTopup)
            .options(joinedload(models.BalanceTopup.user))
            .order_by(models.BalanceTopup.created_at.desc())
            .limit(50)
        )
        last_transactions = list(last_transactions.scalars().all())

        for transaction in transactions["result"]:
            # print(transaction)
            if int(transaction["in_msg"]["value"]) == 0:
                continue

            # self.logger.debug('find valid transaction')

            transaction_memo = str(transaction["in_msg"]["message"])
            transaction_time = str(transaction["utime"])
            transaction_amount = int(transaction["in_msg"]["value"])

            finded = False

            for last_transaction in last_transactions:
                if (
                    transaction_time == last_transaction.time
                    and transaction_memo == last_transaction.user.memo
                    and transaction_amount == last_transaction.amount
                ):
                    finded = True
                    break

            if finded:
                # self.logger.debug('transaction already')
                continue

            topup_user = await db_session.execute(select(models.User).where(models.User.memo == transaction_memo))
            topup_user = topup_user.scalar_one_or_none()

            if topup_user is None:
                # self.logger.debug('memo not found')
                continue

            new_topup = models.BalanceTopup(amount=transaction_amount, time=transaction_time, user_id=topup_user.id)
            topup_user.market_balance += transaction_amount
            db_session.add(new_topup)
            await db_session.flush()
            # self.logger.debug('created new topup')

        await db_session.commit()
        await s.close()

    async def _run_check_transactions(
        self,
    ):
        while True:
            try:
                async with SessionLocal() as db_session:
                    await self.check_topups(db_session)
            except Exception as e:
                logger.error(f"Ошибка в check_transactions: {e}")
            await asyncio.sleep(5)

    @staticmethod
    def run_check_transactions():
        from app.utils.background_tasks import safe_background_task

        wallet = TonWallet()
        _wallet = Wallet(settings.output_wallet)
        asyncio.create_task(
            safe_background_task(
                task_name="check_transactions",
                task_func=wallet._run_check_transactions,
                restart_delay=30,
                max_consecutive_failures=5,
            )
        )
