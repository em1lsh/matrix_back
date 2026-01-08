import random
import string


def generate_memo(length=16):
    return "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(length))


def slugify_str(stroke: str) -> str:
    return stroke.replace("-", "").replace(" ", "").replace("'", "").lower()
