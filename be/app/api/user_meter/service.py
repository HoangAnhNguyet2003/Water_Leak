from . import repo

def get_meters(user_id: str):
    return repo.list_meters_of_user(user_id)

def get_meters_simple(user_id: str, limit: int = None):
    return repo.list_meters_of_user_simple(user_id, limit)
