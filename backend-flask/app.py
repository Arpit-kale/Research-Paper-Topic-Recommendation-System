"""
Research Paper & Topic Recommendation System — Flask API

Run with:  python app.py
Serves JSON at http://127.0.0.1:5000/api/...

No external services required — SQLite database file is created and seeded
automatically on first run (see database.py / database/schema.sql).
"""
import re
import sqlite3
import time
import uuid
from datetime import datetime

import requests
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from database import ensure_database, get_connection, row_to_dict, rows_to_list
from generators import build_paper_summary, build_research_gap, build_literature_paragraph

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["JSON_SORT_KEYS"] = False
CORS(app)  # harmless to leave on; not needed now that the frontend is same-origin

# Create + seed the SQLite database on import (not just when run directly) —
# this is what makes it work under a real WSGI server like PythonAnywhere,
# gunicorn, etc., which import `app` as a module rather than executing
# `python app.py`. ensure_database() is a no-op if the .db file already exists.
ensure_database()

VALID_STATUSES = {"solved", "partially_solved", "open"}
VALID_CATEGORIES = {"works_well", "open_challenge"}


# ---------------------------------------------------------------------------
# Frontend — served directly by Flask from templates/index.html
# ---------------------------------------------------------------------------
@app.get("/")
def dashboard_page():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    text = re.sub(r"[\s_-]+", "-", text)
    return text or f"theme-{uuid.uuid4().hex[:8]}"


def error(message: str, code: int = 422):
    return jsonify({"message": message}), code


def require_fields(data: dict, fields: list[str]):
    """Returns an error response tuple if any field is missing/empty, else None."""
    missing = [f for f in fields if data.get(f) in (None, "")]
    if missing:
        pretty = ", ".join(f.replace("_", " ") for f in missing)
        return error(f"{pretty.capitalize()} {'is' if len(missing) == 1 else 'are'} required")
    return None


@app.errorhandler(sqlite3.Error)
def handle_db_error(e):
    return jsonify({"message": "Database error", "detail": str(e)}), 500


@app.errorhandler(404)
def handle_404(e):
    return jsonify({"message": "Not found"}), 404


# ---------------------------------------------------------------------------
# Dashboard summary
# ---------------------------------------------------------------------------
@app.get("/api/dashboard/summary")
def dashboard_summary():
    conn = get_connection()

    total_papers = conn.execute("SELECT COUNT(*) FROM research_papers").fetchone()[0]
    total_themes = conn.execute("SELECT COUNT(*) FROM themes").fetchone()[0]

    themes = rows_to_list(conn.execute(
        """SELECT t.*, (SELECT COUNT(*) FROM research_papers rp WHERE rp.theme_id = t.id) AS papers_count
           FROM themes t ORDER BY t.theme_no"""
    ).fetchall())

    theme_distribution = []
    for t in themes:
        pct = round((t["papers_count"] / total_papers) * 100, 1) if total_papers else 0
        theme_distribution.append({
            "id": t["id"], "name": t["name"], "count": t["papers_count"],
            "percent": pct, "color": t["color"], "icon": t["icon"],
        })

    top_themes = sorted(theme_distribution, key=lambda t: t["count"], reverse=True)[:5]

    works_well_count = conn.execute(
        "SELECT COUNT(*) FROM key_findings WHERE category = 'works_well'").fetchone()[0]
    open_challenge_count = conn.execute(
        "SELECT COUNT(*) FROM key_findings WHERE category = 'open_challenge'").fetchone()[0]
    future_work_count = conn.execute("SELECT COUNT(*) FROM future_works").fetchone()[0]

    year_min = conn.execute("SELECT MIN(year) FROM research_papers").fetchone()[0]
    year_max = conn.execute("SELECT MAX(year) FROM research_papers").fetchone()[0]

    year_rows = conn.execute(
        "SELECT year, COUNT(*) AS count FROM research_papers GROUP BY year ORDER BY year"
    ).fetchall()
    papers_by_year = [{"year": r["year"], "count": r["count"]} for r in year_rows]

    citations_checked = conn.execute(
        "SELECT COUNT(*) FROM research_papers WHERE citation_count IS NOT NULL"
    ).fetchone()[0]

    literature_table = []
    for t in themes:
        key_ref = conn.execute(
            "SELECT title FROM research_papers WHERE theme_id = ? ORDER BY year DESC LIMIT 1",
            (t["id"],),
        ).fetchone()
        solved = conn.execute(
            "SELECT COUNT(*) FROM research_papers WHERE theme_id = ? AND status = 'solved'",
            (t["id"],),
        ).fetchone()[0]
        opened = conn.execute(
            "SELECT COUNT(*) FROM research_papers WHERE theme_id = ? AND status = 'open'",
            (t["id"],),
        ).fetchone()[0]
        literature_table.append({
            "theme": t["name"], "papers_reviewed": t["papers_count"],
            "key_reference": key_ref["title"] if key_ref else None,
            "solved": solved, "open": opened,
        })

    meta = row_to_dict(conn.execute("SELECT * FROM report_meta LIMIT 1").fetchone())
    research_gap = row_to_dict(conn.execute("SELECT * FROM research_gap LIMIT 1").fetchone())
    conn.close()

    return jsonify({
        "meta": meta,
        "stats": {
            "total_papers": total_papers,
            "publication_span": f"{year_min} - {year_max}",
            "total_themes": total_themes,
            "works_well_count": works_well_count,
            "open_challenge_count": open_challenge_count,
            "future_work_count": future_work_count,
            "citations_checked": citations_checked,
        },
        "theme_distribution": theme_distribution,
        "top_themes": top_themes,
        "papers_by_year": papers_by_year,
        "literature_table": literature_table,
        "research_gap": research_gap,
    })


