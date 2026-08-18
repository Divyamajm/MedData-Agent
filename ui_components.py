"""
MedData AI & UrbanLocate - Multi-Domain UI Components & Enterprise Design System
Provides modern healthcare and real estate CSS styling, doctor/housing result cards,
interactive geo-spatial maps, side-by-side comparison matrices, .ics calendar export,
and insurance calculators.
"""

import textwrap
from datetime import datetime
import streamlit as st
import pandas as pd
from typing import Dict, Any, List, Optional
from models import ExplainabilityAudit, QueryResult, DomainType


CUSTOM_CSS = """
<style>
/* Enterprise Glassmorphic Theme */
.main-header-container {
    background: linear-gradient(135deg, #0d233a 0%, #1a365d 100%);
    padding: 1.5rem 2rem;
    border-radius: 14px;
    color: white;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 16px rgba(0,0,0,0.12);
}
.header-badge {
    background: linear-gradient(90deg, #e53e3e, #dd6b20);
    color: white;
    font-size: 0.75rem;
    font-weight: 700;
    padding: 0.25rem 0.65rem;
    border-radius: 20px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    display: inline-block;
    margin-bottom: 0.5rem;
}
.domain-pill {
    background-color: #2b6cb0;
    color: #e2e8f0;
    font-size: 0.8rem;
    padding: 0.25rem 0.6rem;
    border-radius: 6px;
    font-weight: 600;
    display: inline-block;
    margin-left: 0.5rem;
}
.entity-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1.25rem;
    margin-bottom: 1rem;
    box-shadow: 0 2px 6px rgba(0,0,0,0.04);
    transition: all 0.2s ease-in-out;
}
.entity-card:hover {
    border-color: #3182ce;
    box-shadow: 0 6px 16px rgba(49, 130, 206, 0.12);
}
.entity-title {
    font-size: 1.25rem;
    font-weight: 700;
    color: #1a202c;
    margin-bottom: 0.2rem;
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
.badge-livability-high {
    background: #c6f6d5;
    color: #22543d;
    font-weight: 700;
    padding: 0.25rem 0.6rem;
    border-radius: 6px;
    font-size: 0.85rem;
}
.badge-livability-med {
    background: #bee3f8;
    color: #2b6cb0;
    font-weight: 700;
    padding: 0.25rem 0.6rem;
    border-radius: 6px;
    font-size: 0.85rem;
}
.badge-crime-safe {
    background: #c6f6d5;
    color: #22543d;
    font-weight: 600;
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
}
.badge-crime-mod {
    background: #fefcbf;
    color: #744210;
    font-weight: 600;
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
}
.badge-crime-high {
    background: #fed7d7;
    color: #9b2c2c;
    font-weight: 600;
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
}
.audit-container {
    background-color: #f8fafc;
    border: 1px solid #cbd5e0;
    border-left: 4px solid #3182ce;
    border-radius: 8px;
    padding: 1rem;
    margin-top: 1rem;
    font-size: 0.9rem;
}
</style>
"""


