from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent
load_dotenv(ROOT_DIR / ".env", override=False)
APP_SECRET = os.getenv("APP_SECRET", "local-development-only-change-before-deployment")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("campus-customs")
if APP_SECRET == "local-development-only-change-before-deployment" or APP_SECRET.startswith("replace-"):
    APP_SECRET = secrets.token_urlsafe(32)
    logger.warning("Using a temporary local session secret; set APP_SECRET in .env for stable sessions.")

from agent import REMOTE_MODEL_ENABLED, answer_message
from models import (
    AuthResponse,
    ChatHistoryItem,
    ChatRequest,
    ChatResponse,
    LoginRequest,
    ProductCard,
    PublicUser,
    RegisterRequest,
)
from tools import (
    DATABASE_PATH,
    PRODUCTS_DIR,
    create_user,
    ensure_audit_file,
    ensure_chat_table,
    get_product,
    get_user_by_email,
    get_user_by_id,
    list_products,
    load_chat_history,
    record_audit,
    save_chat_message,
    verify_password,
)


def _user_for_response(user: dict[str, Any]) -> PublicUser:
    full_name = str(user.get("name") or "Campus Customs shopper").strip()
    parts = full_name.split(maxsplit=1)
    first_name = str(user.get("first_name") or (parts[0] if parts else "Shopper")).strip()
    last_name = str(user.get("last_name") or (parts[1] if len(parts) > 1 else "")).strip()
    return PublicUser(
        id=int(user["id"]),
        first_name=first_name,
        last_name=last_name,
        name=full_name,
        email=str(user["email"]),
    )


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _create_session_token(user_id: int) -> str:
    payload = _b64(json.dumps({"sub": user_id, "exp": int(time.time()) + 7 * 24 * 3600}).encode())
    signature = _b64(hmac.new(APP_SECRET.encode(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{signature}"


def _decode_session_token(token: str) -> int | None:
    try:
        payload, signature = token.split(".", 1)
        expected = _b64(hmac.new(APP_SECRET.encode(), payload.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            return None
        padding = "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload + padding))
        if int(data.get("exp", 0)) <= int(time.time()):
            return None
        return int(data["sub"])
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None


def _current_user(authorization: str | None) -> dict[str, Any] | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    user_id = _decode_session_token(authorization.split(" ", 1)[1].strip())
    return get_user_by_id(user_id) if user_id is not None else None


def optional_user(authorization: str | None = Header(default=None)) -> dict[str, Any] | None:
    return _current_user(authorization)


def required_user(user: dict[str, Any] | None = Depends(optional_user)) -> dict[str, Any]:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Please log in first.")
    return user


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_audit_file()
    try:
        ensure_chat_table()
    except FileNotFoundError:
        logger.warning("Course database is missing; add data/campus_customs.db to enable shop features.")
    yield


app = FastAPI(
    title="Campus Customs Shop API",
    description="Local catalogue, account, and product-chat API for Homework 4.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
if PRODUCTS_DIR.is_dir():
    app.mount("/media/products", StaticFiles(directory=PRODUCTS_DIR), name="product-images")


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "database_ready": DATABASE_PATH.is_file(),
        "products_ready": PRODUCTS_DIR.is_dir(),
        "assistant_mode": "pydantic-ai" if REMOTE_MODEL_ENABLED else "local",
    }


@app.get("/api/products", response_model=list[ProductCard])
def products(
    search: str = Query(default="", max_length=160),
    limit: int = Query(default=120, ge=1, le=120),
) -> list[ProductCard]:
    try:
        return list_products(search, limit)
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        logger.exception("Product catalogue lookup failed")
        raise HTTPException(status_code=500, detail="The catalogue could not be loaded.") from error


@app.get("/api/products/{product_id}", response_model=ProductCard)
def product_detail(product_id: str) -> ProductCard:
    try:
        product = get_product(product_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    if product is None:
        raise HTTPException(status_code=404, detail="That product was not found.")
    return product


@app.post("/api/auth/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest) -> AuthResponse:
    try:
        if get_user_by_email(str(payload.email)):
            raise HTTPException(status_code=409, detail="An account with this email already exists.")
        user = create_user(payload.first_name, payload.last_name, str(payload.email), payload.password)
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("Account creation failed")
        raise HTTPException(status_code=500, detail="The account could not be created.") from error
    record_audit("create_account", {"email_domain": str(payload.email).split("@")[-1]}, "Created account with a salted password hash", "account_created")
    return AuthResponse(token=_create_session_token(int(user["id"])), user=_user_for_response(user))


@app.post("/api/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest) -> AuthResponse:
    try:
        user = get_user_by_email(str(payload.email))
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    if not user or not verify_password(payload.password, str(user["password_hash"])):
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    record_audit("login", {"email_domain": str(payload.email).split("@")[-1]}, "Verified password hash", "login_complete")
    return AuthResponse(token=_create_session_token(int(user["id"])), user=_user_for_response(user))


@app.get("/api/auth/me", response_model=PublicUser)
def me(user: dict[str, Any] = Depends(required_user)) -> PublicUser:
    return _user_for_response(user)


@app.get("/api/chat/history", response_model=list[ChatHistoryItem])
def chat_history(user: dict[str, Any] | None = Depends(optional_user)) -> list[ChatHistoryItem]:
    if user is None:
        return []
    try:
        return [ChatHistoryItem.model_validate(item) for item in load_chat_history(int(user["id"]))]
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    user: dict[str, Any] | None = Depends(optional_user),
) -> ChatResponse:
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Please enter a message.")
    current_product_id = payload.product_id
    if current_product_id:
        try:
            if get_product(current_product_id) is None:
                current_product_id = None
        except FileNotFoundError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
    if user is not None:
        save_chat_message(int(user["id"]), "user", message)
    try:
        result, found_products, mode = await answer_message(
            message,
            product_id=current_product_id,
            user_name=str(user.get("name") or "") if user else None,
            user_email=str(user.get("email") or "") if user else None,
        )
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        logger.exception("Chat request failed")
        raise HTTPException(status_code=500, detail="The assistant could not answer right now.") from error
    if user is not None:
        save_chat_message(int(user["id"]), "assistant", result.reply, found_products)
    return ChatResponse(
        reply=result.reply,
        products=found_products[:8],
        history_saved=user is not None,
        assistant_mode=mode,
    )
