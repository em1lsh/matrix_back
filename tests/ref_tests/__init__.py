"""
Рефакторинг-тесты (ref_tests) - тесты для отслеживания состояния API при рефакторинге.

Цель: Убедиться что все эндпоинты возвращают статус 200 и базовая бизнес-логика работает.
Эти тесты должны проходить ДО и ПОСЛЕ любого рефакторинга.

Структура:
- test_ref_accounts.py - тесты для /api/accounts/*
- test_ref_auctions.py - тесты для /api/auctions/*
- test_ref_channels.py - тесты для /api/channels/*
- test_ref_market.py - тесты для /api/market/*
- test_ref_nft.py - тесты для /api/nft/*
- test_ref_offers.py - тесты для /api/offers/*
- test_ref_presale.py - тесты для /api/presales/*
- test_ref_trades.py - тесты для /api/trade/*
- test_ref_users.py - тесты для /api/users/*
"""
