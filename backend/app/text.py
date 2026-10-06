import re

TITLES = {"mr", "mrs", "ms", "dr", "smt", "shri"}


def normalize(text: str | None) -> str | None:
    """'Ms. ANANYA  Rao' and 'Ananya Rao' are the same answer, so compare them without case, punctuation or titles."""
    if text is None:
        return None
    words = re.sub(r"[^a-z0-9]+", " ", text.lower()).split()
    return " ".join(word for word in words if word not in TITLES)
