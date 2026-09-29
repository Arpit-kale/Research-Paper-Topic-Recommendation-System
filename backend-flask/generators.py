"""
Deterministic, template-based text generation for the dashboard's research
tools (One-Click Summary, Auto-Generated Research Gap, Literature-Review
Paragraph). These do NOT call any external AI/LLM — they compose real text
from your actual database rows (papers, themes, key findings), so they work
100% offline and always produce the same output for the same data. That
means no API key, no cost, no chance of hallucination — the trade-off is
that the prose is templated rather than freely generated.
"""
import re

STATUS_LABELS = {"solved": "Solved", "partially_solved": "Partially Solved", "open": "Open"}

PARAGRAPH_CONNECTORS = [
    "",
    "Building on this, ",
    "In a related direction, ",
    "More recently, ",
    "Extending this line of work, ",
    "Complementing these efforts, ",
    "Around the same time, ",
]


def _decapitalize_first(text: str) -> str:
    return text[0].lower() + text[1:] if text else text


def _first_sentences(text: str, n: int = 3) -> str:
    if not text:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(sentences[:n])


def build_paper_summary(paper: dict) -> str:
    """
    One-click summary for a single paper — works for a paper already saved
    locally (has 'contribution', 'theme', 'status') or an ad-hoc result
    fetched from Discover Papers (has 'abstract', 'venue', 'authors').
    """
    title = paper.get("title") or "(untitled)"
    lines = [f"### {title}", ""]

    meta_bits = []
    authors = paper.get("authors_venue") or paper.get("authors")
    if authors:
        meta_bits.append(authors)
    venue = paper.get("venue")
    if venue and not paper.get("authors_venue"):
        meta_bits.append(venue)
    year = paper.get("year")
    if year:
        meta_bits.append(str(year))
    if meta_bits:
        lines.append(" · ".join(str(b) for b in meta_bits))
        lines.append("")

    citation_count = paper.get("citation_count")
    if citation_count is not None:
        lines.append(f"**Citations:** {citation_count}")

    theme = paper.get("theme")
    if theme:
        lines.append(f"**Theme:** {theme.get('name')}")

    status = paper.get("status")
    if status:
        lines.append(f"**Status:** {STATUS_LABELS.get(status, status)}")

    source = paper.get("source")
    if source:
        lines.append(f"**Source:** {source}")

    lines.append("")
    body = paper.get("contribution") or paper.get("abstract") or ""
    if body:
        lines.append("**Summary:** " + _first_sentences(body, 3))
    else:
        lines.append("_No abstract or contribution text is available to summarize for this paper._")

    return "\n".join(lines)


def build_research_gap(papers: list, key_findings: list) -> str:
    """
    Auto-generate a research-gap paragraph from whatever papers are
    currently saved locally — recomputes fresh each time, so adding or
    removing papers changes the result.
    """
    if not papers:
        return ("No papers are saved yet. Add papers under Research Papers or "
                "import some from Discover Papers, then generate again.")

    total = len(papers)
    by_status = {"solved": 0, "partially_solved": 0, "open": 0}
    by_theme = {}
    years = []

    for p in papers:
        by_status[p["status"]] = by_status.get(p["status"], 0) + 1
        theme_name = p.get("theme_name") or "Unassigned"
        bucket = by_theme.setdefault(theme_name, {"count": 0, "open": 0})
        bucket["count"] += 1
        if p["status"] == "open":
            bucket["open"] += 1
        if p.get("year"):
            years.append(p["year"])

    # Theme with the highest ratio of unresolved ("open") papers is the headline gap.
    gap_theme_name, gap_theme_stats = max(
        by_theme.items(),
        key=lambda kv: (kv[1]["open"] / kv[1]["count"], kv[1]["open"]),
    )

    open_challenges = [f["description"] for f in key_findings if f["category"] == "open_challenge"][:3]
    challenge_text = "; ".join(open_challenges) if open_challenges else "no open challenges have been logged yet"

    span = f"{min(years)}–{max(years)}" if years else "an unspecified period"
    pct_solved = round((by_status.get("solved", 0) / total) * 100)
    pct_open = round((by_status.get("open", 0) / total) * 100)

    return (
        f"Across the {total} papers currently saved in this review (spanning {span} "
        f"across {len(by_theme)} theme{'s' if len(by_theme) != 1 else ''}), {pct_solved}% are fully solved "
        f"and {pct_open}% remain open. Unresolved work concentrates most heavily in "
        f"**{gap_theme_name}** ({gap_theme_stats['open']} of {gap_theme_stats['count']} papers there still open). "
        f"Recurring challenges noted across the literature include: {challenge_text}. "
        f"This points to the clearest opportunity for new work: addressing "
        f"{gap_theme_name}, building on approaches that already work well elsewhere in this review."
    )


def build_literature_paragraph(theme: dict, papers: list) -> str:
    """
    Draft a literature-review paragraph for one theme, stitching its papers
    together in publication order with varied connective phrases.
    """
    if not papers:
        return f"No papers have been reviewed yet under the theme \"{theme['name']}\"."

    sentences = []
    for i, p in enumerate(papers):
        connector = PARAGRAPH_CONNECTORS[i % len(PARAGRAPH_CONNECTORS)]
        contribution = _decapitalize_first((p.get("contribution") or "").rstrip("."))
        sentences.append(f"{connector}{p['authors_venue']} ({p['year']}) {contribution}")

    open_count = sum(1 for p in papers if p["status"] == "open")
    if open_count:
        closing = (
            f" Despite these contributions, {open_count} of the {len(papers)} papers reviewed under this "
            f"theme leave open questions, suggesting that {theme['description'].rstrip('.')} "
            f"remains an active area for future work."
        )
    else:
        closing = f" Collectively, this body of work substantially addresses {theme['name']}."

    return ". ".join(sentences) + "." + closing
