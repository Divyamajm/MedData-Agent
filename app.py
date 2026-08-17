import streamlit as st
import pandas as pd
import sqlite3
import random
from datetime import datetime, timedelta

# ==========================================
# 1. ENTERPRISE TRIAGE & BOOKING DATABASE
# ==========================================
def setup_ultimate_database():
    conn = sqlite3.connect('hospital_ultimate.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS Doctors (
                    id INTEGER PRIMARY KEY, name TEXT, specialty TEXT, 
                    primary_surgery TEXT, surgery_success_rate REAL, 
                    satisfaction_score INTEGER, distance_miles REAL, 
                    consultation_fee INTEGER, is_available_today TEXT, 
                    next_available_date TEXT)''')
    c.execute('DELETE FROM Doctors') 
    
    specialties = {'Cardiology': 'Bypass', 'Neurology': 'Spinal Fusion', 'Orthopedics': 'Knee Replacement', 'Pediatrics': 'General', 'Emergency': 'Trauma'}
    last_names = ['Smith', 'Patel', 'Lee', 'Garcia', 'Martinez', 'Johnson', 'Kim', 'Davis', 'Chen', 'Okafor']
    
    dummy_data = []
    base_date = datetime.today()
    
    for i in range(1, 201):
        name = f"Dr. {random.choice(last_names)}"
        specialty = random.choice(list(specialties.keys()))
        surgery = specialties[specialty]
        
        score = random.randint(70, 100)
        success = round(random.uniform(85.0, 99.9), 1)
        
        # New Complex Metrics
        distance = round(random.uniform(0.5, 30.0), 1) # Miles away
        fee = random.choice([0, 50, 100, 150, 250, 500]) # 0 means fully covered/free
        
        # Scheduling Logic
        is_today = random.choice(['Yes', 'No'])
        if is_today == 'Yes':
            next_date = base_date.strftime('%Y-%m-%d')
        else:
            next_date = (base_date + timedelta(days=random.randint(1, 14))).strftime('%Y-%m-%d')
            
        dummy_data.append((i, name, specialty, surgery, success, score, distance, fee, is_today, next_date))
        
    c.executemany('INSERT INTO Doctors VALUES (?,?,?,?,?,?,?,?,?,?)', dummy_data)
    conn.commit()
    return conn

conn = setup_ultimate_database()

# ==========================================
# 2. STREAMLIT UI CONFIGURATION
# ==========================================
st.set_page_config(page_title="MedData AI Booking Agent", page_icon="🚑", layout="wide")

st.markdown("<h1 style='color: #d9534f;'>🚑 MedData Smart Triage & Booking Agent</h1>", unsafe_allow_html=True)
st.markdown("**Handles Emergencies, Scheduling, Fees, and Fallback Recommendations.**")
st.divider()

with st.sidebar:
    st.header("🗄️ Database Inspector")
    if st.checkbox("Show all 200 Database Records"):
        st.dataframe(pd.read_sql_query("SELECT * FROM Doctors", conn), use_container_width=True)

# ==========================================
# 3. CHAT STATE MANAGEMENT
# ==========================================
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello. I am the MedData Triage Agent. Are you experiencing an emergency, looking to book an appointment, or searching for the most affordable care?"}]
if "clarification_context" not in st.session_state:
    st.session_state.clarification_context = None

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ==========================================
# 4. ADVANCED AGENT ROUTING LOGIC
# ==========================================
if prompt := st.chat_input("E.g., 'I have an emergency' or 'Find a cheap doctor'"):
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
        
    with st.chat_message("assistant"):
        prompt_lower = prompt.lower()
        explanation = ""
        sql = ""
        
        # --- SCENARIO 1: EMERGENCY (GEOSPATIAL + TIME) ---
        if "emergency" in prompt_lower or "urgent" in prompt_lower:
            st.markdown("🚨 **EMERGENCY PROTOCOL ACTIVATED:** Locating the absolute closest doctors who are available *right now*.")
            sql = "SELECT name, specialty, distance_miles, is_available_today, consultation_fee FROM Doctors WHERE is_available_today = 'Yes' ORDER BY distance_miles ASC LIMIT 3"
            explanation = "AI detected 'emergency'. Bypassed standard metrics to filter strictly by immediate availability (today) and sorted by lowest distance in miles."
            
        # --- SCENARIO 2: FINANCIAL/AFFORDABILITY ---
        elif "cheap" in prompt_lower or "free" in prompt_lower or "lowest fee" in prompt_lower:
            st.markdown("💰 **FINANCIAL ROUTING:** Finding the most affordable care options for you.")
            sql = "SELECT name, specialty, consultation_fee, satisfaction_score, distance_miles FROM Doctors ORDER BY consultation_fee ASC, satisfaction_score DESC LIMIT 5"
            explanation = "AI detected financial sensitivity. Sorted database primarily by lowest 'consultation_fee', using 'satisfaction_score' as a secondary tie-breaker for quality."

        # --- SCENARIO 3: UNAVAILABLE FALLBACK / RECOMMENDATION ---
        elif "book" in prompt_lower or "appointment" in prompt_lower:
            if "cardiologist" in prompt_lower or "heart" in prompt_lower:
                st.markdown("📅 **SCHEDULING PROTOCOL:** Checking Cardiology availability for today...")
                # Simulate checking for a specific doctor and falling back to others
                st.markdown("⚠️ *Note: Dr. Smith (Cardiology) is fully booked today. However, the system has automatically found 3 other top-rated Cardiologists available immediately:*")
                sql = "SELECT name, specialty, is_available_today, next_available_date, satisfaction_score FROM Doctors WHERE specialty = 'Cardiology' AND is_available_today = 'Yes' AND name != 'Dr. Smith' ORDER BY satisfaction_score DESC LIMIT 3"
                explanation = "AI attempted to book a specific specialty. Simulated a 'fully booked' scenario and successfully executed a fallback recommendation query to provide alternate doctors in the same specialty."
            else:
                st.markdown("📅 **SCHEDULING PROTOCOL:** Here are our earliest available appointments across all specialties.")
                sql = "SELECT name, specialty, next_available_date, consultation_fee FROM Doctors ORDER BY next_available_date ASC LIMIT 5"
                explanation = "AI sorted entire database chronologically by 'next_available_date' to show the soonest possible appointments."

        # --- SCENARIO 4: THE ORIGINAL AMBIGUITY LOOP ---
        elif "best" in prompt_lower:
            st.markdown("⚠️ **Ambiguity Detected:** By 'best', do you mean the doctor with the **highest satisfaction score**, or the **highest surgical success rate**?")
            sql = "SELECT * FROM Doctors LIMIT 0" # Return empty just to pause
            explanation = "Intercepted ambiguous human logic. Awaiting clarification."
            
        # --- FALLBACK ---
        else:
            st.markdown("Executing standard database query...")
            sql = "SELECT name, specialty, distance_miles, consultation_fee, next_available_date FROM Doctors LIMIT 5"
            explanation = "Standard unstructured query executed."

        # --- EXECUTE AND SHOW PROOF ---
        if sql and "LIMIT 0" not in sql:
            df = pd.read_sql_query(sql, conn)
            st.dataframe(df, use_container_width=True)
            
            with st.expander("🔍 Interviewer Proof: AI Decision Logic & SQL Audit"):
                st.write(f"**1. AI Logic Translation:** {explanation}")
                st.write("**2. Raw SQL Executed:**")
                st.code(sql, language="sql")
                st.write("**3. Verification:** Data generated dynamically from 200-record SQLite mock server.")