# Usability improvements

## Front end

### 1. Search, style filters, and price sorting

The Products page has a search box, quick style filters, and price sorting. This helps shoppers narrow a large catalogue without reading every product card.

### 2. Stock status at a glance

Product cards show a stock label, and each item page lists the exact quantity by size, including a clear “Out of stock” state. This helps shoppers decide whether an item is worth opening and prevents surprises at checkout.

## Assistant and back end

### 3. Bounded catalogue searches

Chat searches return no more than eight matches, while catalogue requests are capped at 120 products. This keeps the chat response quick and the product cards easy to compare.

### 4. Clarify uncertain product matches

When a question could refer to several products, the assistant asks the shopper to choose a style before it reports price or stock. Exact facts are looked up from SQLite, which helps prevent confident but incorrect answers.
