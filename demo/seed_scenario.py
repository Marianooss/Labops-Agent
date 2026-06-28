"""
seed_scenario.py — Prepara el escenario exacto del demo para LabOps Agent.

Uso:
    python demo/seed_scenario.py

Qué hace:
    1. Resetea el stock de TSH a 680 (escenario demo)
    2. Limpia órdenes pendientes anteriores
    3. Limpia el alerts_log para demo limpio
    4. Pre-entrena el modelo Prophet para TSH (evita lag en el demo)
    5. Verifica que calculate_stockout_projection() devuelve alert_trigger=True

Correr ANTES de grabar el video demo.
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import database as db
import prediction


def reset_demo_scenario():
    """Reset all tables to clean demo state."""
    print("🔄 Resetting demo scenario...")

    client = db.get_supabase()

    # 1. Reset TSH stock to demo value
    client.table("inventory").update({
        "current_stock": 680,
        "updated_at": "now()"
    }).eq("reagent_name", "TSH").execute()
    print("  ✅ TSH stock reset to 680")

    # 2. Clear pending orders (keep delivered ones for history)
    client.table("orders").delete().eq("status", "pending").execute()
    print("  ✅ Pending orders cleared")

    # 3. Clear alerts_log for clean demo
    client.table("alerts_log").delete().neq("id", 0).execute()
    print("  ✅ Alerts log cleared")

    print()


def pretrain_prophet_model():
    """Pre-train Prophet model to avoid lag during demo."""
    print("🧠 Pre-training Prophet model for TSH...")

    model_path = os.path.join(
        os.path.dirname(__file__), '..', 'models', 'TSH_model.pkl'
    )

    if os.path.exists(model_path):
        print("  ✅ TSH model already trained (cached)")
    else:
        # Force training by calling get_forecast
        result = prediction.get_forecast("TSH", days=30)
        print(f"  ✅ TSH model trained — {len(result['daily_demand'])} days forecasted")

    print()


def verify_demo_scenario():
    """Verify the demo scenario is correctly set up."""
    print("🔍 Verifying demo scenario...")

    # Check inventory
    inventory = db.get_inventory("TSH")
    if not inventory:
        print("  ❌ TSH not found in inventory")
        return False

    tsh = inventory[0]
    assert tsh["current_stock"] == 680, f"TSH stock is {tsh['current_stock']}, expected 680"
    assert tsh["is_demo"] == True, "is_demo should be True"
    print(f"  ✅ TSH stock: {tsh['current_stock']} units (is_demo={tsh['is_demo']})")

    # Check stockout projection
    projection = prediction.calculate_stockout_projection(
        reagent_name="TSH",
        current_stock=float(tsh["current_stock"]),
        reorder_lead_time=int(tsh["reorder_lead_time_days"])
    )

    days = projection["projected_stockout_days"]
    trigger = projection["alert_trigger"]

    print(f"  ✅ Projected stockout: {days} days")
    print(f"  ✅ Alert trigger: {trigger}")
    print(f"  ✅ Severity: {projection['severity']}")

    if not trigger:
        print("  ⚠️  WARNING: alert_trigger=False — demo won't fire alert!")
        print(f"     projected_stockout_days={days} >= reorder_lead_time={tsh['reorder_lead_time_days']}")
        return False

    if days > 5:
        print(f"  ⚠️  WARNING: {days} days is more than expected ~4 days")
        print("     Demo script says '~4 días' — check seed data")

    print()
    return True


def print_demo_readiness():
    """Print final readiness status."""
    print("=" * 50)
    print("🎬 DEMO READINESS STATUS")
    print("=" * 50)
    print()
    print("To trigger the demo alert, run:")
    print()
    print('  curl "http://localhost:8000/alert/trigger?reagent=TSH&channel=labops-alerts"')
    print()
    print("Or wait for the scheduled check (runs every hour).")
    print()
    print("Make sure these are running:")
    print("  Terminal 1: uvicorn backend.main:app --reload")
    print("  Terminal 2: python -m backend.slack_client")
    print()
    print("=" * 50)


if __name__ == "__main__":
    print()
    print("🔬 LabOps Agent — Demo Setup")
    print("Calibrating demo scenario for TSH stockout...")
    print()

    try:
        reset_demo_scenario()
        pretrain_prophet_model()
        ok = verify_demo_scenario()

        if ok:
            print("✅ Demo scenario ready.")
            print_demo_readiness()
        else:
            print("❌ Demo scenario has issues — check output above.")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
