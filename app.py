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
# 2. STREAMLIT UI CONFIGURATION 
# ==========================================
st.set_page_config(page_title="MedData AI Booking Agent", page_icon="🚑", layout="wide")

st.markdown("<h1 style='color: #d9534f; text-align: center;'>🚑 MedData Enterprise Agent</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'><strong>Smart Triage Agent | Live Data Explorer | SQL Verification Sandbox</strong></p>", unsafe_allow_html=True)
st.divider()

tab1, tab2, tab3 = st.tabs(["💬 AI Triage Agent", "🗄️ Database Explorer", "⚡ Interviewer SQL Sandbox"])

# ==========================================
# TAB 1: THE AI AGENT (WITH CONTEXT MEMORY)
# ==========================================
with tab1:
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "Hello. I am the MedData Triage Agent. Are you experiencing an emergency, looking to book an appointment, or searching for affordable care?", "type": "text"}]
    if "pending_clarification" not in st.session_state:
        st.session_state.pending_clarification = False
    if "current_filter" not in st.session_state:
        st.session_state.current_filter = None # THIS IS THE MEMORY FIX

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("type") == "data":
                st.dataframe(msg["df"], use_container_width=True)
                with st.expander("🔍 Explainability Audit Trail"):
                    st.write(f"**AI Logic Translation:** {msg['explanation']}")
                    st.code(msg['sql'], language="sql")

    # THE BUTTONS NOW USE MEMORY
    if st.session_state.pending_clarification:
        with st.chat_message("assistant"):
            st.markdown("⚠️ **Ambiguity Detected:** Please clarify what you mean by 'best':")
            
            col1, col2 = st.columns(2)
            
            if col1.button("⭐ Highest Satisfaction Score"):
                st.session_state.messages.append({"role": "user", "content": "Highest Satisfaction Score", "type": "text"})
                
                # Check if we remembered a specialty
                if st.session_state.current_filter:
                    sql = f"SELECT name, specialty, satisfaction_score, consultation_fee FROM Doctors WHERE specialty = '{st.session_state.current_filter}' ORDER BY satisfaction_score DESC LIMIT 5"
                    explanation = f"User clicked 'Satisfaction Score'. AI remembered context: filtered strictly by {st.session_state.current_filter}."
                else:
                    sql = "SELECT name, specialty, satisfaction_score, consultation_fee FROM Doctors ORDER BY satisfaction_score DESC LIMIT 5"
                    explanation = "User clicked 'Satisfaction Score'. Sorted descending by score across all specialties."
                    
                df = pd.read_sql_query(sql, conn)
                st.session_state.messages.append({"role": "assistant", "content": "Here are the top doctors by patient satisfaction:", "type": "data", "df": df, "sql": sql, "explanation": explanation})
                st.session_state.pending_clarification = False
                st.session_state.current_filter = None # Clear memory
                st.rerun()
                
            if col2.button("📈 Highest Surgical Success Rate"):
                st.session_state.messages.append({"role": "user", "content": "Highest Surgical Success Rate", "type": "text"})
                
                # Check if we remembered a specialty
                if st.session_state.current_filter:
                    sql = f"SELECT name, specialty, primary_surgery, surgery_success_rate FROM Doctors WHERE specialty = '{st.session_state.current_filter}' ORDER BY surgery_success_rate DESC LIMIT 5"
                    explanation = f"User clicked 'Surgical Success Rate'. AI remembered context: filtered strictly by {st.session_state.current_filter}."
                else:
                    sql = "SELECT name, specialty, primary_surgery, surgery_success_rate FROM Doctors ORDER BY surgery_success_rate DESC LIMIT 5"
                    explanation = "User clicked 'Surgical Success Rate'. Sorted descending by success rate across all specialties."
                    
                df = pd.read_sql_query(sql, conn)
                st.session_state.messages.append({"role": "assistant", "content": "Here are the top doctors by surgical success rate:", "type": "data", "df": df, "sql": sql, "explanation": explanation})
                st.session_state.pending_clarification = False
                st.session_state.current_filter = None # Clear memory
                st.rerun()

    elif prompt := st.chat_input("Ask the MedData Agent..."):
        st.session_state.messages.append({"role": "user", "content": prompt, "type": "text"})
        prompt_lower = prompt.lower()
        st.session_state.current_filter = None # Reset memory on new prompts
        
        # --- LOCATION ---
        if any(word in prompt_lower for word in ["emergency", "urgent", "shortest", "distance", "closest", "near"]):
            sql = "SELECT name, specialty, distance_miles, is_available_today, consultation_fee FROM Doctors ORDER BY distance_miles ASC LIMIT 5"
            explanation = "AI detected intent for proximity/distance. Sorted database by 'distance_miles' in ascending order."
            df = pd.read_sql_query(sql, conn)
            st.session_state.messages.append({"role": "assistant", "content": "📍 **LOCATION PROTOCOL:** Finding the closest doctors to the hospital.", "type": "data", "df": df, "sql": sql, "explanation": explanation})
            st.rerun()
            
        # --- FINANCIAL ---
        elif any(word in prompt_lower for word in ["cheap", "free", "fee", "affordable"]):
            sql = "SELECT name, specialty, consultation_fee, satisfaction_score, distance_miles FROM Doctors ORDER BY consultation_fee ASC, satisfaction_score DESC LIMIT 5"
            explanation = "Sorted primarily by lowest 'consultation_fee', using 'satisfaction_score' as a secondary tie-breaker."
            df = pd.read_sql_query(sql, conn)
            st.session_state.messages.append({"role": "assistant", "content": "💰 **FINANCIAL ROUTING:** Finding the most affordable care options.", "type": "data", "df": df, "sql": sql, "explanation": explanation})
            st.rerun()

        # --- AMBIGUITY INTERCEPTOR (NOW SAVES TO MEMORY) ---
        elif "best" in prompt_lower or "top" in prompt_lower:
            specialties = ['cardiology', 'neurology', 'orthopedics', 'pediatrics', 'emergency']
            for spec in specialties:
                if spec in prompt_lower:
                    st.session_state.current_filter = spec.capitalize() # Save specialty to memory!
                    break
                    
            st.session_state.pending_clarification = True
            st.rerun()
            
        # --- DIRECTORY INTENT ---
        elif any(word in prompt_lower for word in ["all", "every", "list"]):
            specialties = ['cardiology', 'neurology', 'orthopedics', 'pediatrics', 'emergency']
            found_specialty = None
            for spec in specialties:
                if spec in prompt_lower:
                    found_specialty = spec.capitalize()
                    break
            
            if found_specialty:
                sql = f"SELECT name, specialty, distance_miles, consultation_fee, next_available_date FROM Doctors WHERE specialty = '{found_specialty}'"
                explanation = f"AI detected 'all' intent AND extracted an entity ('{found_specialty}'). Injected a strict WHERE clause."
                msg_content = f"📋 **DIRECTORY PROTOCOL:** Fetching all our **{found_specialty}** specialists."
            else:
                sql = "SELECT name, specialty, distance_miles, consultation_fee, next_available_date FROM Doctors"
                explanation = "AI detected intent for the full dataset but no specific specialty. Removed the 'LIMIT 5' constraint."
                msg_content = "📋 **DIRECTORY PROTOCOL:** Fetching the complete directory of all doctors."
            
            df = pd.read_sql_query(sql, conn)
            st.session_state.messages.append({"role": "assistant", "content": msg_content, "type": "data", "df": df, "sql": sql, "explanation": explanation})
            st.rerun()
            
        # --- STANDARD FALLBACK ---
        else:
            sql = "SELECT name, specialty, distance_miles, consultation_fee, next_available_date FROM Doctors LIMIT 5"
            explanation = "Generic query detected. Applied standard 'LIMIT 5' for UI safety."
            df = pd.read_sql_query(sql, conn)
            st.session_state.messages.append({"role": "assistant", "content": "Here is a sample of 5 doctors from our database. Ask for 'all' to see the full list.", "type": "data", "df": df, "sql": sql, "explanation": explanation})
            st.rerun()

