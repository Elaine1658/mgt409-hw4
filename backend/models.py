from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class StockLevel(BaseModel):
    size: str
    quantity: int


class ProductCard(BaseModel):
    product_id: str
    name: str
    garment_type: str
    description: str
    colors: list[str] = Field(default_factory=list)
    search_tags: list[str] = Field(default_factory=list)
    image_file_path: str
    image_url: str
    price: float
    inventory: list[StockLevel] = Field(default_factory=list)
    total_stock: int = 0


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1500)
    product_id: str | None = Field(default=None, max_length=120)
    page_route: str | None = Field(default=None, max_length=240)


class ChatResponse(BaseModel):
    reply: str
    products: list[ProductCard] = Field(default_factory=list)
    history_saved: bool = False
    assistant_mode: str


class RegisterRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class PublicUser(BaseModel):
    id: int
    first_name: str
    last_name: str
    name: str
    email: EmailStr


class AuthResponse(BaseModel):
    token: str
    user: PublicUser


class ChatHistoryItem(BaseModel):
    id: int
    role: str
    content: str
    products: list[ProductCard] = Field(default_factory=list)
    created_at: str


class AgentReply(BaseModel):
    reply: str = Field(description="A concise, friendly reply grounded in the shop tools")
    product_ids: list[str] = Field(
        default_factory=list,
        description="IDs of catalogue items that should appear as cards, at most eight",
    )