def inject_custom_css():
    """Injects custom CSS styles into Streamlit head."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_header(domain: DomainType = DomainType.HEALTHCARE):
    """Renders the top hero banner with live status badges."""
    inject_custom_css()
    if domain == DomainType.HEALTHCARE:
        title = "🏥 MedData AI"
        subtitle = "Enterprise Clinical Triage, Doctor Discovery & Parameterized SQL Engine"
        domain_label = "Active Domain: Clinical Health"
    else:
        title = "🏡 UrbanLocate AI"
        subtitle = "Intelligent Real Estate & Neighborhood Livability Discovery Engine"
        domain_label = "Active Domain: Real Estate & Livability"

    st.markdown(textwrap.dedent(f"""
        <div class="main-header-container">
            <span class="header-badge">Deterministic Grounding</span>
            <span class="domain-pill">{domain_label}</span>
            <h1 style="margin: 0.3rem 0; font-size: 2.1rem; color: #ffffff;">{title}</h1>
            <p style="margin: 0; color: #cbd5e0; font-size: 1.05rem;">{subtitle}</p>
        </div>
    """), unsafe_allow_html=True)


def render_doctor_cards(doctors: List[Dict[str, Any]], show_table_fallback: bool = True):
    """Renders verified doctor cards with surgical metrics and formatting."""
    if not doctors:
        st.info("No matching doctors found.")
        return

    # If large result set (e.g. 200 rows), show top 5 cards and expandable table
    cards_to_show = doctors[:5] if show_table_fallback and len(doctors) > 5 else doctors

    st.markdown(f"**Found {len(doctors)} matching doctor(s) from the verified database:**")

    for doc in cards_to_show:
        is_avail = doc.get("is_available_today") == "Yes"
        avail_badge = '<span style="color: #22543d; background-color: #c6f6d5; padding: 0.2rem 0.5rem; border-radius: 4px; font-weight: 600; font-size: 0.8rem;">🟢 Available Today</span>' if is_avail else f'<span style="color: #744210; background-color: #fefcbf; padding: 0.2rem 0.5rem; border-radius: 4px; font-weight: 600; font-size: 0.8rem;">📅 Next: {doc.get("next_available_date")}</span>'
        fee_str = "FREE ($0)" if doc.get("consultation_fee") == 0 else f"${doc.get('consultation_fee')}"

        card_html = textwrap.dedent(f"""
            <div class="entity-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div class="entity-title">{doc.get('name')}</div>
                    <div>{avail_badge}</div>
                </div>
                <div style="margin: 0.2rem 0 0.5rem 0;">
                    <span style="background-color: #ebf8ff; color: #2b6cb0; font-size: 0.8rem; font-weight: 600; padding: 0.2rem 0.6rem; border-radius: 6px;">{doc.get('specialty')}</span>
                    <span style="color: #718096; font-size: 0.85rem; margin-left: 0.5rem;">• Surgery: <b>{doc.get('primary_surgery')}</b></span>
                </div>
                <div class="metric-grid">
                    <div class="metric-item">⭐ Satisfaction: <span class="metric-val">{doc.get('satisfaction_score')}/100</span></div>
                    <div class="metric-item">📈 Success Rate: <span class="metric-val">{doc.get('surgery_success_rate')}%</span></div>
                    <div class="metric-item">📍 Distance: <span class="metric-val">{doc.get('distance_miles')} mi</span></div>
                    <div class="metric-item">💰 Fee: <span class="metric-val">{fee_str}</span></div>
                </div>
            </div>
        """)
        st.markdown(card_html, unsafe_allow_html=True)

    if show_table_fallback and len(doctors) > 5:
        with st.expander(f"📋 View Complete Directory Table ({len(doctors)} Doctors)"):
            df = pd.DataFrame(doctors)
            st.dataframe(df, use_container_width=True, hide_index=True)


def render_housing_cards(properties: List[Dict[str, Any]]):
    """Renders real estate property cards with livability metrics."""
    if not properties:
        st.info("No matching properties found.")
        return

    st.markdown(f"**Found {len(properties)} matching property record(s) with verified metrics:**")

    for p in properties[:6]:
        livability = p.get("livability_score", 80)
        liv_badge_class = "badge-livability-high" if livability >= 85 else "badge-livability-med"
        
        crime = p.get("crime_index_score", 20)
        if crime <= 20:
            crime_badge = f'<span class="badge-crime-safe">🛡️ Ultra Safe ({crime}/100)</span>'
        elif crime <= 40:
            crime_badge = f'<span class="badge-crime-mod">⚠️ Moderate Crime ({crime}/100)</span>'
        else:
            crime_badge = f'<span class="badge-crime-high">🚨 High Crime ({crime}/100)</span>'

        card_html = textwrap.dedent(f"""
            <div class="entity-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div class="entity-title">{p.get('title')}</div>
                    <div><span class="{liv_badge_class}">🏆 Livability: {livability}/100</span></div>
                </div>
                <div style="margin: 0.2rem 0 0.5rem 0;">
                    <span style="background-color: #edf2f7; color: #2d3748; font-size: 0.8rem; font-weight: 600; padding: 0.2rem 0.6rem; border-radius: 6px;">📍 {p.get('neighborhood')}</span>
                    <span style="color: #4a5568; font-size: 0.85rem; margin-left: 0.5rem;">• {p.get('property_type')} • <b>{p.get('bedrooms')} BHK / {p.get('bathrooms')} Bath</b> ({p.get('sqft')} sqft)</span>
                </div>
                <div class="metric-grid">
                    <div class="metric-item">💰 Rent: <span class="metric-val">${p.get('price_per_month')}/mo</span></div>
                    <div class="metric-item">🏫 Schools: <span class="metric-val">{p.get('school_rating')}/10</span></div>
                    <div class="metric-item">🏥 Hospital: <span class="metric-val">{p.get('hospital_dist_miles')} mi</span></div>
                    <div class="metric-item">🚇 Transit: <span class="metric-val">{p.get('transit_dist_miles')} mi</span></div>
                </div>
                <div style="margin-top: 0.5rem; display: flex; justify-content: space-between; align-items: center;">
                    <div>{crime_badge}</div>
                    <div style="font-size: 0.8rem; color: #718096;">🛒 Shopping / Market: <b>{p.get('market_dist_miles')} mi</b></div>
                </div>
            </div>
        """)
        st.markdown(card_html, unsafe_allow_html=True)

    if len(properties) > 6:
        with st.expander(f"📋 View Complete Property Lake ({len(properties)} Listings)"):
            df = pd.DataFrame(properties)
            st.dataframe(df, use_container_width=True, hide_index=True)


def render_geo_map(data: List[Dict[str, Any]], domain: DomainType = DomainType.HEALTHCARE):
    """Renders interactive latitude/longitude scatter map with pins."""
    if not data:
        st.warning("No data points available to render on the map.")
        return

    # Extract coordinates
    coords = []
    for item in data:
        if "latitude" in item and "longitude" in item:
            coords.append({
                "lat": float(item["latitude"]),
                "lon": float(item["longitude"]),
                "name": item.get("name") or item.get("title"),
                "category": item.get("specialty") or item.get("property_type")
            })

    if coords:
        map_df = pd.DataFrame(coords)
        st.map(map_df, latitude="lat", longitude="lon", size=20, zoom=11, use_container_width=True)
        st.caption(f"Displaying **{len(coords)}** verified geolocation pins across the metropolitan radius.")


def render_comparison_matrix(items: List[Dict[str, Any]], domain: DomainType = DomainType.HEALTHCARE):
    """Renders a side-by-side head-to-head comparison table for selected items."""
    if not items:
        st.info("Select 2 or more items to view the side-by-side comparison matrix.")
        return

    if domain == DomainType.HEALTHCARE:
        comp_data = []
        for d in items:
            comp_data.append({
                "Doctor Name": d.get("name"),
                "Specialty": d.get("specialty"),
                "Surgery Success Rate": f"{d.get('surgery_success_rate')}%",
                "Satisfaction Score": f"{d.get('satisfaction_score')}/100",
                "Consultation Fee": "FREE" if d.get("consultation_fee") == 0 else f"${d.get('consultation_fee')}",
                "Distance (miles)": f"{d.get('distance_miles')} mi",
                "Availability": "Today (Yes)" if d.get("is_available_today") == "Yes" else d.get("next_available_date")
            })
        comp_df = pd.DataFrame(comp_data).set_index("Doctor Name").T
        st.dataframe(comp_df, use_container_width=True)
    else:
        comp_data = []
        for p in items:
            comp_data.append({
                "Property": p.get("title"),
                "Neighborhood": p.get("neighborhood"),
                "Rent": f"${p.get('price_per_month')}/mo",
                "Livability Score": f"{p.get('livability_score')}/100",
                "Crime Index": f"{p.get('crime_index_score')}/100",
                "School Rating": f"{p.get('school_rating')}/10",
                "Hospital Distance": f"{p.get('hospital_dist_miles')} mi",
                "Transit Distance": f"{p.get('transit_dist_miles')} mi",
                "Size": f"{p.get('bedrooms')} BHK ({p.get('sqft')} sqft)"
            })
        comp_df = pd.DataFrame(comp_data).set_index("Property").T
        st.dataframe(comp_df, use_container_width=True)


def generate_ics_calendar(
    doctor_name: str, 
    specialty: str, 
    patient_name: str, 
    appointment_date: str, 
    time_slot: str
) -> str:
    """Generates standard RFC 5545 .ics iCalendar file content for Google/Apple Calendar."""
    # Parse date and time
    dt_str = f"{appointment_date} {time_slot}"
    try:
        dt_obj = datetime.strptime(dt_str, "%Y-%m-%d %I:%M %p")
    except Exception:
        dt_obj = datetime.now()

    start_utc = dt_obj.strftime("%Y%m%dT%H%M00")
    end_utc = dt_obj.strftime("%Y%m%dT%H%M00")
    stamp_utc = datetime.utcnow().strftime("%Y%m%dT%H%M00Z")

    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//MedData AI//Medical Appointment Scheduler//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
BEGIN:VEVENT
UID:{int(datetime.now().timestamp())}@meddata-agent.ai
DTSTAMP:{stamp_utc}
DTSTART:{start_utc}
DTEND:{end_utc}
SUMMARY:Medical Appointment with {doctor_name} ({specialty})
DESCRIPTION:Patient: {patient_name}\\nSpecialty: {specialty}\\nConsultation with {doctor_name}. Demo Medical Simulation.
LOCATION:Metropolitan Medical Center, Clinic Room 402
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR"""
    return ics_content.strip()


