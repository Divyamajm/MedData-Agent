"""
MedData AI - Universal Dynamic Auto-Schema Profiler & Query Engine
Inspects arbitrary databases, tables, or uploaded CSVs, infers semantic roles,
and executes natural language queries and statistical breakdowns on the fly.
"""

import re
import math
import random
import sqlite3
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class SemanticColumnRole(str, Enum):
    TITLE_NAME = "title_name"
    PRICE_COST = "price_cost"
    RATING_SCORE = "rating_score"
    SAFETY_RISK = "safety_risk"
    DISTANCE_KM = "distance_km"
    CATEGORY_TYPE = "category_type"
    GEO_LAT = "geo_latitude"
    GEO_LNG = "geo_longitude"
    GENERIC_NUMERIC = "generic_numeric"
    GENERIC_TEXT = "generic_text"


@dataclass
class ColumnProfile:
    name: str
    dtype: str
    semantic_role: SemanticColumnRole
    sample_values: List[Any] = field(default_factory=list)
    unique_count: int = 0
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    mean_val: Optional[float] = None
    description: str = ""


@dataclass
class TableProfile:
    table_name: str
    row_count: int
    column_count: int
    columns: Dict[str, ColumnProfile] = field(default_factory=dict)
    inferred_domain: str = "General Dataset"
    summary_description: str = ""
    suggested_queries: List[str] = field(default_factory=list)
    has_geo_coordinates: bool = False
    lat_column: Optional[str] = None
    lng_column: Optional[str] = None
    primary_price_col: Optional[str] = None
    primary_rating_col: Optional[str] = None
    primary_category_col: Optional[str] = None
    primary_title_col: Optional[str] = None


