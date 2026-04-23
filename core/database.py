import chromadb
import chromadb.api.types as chroma_types
import json
import hashlib
from datetime import datetime, timezone


class _NoOpEmbeddingFunction(chroma_types.EmbeddingFunction):
    """Simple hash-based embedding — we don't use similarity search."""

    def __init__(self) -> None:
        pass

    def __call__(self, input: list[str]) -> list[list[float]]:
        results = []
        for text in input:
            h = hashlib.md5(text.encode()).hexdigest()
            # Convert hex digest to a fixed-length float vector
            vec = [float(int(h[i : i + 2], 16)) / 255.0 for i in range(0, 32, 2)]
            results.append(vec)
        return results


_ef = _NoOpEmbeddingFunction()
_client = chromadb.PersistentClient(path="./chroma_store")

_snapshots = _client.get_or_create_collection(name="dataset_snapshots", embedding_function=_ef)
_stories = _client.get_or_create_collection(name="stories", embedding_function=_ef)


def save_snapshot(dataset_id: str, metadata: dict, content_hash: str) -> None:
    """Save a dataset metadata snapshot to ChromaDB."""
    doc_id = f"snap_{dataset_id}_{datetime.now(timezone.utc).isoformat()}"
    meta = {
        "dataset_id": dataset_id,
        "content_hash": content_hash,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "title": metadata.get("title", ""),
        "modified": metadata.get("modified", ""),
    }
    _snapshots.upsert(
        ids=[doc_id],
        documents=[json.dumps(metadata, default=str)],
        metadatas=[meta],
    )


def get_last_snapshot(dataset_id: str) -> dict | None:
    """Return the most recent snapshot for a dataset, or None if none exist."""
    results = _snapshots.get(
        where={"dataset_id": dataset_id},
        include=["documents", "metadatas"],
    )
    if not results["ids"]:
        return None

    # Find the most recent by timestamp
    best_idx = 0
    best_ts = ""
    for i, meta in enumerate(results["metadatas"]):
        ts = meta.get("timestamp", "")
        if ts > best_ts:
            best_ts = ts
            best_idx = i

    snapshot_meta = results["metadatas"][best_idx]
    try:
        snapshot_doc = json.loads(results["documents"][best_idx])
    except (json.JSONDecodeError, TypeError):
        snapshot_doc = {}

    return {**snapshot_meta, "document": snapshot_doc}


def save_story(title: str, body: str, topic: str, source_url: str, dataset_id: str) -> None:
    """Save a generated story to ChromaDB."""
    now = datetime.now(timezone.utc).isoformat()
    doc_id = f"story_{dataset_id}_{hashlib.md5(title.encode()).hexdigest()[:8]}_{now}"
    meta = {
        "title": title,
        "topic": topic,
        "source_url": source_url,
        "dataset_id": dataset_id,
        "date": now,
    }
    _stories.upsert(
        ids=[doc_id],
        documents=[body],
        metadatas=[meta],
    )


def get_recent_stories(limit: int = 20) -> list[dict]:
    """Return the most recent stories, sorted by date descending."""
    results = _stories.get(
        include=["documents", "metadatas"],
        limit=min(limit, 100),
    )
    if not results["ids"]:
        return []

    stories = []
    for i in range(len(results["ids"])):
        meta = results["metadatas"][i]
        stories.append(
            {
                "title": meta.get("title", ""),
                "body": results["documents"][i],
                "topic": meta.get("topic", ""),
                "source_url": meta.get("source_url", ""),
                "date": meta.get("date", ""),
            }
        )

    # Sort by date descending
    stories.sort(key=lambda s: s["date"], reverse=True)
    return stories[:limit]


def get_stories_by_topic(topic: str, limit: int = 10) -> list[dict]:
    """Return stories filtered by topic, sorted by date descending."""
    results = _stories.get(
        where={"topic": topic},
        include=["documents", "metadatas"],
        limit=min(limit, 100),
    )
    if not results["ids"]:
        return []

    stories = []
    for i in range(len(results["ids"])):
        meta = results["metadatas"][i]
        stories.append(
            {
                "title": meta.get("title", ""),
                "body": results["documents"][i],
                "topic": meta.get("topic", ""),
                "source_url": meta.get("source_url", ""),
                "date": meta.get("date", ""),
            }
        )

    stories.sort(key=lambda s: s["date"], reverse=True)
    return stories[:limit]


def get_total_story_count() -> int:
    """Return total number of stories stored."""
    return _stories.count()


def get_total_snapshot_count() -> int:
    """Return total number of dataset snapshots stored."""
    return _snapshots.count()


def get_topic_counts() -> list[dict]:
    """Return a list of topics with their story counts."""
    all_stories = _stories.get(include=["metadatas"])
    topic_map: dict[str, int] = {}
    for meta in all_stories.get("metadatas", []):
        topic = meta.get("topic", "other")
        topic_map[topic] = topic_map.get(topic, 0) + 1

    return [{"topic": t, "count": c} for t, c in sorted(topic_map.items())]