# ---------------------------------------------------------------------------
# Themes
# ---------------------------------------------------------------------------
@app.get("/api/themes")
def list_themes():
    conn = get_connection()
    rows = rows_to_list(conn.execute(
        """SELECT t.*, (SELECT COUNT(*) FROM research_papers rp WHERE rp.theme_id = t.id) AS papers_count
           FROM themes t ORDER BY t.theme_no"""
    ).fetchall())
    conn.close()
    return jsonify({"data": rows})


@app.get("/api/themes/<int:theme_id>")
def get_theme(theme_id):
    conn = get_connection()
    theme = row_to_dict(conn.execute("SELECT * FROM themes WHERE id = ?", (theme_id,)).fetchone())
    if not theme:
        conn.close()
        return error("Theme not found", 404)
    theme["papers"] = rows_to_list(conn.execute(
        "SELECT * FROM research_papers WHERE theme_id = ? ORDER BY year DESC", (theme_id,)
    ).fetchall())
    conn.close()
    return jsonify({"data": theme})


@app.post("/api/themes")
def create_theme():
    data = request.get_json(force=True, silent=True) or {}
    err = require_fields(data, ["theme_no", "name", "description"])
    if err:
        return err

    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO themes (theme_no, name, slug, description, color, icon) VALUES (?, ?, ?, ?, ?, ?)",
        (data["theme_no"], data["name"], slugify(data["name"]), data["description"],
         data.get("color", "#4F6EF7"), data.get("icon", "📄")),
    )
    conn.commit()
    new_id = cur.lastrowid
    theme = row_to_dict(conn.execute("SELECT * FROM themes WHERE id = ?", (new_id,)).fetchone())
    conn.close()
    return jsonify({"data": theme, "message": "Theme created successfully"}), 201


