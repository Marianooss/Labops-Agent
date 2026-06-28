"""
database.py — Supabase client for LabOps Agent.
Handles inventory, demand_history, orders, alerts_log tables.
"""
import os
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()  # Load .env before reading env vars

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

_supabase: Optional[Client] = None


def get_supabase() -> Client:
    global _supabase
    if _supabase is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set")
        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase


# ---------------------------------------------------------------------------
# inventory
# ---------------------------------------------------------------------------
def get_inventory(reagent_name: Optional[str] = None) -> List[Dict[str, Any]]:
    sb = get_supabase()
    q = sb.table("inventory").select("*")
    if reagent_name:
        q = q.eq("reagent_name", reagent_name)
    resp = q.execute()
    return resp.data or []


def update_inventory_stock(reagent_name: str, new_stock: float) -> Dict[str, Any]:
    sb = get_supabase()
    resp = (
        sb.table("inventory")
        .update({"current_stock": new_stock, "updated_at": "now()"})
        .eq("reagent_name", reagent_name)
        .execute()
    )
    return resp.data[0] if resp.data else {}


# ---------------------------------------------------------------------------
# demand_history
# ---------------------------------------------------------------------------
def get_demand_history(reagent_name: Optional[str] = None, limit: int = 365) -> List[Dict[str, Any]]:
    sb = get_supabase()
    q = sb.table("demand_history").select("*").order("date", desc=True).limit(limit)
    if reagent_name:
        q = q.eq("reagent_name", reagent_name)
    resp = q.execute()
    return resp.data or []


def insert_demand_record(record: Dict[str, Any]) -> Dict[str, Any]:
    sb = get_supabase()
    resp = sb.table("demand_history").insert(record).execute()
    return resp.data[0] if resp.data else {}


# ---------------------------------------------------------------------------
# orders
# ---------------------------------------------------------------------------
def create_order(reagent_name: str, quantity: float, supplier: str, status: str = "pending") -> Dict[str, Any]:
    sb = get_supabase()
    record = {
        "reagent_name": reagent_name,
        "quantity": quantity,
        "supplier": supplier,
        "status": status,
    }
    resp = sb.table("orders").insert(record).execute()
    return resp.data[0] if resp.data else {}


def get_orders(reagent_name: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
    sb = get_supabase()
    q = sb.table("orders").select("*").order("created_at", desc=True)
    if reagent_name:
        q = q.eq("reagent_name", reagent_name)
    if status:
        q = q.eq("status", status)
    resp = q.execute()
    return resp.data or []


def update_order_status(order_id: str, new_status: str) -> Dict[str, Any]:
    sb = get_supabase()
    resp = (
        sb.table("orders")
        .update({"status": new_status, "updated_at": "now()"})
        .eq("id", order_id)
        .execute()
    )
    return resp.data[0] if resp.data else {}


# ---------------------------------------------------------------------------
# alerts_log
# ---------------------------------------------------------------------------
def log_alert(reagent_name: str, predicted_stockout_date: str, severity: str, explanation: str = "") -> Dict[str, Any]:
    sb = get_supabase()
    record = {
        "reagent_name": reagent_name,
        "predicted_stockout_date": predicted_stockout_date,
        "severity": severity,
        "explanation": explanation,
    }
    resp = sb.table("alerts_log").insert(record).execute()
    return resp.data[0] if resp.data else {}


def get_alerts(reagent_name: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    sb = get_supabase()
    q = sb.table("alerts_log").select("*").order("created_at", desc=True).limit(limit)
    if reagent_name:
        q = q.eq("reagent_name", reagent_name)
    resp = q.execute()
    return resp.data or []


# ---------------------------------------------------------------------------
# demo data helper
# ---------------------------------------------------------------------------
def has_demo_data() -> bool:
    """
    Return True if any demo (synthetic) data exists in the database.
    Checks the inventory table for rows flagged with is_demo = true.
    """
    sb = get_supabase()
    resp = sb.table("inventory").select("is_demo").eq("is_demo", True).limit(1).execute()
    return bool(resp.data)
