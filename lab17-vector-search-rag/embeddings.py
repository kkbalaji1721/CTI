"""Embedding providers for the lab. Offline vectors are deterministic feature hashes."""

import hashlib
import json
import math
import os
import re
import urllib.error
import urllib.request

LOCAL_DIMENSIONS = 384
VOYAGE_MODELS = {
    "voyage-3-lite": 512,
    "voyage-3.5-lite": 512,
}


def _local_vector(text: str, dimensions: int = LOCAL_DIMENSIONS) -> list[float]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    features = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
    vector = [0.0] * dimensions
    for feature in features:
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        value = int.from_bytes(digest[:4], "little")
        vector[value % dimensions] += 1.0 if digest[4] & 1 else -1.0
    norm = math.sqrt(sum(value * value for value in vector))
    if norm:
        vector = [value / norm for value in vector]
    return vector


def local_embeddings(texts: list[str], dimensions: int = LOCAL_DIMENSIONS) -> list[list[float]]:
    return [_local_vector(text, dimensions) for text in texts]


class EmbeddingProvider:
    def __init__(self) -> None:
        self.api_key = os.getenv("VOYAGE_API_KEY")
        self.model = os.getenv("VOYAGE_MODEL", "voyage-3-lite")
        if self.api_key:
            if self.model not in VOYAGE_MODELS:
                raise ValueError(f"Unsupported Voyage model for configured dimension: {self.model}")
            self.dimensions = VOYAGE_MODELS[self.model]
            self.provider = "Voyage AI"
        else:
            self.dimensions = LOCAL_DIMENSIONS
            self.provider = "local deterministic feature hashing (not a learned semantic model)"

    def embed(self, texts: list[str], input_type: str = "document") -> list[list[float]]:
        if not texts:
            return []
        if not self.api_key:
            return local_embeddings(texts, self.dimensions)

        vectors = []
        for start in range(0, len(texts), 128):
            payload = json.dumps(
                {"input": texts[start : start + 128], "model": self.model, "input_type": input_type}
            ).encode("utf-8")
            request = urllib.request.Request(
                "https://api.voyageai.com/v1/embeddings",
                data=payload,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    result = json.loads(response.read().decode("utf-8"))
            except (urllib.error.URLError, TimeoutError) as exc:
                raise RuntimeError(f"Voyage embedding request failed: {exc}") from exc
            vectors.extend(
                row["embedding"] for row in sorted(result["data"], key=lambda row: row["index"])
            )
        if any(len(vector) != self.dimensions for vector in vectors):
            raise RuntimeError("Voyage returned an embedding with an unexpected dimension.")
        return vectors


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("Cannot compare embeddings with different dimensions.")
    denominator = math.sqrt(sum(x * x for x in left) * sum(y * y for y in right))
    return sum(x * y for x, y in zip(left, right)) / denominator if denominator else 0.0
