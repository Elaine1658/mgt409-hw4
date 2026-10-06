# System harness and data notes

## Problem 2 — Database fields

The course data pack starts with three application tables: `catalogue`, `inventory`, and `users`. Problem 8 adds `chat_messages` at runtime for signed-in chat history. The internal `sqlite_sequence` table is SQLite bookkeeping and is not used by the shop.

### `catalogue`

| Field | Type | Why it matters |
|---|---|---|
| `product_id` | TEXT, primary key | Stable key for product pages, card links, and tool lookups. |
| `name` | TEXT | Customer-facing item name and exact product search. |
| `garment_type` | TEXT | Lets shoppers browse by category, such as hoodie or crewneck. |
| `description` | TEXT | Product facts used on detail pages and in assistant replies. |
| `colors` | TEXT containing JSON | Lists recorded product colors; the assistant does not invent color options. |
| `search_tags` | TEXT containing JSON | Helps find items by sport, college, design, and common search words. |
| `image_file_path` | TEXT | Maps each item to its local image in `data/products/`. |
| `price` | REAL | The authoritative item price shown by the site and chat tools. |

### `inventory`

| Field | Type | Why it matters |
|---|---|---|
| `id` | INTEGER, primary key | Unique inventory row identifier. |
| `product_id` | TEXT | Joins a stock row to the product it belongs to. |
| `size` | TEXT | Identifies the size a shopper asks about. |
| `quantity` | INTEGER | Exact stock count; zero is reported as out of stock. |

### `users`

| Field | Type | Why it matters |
|---|---|---|
| `id` | INTEGER, primary key | Internal account key used for signed-in chat history. |
| `name` | TEXT | Existing display name for a shopper. |
| `email` | TEXT | Login identifier and account lookup field. |
| `password_hash` | TEXT | PBKDF2-SHA256 hash used to verify passwords; never returned to the browser or written to the audit trail. |
| `created_at` | TEXT | Records when the account was created. |
| `first_name` | TEXT, nullable | Greeting shown in the site header and assistant context. |
| `last_name` | TEXT, nullable | Supports account creation and the public profile. |

### `chat_messages`

| Field | Type | Why it matters |
|---|---|---|
| `id` | INTEGER, primary key | Orders messages when history is reloaded. |
| `user_id` | INTEGER | Keeps saved chat history scoped to one signed-in account. |
| `role` | TEXT | Tells the UI whether a message came from the shopper or assistant. |
| `content` | TEXT | Stores the visible message for signed-in shoppers. |
| `products_json` | TEXT, nullable | Preserves structured product cards in assistant replies. |
| `created_at` | TEXT | Gives each saved message its database timestamp. |

## Front end and API contract

- The Vite development server runs on port `5173` and proxies `/api` and `/media` to FastAPI on port `8000`.
- `GET /api/products?search=&limit=` returns catalogue cards with the database description, price, colors, image URL, and per-size inventory. Catalogue requests are capped at 120 cards.
- `GET /api/products/{product_id}` returns one full detail card. Images are served from `/media/products/{filename}` using the local course pack.
- `POST /api/auth/register` and `POST /api/auth/login` return a signed seven-day session token and public profile fields. Requests use `Authorization: Bearer …` after login.
- `POST /api/chat` accepts `message`, optional `product_id`, and `page_route`. It returns `reply`, up to eight database-verified `products`, `history_saved`, and `assistant_mode`.
- `GET /api/chat/history` returns the latest 40 messages for the authenticated shopper. Guest chat is not saved. The database query is always scoped by the signed-in user ID.

## Agent model and tools

`backend/models.py` defines `ProductCard`, `StockLevel`, `ChatRequest`, `ChatResponse`, `ChatHistoryItem`, and the PydanticAI `AgentReply`. `AgentReply` contains a short answer and product IDs. The server turns those IDs back into product cards from SQLite before sending the response to the page.

`backend/agent.py` loads `backend/prompts/prompt.md`, passes the signed-in name/email and current product ID as dynamic context, and exposes these tools when optional PydanticAI mode is enabled. The current product page is resolved to its database name and ID so the agent can interpret follow-up questions such as “do you have this in pink?”

| Tool | Inputs | Result fields and reason |
|---|---|---|
| `search_catalogue` | Search text | Returns at most eight full `ProductCard` matches so the assistant can recommend real products and the site can display cards. |
| `get_product_info` | `product_id` | Returns the canonical description, price, colors, image, and inventory for one item. |
| `get_stock` | `product_id`, optional `size` | Returns database stock by size and the product price for exact availability questions. |

The local assistant is the default and works without any model credential. It calls the same SQLite lookup functions, answers price and stock questions only from database values, and asks a follow-up when it cannot identify one item confidently. PydanticAI with a direct OpenAI key can be enabled explicitly with `USE_REMOTE_MODEL=true`; the remote model defaults to `openai:gpt-5-mini` and can be changed with `OPENAI_MODEL`. The application does not read `PORTKEY_API_KEY`. In remote mode, each run allows at most 5 model requests and 8 total tool calls.

## Auth, memory, and safety

- New passwords use a salted PBKDF2-SHA256 hash with 600,000 rounds. The provided test account uses the course fixture's three-part PBKDF2-SHA256 format with a fixture-defined salt and 120,000 rounds; the verifier supports both formats.
- The app returns only public account fields. Password hashes, API keys, session tokens, and full chat messages are not written to the audit trail.
- A shopper's name, email, and current product page may be used as context for the current chat request. In remote mode, these fields are sent to the configured model provider. Guest chats remain temporary; logged-in messages use that shopper's `user_id`.
- `output/audit_trail.json` is a logical append-only list. Each entry records an ISO timestamp, tool name, short arguments, a result summary, and a stop reason. It omits passwords, API keys, session tokens, and full customer messages.
- The agent must use database tools for product facts, report a zero quantity explicitly, and clarify an uncertain match instead of guessing.
- The assistant cannot place orders, reserve stock, modify inventory, or request a password or payment details in chat.
- Database access uses parameterized SQL. Product images are served from the local products directory. Search results are bounded.

## Limits and run steps

- Message length: at most 1,500 characters.
- Product results: at most 8 in chat, 120 in a catalogue request.
- Saved history: latest 40 messages returned; a request can read at most 80.
- Search operations use the local SQLite database; no vector database or external service is required. The optional model mode uses the configured direct OpenAI provider.
- Front end: from `frontend/`, run `npm install` and `npm run dev` (port 5173).
- Back end: from `backend/`, run `uvicorn main:app --reload --port 8000`.
- Before a public deployment, set a unique `APP_SECRET`. The example value is for local development only.
- Test account credentials are omitted from this public repository. Use the credentials provided with the course fixture locally.
