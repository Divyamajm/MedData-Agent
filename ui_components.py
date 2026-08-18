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
    """Renders verified doctor records with clean spreadsheet dataframe when all data/directory is requested."""
    if not doctors:
        st.info("No matching doctors found.")
        return

    # If full directory / large result set (> 5 records), render direct interactive spreadsheet table
    if len(doctors) > 5:
        st.markdown(f"### 📋 Verified Doctors Database ({len(doctors)} Records)")
        st.caption("Direct grounded tabular spreadsheet view of all matching doctors.")
        df = pd.DataFrame(doctors)
        display_cols = [c for c in ["id", "name", "specialty", "consultation_fee", "primary_surgery", "surgery_success_rate", "satisfaction_score", "distance_miles", "is_available_today", "next_available_date"] if c in df.columns]
        if display_cols:
            df = df[display_cols]
        st.dataframe(df, height=480, hide_index=True)
        return

    st.markdown(f"**Found {len(doctors)} matching doctor(s) from the verified database:**")

    for doc in doctors:
        is_avail = doc.get("is_available_today") == "Yes"
        avail_badge = '<span style="color: #22543d; background-color: #c6f6d5; padding: 0.2rem 0.5rem; border-radius: 4px; font-weight: 600; font-size: 0.8rem;">🟢 Available Today</span>' if is_avail else f'<span style="color: #744210; background-color: #fefcbf; padding: 0.2rem 0.5rem; border-radius: 4px; font-weight: 600; font-size: 0.8rem;">📅 Next: {doc.get("next_available_date")}</span>'
        fee_val = doc.get('consultation_fee', 0)
        fee_str = "FREE (₹0)" if fee_val == 0 else f"₹{fee_val:,}"

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
                    <div class="metric-item">📍 Distance: <span class="metric-val">{doc.get('distance_miles')} km</span></div>
                    <div class="metric-item">💰 Fee: <span class="metric-val">{fee_str}</span></div>
                </div>
            </div>
        """)
        st.markdown(card_html, unsafe_allow_html=True)


def render_housing_cards(properties: List[Dict[str, Any]]):
    """Renders real estate property records with clean spreadsheet dataframe when all data/directory is requested."""
    if not properties:
        st.info("No matching properties found.")
        return

    if len(properties) > 6:
        st.markdown(f"### 📋 Verified Real Estate Database ({len(properties)} Properties)")
        st.caption("Direct grounded tabular spreadsheet view across all 5 Indian Metros.")
        df = pd.DataFrame(properties)
        st.dataframe(df, height=480, hide_index=True)
        return

    st.markdown(f"**Found {len(properties)} matching property record(s) with verified metrics:**")

    for p in properties:
        livability = p.get("livability_score", 80)
        liv_badge_class = "badge-livability-high" if livability >= 85 else "badge-livability-med"
        
        crime = p.get("crime_index_score", 20)
        if crime <= 12:
            crime_badge = f'<span class="badge-crime-safe">🛡️ Ultra Safe & Gated ({crime}/100)</span>'
        elif crime <= 25:
            crime_badge = f'<span class="badge-crime-mod">⚠️ Safe Neighborhood ({crime}/100)</span>'
        else:
            crime_badge = f'<span class="badge-crime-high">🚨 Moderate Crime ({crime}/100)</span>'

        rent_val = p.get('price_per_month', 0)
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
                    <div class="metric-item">💰 Rent: <span class="metric-val">₹{rent_val:,}/mo</span></div>
                    <div class="metric-item">🏫 CBSE/ICSE Schools: <span class="metric-val">{p.get('school_rating')}/10</span></div>
                    <div class="metric-item">🏥 Hospital: <span class="metric-val">{p.get('hospital_dist_miles')} km</span></div>
                    <div class="metric-item">🚇 Metro Transit: <span class="metric-val">{p.get('transit_dist_miles')} km</span></div>
                </div>
                <div style="margin-top: 0.5rem; display: flex; justify-content: space-between; align-items: center;">
                    <div>{crime_badge}</div>
                    <div style="font-size: 0.8rem; color: #718096;">🛒 Shopping / High Street: <b>{p.get('market_dist_miles')} km</b></div>
                </div>
            </div>
        """)
        st.markdown(card_html, unsafe_allow_html=True)

    if len(properties) > 6:
        with st.expander(f"📋 View Complete Property Lake ({len(properties)} Listings)"):
            df = pd.DataFrame(properties)
            st.dataframe(df, hide_index=True)


