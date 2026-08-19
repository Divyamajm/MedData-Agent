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
    "Ananya", "Rajesh", "Priya", "Vikram", "Neha", "Arjun", "Rohan", "Sneha",
    "Karan", "Pooja", "Aditya", "Divya", "Suresh", "Meera", "Ramesh", "Deepak",
    "Sunita", "Amit", "Kavita", "Sanjay"
]

LAST_NAMES = [
    "Sharma", "Iyer", "Patel", "Verma", "Reddy", "Nair", "Malhotra", "Banerjee",
    "Gupta", "Kulkarni", "Deshmukh", "Singhal", "Choudhury", "Mehta", "Bhatia", "Chatterjee",
    "Menon", "Joshi", "Kapoor", "Rao"
]

# Major Indian Medical Center Hubs for realistic geo-clustering (Bengaluru, Mumbai, Delhi, Hyderabad, Chennai)
HOSPITAL_GEO_HUBS = [
    (12.9592, 77.6534),  # Manipal Hospital, HAL Airport Rd, Bengaluru
    (12.9716, 77.5946),  # Apollo Hospital, Sheshadripuram, Bengaluru
    (19.1314, 72.8256),  # Kokilaben Dhirubhai Ambani Hospital, Mumbai
    (28.5273, 77.2140),  # Max Super Speciality Hospital, Saket, Delhi
    (28.4595, 77.0725),  # Fortis Memorial Research Institute, Gurugram
    (17.4243, 78.4116),  # Apollo Health City, Jubilee Hills, Hyderabad
    (13.0604, 80.2496)   # Apollo Hospitals, Greams Road, Chennai
]


# ==========================================
# 🏡 URBANLOCATE INDIA - REAL ESTATE SEED DATA
# ==========================================

