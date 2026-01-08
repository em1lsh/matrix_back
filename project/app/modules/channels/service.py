"""Channels модуль - Service"""

from app.utils.logger import get_logger

from .exceptions import ChannelPermissionDeniedError


logger = get_logger(__name__)


class ChannelService:
    def __init__(self, repository):
        self.repo = repository

    def validate_ownership(self, channel, user_id: int):
        if channel.user_id != user_id:
            raise ChannelPermissionDeniedError(channel.id)
