from typing import Optional


def parse_positive_int(text: str, min_v: int = 0, max_v: int = 10_000_000) -> Optional[int]:
    try:
        v = int(text.strip().replace(" ", "").replace(",", ""))
    except (ValueError, AttributeError):
        return None
    if v < min_v or v > max_v:
        return None
    return v


def validate_media_combo(media: list) -> bool:
    """
    media: list of tuples (type, file_id)
    Allowed combos:
      - 1 photo
      - 2 photos
      - 1 video
    """
    if not media:
        return False
    types = [m[0] for m in media]
    if types == ["photo"]:
        return True
    if types == ["photo", "photo"]:
        return True
    if types == ["video"]:
        return True
    return False


def normalize_username(raw: str) -> str:
    return raw.strip().lstrip("@")