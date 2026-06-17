# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
Searches the mock listings dataset for secondhand items that match the user's item description, optional size, and optional maximum price. It ranks matches by keyword overlap so the most relevant listing appears first.

**Input parameters:**
The function takes:
- `description` (str): The main item query in natural language, such as "vintage graphic tee" or "black cargo pants".
- `size` (str | None): An optional size filter like "M", "28", or "S/M". If omitted, the tool searches all sizes.
- `max_price` (float | None): An optional upper price limit in dollars. If omitted, the tool does not filter by price.

**What it returns:**
Returns a list of listing dictionaries sorted from best match to weakest match. Each dictionary includes `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

**What happens if it fails or returns nothing:**
If nothing matches, return an empty list. The planning loop should stop immediately, store a helpful error message in the session, and tell the user to loosen the search or raise the budget.

---

### Tool 2: suggest_outfit

**What it does:**
Builds 1–2 outfit ideas around the selected listing by combining it with compatible pieces from the user's wardrobe. If the wardrobe is empty, it falls back to general styling advice for the new item instead of requiring specific closet matches.

**Input parameters:**
The function takes:
- `new_item` (dict): The selected listing dictionary returned by `search_listings`, including the item's title, price, category, style tags, and platform.
- `wardrobe` (dict): A wardrobe dictionary with an `items` key containing a list of closet item dictionaries. Each item has `id`, `name`, `category`, `colors`, `style_tags`, and optional `notes`.

**What it returns:**
Returns a non-empty outfit suggestion string. The string should name specific wardrobe pieces when they exist, explain how they pair with the new item, and describe the overall vibe or silhouette.

**What happens if it fails or returns nothing:**
If the wardrobe is empty or no strong outfit can be built, return a general styling paragraph instead of an exception. If the tool still returns an empty string, the planning loop should set an error and stop before calling `create_fit_card`.

---

### Tool 3: create_fit_card

**What it does:**
Turns the chosen outfit and listing into a short shareable fit-card caption that sounds like a real outfit post. It should mention the item name, price, and platform naturally while keeping the tone casual and specific.

**Input parameters:**
The function takes:
- `outfit` (str): The outfit suggestion string returned by `suggest_outfit`, including the recommended combinations and styling notes.
- `new_item` (dict): The selected listing dictionary so the caption can reference the actual item name, price, and platform.

**What it returns:**
Returns a 2–4 sentence caption string suitable for a fit card or social post. The output should feel polished but natural, and it should vary based on the item and outfit details.

**What happens if it fails or returns nothing:**
If the outfit input is missing or blank, return a descriptive error string instead of raising an exception. The planning loop should treat that as a failure, store the message in `session["error"]`, and stop.

---

### Additional Tools (if any)

None. The agent only needs `search_listings`, `suggest_outfit`, and `create_fit_card` for this project.

---

## Planning Loop

**How does your agent decide which tool to call next?**
The loop starts by creating a fresh session and parsing the user's query into `description`, `size`, and `max_price`. It then calls `search_listings` with those values; if the returned list is empty, it sets `session["error"] = "No listings found. Try a broader description or a higher price limit."` and returns immediately. If there is at least one match, it stores `selected_item = search_results[0]`, calls `suggest_outfit(selected_item, wardrobe)`, and stops early if that returns an empty or blank string. When outfit text is present, it passes the outfit and selected item into `create_fit_card`, stores the caption in `session["fit_card"]`, and returns the completed session with `session["error"] = None`.

---

## State Management

**How does information from one tool get passed to the next?**
The session dictionary is the single source of truth for the whole interaction. The parser writes extracted filters into `session["parsed"]`, `search_listings` writes its results into `session["search_results"]`, the chosen top match goes into `session["selected_item"]`, `suggest_outfit` writes its string into `session["outfit_suggestion"]`, and `create_fit_card` writes the final caption into `session["fit_card"]`. Each step reads the values produced by the previous step directly from the same session object, so there is no hidden global state.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Set `session["error"]` to a clear message like "No listings found for that search. Try a broader style term or a higher budget." and return the session without calling any other tools. |
| suggest_outfit | Wardrobe is empty | Continue with general styling advice instead of specific wardrobe matches. If the tool still returns nothing, set `session["error"]` to "Could not generate outfit advice from the current wardrobe." and stop. |
| create_fit_card | Outfit input is missing or incomplete | Store the tool's error text in `session["error"]`, skip the final output, and return the session so the user sees the failure rather than a broken caption. |

---

## Architecture

```mermaid
flowchart TD
     U[User query] --> P[Planning loop]
     P --> S[Parse query into description, size, max_price]
     S --> T1[search_listings(description, size, max_price)]
     T1 --> SR[Session: search_results]
     SR --> D{Results empty?}
     D -- Yes --> E1[Set session.error and return early]
     D -- No --> C[Session: selected_item = search_results[0]]
     C --> T2[suggest_outfit(selected_item, wardrobe)]
     T2 --> O[Session: outfit_suggestion]
     O --> D2{Outfit empty?}
     D2 -- Yes --> E2[Set session.error and return early]
     D2 -- No --> T3[create_fit_card(outfit_suggestion, selected_item)]
     T3 --> F[Session: fit_card]
     F --> R[Return session]
     E1 --> R
     E2 --> R
     P <--> ST[Session state: query, parsed, wardrobe, search_results, selected_item, outfit_suggestion, fit_card, error]
     S --> ST
     T1 --> ST
     T2 --> ST
     T3 --> ST
```

---

## AI Tool Plan

I will use Copilot for the implementation because the codebase is small and the tool signatures are already fixed in `tools.py` and `agent.py`. For the tool implementations, I will give Copilot the Tool 1–3 sections from this file plus the data loader file, and ask it to implement each function exactly to spec; then I will verify the signatures match, that `search_listings` filters and sorts correctly, that `suggest_outfit` handles empty and non-empty wardrobes, and that `create_fit_card` returns a caption or error string without throwing.

**Milestone 3 — Individual tool implementations:**
I will give Copilot the three tool sections from `planning.md` and `utils/data_loader.py`, then ask it to implement `search_listings`, `suggest_outfit`, and `create_fit_card` in `tools.py`. I will verify the output by checking that each function accepts the exact planned parameters, returns the documented type, and handles its failure case with the expected empty list or error string.

**Milestone 4 — Planning loop and state management:**
I will give Copilot the Planning Loop, State Management, Error Handling, and Architecture sections from `planning.md` along with `agent.py`. I expect it to implement the parse → search → select → outfit → fit-card flow, keep all data in the session dict, and stop early on empty search results or failed outfit generation; I will verify this by running the happy-path example and a no-results query.

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
The agent parses the query into `description = "vintage graphic tee"`, `size = None`, and `max_price = 30`, then calls `search_listings(description, size, max_price)`.

**Step 2:**
`search_listings` returns a sorted list of matching tee listings; the agent stores that list in session state, selects the first item, and calls `suggest_outfit(selected_item, wardrobe)` so the output can use the user's baggy jeans and chunky sneakers as styling anchors.

**Step 3:**
`suggest_outfit` returns a short outfit recommendation, which the agent saves and then passes to `create_fit_card(outfit, selected_item)` to generate the final caption.

**Final output to user:**
The user sees the best matching tee, a concrete outfit suggestion that pairs it with their existing wardrobe style, and a fit-card caption they could reuse or post directly.
