# AI Prompts

> Assignment overview prompt (AI-drafted from the course scenario): “Act as my project assistant for MGT 409 Homework 4. Help me build Campus Customs, a custom-apparel store with a React, Vite, and TypeScript front end and a Python FastAPI backend using a PydanticAI agent. Shoppers should be able to browse products, create accounts, chat, see matching product cards, and get accurate prices and size-level stock from the supplied local SQLite database. Use the supplied catalogue image paths and research yalebulldogblue.com for the site's style and information for the agent prompt. Work on one problem at a time, using the problem description I provide in my own words. Explain each step in clear English suitable for an international student, and help me review each result. When the project is ready, help me publish the code to a public GitHub repository and give me its URL so I can submit it on Canvas.” This is an AI-drafted project overview, not a verbatim prompt written by the student.

## Problem 1 — Vibe coder prompts

### Prompt
Please create and maintain this `AI_prompts.md` file for Homework 4. As we work on each problem, add its number and title and keep a clear record of the main prompt. Use simple English. If a follow-up prompt is needed, include it and explain in one sentence what was missing from the first prompt.

### Follow-up prompt
Not needed for this step.

## Problem 2 — Analyze the database

### Prompt
Please inspect the course SQLite database and explain each field in the catalogue, inventory, and users tables. For every field, add a short note about how it can help the store or chatbot. Also explain the chat-history table that the app creates for signed-in shoppers.

### Follow-up prompt
Not needed; the database schema gives the fields needed for this step.

## Problem 3 — Build the Campus Customs website

### Prompt
Please build a React, Vite, and TypeScript storefront for Campus Customs. Add Home, Products, About Us, Log in, and Create account pages. Show real catalogue images and basic product details on the Products page, and make each card open a full product page. Add a floating chat panel that can connect to the backend later. Use original wording with a polished Yale-inspired campus style.

### Follow-up prompt
Please connect the product pages to the local course database and show size-level inventory when it is available. I added this because a visual storefront alone does not show the real shop data.

## Problem 4 — Create an account and log in

### Prompt
Please add account creation with first name, last name, email, and password, plus login with email and password. Store new accounts in the database and hash passwords securely. Make sure the seeded test account and a new account can both sign in.

### Follow-up prompt
Please keep account details out of chat logs and return only the shopper's public profile fields after login. This was missing from my first request about secure accounts.

## Problem 5 — PydanticAI agent backend

### Prompt
Please create a FastAPI backend in `backend/main.py` and organize the agent files as `backend/agent.py`, `backend/tools.py`, `backend/models.py`, and `backend/prompts/prompt.md`. Connect the chat widget to the backend. The app must work without my Portkey key, so keep a local, database-backed assistant as the default and make any direct model connection optional.

### Follow-up prompt
Please document how the front end calls FastAPI and how the prompt and optional model are loaded. I had not asked for those run details in my first prompt.

## Problem 6 — Product and stock tools

### Prompt
Please give the assistant database tools for product descriptions, prices, and inventory by size. It must use the actual database values and clearly say when a size is out of stock. Add the tool inputs and result fields to the project notes.

### Follow-up prompt
Please cap lookup results and ask me to identify a specific style if a stock question matches several products. This was missing from my first prompt about truthful stock answers.

## Problem 7 — Chat search that updates the page

### Prompt
When a shopper asks for a category such as hoodies, please search the catalogue and return structured product matches. Show those matches as product cards on the page, and make each card open the same full detail page used by the Products page.

### Follow-up prompt
Please pass the selected product ID with chat requests so the same item detail remains available from chat cards. I had not mentioned this page behavior in my first prompt.

## Problem 8 — Customer memory

### Prompt
Please save chat history for signed-in shoppers and reload it when they return. Give the assistant the signed-in shopper's name and email, and pass the current product page so questions like “do you have this in pink?” can use the right item. Guest chat can stay temporary.

### Follow-up prompt
Please limit saved history to the signed-in user's own account and avoid storing guest conversations. This access boundary was missing from my first prompt.

## Problem 9 — Usability improvements

### Prompt
Please add two storefront usability improvements and two assistant or backend improvements. Write a short `output/usability.md` explaining what each change does and why it helps a shopper or the business. Make sure the changes are visible in the running app.

### Follow-up prompt
Please include clear empty states, bounded search results, and a clarification response for uncertain product matches. My first prompt did not define how the app should behave when a search has no reliable answer.

## Problem 10 — Style the website

### Prompt
Please give the storefront a distinctive, imaginative design with campus colors, clear type hierarchy, polished product photography, and a chat panel that fits the shop. Keep the layout easy to use on a phone and a larger screen. Add a short `output/design.md` explaining the choices.

### Follow-up prompt
Please make the product and stock information easy to scan while keeping the visual style warm and editorial. I had not described the balance between visual character and shopping clarity in my first prompt.

## Problem 11 — Site check

### Prompt
Please check the running site and create `output/app_check.html` with a heading, screenshot, and short caption for an inventory answer, chat-generated product cards, and one usability improvement. Save the image files under `output/app_check_images/` and link them with relative paths.

### Follow-up prompt
Please use screenshots from the working local app and make each caption say exactly what the image demonstrates. This evidence detail was missing from my first prompt.

### Outcome
The local behaviors were checked, and all three screenshots are saved under `output/app_check_images/` and linked from `output/app_check.html`: the inventory answer, chat-generated product cards, and usability filters and sorting.

## Problem 12 — Audit trail, safety, and harness

### Prompt
Please keep an append-only `output/audit_trail.json` for agent and tool activity, including time, tool name, short arguments and result, and stop reason. Add practical safety rules to the prompt and finish `output/harness.md` with the model fields, tools, safety rules, limits, model mode, and run instructions.

### Follow-up prompt
Please make sure the audit trail does not include passwords, tokens, or full private chat text, and that new entries remain after later runs. I had not specified those audit details in my first prompt.

## Problem 13 — GitHub and submission

### Prompt
Please organize the project in an `hw4` folder, add `.gitignore`, `.env.example`, and a README, and keep the database and product images out of Git. Prepare the project for a public GitHub repository and include the repository URL in the final handoff when one is available.

### Follow-up prompt
Not needed for preparing the local project. Publishing still needs a GitHub repository destination and account access.
