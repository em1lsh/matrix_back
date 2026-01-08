# app/api/routers/health.py

import logging
from collections import deque

from fastapi import APIRouter, HTTPException, Request


router = APIRouter()
log_buffer = deque(maxlen=1000)


class LogBufferHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
            log_buffer.append(message)
        except Exception:
            self.handleError(record)


@router.get("/health")
async def health(request: Request):
    real_ip = request.headers.get("x-real-ip") or request.headers.get("cf-connecting-ip") or request.client.host

    allowed_ips = {"127.0.0.1", "::1"}
    if real_ip not in allowed_ips:
        raise HTTPException(status_code=403, detail="Forbidden")

    return {"status": "ok"}


@router.get("/logs")
async def get_last_logs():
    tail = list(log_buffer)[-500:]

    lines = []
    for entry in tail:
        for line in str(entry).rstrip("\n").splitlines():
            lines.append(line)

    lines = lines[-500:]

    return {"logs": lines}