def profile_dataframe(df: pd.DataFrame, table_name: str = "Uploaded_Data") -> TableProfile:
    """
    Performs deep automated schema analysis, statistical profiling, and semantic role inference
    on any given pandas DataFrame.
    """
    profile = TableProfile(
        table_name=table_name,
        row_count=len(df),
        column_count=len(df.columns)
    )

    detected_roles = {}
    
    for col in df.columns:
        col_lower = str(col).lower().strip()
        series = df[col].dropna()
        sample_vals = series.head(5).tolist()
        unique_cnt = series.nunique()
        
        is_numeric = pd.api.types.is_numeric_dtype(df[col])
        min_v = float(series.min()) if is_numeric and len(series) > 0 else None
        max_v = float(series.max()) if is_numeric and len(series) > 0 else None
        mean_v = float(series.mean()) if is_numeric and len(series) > 0 else None

        # Infer Semantic Role based on column name heuristics and data distribution
        role = SemanticColumnRole.GENERIC_TEXT
        
        # 1. Coordinates
        if any(k in col_lower for k in ["latitude", "lat", "geo_lat", "y_coord"]):
            role = SemanticColumnRole.GEO_LAT
            profile.lat_column = col
        elif any(k in col_lower for k in ["longitude", "lon", "lng", "geo_lng", "x_coord"]):
            role = SemanticColumnRole.GEO_LNG
            profile.lng_column = col

        # 2. Price / Fee / Cost (₹ INR or general currency)
        elif any(k in col_lower for k in ["price", "rent", "fee", "cost", "salary", "budget", "amount", "charge", "inr", "rs", "₹", "rupees"]):
            role = SemanticColumnRole.PRICE_COST
            if not profile.primary_price_col:
                profile.primary_price_col = col

        # 3. Rating / Score / Satisfaction / Success
        elif any(k in col_lower for k in ["rating", "score", "satisfaction", "success", "stars", "rank", "performance", "grade", "review"]):
            role = SemanticColumnRole.RATING_SCORE
            if not profile.primary_rating_col:
                profile.primary_rating_col = col

        # 4. Safety / Crime / Risk
        elif any(k in col_lower for k in ["crime", "safety", "risk", "hazard", "violation"]):
            role = SemanticColumnRole.SAFETY_RISK

        # 5. Distance / Km / Proximity
        elif any(k in col_lower for k in ["dist", "distance", "km", "miles", "radius", "proximity", "transit", "metro", "hospital"]):
            role = SemanticColumnRole.DISTANCE_KM

        # 6. Title / Name / Identifier
        elif any(k in col_lower for k in ["name", "title", "doctor", "property", "item", "product", "model", "school", "college", "company"]) and not is_numeric:
            role = SemanticColumnRole.TITLE_NAME
            if not profile.primary_title_col:
                profile.primary_title_col = col

        # 7. Category / Type / Locality
        elif (any(k in col_lower for k in ["type", "category", "specialty", "neighborhood", "locality", "city", "department", "brand", "genre", "bhk", "state", "status"])
              or (not is_numeric and unique_cnt < len(df) * 0.4)):
            role = SemanticColumnRole.CATEGORY_TYPE
            if not profile.primary_category_col:
                profile.primary_category_col = col

        # Fallback numeric
        elif is_numeric:
            role = SemanticColumnRole.GENERIC_NUMERIC

        col_profile = ColumnProfile(
            name=str(col),
            dtype=str(df[col].dtype),
            semantic_role=role,
            sample_values=sample_vals,
            unique_count=unique_cnt,
            min_val=min_v,
            max_val=max_v,
            mean_val=mean_v,
            description=f"Auto-inferred {role.value.replace('_', ' ').title()}"
        )
        profile.columns[str(col)] = col_profile
        detected_roles[str(col)] = role

    # Check for Geo Support
    if profile.lat_column and profile.lng_column:
        profile.has_geo_coordinates = True

    # Inferred Domain Classification
    cols_all = " ".join([c.lower() for c in df.columns])
    if any(k in cols_all for k in ["bhk", "rent", "property", "neighborhood", "locality", "sqft", "bedroom", "livability"]):
        profile.inferred_domain = "🏡 Real Estate & Housing (India)"
        profile.summary_description = "Residential real estate and neighborhood livability dataset."
        profile.suggested_queries = [
            "Show properties with rent under ₹35,000",
            "Find highest rated safety score in top localities",
            "List 3BHK options with lowest rent",
            "Show properties near metro station"
        ]
    elif any(k in cols_all for k in ["doctor", "specialty", "surgery", "patient", "consultation", "hospital", "clinic"]):
        profile.inferred_domain = "🏥 Healthcare & Clinical Directory (India)"
        profile.summary_description = "Physicians, surgical outcomes, and healthcare facilities dataset."
        profile.suggested_queries = [
            "Find doctors with consultation fee under ₹1,000",
            "Show highest rated specialists available today",
            "Doctors with top surgical success rate",
            "Nearest multi-specialty clinic"
        ]
    elif any(k in cols_all for k in ["car", "vehicle", "mileage", "fuel", "transmission", "engine", "brand", "model"]):
        profile.inferred_domain = "🚗 Automotive / Vehicles"
        profile.summary_description = "Automobile specifications, pricing, and performance dataset."
        profile.suggested_queries = [
            "Vehicles with price under ₹8 Lakhs",
            "Highest mileage petrol cars",
            "Automatic transmission models"
        ]
    elif any(k in cols_all for k in ["college", "university", "nirf", "placement", "course", "fees", "cutoff", "faculty"]):
        profile.inferred_domain = "🎓 Higher Education / Colleges"
        profile.summary_description = "Institutions, NIRF rankings, and placement statistics dataset."
        profile.suggested_queries = [
            "Colleges with NIRF rank under 20",
            "Top placement average salary",
            "Institutes with lowest tuition fees"
        ]
    else:
        profile.inferred_domain = "📊 Custom Analytical Dataset"
        profile.summary_description = f"General relational dataset containing {profile.row_count} records across {profile.column_count} fields."
        profile.suggested_queries = [
            "Show top 10 records sorted by highest value",
            "Filter records below average cost",
            "Group records by primary category"
        ]

    return profile


