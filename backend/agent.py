from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from models import AgentReply, ProductCard
from tools import get_product, record_audit, search_products


PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "prompt.md"
PROMPT_TEXT = PROMPT_PATH.read_text(encoding="utf-8") if PROMPT_PATH.exists() else ""
REMOTE_MODEL_ENABLED = (
    os.getenv("USE_REMOTE_MODEL", "false").strip().lower() == "true"
    and bool(os.getenv("OPENAI_API_KEY"))
)
ASSISTANT: Any = None


class ShopDeps:
    def __init__(
        self,
        product_id: str | None = None,
        user_name: str | None = None,
        user_email: str | None = None,
    ) -> None:
        self.product_id = product_id
        self.user_name = user_name
        self.user_email = user_email


if REMOTE_MODEL_ENABLED:
    try:
        from pydantic_ai import Agent, RunContext, UsageLimits

        MAX_AGENT_REQUESTS = 5
        MAX_AGENT_TOOL_CALLS = 8

        ASSISTANT = Agent(
            os.getenv("OPENAI_MODEL", "openai:gpt-5-mini"),
            deps_type=ShopDeps,
            output_type=AgentReply,
            instructions=PROMPT_TEXT,
        )

        @ASSISTANT.tool
        def search_catalogue(ctx: RunContext[ShopDeps], query: str) -> list[dict[str, Any]]:
            products = search_products(query, limit=8)
            record_audit(
                "search_catalogue",
                {"query_length": len(query), "limit": 8},
                f"Returned {len(products)} catalogue matches",
                "tool_complete",
            )
            return [product.model_dump() for product in products]

        @ASSISTANT.tool
        def get_product_info(ctx: RunContext[ShopDeps], product_id: str) -> dict[str, Any] | None:
            product = get_product(product_id)
            record_audit(
                "get_product_info",
                {"product_id": product_id[:120]},
                "Product found" if product else "No product with this ID",
                "tool_complete",
            )
            return product.model_dump() if product else None

        @ASSISTANT.tool
        def get_stock(ctx: RunContext[ShopDeps], product_id: str, size: str | None = None) -> dict[str, Any]:
            product = get_product(product_id)
            if not product:
                result = {"found": False, "inventory": []}
            else:
                inventory = [x.model_dump() for x in product.inventory]
                if size:
                    inventory = [x for x in inventory if x["size"].lower() == size.lower()]
                result = {
                    "found": True,
                    "product_id": product.product_id,
                    "name": product.name,
                    "price": product.price,
                    "inventory": inventory,
                    "total_stock": sum(x["quantity"] for x in inventory) if size else product.total_stock,
                }
            record_audit(
                "get_stock",
                {"product_id": product_id[:120], "size": (size or "")[:12]},
                "Inventory lookup completed",
                "tool_complete",
            )
            return result

        @ASSISTANT.instructions
        def shopper_and_page_context(ctx: RunContext[ShopDeps]) -> str:
            details: list[str] = []
            if ctx.deps.user_name:
                details.append(f"Signed-in shopper name: {ctx.deps.user_name}.")
            if ctx.deps.user_email:
                details.append(f"Signed-in shopper email: {ctx.deps.user_email}.")
            if ctx.deps.product_id:
                product = get_product(ctx.deps.product_id)
                if product:
                    details.append(
                        f"Current product page: {product.name} (product ID: {product.product_id}). "
                        "Use this item to interpret references such as 'this item', and use the shop tools for facts."
                    )
            if not details:
                return "The shopper is a guest, and no product page context is available."
            return "\n".join(details)

    except Exception:
        # The keyless local assistant remains available if optional model setup is incomplete.
        ASSISTANT = None


