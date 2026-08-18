"""
MedData AI - Enterprise Triage & Doctor Discovery Agent
Production-style Streamlit Application with Deterministic Query Engine,
Explainability Audit Trail, Data Lake Explorer, Safe SQL Sandbox, and Automated Test Suite.
"""

import time
import pandas as pd
import streamlit as st

from models import (
    IntentType, CanonicalSpecialty, SortMetric, SortOrder,
    SearchFilters, ExplainabilityAudit
)
from database import (
    init_database, get_connection, get_database_stats, 
    reset_demo_data, DB_PATH
)
from intent_parser import parse_intent_and_filters
from query_engine import execute_doctor_search, get_doctor_details_by_id
from safety import validate_sql_sandbox_query
from ui_components import (
    apply_custom_styles, render_app_header, render_doctor_cards,
    render_audit_trail, render_booking_modal
)
from tests.test_suite import run_all_tests, run_sql_sandbox_security_tests
from tests.test_cases import ALL_TEST_CASES

# ==========================================
# 1. APPLICATION INITIALIZATION & CONFIG
# ==========================================
st.set_page_config(
    page_title="MedData AI - Triage & Doctor Discovery",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply enterprise styles
apply_custom_styles()

# Initialize SQLite database (seeds 200 unique doctors if empty)
init_database()

# Session State Initialization
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Hello. I am the **MedData AI Triage & Discovery Agent**.\n\n"
                "I provide deterministic, database-grounded discovery across our verified physician directory. "
                "You can search by specialty, affordability, distance, surgical success rate, patient satisfaction, "
                "or availability.\n\n"
                "💡 *Example: 'Find a cardiologist within 10 miles under $150 available today'*"
            ),
            "type": "text"
        }
    ]

if "pending_clarification" not in st.session_state:
    st.session_state.pending_clarification = False

if "clarification_data" not in st.session_state:
    st.session_state.clarification_data = None

if "selected_doctor_for_booking" not in st.session_state:
    st.session_state.selected_doctor_for_booking = None

if "sql_sandbox_query" not in st.session_state:
    st.session_state.sql_sandbox_query = "SELECT specialty, COUNT(*) as total_doctors, AVG(consultation_fee) as avg_fee, AVG(satisfaction_score) as avg_satisfaction FROM Doctors GROUP BY specialty;"

if "test_results" not in st.session_state:
    st.session_state.test_results = None

# ==========================================
# 2. HEADER & SIDEBAR NAVIGATION
# ==========================================
render_app_header()

with st.sidebar:
    st.markdown("### 🏥 System Status")
    st.markdown("• **Engine:** Grounded SQL Engine")
    st.markdown("• **Hallucination Rate:** `0.0% (Zero Guessing)`")
    st.markdown("• **Safety Mode:** Clinical Boundary Enforced")
    st.markdown("• **Data Mode:** `DEMO / MOCK HEALTHCARE DB`")
    st.divider()

    st.markdown("### 🔍 Sample Test Inquiries")
    sample_queries = [
        "Find a cardiologist",
        "Who is the best cardiologist?",
        "Nearest neurologist within 5 miles",
        "Cheapest orthopedic doctor",
        "Cardiologist available today under $100",
        "I don't need a cardiologist",
        "Do I have cancer?",
        "Which doctor speaks Hindi?",
        "Find a free doctor charging $500",
        "Show all pediatricians"
    ]
    for sq in sample_queries:
        if st.button(sq, key=f"sq_{sq}", use_container_width=True):
            st.session_state.preset_prompt = sq
            st.rerun()

    st.divider()
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.messages = [st.session_state.messages[0]]
        st.session_state.pending_clarification = False
        st.session_state.clarification_data = None
        st.session_state.selected_doctor_for_booking = None
        st.rerun()

# ==========================================
# 3. MAIN TABS ARCHITECTURE
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs([
    "💬 AI Triage & Discovery",
    "🗄️ Database Lake Explorer",
    "⚡ Secure SQL Sandbox",
    "🧪 Automated Verification Suite"
])

# ==========================================
# TAB 1: AI TRIAGE & DOCTOR DISCOVERY
# ==========================================
with tab1:
    # Booking Modal (if doctor selected)
    if st.session_state.selected_doctor_for_booking:
        render_booking_modal(st.session_state.selected_doctor_for_booking)
        st.divider()

    # Render Chat History
    for idx, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

            # Render Doctor Cards if data available
            if msg.get("type") == "data" and msg.get("doctors"):
                render_doctor_cards(msg["doctors"], context_key=f"msg_{idx}")
            
            # Render Relaxation Options if 0 results
            if msg.get("type") == "zero_results" and msg.get("relaxation_suggestions"):
                st.markdown("#### 🔄 Suggested Filter Relaxations:")
                rel_cols = st.columns(min(len(msg["relaxation_suggestions"]), 3))
                for r_idx, sugg in enumerate(msg["relaxation_suggestions"]):
                    with rel_cols[r_idx % 3]:
                        if st.button(f"{sugg['label']} ({sugg['result_count']} matches)", key=f"rel_{idx}_{r_idx}"):
                            # Apply relaxed query
                            relaxed_filters = msg["applied_filters_obj"]
                            if sugg["action"] == "remove_availability":
                                relaxed_filters.available_today = None
                            elif sugg["action"] == "expand_distance":
                                relaxed_filters.max_distance = sugg["new_distance"]
                            elif sugg["action"] == "increase_fee":
                                relaxed_filters.max_fee = sugg["new_fee"]
                            elif sugg["action"] == "lower_success_rate":
                                relaxed_filters.min_success_rate = sugg["new_rate"]
                            
                            res = execute_doctor_search(relaxed_filters)
                            audit = ExplainabilityAudit(
                                raw_query=f"Relaxation applied: {sugg['label']}",
                                intent="filter_relaxation",
                                confidence=1.0,
                                interpreted_entities={"relaxation_action": sugg["action"]},
                                negated_entities=[],
                                applied_filters=res.applied_filters,
                                sql_query=res.sql_template,
                                sql_parameters=res.params,
                                execution_time_ms=res.execution_time_ms,
                                result_count=res.row_count,
                                rationale=res.explanation
                            )
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": f"Applied relaxation: **{sugg['label']}**. Found **{res.row_count}** matching doctor(s):",
                                "type": "data",
                                "doctors": res.data,
                                "audit": audit
                            })
                            st.rerun()

            # Render Audit Trail expander
            if msg.get("audit"):
                render_audit_trail(msg["audit"])

    # Ambiguity Clarification Interceptor
    if st.session_state.pending_clarification and st.session_state.clarification_data:
        cdata = st.session_state.clarification_data
        with st.chat_message("assistant"):
            st.markdown(cdata.get("explanation", "Please clarify your optimization criteria:"))
            
            # Render clarification buttons
            clarification_options = cdata.get("clarification_options", [])
            cols = st.columns(min(len(clarification_options), 5))
            
            for i, opt in enumerate(clarification_options):
                with cols[i % len(cols)]:
                    if st.button(opt, key=f"clarify_btn_{i}", use_container_width=True):
                        pending_filters = cdata.get("filters", SearchFilters())
                        
                        # Map button choice to sorting metric
                        if "Satisfaction" in opt:
                            pending_filters.sort_by = SortMetric.SATISFACTION_SCORE
                            pending_filters.sort_order = SortOrder.DESC
                            sort_label = "Highest Patient Satisfaction"
                        elif "Success Rate" in opt:
                            pending_filters.sort_by = SortMetric.SURGERY_SUCCESS_RATE
                            pending_filters.sort_order = SortOrder.DESC
                            sort_label = "Highest Surgical Success Rate"
                        elif "Distance" in opt:
                            pending_filters.sort_by = SortMetric.DISTANCE_MILES
                            pending_filters.sort_order = SortOrder.ASC
                            sort_label = "Closest Distance"
                        elif "Fee" in opt or "Cost" in opt:
                            pending_filters.sort_by = SortMetric.CONSULTATION_FEE
                            pending_filters.sort_order = SortOrder.ASC
                            sort_label = "Lowest Consultation Fee"
                        elif "Availability" in opt:
                            pending_filters.sort_by = SortMetric.NEXT_AVAILABLE_DATE
                            pending_filters.sort_order = SortOrder.ASC
                            sort_label = "Earliest Availability"
                        elif "Cardiology" in opt:
                            pending_filters.specialty = CanonicalSpecialty.CARDIOLOGY
                            sort_label = "Cardiology"
                        elif "Neurology" in opt:
                            pending_filters.specialty = CanonicalSpecialty.NEUROLOGY
                            sort_label = "Neurology"
                        elif "Orthopedics" in opt:
                            pending_filters.specialty = CanonicalSpecialty.ORTHOPEDICS
                            sort_label = "Orthopedics"
                        elif "Pediatrics" in opt:
                            pending_filters.specialty = CanonicalSpecialty.PEDIATRICS
                            sort_label = "Pediatrics"
                        elif "Emergency" in opt:
                            pending_filters.specialty = CanonicalSpecialty.EMERGENCY
                            sort_label = "Emergency"
                        else:
                            sort_label = opt

                        st.session_state.messages.append({
                            "role": "user",
                            "content": f"Optimized by: {sort_label}",
                            "type": "text"
                        })

                        # Execute query with resolved criterion
                        query_result = execute_doctor_search(pending_filters)
                        spec_info = f" in **{pending_filters.specialty.value}**" if pending_filters.specialty else ""
                        
                        audit = ExplainabilityAudit(
                            raw_query=f"Clarified optimization: {sort_label}",
                            intent="clarified_search",
                            confidence=1.0,
                            interpreted_entities={"selected_criterion": sort_label},
                            negated_entities=[],
                            applied_filters=query_result.applied_filters,
                            sql_query=query_result.sql_template,
                            sql_parameters=query_result.params,
                            execution_time_ms=query_result.execution_time_ms,
                            result_count=query_result.row_count,
                            rationale=query_result.explanation
                        )

                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": f"Top verified doctors{spec_info} ranked by **{sort_label}**:",
                            "type": "data",
                            "doctors": query_result.data,
                            "audit": audit
                        })

                        st.session_state.pending_clarification = False
                        st.session_state.clarification_data = None
                        st.rerun()

    # Chat Input Handler
    preset = st.session_state.pop("preset_prompt", None)
    prompt = st.chat_input("Ask about doctors, specialties, costs, distance, or availability...") or preset

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt, "type": "text"})

        # Step 1: Deterministic NLP & Guardrails Parsing
        classification = parse_intent_and_filters(prompt)

        # Step 2: Handle Guardrails & Refusals
        if classification.intent in [
            IntentType.MEDICAL_ADVICE, IntentType.EMERGENCY, 
            IntentType.UNKNOWN_ATTRIBUTE, IntentType.CONTRADICTION,
            IntentType.PROMPT_INJECTION
        ]:
            st.session_state.messages.append({
                "role": "assistant",
                "content": classification.explanation,
                "type": "alert"
            })
            st.session_state.pending_clarification = False
            st.session_state.clarification_data = None
            st.rerun()

        # Step 3: Handle Greetings
        elif classification.intent == IntentType.GREETING:
            st.session_state.messages.append({
                "role": "assistant",
                "content": classification.explanation,
                "type": "text"
            })
            st.rerun()

        # Step 4: Handle Ambiguity
        elif classification.ambiguity_detected:
            st.session_state.pending_clarification = True
            st.session_state.clarification_data = {
                "explanation": classification.explanation,
                "clarification_options": classification.clarification_options,
                "filters": classification.filters,
                "raw_prompt": prompt
            }
            st.rerun()

        # Step 5: Handle Executable Search / Directory / Doctor Details
        else:
            query_res = execute_doctor_search(classification.filters)

            audit = ExplainabilityAudit(
                raw_query=prompt,
                intent=classification.intent.value,
                confidence=classification.confidence,
                interpreted_entities=classification.normalized_entities,
                negated_entities=classification.negated_entities,
                applied_filters=query_res.applied_filters,
                sql_query=query_res.sql_template,
                sql_parameters=query_res.params,
                execution_time_ms=query_res.execution_time_ms,
                result_count=query_res.row_count,
                rationale=query_res.explanation
            )

            if query_res.row_count > 0:
                spec_str = f" in **{classification.filters.specialty.value}**" if classification.filters.specialty else ""
                content_msg = f"Found **{query_res.row_count}** matching doctor(s){spec_str} from the verified database:"
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": content_msg,
                    "type": "data",
                    "doctors": query_res.data,
                    "audit": audit
                })
            else:
                zero_content = (
                    "⚠️ **Zero Results Found**: No doctors in the demo database match all of your specified criteria.\n\n"
                    f"**Applied Constraints:** `{query_res.applied_filters}`\n\n"
                    "The system will **never silently relax filters**. You may select a controlled relaxation below:"
                )
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": zero_content,
                    "type": "zero_results",
                    "relaxation_suggestions": query_res.relaxation_suggestions,
                    "applied_filters_obj": classification.filters,
                    "audit": audit
                })

            st.rerun()