@app.put("/api/themes/<int:theme_id>")
def update_theme(theme_id):
    data = request.get_json(force=True, silent=True) or {}
    conn = get_connection()
    existing = conn.execute("SELECT id FROM themes WHERE id = ?", (theme_id,)).fetchone()
    if not existing:
        conn.close()
        return error("Theme not found", 404)

    fields, values = [], []
    for key in ("theme_no", "name", "description", "color", "icon"):
        if key in data:
            fields.append(f"{key} = ?")
            values.append(data[key])
    if "name" in data:
        fields.append("slug = ?")
        values.append(slugify(data["name"]))
    if not fields:
        conn.close()
        return error("Nothing to update")

    values.append(theme_id)
    conn.execute(f"UPDATE themes SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    theme = row_to_dict(conn.execute("SELECT * FROM themes WHERE id = ?", (theme_id,)).fetchone())
    conn.close()
    return jsonify({"data": theme, "message": "Theme updated successfully"})


@app.delete("/api/themes/<int:theme_id>")
def delete_theme(theme_id):
    conn = get_connection()
    conn.execute("DELETE FROM themes WHERE id = ?", (theme_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Theme deleted successfully"})


# ---------------------------------------------------------------------------
# Research papers
# ---------------------------------------------------------------------------
def fetch_paper(conn, paper_id):
    row = conn.execute(
        """SELECT rp.*, t.name AS theme_name, t.color AS theme_color
           FROM research_papers rp JOIN themes t ON t.id = rp.theme_id
           WHERE rp.id = ?""",
        (paper_id,),
    ).fetchone()
    return format_paper(row) if row else None


def format_paper(row):
    d = dict(row)
    theme = None
    if "theme_name" in d:
        theme = {"id": d["theme_id"], "name": d.pop("theme_name"), "color": d.pop("theme_color")}
    d["theme"] = theme
    return d


@app.get("/api/papers")
def list_papers():
    conn = get_connection()
    where, params = [], []

    theme_id = request.args.get("theme_id")
    status = request.args.get("status")
    search = request.args.get("search")

    if theme_id:
        where.append("rp.theme_id = ?")
        params.append(theme_id)
    if status:
        where.append("rp.status = ?")
        params.append(status)
    if search:
        term = f"%{search}%"
        where.append("(rp.title LIKE ? OR rp.authors_venue LIKE ? OR rp.contribution LIKE ?)")
        params += [term, term, term]

    sql = """SELECT rp.*, t.name AS theme_name, t.color AS theme_color
             FROM research_papers rp JOIN themes t ON t.id = rp.theme_id"""
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY rp.year DESC"

    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return jsonify({"data": [format_paper(r) for r in rows]})


@app.get("/api/papers/<int:paper_id>")
def get_paper(paper_id):
    conn = get_connection()
    paper = fetch_paper(conn, paper_id)
    conn.close()
    if not paper:
        return error("Paper not found", 404)
    return jsonify({"data": paper})


@app.post("/api/papers")
def create_paper():
    data = request.get_json(force=True, silent=True) or {}
    err = require_fields(data, ["theme_id", "title", "authors_venue", "year", "contribution", "status"])
    if err:
        return err
    if data["status"] not in VALID_STATUSES:
        return error(f"Status must be one of: {', '.join(VALID_STATUSES)}")

    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO research_papers (theme_id, title, authors_venue, year, contribution, status)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (data["theme_id"], data["title"], data["authors_venue"], data["year"],
         data["contribution"], data["status"]),
    )
    conn.commit()
    paper = fetch_paper(conn, cur.lastrowid)
    conn.close()
    return jsonify({"data": paper, "message": "Paper added successfully"}), 201


@app.put("/api/papers/<int:paper_id>")
def update_paper(paper_id):
    data = request.get_json(force=True, silent=True) or {}
    if "status" in data and data["status"] not in VALID_STATUSES:
        return error(f"Status must be one of: {', '.join(VALID_STATUSES)}")

    conn = get_connection()
    existing = conn.execute("SELECT id FROM research_papers WHERE id = ?", (paper_id,)).fetchone()
    if not existing:
        conn.close()
        return error("Paper not found", 404)

    fields, values = [], []
    for key in ("theme_id", "title", "authors_venue", "year", "contribution", "status"):
        if key in data:
            fields.append(f"{key} = ?")
            values.append(data[key])
    if not fields:
        conn.close()
        return error("Nothing to update")

    values.append(paper_id)
    conn.execute(f"UPDATE research_papers SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    paper = fetch_paper(conn, paper_id)
    conn.close()
    return jsonify({"data": paper, "message": "Paper updated successfully"})


@app.delete("/api/papers/<int:paper_id>")
def delete_paper(paper_id):
    conn = get_connection()
    conn.execute("DELETE FROM research_papers WHERE id = ?", (paper_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Paper deleted successfully"})


# ---------------------------------------------------------------------------
# Key findings
# ---------------------------------------------------------------------------
@app.get("/api/key-findings")
def list_findings():
    conn = get_connection()
    sql = "SELECT * FROM key_findings"
    params = []
    category = request.args.get("category")
    if category:
        sql += " WHERE category = ?"
        params.append(category)
    sql += " ORDER BY category, sort_order"
    rows = rows_to_list(conn.execute(sql, params).fetchall())
    conn.close()
    return jsonify({"data": rows})


@app.post("/api/key-findings")
def create_finding():
    data = request.get_json(force=True, silent=True) or {}
    err = require_fields(data, ["category", "description"])
    if err:
        return err
    if data["category"] not in VALID_CATEGORIES:
        return error(f"Category must be one of: {', '.join(VALID_CATEGORIES)}")

    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO key_findings (category, description, sort_order) VALUES (?, ?, ?)",
        (data["category"], data["description"], data.get("sort_order", 0)),
    )
    conn.commit()
    finding = row_to_dict(conn.execute("SELECT * FROM key_findings WHERE id = ?", (cur.lastrowid,)).fetchone())
    conn.close()
    return jsonify({"data": finding, "message": "Key finding added successfully"}), 201


@app.put("/api/key-findings/<int:finding_id>")
def update_finding(finding_id):
    data = request.get_json(force=True, silent=True) or {}
    conn = get_connection()
    existing = conn.execute("SELECT id FROM key_findings WHERE id = ?", (finding_id,)).fetchone()
    if not existing:
        conn.close()
        return error("Key finding not found", 404)

    fields, values = [], []
    for key in ("category", "description", "sort_order"):
        if key in data:
            fields.append(f"{key} = ?")
            values.append(data[key])
    if not fields:
        conn.close()
        return error("Nothing to update")

    values.append(finding_id)
    conn.execute(f"UPDATE key_findings SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    finding = row_to_dict(conn.execute("SELECT * FROM key_findings WHERE id = ?", (finding_id,)).fetchone())
    conn.close()
    return jsonify({"data": finding, "message": "Key finding updated successfully"})


@app.delete("/api/key-findings/<int:finding_id>")
def delete_finding(finding_id):
    conn = get_connection()
    conn.execute("DELETE FROM key_findings WHERE id = ?", (finding_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Key finding deleted successfully"})


# ---------------------------------------------------------------------------
# Future work
# ---------------------------------------------------------------------------
@app.get("/api/future-work")
def list_future_work():
    conn = get_connection()
    rows = rows_to_list(conn.execute("SELECT * FROM future_works ORDER BY sort_order").fetchall())
    conn.close()
    return jsonify({"data": rows})


@app.post("/api/future-work")
def create_future_work():
    data = request.get_json(force=True, silent=True) or {}
    err = require_fields(data, ["title", "description"])
    if err:
        return err

    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO future_works (title, description, sort_order) VALUES (?, ?, ?)",
        (data["title"], data["description"], data.get("sort_order", 0)),
    )
    conn.commit()
    item = row_to_dict(conn.execute("SELECT * FROM future_works WHERE id = ?", (cur.lastrowid,)).fetchone())
    conn.close()
    return jsonify({"data": item, "message": "Recommendation added successfully"}), 201


@app.put("/api/future-work/<int:item_id>")
def update_future_work(item_id):
    data = request.get_json(force=True, silent=True) or {}
    conn = get_connection()
    existing = conn.execute("SELECT id FROM future_works WHERE id = ?", (item_id,)).fetchone()
    if not existing:
        conn.close()
        return error("Recommendation not found", 404)

    fields, values = [], []
    for key in ("title", "description", "sort_order"):
        if key in data:
            fields.append(f"{key} = ?")
            values.append(data[key])
    if not fields:
        conn.close()
        return error("Nothing to update")

    values.append(item_id)
    conn.execute(f"UPDATE future_works SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    item = row_to_dict(conn.execute("SELECT * FROM future_works WHERE id = ?", (item_id,)).fetchone())
    conn.close()
    return jsonify({"data": item, "message": "Recommendation updated successfully"})


@app.delete("/api/future-work/<int:item_id>")
def delete_future_work(item_id):
    conn = get_connection()
    conn.execute("DELETE FROM future_works WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Recommendation deleted successfully"})


# ---------------------------------------------------------------------------
# Research gap (single record)
# ---------------------------------------------------------------------------
@app.get("/api/research-gap")
def get_research_gap():
    conn = get_connection()
    row = row_to_dict(conn.execute("SELECT * FROM research_gap LIMIT 1").fetchone())
    conn.close()
    if not row:
        return error("Research gap not found", 404)
    return jsonify({"data": row})


@app.put("/api/research-gap")
def update_research_gap():
    data = request.get_json(force=True, silent=True) or {}
    err = require_fields(data, ["summary", "gap_statement", "closing_statement"])
    if err:
        return err

    conn = get_connection()
    conn.execute(
        "UPDATE research_gap SET summary = ?, gap_statement = ?, closing_statement = ? WHERE id = 1",
        (data["summary"], data["gap_statement"], data["closing_statement"]),
    )
    conn.commit()
    row = row_to_dict(conn.execute("SELECT * FROM research_gap LIMIT 1").fetchone())
    conn.close()
    return jsonify({"data": row, "message": "Research gap updated successfully"})


# ---------------------------------------------------------------------------
# Report meta / Settings (single record)
# ---------------------------------------------------------------------------
@app.get("/api/report-meta")
def get_report_meta():
    conn = get_connection()
    row = row_to_dict(conn.execute("SELECT * FROM report_meta LIMIT 1").fetchone())
    conn.close()
    if not row:
        return error("Report meta not found", 404)
    return jsonify({"data": row})


@app.put("/api/report-meta")
def update_report_meta():
    data = request.get_json(force=True, silent=True) or {}
    err = require_fields(
        data, ["title", "subtitle", "author_name", "author_class", "roll_no", "subject", "review_period"]
    )
    if err:
        return err

    conn = get_connection()
    conn.execute(
        """UPDATE report_meta SET title = ?, subtitle = ?, author_name = ?, author_class = ?,
           roll_no = ?, subject = ?, review_period = ? WHERE id = 1""",
        (data["title"], data["subtitle"], data["author_name"], data["author_class"],
         data["roll_no"], data["subject"], data["review_period"]),
    )
    conn.commit()
    row = row_to_dict(conn.execute("SELECT * FROM report_meta LIMIT 1").fetchone())
    conn.close()
    return jsonify({"data": row, "message": "Settings updated successfully"})


# ---------------------------------------------------------------------------
# Live paper search — real-time data from real external APIs.
# Semantic Scholar first (richer: abstracts, precise citation counts, open-
# access PDFs), automatically falling back to CrossRef if Semantic Scholar
# is unavailable or rate-limited. All three are free, public, and need no
# API key: Semantic Scholar -> CrossRef -> OpenAlex, in that order.
# ---------------------------------------------------------------------------
SEMANTIC_SCHOLAR_SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
SEMANTIC_SCHOLAR_MATCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search/match"
CROSSREF_URL = "https://api.crossref.org/works"
OPENALEX_URL = "https://api.openalex.org/works"

_search_cache: dict[str, tuple[float, list, str]] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes — avoids re-hitting external APIs for repeat searches


def _format_crossref_item(item: dict) -> dict:
    authors = item.get("author", [])
    author_names = ", ".join(
        f"{a.get('given', '')} {a.get('family', '')}".strip()
        for a in authors
        if a.get("family")
    ) or "Unknown authors"

    year = None
    for date_field in ("published-print", "published-online", "published", "issued"):
        parts = item.get(date_field, {}).get("date-parts")
        if parts and parts[0] and parts[0][0]:
            year = parts[0][0]
            break

    titles = item.get("title") or []
    venues = item.get("container-title") or []

    return {
        "title": titles[0] if titles else "(untitled)",
        "authors": author_names,
        "year": year,
        "venue": venues[0] if venues else item.get("publisher", ""),
        "doi": item.get("DOI", ""),
        "url": item.get("URL", ""),
        "citation_count": item.get("is-referenced-by-count", 0),
        "abstract": None,
        "pdf_url": None,
        "type": item.get("type", ""),
        "source": "CrossRef",
    }


def _format_semantic_scholar_item(item: dict) -> dict:
    authors = item.get("authors") or []
    author_names = ", ".join(a.get("name", "") for a in authors if a.get("name")) or "Unknown authors"
    abstract = item.get("abstract")
    external_ids = item.get("externalIds") or {}
    open_pdf = item.get("openAccessPdf") or {}

    return {
        "title": item.get("title") or "(untitled)",
        "authors": author_names,
        "year": item.get("year"),
        "venue": item.get("venue") or "",
        "doi": external_ids.get("DOI", ""),
        "url": item.get("url") or (open_pdf.get("url") if open_pdf else ""),
        "citation_count": item.get("citationCount", 0),
        "abstract": (abstract[:280] + "…") if abstract and len(abstract) > 280 else abstract,
        "pdf_url": open_pdf.get("url") if open_pdf else None,
        "type": ", ".join(item.get("publicationTypes") or []) or "",
        "source": "Semantic Scholar",
    }


def _reconstruct_openalex_abstract(inverted_index) -> str | None:
    """OpenAlex stores abstracts as {word: [positions]} to save space; rebuild plain text."""
    if not inverted_index:
        return None
    positions = {}
    for word, idxs in inverted_index.items():
        for i in idxs:
            positions[i] = word
    if not positions:
        return None
    max_pos = max(positions.keys())
    return " ".join(positions.get(i, "") for i in range(max_pos + 1))


def _format_openalex_item(item: dict) -> dict:
    authorships = item.get("authorships") or []
    author_names = ", ".join(
        a.get("author", {}).get("display_name", "") for a in authorships if a.get("author")
    ) or "Unknown authors"

    primary_location = item.get("primary_location") or {}
    source = primary_location.get("source") or {}
    venue = source.get("display_name", "") if source else ""

    doi = item.get("doi") or ""
    if doi.startswith("https://doi.org/"):
        doi = doi[len("https://doi.org/"):]

    abstract = _reconstruct_openalex_abstract(item.get("abstract_inverted_index"))

    return {
        "title": item.get("title") or item.get("display_name") or "(untitled)",
        "authors": author_names,
        "year": item.get("publication_year"),
        "venue": venue,
        "doi": doi,
        "url": primary_location.get("landing_page_url") or item.get("id") or "",
        "citation_count": item.get("cited_by_count", 0),
        "abstract": (abstract[:280] + "…") if abstract and len(abstract) > 280 else abstract,
        "pdf_url": primary_location.get("pdf_url"),
        "type": item.get("type", ""),
        "source": "OpenAlex",
    }


def _search_semantic_scholar(query: str, limit: int) -> list:
    resp = requests.get(
        SEMANTIC_SCHOLAR_SEARCH_URL,
        params={
            "query": query,
            "limit": limit,
            "fields": "title,authors,year,venue,citationCount,abstract,url,openAccessPdf,externalIds,publicationTypes",
        },
        headers={"User-Agent": "ResearchDashboard/1.0"},
        timeout=8,
    )
    resp.raise_for_status()
    items = resp.json().get("data", []) or []
    return [_format_semantic_scholar_item(i) for i in items]


def _search_crossref(query: str, limit: int) -> list:
    resp = requests.get(
        CROSSREF_URL,
        params={
            "query": query,
            "rows": limit,
            "select": "title,author,published,published-print,published-online,"
                      "issued,container-title,DOI,URL,is-referenced-by-count,type",
            "mailto": "dashboard-demo@example.com",  # CrossRef's "polite pool" for reliable service
        },
        headers={"User-Agent": "ResearchDashboard/1.0 (mailto:dashboard-demo@example.com)"},
        timeout=8,
    )
    resp.raise_for_status()
    items = resp.json().get("message", {}).get("items", [])
    return [_format_crossref_item(i) for i in items]


def _search_openalex(query: str, limit: int) -> list:
    resp = requests.get(
        OPENALEX_URL,
        params={"search": query, "per_page": limit, "mailto": "dashboard-demo@example.com"},
        headers={"User-Agent": "ResearchDashboard/1.0 (mailto:dashboard-demo@example.com)"},
        timeout=8,
    )
    resp.raise_for_status()
    items = resp.json().get("results", [])
    return [_format_openalex_item(i) for i in items]


# Tried in order until one succeeds — each is a real, free, keyless public API.
SEARCH_PROVIDERS = [
    ("Semantic Scholar", _search_semantic_scholar),
    ("CrossRef", _search_crossref),
    ("OpenAlex", _search_openalex),
]


@app.get("/api/search/live")
def search_live():
    query = (request.args.get("q") or "").strip()
    limit = min(max(request.args.get("limit", 8, type=int), 1), 20)

    if not query:
        return jsonify({"data": [], "message": "Type something to search"}), 200
    if len(query) < 3:
        return jsonify({"data": [], "message": "Keep typing (min 3 characters)"}), 200

    cache_key = f"{query.lower()}::{limit}"
    cached = _search_cache.get(cache_key)
    if cached and (time.time() - cached[0]) < CACHE_TTL_SECONDS:
        return jsonify({"data": cached[1], "source": cached[2] + " (cached)"})

    last_error = None
    for i, (name, search_fn) in enumerate(SEARCH_PROVIDERS):
        try:
            results = search_fn(query, limit)
            _search_cache[cache_key] = (time.time(), results, name)
            label = name if i == 0 else f"{name} (fallback)"
            return jsonify({"data": results, "source": label})
        except requests.exceptions.RequestException as e:
            last_error = e
            continue  # try the next provider

    # All three providers failed.
    if isinstance(last_error, requests.exceptions.Timeout):
        return jsonify({"message": "All external paper databases timed out. Try again in a moment."}), 504
    if isinstance(last_error, requests.exceptions.HTTPError):
        status = last_error.response.status_code if last_error.response is not None else 502
        if status == 429:
            return jsonify({"message": "External paper databases are rate-limiting us right now. Try again shortly."}), 429
        return jsonify({"message": f"External paper databases returned an error ({status})."}), 502
    return jsonify({"message": f"Couldn't reach any external paper database: {last_error}"}), 502


# ---------------------------------------------------------------------------
# Live citation refresh — pulls a REAL, current citation count for papers
# already in your local reviewed-papers table (not just the search page).
# ---------------------------------------------------------------------------
def _lookup_citation_count(title: str) -> int | None:
    """Best-effort: resolve a known paper title to its current citation count."""
    try:
        resp = requests.get(
            SEMANTIC_SCHOLAR_MATCH_URL,
            params={"query": title, "fields": "citationCount"},
            headers={"User-Agent": "ResearchDashboard/1.0"},
            timeout=6,
        )
        if resp.ok:
            data = resp.json().get("data", [])
            if data:
                return data[0].get("citationCount")
    except requests.exceptions.RequestException:
        pass

    # Fallback to CrossRef's top hit for the same title.
    try:
        resp = requests.get(
            CROSSREF_URL,
            params={"query.bibliographic": title, "rows": 1, "select": "is-referenced-by-count"},
            headers={"User-Agent": "ResearchDashboard/1.0 (mailto:dashboard-demo@example.com)"},
            timeout=6,
        )
        if resp.ok:
            items = resp.json().get("message", {}).get("items", [])
            if items:
                return items[0].get("is-referenced-by-count")
    except requests.exceptions.RequestException:
        pass

    # Final fallback: OpenAlex's top hit for the same title.
    try:
        resp = requests.get(
            OPENALEX_URL,
            params={"search": title, "per_page": 1, "select": "cited_by_count",
                    "mailto": "dashboard-demo@example.com"},
            headers={"User-Agent": "ResearchDashboard/1.0"},
            timeout=6,
        )
        if resp.ok:
            results = resp.json().get("results", [])
            if results:
                return results[0].get("cited_by_count")
    except requests.exceptions.RequestException:
        pass

    return None


@app.post("/api/papers/<int:paper_id>/refresh-citations")
def refresh_paper_citations(paper_id):
    conn = get_connection()
    paper = conn.execute("SELECT title FROM research_papers WHERE id = ?", (paper_id,)).fetchone()
    if not paper:
        conn.close()
        return error("Paper not found", 404)

    count = _lookup_citation_count(paper["title"])
    now = time.strftime("%Y-%m-%d %H:%M:%S")

    if count is None:
        conn.close()
        return jsonify({"message": "Couldn't find a confident match in either external database for this title."}), 502

    conn.execute(
        "UPDATE research_papers SET citation_count = ?, citations_updated_at = ? WHERE id = ?",
        (count, now, paper_id),
    )
    conn.commit()
    updated = fetch_paper(conn, paper_id)
    conn.close()
    return jsonify({"data": updated, "message": f"Citation count updated: {count}"})


@app.post("/api/papers/refresh-citations")
def refresh_all_citations():
    conn = get_connection()
    papers = conn.execute("SELECT id, title FROM research_papers").fetchall()
    conn.close()

    updated, failed = [], []
    for p in papers:
        count = _lookup_citation_count(p["title"])
        if count is None:
            failed.append(p["title"])
            continue
        conn = get_connection()
        conn.execute(
            "UPDATE research_papers SET citation_count = ?, citations_updated_at = ? WHERE id = ?",
            (count, time.strftime("%Y-%m-%d %H:%M:%S"), p["id"]),
        )
        conn.commit()
        conn.close()
        updated.append({"title": p["title"], "citation_count": count})
        time.sleep(0.3)  # be polite to the free/keyless API tiers

    return jsonify({
        "message": f"Updated {len(updated)} of {len(papers)} papers"
                   + (f" ({len(failed)} couldn't be matched)" if failed else ""),
        "updated": updated,
        "failed": failed,
    })


# ---------------------------------------------------------------------------
# Topic trend chart — papers per year for a topic, from OpenAlex's
# group_by=publication_year aggregation (real publication-volume data, not
# just a handful of search results).
# ---------------------------------------------------------------------------
_trend_cache: dict[str, tuple[float, list]] = {}


@app.get("/api/topic-trend")
def topic_trend():
    query = (request.args.get("q") or "").strip()
    if not query or len(query) < 3:
        return jsonify({"data": [], "message": "Type a topic (min 3 characters)"}), 200

    cache_key = query.lower()
    cached = _trend_cache.get(cache_key)
    if cached and (time.time() - cached[0]) < CACHE_TTL_SECONDS:
        return jsonify({"data": cached[1], "source": "OpenAlex (cached)"})

    try:
        resp = requests.get(
            OPENALEX_URL,
            params={
                "search": query,
                "group_by": "publication_year",
                "mailto": "dashboard-demo@example.com",
            },
            headers={"User-Agent": "ResearchDashboard/1.0"},
            timeout=8,
        )
        resp.raise_for_status()
        groups = resp.json().get("group_by", [])

        current_year = datetime.now().year
        data = []
        for g in groups:
            try:
                year = int(g.get("key"))
            except (TypeError, ValueError):
                continue
            if current_year - 14 <= year <= current_year:  # keep the chart to a readable last-15-years window
                data.append({"year": year, "count": g.get("count", 0)})
        data.sort(key=lambda x: x["year"])

        _trend_cache[cache_key] = (time.time(), data)
        return jsonify({"data": data, "source": "OpenAlex"})

    except requests.exceptions.Timeout:
        return jsonify({"message": "OpenAlex timed out. Try again in a moment."}), 504
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else 502
        return jsonify({"message": f"OpenAlex returned an error ({status})."}), 502
    except requests.exceptions.RequestException as e:
        return jsonify({"message": f"Couldn't reach OpenAlex: {e}"}), 502


# ---------------------------------------------------------------------------
# Reading list — bookmarks (with tags, notes, read/unread) from Discover Papers
# ---------------------------------------------------------------------------
@app.get("/api/reading-list")
def list_reading_list():
    conn = get_connection()
    sql = "SELECT * FROM reading_list"
    where, params = [], []

    status = request.args.get("status")
    tag = request.args.get("tag")
    search = request.args.get("search")

    if status:
        where.append("status = ?")
        params.append(status)
    if tag:
        where.append("tags LIKE ?")
        params.append(f"%{tag}%")
    if search:
        where.append("(title LIKE ? OR authors LIKE ?)")
        term = f"%{search}%"
        params += [term, term]

    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY bookmarked_at DESC"

    rows = rows_to_list(conn.execute(sql, params).fetchall())
    conn.close()
    return jsonify({"data": rows})


@app.post("/api/reading-list")
def add_to_reading_list():
    data = request.get_json(force=True, silent=True) or {}
    err = require_fields(data, ["title"])
    if err:
        return err

    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO reading_list
           (title, authors, venue, year, doi, url, abstract, source, tags, notes, status, bookmarked_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data.get("title"), data.get("authors", ""), data.get("venue", ""), data.get("year"),
            data.get("doi", ""), data.get("url", ""), data.get("abstract", ""), data.get("source", ""),
            data.get("tags", ""), data.get("notes", ""), data.get("status", "unread"),
            time.strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    conn.commit()
    item = row_to_dict(conn.execute("SELECT * FROM reading_list WHERE id = ?", (cur.lastrowid,)).fetchone())
    conn.close()
    return jsonify({"data": item, "message": "Added to reading list"}), 201


@app.put("/api/reading-list/<int:item_id>")
def update_reading_list_item(item_id):
    data = request.get_json(force=True, silent=True) or {}
    conn = get_connection()
    existing = conn.execute("SELECT id FROM reading_list WHERE id = ?", (item_id,)).fetchone()
    if not existing:
        conn.close()
        return error("Not found in reading list", 404)

    fields, values = [], []
    for key in ("title", "authors", "venue", "year", "tags", "notes", "status"):
        if key in data:
            fields.append(f"{key} = ?")
            values.append(data[key])
    if not fields:
        conn.close()
        return error("Nothing to update")

    values.append(item_id)
    conn.execute(f"UPDATE reading_list SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    item = row_to_dict(conn.execute("SELECT * FROM reading_list WHERE id = ?", (item_id,)).fetchone())
    conn.close()
    return jsonify({"data": item, "message": "Reading list item updated"})


@app.delete("/api/reading-list/<int:item_id>")
def delete_reading_list_item(item_id):
    conn = get_connection()
    conn.execute("DELETE FROM reading_list WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Removed from reading list"})


# ---------------------------------------------------------------------------
# Research tools — one-click summary, auto-generated research gap, and
# literature-review paragraph drafting. All template-based (see
# generators.py): no external AI, no API key, fully deterministic.
# ---------------------------------------------------------------------------
@app.post("/api/tools/paper-summary")
def tool_paper_summary():
    data = request.get_json(force=True, silent=True) or {}

    if data.get("paper_id"):
        conn = get_connection()
        paper = fetch_paper(conn, data["paper_id"])
        conn.close()
        if not paper:
            return error("Paper not found", 404)
        content = build_paper_summary(paper)
    else:
        err = require_fields(data, ["title"])
        if err:
            return err
        content = build_paper_summary(data)

    return jsonify({"content": content})


@app.get("/api/tools/research-gap")
def tool_research_gap():
    conn = get_connection()
    papers = rows_to_list(conn.execute(
        """SELECT rp.*, t.name AS theme_name FROM research_papers rp
           JOIN themes t ON t.id = rp.theme_id"""
    ).fetchall())
    findings = rows_to_list(conn.execute("SELECT * FROM key_findings").fetchall())
    conn.close()
    content = build_research_gap(papers, findings)
    return jsonify({"content": content})


@app.get("/api/tools/literature-paragraph")
def tool_literature_paragraph():
    theme_id = request.args.get("theme_id", type=int)
    if not theme_id:
        return error("theme_id is required")

    conn = get_connection()
    theme = row_to_dict(conn.execute("SELECT * FROM themes WHERE id = ?", (theme_id,)).fetchone())
    if not theme:
        conn.close()
        return error("Theme not found", 404)
    papers = rows_to_list(conn.execute(
        "SELECT * FROM research_papers WHERE theme_id = ? ORDER BY year ASC", (theme_id,)
    ).fetchall())
    conn.close()

    content = build_literature_paragraph(theme, papers)
    return jsonify({"content": content, "theme_name": theme["name"]})


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
