#!/usr/bin/env python3
"""Vyre — Database seed script. Run after docker-compose up."""
import os, sys, uuid
import psycopg2
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://vyre:vyre_secret@localhost:5432/vyre")
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

def conn(): return psycopg2.connect(DATABASE_URL)

def create_admin(db, email, password, name):
    cur = db.cursor()
    cur.execute("SELECT id FROM users WHERE email=%s", (email,))
    if cur.fetchone(): print(f"  Admin {email} already exists"); cur.close(); return
    cur.execute("INSERT INTO users (id,email,full_name,role,password_hash,is_active) VALUES (%s,%s,%s,'super_admin',%s,true)",
                (str(uuid.uuid4()), email, name, pwd.hash(password)))
    db.commit(); print(f"  Created admin: {email}"); cur.close()

def create_demo(db):
    cur = db.cursor()
    cur.execute("SELECT id FROM organisations WHERE name='Acme Retail Ltd'")
    if cur.fetchone(): print("  Demo org exists"); cur.close(); return
    oid = str(uuid.uuid4())
    cur.execute("INSERT INTO organisations (id,name,website,vertical,tier) VALUES (%s,'Acme Retail Ltd','acmeretail.com','retail','core')", (oid,))
    cur.execute("INSERT INTO users (id,org_id,email,full_name,role,password_hash,is_active) VALUES (%s,%s,'james@acmeretail.com','James Mitchell','client_admin',%s,true)",
                (str(uuid.uuid4()), oid, pwd.hash("demo1234")))
    db.commit(); print("  Created demo: james@acmeretail.com / demo1234"); cur.close()

def main():
    print("\nVyre Setup"); print("="*40)
    email = os.getenv("ADMIN_EMAIL", "admin@vyre.io")
    password = os.getenv("ADMIN_PASSWORD", "Admin1234!")
    name = os.getenv("ADMIN_NAME", "Operator Admin")
    try:
        db = conn(); print("Database connected")
    except Exception as e:
        print(f"Connection failed: {e}\nRun: docker-compose up -d db"); sys.exit(1)
    print("\nCreating admin..."); create_admin(db, email, password, name)
    print("Creating demo org..."); create_demo(db)
    cur = db.cursor(); cur.execute("SELECT COUNT(*) FROM benchmark_config"); n=cur.fetchone()[0]; cur.close()
    print(f"Benchmarks: {n} entries loaded")
    db.close()
    print(f"\n{'='*40}\nDone!\n\nAdmin:  {email} / {password}")
    print("Client: james@acmeretail.com / demo1234")
    print("URL:    http://localhost:3000\n")

if __name__=="__main__": main()