# ==========================================
# TAB 2: DATABASE LAKE EXPLORER
# ==========================================
with tab2:
    st.markdown("### 🗄️ Enterprise Data Lake & Directory Explorer")
    st.caption("Live, real-time analytics across the local SQLite clinical database.")

    stats = get_database_stats()

    # Metric Cards
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Total Active Doctors", str(stats["total_doctors"]))
    m2.metric("Specialties", str(stats["total_specialties"]))
    m3.metric("Avg Consultation Fee", f"${stats['avg_fee']}")
    m4.metric("Available Today", str(stats["available_today_count"]))
    m5.metric("Avg Satisfaction", f"{stats['avg_satisfaction']}/100")
    m6.metric("Avg Success Rate", f"{stats['avg_success_rate']}%")

    st.divider()

    # Specialty Breakdown Metrics & Table
    st.markdown("#### 📊 Specialty Overview & Performance")
    spec_df = pd.DataFrame(stats["specialty_breakdown"])
    spec_df.columns = ["Specialty", "Total Doctors", "Avg Fee ($)", "Avg Satisfaction Score"]
    st.dataframe(spec_df, use_container_width=True, hide_index=True)

    st.divider()

    # Interactive Explorer Controls
    st.markdown("#### 🔍 Filter Database Records")
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    
    spec_choice = col_f1.selectbox("Filter Specialty", ["All Specialties", "Cardiology", "Neurology", "Orthopedics", "Pediatrics", "Emergency"])
    max_dist_filter = col_f2.slider("Max Distance (miles)", 0.0, 30.0, 30.0, 0.5)
    max_fee_filter = col_f3.slider("Max Consultation Fee ($)", 0, 500, 500, 25)
    avail_only = col_f4.checkbox("Available Today Only", value=False)

    # Dynamic Explorer Query
    exp_filters = SearchFilters(
        specialty=CanonicalSpecialty(spec_choice) if spec_choice != "All Specialties" else None,
        max_distance=max_dist_filter if max_dist_filter < 30.0 else None,
        max_fee=max_fee_filter if max_fee_filter < 500 else None,
        available_today=True if avail_only else None,
        limit=200
    )
    exp_result = execute_doctor_search(exp_filters)

    if exp_result.data:
        full_df = pd.DataFrame(exp_result.data)
        st.dataframe(full_df, use_container_width=True, height=450)
        st.caption(f"Displaying **{len(full_df)}** matching rows. Executed in {exp_result.execution_time_ms} ms.")
    else:
        st.warning("No doctors match the selected explorer filters.")

    st.divider()
    # Reset Demo Database button
    st.markdown("#### 🔄 Database Maintenance")
    if st.button("Re-Seed & Reset Demo Data", type="secondary"):
        reset_demo_data()
        st.success("✅ Demo database successfully re-seeded with 200 unique doctor identities and indexes.")
        time.sleep(1)
        st.rerun()


