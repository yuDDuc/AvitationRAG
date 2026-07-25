import re
import unicodedata


def _normalize_for_matching(text: str) -> str:
    """Lowercase, strip accents, and collapse whitespace for guardrail checks."""
    normalized = unicodedata.normalize("NFD", text.lower())
    without_accents = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )
    return re.sub(r"\s+", " ", without_accents).strip()


def is_prompt_injection(text: str) -> bool:
    """
    Purpose
    Protect the LLM before inference.

    Responsibilities
    - Detect prompt injection attempts.
    - Detect jailbreak attempts.
    - Detect requests to ignore previous instructions.
    - Detect attempts to reveal system prompts.
    - Detect attempts to reveal raw retrieved documents.
    - Detect role-changing attacks.
    - Detect requests for internal implementation.
    - Detect requests for hidden prompts.

    Behavior
    If malicious intent is detected:
    - Reject the request.
    - Return a predefined safe message.
    - Do not forward the request to the LLM.

    Otherwise:
    Forward the sanitized question to the retrieval pipeline.
    """
    normalized_text = _normalize_for_matching(text)
    patterns = [
        r"ignore previous instructions",
        r"bo qua (tat ca )?(cac )?(huong dan|chi dan|lenh)",
        r"tu bo (tat ca )?(cac )?(huong dan|chi dan|lenh)",
        r"quen het",
        r"forget everything",
        r"system prompt",
        r"(tiet lo|hien thi|in ra|dua ra).*(system prompt|prompt he thong|prompt)",
        r"you are now a",
        r"ban bay gio la",
        r"developer mode",
        r"jailbreak",
        r"bypass filter",
        r"vuot qua .*bo loc",
        r"(tiet lo|in ra|dua ra).*(toan bo file|raw document|noi dung goc)",
    ]

    return any(re.search(pattern, normalized_text, re.IGNORECASE) for pattern in patterns)


def sanitize_input(text: str) -> str:
    """Trim user input and collapse repeated whitespace."""
    return re.sub(r"\s+", " ", text).strip()
