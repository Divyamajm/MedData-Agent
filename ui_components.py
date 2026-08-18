"""
MedData AI - UI Components & Enterprise Design System
Provides modern healthcare CSS styling, doctor result cards, explainability audit panels,
clarification dialogs, safety alerts, and simulation booking widgets.
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, List, Optional
from models import ExplainabilityAudit, QueryResult


CUSTOM_CSS = """
<style>
/* MedData Enterprise Healthcare Theme */
.main-header-container {
    background: linear-gradient(135deg, #0d233a 0%, #1a365d 100%);
    padding: 1.5rem 2rem;
    border-radius: 12px;
    color: white;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}
.header-badge {
    background-color: #e53e3e;
    color: white;
    font-size: 0.75rem;
    font-weight: 700;
    padding: 0.25rem 0.6rem;
    border-radius: 20px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    display: inline-block;
    margin-bottom: 0.5rem;
}
.doctor-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 1.25rem;
    margin-bottom: 1rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.03);
    transition: all 0.2s ease-in-out;
}
.doctor-card:hover {
    border-color: #3182ce;
    box-shadow: 0 4px 12px rgba(49, 130, 206, 0.12);
}
.doc-name {
    font-size: 1.2rem;
    font-weight: 700;
    color: #1a202c;
    margin-bottom: 0.2rem;
}
.spec-badge {
    background-color: #ebf8ff;
    color: #2b6cb0;
    font-size: 0.8rem;
    font-weight: 600;
    padding: 0.2rem 0.6rem;
    border-radius: 6px;
    display: inline-block;
    margin-bottom: 0.8rem;
}
.metric-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.5rem;
    background: #f7fafc;
    padding: 0.75rem;
    border-radius: 8px;
    margin-top: 0.5rem;
}
.metric-item {
    font-size: 0.85rem;
    color: #4a5568;
}
.metric-val {
    font-weight: 700;
    color: #2d3748;
    font-size: 0.95rem;
}
.avail-tag-yes {
    color: #22543d;
    background-color: #c6f6d5;
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    font-weight: 600;
    font-size: 0.8rem;
}
.avail-tag-no {
    color: #744210;
    background-color: #fefcbf;
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    font-weight: 600;
    font-size: 0.8rem;
}
.audit-container {
    background-color: #f8fafc;
    border-left: 4px solid #3182ce;
    padding: 1rem;
    border-radius: 0 8px 8px 0;
    margin-top: 0.5rem;
    font-size: 0.9rem;
}
.emergency-banner {
    background-color: #fff5f5;
    border: 2px solid #feb2b2;
    border-left: 6px solid #e53e3e;
    padding: 1.25rem;
    border-radius: 8px;
    color: #9b2c2c;
    margin: 1rem 0;
}
.safety-banner {
    background-color: #ebf8ff;
    border-left: 6px solid #3182ce;
    padding: 1.25rem;
    border-radius: 8px;
    color: #2b6cb0;
    margin: 1rem 0;
}
</style>
"""


def apply_custom_styles():
    """Injects custom enterprise CSS into the Streamlit app."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_app_header():
    """Renders the top application branding header with the DEMO DATA badge."""
    st.markdown("""
        <div class="main-header-container">
            <span class="header-badge">⚠️ DEMO / MOCK DATA ENVIRONMENT</span>
            <h1 style="margin: 0; font-size: 2rem; color: #ffffff;">🏥 MedData AI — Triage & Doctor Discovery</h1>
            <p style="margin: 0.5rem 0 0 0; color: #cbd5e0; font-size: 1rem;">
                Deterministic, Grounded Healthcare Discovery Agent & SQL Verification Engine
            </p>
        </div>
    """, unsafe_allow_html=True)


