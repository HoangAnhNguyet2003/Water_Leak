
from bson import ObjectId

def to_object_id(id_or_str):
    if isinstance(id_or_str, ObjectId):
        return id_or_str
    return ObjectId(str(id_or_str))

def oid_str(oid):
    return str(oid) if isinstance(oid, ObjectId) else str(oid)