# ==========================================
# TAB 3: SECURE SQL SANDBOX
# ==========================================
with tab3:
    st.markdown("### ⚡ Live SQL Sandbox (Strict Read-Only Enforcement)")
    st.markdown(
        "Inspect and query the clinical SQLite schema directly. For security and integrity, **all write/mutation "
        "operations (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `PRAGMA`) are strictly rejected by the validator.**"
    )

    with st.expander("📖 Database Schema Reference"):
        st.code("""
-- Doctors Table
CREATE TABLE Doctors (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    specialty TEXT NOT NULL,
    primary_surgery TEXT NOT NULL,
    surgery_success_rate REAL NOT NULL,
    satisfaction_score INTEGER NOT NULL,
    distance_miles REAL NOT NULL,
    consultation_fee INTEGER NOT NULL,
    is_available_today TEXT NOT NULL,  -- 'Yes' or 'No'
    next_available_date TEXT NOT NULL  -- 'YYYY-MM-DD'
);
        """, language="sql")

    # Sample queries dropdown
    sample_sql_queries = {
        "Custom Query": "",
        "Specialty Summary & Avg Metrics": "SELECT specialty, COUNT(*) as total_doctors, AVG(consultation_fee) as avg_fee, AVG(satisfaction_score) as avg_score, AVG(surgery_success_rate) as avg_success FROM Doctors GROUP BY specialty;",
        "Top 10 Highest Satisfaction Doctors": "SELECT name, specialty, satisfaction_score, surgery_success_rate, consultation_fee FROM Doctors ORDER BY satisfaction_score DESC LIMIT 10;",
        "Available Today Under $100": "SELECT name, specialty, consultation_fee, distance_miles, is_available_today FROM Doctors WHERE is_available_today = 'Yes' AND consultation_fee <= 100 ORDER BY distance_miles ASC;",
        "Simulated Malicious Query (Test Rejection)": "DROP TABLE Doctors;"
    }

    selected_sample = st.selectbox("Load Sample Query:", list(sample_sql_queries.keys()))
    if selected_sample != "Custom Query" and sample_sql_queries[selected_sample]:
        st.session_state.sql_sandbox_query = sample_sql_queries[selected_sample]

    query_input = st.text_area(
        "SQL Query Editor (SELECT / WITH only):",
        value=st.session_state.sql_sandbox_query,
        height=140
    )

    col_btn, col_info = st.columns([1, 4])
    if col_btn.button("▶ Run Safe Query", type="primary", use_container_width=True):
        st.session_state.sql_sandbox_query = query_input
        
        # Step 1: Validate Read-Only Safety
        is_safe, safety_msg = validate_sql_sandbox_query(query_input)
        
        if not is_safe:
            st.error(f"❌ **Query Rejected by Safety Guardrail**: {safety_msg}")
        else:
            try:
                conn = get_connection()
                start = time.perf_counter()
                res_df = pd.read_sql_query(query_input, conn)
                elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
                conn.close()

                st.success(f"✅ Query executed successfully in **{elapsed_ms} ms** ({len(res_df)} rows returned).")
                st.dataframe(res_df, use_container_width=True)
            except Exception as e:
                st.error(f"SQL Execution Error: {str(e)}")


