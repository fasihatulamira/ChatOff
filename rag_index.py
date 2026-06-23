"""Fast cosine search using pre-normalized embedding vectors."""
import math


def normalize(vec: list[float]) -> list[float]:
    mag = math.sqrt(sum(x * x for x in vec))
    if mag == 0:
        return list(vec)
    return [x / mag for x in vec]


def ensure_norm_embeddings(db: dict) -> None:
    """Build or refresh norm_embeddings cache aligned with embeddings list."""
    embeddings = db.get("embeddings", [])
    norm = db.get("norm_embeddings", [])
    if norm and len(norm) == len(embeddings):
        return
    db["norm_embeddings"] = [normalize(e) for e in embeddings]


def search_similar(
    query_emb: list[float],
    norm_embeddings: list[list[float]],
    indices: list[int] | None = None,
) -> list[tuple[float, int]]:
    """
    Return (score, index) pairs sorted by score descending.
    Scores are cosine similarity because vectors are unit-normalized.
    """
    q = normalize(query_emb)
    pool = indices if indices is not None else list(range(len(norm_embeddings)))
    scored: list[tuple[float, int]] = []
    for i in pool:
        emb = norm_embeddings[i]
        score = sum(a * b for a, b in zip(q, emb))
        scored.append((score, i))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored
