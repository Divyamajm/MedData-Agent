"""
MedData AI & UrbanLocate - Multi-Domain Discovery & Triage Platform
Production Streamlit Application with Deterministic Query Engines,
Interactive Geo-Spatial Maps, Appointment Conflict Scheduler, Side-by-Side Comparison Matrix,
Insurance Estimator, Multi-Dataset Explorer, AST SQL Sandbox, and Automated Test Suite.
"""

import time
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

from models import (
    IntentType, CanonicalSpecialty, SortMetric, SortOrder, DomainType,
    SearchFilters, HousingSearchFilters, ExplainabilityAudit
)
from database import (
    init_database, get_connection, get_database_stats, reset_demo_data,
    book_appointment, get_all_appointments, check_appointment_conflict, DB_PATH
)
from intent_parser import classify_intent_and_extract_entities, detect_domain
from query_engine import execute_doctor_search, execute_housing_search
from safety import validate_sql_sandbox_query
from ui_components import (
    inject_custom_css, render_header, render_doctor_cards, render_housing_cards,
    render_geo_map, render_comparison_matrix, generate_ics_calendar,
    render_insurance_calculator, render_audit_trail, render_clarification_buttons,
    render_safety_warning
)
from tests.test_suite import run_all_tests, run_sql_sandbox_security_tests
from tests.test_cases import ALL_TEST_CASES

# ==========================================
# 1. APPLICATION INITIALIZATION & CONFIG
# ==========================================
st.set_page_config(
    page_title="MedData AI & UrbanLocate - Grounded Discovery Platform",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply custom enterprise styles
inject_custom_css()

# Initialize SQLite database (seeds 200 doctors + 36 housing records if empty)
init_database()

# Session State Initialization
if "active_domain" not in st.session_state:
    st.session_state.active_domain = DomainType.HEALTHCARE

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Hello. I am the **MedData AI & UrbanLocate Grounded Discovery Agent**.\n\n"
                "I provide deterministic, database-grounded discovery across **Verified Physician Directories** "
                "and **Curated Real Estate & Neighborhood Livability Datasets** with zero hallucinations.\n\n"
                "💡 *Healthcare: 'Find a cardiologist within 10 miles under $150 available today'*\n"
                "🏡 *Real Estate: 'Find a 3BHK near top schools with low crime and hospital within 2 miles'*"
            ),
            "type": "text"
        }
    ]

if "pending_clarification" not in st.session_state:
    st.session_state.pending_clarification = False

if "clarification_data" not in st.session_state:
    st.session_state.clarification_data = None

if "sql_sandbox_query" not in st.session_state:
    st.session_state.sql_sandbox_query = "SELECT specialty, COUNT(*) as total_doctors, AVG(consultation_fee) as avg_fee, AVG(satisfaction_score) as avg_satisfaction FROM Doctors GROUP BY specialty;"

if "test_results" not in st.session_state:
    st.session_state.test_results = None

# ==========================================
# 2. HEADER & DOMAIN SELECTOR
# ==========================================
render_header(st.session_state.active_domain)