def render_geo_map(data: List[Dict[str, Any]], domain: DomainType = DomainType.HEALTHCARE):
    """Renders interactive latitude/longitude scatter map with city-level zoom and precision pins."""
    if not data:
        st.warning("No data points available to render on the map.")
        return

    # Metro City Center Bounding & Lat/Long Limits
    CITY_CENTERS = {
        "🇮🇳 All India (National Overview)": {"lat_min": 8.0, "lat_max": 35.0, "lon_min": 68.0, "lon_max": 97.0, "zoom": 4},
        "🏙️ Bengaluru (Silicon Valley)": {"lat_min": 12.75, "lat_max": 13.15, "lon_min": 77.45, "lon_max": 77.85, "zoom": 11},
        "🌊 Mumbai (Financial Capital)": {"lat_min": 18.85, "lat_max": 19.30, "lon_min": 72.75, "lon_max": 73.05, "zoom": 11},
        "🏛️ Delhi-NCR (Capital Region)": {"lat_min": 28.35, "lat_max": 28.75, "lon_min": 76.95, "lon_max": 77.45, "zoom": 11},
        "👑 Hyderabad (Cyberabad)": {"lat_min": 17.30, "lat_max": 17.55, "lon_min": 78.25, "lon_max": 78.55, "zoom": 11},
        "🌴 Chennai (Coastal Tech Hub)": {"lat_min": 12.85, "lat_max": 13.18, "lon_min": 80.10, "lon_max": 80.32, "zoom": 11}
    }

    col_map1, col_map2 = st.columns([1, 3])
    selected_city_focus = col_map1.selectbox(
        "🗺️ Focus Metro Radar:",
        list(CITY_CENTERS.keys()),
        index=0
    )

    # Extract coordinates and sanitize
    coords = []
    for item in data:
        if "latitude" in item and "longitude" in item and item["latitude"] is not None and item["longitude"] is not None:
            lat = float(item["latitude"])
            lon = float(item["longitude"])
            city_filter = CITY_CENTERS[selected_city_focus]

            if city_filter["lat_min"] <= lat <= city_filter["lat_max"] and city_filter["lon_min"] <= lon <= city_filter["lon_max"]:
                coords.append({
                    "lat": lat,
                    "lon": lon,
                    "Name": item.get("name") or item.get("title") or item.get("College_Name"),
                    "Location / Details": item.get("neighborhood") or item.get("specialty") or item.get("City"),
                    "Price / Metric": f"₹{item.get('price_per_month', item.get('consultation_fee', item.get('Annual_Fees_INR', 'N/A'))):,}" if isinstance(item.get('price_per_month', item.get('consultation_fee', item.get('Annual_Fees_INR'))), (int, float)) else "N/A"
                })

    if coords:
        map_df = pd.DataFrame(coords)
        col_map2.map(map_df[["lat", "lon"]], zoom=CITY_CENTERS[selected_city_focus]["zoom"])
        st.caption(f"Displaying **{len(coords)}** verified Indian geolocation points in `{selected_city_focus}`.")

        with st.expander(f"📍 View Geolocation Point Directory ({len(coords)} Locations)", expanded=False):
            st.dataframe(map_df[["Name", "Location / Details", "Price / Metric", "lat", "lon"]], hide_index=True)
    else:
        st.info(f"No records found within the bounding coordinates of **{selected_city_focus}**. Try selecting *All India* to view all mapped points.")


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
        st.dataframe(comp_df)
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
        st.dataframe(comp_df)


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
    """Renders interactive Indian health insurance co-pay and deductible estimator."""
    st.markdown("#### 💳 Indian Health Insurance & OPD Co-Pay Estimator")
    st.caption("Calculate estimated patient out-of-pocket consultation expenses across major Indian health insurance providers.")

    col1, col2, col3 = st.columns(3)
    plan = col1.selectbox("Health Insurance Provider", [
        "Star Health Comprehensive (OPD Rider)",
        "HDFC ERGO Optima Secure (In-Network)",
        "Care Health Supreme Plan (In-Network)",
        "ICICI Lombard Complete Health (In-Network)",
        "Niva Bupa ReAssure 2.0 (Cashless)",
        "Ayushman Bharat PM-JAY (Govt Empanelled)",
        "Self-Pay / Out-of-Pocket"
    ])
    doc_fee = col2.number_input("Doctor Consultation Fee (₹)", min_value=0, max_value=5000, value=800, step=100)
    policy_active = col3.checkbox("Cashless Network Hospital?", value=True)

    if "Self-Pay" in plan:
        copay = doc_fee
        covered = 0
        note = "Self-Pay: 100% patient direct payment."
    elif "Ayushman Bharat" in plan:
        copay = 0
        covered = doc_fee
        note = "Ayushman Bharat PM-JAY covers 100% of approved treatment and OPD at empanelled centers."
    elif policy_active:
        copay = 0 if doc_fee == 0 else min(150, int(doc_fee * 0.10))
        covered = doc_fee - copay
        note = f"Cashless In-Network OPD coverage applied. Nominal co-pay: ₹{copay}."
    else:
        copay = int(doc_fee * 0.30)
        covered = doc_fee - copay
        note = "Reimbursement Claim: 30% co-payment applied for non-network center."

    res_col1, res_col2 = st.columns(2)
    res_col1.metric("Estimated Patient Co-Pay", f"₹{copay:,}")
    res_col2.metric("Covered by Insurance", f"₹{covered:,}")
    st.info(f"ℹ️ **Policy Summary:** {note}")


