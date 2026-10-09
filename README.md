# Campus Customs Shop + Chatbot

A React + Vite + TypeScript storefront with a FastAPI backend for the Campus Customs Homework 4 project. The product catalogue, prices, inventory, and account records come from the course SQLite database.

## What is included

- Home, Products, About Us, Log in, and Create account pages
- Product cards, detail pages, product images, and size-level stock
- Floating chat that can show matching product cards
- Account registration and login with salted PBKDF2 password hashes
- Per-account chat history for signed-in shoppers; guest chat is temporary
- A PydanticAI integration for Portkey or direct OpenAI, plus a local database-backed assistant that works without a model key
- Product and inventory tools, safety prompt, append-only audit history, and homework write-ups under `output/`

## Course data

The database and product images are local-only and are intentionally excluded from Git. Download the course `data.zip` and unzip it in this folder so the paths are:

```text
data/campus_customs.db
data/products/
```

The app will start without the data pack, but product, account, and chat features need the database.

## Run the backend

Use Python 3.11 or newer. From the `hw4/` folder:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd backend
uvicorn main:app --reload --port 8000
```

The API docs are available at `http://127.0.0.1:8000/docs`.

## Run the front end

In a second terminal, from the `hw4/` folder:

```bash
cd frontend
npm install
npm run dev
```

Open the local Vite address shown in the terminal, usually `http://127.0.0.1:5173`.

## Chat model mode

The local assistant searches the database and answers price and stock questions without calling an external model. To enable the PydanticAI agent through Portkey, copy `.env.example` to `.env` and set `PORTKEY_API_KEY`. The default Portkey model is `gpt-4o-mini-2024-07-18`, which is the concrete model route available to the course gateway. You can change the model or gateway URL with `PORTKEY_MODEL` and `PORTKEY_BASE_URL`. Alternatively, set `USE_REMOTE_MODEL=true` and provide `OPENAI_API_KEY` to call OpenAI directly. If the remote model setup is unavailable, the app falls back to its local assistant. In remote mode, a signed-in shopper's name and email, plus the current product ID, are included in the model context so follow-up questions can refer to the right item.

Set a long random `APP_SECRET` in `.env` before using this outside local development. Never commit `.env`, the course database, or product images.