def _normalize(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
    aliases = {
        "hoodies": "hoodie", "shirts": "shirt", "tees": "shirt", "tshirts": "shirt",
        "crewnecks": "crewneck", "sweatshirts": "sweatshirt", "sweaters": "sweater",
        "jackets": "jacket",
    }
    return " ".join(aliases.get(token, token) for token in text.split())


def _product_tokens(value: str) -> set[str]:
    ignored = {
        "a", "about", "an", "and", "are", "available", "can", "cost", "do", "does",
        "for", "have", "how", "in", "is", "it", "many", "me", "much", "of", "our",
        "price", "size", "sizes", "stock", "the", "this", "that", "what", "with", "you",
    }
    return {token for token in _normalize(value).split() if token not in ignored and not token.isdigit()}


def _is_category_question(message: str) -> bool:
    text = _normalize(message)
    return any(
        term in text.split()
        for term in ("hoodie", "hoodies", "shirt", "shirts", "crewneck", "crewnecks", "sweatshirt", "sweaters", "jacket", "jackets")
    )


def _find_product(message: str, product_id: str | None) -> ProductCard | None:
    text = _normalize(message)
    category_question = _is_category_question(message)
    pronoun_context = any(word in text.split() for word in ("this", "it", "that", "one"))
    if product_id and not category_question and (pronoun_context or len(text.split()) <= 4):
        product = get_product(product_id)
        if product:
            record_audit("get_product_info", {"product_id": product_id}, "Current product context loaded", "tool_complete")
            return product

    candidates = search_products(message, limit=8)
    best: ProductCard | None = None
    best_score = 0.0
    query_tokens = _product_tokens(message)
    for product in candidates:
        name_tokens = _product_tokens(product.name)
        overlap = len(name_tokens & query_tokens) / max(1, len(name_tokens))
        if overlap > best_score:
            best, best_score = product, overlap
    if best and best_score >= 0.5:
        return best
    return None


def _size_in(message: str) -> str | None:
    match = re.search(r"\b(XXS|XXL|XS|XL|S|M|L)\b", message, flags=re.IGNORECASE)
    return match.group(1).upper() if match else None


def _has_stock_intent(message: str) -> bool:
    return bool(re.search(r"\b(stock|available|availability|quantity|size|sizes|have|carry)\b", message, re.I))


def _has_price_intent(message: str) -> bool:
    return bool(re.search(r"\b(price|cost|how much|priced)\b", message, re.I))


def _local_reply(message: str, deps: ShopDeps) -> tuple[AgentReply, list[ProductCard], str]:
    product = _find_product(message, deps.product_id)
    stock_question = _has_stock_intent(message)
    price_question = _has_price_intent(message)

    category_request = _is_category_question(message) and product is None
    if product and (stock_question or price_question):
        requested_color = next(
            (color for color in ("pink", "navy", "blue", "white", "gray", "grey", "black", "red", "cream", "yellow", "green") if re.search(rf"\b{color}\b", message, re.I)),
            None,
        )
        if requested_color:
            known_colors = {color.lower() for color in product.colors}
            if requested_color not in known_colors:
                listed_colors = ", ".join(product.colors) if product.colors else "no colors"
                reply = f"The catalogue does not list {requested_color} for {product.name}. The recorded colors are {listed_colors}."
                record_audit(
                    "answer_from_catalogue",
                    {"product_id": product.product_id, "color_check": requested_color},
                    "Color list checked against the catalogue; stock is not tracked by color",
                    "local_color_reply",
                )
                return AgentReply(reply=reply, product_ids=[product.product_id]), [product], "local"
            reply = f"The catalogue lists {requested_color} for {product.name}, but inventory is tracked by size, not by color. {product.total_stock} total unit(s) are listed across sizes."
            record_audit(
                "answer_from_catalogue",
                {"product_id": product.product_id, "color_check": requested_color},
                "Color confirmed; stock is tracked by size only",
                "local_color_reply",
            )
            return AgentReply(reply=reply, product_ids=[product.product_id]), [product], "local"
        size = _size_in(message)
        price_line = f"It is listed at ${product.price:.2f}."
        if stock_question:
            levels = product.inventory
            if size:
                selected = next((row for row in levels if row.size.lower() == size.lower()), None)
                if selected is None:
                    reply = f"I do not see a {size} inventory record for {product.name}. {price_line}"
                elif selected.quantity == 0:
                    reply = f"{product.name} is currently out of stock in size {size}. {price_line}"
                else:
                    reply = f"Yes. {product.name} has {selected.quantity} in stock in size {size}. {price_line}"
            else:
                available = [f"{row.size}: {row.quantity}" for row in levels]
                if available:
                    reply = f"Here is the current inventory for {product.name}: {', '.join(available)}. {price_line}"
                else:
                    reply = f"I do not have a size-level inventory record for {product.name}. {price_line}"
        else:
            reply = f"{product.name} is listed at ${product.price:.2f}. Its description is: {product.description}"
        record_audit(
            "answer_from_catalogue",
            {"product_id": product.product_id, "size": _size_in(message) or ""},
            "Price and stock facts read from the course database",
            "local_fact_reply",
        )
        return AgentReply(reply=reply, product_ids=[product.product_id]), [product], "local"

    if product:
        reply = f"{product.name}: {product.description} It is ${product.price:.2f}. I have shown the item below so you can check the current sizes and stock."
        record_audit("get_product_info", {"product_id": product.product_id}, "Product details loaded", "local_product_reply")
        return AgentReply(reply=reply, product_ids=[product.product_id]), [product], "local"

    matches = search_products(message, limit=8)
    record_audit(
        "search_catalogue",
        {"query_terms": len(_normalize(message).split()), "limit": 8},
        f"Returned {len(matches)} catalogue matches",
        "local_search_complete",
    )
    if matches:
        if (stock_question or price_question) and not category_request:
            reply = "I found a few possible items. Please choose the exact style so I can check its price and size-level stock accurately."
        else:
            reply = f"I found {len(matches)} matching item(s) in the catalogue. Their prices and stock are listed on each card. Select a card to see all sizes."
        return AgentReply(reply=reply, product_ids=[item.product_id for item in matches]), matches, "local"

    lowered = message.strip().lower()
    if any(greeting in lowered for greeting in ("hello", "hi", "hey")):
        first_name = deps.user_name.split(maxsplit=1)[0] if deps.user_name else ""
        greeting = f"Hi, {first_name}!" if first_name else "Hi!"
        reply = f"{greeting} I can help you find Campus Customs products and check prices or size-level stock. What are you looking for?"
    else:
        reply = "I could not find a clear match in the product catalogue. Please share the product name or type, and I will check the database."
    record_audit("assistant_reply", {"intent": "clarify"}, "Asked for a clearer product request", "local_clarification")
    return AgentReply(reply=reply), [], "local"


async def answer_message(
    message: str,
    product_id: str | None = None,
    user_name: str | None = None,
    user_email: str | None = None,
) -> tuple[AgentReply, list[ProductCard], str]:
    deps = ShopDeps(product_id=product_id, user_name=user_name, user_email=user_email)
    if ASSISTANT is None:
        return _local_reply(message, deps)

    try:
        result = await ASSISTANT.run(
            message,
            deps=deps,
            usage_limits=UsageLimits(
                request_limit=MAX_AGENT_REQUESTS,
                tool_calls_limit=MAX_AGENT_TOOL_CALLS,
            ),
        )
        structured: AgentReply = result.output
        products: list[ProductCard] = []
        for product_id in structured.product_ids[:8]:
            product = get_product(product_id)
            if product:
                products.append(product)
        record_audit(
            "assistant_reply",
            {"product_context": product_id or ""},
            f"Generated a structured reply with {len(products)} verified product cards",
            "agent_completed",
        )
        return structured, products, "pydantic-ai"
    except Exception:
        record_audit("assistant_reply", {"mode": "fallback"}, "Remote model unavailable; used local catalogue logic", "model_error_fallback")
        return _local_reply(message, deps)
