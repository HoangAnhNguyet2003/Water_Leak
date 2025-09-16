import bcrypt as bc

def hash_password(plain: str) -> str:
    return bc.hashpw(plain.encode("utf-8"), bc.gensalt()).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    if not isinstance(hashed, str):
        hashed = hashed.decode("utf-8", errors="ignore")
    hashed = hashed.strip()
    return bc.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))