"""
database.py — Dual backend database client for LabOps Agent.
Supports Supabase (cloud) or direct PostgreSQL via psycopg2 (local/Docker).
"""
import os
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# ---------------------------------------------------------------------------
# Backend selection
# ---------------------------------------------------------------------------
_use_pg = bool(DATABASE_URL and not (SUPABASE_URL and SUPABASE_KEY))

if _use_pg:
    import psycopg2
    from psycopg2.extras import RealDictCursor

    def _get_pg_conn():
        return psycopg2.connect(DATABASE_URL)
else:
    from supabase import create_client, Client
    _supabase: Optional[Client] = None

    def get_supabase() -> Client:
        global _supabase
        if _supabase is None:
            if not SUPABASE_URL or not SUPABASE_KEY:
                raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set")
            _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        return _supabase


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _pg_execute(sql: str, params: tuple = (), fetch: bool = False):
    conn = _get_pg_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(sql, params)
    if fetch:
        rows = cur.fetchall()
    else:
        conn.commit()
        try:
            rows = cur.fetchall()
        except Exception:
            rows = []
    cur.close()
    conn.close()
    return [dict(r) for r in rows]


def _pg_execute_one(sql: str, params: tuple = ()):
    rows = _pg_execute(sql, params, fetch=True)
    return rows[0] if rows else {}


# ---------------------------------------------------------------------------
# inventory
# ---------------------------------------------------------------------------
def get_inventory(reagent_name: Optional[str] = None) -> List[Dict[str, Any]]:
    if _use_pg:
        sql = "SELECT * FROM inventory"
        params = ()
        if reagent_name:
            sql += " WHERE reagent_name = %s"
            params = (reagent_name,)
        return _pg_execute(sql, params, fetch=True)
    sb = get_supabase()
    q = sb.table("inventory").select("*")
    if reagent_name:
        q = q.eq("reagent_name", reagent_name)
    resp = q.execute()
    return resp.data or []


def update_inventory_stock(reagent_name: str, new_stock: float) -> Dict[str, Any]:
    if _use_pg:
        sql = (
            "UPDATE inventory SET current_stock = %s, updated_at = now() "
            "WHERE reagent_name = %s RETURNING *"
        )
        return _pg_execute_one(sql, (new_stock, reagent_name))
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
    if _use_pg:
        sql = "SELECT * FROM demand_history ORDER BY date DESC LIMIT %s"
        params = (limit,)
        if reagent_name:
            sql = (
                "SELECT * FROM demand_history WHERE reagent_name = %s "
                "ORDER BY date DESC LIMIT %s"
            )
            params = (reagent_name, limit)
        return _pg_execute(sql, params, fetch=True)
    sb = get_supabase()
    q = sb.table("demand_history").select("*").order("date", desc=True).limit(limit)
    if reagent_name:
        q = q.eq("reagent_name", reagent_name)
    resp = q.execute()
    return resp.data or []


def insert_demand_record(record: Dict[str, Any]) -> Dict[str, Any]:
    if _use_pg:
        cols = ", ".join(record.keys())
        vals = ", ".join(["%s"] * len(record))
        sql = f"INSERT INTO demand_history ({cols}) VALUES ({vals}) RETURNING *"
        return _pg_execute_one(sql, tuple(record.values()))
    sb = get_supabase()
    resp = sb.table("demand_history").insert(record).execute()
    return resp.data[0] if resp.data else {}


# ---------------------------------------------------------------------------
# orders
# ---------------------------------------------------------------------------
def create_order(reagent_name: str, quantity: float, supplier: str, status: str = "pending") -> Dict[str, Any]:
    if _use_pg:
        sql = (
            "INSERT INTO orders (reagent_name, quantity, supplier, status) "
            "VALUES (%s, %s, %s, %s) RETURNING *"
        )
        return _pg_execute_one(sql, (reagent_name, quantity, supplier, status))
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
    if _use_pg:
        sql = "SELECT * FROM orders ORDER BY created_at DESC"
        params = ()
        conditions = []
        if reagent_name:
            conditions.append("reagent_name = %s")
            params += (reagent_name,)
        if status:
            conditions.append("status = %s")
            params += (status,)
        if conditions:
            sql = f"SELECT * FROM orders WHERE {' AND '.join(conditions)} ORDER BY created_at DESC"
        return _pg_execute(sql, params, fetch=True)
    sb = get_supabase()
    q = sb.table("orders").select("*").order("created_at", desc=True)
    if reagent_name:
        q = q.eq("reagent_name", reagent_name)
    if status:
        q = q.eq("status", status)
    resp = q.execute()
    return resp.data or []


def update_order_status(order_id: str, new_status: str) -> Dict[str, Any]:
    if _use_pg:
        sql = (
            "UPDATE orders SET status = %s, updated_at = now() "
            "WHERE id = %s RETURNING *"
        )
        return _pg_execute_one(sql, (new_status, order_id))
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
    if _use_pg:
        sql = (
            "INSERT INTO alerts_log (reagent_name, predicted_stockout_date, severity, explanation) "
            "VALUES (%s, %s, %s, %s) RETURNING *"
        )
        return _pg_execute_one(sql, (reagent_name, predicted_stockout_date, severity, explanation))
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
    if _use_pg:
        sql = "SELECT * FROM alerts_log ORDER BY created_at DESC LIMIT %s"
        params = (limit,)
        if reagent_name:
            sql = (
                "SELECT * FROM alerts_log WHERE reagent_name = %s "
                "ORDER BY created_at DESC LIMIT %s"
            )
            params = (reagent_name, limit)
        return _pg_execute(sql, params, fetch=True)
    sb = get_supabase()
    q = sb.table("alerts_log").select("*").order("created_at", desc=True).limit(limit)
    if reagent_name:
        q = q.eq("reagent_name", reagent_name)
    resp = q.execute()
    return resp.data or []


# ---------------------------------------------------------------------------
# lab_config
# ---------------------------------------------------------------------------
def get_lab_config(key: str) -> Optional[str]:
    """Return config value by key, or None if not set."""
    if _use_pg:
        sql = "SELECT value FROM lab_config WHERE key = %s LIMIT 1"
        rows = _pg_execute(sql, (key,), fetch=True)
        return rows[0]["value"] if rows else None
    sb = get_supabase()
    resp = sb.table("lab_config").select("value").eq("key", key).limit(1).execute()
    if resp.data:
        return resp.data[0]["value"]
    return None


def set_lab_config(key: str, value: str) -> Dict[str, Any]:
    """Upsert a config key-value pair."""
    if _use_pg:
        sql = (
            "INSERT INTO lab_config (key, value, updated_at) VALUES (%s, %s, now()) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now() "
            "RETURNING *"
        )
        return _pg_execute_one(sql, (key, value))
    sb = get_supabase()
    resp = (
        sb.table("lab_config")
        .upsert({"key": key, "value": value, "updated_at": "now()"})
        .execute()
    )
    return resp.data[0] if resp.data else {}


# ---------------------------------------------------------------------------
# demo data helper
# ---------------------------------------------------------------------------
def has_demo_data() -> bool:
    """
    Return True if any demo (synthetic) data exists in the database.
    Checks the inventory table for rows flagged with is_demo = true.
    """
    if _use_pg:
        sql = "SELECT is_demo FROM inventory WHERE is_demo = true LIMIT 1"
        rows = _pg_execute(sql, fetch=True)
        return bool(rows)
    sb = get_supabase()
    resp = sb.table("inventory").select("is_demo").eq("is_demo", True).limit(1).execute()
    return bool(resp.data)
