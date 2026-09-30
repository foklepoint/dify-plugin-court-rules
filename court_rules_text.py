"""Plain-text digests of Court Rules API responses.

Each tool sends a short digest for the model to read and the full API response as JSON for
workflows. Every function tolerates missing fields, so an unexpected response never raises.
"""

from typing import Any

DIGEST_ROW_LIMIT = 15


def shorten(text: Any, limit: int = 300) -> str:
    """Collapse whitespace and cut long text."""
    collapsed = " ".join(str(text or "").split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3].rstrip() + "..."


def as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def more_note(shown: int, total: int, hint: str) -> str:
    if total <= shown:
        return ""
    return "... " + str(total - shown) + " more. " + hint


def citation_text(citation: Any) -> str:
    """Turn the citation_source object of a rule into 'page 3, section II.A'."""
    citation = as_dict(citation)
    pieces = []
    if citation.get("page") is not None:
        pieces.append("page " + str(citation["page"]))
    if citation.get("section"):
        pieces.append("section " + str(citation["section"]))
    if citation.get("paragraph"):
        pieces.append("paragraph " + str(citation["paragraph"]))
    return ", ".join(pieces)


def extracted_rule_line(rule: Any) -> str:
    """One line for a rule from /extracted-rules or from the rules of a state court."""
    rule = as_dict(rule)
    content = as_dict(rule.get("content"))
    tags = [str(rule.get("logic_type") or "rule")]
    if content.get("visual_severity"):
        tags.append(str(content["visual_severity"]))
    summary = shorten(content.get("summary") or content.get("source_text"))
    where = [str(rule.get("judge_slug") or ""), str(rule.get("district_id") or "")]
    location = ", ".join(piece for piece in where if piece)
    citation = citation_text(content.get("citation_source"))
    if citation != "":
        location = location + "; " + citation
    line = "- [" + ", ".join(tags) + "] " + summary + " (" + location + ")"
    if rule.get("source_url"):
        line = line + " " + str(rule["source_url"])
    return line


def court_line(court: Any) -> str:
    court = as_dict(court)
    place = ", ".join(str(part) for part in (court.get("circuit"), court.get("state")) if part)
    if place == "":
        place = "no circuit or state"
    return (
        "- "
        + str(court.get("district_id") or "")
        + ": "
        + str(court.get("name") or "")
        + " ("
        + place
        + "), "
        + str(court.get("status") or "unknown status")
        + ", "
        + str(court.get("judges_mapped", 0))
        + " judges mapped"
    )
