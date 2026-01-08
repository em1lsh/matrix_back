from fastapi import FastAPI

from .mrkt.route import mrkt_router
from .portals.route import portals_router
from .tonnel.route import tonnel_router


def include_integrations(app: FastAPI):
    app.include_router(mrkt_router)
    app.include_router(tonnel_router)
    app.include_router(portals_router)
