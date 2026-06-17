# FitFindr — Starter Kit

This starter kit contains everything you need to begin Project 2.

## What's Included

```
ai201-project2-fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # Helper functions for loading the data
├── planning.md                # Your planning template — fill this out first
└── requirements.txt           # Python dependencies
```

## Setup

**macOS / Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows:**
```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (get a free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```

## The Mock Listings Dataset

`data/listings.json` contains 40 mock secondhand listings across categories (tops, bottoms, outerwear, shoes, accessories) and styles (vintage, y2k, grunge, cottagecore, streetwear, and more).

Each listing has: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

Load it with:
```python
from utils.data_loader import load_listings
listings = load_listings()
```

## The Wardrobe Schema

`data/wardrobe_schema.json` defines the format your agent uses to represent a user's existing wardrobe. It includes:

- `schema`: field definitions for a wardrobe item
- `example_wardrobe`: a sample wardrobe with 10 items you can use for testing
- `empty_wardrobe`: a starting template for a new user

Load an example wardrobe with:
```python
from utils.data_loader import get_example_wardrobe
wardrobe = get_example_wardrobe()
```

## Tool Inventory

Your README submission must document each tool's name, inputs, and return value. **These must exactly match your actual function signatures in `tools.py`.** Your documented interfaces will be checked against your actual function signatures in `tools.py` — if the parameter count or types contradict what's in the code, you may not receive full credit for that tool.

### `search_listings(description, size, max_price)`

**Purpose:** Search the mock listings dataset for items that match the user query, optional size, and optional price ceiling.

**Inputs:**
- `description` (str): The item the user wants, such as `"vintage graphic tee"`.
- `size` (str | None): Optional size filter such as `"M"`, `"W30 L30"`, or `"XXS"`.
- `max_price` (float | None): Optional maximum price to keep listings at or below the budget.

**Output:**
- `list[dict]`: A list of listing dictionaries sorted by relevance. Each dict contains `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

### `suggest_outfit(new_item, wardrobe)`

**Purpose:** Generate 1–2 outfit ideas around the selected thrift item using the user's wardrobe, or general styling advice if the wardrobe is empty.

**Inputs:**
- `new_item` (dict): The selected listing dictionary returned by `search_listings`.
- `wardrobe` (dict): A wardrobe dictionary with an `items` key containing a list of wardrobe item dicts.

**Output:**
- `str`: A non-empty outfit suggestion string. The string names specific wardrobe pieces when they exist and falls back to general styling advice when the wardrobe is empty.

### `create_fit_card(outfit, new_item)`

**Purpose:** Turn the outfit suggestion and item details into a short, shareable caption for the final fit card.

**Inputs:**
- `outfit` (str): The outfit suggestion string returned by `suggest_outfit`.
- `new_item` (dict): The selected listing dictionary returned by `search_listings`.

**Output:**
- `str`: A 2–4 sentence caption that mentions the item name, price, and platform naturally. If `outfit` is empty, it returns a descriptive error string instead of raising an exception.

---

## Planning Loop

The planning loop in `run_agent()` always follows the same order: create a fresh session, parse the query into `description`, `size`, and `max_price`, call `search_listings()`, and stop immediately if that returns an empty list. If search results exist, the agent stores the first result in `session["selected_item"]`, calls `suggest_outfit()` with that item and the current wardrobe, and stops early if the outfit string is blank. Only when both earlier steps succeed does it call `create_fit_card()` and store the caption in `session["fit_card"]`; on success, `session["error"]` stays `None`.

---

## State Management

State is kept entirely inside the session dictionary returned by `_new_session()`. The query parser writes its output to `session["parsed"]`, `search_listings()` writes its full result list to `session["search_results"]`, the top match is copied into `session["selected_item"]`, `suggest_outfit()` writes its text into `session["outfit_suggestion"]`, and `create_fit_card()` writes the final caption into `session["fit_card"]`. That same session object is passed from one step to the next, so each tool reads the exact values created by the previous step and there is no hidden global state.

---

## Interaction Walkthrough

**User query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1 — Tool called:** `search_listings(description="vintage graphic tee", size=None, max_price=30)`
- **Why this tool:** It finds the most relevant thrift listings that match the user's item request and budget.
- **Output:** A sorted list of matching listings, with the top result being `Y2K Baby Tee — Butterfly Print` in my example run.

**Step 2 — Tool called:** `suggest_outfit(new_item=selected_item, wardrobe=get_example_wardrobe())`
- **Why this tool:** It turns the selected item into an outfit recommendation using the user's existing wardrobe pieces.
- **Output:** A styling paragraph that pairs the tee with pieces like baggy jeans, a cropped hoodie, and chunky sneakers.

**Step 3 — Tool called:** `create_fit_card(outfit=outfit_suggestion, new_item=selected_item)`
- **Why this tool:** It converts the outfit idea into a short caption the user can reuse or post.
- **Output:** A 2–4 sentence fit-card caption mentioning the item, price, platform, and outfit vibe.

**Final output to user:** The user sees the top listing, a concrete outfit suggestion, and a short fit-card caption that explains how to style the item.

---

## Error Handling and Fail Points

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| `search_listings` | No listings match the query, size, and budget. | Return `[]`, then have the agent stop immediately and show the user `No listings found. Try a broader description or a higher price limit.` In my testing, `search_listings('designer ballgown', size='XXS', max_price=5)` returned an empty list with no exception. |
| `suggest_outfit` | The wardrobe is empty or cannot produce a useful outfit. | Return a general styling paragraph instead of crashing. In my testing, calling `suggest_outfit()` with `get_empty_wardrobe()` still produced a non-empty suggestion about general styling rather than throwing an error. |
| `create_fit_card` | The outfit string is missing or blank. | Return a descriptive error message string instead of raising an exception. In my testing, `create_fit_card('', results[0])` returned `Unable to create a fit card because the outfit suggestion is missing.` |

---

## Spec Reflection

**One way planning.md helped during implementation:**
The planning document kept the tool contracts and the planning-loop branches explicit before I wrote code. That made it easier to implement `run_agent()` without guessing, because I could directly match the session fields, error messages, and early-return points to the spec I had already written.

**One divergence from your spec, and why:**
I originally planned to make the outfit and fit-card tools behave strictly by returning empty strings on failure, but in implementation I added defensive fallback text so the UI still shows something useful when Groq returns an empty response or the network fails. I kept the planning logic aligned with the spec by treating those cases as errors at the agent level, but the tool functions themselves are more resilient than the first draft suggested.

---

## AI Usage

I used Copilot to draft `search_listings()` from the Tool 1 spec, then revised it so it used `load_listings()` from `utils/data_loader.py` instead of re-reading files manually. I also overrode the first draft of the size filter because it was too strict for values like `S/M` and `One Size / Oversized`, and I changed it to match by substring and token overlap instead.

I used Copilot again for `run_agent()` and gave it the Planning Loop, State Management, and Architecture sections from `planning.md`. The generated version was too shallow at first because it called the tools without storing all intermediate values, so I revised it to write every step into the session dict, return early on empty search results, and preserve the exact error strings documented in the README and planning file.

---

## Where to Start

1. **Read `planning.md` and fill it out before writing any code.**
2. Verify the data loads correctly by running `python utils/data_loader.py`.
3. Build and test each tool individually before connecting them through your planning loop.

Your implementation files go in this same directory. There's no required file structure for your agent code — organize it however makes sense for your design.