# ==========================================
# TAB 4: AUTOMATED VERIFICATION SUITE
# ==========================================
with tab4:
    st.markdown("### 🧪 Automated Verification & Quality Assurance Suite")
    st.markdown(
        "Run end-to-end regression tests verifying intent classification, entity extraction, "
        "ambiguity interception, negation handling, safety guardrails, and deterministic database grounding."
    )

    if st.button("▶ Run Full Verification Suite", type="primary"):
        with st.spinner("Executing all automated test batteries..."):
            test_results = run_all_tests()
            sql_sec_results = run_sql_sandbox_security_tests()
            st.session_state.test_results = {
                "suite_results": test_results,
                "sql_security": sql_sec_results
            }

    if st.session_state.test_results:
        t_data = st.session_state.test_results["suite_results"]
        sql_sec = st.session_state.test_results["sql_security"]

        passed_count = sum(1 for r in t_data if r.passed)
        total_count = len(t_data)
        pass_rate = round((passed_count / total_count) * 100, 1)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Test Cases", str(total_count))
        c2.metric("Passed Tests", str(passed_count), delta=f"{pass_rate}%")
        c3.metric("Failed Tests", str(total_count - passed_count))
        c4.metric("SQL Security Tests", f"{sql_sec['passed']}/{sql_sec['total']}")

        st.divider()

        # Detailed Test Table
        st.markdown("#### 📋 Test Results Breakdown")
        table_rows = []
        for r in t_data:
            tc = r.test_case
            status_str = "✅ PASS" if r.passed else "❌ FAIL"
            table_rows.append({
                "ID": tc.id,
                "Status": status_str,
                "Category": tc.category,
                "Input Prompt": tc.input_prompt,
                "Expected Intent": tc.expected_intent.value,
                "Actual Intent": r.actual_intent.value,
                "Ambiguity": "Yes" if r.actual_ambiguity else "No",
                "Rows": r.result_count,
                "Time (ms)": r.execution_time_ms
            })

        st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

        st.divider()

        # Expandable failure and audit inspection
        st.markdown("#### 🔍 Individual Test Case Details")
        for r in t_data:
            tc = r.test_case
            icon = "✅" if r.passed else "❌"
            with st.expander(f"{icon} [{tc.id}] {tc.category}: '{tc.input_prompt}'"):
                st.write(f"**Description:** {tc.description}")
                st.write(f"**Expected Intent:** `{tc.expected_intent.value}` | **Actual Intent:** `{r.actual_intent.value}`")
                if r.actual_sql:
                    st.code(r.actual_sql, language="sql")
                    st.write(f"**Parameters:** `{r.actual_params}` | **Result Rows:** {r.result_count}")
                if not r.passed:
                    st.error("Failure Reasons:\n" + "\n".join([f"• {f}" for f in r.failure_reasons]))
                else:
                    st.success("Verification: Grounding and behavior matches all assertions.")