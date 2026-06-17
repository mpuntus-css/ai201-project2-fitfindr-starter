"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os
import re

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()

_STOPWORDS = {
    "a",
    "an",
    "and",
    "any",
    "around",
    "be",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "like",
    "looking",
    "me",
    "my",
    "of",
    "on",
    "out",
    "please",
    "shirt",
    "style",
    "styles",
    "the",
    "to",
    "try",
    "that",
    "this",
    "with",
    "what",
    "wear",
    "would",
    "you",
}


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def _keyword_tokens(text: str) -> set[str]:
    return {token for token in _tokenize(text) if token not in _STOPWORDS}


def _listing_search_text(listing: dict) -> str:
    parts = [
        listing.get("title", ""),
        listing.get("description", ""),
        listing.get("category", ""),
        " ".join(listing.get("style_tags") or []),
        " ".join(listing.get("colors") or []),
        listing.get("brand") or "",
        listing.get("platform", ""),
    ]
    return " ".join(parts)


def _size_matches(user_size: str, listing_size: str) -> bool:
    user_size = user_size.strip().lower()
    listing_size = listing_size.strip().lower()
    if not user_size or not listing_size:
        return True

    if user_size in listing_size or listing_size in user_size:
        return True

    user_tokens = set(_tokenize(user_size))
    listing_tokens = set(_tokenize(listing_size))
    return bool(user_tokens & listing_tokens)


def _call_groq(prompt: str, *, temperature: float, system_message: str) -> str:
    client = _get_groq_client()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        temperature=temperature,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt},
        ],
    )

    content = response.choices[0].message.content if response.choices else ""
    return content.strip() if content else ""


def _rank_wardrobe_items(new_item: dict, wardrobe_items: list[dict], limit: int = 6) -> list[dict]:
    new_tokens = _keyword_tokens(_listing_search_text(new_item))
    new_tokens.update(_keyword_tokens(str(new_item.get("category", ""))))

    ranked_items: list[tuple[int, str, dict]] = []
    for item in wardrobe_items:
        item_text = " ".join(
            [
                item.get("name", ""),
                item.get("category", ""),
                " ".join(item.get("colors") or []),
                " ".join(item.get("style_tags") or []),
                item.get("notes") or "",
            ]
        )
        item_tokens = _keyword_tokens(item_text)
        score = len(new_tokens & item_tokens)
        ranked_items.append((score, item.get("name", ""), item))

    ranked_items.sort(key=lambda entry: (-entry[0], entry[1].lower()))
    return [item for _, _, item in ranked_items[:limit]]


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    listings = load_listings()
    query_tokens = _keyword_tokens(description)

    matches: list[tuple[int, float, str, dict]] = []
    for listing in listings:
        price = listing.get("price")
        if max_price is not None and price is not None and price > max_price:
            continue

        if size is not None and not _size_matches(size, str(listing.get("size", ""))):
            continue

        listing_tokens = _keyword_tokens(_listing_search_text(listing))
        score = len(query_tokens & listing_tokens)

        if score <= 0:
            continue

        matches.append((score, float(price or 0), str(listing.get("title", "")).lower(), listing))

    matches.sort(key=lambda entry: (-entry[0], entry[1], entry[2]))
    return [listing for _, _, _, listing in matches]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    wardrobe_items = (wardrobe or {}).get("items") or []
    item_name = new_item.get("title") or new_item.get("name") or "the item"

    if wardrobe_items:
        relevant_items = _rank_wardrobe_items(new_item, wardrobe_items)
        wardrobe_summary = "\n".join(
            f"- {piece.get('name', 'Unnamed item')} ({piece.get('category', 'unknown')}; colors: {', '.join(piece.get('colors') or ['none'])}; tags: {', '.join(piece.get('style_tags') or ['none'])})"
            for piece in relevant_items
        )
        prompt = (
            f"New thrifted item: {item_name}\n"
            f"Price: ${new_item.get('price', 'unknown')}\n"
            f"Category: {new_item.get('category', 'unknown')}\n"
            f"Style tags: {', '.join(new_item.get('style_tags') or []) or 'none'}\n\n"
            f"Wardrobe items:\n{wardrobe_summary}\n\n"
            "Write 1-2 outfit ideas using specific wardrobe pieces by name. "
            "Keep it practical, mention silhouette and vibe, and avoid generic filler."
        )
        fallback = (
            f"Try pairing {item_name} with your best matching wardrobe basics, then finish with a shoe or outerwear piece that echoes its vibe."
        )
        system_message = "You are a concise fashion stylist who suggests realistic secondhand outfits."
    else:
        prompt = (
            f"New thrifted item: {item_name}\n"
            f"Price: ${new_item.get('price', 'unknown')}\n"
            f"Category: {new_item.get('category', 'unknown')}\n"
            f"Style tags: {', '.join(new_item.get('style_tags') or []) or 'none'}\n\n"
            "The user has no wardrobe items saved. Write general styling advice for this item, including what kinds of bottoms, shoes, or layers would work best and what vibe it gives."
        )
        fallback = (
            f"{item_name} works best with simple basics, a supportive bottom silhouette, and shoes that match its style tags."
        )
        system_message = "You are a concise fashion stylist who gives practical styling advice."

    try:
        response = _call_groq(prompt, temperature=0.7, system_message=system_message)
        return response or fallback
    except Exception:
        return fallback


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    if not outfit or not outfit.strip():
        return "Unable to create a fit card because the outfit suggestion is missing."

    item_name = new_item.get("title") or new_item.get("name") or "the item"
    prompt = (
        f"Item: {item_name}\n"
        f"Price: ${new_item.get('price', 'unknown')}\n"
        f"Platform: {new_item.get('platform', 'unknown')}\n"
        f"Outfit: {outfit.strip()}\n\n"
        "Write a 2-4 sentence caption for a fit card. It should sound casual and authentic, mention the item name, price, and platform naturally, and reflect the outfit vibe without sounding like a product listing."
    )

    fallback = (
        f"{item_name} is such a good find at ${new_item.get('price', 'unknown')} from {new_item.get('platform', 'unknown')}. "
        f"The outfit feels {outfit.strip()} and easy to wear, with a clean secondhand vibe that still looks put together."
    )

    try:
        response = _call_groq(
            prompt,
            temperature=1.0,
            system_message="You write short, natural fashion captions for thrifted outfit posts.",
        )
        return response or fallback
    except Exception:
        return fallback