def render_dynamic_dataset_view(df: pd.DataFrame, profile: Any, search_result: Optional[Dict[str, Any]] = None):
    """Renders automated schema profiling, metric cards, and query results for any custom uploaded dataset."""
    st.markdown(f"### 📂 Auto-Analyzed Dataset: **{profile.table_name}**")
    st.markdown(f"**Inferred Domain:** `{profile.inferred_domain}` | **Total Rows:** `{profile.row_count}` | **Total Fields:** `{profile.column_count}`")
    st.caption(profile.summary_description)

    # Metric Row
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Records", f"{profile.row_count}")
    c2.metric("Columns Profiled", f"{profile.column_count}")
    if profile.primary_price_col and profile.primary_price_col in df.columns:
        avg_price = df[profile.primary_price_col].mean()
        c3.metric(f"Avg {profile.primary_price_col}", f"₹{avg_price:,.0f}" if avg_price > 100 else f"{avg_price:.1f}")
    if profile.primary_rating_col and profile.primary_rating_col in df.columns:
        avg_rating = df[profile.primary_rating_col].mean()
        c4.metric(f"Avg {profile.primary_rating_col}", f"{avg_rating:.2f}")

    # Display Query Results or Ambiguity Clarification
    if search_result:
        if search_result.get("ambiguity_detected"):
            st.warning(f"⚠️ **Ambiguity Intercepted (Zero-Hallucination Policy):** {search_result.get('ambiguity_reason')}")
            st.markdown("##### 💡 What is your primary priority? (Click to rank deterministically):")
            options = search_result.get("clarification_options", [])
            cols = st.columns(len(options))
            for i, opt in enumerate(options):
                if cols[i].button(opt, key=f"dyn_clarify_btn_{i}_{abs(hash(opt)) % 100000}"):
                    st.session_state["dynamic_search_override"] = opt
                    st.rerun()
        elif search_result.get("data") is not None:
            res_df = search_result["data"]
            st.markdown(f"#### 🎯 Query Results: **{len(res_df)} matches found**")
            st.caption(f"Applied Rules: {', '.join(search_result.get('applied_rules', []))}")
            st.dataframe(res_df, hide_index=True)
    else:
        st.markdown("#### 📋 Raw Dataset Preview (Top 10 Records)")
        st.dataframe(df.head(10), hide_index=True)

    # Schema & Semantic Roles Breakdown
    with st.expander("🔍 Inferred Schema & Semantic Column Profiles", expanded=False):
        schema_rows = []
        for col_name, p in profile.columns.items():
            schema_rows.append({
                "Column Name": col_name,
                "Inferred Role": p.semantic_role.value.replace("_", " ").title(),
                "Data Type": p.dtype,
                "Unique Values": p.unique_count,
                "Sample Values": str(p.sample_values[:3])
            })
        st.dataframe(pd.DataFrame(schema_rows), hide_index=True)

    # If coordinates exist, render map
    if profile.has_geo_coordinates and profile.lat_column and profile.lng_column:
        st.markdown("#### 🗺️ Spatial Geo-Distribution")
        geo_df = df[[profile.lat_column, profile.lng_column]].dropna()
        geo_df.columns = ["lat", "lon"]
        st.map(geo_df, zoom=10)


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
    st.markdown("##### 💡 Please clarify your primary priority (Zero-Hallucination Disambiguation):")
    cols = st.columns(len(options))
    for i, opt in enumerate(options):
        if cols[i].button(opt, key=f"clarify_btn_{i}"):
            st.session_state.pending_clarification = False
            st.session_state.clarification_data = None
            st.session_state["sample_to_run"] = f"Sort by {opt}"
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