# ==========================================
# TAB 2 & 3: DATABASE EXPLORER & SANDBOX
# ==========================================
with tab2:
    st.markdown("### 🗄️ Enterprise Data Lake (Mock View)")
    col1, col2, col3, col4 = st.columns(4)
    all_df = pd.read_sql_query("SELECT * FROM Doctors", conn)
    col1.metric("Total Active Doctors", f"{len(all_df)}")
    col2.metric("Specialties Represented", f"{all_df['specialty'].nunique()}")
    col3.metric("Avg Consultation Fee", f"${round(all_df['consultation_fee'].mean(), 2)}")
    col4.metric("Available Today", f"{len(all_df[all_df['is_available_today'] == 'Yes'])}")
    st.dataframe(all_df, use_container_width=True, height=500)

with tab3:
    st.markdown("### ⚡ Live SQL Sandbox")
    custom_sql = st.text_area("Write your SQL Query here:", value="SELECT specialty, COUNT(*) as Total_Doctors, AVG(consultation_fee) as Avg_Fee FROM Doctors GROUP BY specialty;")
    if st.button("▶ Run Custom Query"):
        try:
            st.dataframe(pd.read_sql_query(custom_sql, conn), use_container_width=True)
            st.success("Query Executed Successfully!")
        except Exception as e:
            st.error(f"SQL Error: {e}")