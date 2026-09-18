"""Supabase client connection - fill in your project URL and key as env vars."""
import os
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
# The secret key is used only by this trusted FastAPI server. It bypasses RLS
# and must never be copied into citizen-web or committed to source control.
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY") or os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL and SUPABASE_SECRET_KEY must be set in backend/.env")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
