import textstat


def flesch_reading_ease_score(text: str) -> float:
    """Return Flesch Reading Ease for English text (higher = easier to read)."""
    return float(textstat.flesch_reading_ease(text))


def flesch_kincaid_grade_level(text: str) -> float:
    """Return Flesch-Kincaid grade level (higher = more advanced reading level)."""
    return float(textstat.flesch_kincaid_grade(text))
