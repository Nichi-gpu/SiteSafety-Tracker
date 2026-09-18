import sqlite3
import bcrypt
from database import get_db, init_db

def seed():
    print('[*] Seeding SiteSafety database...')
    init_db()
    conn = get_db()
    
    # ── 1. Default Users ────────────────────────────────────
    users = [
        ('manager', 'manager@sitesafety.com', bcrypt.hashpw('password123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'), 'manager', 'SiteSafety Corp'),
        ('andrei', 'andrei@sitesafety.com', bcrypt.hashpw('password123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'), 'staff', 'SiteSafety Corp'),
        ('admin', 'admin@sitesafety.com', bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'), 'manager', 'SiteSafety Global')
    ]
    with conn:
        for u in users:
            existing = conn.execute('SELECT id FROM users WHERE email = ?', (u[1],)).fetchone()
            if existing:
                conn.execute('''
                    UPDATE users SET username = ?, role = ?, company = ? WHERE email = ?
                ''', (u[0], u[3], u[4], u[1]))
            else:
                conn.execute('''
                    INSERT INTO users (username, email, password, role, company, signup_time)
                    VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'))
                ''', (u[0], u[1], u[2], u[3], u[4]))
    print('  [OK] Users seeded with usernames & timestamps')

    # Seed initial audit log entry
    with conn:
        conn.execute('''
            INSERT INTO login_logs (username, email, role, action, status, timestamp, details)
            VALUES ('system', 'system@sitesafety.com', 'manager', 'SYSTEM_INIT', 'SUCCESS', datetime('now', 'localtime'), 'Database initialized & seeded')
        ''')

    # ── 2. Hazards (Pending + Resolved) ─────────────────────
    hazards = [
        # Pending
        ('ABC-2026-0315-01','Site Alpha - North Wing','Electrical Hazard','03-15-26','09:30 AM','Critical','Pending','Exposed high-voltage conduit near rain gutter.','Michael Vance','Lead Safety Officer','+1 (555) 201-4491','Security'),
        ('ABC-2026-0315-02','Site Beta - Crane Zone','Structural Defect','03-15-26','10:15 AM','High','Pending','Loose anchor pins discovered on primary mobile crane counterweight.','Elena Gomez','First Aid Coordinator','+1 (555) 431-7705','Medical'),
        ('ABC-2026-0315-03','Site Gamma - Chem Storage','Chemical Spillage','03-15-26','11:00 AM','Urgent','Pending','Chemical solvent drum seal failure causing strong fumes.','Dr. Robert Hayes','Chief Medical Officer','+1 (555) 388-1200','Medical'),
        ('ABC-2026-0315-04','Site Delta - Excavation A','Trench Collapse Risk','03-15-26','01:20 PM','Critical','Pending','Shifting substrate on south trench wall after rain.','Marcus Sterling','Hazard Mitigation Chief','+1 (555) 883-6629','Emergency'),
        ('ABC-2026-0315-05','Site Epsilon - Level 4','Missing Guardrail','03-15-26','02:45 PM','High','Pending','Edge protection removed during dry-wall staging and not replaced.','Sarah Lin','Emergency Response Lead','+1 (555) 911-3042','Emergency'),
        ('ABC-2026-0315-06','Site Zeta - Main Hallway','Water Accumulation','03-15-26','04:10 PM','Medium','Pending','Overhead AC condensate drip creating slip hazard.','Jennifer Ward','Compliance Supervisor','+1 (555) 319-5504','Administration'),
        ('ABC-2026-0316-07','Site Alpha - West Tower','Exposed High-Voltage','03-16-26','08:45 AM','Critical','Pending','High voltage junction box opened by sub-contractor.','David Kim','Perimeter Security','+1 (555) 670-8821','Security'),
        ('ABC-2026-0316-08','Site Beta - Loading Bay','Faulty Scaffold Anchor','03-16-26','09:50 AM','High','Pending','Connector clamp fractured on exterior scaffold column.','Angela Brooks','Site Safety Administrator','+1 (555) 472-9918','Administration'),
        ('ABC-2026-0316-09','Site Gamma - Roof Edge','Loose HVAC Ducting','03-16-26','11:30 AM','Medium','Pending','High wind gusts detached corner sheet metal.','Michael Vance','Lead Safety Officer','+1 (555) 201-4491','Security'),
        ('ABC-2026-0316-10','Site Delta - Workshop B','Gas Cylinder Leak','03-16-26','01:15 PM','Critical','Pending','Faulty regulator on acetylene welding tank.','Marcus Sterling','Hazard Mitigation Chief','+1 (555) 883-6629','Emergency'),
        ('ABC-2026-0316-11','Site Epsilon - Stairwell 2','Emergency Light Out','03-16-26','03:00 PM','Medium','Pending','Battery backup module burned out.','Elena Gomez','First Aid Coordinator','+1 (555) 431-7705','Medical'),
        ('ABC-2026-0316-12','Site Zeta - South Ramp','Oil Spill on Ramp','03-16-26','04:40 PM','High','Pending','Forklift hydraulic line ruptured during transit.','Sarah Lin','Emergency Response Lead','+1 (555) 911-3042','Emergency'),
        # Resolved
        ('ABC-2026-0310-01','Site Alpha - North Wing','Exposed Wiring','03-10-26','09:30 AM','Medium','Resolved','Chafed wire conduit replaced with industrial flex casing.','Sarah Lin','Emergency Lead','+1 (555) 911-3042','Emergency'),
        ('ABC-2026-0310-02','Site Beta - Crane Zone','Scaffold Clamp Failure','03-10-26','11:15 AM','High','Resolved','Heavy-duty steel coupler installed and tested.','Michael Vance','Lead Safety Officer','+1 (555) 201-4491','Security'),
        ('ABC-2026-0310-03','Site Gamma - Chem Storage','Acid Spillage','03-10-26','01:45 PM','Critical','Resolved','Neutralizing agent applied and hazardous waste disposed.','Dr. Hayes','Chief Medical Officer','+1 (555) 388-1200','Medical'),
        ('ABC-2026-0310-04','Site Delta - Substation 4','Circuit Breaker Trip','03-10-26','03:10 PM','Medium','Resolved','Overload breaker replaced and re-calibrated.','Angela Brooks','Administrator','+1 (555) 472-9918','Administration'),
        ('ABC-2026-0310-05','Site Epsilon - Level 2','Oil On Walkway','03-10-26','04:25 PM','Low','Resolved','Industrial degreaser scrubbed and non-slip mats laid.','Elena Gomez','Coordinator','+1 (555) 431-7705','Medical'),
        ('ABC-2026-0310-06','Site Zeta - Loading Gate','Damaged Safety Net','03-10-26','05:00 PM','High','Resolved','New high-tensile safety netting fastened.','David Kim','Perimeter Guard','+1 (555) 670-8821','Security'),
        ('ABC-2026-0305-07','Site Alpha - West Tower','Gas Pressure Anomaly','03-05-26','08:45 AM','Critical','Resolved','Pressure relief valve cleaned and certified.','Marcus Sterling','Chief','+1 (555) 883-6629','Emergency'),
        ('ABC-2026-0305-08','Site Beta - Workshop 1','Grinder Guard Detached','03-05-26','10:20 AM','Medium','Resolved','Steel guard re-bolted with torque wrench.','Jennifer Ward','Supervisor','+1 (555) 319-5504','Administration'),
        ('ABC-2026-0305-09','Site Gamma - Roof Edge','Harness Anchor Loose','03-05-26','01:30 PM','High','Resolved','Chemical anchor bolts installed and load pull-tested.','Sarah Lin','Lead','+1 (555) 911-3042','Emergency'),
    ]
    with conn:
        conn.executemany('''
            INSERT OR IGNORE INTO hazards
            (ticket, location, category, date, time, urgency, status, cause,
            reporter_name, reporter_position, reporter_phone, reporter_dept)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', hazards)
    print(f'  [OK] {len(hazards)} hazards seeded')

    # ── 3. Inspections ──────────────────────────────────────
    inspections = [
        ('Tower Crane Integrity Check','Site A - Sector 3','Marcus Vance','09-18-26','09:00 AM','Scheduled'),
        ('Scaffolding Safety Audit','Site B - Main Gate','Elena Gomez','09-18-26','11:30 AM','Scheduled'),
        ('Electrical Rig Wiring Review','Site C - Generator 2','David Kim','09-19-26','01:15 PM','Scheduled'),
        ('Excavation Shoring Inspection','Site A - Trench 4','Carlos Mendez','09-19-26','03:45 PM','Scheduled'),
        ('PPE Compliance Patrol','Site B - Warehouse 2','Sarah Lin','09-20-26','10:00 AM','Scheduled'),
        ('Chemical Storage Assessment','Site C - Hazmat Bay','Dr. Hayes','09-20-26','02:00 PM','Scheduled'),
        ('Fire Suppression Pipeline Test','Site A - Sublevel 1','Angela Brooks','09-21-26','08:30 AM','Scheduled'),
        ('Fall Arrest Anchor Audit','Site B - Roof Deck','Marcus Sterling','09-21-26','10:45 AM','Scheduled'),
        ('Concrete Pour Formwork Check','Site C - Block D','Jennifer Ward','09-22-26','01:00 PM','Scheduled'),
        ('Heavy Plant Machinery Inspection','Site A - Depot 1','Michael Vance','09-22-26','03:30 PM','Scheduled'),
        ('First Aid Station Supply Audit','Site B - Clinic Area','Elena Gomez','09-23-26','09:15 AM','Scheduled'),
        ('Perimeter Barrier Stability Review','Site C - Boundary North','David Kim','09-23-26','11:00 AM','Scheduled'),
        ('Emergency Egress Pathway Check','Site A - Sector 1','Sarah Lin','09-24-26','09:00 AM','Scheduled'),
        ('Ventilation & Air Quality Review','Site B - Subterranean','Dr. Hayes','09-24-26','11:30 AM','Scheduled'),
        ('Hydraulic Lift Systems Testing','Site C - Sector 2','Carlos Mendez','09-25-26','01:45 PM','Scheduled'),
        ('Ground Resistance & Earthing Check','Site A - Transformer 1','David Kim','09-25-26','03:15 PM','Scheduled'),
        ('Confined Space Entry Signoff','Site B - Tank 3','Marcus Sterling','09-26-26','10:00 AM','Scheduled'),
        ('Hazardous Waste Manifest Audit','Site C - Disposal Area','Angela Brooks','09-26-26','02:30 PM','Scheduled'),
    ]
    with conn:
        conn.executemany('''
            INSERT OR IGNORE INTO inspections (title, location, inspector, date, time, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', inspections)
    print(f'  [OK] {len(inspections)} inspections seeded')

    # ── 4. Notifications ────────────────────────────────────
    notifs = [
        ('New Safety Protocol Published for Q3', '10 mins ago', 1),
        ('Scaffolding Audit Inspection Completed', '1 hour ago', 1),
        ('Hazard Ticket ABC-2026-0310-01 Marked as Resolved', 'Yesterday', 0)
    ]
    with conn:
        conn.executemany('''
            INSERT OR IGNORE INTO notifications (title, time_label, unread)
            VALUES (?, ?, ?)
        ''', notifs)
    print('  [OK] Notifications seeded')

    # ── 5. Contacts ─────────────────────────────────────────
    contacts = [
        ('Michael Vance','Lead Safety Officer','+1 (555) 201-4491','Security','Active'),
        ('Elena Gomez','First Aid Coordinator','+1 (555) 431-7705','Medical','Active'),
        ('Dr. Robert Hayes','Chief Medical Officer','+1 (555) 388-1200','Medical','Active'),
        ('Marcus Sterling','Hazard Mitigation Chief','+1 (555) 883-6629','Emergency','Active'),
        ('Sarah Lin','Emergency Response Lead','+1 (555) 911-3042','Emergency','Active'),
        ('Jennifer Ward','Compliance Supervisor','+1 (555) 319-5504','Administration','Active'),
        ('David Kim','Perimeter Security','+1 (555) 670-8821','Security','Active'),
        ('Angela Brooks','Site Safety Administrator','+1 (555) 472-9918','Administration','Active'),
    ]
    with conn:
        conn.executemany('''
            INSERT OR IGNORE INTO contacts (name, position, phone, department, status)
            VALUES (?, ?, ?, ?, ?)
        ''', contacts)
    print(f'  [OK] {len(contacts)} contacts seeded')

    conn.close()
    print('[OK] Database successfully seeded with users, logins, hazards, and inspections!')

if __name__ == '__main__':
    seed()