CURATED_PROPERTIES = [
    # -------------------------------------------------------------
    # 🏙️ 1. BENGALURU (10 Properties - Tech Capital, Silicon Valley)
    # -------------------------------------------------------------
    ("100ft Road Luxury Penthouse", "Bengaluru", "Indiranagar", "Condo", 95000, 3, 3.0, 2400, 12, 9.8, 1.2, 0.4, 0.3, 12.9784, 77.6408),
    ("Defence Colony Independent Villa", "Bengaluru", "Indiranagar", "Luxury Villa", 160000, 4, 4.0, 3800, 9, 9.9, 1.5, 0.6, 0.4, 12.9750, 77.6450),
    ("Koramangala 4th Block Duplex", "Bengaluru", "Koramangala", "Single Family", 82000, 3, 3.0, 2200, 14, 9.6, 0.9, 0.5, 0.4, 12.9340, 77.6280),
    ("Sony World Signal 3BHK Flat", "Bengaluru", "Koramangala", "Apartment", 48000, 3, 2.0, 1550, 15, 9.4, 1.2, 0.3, 0.2, 12.9355, 77.6240),
    ("HSR Sector 2 Family Home", "Bengaluru", "HSR Layout", "Single Family", 55000, 3, 2.5, 2100, 11, 9.7, 1.8, 0.8, 0.5, 12.9120, 77.6450),
    ("Prestige Tech Vista 3BHK", "Bengaluru", "Whitefield", "Condo", 48000, 3, 2.5, 1750, 16, 9.3, 1.1, 0.4, 0.5, 12.9698, 77.7499),
    ("Green Glen Layout Lakeview 2BHK", "Bengaluru", "Bellandur", "Apartment", 34000, 2, 2.0, 1200, 18, 9.1, 1.4, 0.7, 0.3, 12.9260, 77.6762),
    ("JP Nagar 7th Phase Garden Villa", "Bengaluru", "JP Nagar", "Luxury Villa", 115000, 4, 3.5, 3200, 10, 9.7, 1.6, 0.9, 0.6, 12.9063, 77.5857),
    ("Margosa Road Heritage Floor", "Bengaluru", "Malleshwaram", "Townhouse", 52000, 3, 2.0, 1650, 13, 9.5, 0.8, 0.4, 0.2, 13.0031, 77.5643),
    ("Manyata Tech Park Residency", "Bengaluru", "Hebbal", "Apartment", 38000, 2, 2.0, 1350, 17, 9.2, 1.5, 0.5, 0.4, 13.0358, 77.5970),

    # -------------------------------------------------------------
    # 🏙️ 2. MUMBAI (10 Properties - Financial Capital, Coastal Metros)
    # -------------------------------------------------------------
    ("Carter Road Sea-Facing Flat", "Mumbai", "Bandra West", "Apartment", 150000, 3, 3.0, 1800, 12, 9.7, 0.9, 0.5, 0.3, 19.0596, 72.8295),
    ("Pali Hill Heritage Villa", "Mumbai", "Bandra West", "Luxury Villa", 280000, 5, 5.0, 5000, 6, 9.9, 1.2, 0.7, 0.4, 19.0680, 72.8310),
    ("Hiranandani Gardens Heritage", "Mumbai", "Powai", "Condo", 75000, 3, 2.5, 1650, 14, 9.6, 1.0, 0.5, 0.3, 19.1190, 72.9050),
    ("Juhu Tara Beachfront 4BHK", "Mumbai", "Juhu", "Luxury Villa", 240000, 4, 4.0, 4200, 8, 9.8, 1.3, 0.8, 0.5, 19.1075, 72.8263),
    ("Lokhandwala Complex Luxury Flat", "Mumbai", "Andheri West", "Apartment", 68000, 3, 2.5, 1600, 16, 9.4, 0.8, 0.3, 0.2, 19.1363, 72.8277),
    ("Sea Face Promenade Penthouse", "Mumbai", "Worli", "Condo", 210000, 4, 4.0, 3800, 9, 9.8, 1.1, 0.6, 0.4, 19.0178, 72.8178),
    ("One Avighna Park High-Rise", "Mumbai", "Lower Parel", "Condo", 125000, 3, 3.0, 2100, 13, 9.5, 0.7, 0.2, 0.2, 18.9953, 72.8302),
    ("Shivaji Park Heritage 2BHK", "Mumbai", "Dadar", "Apartment", 58000, 2, 2.0, 1100, 11, 9.6, 0.6, 0.3, 0.2, 19.0178, 72.8478),
    ("Hiranandani Estate Rodas Flat", "Mumbai", "Thane West", "Apartment", 38000, 2, 2.0, 1250, 15, 9.3, 1.4, 0.7, 0.4, 19.2183, 72.9781),
    ("Diamond Garden Premium 3BHK", "Mumbai", "Chembur", "Apartment", 62000, 3, 2.5, 1500, 14, 9.4, 1.0, 0.4, 0.3, 19.0522, 72.8994),

    # -------------------------------------------------------------
    # 🏙️ 3. DELHI-NCR (10 Properties - National Capital & Corporate Hubs)
    # -------------------------------------------------------------
    ("DLF The Aralias Penthouse", "Delhi-NCR", "Cyber City", "Condo", 165000, 4, 4.0, 4500, 14, 9.7, 0.8, 0.3, 0.3, 28.4750, 77.0900),
    ("Golf Course Road Smart 3BHK", "Delhi-NCR", "Cyber City", "Apartment", 65000, 3, 2.5, 1950, 16, 9.5, 1.0, 0.4, 0.4, 28.4680, 77.0980),
    ("Cyber Hub Walkable 2BHK", "Delhi-NCR", "Cyber City", "Apartment", 42000, 2, 2.0, 1250, 20, 9.2, 0.6, 0.2, 0.2, 28.4900, 77.0880),
    ("GK-1 M-Block Luxury Floor", "Delhi-NCR", "Greater Kailash", "Townhouse", 85000, 3, 3.0, 2200, 18, 9.6, 0.7, 0.3, 0.2, 28.5520, 77.2380),
    ("Hauz Khas Enclave Designer Flat", "Delhi-NCR", "Hauz Khas", "Apartment", 78000, 3, 2.5, 2000, 15, 9.7, 0.9, 0.4, 0.3, 28.5494, 77.2001),
    ("Vasant Kunj Sector C Green Villa", "Delhi-NCR", "Vasant Kunj", "Luxury Villa", 130000, 4, 3.5, 3600, 12, 9.8, 1.2, 0.8, 0.5, 28.5284, 77.1554),
    ("South Extension Part 2 Floor", "Delhi-NCR", "South Extension", "Townhouse", 68000, 3, 2.5, 1800, 17, 9.5, 0.8, 0.3, 0.2, 28.5729, 77.2208),
    ("Noida Sector 62 Metro Connected", "Delhi-NCR", "Noida", "Apartment", 32000, 2, 2.0, 1200, 19, 9.1, 1.5, 0.3, 0.3, 28.6270, 77.3620),
    ("Dwarka Sector 12 DDA SFS Flat", "Delhi-NCR", "Dwarka", "Apartment", 36000, 3, 2.0, 1500, 16, 9.3, 1.1, 0.4, 0.4, 28.5921, 77.0460),
    ("Saket Anupam Complex 3BHK", "Delhi-NCR", "Saket", "Apartment", 58000, 3, 2.0, 1650, 16, 9.4, 0.6, 0.4, 0.2, 28.5244, 77.2167),

    # -------------------------------------------------------------
    # 🏙️ 4. HYDERABAD (10 Properties - Cyberabad & Royal Heritage)
    # -------------------------------------------------------------
    ("Road No 36 Luxury Villa", "Hyderabad", "Jubilee Hills", "Luxury Villa", 185000, 5, 4.5, 5200, 7, 9.9, 1.1, 0.8, 0.6, 17.4320, 78.4050),
    ("Apollo Health City 3BHK Flat", "Hyderabad", "Jubilee Hills", "Condo", 58000, 3, 2.5, 2100, 9, 9.7, 0.4, 0.5, 0.4, 17.4260, 78.4140),
    ("Banjara Hills Road No 12 Floor", "Hyderabad", "Banjara Hills", "Townhouse", 72000, 3, 3.0, 2400, 10, 9.7, 0.8, 0.6, 0.3, 17.4156, 78.4357),
    ("My Home Bhooja Sky Mansion", "Hyderabad", "Hitec City", "Condo", 90000, 3, 3.0, 2600, 11, 9.6, 0.9, 0.3, 0.3, 17.4483, 78.3813),
    ("Gachibowli Stadium Road 2BHK", "Hyderabad", "Gachibowli", "Apartment", 32000, 2, 2.0, 1250, 14, 9.3, 1.3, 0.5, 0.4, 17.4401, 78.3489),
    ("Madhapur Inorbit Mall Flat", "Hyderabad", "Madhapur", "Apartment", 45000, 3, 2.0, 1700, 15, 9.4, 1.0, 0.3, 0.2, 17.4486, 78.3908),
    ("Botanical Garden Road 3BHK", "Hyderabad", "Kondapur", "Apartment", 42000, 3, 2.0, 1600, 13, 9.5, 1.2, 0.6, 0.4, 17.4699, 78.3578),
    ("Lanco Hills Luxury Apartment", "Hyderabad", "Manikonda", "Condo", 38000, 3, 2.5, 1850, 16, 9.2, 1.5, 0.8, 0.5, 17.4022, 78.3845),
    ("KPHB 9th Phase Gated 2BHK", "Hyderabad", "Kukatpally", "Apartment", 26000, 2, 2.0, 1150, 18, 9.0, 1.6, 0.4, 0.3, 17.4948, 78.3996),
    ("Financial District High-Rise", "Hyderabad", "Financial District", "Condo", 62000, 3, 2.5, 2050, 10, 9.7, 1.0, 0.7, 0.5, 17.4150, 78.3450),

    # -------------------------------------------------------------
    # 🏙️ 5. CHENNAI (10 Properties - Coastal IT Hub & Cultural Belt)
    # -------------------------------------------------------------
    ("Anna Nagar 2nd Avenue 3BHK", "Chennai", "Anna Nagar", "Apartment", 42000, 3, 2.0, 1600, 12, 9.6, 0.9, 0.3, 0.2, 13.0850, 80.2100),
    ("Tower Park View Luxury Villa", "Chennai", "Anna Nagar", "Luxury Villa", 110000, 4, 3.5, 3400, 9, 9.8, 1.2, 0.4, 0.3, 13.0880, 80.2150),
    ("Adyar Riverview Luxury Flat", "Chennai", "Adyar", "Condo", 68000, 3, 2.5, 1900, 10, 9.7, 0.7, 0.5, 0.3, 13.0012, 80.2565),
    ("Besant Nagar Beachfront 3BHK", "Chennai", "Besant Nagar", "Apartment", 75000, 3, 3.0, 2100, 8, 9.8, 1.1, 0.6, 0.4, 13.0002, 80.2667),
    ("T. Nagar Pondy Bazaar 2BHK", "Chennai", "T. Nagar", "Apartment", 34000, 2, 2.0, 1200, 17, 9.3, 0.8, 0.2, 0.1, 13.0418, 80.2341),
    ("OMR Express IT Corridor 3BHK", "Chennai", "OMR", "Apartment", 36000, 3, 2.0, 1550, 16, 9.2, 1.4, 0.5, 0.4, 12.9360, 80.2300),
    ("Phoenix MarketCity Flat", "Chennai", "Velachery", "Apartment", 32000, 2, 2.0, 1250, 15, 9.3, 1.2, 0.4, 0.2, 12.9759, 80.2212),
    ("Kothari Road Prime Bungalow", "Chennai", "Nungambakkam", "Luxury Villa", 145000, 4, 4.0, 3800, 9, 9.8, 0.9, 0.5, 0.3, 13.0569, 80.2425),
    ("TTK Road Heritage Townhouse", "Chennai", "Alwarpet", "Townhouse", 58000, 3, 2.5, 1850, 11, 9.6, 0.7, 0.4, 0.3, 13.0336, 80.2505),
    ("DLF IT Park Walkable 2BHK", "Chennai", "Porur", "Apartment", 24000, 2, 2.0, 1100, 16, 9.1, 1.5, 0.6, 0.4, 13.0382, 80.1565)
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
    """Returns a SQLite connection configured with Row factory and WAL journal mode."""
    conn = sqlite3.connect(db_path, timeout=10.0, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.row_factory = sqlite3.Row
    return conn

# Alias for standard naming
get_db_connection = get_connection


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
            city TEXT NOT NULL,
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

    c.execute("PRAGMA table_info(Properties)")
    prop_cols = [col[1] for col in c.fetchall()]
    if "city" not in prop_cols:
        c.execute("DROP TABLE IF EXISTS Properties")
        c.execute("""
            CREATE TABLE Properties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                city TEXT NOT NULL,
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
        force_reset = True

    # 5. Performance Indexes
    c.execute("CREATE INDEX IF NOT EXISTS idx_doctors_specialty ON Doctors(specialty);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_doctors_fee ON Doctors(consultation_fee);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_doctors_distance ON Doctors(distance_miles);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_doctors_available ON Doctors(is_available_today);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_doctors_satisfaction ON Doctors(satisfaction_score);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_doctors_success ON Doctors(surgery_success_rate);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_appointments_slot ON Appointments(doctor_id, appointment_date, time_slot);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_properties_city ON Properties(city);")
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
            fee = rng.choice([0, 400, 500, 700, 800, 1000, 1200, 1500, 2000, 2500, 3000])
            
            is_today = rng.choice(["Yes", "No"])
            if is_today == "Yes":
                next_date = base_date.strftime("%Y-%m-%d")
            else:
                days_ahead = rng.randint(1, 5)
                next_date = (base_date + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
            
            # Select random hospital hub with realistic coordinate jitter (± 0.045 deg)
            hub_lat, hub_lng = rng.choice(HOSPITAL_GEO_HUBS)
            doc_lat = round(hub_lat + rng.uniform(-0.045, 0.045), 4)
            doc_lng = round(hub_lng + rng.uniform(-0.045, 0.045), 4)

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
            title, city, nbh, ptype, price, beds, baths, sqft, crime, school, hosp_d, trans_d, mkt_d, lat, lng = p
            livability = calculate_livability_score(crime, school, hosp_d, trans_d)
            dummy_properties.append((
                title, city, nbh, ptype, price, beds, baths, sqft, crime, school, hosp_d, trans_d, mkt_d, livability, lat, lng
            ))

        c.executemany("""
            INSERT INTO Properties (
                title, city, neighborhood, property_type, price_per_month, bedrooms, bathrooms,
                sqft, crime_index_score, school_rating, hospital_dist_miles, transit_dist_miles,
                market_dist_miles, livability_score, latitude, longitude
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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

# Standard alias
initialize_database = init_database