def render_insurance_calculator():
    """Renders interactive patient insurance co-pay and deductible estimator."""
    st.markdown("#### 💳 Insurance & Co-Pay Estimation Calculator")
    st.caption("Calculate your estimated patient out-of-pocket consultation expense based on your insurance plan.")

    col1, col2, col3 = st.columns(3)
    plan = col1.selectbox("Insurance Provider", [
        "BlueCross BlueShield (In-Network)",
        "Aetna Health (In-Network)",
        "Cigna Healthcare (In-Network)",
        "Medicare Part B (Standard)",
        "Out-of-Network / Uninsured"
    ])
    doc_fee = col2.number_input("Standard Consultation Fee ($)", min_value=0, max_value=1000, value=150, step=25)
    deductible_met = col3.checkbox("Annual Deductible Met?", value=True)

    # Co-pay logic
    if "Out-of-Network" in plan:
        copay = doc_fee
        covered = 0
        note = "Uninsured or Out-of-Network: 100% patient responsibility."
    elif "Medicare" in plan:
        copay = 0 if doc_fee == 0 else int(doc_fee * 0.20)
        covered = doc_fee - copay
        note = "Medicare Part B covers 80% of approved consultation costs."
    elif deductible_met:
        copay = 0 if doc_fee == 0 else min(30, int(doc_fee * 0.15))
        covered = doc_fee - copay
        note = f"In-Network Specialist Co-Pay applied: Flat ${copay}."
    else:
        copay = int(doc_fee * 0.70)
        covered = doc_fee - copay
        note = "Deductible pending: 70% patient cost-sharing until annual limit is reached."

    res_col1, res_col2 = st.columns(2)
    res_col1.metric("Estimated Patient Co-Pay", f"${copay}")
    res_col2.metric("Covered by Insurance", f"${covered}")
    st.info(f"ℹ️ **Policy Note:** {note}")


