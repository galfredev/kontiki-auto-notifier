import os
from supabase import create_client
from functools import lru_cache

@lru_cache
def get_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError(
            "Faltan SUPABASE_URL / SUPABASE_KEY. Cargalas en Render → Environment."
        )
    return create_client(url, key)
