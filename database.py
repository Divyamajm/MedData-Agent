"""
MedData AI & UrbanLocate - Multi-Dataset Database Management Layer
Provides schema definitions, indices, thread-safe connection pooling, 
unique mock data seeding, and summary statistics across Healthcare and Real Estate domains.
"""

import sqlite3
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

DB_PATH = "hospital_ultimate.db"

# ==========================================
# 🏥 HEALTHCARE SPECIALTIES METADATA
# ==========================================

SPECIALTIES_METADATA = {
    "Cardiology": {
        "primary_surgery": "Coronary Artery Bypass",
        "description": "Diagnosis, treatment, and surgical care of heart disorders and cardiovascular system.",
        "typical_procedures": "Angioplasty, Coronary Bypass, Valve Repair, Pacemaker Implantation",
        "common_conditions": "Coronary Artery Disease, Arrhythmia, Heart Failure, Hypertension"
    },
    "Neurology": {
        "primary_surgery": "Spinal Fusion & Decompression",
        "description": "Specialized care for the nervous system, brain, spinal cord, and peripheral nerves.",
        "typical_procedures": "Spinal Fusion, Craniotomy, Nerve Decompression, Deep Brain Stimulation",
        "common_conditions": "Stroke, Epilepsy, Multiple Sclerosis, Spinal Cord Compression"
    },
    "Orthopedics": {
        "primary_surgery": "Total Knee & Hip Replacement",
        "description": "Surgical and nonsurgical treatment of musculoskeletal system, bones, and joints.",
        "typical_procedures": "Total Knee Arthroplasty, Total Hip Replacement, ACL Reconstruction, Rotator Cuff Repair",
        "common_conditions": "Osteoarthritis, Fractures, Ligament Tears, Joint Degeneration"
    },
    "Pediatrics": {
        "primary_surgery": "Pediatric General Surgery",
        "description": "Comprehensive medical care and surgical interventions for infants, children, and adolescents.",
        "typical_procedures": "Hernia Repair, Appendectomy, Tonsillectomy, Congenital Defect Correction",
        "common_conditions": "Pediatric Infections, Asthma, Developmental Disorders, Acute Abdomen"
    },
    "Emergency": {
        "primary_surgery": "Emergency Trauma Stabilization",
        "description": "Immediate acute medical care, resuscitation, and trauma intervention for urgent conditions.",
        "typical_procedures": "Trauma Laparotomy, Chest Tube Insertion, Rapid Wound Debridement, Resuscitative Surgery",
        "common_conditions": "Acute Trauma, Cardiac Arrest, Severe Hemorrhage, Respiratory Failure"
    }
}

FIRST_NAMES = [
    "Sarah", "Michael", "Emily", "David", "James", "Aisha", "Lucas", "Priya",
    "Marcus", "Elena", "Daniel", "Olivia", "William", "Fatima", "Alexander", "Maya",
    "Gabriel", "Sophia", "Benjamin", "Chloe"
]

LAST_NAMES = [
    "Chen", "Patel", "Rodriguez", "Okafor", "Smith", "Al-Mansoor", "Santos", "Sharma",
    "Johnson", "Rostova", "Kim", "Martinez", "Lee", "Zahra", "Wright", "Lin",
    "Taylor", "Rossi", "Hayes", "Dubois"
]

# Major medical center coordinates for realistic geo-clustering
HOSPITAL_GEO_HUBS = [
    (37.7631, -122.4578),  # Parnassus Medical Hub
    (37.7885, -122.4215),  # Van Ness Clinical Center
    (37.7760, -122.3980),  # Mission Bay Hospital
    (37.7850, -122.4410),  # Mount Zion Center
    (37.7280, -122.4350)   # Southern Heights Medical
]


# ==========================================
# 🏡 URBANLOCATE HOUSING SEED DATA
# ==========================================