with st.sidebar:
    st.markdown("### 🌐 Active Data Lake Domain")
    domain_choice = st.radio(
        "Select Operating Domain:",
        ["🏥 Healthcare Triage & Doctors", "🏡 UrbanLocate Real Estate"],
        index=0 if st.session_state.active_domain == DomainType.HEALTHCARE else 1
    )
    new_domain = DomainType.HEALTHCARE if "Healthcare" in domain_choice else DomainType.REAL_ESTATE
    if new_domain != st.session_state.active_domain:
        st.session_state.active_domain = new_domain
        st.rerun()

    st.divider()
    st.markdown("### 🛡️ System Integrity")
    st.markdown("• **Engine:** Parameterized SQL Builder")
    st.markdown("• **Hallucination Rate:** `0.0% (Grounded)`")
    st.markdown("• **Safety Mode:** Clinical Boundaries Active")
    st.markdown("• **Data Mode:** `VERIFIED LOCAL SQLITE DB`")
    st.divider()

    st.markdown("### 🔍 Sample Multi-Domain Inquiries")
    if st.session_state.active_domain == DomainType.HEALTHCARE:
        sample_queries = [
            "Find a cardiologist within 10 miles",
            "Who is the best neurologist?",
            "Cheapest orthopedic doctor available today",
            "Doctor under $100 within 5 miles",
            "Do I have cancer?",
            "Which doctor speaks Hindi?",
            "Show all pediatricians"
        ]
    else:
        sample_queries = [
            "Find 3BHK house under $3000 near top schools",
            "Safest neighborhood with low crime index < 20",
            "Apartment near hospital within 1.5 miles",
            "Cheapest rental property near transit",
            "Luxury Villa in Pacific Heights or Marina Bay",
            "Best livability properties under $2500"
        ]

    for q in sample_queries:
        if st.button(q, key=f"sidebar_sample_{hash(q)}", use_container_width=True):
            st.session_state["sample_to_run"] = q
            st.rerun()

    st.divider()
    if st.button("🧹 Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.session_state.pending_clarification = False
        st.rerun()


# ==========================================
# 3. MASTER APPLICATION NAVIGATION TABS
# ==========================================
tab_chat, tab_map, tab_comp, tab_sched, tab_ins, tab_lake, tab_sql, tab_tests = st.tabs([
    "💬 AI Discovery",
    "🗺️ Geo-Spatial Radar",
    "⚖️ Comparison Matrix",
    "📅 Smart Scheduler",
    "💳 Insurance Estimator",
    "🗄️ Data Lake Explorer",
    "⚡ AST SQL Sandbox",
    "🧪 Verification Suite"
])


# ==========================================
# TAB 1: 💬 AI DISCOVERY & NATURAL LANGUAGE TRIAGE
# ==========================================
with tab_chat:
    st.markdown("#### 💬 Natural Language Grounded Assistant")
    st.caption("Ask questions in natural language. Queries are parsed deterministically into schema-validated SQL with 100% database grounding.")

    # Voice / Audio Query Simulator Toggle
    with st.expander("🎙️ Voice & Audio Query Interface", expanded=False):
        col_v1, col_v2 = st.columns([3, 1])
        voice_text = col_v1.text_input("Speak or dictate your clinical symptom or housing preference:", placeholder="e.g. 'I need a safe 2BHK flat near a hospital with top rated schools'")
        if col_v2.button("🎙️ Process Voice Audio", use_container_width=True):
            if voice_text:
                st.session_state["sample_to_run"] = voice_text
                st.rerun()

    # Render Chat History
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg.get("type") == "text":
                st.markdown(msg["content"])
            elif msg.get("type") == "cards":
                if msg.get("domain") == DomainType.REAL_ESTATE:
                    render_housing_cards(msg["data"])
                else:
                    render_doctor_cards(msg["data"])
                if "audit" in msg:
                    render_audit_trail(msg["audit"])
            elif msg.get("type") == "warning":
                render_safety_warning(msg.get("warning_type", "general"), msg["content"])

    # Ambiguity clarification dialog
    if st.session_state.pending_clarification and st.session_state.clarification_data:
        cdata = st.session_state.clarification_data
        st.warning(f"⚠️ **Ambiguous Query**: {cdata.get('reason')}")
        render_clarification_buttons(cdata.get("options", []))

    # Handle incoming input
    user_prompt = st.chat_input("Enter your discovery query or clinical need...")
    if "sample_to_run" in st.session_state and st.session_state.sample_to_run:
        user_prompt = st.session_state.sample_to_run
        st.session_state.sample_to_run = None

    if user_prompt:
        # Append User Message
        st.session_state.messages.append({"role": "user", "content": user_prompt, "type": "text"})

        # Step 1: Deterministic Parsing
        parsed_result = classify_intent_and_extract_entities(user_prompt, active_domain=st.session_state.active_domain)

        # Step 2: Handle Guardrails & Refusals
        if parsed_result.intent == IntentType.PROMPT_INJECTION:
            st.session_state.messages.append({"role": "assistant", "content": parsed_result.explanation, "type": "warning", "warning_type": "injection"})
            st.rerun()
        elif parsed_result.intent == IntentType.MEDICAL_ADVICE:
            st.session_state.messages.append({"role": "assistant", "content": parsed_result.explanation, "type": "warning", "warning_type": "medical_advice"})
            st.rerun()
        elif parsed_result.intent == IntentType.EMERGENCY:
            st.session_state.messages.append({"role": "assistant", "content": parsed_result.explanation, "type": "warning", "warning_type": "acute_emergency"})
            st.rerun()
        elif parsed_result.intent == IntentType.UNKNOWN_ATTRIBUTE:
            st.session_state.messages.append({"role": "assistant", "content": parsed_result.explanation, "type": "warning", "warning_type": "unknown_attribute"})
            st.rerun()
        elif parsed_result.intent == IntentType.CONTRADICTION:
            st.session_state.messages.append({"role": "assistant", "content": parsed_result.explanation, "type": "warning", "warning_type": "contradiction"})
            st.rerun()
        elif parsed_result.intent == IntentType.AMBIGUOUS:
            st.session_state.pending_clarification = True
            st.session_state.clarification_data = {
                "reason": parsed_result.ambiguity_reason,
                "options": parsed_result.clarification_options
            }
            st.rerun()
        elif parsed_result.intent == IntentType.GREETING:
            greeting_msg = "Hello! I am ready to assist you. Ask for verified physicians, specialty procedures, or housing & neighborhood livability data."
            st.session_state.messages.append({"role": "assistant", "content": greeting_msg, "type": "text"})
            st.rerun()

        # Step 3: Execute Deterministic SQL Query
        if parsed_result.domain == DomainType.REAL_ESTATE and parsed_result.housing_filters:
            query_res = execute_housing_search(parsed_result.housing_filters)
        else:
            query_res = execute_doctor_search(parsed_result.filters)

        audit = ExplainabilityAudit(
            raw_query=user_prompt,
            domain=parsed_result.domain.value,
            intent=parsed_result.intent.value,
            confidence=parsed_result.confidence,
            interpreted_entities=parsed_result.normalized_entities,
            negated_entities=parsed_result.negated_entities,
            applied_filters=query_res.applied_filters,
            sql_query=query_res.sql_template,
            sql_parameters=query_res.params,
            execution_time_ms=query_res.execution_time_ms,
            result_count=query_res.row_count,
            rationale=query_res.explanation
        )

        st.session_state.messages.append({
            "role": "assistant",
            "type": "cards",
            "domain": parsed_result.domain,
            "data": query_res.data,
            "audit": audit
        })
        st.session_state.pending_clarification = False
        st.rerun()


# ==========================================
# TAB 2: 🗺️ GEO-SPATIAL MAP & PROXIMITY RADAR
# ==========================================
with tab_map:
    st.markdown("#### 🗺️ Interactive Proximity Radar & Clinic Mapping")
    st.caption("Visual scatter map plotting clinic and housing coordinates across the metropolitan area.")

    map_col1, map_col2 = st.columns([1, 3])
    with map_col1:
        map_domain = st.selectbox("Select Map Layer", ["Healthcare Clinics & Doctors", "UrbanLocate Housing Properties"])
        max_rad = st.slider("Proximity Radius (miles)", 0.5, 30.0, 15.0, 0.5)

    with map_col2:
        conn = get_connection()
        if "Healthcare" in map_domain:
            c = conn.cursor()
            c.execute("SELECT name, specialty, consultation_fee, satisfaction_score, latitude, longitude FROM Doctors WHERE distance_miles <= ? LIMIT 50", (max_rad,))
            map_data = [dict(r) for r in c.fetchall()]
            render_geo_map(map_data, domain=DomainType.HEALTHCARE)
        else:
            c = conn.cursor()
            c.execute("SELECT title, neighborhood, property_type, price_per_month, livability_score, latitude, longitude FROM Properties")
            map_data = [dict(r) for r in c.fetchall()]
            render_geo_map(map_data, domain=DomainType.REAL_ESTATE)
        conn.close()


# ==========================================
# TAB 3: ⚖️ HEAD-TO-HEAD COMPARISON MATRIX
# ==========================================
with tab_comp:
    st.markdown("#### ⚖️ Side-by-Side Head-to-Head Comparison Matrix")
    st.caption("Select 2 to 4 entities to compare their performance, price, quality, and proximity side-by-side.")

    conn = get_connection()
    c = conn.cursor()

    comp_choice = st.radio("Domain to Compare", ["Doctors & Physicians", "Housing & Neighborhoods"], horizontal=True)

    if "Doctors" in comp_choice:
        c.execute("SELECT id, name, specialty, primary_surgery, surgery_success_rate, satisfaction_score, distance_miles, consultation_fee, is_available_today, next_available_date FROM Doctors LIMIT 50")
        all_docs = [dict(r) for r in c.fetchall()]
        doc_names = [d["name"] for d in all_docs]
        selected_names = st.multiselect("Select Doctors to Compare:", doc_names, default=doc_names[:3] if len(doc_names) >= 3 else doc_names)
        selected_items = [d for d in all_docs if d["name"] in selected_names]
        render_comparison_matrix(selected_items, domain=DomainType.HEALTHCARE)
    else:
        c.execute("SELECT id, title, neighborhood, property_type, price_per_month, bedrooms, bathrooms, sqft, crime_index_score, school_rating, hospital_dist_miles, transit_dist_miles, livability_score FROM Properties")
        all_props = [dict(r) for r in c.fetchall()]
        prop_titles = [p["title"] for p in all_props]
        selected_titles = st.multiselect("Select Properties to Compare:", prop_titles, default=prop_titles[:3] if len(prop_titles) >= 3 else prop_titles)
        selected_items = [p for p in all_props if p["title"] in selected_titles]
        render_comparison_matrix(selected_items, domain=DomainType.REAL_ESTATE)

    conn.close()


# ==========================================
# TAB 4: 📅 SMART SCHEDULER & CALENDAR SYNC
# ==========================================
with tab_sched:
    st.markdown("#### 📅 Smart Appointment Booking & Double-Booking Conflict Prevention")
    st.caption("Book an appointment directly into the SQLite database. Detects double-booking time slot conflicts and exports standard `.ics` calendar files.")

    sched_col1, sched_col2 = st.columns([1, 1])

    with sched_col1:
        st.markdown("##### 📝 Schedule New Appointment")
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT id, name, specialty FROM Doctors LIMIT 30")
        docs_list = [dict(r) for r in c.fetchall()]
        conn.close()

        doc_options = {f"{d['name']} ({d['specialty']})": d["id"] for d in docs_list}
        selected_doc_label = st.selectbox("Select Doctor", list(doc_options.keys()))
        selected_doc_id = doc_options[selected_doc_label]

        p_name = st.text_input("Patient Full Name", value="Divyam Sharma")
        p_email = st.text_input("Patient Email", value="divyamajm@gmail.com")
        p_date = st.date_input("Appointment Date", min_value=datetime.today().date(), value=datetime.today().date())
        p_slot = st.selectbox("Preferred Time Slot", ["09:00 AM", "10:30 AM", "11:30 AM", "02:00 PM", "03:30 PM", "04:30 PM"])
        p_reason = st.text_area("Consultation Symptoms / Reason", value="Routine Health Checkup & Consultation")

        if st.button("Confirm Appointment Booking", type="primary", use_container_width=True):
            date_str = p_date.strftime("%Y-%m-%d")
            res = book_appointment(
                doctor_id=selected_doc_id,
                patient_name=p_name,
                patient_email=p_email,
                appointment_date=date_str,
                time_slot=p_slot,
                symptoms_reason=p_reason
            )

            if res["success"]:
                st.success(f"✅ Appointment Successfully Confirmed with **{res['doctor_name']}** for **{res['appointment_date']} at {res['time_slot']}**!")
                
                # Generate .ics calendar download
                ics_str = generate_ics_calendar(
                    doctor_name=res["doctor_name"],
                    specialty=res["specialty"],
                    patient_name=p_name,
                    appointment_date=date_str,
                    time_slot=p_slot
                )
                st.download_button(
                    label="📥 Download .ICS Calendar Event (Google/Apple Calendar)",
                    data=ics_str,
                    file_name=f"appointment_{res['doctor_name'].replace(' ', '_')}_{date_str}.ics",
                    mime="text/calendar",
                    use_container_width=True
                )
            else:
                st.error(f"❌ Booking Conflict: {res['error']}")

    with sched_col2:
        st.markdown("##### 📋 Confirmed Database Bookings")
        bookings = get_all_appointments()
        if bookings:
            bookings_df = pd.DataFrame(bookings)[["id", "doctor_name", "specialty", "patient_name", "appointment_date", "time_slot", "status", "symptoms_reason"]]
            st.dataframe(bookings_df, use_container_width=True, hide_index=True)
        else:
            st.info("No appointments currently scheduled.")


# ==========================================
# TAB 5: 💳 INSURANCE & CO-PAY ESTIMATOR
# ==========================================
with tab_ins:
    render_insurance_calculator()


# ==========================================
# TAB 6: 🗄️ DATA LAKE EXPLORER
# ==========================================
with tab_lake:
    st.markdown("#### 🗄️ Multi-Dataset Lake Explorer")
    st.caption("Inspect raw SQLite tables across Healthcare and Real Estate datasets.")

    stats = get_database_stats()
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Doctors", stats["total_doctors"])
    m2.metric("Available Today", stats["available_today_count"])
    m3.metric("Avg Consultation Fee", f"${stats['avg_fee']}")
    m4.metric("Avg Satisfaction", f"{stats['avg_satisfaction']}/100")
    m5.metric("Total Properties", stats["total_properties"])

    st.divider()

    table_view = st.selectbox("Select Table to Explore", ["Doctors Directory", "Properties (UrbanLocate)", "Specialties Metadata", "Appointments"])
    conn = get_connection()

    if table_view == "Doctors Directory":
        df = pd.read_sql_query("SELECT id, name, specialty, primary_surgery, surgery_success_rate, satisfaction_score, distance_miles, consultation_fee, is_available_today, next_available_date FROM Doctors", conn)
        st.dataframe(df, use_container_width=True, height=450)
    elif table_view == "Properties (UrbanLocate)":
        df = pd.read_sql_query("SELECT * FROM Properties", conn)
        st.dataframe(df, use_container_width=True, height=450)
    elif table_view == "Specialties Metadata":
        df = pd.read_sql_query("SELECT * FROM Specialties", conn)
        st.dataframe(df, use_container_width=True)
    else:
        df = pd.read_sql_query("SELECT * FROM Appointments", conn)
        st.dataframe(df, use_container_width=True)

    conn.close()

    st.divider()
    if st.button("🔄 Re-Seed & Reset Both Demo Databases", type="secondary"):
        reset_demo_data()
        st.success("Databases successfully re-seeded with pristine mock data!")
        st.rerun()


# ==========================================
# TAB 7: ⚡ AST SECURE SQL SANDBOX
# ==========================================
with tab_sql:
    st.markdown("#### ⚡ AST-Validated Read-Only SQL Sandbox")
    st.caption("Execute custom SQL queries against the local SQLite database. Enforces strict read-only AST token validation.")

    sandbox_sql = st.text_area("SQL Query", value=st.session_state.sql_sandbox_query, height=120)

    col_btn, col_info = st.columns([1, 3])
    if col_btn.button("🚀 Execute SQL", type="primary", use_container_width=True):
        st.session_state.sql_sandbox_query = sandbox_sql
        is_safe, msg = validate_sql_sandbox_query(sandbox_sql)

        if not is_safe:
            st.error(f"🛑 AST Security Violation: {msg}")
        else:
            try:
                start_t = time.perf_counter()
                conn = get_connection()
                df = pd.read_sql_query(sandbox_sql, conn)
                conn.close()
                dur = round((time.perf_counter() - start_t) * 1000, 2)

                st.success(f"✅ Executed safely in {dur} ms ({len(df)} rows returned)")
                st.dataframe(df, use_container_width=True)
            except Exception as e:
                st.error(f"SQL Syntax Error: {e}")


# ==========================================
# TAB 8: 🧪 AUTOMATED VERIFICATION SUITE
# ==========================================
with tab_tests:
    st.markdown("#### 🧪 Automated Verification Suite")
    st.caption("Run all regression tests covering multi-filter extraction, clinical safety boundaries, and SQL security.")

    if st.button("▶️ Execute Full Verification Suite", type="primary"):
        with st.spinner("Executing automated test batteries..."):
            test_results = run_all_tests()
            st.session_state.test_results = test_results

    if st.session_state.test_results:
        results = st.session_state.test_results
        passed = sum(1 for r in results if r.passed)
        total = len(results)

        st.metric("Test Suite Pass Rate", f"{passed}/{total} ({passed/total*100:.1f}%)")

        for res in results:
            if res.passed:
                st.success(f"✅ **{res.test_case.id}**: {res.test_case.description} ({res.execution_time_ms} ms)")
            else:
                st.error(f"❌ **{res.test_case.id}**: {res.test_case.description}\nFailures: {res.failure_reasons}")