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
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* Universal Font & Base Polish */
html, body, [class*="css"], .stMarkdown, .stText {
    font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    letter-spacing: -0.01em;
}

/* Executive Glassmorphic Hero Header */
.main-header-container {
    background: linear-gradient(135deg, #091e3a 0%, #102a4e 45%, #173865 100%);
    padding: 1.75rem 2.25rem;
    border-radius: 16px;
    color: #ffffff;
    margin-bottom: 1.5rem;
    border: 1px solid rgba(255, 255, 255, 0.12);
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.1);
    position: relative;
    overflow: hidden;
}
.main-header-container::after {
    content: "";
    position: absolute;
    top: -50%;
    right: -20%;
    width: 300px;
    height: 300px;
    background: radial-gradient(circle, rgba(59, 130, 246, 0.25) 0%, rgba(0,0,0,0) 70%);
    pointer-events: none;
}
.header-badge {
    background: linear-gradient(90deg, #ef4444, #f97316);
    color: white;
    font-size: 0.72rem;
    font-weight: 800;
    padding: 0.3rem 0.75rem;
    border-radius: 20px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    box-shadow: 0 2px 8px rgba(239, 68, 68, 0.3);
}
.domain-pill {
    background: rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(255, 255, 255, 0.18);
    color: #e0e7ff;
    font-size: 0.78rem;
    padding: 0.3rem 0.75rem;
    border-radius: 20px;
    font-weight: 600;
    display: inline-block;
    margin-left: 0.5rem;
}
.status-pill {
    background: rgba(16, 185, 129, 0.15);
    border: 1px solid rgba(16, 185, 129, 0.35);
    color: #6ee7b7;
    font-size: 0.75rem;
    padding: 0.3rem 0.75rem;
    border-radius: 20px;
    font-weight: 600;
    display: inline-block;
    margin-left: 0.5rem;
}

/* Modern Segmented Pill Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background: rgba(15, 23, 42, 0.6);
    padding: 6px 8px;
    border-radius: 14px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    margin-bottom: 1.25rem;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 10px;
    padding: 8px 18px;
    font-weight: 600;
    font-size: 0.92rem;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    color: #94a3b8;
    border: none;
}
.stTabs [data-baseweb="tab"]:hover {
    background: rgba(255, 255, 255, 0.08);
    color: #f8fafc;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
    color: #ffffff !important;
    box-shadow: 0 4px 14px rgba(37, 99, 235, 0.38);
}

/* Glassmorphic Entity Cards */
.entity-card {
    background: linear-gradient(145deg, rgba(30, 41, 59, 0.85), rgba(15, 23, 42, 0.95));
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 14px;
    padding: 1.35rem 1.5rem;
    margin-bottom: 1.15rem;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
    transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
    backdrop-filter: blur(12px);
}
.entity-card:hover {
    border-color: rgba(96, 165, 250, 0.5);
    transform: translateY(-2px);
    box-shadow: 0 8px 28px rgba(37, 99, 235, 0.2);
}
.entity-title {
    font-size: 1.25rem;
    font-weight: 700;
    color: #f8fafc;
    margin-bottom: 0.25rem;
    letter-spacing: -0.02em;
}
.metric-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.65rem;
    background: rgba(255, 255, 255, 0.035);
    border: 1px solid rgba(255, 255, 255, 0.06);
    padding: 0.85rem 1rem;
    border-radius: 10px;
    margin-top: 0.65rem;
}
.metric-item {
    font-size: 0.82rem;
    color: #94a3b8;
}
.metric-val {
    font-weight: 700;
    color: #f1f5f9;
    font-size: 0.95rem;
}

