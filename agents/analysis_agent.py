"""Analysis Agent — reads a changed dataset and extracts insights using Groq."""

import asyncio
import httpx
import csv
import io
import json
from groq import Groq
from core.config import GROQ_API_KEY, GROQ_MODEL


# Initialize Groq client
_client = Groq(api_key=GROQ_API_KEY)


async def run_analysis(dataset: dict) -> dict:
    """
    Analyse a changed dataset and produce structured insight bullets.
    Downloads dataset content if available, then uses Groq for analysis.
    """
    dataset_id = dataset.get("dataset_id", "")
    title = dataset.get("title", "Untitled")
    description = dataset.get("description", "")
    resource_url = dataset.get("resource_url", "")
    topic = dataset.get("topic", "economy")
    page_url = dataset.get("page_url", "")
    modified = dataset.get("modified", "")

    # Attempt to download and summarise the dataset content
    data_summary = ""
    if resource_url:
        data_summary = await _download_and_summarise(resource_url)

    # Build the prompt
    prompt = _build_analysis_prompt(title, description, data_summary)

    # Call Groq (with retry for rate limits)
    analysis_text = None
    for attempt in range(3):
        try:
            response = _client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.7,
            )
            analysis_text = response.choices[0].message.content.strip()
            break
        except Exception as e:
            err_str = str(e)
            if "429" in err_str and attempt < 2:
                wait = (attempt + 1) * 15
                print(f"Analysis Agent: Rate limited, retrying in {wait}s...")
                await asyncio.sleep(wait)
            else:
                print(f"Analysis Agent: Groq error for '{title}' — {e}")
                break

    if not analysis_text:
        analysis_text = (
            "• This dataset was recently updated with new figures.\n"
            "• Luxembourg residents who rely on public services may be affected.\n"
            "• Check the source data for the latest numbers."
        )

    # Parse the three bullets
    bullets = _parse_bullets(analysis_text)

    result = {
        "dataset_id": dataset_id,
        "title": title,
        "topic": topic,
        "key_finding": bullets[0],
        "who_affected": bullets[1],
        "practical_implication": bullets[2],
        "source_url": page_url or resource_url,
        "modified_date": modified,
    }

    print(f"Analysis Agent: Processed — {title}")
    return result


async def _download_and_summarise(url: str) -> str:
    """Download the first 500 rows of a CSV/JSON resource and summarise."""
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").lower()
            text = response.text[:500_000]  # Cap at 500KB of text

        if "csv" in content_type or url.lower().endswith(".csv"):
            return _summarise_csv(text)
        elif "json" in content_type or url.lower().endswith(".json"):
            return _summarise_json(text)
        else:
            # Try CSV first, fall back to JSON
            try:
                return _summarise_csv(text)
            except Exception:
                try:
                    return _summarise_json(text)
                except Exception:
                    return f"Raw data preview (first 500 chars): {text[:500]}"
    except Exception as e:
        print(f"Analysis Agent: Could not download resource — {e}")
        return ""


def _summarise_csv(text: str) -> str:
    """Parse CSV text and return a human-readable summary."""
    reader = csv.reader(io.StringIO(text))
    rows = []
    for i, row in enumerate(reader):
        if i >= 501:  # header + 500 rows
            break
        rows.append(row)

    if len(rows) < 2:
        return "CSV file with insufficient data for analysis."

    headers = rows[0]
    data_rows = rows[1:]

    summary_parts = [
        f"Columns ({len(headers)}): {', '.join(headers[:15])}",
        f"Total rows sampled: {len(data_rows)}",
        "",
        "First 5 rows:",
    ]

    for row in data_rows[:5]:
        summary_parts.append("  " + " | ".join(row[:10]))

    # Basic numeric stats
    numeric_stats = _compute_numeric_stats(headers, data_rows)
    if numeric_stats:
        summary_parts.append("")
        summary_parts.append("Numeric column stats:")
        for stat in numeric_stats:
            summary_parts.append(f"  {stat}")

    return "\n".join(summary_parts)


def _summarise_json(text: str) -> str:
    """Parse JSON text and return a human-readable summary."""
    data = json.loads(text)

    if isinstance(data, list):
        items = data[:500]
        if not items:
            return "Empty JSON array."
        sample = items[0] if isinstance(items[0], dict) else {}
        keys = list(sample.keys())[:15] if sample else []
        summary = f"JSON array with {len(items)} items.\nFields: {', '.join(keys)}\n\nFirst 3 items:\n"
        for item in items[:3]:
            summary += f"  {json.dumps(item, default=str)[:200]}\n"
        return summary
    elif isinstance(data, dict):
        # Could be a single object or a wrapper
        if "data" in data and isinstance(data["data"], list):
            return _summarise_json(json.dumps(data["data"]))
        keys = list(data.keys())[:15]
        return f"JSON object with keys: {', '.join(keys)}\nPreview: {json.dumps(data, default=str)[:500]}"
    else:
        return f"JSON value: {str(data)[:500]}"


def _compute_numeric_stats(headers: list, rows: list) -> list[str]:
    """Compute min/max/count for numeric columns."""
    stats = []
    for col_idx, header in enumerate(headers[:10]):
        values = []
        for row in rows:
            if col_idx < len(row):
                try:
                    values.append(float(row[col_idx].replace(",", ".")))
                except (ValueError, AttributeError):
                    continue
        if len(values) >= 3:
            stats.append(
                f"{header}: min={min(values):.2f}, max={max(values):.2f}, "
                f"count={len(values)}, avg={sum(values)/len(values):.2f}"
            )
    return stats[:5]


def _build_analysis_prompt(title: str, description: str, data_summary: str) -> str:
    """Build the structured prompt for dataset analysis."""
    parts = [
        "You are an analyst. Read this Luxembourg public dataset.",
        f"\nDataset title: {title}",
        f"\nDescription: {description[:500]}",
    ]

    if data_summary:
        parts.append(f"\nData summary:\n{data_summary[:3000]}")

    parts.append(
        "\n\nIn 3 bullet points, identify:"
        "\n(1) What changed or what is the most important finding"
        "\n(2) Which group of Luxembourg residents this affects most"
        "\n(3) One practical implication for daily life"
        "\n\nBe specific with numbers. Keep each bullet under 25 words. "
        "Do not use marketing language."
        "\n\nFormat your response as exactly 3 lines starting with '•' (bullet character)."
    )

    return "\n".join(parts)


def _parse_bullets(text: str) -> list[str]:
    """Extract three bullet points from LLM response."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    bullets = []
    for line in lines:
        cleaned = line.lstrip("•-*123456789.)  ").strip()
        if cleaned:
            bullets.append(cleaned)
        if len(bullets) >= 3:
            break

    # Pad if fewer than 3 bullets
    while len(bullets) < 3:
        bullets.append("See the source data for more details.")

    return bullets[:3]