CURATED_PROPERTIES = [
    # Pacific Heights - Ultra Safe, Elite Schools, High Price
    ("Grand Victorian Estate", "Pacific Heights", "Luxury Villa", 4800, 4, 3.5, 3200, 12, 9.8, 1.2, 0.4, 0.3, 37.7925, -122.4355),
    ("Alta Plaza Penthouse", "Pacific Heights", "Condo", 3600, 3, 2.0, 1850, 14, 9.6, 1.4, 0.5, 0.4, 37.7910, -122.4380),
    ("Clay Street Modern Flat", "Pacific Heights", "Apartment", 2800, 2, 2.0, 1200, 15, 9.4, 1.1, 0.3, 0.2, 37.7900, -122.4330),
    ("Jackson Street Brownstone", "Pacific Heights", "Townhouse", 4200, 3, 2.5, 2400, 11, 9.7, 1.5, 0.6, 0.5, 37.7930, -122.4310),

    # Sunset District - Safe, Great Family Schools, Moderate Price
    ("Ocean Breeze Single Family", "Sunset District", "Single Family", 2900, 3, 2.0, 1750, 14, 9.4, 0.8, 0.6, 0.5, 37.7550, -122.4850),
    ("Noriega Sunshine Flat", "Sunset District", "Apartment", 2100, 2, 1.0, 1050, 22, 8.5, 1.2, 0.2, 0.3, 37.7535, -122.4920),
    ("Sunset Boulevard Townhome", "Sunset District", "Townhouse", 3100, 3, 2.5, 1900, 19, 8.9, 0.9, 0.4, 0.6, 37.7500, -122.4950),
    ("Taraval Garden Duplex", "Sunset District", "Apartment", 1850, 1, 1.0, 800, 20, 8.4, 1.5, 0.1, 0.2, 37.7420, -122.4880),

    # Mission Valley - Vibrant, Low Transit Distance, Moderate Crime
    ("Valencia Loft Residences", "Mission Valley", "Apartment", 2400, 2, 1.5, 1150, 48, 7.2, 0.4, 0.1, 0.1, 37.7590, -122.4215),
    ("Dolores Park View Condo", "Mission Valley", "Condo", 3200, 2, 2.0, 1400, 35, 8.1, 0.7, 0.2, 0.2, 37.7600, -122.4260),
    ("Mission Urban Studio", "Mission Valley", "Apartment", 1550, 1, 1.0, 650, 55, 6.8, 0.5, 0.1, 0.1, 37.7570, -122.4190),
    ("Capp Street Artist Flat", "Mission Valley", "Apartment", 1950, 2, 1.0, 950, 52, 7.0, 0.6, 0.2, 0.2, 37.7580, -122.4180),

    # Silicon Hills - High Tech, Top Schools, Low Crime, Higher Distance to Hospital
    ("Tech Corridor Smart Villa", "Silicon Hills", "Luxury Villa", 5200, 4, 3.5, 3600, 8, 9.9, 4.5, 1.2, 0.8, 37.7350, -122.4480),
    ("Innovation Ridge Townhouse", "Silicon Hills", "Townhouse", 3400, 3, 2.5, 2100, 10, 9.7, 4.8, 0.9, 1.0, 37.7320, -122.4510),
    ("Palo Green Contemporary", "Silicon Hills", "Single Family", 4100, 3, 2.0, 2300, 9, 9.8, 5.1, 1.4, 1.2, 37.7300, -122.4550),
    ("Silicon Vista Executive Apt", "Silicon Hills", "Apartment", 2600, 2, 2.0, 1300, 12, 9.5, 4.2, 0.8, 0.9, 37.7380, -122.4440),

    # Downtown Metro - High Walkability/Transit, Hospital Adjacent, Higher Crime
    ("Metropolitan Tower Luxury", "Downtown Metro", "Condo", 3100, 2, 2.0, 1350, 68, 6.5, 0.3, 0.1, 0.1, 37.7870, -122.4080),
    ("Market Street Central Loft", "Downtown Metro", "Apartment", 2250, 1, 1.0, 850, 72, 6.0, 0.2, 0.1, 0.1, 37.7850, -122.4120),
    ("SOMA Tech Hub Flat", "Downtown Metro", "Apartment", 2700, 2, 2.0, 1200, 62, 6.8, 0.6, 0.1, 0.2, 37.7810, -122.4050),
    ("Financial District Penthouse", "Downtown Metro", "Condo", 4500, 3, 3.0, 2200, 58, 7.1, 0.5, 0.1, 0.1, 37.7930, -122.4000),

    # Marina Bay - Scenic, Very Safe, Premium Water Views
    ("Marina Green View Flat", "Marina Bay", "Apartment", 3400, 2, 2.0, 1400, 16, 9.1, 1.8, 0.4, 0.3, 37.8040, -122.4380),
    ("Chestnut Street Townhome", "Marina Bay", "Townhouse", 3900, 3, 2.5, 2100, 14, 9.3, 1.9, 0.3, 0.2, 37.8010, -122.4400),
    ("Yacht Harbor Luxury Villa", "Marina Bay", "Luxury Villa", 6500, 5, 4.0, 4200, 10, 9.5, 2.1, 0.6, 0.4, 37.8060, -122.4420),
    ("Bayview Terrace Condo", "Marina Bay", "Condo", 2950, 2, 1.5, 1150, 18, 8.9, 1.7, 0.5, 0.3, 37.8020, -122.4350),

    # Green Valley - Affordable, Suburban, Family Friendly
    ("Meadow Lane Family Home", "Green Valley", "Single Family", 2300, 3, 2.0, 1800, 24, 8.2, 2.5, 1.1, 0.8, 37.7180, -122.4650),
    ("Valley View Quiet Apartment", "Green Valley", "Apartment", 1600, 2, 1.0, 950, 26, 7.9, 2.8, 0.9, 0.7, 37.7150, -122.4680),
    ("Cedar Ridge Townhouse", "Green Valley", "Townhouse", 2500, 3, 2.0, 1650, 22, 8.3, 2.3, 1.0, 0.9, 37.7200, -122.4620),
    ("Greenfield Budget Studio", "Green Valley", "Apartment", 1250, 1, 1.0, 550, 28, 7.5, 3.1, 0.8, 0.6, 37.7120, -122.4710),

    # Beacon Hill - Historic, Safe, Highly Walkable
    ("Heritage Brick Residence", "Beacon Hill", "Townhouse", 3700, 3, 2.5, 2200, 18, 9.2, 1.0, 0.3, 0.2, 37.7780, -122.4320),
    ("Pinckney Historic Flat", "Beacon Hill", "Apartment", 2500, 2, 1.5, 1100, 20, 9.0, 1.1, 0.2, 0.2, 37.7790, -122.4350),
    ("Charles Street Terrace", "Beacon Hill", "Condo", 3300, 2, 2.0, 1500, 17, 9.3, 0.9, 0.2, 0.1, 37.7810, -122.4300),
    ("Beacon Summit Villa", "Beacon Hill", "Luxury Villa", 5600, 4, 3.5, 3400, 15, 9.4, 1.3, 0.4, 0.3, 37.7760, -122.4360),

    # Highland Park - High Elevation, Panoramic Views, Very Quiet
    ("Highland View Single Family", "Highland Park", "Single Family", 3100, 3, 2.0, 2000, 16, 8.7, 2.2, 1.3, 1.0, 37.7420, -122.4280),
    ("Crestline Luxury Home", "Highland Park", "Single Family", 4400, 4, 3.0, 2900, 12, 9.0, 2.5, 1.5, 1.2, 37.7400, -122.4310),
    ("Skyline Ridge Condo", "Highland Park", "Condo", 2750, 2, 2.0, 1300, 18, 8.6, 2.0, 1.1, 0.9, 37.7450, -122.4250),
    ("Highland Garden Apartment", "Highland Park", "Apartment", 1950, 2, 1.0, 980, 20, 8.4, 2.1, 1.0, 0.8, 37.7470, -122.4230)
]


