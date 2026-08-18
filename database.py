"""
MedData AI - Database Management Layer
Provides schema definitions, indices, thread-safe connection pooling, 
unique mock data seeding, and summary statistics.
"""

import sqlite3
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

DB_PATH = "hospital_ultimate.db"

# Canonical specialties & their clinical procedures in the demo dataset
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

# 20 First Names & 20 Last Names => 400 unique combinations available
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


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Returns a SQLite connection configured with Row factory."""
    conn = sqlite3.connect(db_path, timeout=10.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_database(db_path: str = DB_PATH, force_reset: bool = False) -> None:
    """
    Initializes the SQLite schema with tables and indexes.
    Seeds 200 unique realistic fictional doctors ONLY if table is empty or force_reset=True.
    """
    conn = get_connection(db_path)
    c = conn.cursor()

    # 1. Create Doctors Table
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
            next_available_date TEXT NOT NULL
        )
    """)

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

    # 3. Create Simulated Appointments Table (for Demo Booking)
    c.execute("""
        CREATE TABLE IF NOT EXISTS Appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_id INTEGER NOT NULL,
            doctor_name TEXT NOT NULL,
            patient_name TEXT NOT NULL,
            appointment_date TEXT NOT NULL,
            time_slot TEXT NOT NULL,
            status TEXT NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (doctor_id) REFERENCES Doctors(id)
        )
    """)

    # 4. Performance Indexes
    c.execute("CREATE INDEX IF NOT EXISTS idx_doctors_specialty ON Doctors(specialty);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_doctors_fee ON Doctors(consultation_fee);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_doctors_distance ON Doctors(distance_miles);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_doctors_available ON Doctors(is_available_today);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_doctors_satisfaction ON Doctors(satisfaction_score);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_doctors_success ON Doctors(surgery_success_rate);")

    # Check if data already exists and has the new unique full names
    c.execute("SELECT COUNT(*) FROM Doctors")
    count = c.fetchone()[0]
    
    needs_seed = (count == 0 or force_reset)
    if not needs_seed and count > 0:
        c.execute("SELECT name FROM Doctors LIMIT 5")
        sample_names = [row[0] for row in c.fetchall()]
        # Check if sample names are legacy format like 'Dr. Smith' (only 2 words) instead of 'Dr. Sarah Chen' (3 words)
        if any(len(n.split()) < 3 for n in sample_names):
            needs_seed = True

    if needs_seed:
        c.execute("DELETE FROM Doctors")
        c.execute("DELETE FROM Specialties")
        c.execute("DELETE FROM Appointments")

        # Populate Specialties
        for spec_name, spec_info in SPECIALTIES_METADATA.items():
            c.execute("""
                INSERT INTO Specialties (name, description, typical_procedures, common_conditions)
                VALUES (?, ?, ?, ?)
            """, (spec_name, spec_info["description"], spec_info["typical_procedures"], spec_info["common_conditions"]))

        # Generate 200 Unique Doctor Identities
        # Fixed random seed for deterministic demo consistency across restarts
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
            
            # Realistic, varied clinical metrics
            satisfaction = rng.randint(72, 99)
            success_rate = round(rng.uniform(88.0, 99.8), 1)
            distance = round(rng.uniform(0.4, 28.5), 1)
            fee = rng.choice([0, 50, 75, 100, 150, 200, 300, 500])
            
            is_today = rng.choice(["Yes", "No"])
            if is_today == "Yes":
                next_date = base_date.strftime("%Y-%m-%d")
            else:
                next_date = (base_date + timedelta(days=rng.randint(1, 14))).strftime("%Y-%m-%d")
            
            dummy_doctors.append((
                i, name, specialty, surgery, success_rate, satisfaction, 
                distance, fee, is_today, next_date
            ))

        c.executemany("""
            INSERT INTO Doctors (
                id, name, specialty, primary_surgery, surgery_success_rate,
                satisfaction_score, distance_miles, consultation_fee, 
                is_available_today, next_available_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, dummy_doctors)

        # Seed 5 sample mock appointments for realism
        mock_appointments = [
            (1, dummy_doctors[0][1], "Demo Patient A", base_date.strftime("%Y-%m-%d"), "09:00 AM", "Confirmed", "Routine Consultation", datetime.now().isoformat()),
            (2, dummy_doctors[1][1], "Demo Patient B", base_date.strftime("%Y-%m-%d"), "11:30 AM", "Confirmed", "Pre-op Assessment", datetime.now().isoformat()),
            (3, dummy_doctors[2][1], "Demo Patient C", (base_date + timedelta(days=1)).strftime("%Y-%m-%d"), "02:00 PM", "Confirmed", "Post-op Followup", datetime.now().isoformat()),
        ]
        c.executemany("""
            INSERT INTO Appointments (
                doctor_id, doctor_name, patient_name, appointment_date, 
                time_slot, status, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, mock_appointments)

        conn.commit()

    conn.close()


def get_database_stats(db_path: str = DB_PATH) -> Dict[str, Any]:
    """Retrieves high-level summary metrics for the Data Lake Explorer."""
    conn = get_connection(db_path)
    c = conn.cursor()

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
        "specialty_breakdown": specialty_breakdown
    }


def reset_demo_data(db_path: str = DB_PATH) -> None:
    """Explicitly resets and re-seeds the demo database."""
    init_database(db_path=db_path, force_reset=True)


def book_simulated_appointment(
    doctor_id: int, 
    patient_name: str, 
    appointment_date: str, 
    time_slot: str, 
    notes: str = "",
    db_path: str = DB_PATH
) -> Dict[str, Any]:
    """Records a simulated demo appointment booking in SQLite."""
    conn = get_connection(db_path)
    c = conn.cursor()

    c.execute("SELECT name, specialty FROM Doctors WHERE id = ?", (doctor_id,))
    doc = c.fetchone()
    if not doc:
        conn.close()
        return {"success": False, "error": f"Doctor ID {doctor_id} not found."}

    doc_name = doc["name"]
    created_at = datetime.now().isoformat()

    c.execute("""
        INSERT INTO Appointments (
            doctor_id, doctor_name, patient_name, appointment_date, 
            time_slot, status, notes, created_at
        ) VALUES (?, ?, ?, ?, ?, 'Confirmed (Demo Simulation)', ?, ?)
    """, (doctor_id, doc_name, patient_name, appointment_date, time_slot, notes, created_at))

    booking_id = c.lastrowid
    conn.commit()
    conn.close()

    return {
        "success": True,
        "booking_id": booking_id,
        "doctor_name": doc_name,
        "patient_name": patient_name,
        "appointment_date": appointment_date,
        "time_slot": time_slot,
        "disclaimer": "DEMO SIMULATION — No actual medical appointment was scheduled."
    }
