import sys
from pathlib import Path

# Add project root to path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.database.session import engine, SessionLocal
from backend.database.base import Base
import backend.database.models  # ensures all models register with Base.metadata

from backend.database.models import Role, Department, User
from backend.permissions import ROLE_PERMISSIONS
from backend.auth import hash_password

# Demo seed data: (username, password, role_name, full_name, email, dept_name | None)
DEMO_USERS = [
    ("admin",      "admin123",      "Admin",            "Head Office Admin",    "admin@regintel.ai",      None),
    ("superadmin", "super123",      "Super Admin",      "Super Administrator",  "superadmin@regintel.ai", None),
    ("compliance", "compliance123", "Compliance Head",  "Compliance Head",      "compliance@bank.in",     "Compliance"),
    ("risk",       "risk123",       "Risk Head",        "Risk Manager",         "risk@bank.in",           "Risk"),
    ("audit",      "audit123",      "Audit Head",       "Internal Audit Lead",  "audit@bank.in",          "Internal Audit"),
    ("it",         "it123",         "IT Head",          "IT Security Manager",  "it@bank.in",             "IT"),
    ("operations", "ops123",        "Operations Head",  "Operations Manager",   "ops@bank.in",            "Operations"),
    ("viewer",     "viewer123",     "Viewer",           "Read-Only Viewer",     "viewer@bank.in",         None),
]

DEPARTMENTS = [
    ("Compliance",      "Central Compliance Office"),
    ("IT",              "Information Technology"),
    ("Risk",            "Risk Management"),
    ("Internal Audit",  "Internal Audit Department"),
    ("Operations",      "Operations Department"),
    ("Treasury",        "Treasury Department"),
    ("Legal",           "Legal & Regulatory Affairs"),
]

def init_db():
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created.")

    db = SessionLocal()
    try:
        # 1. Seed roles with proper permissions from ROLE_PERMISSIONS
        existing_roles = {r.role_name for r in db.query(Role).all()}
        for role_name, perms in ROLE_PERMISSIONS.items():
            if role_name not in existing_roles:
                db.add(Role(role_name=role_name, permissions=perms))
                print(f"  [+] Role: {role_name}")
            else:
                # Update permissions on existing roles so they stay in sync
                role = db.query(Role).filter_by(role_name=role_name).first()
                role.permissions = perms

        db.flush()

        # 2. Seed departments
        existing_depts = {d.name for d in db.query(Department).all()}
        for dept_name, dept_desc in DEPARTMENTS:
            if dept_name not in existing_depts:
                db.add(Department(name=dept_name, description=dept_desc))
                print(f"  [+] Department: {dept_name}")

        db.flush()

        # 3. Seed demo users
        existing_users = {u.username for u in db.query(User).all()}
        for username, password, role_name, full_name, email, dept_name in DEMO_USERS:
            if username not in existing_users:
                role   = db.query(Role).filter_by(role_name=role_name).first()
                dept   = db.query(Department).filter_by(name=dept_name).first() if dept_name else None
                pw_hash = hash_password(password)
                db.add(User(
                    username=username,
                    email=email,
                    full_name=full_name,
                    password_hash=pw_hash,
                    role_id=role.id if role else None,
                    department_id=dept.id if dept else None,
                ))
                print(f"  [+] User: {username} ({role_name})")

        db.commit()
        print("Seeding complete.")
    except Exception as e:
        db.rollback()
        print(f"Seeding error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