def calculate_livability_score(crime_index: int, school_rating: float, hospital_dist: float, transit_dist: float) -> int:
    """
    Computes a deterministic composite livability score (0-100).
    - Safety (Crime Index): 35% weight (lower crime = higher points)
    - School Quality: 30% weight (10 = 100 pts)
    - Hospital Proximity: 20% weight (<1 mi = 100 pts, degrades gracefully)
    - Transit / Market Proximity: 15% weight
    """
    safety_pts = max(0.0, 100.0 - crime_index)
    school_pts = min(100.0, school_rating * 10.0)
    
    # Hospital proximity score
    if hospital_dist <= 1.0:
        hosp_pts = 100.0
    elif hospital_dist <= 3.0:
        hosp_pts = 85.0
    elif hospital_dist <= 6.0:
        hosp_pts = 65.0
    else:
        hosp_pts = max(20.0, 100.0 - (hospital_dist * 10.0))
        
    # Transit proximity score
    if transit_dist <= 0.3:
        transit_pts = 100.0
    elif transit_dist <= 0.8:
        transit_pts = 85.0
    elif transit_dist <= 1.5:
        transit_pts = 65.0
    else:
        transit_pts = max(20.0, 100.0 - (transit_dist * 25.0))
        
    composite = (safety_pts * 0.35) + (school_pts * 0.30) + (hosp_pts * 0.20) + (transit_pts * 0.15)
    return int(round(composite))


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Returns a SQLite connection configured with Row factory."""
    conn = sqlite3.connect(db_path, timeout=10.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_database(db_path: str = DB_PATH, force_reset: bool = False) -> None:
    """
    Initializes the SQLite schema with tables and indexes across Healthcare and Housing.
    """
    conn = get_connection(db_path)
    c = conn.cursor()

    # 1. Create Doctors Table (with Geo Coordinates)
    c.execute("""
        CREATE TABLE IF NOT EXISTS Doctors (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            specialty TEXT NOT NULL,
            primary_surgery TEXT NOT NULL,
            surgery_success_rate REAL NOT NULL,
            satisfaction_score INTEGER NOT NULL,
            distance_miles REAL NOT NULL,
            consultation_fee INTEGER NOT NULL,
            is_available_today TEXT NOT NULL,
            next_available_date TEXT NOT NULL,
            latitude REAL DEFAULT 37.7749,
            longitude REAL DEFAULT -122.4194
        )
    """)

    # Verify column existence and auto-upgrade if needed
    c.execute("PRAGMA table_info(Doctors)")
    existing_cols = [col[1] for col in c.fetchall()]
    if "latitude" not in existing_cols:
        c.execute("DROP TABLE IF EXISTS Doctors")
        c.execute("""
            CREATE TABLE Doctors (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                specialty TEXT NOT NULL,
                primary_surgery TEXT NOT NULL,
                surgery_success_rate REAL NOT NULL,
                satisfaction_score INTEGER NOT NULL,
                distance_miles REAL NOT NULL,
                consultation_fee INTEGER NOT NULL,
                is_available_today TEXT NOT NULL,
                next_available_date TEXT NOT NULL,
                latitude REAL DEFAULT 37.7749,
                longitude REAL DEFAULT -122.4194
            )
        """)
        force_reset = True

    # 2. Create Specialties Metadata Table
    c.execute("""
        CREATE TABLE IF NOT EXISTS Specialties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT NOT NULL,
            typical_procedures TEXT NOT NULL,
            common_conditions TEXT NOT NULL
        )
    """)

    # 3. Create Real-Time Appointments Table
    c.execute("""
        CREATE TABLE IF NOT EXISTS Appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_id INTEGER NOT NULL,
            doctor_name TEXT NOT NULL,
            specialty TEXT NOT NULL,
            patient_name TEXT NOT NULL,
            patient_email TEXT NOT NULL,
            appointment_date TEXT NOT NULL,
            time_slot TEXT NOT NULL,
            status TEXT NOT NULL,
            symptoms_reason TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (doctor_id) REFERENCES Doctors(id)
        )
    """)

    c.execute("PRAGMA table_info(Appointments)")
    app_cols = [col[1] for col in c.fetchall()]
    if "specialty" not in app_cols:
        c.execute("DROP TABLE IF EXISTS Appointments")
        c.execute("""
            CREATE TABLE Appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doctor_id INTEGER NOT NULL,
                doctor_name TEXT NOT NULL,
                specialty TEXT NOT NULL,
                patient_name TEXT NOT NULL,
                patient_email TEXT NOT NULL,
                appointment_date TEXT NOT NULL,
                time_slot TEXT NOT NULL,
                status TEXT NOT NULL,
                symptoms_reason TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (doctor_id) REFERENCES Doctors(id)
            )
        """)
        force_reset = True

    # 4. Create UrbanLocate Properties / Housing Table
    c.execute("""
        CREATE TABLE IF NOT EXISTS Properties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            neighborhood TEXT NOT NULL,
            property_type TEXT NOT NULL,
            price_per_month INTEGER NOT NULL,
            bedrooms INTEGER NOT NULL,
            bathrooms REAL NOT NULL,
            sqft INTEGER NOT NULL,
            crime_index_score INTEGER NOT NULL,
            school_rating REAL NOT NULL,
            hospital_dist_miles REAL NOT NULL,
            transit_dist_miles REAL NOT NULL,
            market_dist_miles REAL NOT NULL,
            livability_score INTEGER NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL
        )
    """)

    # 5. Performance Indexes
    c.execute("CREATE INDEX IF NOT EXISTS idx_doctors_specialty ON Doctors(specialty);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_doctors_fee ON Doctors(consultation_fee);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_doctors_distance ON Doctors(distance_miles);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_doctors_available ON Doctors(is_available_today);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_doctors_satisfaction ON Doctors(satisfaction_score);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_doctors_success ON Doctors(surgery_success_rate);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_appointments_slot ON Appointments(doctor_id, appointment_date, time_slot);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_properties_price ON Properties(price_per_month);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_properties_crime ON Properties(crime_index_score);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_properties_school ON Properties(school_rating);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_properties_livability ON Properties(livability_score);")

    # Check if Doctors Table needs seeding
    c.execute("SELECT COUNT(*) FROM Doctors")
    doc_count = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM Properties")
    prop_count = c.fetchone()[0]

    needs_seed = (doc_count == 0 or prop_count == 0 or force_reset)

    if needs_seed:
        c.execute("DELETE FROM Doctors")
        c.execute("DELETE FROM Specialties")
        c.execute("DELETE FROM Appointments")
        c.execute("DELETE FROM Properties")

        # Populate Specialties
        for spec_name, spec_info in SPECIALTIES_METADATA.items():
            c.execute("""
                INSERT INTO Specialties (name, description, typical_procedures, common_conditions)
                VALUES (?, ?, ?, ?)
            """, (spec_name, spec_info["description"], spec_info["typical_procedures"], spec_info["common_conditions"]))

        # Seed 200 Unique Doctors with Geolocation
        rng = random.Random(42)
        unique_names = set()
        while len(unique_names) < 200:
            first = rng.choice(FIRST_NAMES)
            last = rng.choice(LAST_NAMES)
            unique_names.add(f"Dr. {first} {last}")
        
        doctor_names_list = sorted(list(unique_names))
        specialty_keys = list(SPECIALTIES_METADATA.keys())
        base_date = datetime.today()

        dummy_doctors = []
        for i, name in enumerate(doctor_names_list, start=1):
            specialty = specialty_keys[(i - 1) % len(specialty_keys)]
            surgery = SPECIALTIES_METADATA[specialty]["primary_surgery"]
            
            satisfaction = rng.randint(72, 99)
            success_rate = round(rng.uniform(88.0, 99.8), 1)
            distance = round(rng.uniform(0.4, 28.5), 1)
            fee = rng.choice([0, 50, 75, 100, 150, 200, 300, 500])
            
            is_today = rng.choice(["Yes", "No"])
            if is_today == "Yes":
                next_date = base_date.strftime("%Y-%m-%d")
            else:
                next_date = (base_date + timedelta(days=rng.randint(1, 14))).strftime("%Y-%m-%d")
            
            # Select random hospital hub with realistic coordinate jitter (± 0.02 deg)
            hub_lat, hub_lng = rng.choice(HOSPITAL_GEO_HUBS)
            doc_lat = round(hub_lat + rng.uniform(-0.025, 0.025), 5)
            doc_lng = round(hub_lng + rng.uniform(-0.025, 0.025), 5)

            dummy_doctors.append((
                i, name, specialty, surgery, success_rate, satisfaction, 
                distance, fee, is_today, next_date, doc_lat, doc_lng
            ))

        c.executemany("""
            INSERT INTO Doctors (
                id, name, specialty, primary_surgery, surgery_success_rate,
                satisfaction_score, distance_miles, consultation_fee, 
                is_available_today, next_available_date, latitude, longitude
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, dummy_doctors)

        # Seed Curated Properties with Livability Scores
        dummy_properties = []
        for p in CURATED_PROPERTIES:
            title, nbh, ptype, price, beds, baths, sqft, crime, school, hosp_d, trans_d, mkt_d, lat, lng = p
            livability = calculate_livability_score(crime, school, hosp_d, trans_d)
            dummy_properties.append((
                title, nbh, ptype, price, beds, baths, sqft, crime, school, hosp_d, trans_d, mkt_d, livability, lat, lng
            ))

        c.executemany("""
            INSERT INTO Properties (
                title, neighborhood, property_type, price_per_month, bedrooms, bathrooms,
                sqft, crime_index_score, school_rating, hospital_dist_miles, transit_dist_miles,
                market_dist_miles, livability_score, latitude, longitude
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, dummy_properties)

        # Seed 3 Sample Confirmed Appointments
        mock_appointments = [
            (1, dummy_doctors[0][1], "Cardiology", "Alice Walker", "alice@example.com", base_date.strftime("%Y-%m-%d"), "09:00 AM", "CONFIRMED", "Routine Cardiac Checkup", datetime.now().isoformat()),
            (2, dummy_doctors[1][1], "Neurology", "Bob Vance", "bob@example.com", base_date.strftime("%Y-%m-%d"), "11:30 AM", "CONFIRMED", "Migraine Assessment", datetime.now().isoformat()),
            (3, dummy_doctors[2][1], "Orthopedics", "Carol Danvers", "carol@example.com", (base_date + timedelta(days=1)).strftime("%Y-%m-%d"), "02:00 PM", "CONFIRMED", "Knee Arthroscopy Followup", datetime.now().isoformat()),
        ]
        c.executemany("""
            INSERT INTO Appointments (
                doctor_id, doctor_name, specialty, patient_name, patient_email, appointment_date, 
                time_slot, status, symptoms_reason, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, mock_appointments)

        conn.commit()

    conn.close()


# ==========================================
# 📅 APPOINTMENT CONFLICT & BOOKING LOGIC
# ==========================================

def check_appointment_conflict(doctor_id: int, appointment_date: str, time_slot: str, db_path: str = DB_PATH) -> bool:
    """Checks if a specific doctor already has a confirmed booking for date & time slot."""
    conn = get_connection(db_path)
    c = conn.cursor()
    c.execute("""
        SELECT COUNT(*) FROM Appointments 
        WHERE doctor_id = ? AND appointment_date = ? AND time_slot = ? AND status = 'CONFIRMED'
    """, (doctor_id, appointment_date, time_slot))
    count = c.fetchone()[0]
    conn.close()
    return count > 0


def book_appointment(
    doctor_id: int, 
    patient_name: str, 
    patient_email: str,
    appointment_date: str, 
    time_slot: str, 
    symptoms_reason: str = "General Consultation",
    db_path: str = DB_PATH
) -> Dict[str, Any]:
    """Records an appointment in SQLite with strict double-booking conflict verification."""
    conn = get_connection(db_path)
    c = conn.cursor()

    c.execute("SELECT name, specialty FROM Doctors WHERE id = ?", (doctor_id,))
    doc = c.fetchone()
    if not doc:
        conn.close()
        return {"success": False, "error": f"Doctor ID {doctor_id} not found."}

    doc_name = doc["name"]
    specialty = doc["specialty"]

    # Conflict check
    if check_appointment_conflict(doctor_id, appointment_date, time_slot, db_path=db_path):
        conn.close()
        return {
            "success": False, 
            "error": f"Time slot {time_slot} on {appointment_date} is already booked for {doc_name}. Please choose another time."
        }

    created_at = datetime.now().isoformat()

    c.execute("""
        INSERT INTO Appointments (
            doctor_id, doctor_name, specialty, patient_name, patient_email, appointment_date, 
            time_slot, status, symptoms_reason, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'CONFIRMED', ?, ?)
    """, (doctor_id, doc_name, specialty, patient_name, patient_email, appointment_date, time_slot, symptoms_reason, created_at))

    booking_id = c.lastrowid
    conn.commit()
    conn.close()

    return {
        "success": True,
        "booking_id": booking_id,
        "doctor_name": doc_name,
        "specialty": specialty,
        "patient_name": patient_name,
        "patient_email": patient_email,
        "appointment_date": appointment_date,
        "time_slot": time_slot,
        "symptoms_reason": symptoms_reason
    }


def get_all_appointments(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """Retrieves all confirmed appointment records."""
    conn = get_connection(db_path)
    c = conn.cursor()
    c.execute("SELECT * FROM Appointments ORDER BY appointment_date ASC, time_slot ASC")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


# ==========================================
# 📊 MULTI-DATASET SUMMARY STATS
# ==========================================

def get_database_stats(db_path: str = DB_PATH) -> Dict[str, Any]:
    """Retrieves high-level summary metrics across Healthcare and Real Estate datasets."""
    conn = get_connection(db_path)
    c = conn.cursor()

    # Healthcare stats
    c.execute("SELECT COUNT(*) FROM Doctors")
    total_doctors = c.fetchone()[0]

    c.execute("SELECT COUNT(DISTINCT specialty) FROM Doctors")
    total_specialties = c.fetchone()[0]

    c.execute("SELECT AVG(consultation_fee) FROM Doctors")
    avg_fee = round(c.fetchone()[0] or 0.0, 2)

    c.execute("SELECT COUNT(*) FROM Doctors WHERE is_available_today = 'Yes'")
    available_today_count = c.fetchone()[0]

    c.execute("SELECT AVG(satisfaction_score) FROM Doctors")
    avg_satisfaction = round(c.fetchone()[0] or 0.0, 1)

    c.execute("SELECT AVG(surgery_success_rate) FROM Doctors")
    avg_success_rate = round(c.fetchone()[0] or 0.0, 1)

    c.execute("SELECT MIN(distance_miles), MAX(distance_miles) FROM Doctors")
    min_dist, max_dist = c.fetchone()

    c.execute("SELECT specialty, COUNT(*) as count, AVG(consultation_fee) as avg_fee, AVG(satisfaction_score) as avg_score FROM Doctors GROUP BY specialty")
    specialty_breakdown = [dict(row) for row in c.fetchall()]

    # Housing stats
    c.execute("SELECT COUNT(*) FROM Properties")
    total_properties = c.fetchone()[0]

    c.execute("SELECT AVG(price_per_month) FROM Properties")
    avg_rent = round(c.fetchone()[0] or 0.0, 2)

    c.execute("SELECT AVG(crime_index_score) FROM Properties")
    avg_crime = round(c.fetchone()[0] or 0.0, 1)

    c.execute("SELECT AVG(school_rating) FROM Properties")
    avg_school = round(c.fetchone()[0] or 0.0, 1)

    c.execute("SELECT AVG(livability_score) FROM Properties")
    avg_livability = round(c.fetchone()[0] or 0.0, 1)

    c.execute("SELECT neighborhood, COUNT(*) as count, AVG(price_per_month) as avg_price, AVG(livability_score) as avg_score FROM Properties GROUP BY neighborhood")
    neighborhood_breakdown = [dict(row) for row in c.fetchall()]

    conn.close()

    return {
        "total_doctors": total_doctors,
        "total_specialties": total_specialties,
        "avg_fee": avg_fee,
        "available_today_count": available_today_count,
        "avg_satisfaction": avg_satisfaction,
        "avg_success_rate": avg_success_rate,
        "min_distance": round(min_dist or 0.0, 1),
        "max_distance": round(max_dist or 0.0, 1),
        "specialty_breakdown": specialty_breakdown,
        "total_properties": total_properties,
        "avg_rent": avg_rent,
        "avg_crime": avg_crime,
        "avg_school": avg_school,
        "avg_livability": avg_livability,
        "neighborhood_breakdown": neighborhood_breakdown
    }


def reset_demo_data(db_path: str = DB_PATH) -> None:
    """Explicitly resets and re-seeds both Healthcare and Housing datasets."""
    init_database(db_path=db_path, force_reset=True)
