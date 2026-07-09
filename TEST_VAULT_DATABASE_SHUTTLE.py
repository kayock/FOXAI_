from pathlib import Path
from core_v10.database_shuttle import DatabaseShuttle
from core_v10.vault import Vault

root = Path(__file__).resolve().parent

db = DatabaseShuttle(root)
print("FOXAI CM v2.4 - USS Database Shuttle")
print("====================================")
print()

print("Health:")
print(db.health())
print()

vault = Vault(root)
mission = vault.log_mission(
    title="Vault smoke test",
    request="Confirm FOXAI.db can record missions through controlled APIs.",
    professor="Mission Control",
    mission_type="database_smoke_test",
    department="Engineering",
)
vault.log_step(
    mission_id=mission["mission_id"],
    step_number=1,
    capability="mission_history",
    shuttle_key="database",
    shuttle_callsign="USS Database Shuttle",
    status="complete",
    details="Created mission and step through Vault service.",
)
vault.log_event(
    mission_id=mission["mission_id"],
    level="INFO",
    source="MissionBus",
    message="Vault smoke test complete.",
)

print("Logged mission:", mission)
print()
print("Recent missions:")
for item in vault.list_missions(limit=5)["missions"]:
    print(f"- #{item['id']} {item['title']} [{item['status']}]")
print()
print("Vault path:", vault.vault_root)
print("Database:", vault.db_path)
