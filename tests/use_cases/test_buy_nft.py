"""
Unit тесты для BuyNFTUseCase

Тестируем бизнес-логику покупки NFT без HTTP слоя
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from app.use_cases.nft.buy_nft import BuyNFTUseCase
from app.exceptions import NFTNotFoundError, InsufficientBalanceError


@pytest.fixture
def mock_db_session():
    """Mock для AsyncSession"""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.refresh = AsyncMock()
    session.add = Mock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def mock_nft():
    """Mock для NFT"""
    nft = Mock()
    nft.id = 1
    nft.price = 1000000000  # 1 TON
    nft.user_id = 2
    nft.gift_id = 10
    nft.account_id = None
    nft.gift = Mock(title="Test Gift")
    nft.user = Mock(id=2, language="en", market_balance=5000000000)
    return nft


@pytest.fixture
def mock_buyer():
    """Mock для покупателя"""
    buyer = Mock()
    buyer.id = 3
    buyer.market_balance = 2000000000  # 2 TON
    return buyer


@pytest.mark.asyncio
async def test_buy_nft_success(mock_db_session, mock_nft, mock_buyer):
    """Успешная покупка NFT"""
    # Arrange
    mock_db_session.execute.side_effect = [
        Mock(scalar_one_or_none=Mock(return_value=mock_nft)),  # get NFT
        Mock(scalar_one=Mock(return_value=mock_buyer)),  # get buyer
    ]

    with patch("app.use_cases.nft.buy_nft.redis_lock") as mock_lock, patch(
        "app.use_cases.nft.buy_nft.get_uow"
    ) as mock_uow, patch("app.use_cases.nft.buy_nft.sell_nft") as mock_sell_nft:
        mock_lock.return_value.__aenter__ = AsyncMock()
        mock_lock.return_value.__aexit__ = AsyncMock()

        uow_instance = AsyncMock()
        uow_instance.commit = AsyncMock()
        mock_uow.return_value.__aenter__ = AsyncMock(return_value=uow_instance)
        mock_uow.return_value.__aexit__ = AsyncMock()

        use_case = BuyNFTUseCase(mock_db_session)

        # Act
        result = await use_case.execute(nft_id=1, buyer_id=3)

        # Assert
        assert result["success"] is True
        assert result["nft_id"] == 1
        assert result["buyer_id"] == 3
        assert result["seller_id"] == 2
        assert result["price"] == 1000000000

        # Проверяем что commit был вызван
        uow_instance.commit.assert_called_once()

        # Проверяем что уведомление отправлено
        mock_sell_nft.assert_called_once()

        # Проверяем финансовые операции
        assert mock_buyer.market_balance == 1000000000  # 2 TON - 1 TON
        assert mock_nft.user_id == 3  # Владелец изменился
        assert mock_nft.price is None  # Цена сброшена


@pytest.mark.asyncio
async def test_buy_nft_not_found(mock_db_session):
    """Покупка несуществующего NFT"""
    # Arrange
    mock_db_session.execute.return_value = Mock(scalar_one_or_none=Mock(return_value=None))

    with patch("app.use_cases.nft.buy_nft.redis_lock") as mock_lock, patch("app.use_cases.nft.buy_nft.get_uow") as mock_uow:
        mock_lock.return_value.__aenter__ = AsyncMock()
        mock_lock.return_value.__aexit__ = AsyncMock()

        uow_instance = AsyncMock()
        mock_uow.return_value.__aenter__ = AsyncMock(return_value=uow_instance)
        mock_uow.return_value.__aexit__ = AsyncMock()

        use_case = BuyNFTUseCase(mock_db_session)

        # Act & Assert
        with pytest.raises(NFTNotFoundError):
            await use_case.execute(nft_id=999, buyer_id=3)


@pytest.mark.asyncio
async def test_buy_nft_insufficient_balance(mock_db_session, mock_nft):
    """Покупка NFT с недостаточным балансом"""
    # Arrange
    poor_buyer = Mock()
    poor_buyer.id = 3
    poor_buyer.market_balance = 500000000  # 0.5 TON (недостаточно)

    mock_db_session.execute.side_effect = [
        Mock(scalar_one_or_none=Mock(return_value=mock_nft)),  # get NFT
        Mock(scalar_one=Mock(return_value=poor_buyer)),  # get buyer
    ]

    with patch("app.use_cases.nft.buy_nft.redis_lock") as mock_lock, patch("app.use_cases.nft.buy_nft.get_uow") as mock_uow:
        mock_lock.return_value.__aenter__ = AsyncMock()
        mock_lock.return_value.__aexit__ = AsyncMock()

        uow_instance = AsyncMock()
        mock_uow.return_value.__aenter__ = AsyncMock(return_value=uow_instance)
        mock_uow.return_value.__aexit__ = AsyncMock()

        use_case = BuyNFTUseCase(mock_db_session)

        # Act & Assert
        with pytest.raises(InsufficientBalanceError):
            await use_case.execute(nft_id=1, buyer_id=3)

        # Проверяем что commit НЕ был вызван
        uow_instance.commit.assert_not_called()


@pytest.mark.asyncio
async def test_buy_nft_commission_calculation(mock_db_session, mock_nft, mock_buyer):
    """Проверка правильности расчета комиссии"""
    # Arrange
    mock_db_session.execute.side_effect = [
        Mock(scalar_one_or_none=Mock(return_value=mock_nft)),
        Mock(scalar_one=Mock(return_value=mock_buyer)),
    ]

    with patch("app.use_cases.nft.buy_nft.redis_lock") as mock_lock, patch(
        "app.use_cases.nft.buy_nft.get_uow"
    ) as mock_uow, patch("app.use_cases.nft.buy_nft.sell_nft") as mock_sell_nft, patch(
        "app.use_cases.nft.buy_nft.settings"
    ) as mock_settings:
        mock_settings.market_comission = 10  # 10% комиссия

        mock_lock.return_value.__aenter__ = AsyncMock()
        mock_lock.return_value.__aexit__ = AsyncMock()

        uow_instance = AsyncMock()
        mock_uow.return_value.__aenter__ = AsyncMock(return_value=uow_instance)
        mock_uow.return_value.__aexit__ = AsyncMock()

        use_case = BuyNFTUseCase(mock_db_session)

        # Act
        result = await use_case.execute(nft_id=1, buyer_id=3)

        # Assert
        expected_commission = round(1000000000 / 100 * 10)  # 100000000 (0.1 TON)
        assert result["commission"] == expected_commission

        # Продавец должен получить цену минус комиссия
        expected_seller_amount = 1000000000 - expected_commission
        assert mock_nft.user.market_balance == 5000000000 + expected_seller_amount