def render_audit_trail(audit: ExplainabilityAudit):
    """Renders the Explainability Audit Trail dropdown panel."""
    with st.expander("🔍 Explainability & Query Provenance Audit Trail", expanded=False):
        st.markdown(f"**Domain:** `{audit.domain}` | **Interpreted Intent:** `{audit.intent}` (Confidence: `{audit.confidence * 100:.0f}%`)")
        st.markdown(f"**Execution Latency:** `{audit.execution_time_ms} ms` | **Verified Rows Returned:** `{audit.result_count}`")
        
        st.markdown("**Executed Parameterized SQL:**")
        st.code(audit.sql_query, language="sql")
        
        if audit.sql_parameters:
            st.markdown(f"**Bound Parameters:** `{audit.sql_parameters}`")

        st.markdown(f"**Anti-Hallucination Grounding Status:** 🟢 `{audit.ai_fabrication_check}`")


def render_clarification_buttons(options: List[str]):
    """Renders interactive clarification buttons for ambiguous prompts."""
    st.markdown("##### 💡 Please clarify your primary priority:")
    cols = st.columns(len(options))
    for i, opt in enumerate(options):
        if cols[i].button(opt, key=f"clarify_btn_{i}", use_container_width=True):
            st.session_state["active_prompt"] = f"Find best doctor sorted by {opt}"
            st.rerun()


def render_safety_warning(warning_type: str, message: str):
    """Renders distinct visual alerts for medical emergencies, advice refusal, or guardrails."""
    if warning_type == "acute_emergency":
        st.error(message)
    elif warning_type == "medical_advice":
        st.warning(message)
    elif warning_type == "unknown_attribute":
        st.info(message)
    else:
        st.error(message)