/* Badges */
.badge-avail-today {
    background: rgba(16, 185, 129, 0.18);
    border: 1px solid rgba(16, 185, 129, 0.4);
    color: #34d399;
    padding: 0.25rem 0.65rem;
    border-radius: 6px;
    font-weight: 700;
    font-size: 0.8rem;
}
.badge-avail-next {
    background: rgba(245, 158, 11, 0.18);
    border: 1px solid rgba(245, 158, 11, 0.4);
    color: #fbbf24;
    padding: 0.25rem 0.65rem;
    border-radius: 6px;
    font-weight: 700;
    font-size: 0.8rem;
}
.badge-specialty {
    background: rgba(59, 130, 246, 0.18);
    border: 1px solid rgba(59, 130, 246, 0.35);
    color: #93c5fd;
    font-size: 0.8rem;
    font-weight: 600;
    padding: 0.2rem 0.65rem;
    border-radius: 6px;
}
.badge-livability-high {
    background: rgba(16, 185, 129, 0.2);
    border: 1px solid rgba(16, 185, 129, 0.4);
    color: #34d399;
    font-weight: 700;
    padding: 0.25rem 0.65rem;
    border-radius: 6px;
    font-size: 0.82rem;
}
.badge-livability-med {
    background: rgba(59, 130, 246, 0.2);
    border: 1px solid rgba(59, 130, 246, 0.4);
    color: #93c5fd;
    font-weight: 700;
    padding: 0.25rem 0.65rem;
    border-radius: 6px;
    font-size: 0.82rem;
}
.badge-crime-safe {
    background: rgba(16, 185, 129, 0.18);
    border: 1px solid rgba(16, 185, 129, 0.35);
    color: #34d399;
    font-weight: 600;
    padding: 0.2rem 0.55rem;
    border-radius: 6px;
    font-size: 0.8rem;
}
.badge-crime-mod {
    background: rgba(245, 158, 11, 0.18);
    border: 1px solid rgba(245, 158, 11, 0.35);
    color: #fbbf24;
    font-weight: 600;
    padding: 0.2rem 0.55rem;
    border-radius: 6px;
    font-size: 0.8rem;
}
.badge-crime-high {
    background: rgba(239, 68, 68, 0.18);
    border: 1px solid rgba(239, 68, 68, 0.35);
    color: #f87171;
    font-weight: 600;
    padding: 0.2rem 0.55rem;
    border-radius: 6px;
    font-size: 0.8rem;
}

