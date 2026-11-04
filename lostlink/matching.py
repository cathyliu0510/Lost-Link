"""
Matching logic for Lost Link.

Two rankers live here so the evaluation compares them on exactly the same
visible fields:

* `rank_alias`    – our matcher: vocabulary normalization (flask -> bottle,
                    navy -> blue, "Hayden" -> library zone), date window,
                    explicit `unknown` handling, and human-readable reasons.
* `rank_baseline` – the simple rule from the HW5 plan: exact category string
                    + raw keyword overlap.

Neither ranker ever sees `private_detail`. Callers pass only the public
fields (see PUBLIC_FIELDS) so a leak is impossible by construction.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Iterable

# Fields a ranker is allowed to read. private_detail is deliberately absent.
PUBLIC_FIELDS = ("report_id", "kind", "category", "color", "brand",
                 "location", "date", "description")

# ---------------------------------------------------------------------------
# Controlled vocabularies (small, hand-written for the one-campus demo)
# ---------------------------------------------------------------------------
# Each raw word/phrase maps to a canonical value. Multi-word keys are matched
# before single words (see _canon).
CATEGORY_ALIASES = {
    "bottle": ["bottle", "water bottle", "flask", "thermos", "tumbler",
               "hydro flask", "hydroflask", "nalgene", "canteen"],
    "phone": ["phone", "iphone", "smartphone", "cell phone", "cellphone",
              "android", "pixel"],
    "earbuds": ["earbuds", "airpods", "earphones", "headphones", "buds"],
    "keys": ["keys", "key", "keychain", "key ring", "keyring"],
    "wallet": ["wallet", "card holder", "cardholder", "purse"],
    "id_card": ["id", "id card", "student id", "badge", "mit id"],
    "umbrella": ["umbrella", "brolly"],
    "laptop": ["laptop", "macbook", "notebook computer", "chromebook"],
    "charger": ["charger", "power adapter", "charging cable", "usb-c cable",
                "power brick"],
    "jacket": ["jacket", "coat", "hoodie", "sweatshirt", "fleece", "parka"],
    "backpack": ["backpack", "bag", "rucksack", "book bag", "tote"],
    "glasses": ["glasses", "spectacles", "eyeglasses", "sunglasses"],
    "calculator": ["calculator", "ti-84", "graphing calculator"],
    "notebook": ["notebook", "journal", "notepad", "moleskine"],
}

COLOR_ALIASES = {
    "blue": ["blue", "navy", "navy blue", "cobalt", "royal blue", "light blue",
             "sky blue", "teal", "turquoise", "dark blue"],
    "black": ["black", "matte black", "charcoal", "jet black"],
    "white": ["white", "ivory", "cream", "off-white"],
    "gray": ["gray", "grey", "silver", "space gray", "graphite"],
    "red": ["red", "maroon", "burgundy", "crimson", "cardinal"],
    "green": ["green", "olive", "sage", "forest green", "mint"],
    "pink": ["pink", "rose", "magenta", "blush"],
    "yellow": ["yellow", "gold", "mustard"],
    "brown": ["brown", "tan", "beige", "khaki", "camel"],
    "purple": ["purple", "violet", "lavender", "lilac"],
    "orange": ["orange", "coral", "rust"],
}

# Campus "zones" so that "Hayden", "the library" and "Hayden 2nd floor" agree.
LOCATION_ALIASES = {
    "library": ["library", "hayden", "hayden library", "barker", "barker library",
                "rotch", "reading room", "stacks"],
    "student_center": ["student center", "stud", "stratton", "lobdell",
                       "w20", "coffeehouse"],
    "stata": ["stata", "stata center", "building 32", "32-123", "r&d pub"],
    "infinite": ["infinite corridor", "infinite", "lobby 7", "lobby 10",
                 "building 10", "killian"],
    "gym": ["gym", "z center", "zesiger", "pool", "athletics"],
    "media_lab": ["media lab", "e14", "e15", "building e14"],
    "dorm": ["dorm", "dormitory", "residence hall", "simmons", "baker",
             "maseeh", "next house"],
    "dining": ["dining hall", "dining", "cafeteria", "maseeh dining"],
    "kendall": ["kendall", "kendall square", "kendall t", "red line"],
}

STOPWORDS = {"a", "an", "the", "my", "i", "it", "is", "was", "on", "in", "at",
             "of", "with", "and", "or", "near", "around", "to", "for", "has",
             "have", "lost", "found", "left", "some", "small", "this", "that",
             "floor", "maybe", "probably", "think", "yesterday", "today"}


def _build_lookup(aliases: dict[str, list[str]]) -> list[tuple[str, str]]:
    """Flatten an alias dict to (phrase, canonical) pairs, longest phrase first."""
    pairs = [(p.lower(), canon) for canon, ps in aliases.items() for p in ps]
    return sorted(pairs, key=lambda x: -len(x[0]))


_CAT = _build_lookup(CATEGORY_ALIASES)
_COL = _build_lookup(COLOR_ALIASES)
_LOC = _build_lookup(LOCATION_ALIASES)


def _canon(text: str | None, lookup: list[tuple[str, str]]) -> str | None:
    """Return the canonical value of the first (longest) alias found in text."""
    if not text:
        return None
    t = f" {text.lower()} "
    for phrase, canon in lookup:
        # word-boundary match so "id" does not fire inside "inside"
        if re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", t):
            return canon
    return None


def _tokens(text: str | None) -> set[str]:
    """Lower-case content words, with colour/category aliases collapsed."""
    if not text:
        return set()
    out = set()
    for w in re.findall(r"[a-z0-9\-]+", text.lower()):
        if w in STOPWORDS or len(w) < 2:
            continue
        out.add(_canon(w, _CAT) or _canon(w, _COL) or w)
    return out


def normalize(report: dict) -> dict:
    """
    Turn a report's public fields into canonical values.
    Category/colour fall back to the free-text description when the field
    itself is empty, because agents often put everything in one sentence.
    """
    desc = report.get("description") or ""
    return {
        "category": _canon(report.get("category"), _CAT) or _canon(desc, _CAT),
        "color": _canon(report.get("color"), _COL) or _canon(desc, _COL),
        "location": _canon(report.get("location"), _LOC) or _canon(desc, _LOC),
        "brand": (report.get("brand") or "").strip().lower() or None,
        "date": report.get("date") or None,
        "tokens": _tokens(" ".join(filter(None, [desc, report.get("brand")]))),
    }


def _days_apart(a: str | None, b: str | None) -> int | None:
    """Absolute day difference between two ISO dates, or None if either is unknown."""
    if not a or not b:
        return None
    try:
        return abs((date.fromisoformat(a) - date.fromisoformat(b)).days)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Our ranker
# ---------------------------------------------------------------------------
# Weights sum to 1.0. Unknown fields get half credit: "unknown" is neither
# evidence for nor against a match (a design point from the HW5 reviewers).
W = {"category": 0.40, "color": 0.20, "location": 0.20, "date": 0.10,
     "keywords": 0.10}
MIN_SCORE = 0.45  # below this a candidate is not worth an agent's attention


def score_pair(lost: dict, found: dict) -> dict:
    """Score one lost/found pair; return score, reasons, unknown and conflicts."""
    L, F = normalize(lost), normalize(found)
    score, reasons, unknown, conflicts = 0.0, [], [], []

    # --- categorical fields: match / unknown / conflict ---------------------
    for field in ("category", "color", "location"):
        a, b = L[field], F[field]
        if a is None or b is None:
            score += W[field] * 0.5
            unknown.append(field)
        elif a == b:
            score += W[field]
            reasons.append(f"{field} matches after normalization ({a})")
        else:
            conflicts.append(f"{field}: lost={a}, found={b}")

    # --- date: full credit within 2 days, partial within 7 ------------------
    d = _days_apart(L["date"], F["date"])
    if d is None:
        score += W["date"] * 0.5
        unknown.append("date")
    elif d <= 2:
        score += W["date"]
        reasons.append(f"dates within {d} day(s)")
    elif d <= 7:
        score += W["date"] * 0.5
        reasons.append(f"dates {d} days apart")
    else:
        conflicts.append(f"date: {d} days apart")

    # --- free-text overlap (Jaccard on normalized tokens) -------------------
    if L["tokens"] and F["tokens"]:
        jac = len(L["tokens"] & F["tokens"]) / len(L["tokens"] | F["tokens"])
        score += W["keywords"] * jac
        shared = sorted(L["tokens"] & F["tokens"])[:4]
        if shared:
            reasons.append("shared description words: " + ", ".join(shared))

    # A category conflict is almost always a different object: hard penalty.
    if any(c.startswith("category") for c in conflicts):
        score *= 0.3

    return {"score": round(score, 3), "reasons": reasons,
            "unknown": unknown, "conflicts": conflicts}


def rank_alias(lost: dict, founds: Iterable[dict], limit: int = 3) -> list[dict]:
    """Rank candidates only with positive evidence of a shared item type.

    HW7 tuning found that half-credit for an unknown category could surface
    unrelated items. Abstain when type evidence is missing or unsupported;
    category words in the description still work through normalize(). This
    conservative policy trades recall on unseen types for fewer suggestions.
    """
    category = normalize(lost)["category"]
    if category is None:
        return []
    scored = []
    for f in founds:
        if normalize(f)["category"] != category:
            continue
        s = score_pair(lost, f)
        if s["score"] >= MIN_SCORE:
            scored.append({"report_id": f["report_id"], **s})
    scored.sort(key=lambda x: (-x["score"], x["report_id"]))
    return scored[:limit]


# ---------------------------------------------------------------------------
# Baseline ranker (HW5 comparison): exact category + raw keyword overlap
# ---------------------------------------------------------------------------
def rank_baseline(lost: dict, founds: Iterable[dict], limit: int = 3) -> list[dict]:
    """Keep found reports whose raw category string equals the lost one
    (or all, if the lost category is blank), ranked by raw word overlap."""
    def raw(r):
        txt = " ".join(filter(None, [r.get("category"), r.get("color"),
                                     r.get("location"), r.get("description")]))
        return {w for w in re.findall(r"[a-z0-9\-]+", txt.lower())
                if w not in STOPWORDS}

    lc = (lost.get("category") or "").strip().lower()
    lw = raw(lost)
    out = []
    for f in founds:
        if lc and (f.get("category") or "").strip().lower() != lc:
            continue
        overlap = len(lw & raw(f))
        if overlap:
            out.append({"report_id": f["report_id"], "score": overlap})
    out.sort(key=lambda x: (-x["score"], x["report_id"]))
    return out[:limit]


def missing_fields(lost: dict) -> list[str]:
    """Public fields the *caller* could add to sharpen the search.
    Computed only from the caller's own report, so it can never hint at the
    holder's private verification answer."""
    return [f for f in ("category", "color", "brand", "location", "date")
            if not lost.get(f)]