def render_doctor_cards(doctors: List[Dict[str, Any]], context_key: str = "main"):
    """
    Renders a grid of polished doctor cards sourced strictly from SQLite rows.
    """
    if not doctors:
        return

    for idx, doc in enumerate(doctors):
        avail_badge = (
            '<span class="avail-tag-yes">🟢 Available Today</span>' 
            if doc.get("is_available_today") == "Yes" 
            else f'<span class="avail-tag-no">📅 Next: {doc.get("next_available_date")}</span>'
        )
        fee_display = f"${doc.get('consultation_fee')}" if doc.get('consultation_fee', 0) > 0 else "FREE ($0)"

        with st.container():
            col_main, col_action = st.columns([4, 1])
            with col_main:
                card_html = f"""
                <div class="doctor-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div class="doc-name">{doc.get('name')}</div>
                        <div>{avail_badge}</div>
                    </div>
                    <span class="spec-badge">{doc.get('specialty')}</span> &bull; <span style="font-size: 0.85rem; color: #718096;">Surgery: <strong>{doc.get('primary_surgery')}</strong></span>
                    
                    <div class="metric-grid">
                        <div class="metric-item">⭐ Satisfaction: <span class="metric-val">{doc.get('satisfaction_score')}/100</span></div>
                        <div class="metric-item">📈 Success Rate: <span class="metric-val">{doc.get('surgery_success_rate')}%</span></div>
                        <div class="metric-item">📍 Distance: <span class="metric-val">{doc.get('distance_miles')} mi</span></div>
                        <div class="metric-item">💰 Fee: <span class="metric-val">{fee_display}</span></div>
                    </div>
                </div>
                """
                st.markdown(card_html, unsafe_allow_html=True)
            
            with col_action:
                st.write("")
                st.write("")
                if st.button("📋 Book Demo", key=f"book_btn_{context_key}_{doc.get('id')}_{idx}"):
                    st.session_state.selected_doctor_for_booking = doc
                    st.rerun()


def render_audit_trail(audit: ExplainabilityAudit):
    """Renders the comprehensive Explainability Audit Trail in an expander."""
    with st.expander("🔍 Explainability Audit Trail & Query Provenance", expanded=False):
        st.markdown(f"**Original User Request:** `{audit.raw_query}`")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Classified Intent", audit.intent)
        c2.metric("Execution Time", f"{audit.execution_time_ms} ms")
        c3.metric("Verified Rows", str(audit.result_count))

        st.markdown("#### ⚙️ Interpretation & Applied Filters")
        if audit.interpreted_entities:
            st.write(f"• **Interpreted Entities:** {audit.interpreted_entities}")
        if audit.negated_entities:
            st.write(f"• **Negated Entities (Excluded):** {audit.negated_entities}")
        
        if audit.applied_filters:
            filter_table = pd.DataFrame([
                {"Filter Parameter": k, "Active Constraint": str(v)} 
                for k, v in audit.applied_filters.items()
            ])
            st.dataframe(filter_table, use_container_width=True, hide_index=True)
        else:
            st.info("No restrictive filters were applied.")

        st.markdown("#### 🔒 Safe Parameterized SQL")
        st.code(audit.sql_query, language="sql")
        st.markdown(f"**Bound Parameters:** `{audit.sql_parameters}`")

        st.markdown("#### 🛡️ Grounding & Factuality Assurance")
        st.success(f"✓ {audit.ai_fabrication_check}")
        st.caption(f"**Deterministic Rationale:** {audit.rationale}")


def render_booking_modal(doctor: Dict[str, Any]):
    """Renders simulated demo booking widget."""
    st.info(f"### 📅 Simulated Booking: {doctor.get('name')} ({doctor.get('specialty')})")
    st.caption("⚠️ **DEMO ENVIRONMENT ONLY** — No real appointment is created.")
    
    with st.form("demo_booking_form"):
        col1, col2 = st.columns(2)
        patient_name = col1.text_input("Patient Name", value="Jane Doe")
        time_slot = col2.selectbox("Preferred Time Slot", ["09:00 AM", "11:00 AM", "02:00 PM", "04:30 PM"])
        notes = st.text_area("Reason for Visit (Demo Notes)", value="Routine consultation")
        
        submitted = st.form_submit_button("Confirm Simulated Booking")
        if submitted:
            from database import book_simulated_appointment
            res = book_simulated_appointment(
                doctor_id=doctor["id"],
                patient_name=patient_name,
                appointment_date=doctor.get("next_available_date", "Today"),
                time_slot=time_slot,
                notes=notes
            )
            if res["success"]:
                st.success(f"✅ Demo booking confirmed! Reference ID: `MED-{res['booking_id']:04d}` for **{doctor['name']}** on **{res['appointment_date']} at {time_slot}**.")
            else:
                st.error(res.get("error", "Booking failed."))
    
    if st.button("Close Booking"):
        st.session_state.selected_doctor_for_booking = None
        st.rerun()