def execute_dynamic_nl_query(df: pd.DataFrame, profile: TableProfile, prompt: str) -> Dict[str, Any]:
    """
    Executes a zero-shot natural language filter/query over any arbitrary dataset
    using the auto-inferred semantic schema profile. Enforces zero-hallucination
    ambiguity interception when subjective queries ('best', 'top', 'recommend') lack criteria.
    """
    prompt_lower = prompt.lower().strip()
    applied_rules = []
    
    # 0. Ambiguity Interception (Subjective 'best' / 'top' / 'recommend' queries)
    is_subjective_query = bool(re.search(r"\b(best|top|good|recommended|give me the best|show best|which is best|ideal)\b", prompt_lower))
    has_specific_filter = bool(
        re.search(r"(?:under|below|less than|<=|<|>|>=|above|\$|₹|rs\.?|\d+|diesel|petrol|cng|lakh|bhk)", prompt_lower) or
        any(k in prompt_lower for k in ["fee", "fees", "placement", "salary", "lpa", "rank", "ranking", "cheapest", "lowest", "mileage", "safest", "package", "school", "rate", "year"])
    )

    if is_subjective_query and not has_specific_filter:
        clarification_options = []
        if "Colleges" in profile.table_name or "Education" in profile.inferred_domain or "NIRF" in profile.table_name:
            clarification_options = [
                "🏆 Highest NIRF National Ranking",
                "💰 Highest Average Placement Package (LPA)",
                "📉 Lowest Annual Tuition Fees (Affordable)",
                "🎯 Highest Placement Rate (%)"
            ]
        elif "Cars" in profile.table_name or "Automotive" in profile.inferred_domain:
            clarification_options = [
                "💰 Lowest Price (Most Affordable)",
                "⛽ Highest Fuel Efficiency (Mileage kmpl)",
                "🚗 Lowest Kilometers Driven",
                "🆕 Latest Model Year"
            ]
        elif "Salary" in profile.table_name or "Tech" in profile.table_name or "Job" in profile.table_name:
            clarification_options = [
                "💰 Highest Annual Compensation (LPA)",
                "💼 Lowest Experience Required",
                "🏢 Remote / Hybrid Friendly"
            ]
        else:
            if profile.primary_rating_col:
                clarification_options.append(f"⭐ Highest {profile.primary_rating_col}")
            if profile.primary_price_col:
                clarification_options.append(f"📉 Lowest {profile.primary_price_col}")
            for col_name, col_p in profile.columns.items():
                if col_p.semantic_role == SemanticColumnRole.GENERIC_NUMERIC and col_name not in [profile.primary_price_col, profile.primary_rating_col]:
                    clarification_options.append(f"📈 Highest {col_name}")

        return {
            "success": True,
            "ambiguity_detected": True,
            "ambiguity_reason": f"Subjective query '{prompt}' is ambiguous. In MedData's zero-hallucination architecture, we do not guess what 'best' means for you.",
            "clarification_options": clarification_options,
            "total_matches": 0,
            "returned_rows": 0,
            "data": None,
            "applied_rules": ["Ambiguity Intercepted - Awaiting User Clarification"],
            "table_name": profile.table_name,
            "inferred_domain": profile.inferred_domain
        }

    filtered_df = df.copy()

    # 1. Specialized Education / College Sort Rules
    if "nirf" in prompt_lower or "national rank" in prompt_lower or "ranking" in prompt_lower:
        if "NIRF_Rank" in filtered_df.columns:
            filtered_df = filtered_df.sort_values(by="NIRF_Rank", ascending=True)
            applied_rules.append("Sorted by NIRF National Rank (1 = Top Rank)")
    elif any(k in prompt_lower for k in ["placement package", "package", "highest placement", "lpa"]):
        if "Avg_Package_LPA" in filtered_df.columns:
            filtered_df = filtered_df.sort_values(by="Avg_Package_LPA", ascending=False)
            applied_rules.append("Sorted by Average Placement Package LPA (DESC)")
        elif "Salary_INR_LPA" in filtered_df.columns:
            filtered_df = filtered_df.sort_values(by="Salary_INR_LPA", ascending=False)
            applied_rules.append("Sorted by Annual Salary LPA (DESC)")
    elif "placement rate" in prompt_lower:
        if "Placement_Rate" in filtered_df.columns:
            filtered_df = filtered_df.sort_values(by="Placement_Rate", ascending=False)
            applied_rules.append("Sorted by Placement Rate % (DESC)")

    # 2. Price / Cost Filtering (Support ₹, Rs, K, Lakhs, INR)
    price_col = profile.primary_price_col
    if price_col and price_col in filtered_df.columns:
        lakh_match = re.search(r"(?:under|below|less than|<=|<|\$|₹|rs\.?)\s*(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|l)\b", prompt_lower)
        k_match = re.search(r"(?:under|below|less than|<=|<|\$|₹|rs\.?)\s*(\d+(?:\.\d+)?)\s*(?:k|thousand)\b", prompt_lower)
        num_match = re.search(r"(?:under|below|less than|<=|<|\$|₹|rs\.?)\s*(\d{3,7})", prompt_lower)
        
        target_max_price = None
        if lakh_match:
            target_max_price = float(lakh_match.group(1)) * 100000
        elif k_match:
            target_max_price = float(k_match.group(1)) * 1000
        elif num_match:
            target_max_price = float(num_match.group(1))
            
        if target_max_price is not None:
            filtered_df = filtered_df[filtered_df[price_col] <= target_max_price]
            applied_rules.append(f"Price / Fee ({price_col}) ≤ ₹{int(target_max_price):,}")

    # 3. Rating / Score Filtering
    rating_col = profile.primary_rating_col
    if rating_col and rating_col in filtered_df.columns:
        rating_match = re.search(r"(?:rating|score|stars?)\s*(?:>=|>|above|at least|min)\s*(\d+(?:\.\d+)?)", prompt_lower)
        if rating_match:
            min_r = float(rating_match.group(1))
            filtered_df = filtered_df[filtered_df[rating_col] >= min_r]
            applied_rules.append(f"Score ({rating_col}) ≥ {min_r}")

    # 4. Categorical / Locality / Keyword Filtering
    for col_name, col_prof in profile.columns.items():
        if col_prof.semantic_role == SemanticColumnRole.CATEGORY_TYPE:
            unique_vals = [str(v) for v in df[col_name].dropna().unique()]
            for val in unique_vals:
                if len(val) > 2 and val.lower() in prompt_lower:
                    filtered_df = filtered_df[filtered_df[col_name].astype(str).str.lower() == val.lower()]
                    applied_rules.append(f"Filtered {col_name} == '{val}'")
                    break

    # 5. Sorting & Ordering
    if any(k in prompt_lower for k in ["cheapest", "lowest price", "lowest fee", "lowest fees", "lowest tuition", "lowest rent", "affordable", "budget", "lowest cost", "tuition fees"]):
        if price_col and price_col in filtered_df.columns:
            filtered_df = filtered_df.sort_values(by=price_col, ascending=True)
            applied_rules.append(f"Sorted by lowest {price_col} (ASC - Most Affordable)")
    elif any(k in prompt_lower for k in ["safest", "lowest crime", "low crime"]):
        for col_name, col_prof in profile.columns.items():
            if col_prof.semantic_role == SemanticColumnRole.SAFETY_RISK:
                filtered_df = filtered_df.sort_values(by=col_name, ascending=True)
                applied_rules.append(f"Sorted by lowest {col_name} (ASC - Safest)")
                break

    # 6. Limit / Rows
    limit = 25
    if "all" in prompt_lower or "directory" in prompt_lower or "everything" in prompt_lower:
        limit = len(filtered_df)
    
    result_df = filtered_df.head(limit)

    return {
        "success": True,
        "ambiguity_detected": False,
        "total_matches": len(filtered_df),
        "returned_rows": len(result_df),
        "data": result_df,
        "applied_rules": applied_rules if applied_rules else ["Full semantic scan (No restrictive threshold)"],
        "table_name": profile.table_name,
        "inferred_domain": profile.inferred_domain
    }


