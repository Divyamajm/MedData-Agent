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
        distance = round(random.uniform(0.5, 30.0), 1)
        fee = random.choice([0, 50, 100, 150, 250, 500])
        
        is_today = random.choice(['Yes', 'No'])
        next_date = base_date.strftime('%Y-%m-%d') if is_today == 'Yes' else (base_date + timedelta(days=random.randint(1, 14))).strftime('%Y-%m-%d')
            
        dummy_data.append((i, name, specialty, surgery, success, score, distance, fee, is_today, next_date))
        
    c.executemany('INSERT INTO Doctors VALUES (?,?,?,?,?,?,?,?,?,?)', dummy_data)
    conn.commit()
    return conn

conn = setup_ultimate_database()

# ==========================================
# 2. STREAMLIT UI CONFIGURATION (UPGRADED)
# ==========================================
st.set_page_config(page_title="MedData AI Booking Agent", page_icon="🚑", layout="wide")

st.markdown("<h1 style='color: #d9534f; text-align: center;'>🚑 MedData Enterprise Agent</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'><strong>Smart Triage Agent | Live Data Explorer | SQL Verification Sandbox</strong></p>", unsafe_allow_html=True)
st.divider()

# Create Three Professional UI Tabs
tab1, tab2, tab3 = st.tabs(["💬 AI Triage Agent", "🗄️ Database Explorer", "⚡ Interviewer SQL Sandbox"])

# ==========================================
# TAB 1: THE AI AGENT
# ==========================================
with tab1:
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "Hello. I am the MedData Triage Agent. Are you experiencing an emergency, looking to book an appointment, or searching for affordable care?"}]

    # Display chat messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat Input
    if prompt := st.chat_input("Ask the MedData Agent..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            
        with st.chat_message("assistant"):
            prompt_lower = prompt.lower()
            explanation = ""
            sql = ""
            
            if "emergency" in prompt_lower or "urgent" in prompt_lower:
                st.markdown("🚨 **EMERGENCY PROTOCOL:** Locating the absolute closest doctors available *right now*.")
                sql = "SELECT name, specialty, distance_miles, is_available_today, consultation_fee FROM Doctors WHERE is_available_today = 'Yes' ORDER BY distance_miles ASC LIMIT 3"
                explanation = "Bypassed standard metrics to filter strictly by immediate availability (today) and sorted by lowest distance in miles."
                
            elif "cheap" in prompt_lower or "free" in prompt_lower or "fee" in prompt_lower:
                st.markdown("💰 **FINANCIAL ROUTING:** Finding the most affordable care options.")
                sql = "SELECT name, specialty, consultation_fee, satisfaction_score, distance_miles FROM Doctors ORDER BY consultation_fee ASC, satisfaction_score DESC LIMIT 5"
                explanation = "Sorted primarily by lowest 'consultation_fee', using 'satisfaction_score' as a secondary tie-breaker."

            elif "book" in prompt_lower or "appointment" in prompt_lower:
                st.markdown("📅 **SCHEDULING PROTOCOL:** Here are our earliest available appointments.")
                sql = "SELECT name, specialty, next_available_date, consultation_fee, satisfaction_score FROM Doctors ORDER BY next_available_date ASC LIMIT 5"
                explanation = "Sorted entire database chronologically by 'next_available_date'."

            elif "best" in prompt_lower:
                st.markdown("⚠️ **Ambiguity Detected:** By 'best', do you mean the doctor with the **highest satisfaction score**, or the **highest surgical success rate**?")
                sql = "SELECT * FROM Doctors LIMIT 0" 
                explanation = "Intercepted ambiguous human logic. Awaiting clarification."
                
            else:
                st.markdown("Executing standard database query...")
                sql = "SELECT name, specialty, distance_miles, consultation_fee, next_available_date FROM Doctors LIMIT 5"
                explanation = "Standard unstructured query executed."

            if sql and "LIMIT 0" not in sql:
                df = pd.read_sql_query(sql, conn)
                st.dataframe(df, use_container_width=True)
                
                with st.expander("🔍 Explainability Audit Trail"):
                    st.write(f"**AI Logic Translation:** {explanation}")
                    st.code(sql, language="sql")

# ==========================================
# TAB 2: THE DATABASE EXPLORER
# ==========================================
with tab2:
    st.markdown("### 🗄️ Enterprise Data Lake (Mock View)")
    st.write("This tab allows stakeholders to view the entire ground-truth dataset that powers the AI Agent.")
    
    # Show some cool high-level metrics
    col1, col2, col3, col4 = st.columns(4)
    all_df = pd.read_sql_query("SELECT * FROM Doctors", conn)
    
    col1.metric("Total Active Doctors", f"{len(all_df)}")
    col2.metric("Specialties Represented", f"{all_df['specialty'].nunique()}")
    col3.metric("Avg Consultation Fee", f"${round(all_df['consultation_fee'].mean(), 2)}")
    col4.metric("Available Today", f"{len(all_df[all_df['is_available_today'] == 'Yes'])}")
    
    st.dataframe(all_df, use_container_width=True, height=500)

# ==========================================
# TAB 3: THE INTERVIEWER SQL SANDBOX
# ==========================================
with tab3:
    st.markdown("### ⚡ Live SQL Sandbox")
    st.write("Verify the AI's logic or test my SQL skills by running custom queries directly against the live mock database.")
    
    custom_sql = st.text_area("Write your SQL Query here:", value="SELECT specialty, COUNT(*) as Total_Doctors, AVG(consultation_fee) as Avg_Fee FROM Doctors GROUP BY specialty;")
    
    if st.button("▶ Run Custom Query"):
        try:
            sandbox_df = pd.read_sql_query(custom_sql, conn)
            st.success("Query Executed Successfully!")
            st.dataframe(sandbox_df, use_container_width=True)
        except Exception as e:
            st.error(f"SQL Error: {e}")