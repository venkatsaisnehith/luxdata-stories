"""Monitor Agent — checks data.public.lu for recently updated datasets."""

import httpx
import hashlib
import json
from core.config import LUXEMBOURG_API_BASE, MAX_DATASETS_PER_RUN
from core.database import get_last_snapshot, save_snapshot


async def run_monitor() -> list[dict]:
    """
    Fetch recently modified datasets from data.public.lu.
    Compare each against the last stored snapshot.
    Return a list of dataset dicts that have changed (max MAX_DATASETS_PER_RUN).
    """
    url = f"{LUXEMBOURG_API_BASE}/datasets/?page_size=50"
    changed_datasets = []

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as e:
        print(f"Monitor Agent: HTTP error fetching datasets — {e}")
        return []
    except Exception as e:
        print(f"Monitor Agent: Unexpected error — {e}")
        return []

    datasets = data.get("data", [])

    for ds in datasets:
        if len(changed_datasets) >= MAX_DATASETS_PER_RUN:
            break

        dataset_id = ds.get("id", "")
        if not dataset_id:
            continue

        # Extract relevant fields (API can return null for any of these)
        title = ds.get("title") or "Untitled"
        description = ds.get("description") or ""
        modified = ds.get("last_modified") or ds.get("modified") or ""
        tags = [t.get("name", t) if isinstance(t, dict) else str(t) for t in (ds.get("tags") or [])]
        page_url = ds.get("page") or ds.get("uri") or f"https://data.public.lu/en/datasets/{dataset_id}/"

        # Find the first CSV or JSON resource
        resource_url = ""
        resources = ds.get("resources", [])
        for res in resources:
            fmt = (res.get("format") or "").lower()
            mime = (res.get("mime") or "").lower()
            if fmt in ("csv", "json") or "csv" in mime or "json" in mime:
                resource_url = res.get("url", "")
                break

        # If no CSV/JSON, just take the first resource URL
        if not resource_url and resources:
            resource_url = resources[0].get("url", "")

        # Determine topic from tags
        topic = _classify_topic(title, description, tags)

        # Build a content hash from key metadata
        content_str = json.dumps({"title": title, "modified": modified, "resources": len(resources)}, sort_keys=True)
        content_hash = hashlib.md5(content_str.encode()).hexdigest()

        # Compare with last snapshot
        last_snapshot = get_last_snapshot(dataset_id)

        is_changed = False
        if last_snapshot is None:
            is_changed = True
        else:
            last_modified = last_snapshot.get("modified", "")
            last_hash = last_snapshot.get("content_hash", "")
            if modified > last_modified or content_hash != last_hash:
                is_changed = True

        if is_changed:
            dataset_dict = {
                "dataset_id": dataset_id,
                "title": title,
                "description": description,
                "modified": modified,
                "tags": tags,
                "topic": topic,
                "resource_url": resource_url,
                "page_url": page_url,
            }
            changed_datasets.append(dataset_dict)

            # Save the new snapshot
            save_snapshot(dataset_id, dataset_dict, content_hash)

    print(f"Monitor Agent: Found {len(changed_datasets)} changed datasets")
    return changed_datasets


def _classify_topic(title: str, description: str, tags: list[str]) -> str:
    """Simple keyword-based topic classification."""
    text = f"{title} {description} {' '.join(tags)}".lower()

    topic_keywords = {
        "housing": ["housing", "logement", "immobilier", "rent", "loyer", "habitation", "dwelling", "residential"],
        "employment": ["employment", "emploi", "job", "travail", "chômage", "unemployment", "workforce", "salary", "salaire"],
        "transport": ["transport", "mobility", "traffic", "bus", "train", "road", "parking", "vélo", "bike", "mobilité"],
        "environment": ["environment", "environnement", "climate", "climat", "pollution", "waste", "déchet", "energy", "énergie", "water", "eau"],
        "economy": ["economy", "économie", "gdp", "pib", "business", "entreprise", "commerce", "finance", "budget", "tax", "impôt"],
        "health": ["health", "santé", "hospital", "hôpital", "medical", "médical", "covid", "vaccination", "pharma"],
    }

    for topic, keywords in topic_keywords.items():
        for kw in keywords:
            if kw in text:
                return topic

    return "economy"  # default topic
