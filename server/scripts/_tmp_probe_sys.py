import os
os.environ.setdefault("MONGO_DATABASE", "hoteldata_hub")
from src.app.security.permissions import SYSTEM_SCOPE_CODES, GUEST_PERMISSION_CODES
from src.database.connection import get_database
import importlib.util
db = get_database()
spec = importlib.util.spec_from_file_location("seed_audit", "/app/scripts/init_security_model_ga03.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
print("=== SEED CANONICO: system/guest codes por rol global ===")
for role, codes in m.ROLE_PERMISSION_CODES.items():
    sys_c = sorted(set(codes) & SYSTEM_SCOPE_CODES)
    gst_c = sorted(set(codes) & GUEST_PERMISSION_CODES)
    if sys_c or gst_c:
        print(f"  {role}: system={sys_c} guest={gst_c}")
print("=== DEV roles collection: system/guest codes por rol ===")
for r in db.roles.find({}, {"role_name": 1, "permissions": 1}):
    codes = r.get("permissions", [])
    sys_c = sorted(set(codes) & SYSTEM_SCOPE_CODES)
    gst_c = sorted(set(codes) & GUEST_PERMISSION_CODES)
    if sys_c or gst_c:
        print(f"  {r.get('role_name')}: system={sys_c} guest={gst_c}")