/* Audit Panel */
.audit-container {
    background-color: rgba(15, 23, 42, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-left: 4px solid #3b82f6;
    border-radius: 10px;
    padding: 1rem 1.25rem;
    margin-top: 1rem;
    font-size: 0.9rem;
    color: #cbd5e1;
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
        title = "🏥 MedData AI & Clinical Triage"
        subtitle = "Zero-Hallucination Medical Directory, Physician Discovery & Parameterized Query Engine"
        domain_label = "Clinical Health (India)"
    else:
        title = "🏡 UrbanLocate AI & Livability Radar"
        subtitle = "Intelligent Real Estate, School Scoring & Neighborhood Livability Discovery"
        domain_label = "Real Estate & Livability (5 Metros)"

    st.markdown(textwrap.dedent(f"""
        <div class="main-header-container">
            <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 0.6rem; flex-wrap: wrap;">
                <span class="header-badge">🛡️ Zero-Hallucination Architecture</span>
                <span class="status-pill">🟢 100% Database Grounded</span>
                <span class="domain-pill">📍 {domain_label}</span>
            </div>
            <h1 style="margin: 0.2rem 0; font-size: 2.15rem; font-weight: 800; color: #ffffff; letter-spacing: -0.03em;">{title}</h1>
            <p style="margin: 0; color: #cbd5e1; font-size: 1rem; font-weight: 500;">{subtitle}</p>
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
        avail_badge = '<span class="badge-avail-today">🟢 Available Today</span>' if is_avail else f'<span class="badge-avail-next">📅 Next: {doc.get("next_available_date")}</span>'
        fee_val = doc.get('consultation_fee', 0)
        fee_str = "FREE (₹0)" if fee_val == 0 else f"₹{fee_val:,}"

        card_html = textwrap.dedent(f"""
            <div class="entity-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div class="entity-title">{doc.get('name')}</div>
                    <div>{avail_badge}</div>
                </div>
                <div style="margin: 0.35rem 0 0.65rem 0; display: flex; align-items: center; gap: 8px;">
                    <span class="badge-specialty">{doc.get('specialty')}</span>
                    <span style="color: #94a3b8; font-size: 0.85rem;">• Surgery: <b style="color: #e2e8f0;">{doc.get('primary_surgery')}</b></span>
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
            crime_badge = f'<span class="badge-crime-safe">🛡️ Ultra Safe ({crime}/100)</span>'
        elif crime <= 25:
            crime_badge = f'<span class="badge-crime-mod">⚠️ Safe ({crime}/100)</span>'
        else:
            crime_badge = f'<span class="badge-crime-high">🚨 Moderate ({crime}/100)</span>'

        rent_val = p.get('price_per_month', 0)
        card_html = textwrap.dedent(f"""
            <div class="entity-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div class="entity-title">{p.get('title')}</div>
                    <div><span class="{liv_badge_class}">🏆 Livability: {livability}/100</span></div>
                </div>
                <div style="margin: 0.35rem 0 0.65rem 0; display: flex; align-items: center; gap: 8px;">
                    <span class="badge-specialty">📍 {p.get('neighborhood')}, {p.get('city', 'Bengaluru')}</span>
                    <span style="color: #94a3b8; font-size: 0.85rem;">• {p.get('property_type')} • <b style="color: #e2e8f0;">{p.get('bedrooms')} BHK / {p.get('bathrooms')} Bath</b> ({p.get('sqft')} sqft)</span>
                </div>
                <div class="metric-grid">
                    <div class="metric-item">💰 Rent: <span class="metric-val">₹{rent_val:,}/mo</span></div>
                    <div class="metric-item">🏫 CBSE/ICSE Schools: <span class="metric-val">{p.get('school_rating')}/10</span></div>
                    <div class="metric-item">🏥 Hospital: <span class="metric-val">{p.get('hospital_dist_miles')} km</span></div>
                    <div class="metric-item">🚇 Metro Transit: <span class="metric-val">{p.get('transit_dist_miles')} km</span></div>
                </div>
                <div style="margin-top: 0.65rem; display: flex; justify-content: space-between; align-items: center;">
                    <div>{crime_badge}</div>
                    <div style="font-size: 0.8rem; color: #94a3b8;">🛒 High Street: <b style="color: #f1f5f9;">{p.get('market_dist_miles')} km</b></div>
                </div>
            </div>
        """)
        st.markdown(card_html, unsafe_allow_html=True)

    if len(properties) > 6:
        with st.expander(f"📋 View Complete Property Lake ({len(properties)} Listings)"):
            df = pd.DataFrame(properties)
            st.dataframe(df, hide_index=True)


def render_comparison_matrix(items: List[Dict[str, Any]], domain: DomainType = DomainType.HEALTHCARE, custom_title_col: Optional[str] = None, *args, **kwargs):
    """Renders a side-by-side head-to-head comparison table for selected items across Healthcare, Real Estate, or Any Imported CSV."""
    if not items:
        st.info("Select 2 or more items to view the side-by-side comparison matrix.")
        return

    if domain == DomainType.HEALTHCARE:
        comp_data = []
        for d in items:
            fee_val = d.get('consultation_fee', 0)
            fee_str = "FREE (₹0)" if fee_val == 0 else f"₹{fee_val:,}"
            comp_data.append({
                "Doctor Name": d.get("name"),
                "Specialty": d.get("specialty"),
                "Surgery Success Rate": f"{d.get('surgery_success_rate')}%",
                "Satisfaction Score": f"{d.get('satisfaction_score')}/100",
                "Consultation Fee": fee_str,
                "Distance (km)": f"{d.get('distance_miles')} km",
                "Availability": "🟢 Today (Yes)" if d.get("is_available_today") == "Yes" else f"📅 Next: {d.get('next_available_date')}"
            })
        comp_df = pd.DataFrame(comp_data).set_index("Doctor Name").T
        st.dataframe(comp_df, height=350)
    elif domain == DomainType.REAL_ESTATE:
        comp_data = []
        for p in items:
            rent_val = p.get('price_per_month', 0)
            comp_data.append({
                "Property": p.get("title"),
                "City": p.get("city", "Bengaluru"),
                "Neighborhood": p.get("neighborhood"),
                "Monthly Rent": f"₹{rent_val:,}/mo",
                "Livability Score": f"{p.get('livability_score')}/100",
                "Crime Index": f"{p.get('crime_index_score')}/100 (Lower is Safer)",
                "CBSE/ICSE Schools": f"{p.get('school_rating')}/10",
                "Hospital Distance": f"{p.get('hospital_dist_miles')} km",
                "Metro Transit": f"{p.get('transit_dist_miles')} km",
                "Configuration": f"{p.get('bedrooms')} BHK / {p.get('bathrooms')} Bath ({p.get('sqft')} sqft)"
            })
        comp_df = pd.DataFrame(comp_data).set_index("Property").T
        st.dataframe(comp_df, height=400)
    else:
        # Dynamic Dataset / Imported CSV File Comparison
        comp_data = []
        first_item = items[0]
        id_col = custom_title_col
        if not id_col:
            for candidate in ["Hospital_Name", "College_Name", "Name", "Title", "name", "title", "id", list(first_item.keys())[0]]:
                if candidate in first_item:
                    id_col = candidate
                    break

        for item in items:
            row_dict = {}
            for k, v in item.items():
                if k.lower() in ["latitude", "longitude", "id"]:
                    continue
                # Format numbers nicely
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    if "fee" in k.lower() or "price" in k.lower() or "rent" in k.lower() or "salary" in k.lower():
                        row_dict[k.replace("_", " ").title()] = f"₹{int(v):,}" if v >= 100 else f"₹{v:.2f}"
                    elif "rating" in k.lower() or "score" in k.lower():
                        row_dict[k.replace("_", " ").title()] = f"⭐ {v}"
                    elif "rate" in k.lower() or "pct" in k.lower() or "percent" in k.lower():
                        row_dict[k.replace("_", " ").title()] = f"{v}%"
                    else:
                        row_dict[k.replace("_", " ").title()] = f"{int(v):,}" if isinstance(v, int) else f"{v}"
                else:
                    row_dict[k.replace("_", " ").title()] = str(v)
            comp_data.append(row_dict)

        title_display = id_col.replace("_", " ").title() if id_col else list(comp_data[0].keys())[0]
        comp_df = pd.DataFrame(comp_data)
        if title_display in comp_df.columns:
            comp_df = comp_df.set_index(title_display).T
        st.dataframe(comp_df, height=450)


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
            res_df = search_result["data"].copy()
            st.markdown(f"#### 🎯 Query Results: **{len(res_df)} matches found**")
            st.caption(f"Applied Rules: {', '.join(search_result.get('applied_rules', []))}")
            
            # Interactive Sort & Reorganization Controls
            with st.container():
                st.markdown("###### 🔄 Reorganize & Sort Results Table")
                rc1, rc2 = st.columns([2, 2])
                dyn_sort_col = rc1.selectbox("Choose Column to Reorganize:", ["(Original Search Order)"] + list(res_df.columns), key=f"res_sort_col_{abs(hash(profile.table_name)) % 100000}")
                dyn_sort_dir = rc2.radio("Sort Direction:", ["⬆️ Ascending (Low to High / A-Z)", "⬇️ Descending (High to Low / Z-A)"], horizontal=True, key=f"res_sort_dir_{abs(hash(profile.table_name)) % 100000}")
                
                if dyn_sort_col != "(Original Search Order)" and dyn_sort_col in res_df.columns:
                    is_asc = "Ascending" in dyn_sort_dir
                    res_df = res_df.sort_values(by=dyn_sort_col, ascending=is_asc)
            
            st.dataframe(res_df, height=450, hide_index=True)
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
