import re
import hashlib


def normalize_prompt(prompt: str) -> str:
    """Normalize whitespace and punctuation to increase cache hit probability."""
    # Collapse multiple whitespaces and strip
    cleaned = re.sub(r"\s+", " ", prompt.strip().lower())
    # Strip standard trailing query punctuation
    cleaned = cleaned.rstrip("?!.,;:")
    return cleaned


def generate_cache_key(prompt: str, prefix: str = "jevflow:resp:") -> str:
    """Generate a deterministic SHA-256 cache key from a user prompt."""
    normalized = normalize_prompt(prompt)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]
    return f"{prefix}{digest}"
