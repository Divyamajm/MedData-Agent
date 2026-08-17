import streamlit as st
import pandas as pd
import sqlite3

# ==========================================
# 1. DUMMY DATABASE SETUP
# ==========================================
def setup_database():
    conn = sqlite3.connect('hospital.db')
    c = conn.cursor()
    # Create a table with ambiguous metrics (patients_seen vs satisfaction_score)
    c.execute('CREATE TABLE IF NOT EXISTS Doctors (id INTEGER PRIMARY KEY, name TEXT, specialty TEXT, patients_seen INTEGER, satisfaction_score INTEGER)')
    c.execute('DELETE FROM Doctors') # Clear old data
    
    dummy_data = [
        (1, 'Dr. Smith', 'Cardiology', 320, 98),
        (2, 'Dr. Jones', 'Neurology', 450, 82),
        (3, 'Dr. Patel', 'Pediatrics', 510, 95),
        (4, 'Dr. Lee', 'Cardiology', 210, 99)
    ]
    c.executemany('INSERT INTO Doctors VALUES (?,?,?,?,?)', dummy_data)
    conn.commit()
    return conn

conn = setup_database()

# ==========================================
# 2. STREAMLIT UI CONFIGURATION
# ==========================================
st.set_page_config(page_title="MedData Agent", page_icon="🏥", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .main-header { color: #0056b3; font-family: 'Inter', sans-serif; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-header'>🏥 MedData-Agent</h1>", unsafe_allow_html=True)
st.markdown("**Enterprise Agentic Text-to-SQL Pipeline with Human-in-the-Loop Clarification**")
st.divider()

# ==========================================
# 3. CHAT STATE MANAGEMENT
# ==========================================
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Welcome to MedData. Ask me a question about our hospital data."}]
if "awaiting_clarification" not in st.session_state:
    st.session_state.awaiting_clarification = False

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ==========================================
# 4. THE CLARIFICATION LOOP (AGENT LOGIC)
# ==========================================
if prompt := st.chat_input("E.g., 'Show me our best doctors'"):
    
    # 1. Show user input
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
        
    with st.chat_message("assistant"):
        
        # 2. Check if we are currently resolving an ambiguity
        if st.session_state.awaiting_clarification:
            st.markdown(f"Executing SQL based on clarification: **{prompt}**")
            
            # Execute the deterministic SQL based on the user's clarification
            if "score" in prompt.lower() or "satisfaction" in prompt.lower():
                sql = "SELECT name, specialty, satisfaction_score FROM Doctors ORDER BY satisfaction_score DESC LIMIT 3"
            else:
                sql = "SELECT name, specialty, patients_seen FROM Doctors ORDER BY patients_seen DESC LIMIT 3"
                
            st.code(sql, language="sql")
            df = pd.read_sql_query(sql, conn)
            st.dataframe(df, use_container_width=True)
            
            st.session_state.messages.append({"role": "assistant", "content": f"Results pulled based on {prompt}."})
            st.session_state.awaiting_clarification = False # Reset loop
            
        # 3. The "Ambiguity Evaluator" interceptor
        elif any(word in prompt.lower() for word in ["best", "top", "good"]):
            clarification_msg = "⚠️ **Ambiguity Detected:** By 'best', do you mean the doctors with the **highest satisfaction score** or the **most patients seen**?"
            st.markdown(clarification_msg)
            
            st.session_state.messages.append({"role": "assistant", "content": clarification_msg})
            st.session_state.awaiting_clarification = True # Pause execution and wait for next user input
            
        # 4. Standard clear query fallback
        else:
            st.markdown("Query is clear. Generating standard SQL...")
            sql = "SELECT * FROM Doctors" # Fallback dummy SQL
            st.code(sql, language="sql")
            df = pd.read_sql_query(sql, conn)
            st.dataframe(df, use_container_width=True)
            st.session_state.messages.append({"role": "assistant", "content": "Standard data retrieved."})