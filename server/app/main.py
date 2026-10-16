from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import init_db
from app.routers.admin import router as admin_router
from app.routers.public import router as public_router
from app.services.settings_loader import import_claude_settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """启动时建库、导入 AI 配置。"""
    init_db()
    import_claude_settings()
    yield


app = FastAPI(title="装了吗", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(public_router)
app.include_router(admin_router)