def get_sample_dataset(name: str) -> pd.DataFrame:
    """Returns curated Indian demonstration datasets for zero-shot testing."""
    if "Colleges" in name:
        # Predefined Top 25 Anchor Institutions
        anchors = [
            ("IIT Madras", "Chennai", "Tamil Nadu", 1, 220000, 21.48, 96.2, 12.9915, 80.2337),
            ("IIT Delhi", "New Delhi", "Delhi", 2, 225000, 25.82, 98.1, 28.5450, 77.1926),
            ("IIT Bombay", "Mumbai", "Maharashtra", 3, 230000, 23.50, 97.5, 19.1334, 72.9133),
            ("IIT Kanpur", "Kanpur", "Uttar Pradesh", 4, 215000, 22.00, 95.0, 26.5123, 80.2329),
            ("IIT Kharagpur", "Kharagpur", "West Bengal", 5, 210000, 19.36, 94.8, 22.3149, 87.3105),
            ("IIT Roorkee", "Roorkee", "Uttarakhand", 6, 220000, 18.34, 93.5, 29.8649, 77.8965),
            ("IIT Guwahati", "Guwahati", "Assam", 7, 218000, 18.70, 92.0, 26.1878, 91.6916),
            ("IIT Hyderabad", "Hyderabad", "Telangana", 8, 225000, 20.10, 94.0, 17.5947, 78.1230),
            ("NIT Trichy", "Tiruchirappalli", "Tamil Nadu", 9, 150000, 14.50, 91.0, 10.7589, 78.8132),
            ("Jadavpur University", "Kolkata", "West Bengal", 10, 12000, 11.20, 89.5, 22.4989, 88.3716),
            ("VIT Vellore", "Vellore", "Tamil Nadu", 11, 198000, 9.80, 88.0, 12.9692, 79.1559),
            ("NIT Surathkal", "Mangaluru", "Karnataka", 12, 160000, 14.20, 92.5, 13.0108, 74.7943),
            ("Anna University", "Chennai", "Tamil Nadu", 13, 35000, 8.50, 85.0, 13.0109, 80.2354),
            ("IIT BHU Varanasi", "Varanasi", "Uttar Pradesh", 14, 228000, 18.20, 93.0, 25.2677, 82.9913),
            ("IIT ISM Dhanbad", "Dhanbad", "Jharkhand", 15, 215000, 16.90, 91.5, 23.8143, 86.4412),
            ("NIT Rourkela", "Rourkela", "Odisha", 16, 155000, 13.80, 90.0, 22.2530, 84.9010),
            ("IIT Indore", "Indore", "Madhya Pradesh", 17, 220000, 17.50, 92.0, 22.5204, 75.9207),
            ("BITS Pilani", "Pilani", "Rajasthan", 18, 480000, 19.80, 95.4, 28.3588, 75.5880),
            ("IIIT Hyderabad", "Hyderabad", "Telangana", 19, 360000, 32.00, 99.0, 17.4455, 78.3489),
            ("DTU (Delhi Tech Univ)", "New Delhi", "Delhi", 20, 190000, 15.60, 91.2, 28.7501, 77.1177),
            ("COEP Tech University", "Pune", "Maharashtra", 21, 95000, 11.40, 88.5, 18.5293, 73.8565),
            ("RV College of Engineering", "Bengaluru", "Karnataka", 22, 250000, 12.80, 92.0, 12.9237, 77.4987),
            ("PSG College of Tech", "Coimbatore", "Tamil Nadu", 23, 85000, 10.20, 87.5, 11.0245, 77.0028),
            ("Thapar Institute (TIET)", "Patiala", "Punjab", 24, 420000, 12.50, 89.0, 30.3564, 76.3647),
            ("VIT Chennai", "Chennai", "Tamil Nadu", 25, 198000, 9.50, 88.0, 12.8406, 80.1534)
        ]

        colleges_list = []
        for name_i, city_i, state_i, rank_i, fee_i, lpa_i, rate_i, lat_i, lng_i in anchors:
            colleges_list.append({
                "College_Name": name_i,
                "City": city_i,
                "State": state_i,
                "NIRF_Rank": rank_i,
                "Annual_Fees_INR": fee_i,
                "Avg_Package_LPA": lpa_i,
                "Placement_Rate": rate_i,
                "Latitude": lat_i,
                "Longitude": lng_i
            })

        # Generate Ranks 26 to 200 across Indian States & Educational Hubs
        hub_cities = [
            ("Bengaluru", "Karnataka", 12.9716, 77.5946),
            ("Hyderabad", "Telangana", 17.3850, 78.4867),
            ("Chennai", "Tamil Nadu", 13.0827, 80.2707),
            ("Pune", "Maharashtra", 18.5204, 73.8567),
            ("Mumbai", "Maharashtra", 19.0760, 72.8777),
            ("New Delhi", "Delhi", 28.6139, 77.2090),
            ("Jaipur", "Rajasthan", 26.9124, 75.7873),
            ("Ahmedabad", "Gujarat", 23.0225, 72.5714),
            ("Kolkata", "West Bengal", 22.5726, 88.3639),
            ("Bhopal", "Madhya Pradesh", 23.2599, 77.4126),
            ("Chandigarh", "Punjab", 30.7333, 76.7794),
            ("Kochi", "Kerala", 9.9312, 76.2673),
            ("Lucknow", "Uttar Pradesh", 26.8467, 80.9462),
            ("Coimbatore", "Tamil Nadu", 11.0168, 76.9558),
            ("Bhubaneswar", "Odisha", 20.2961, 85.8245)
        ]

        prefixes = [
            "National Institute of Technology", "Indian Institute of Information Technology",
            "State Institute of Engineering", "Birla Institute of Applied Tech",
            "Government College of Engineering", "SRM Institute of Science & Tech",
            "Manipal Institute of Technology", "Amrita School of Engineering",
            "Shiv Nadar University", "Symbiosis Institute of Tech",
            "BMS College of Engineering", "Ramaiah Institute of Technology",
            "PES University", "Kalinga Institute of Industrial Tech",
            "Sathyabama Institute of Science", "Lovely Professional University",
            "Vellore Institute of Technology", "Chitkara University",
            "Maharaja Agrasen Institute", "Netaji Subhas University of Tech"
        ]

        rng = random.Random(108)
        for rank in range(26, 201):
            prefix = prefixes[(rank - 26) % len(prefixes)]
            city, state, c_lat, c_lng = hub_cities[(rank * 3) % len(hub_cities)]
            coll_name = f"{prefix}, {city}"
            if any(c["College_Name"] == coll_name for c in colleges_list):
                coll_name = f"{prefix} (Campus {rank % 4 + 1}), {city}"

            fee = rng.choice([45000, 85000, 125000, 160000, 195000, 240000, 310000, 380000])
            lpa = round(rng.uniform(6.2, 16.5), 2)
            p_rate = round(rng.uniform(76.0, 94.5), 1)
            lat = round(c_lat + rng.uniform(-0.06, 0.06), 4)
            lng = round(c_lng + rng.uniform(-0.06, 0.06), 4)

            colleges_list.append({
                "College_Name": coll_name,
                "City": city,
                "State": state,
                "NIRF_Rank": rank,
                "Annual_Fees_INR": fee,
                "Avg_Package_LPA": lpa,
                "Placement_Rate": p_rate,
                "Latitude": lat,
                "Longitude": lng
            })

        return pd.DataFrame(colleges_list)

    elif "Cars" in name:
        return pd.DataFrame([
            {"Car_Model": "Hyundai Creta SX", "Brand": "Hyundai", "Fuel_Type": "Petrol", "Year": 2022, "Price_INR": 1350000, "Mileage_kmpl": 17.0, "City": "Bengaluru", "Kms_Driven": 24000},
            {"Car_Model": "Tata Nexon Fearless", "Brand": "Tata", "Fuel_Type": "Diesel", "Year": 2023, "Price_INR": 1180000, "Mileage_kmpl": 23.2, "City": "Mumbai", "Kms_Driven": 14000},
            {"Car_Model": "Maruti Brezza ZXi", "Brand": "Maruti Suzuki", "Fuel_Type": "CNG", "Year": 2023, "Price_INR": 1050000, "Mileage_kmpl": 25.5, "City": "Delhi-NCR", "Kms_Driven": 18000},
            {"Car_Model": "Mahindra XUV700 AX7", "Brand": "Mahindra", "Fuel_Type": "Diesel", "Year": 2022, "Price_INR": 2150000, "Mileage_kmpl": 15.2, "City": "Hyderabad", "Kms_Driven": 32000},
            {"Car_Model": "Honda City ZX", "Brand": "Honda", "Fuel_Type": "Petrol", "Year": 2021, "Price_INR": 1200000, "Mileage_kmpl": 18.4, "City": "Pune", "Kms_Driven": 28000},
            {"Car_Model": "Toyota Innova Crysta", "Brand": "Toyota", "Fuel_Type": "Diesel", "Year": 2020, "Price_INR": 1850000, "Mileage_kmpl": 14.8, "City": "Chennai", "Kms_Driven": 65000},
            {"Car_Model": "Kia Seltos GTX+", "Brand": "Kia", "Fuel_Type": "Petrol", "Year": 2023, "Price_INR": 1720000, "Mileage_kmpl": 16.5, "City": "Delhi-NCR", "Kms_Driven": 12000},
            {"Car_Model": "Maruti Swift VXi", "Brand": "Maruti Suzuki", "Fuel_Type": "Petrol", "Year": 2021, "Price_INR": 620000, "Mileage_kmpl": 22.4, "City": "Ahmedabad", "Kms_Driven": 35000}
        ])
    else:
        # Tech roles & salaries
        return pd.DataFrame([
            {"Job_Title": "Senior Backend Engineer", "Company": "Swiggy", "Tech_Stack": "Go / Java / Redis", "Salary_INR_LPA": 38.0, "Experience_Yrs": 5, "City": "Bengaluru", "Work_Mode": "Hybrid"},
            {"Job_Title": "Distributed Systems Architect", "Company": "Uber", "Tech_Stack": "Go / Kafka / Cassandra", "Salary_INR_LPA": 65.0, "Experience_Yrs": 8, "City": "Bengaluru", "Work_Mode": "In-Office"},
            {"Job_Title": "Full Stack SDE 2", "Company": "Zomato", "Tech_Stack": "Node.js / React / PostgreSQL", "Salary_INR_LPA": 32.0, "Experience_Yrs": 4, "City": "Delhi-NCR", "Work_Mode": "In-Office"},
            {"Job_Title": "Machine Learning Engineer", "Company": "Flipkart", "Tech_Stack": "Python / PyTorch / Spark", "Salary_INR_LPA": 42.0, "Experience_Yrs": 5, "City": "Bengaluru", "Work_Mode": "Hybrid"},
            {"Job_Title": "DevOps & Cloud Engineer", "Company": "PhonePe", "Tech_Stack": "Kubernetes / Terraform / GCP", "Salary_INR_LPA": 28.0, "Experience_Yrs": 3, "City": "Bengaluru", "Work_Mode": "Hybrid"},
            {"Job_Title": "SDE 1 (Frontend)", "Company": "CRED", "Tech_Stack": "React Native / TypeScript", "Salary_INR_LPA": 22.0, "Experience_Yrs": 1, "City": "Bengaluru", "Work_Mode": "In-Office"}
        ])
