import sys
from pathlib import Path
import os
import plotly.express as px
import numpy as np
import pandas as pd
import streamlit as st
from plot_reports import plot_report 
project_root = "/home/ajai-krishna/work/website_streamlit/streamlit_app/src"
sys.path.insert(0, project_root)

from config import *
import xml.etree.ElementTree as ET

# ── helpers ──────────────────────────────────────────────────────────────────

def safe_read(path, **kwargs):
    try:
        if path and os.path.exists(path):
            df = pd.read_excel(path, **kwargs)
            # kill mixed-type object cols (str+datetime+int etc)
            for col in df.select_dtypes(include="object").columns:
                df[col] = df[col].astype(str).replace({"nan": np.nan, "NaT": np.nan})
            return df
    except Exception as e:
        st.error(f"Read fail {path}: {e}")
    return pd.DataFrame()


def fmt(val, suffix=""):
    """Format large numbers nicely."""
    try:
        v = float(val)
        if v >= 1_000_000:
            return f"{v/1_000_000:.1f}M{suffix}"
        if v >= 1_000:
            return f"{v/1_000:.1f}K{suffix}"
        return f"{v:,.0f}{suffix}"
    except Exception:
        return str(val)
    

# ── VISUAL HELPERS (add near top, after fmt()) ─────────────────────────────

def kpi_cards(items, cols_per_row=6):
        """items: list of (label, value, color) tuples. color: 'green'|'orange'|'black'"""
        color_map = {"green": "#1e8e3e", "orange": "#e67e22", "black": "#111"}
        css = """
        <style>
        .kpi-card {border:1px solid #ddd; border-radius:8px; padding:14px 10px;
                text-align:center; background:#fff; margin-bottom:8px;}
        .kpi-val {font-size:26px; font-weight:700;}
        .kpi-label {font-size:13px; color:#666; margin-top:4px;}
        </style>
        """
        st.markdown(css, unsafe_allow_html=True)
        rows = [items[i:i+cols_per_row] for i in range(0, len(items), cols_per_row)]
        for row in rows:
            cols = st.columns(len(row))
            for c, (label, val, color) in zip(cols, row):
                hexcol = color_map.get(color, "#111")
                c.markdown(
                    f'<div class="kpi-card"><div class="kpi-val" style="color:{hexcol}">{val}</div>'
                    f'<div class="kpi-label">{label}</div></div>',
                    unsafe_allow_html=True
                )

def bar_rows(df, label_col, value_col, title="Total", highlight_top_n=0):
        """Horizontal bar list like species breakdown panel."""
        d = df[[label_col, value_col]].copy()
        d[value_col] = pd.to_numeric(d[value_col], errors="coerce").fillna(0)
        d = d.sort_values(value_col, ascending=False)
        max_val = d[value_col].max() or 1

        css = """
        <style>
        .bar-row {display:flex; align-items:center; margin-bottom:6px; font-size:14px;}
        .bar-label {width:150px; flex-shrink:0; color:#333;}
        .bar-track {flex:1; background:#eee; border-radius:3px; height:18px; position:relative;}
        .bar-fill {background:#8f8f7a; height:100%; border-radius:3px;}
        .bar-fill.hi {background:#7ee08a;}
        .bar-val {width:50px; text-align:right; font-weight:600; padding-left:8px;}
        </style>
        """
        st.markdown(css, unsafe_allow_html=True)
        st.markdown(f"**{title}**")
        for i, (_, r) in enumerate(d.iterrows()):
            pct = (r[value_col] / max_val) * 100
            cls = "hi" if i < highlight_top_n else ""
            st.markdown(
                f'<div class="bar-row"><div class="bar-label">{r[label_col]}</div>'
                f'<div class="bar-track"><div class="bar-fill {cls}" style="width:{pct}%"></div></div>'
                f'<div class="bar-val">{fmt(r[value_col])}</div></div>',
                unsafe_allow_html=True
            )


# ── file paths ────────────────────────────────────────────────────────────────

overlap_path        = os.path.join(f"{output_dir}/overlap_analysis.xlsx")
duplicate_uuid_path = os.path.join(f"{data_overview_out}/duplicate_uuids.xlsx")
invalid_mobile_path = os.path.join(f"{data_overview_out}/invalid_phone_numbers.xlsx")
missing_name_path   = os.path.join(f"{data_overview_out}/missing_farmers_names.xlsx")
missing_uuid_path   = os.path.join(f"{data_overview_out}/missing_uuids.xlsx")
missing_village_path= os.path.join(f"{data_overview_out}/missing_village_names.xlsx")
uuid_path           = os.path.join(f"{output_gis_validation}/uuid_report.xlsx")
kobo_val_path       = os.path.join(f"{output_gis_validation}/validation.xlsx")
invalid_coords_path = os.path.join(f"{output_gis_validation}/invalid_coordinates.xlsx")
master_path         = os.path.join(f"{output_dir}/master_Database_cleaned.xlsx")
completion_path     = os.path.join(f"{output_dir}/completion_report.xlsx")
summary_path        = os.path.join(f"{output_dir}/summary.xlsx")
species_path        = os.path.join(f"{output_dir}/species_summary.xlsx")
data_quality_path   = os.path.join(f"{output_dir}/data_quality.xlsx")
farmer_summary_path = os.path.join(f"{output_dir}/farmer_summary.xlsx")
kml_path            = os.path.join(f"{output_dir}/doc.kml")


# ── data loaders (cached) ─────────────────────────────────────────────────────

@st.cache_data
def load_kml_points(path):
    if not path or not os.path.exists(path):
        return pd.DataFrame()
    try:
        tree = ET.parse(path)
        ns = {"kml": "http://www.opengis.net/kml/2.2"}
        rows = []
        for pm in tree.getroot().iter("{http://www.opengis.net/kml/2.2}Placemark"):
            name_el = pm.find("kml:name", ns)
            coord_el = pm.find(".//kml:coordinates", ns)
            if coord_el is not None and coord_el.text:
                coord_text = coord_el.text.strip().split()[0]  # first point only
                parts = coord_text.split(",")
                if len(parts) >= 2:
                    lon, lat = float(parts[0]), float(parts[1])
                    rows.append({
                        "name": name_el.text if name_el is not None else "",
                        "lat": lat, "lon": lon
                    })
        return pd.DataFrame(rows)
    except Exception as e:
        st.error(f"KML parse fail: {e}")
        return pd.DataFrame()

@st.cache_data
def load_master():
    return safe_read(master_path)

@st.cache_data
def load_summary():
    return safe_read(summary_path)

@st.cache_data
def load_species():
    return safe_read(species_path)

@st.cache_data
def load_data_quality():
    return safe_read(data_quality_path)

@st.cache_data
def load_farmer_summary():
    return safe_read(farmer_summary_path)

@st.cache_data
def load_completion():
    return safe_read(completion_path)


# ── TAB 1: DASHBOARD ──────────────────────────────────────────────────────────

def tab_dashboard():

    master      = load_master()
    summary     = load_summary()
    species_df  = load_species()
    quality_df  = load_data_quality()
    farmer_df   = load_farmer_summary()


    # ── KPI Cards ────────────────────────────────────────────────────────────
    st.subheader("Overview")

    # pull scalars from summary sheet if available
    def s(col, default=0):
        if not summary.empty and col in summary.columns:
            return summary[col].iloc[0]
        return default

    total_farmers  = s("total_farmers",  master["Farmer_Name"].nunique()  if "Farmer_Name"  in master.columns else 0)
    total_records  = s("total_rows",     len(master))
    total_trees = s("total_trees", species_df["Trees"].sum() if "Trees" in species_df.columns else 0)
    distinct_sp = s("distinct_species", species_df["tree_cat"].nunique() if "tree_cat" in species_df.columns else 0)
    total_villages = master["Village_Name"].nunique() if "Village_Name" in master.columns else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Farmers",  fmt(total_farmers))
    c2.metric("Records",  fmt(total_records))
    c3.metric("Trees",    fmt(total_trees))
    c4.metric("Species",  fmt(distinct_sp))
    c5.metric("Villages", fmt(total_villages))

    st.markdown("---")

    # ── Species Distribution + Plantation Area ────────────────────────────────
    
    
    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("Species Distribution")
        if not species_df.empty and "tree_cat" in species_df.columns and "Trees" in species_df.columns:
            species_df["Trees"] = pd.to_numeric(species_df["Trees"], errors="coerce").fillna(0)
            sp_chart = species_df.groupby("tree_cat", as_index=False)["Trees"].sum().sort_values("Trees", ascending=False).head(15)
            fig = px.scatter(sp_chart, x="tree_cat", y="Trees", size="Trees", color="tree_cat",
                            title="Species Distribution", size_max=40)
            fig.update_layout(showlegend=False, xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No species data available.")

    with col_r:
        st.subheader("Plantation Area — Claimed vs Actual (acres)")
        if not master.empty:
            has_claimed = "Claimed_Area" in master.columns
            has_actual  = "Actual_Area"  in master.columns
            if has_claimed or has_actual:
                area_data = {}
                if has_claimed:
                    area_data["Claimed"] = pd.to_numeric(master["Claimed_Area"], errors="coerce").sum()
                if has_actual:
                    area_data["Actual"]  = pd.to_numeric(master["Actual_Area"],  errors="coerce").sum()
                st.bar_chart(pd.Series(area_data))
            else:
                st.info("No area columns found.")
        else:
            st.info("No master data available.")

    st.markdown("---")

    # ── Farmer Search & Details ───────────────────────────────────────────────
    st.subheader("Farmer Search & Details")

    if not master.empty and "Farmer_Name" in master.columns:
        search = st.text_input("Search farmer by name or mobile", "")
        filtered = master.copy()
        if search:
            mask = filtered["Farmer_Name"].astype(str).str.contains(search, case=False, na=False)
            if "Farmer_Mobile" in filtered.columns:
                mask |= filtered["Farmer_Mobile"].astype(str).str.contains(search, case=False, na=False)
            filtered = filtered[mask]

        st.caption(f"{len(filtered)} record(s) found")
        show_cols = [c for c in [
            "Farmer_Name", "Farmer_Mobile", "Village_Name",
            "Block_Name", "Claimed_Area", "Actual_Area",
            "Total_Trees", "tree_cat", "_uuid"
        ] if c in filtered.columns]
        st.dataframe(filtered[show_cols].head(100), width="stretch")
    else:
        st.info("Master data not loaded.")

    st.markdown("---")

    # ── Data Quality + GIS Validation ─────────────────────────────────────────
    # col_l2, col_r2 = st.columns(2)

    # with col_l2:
    #     st.subheader("Data Quality Summary")
    #     if not quality_df.empty:
    #         st.dataframe(quality_df, width="stretch")
    #     elif not master.empty:
    #         # fallback: build quick quality counts from master
    #         def quality_label(row):
    #             error = str(row.get("Error", "")).strip().lower()
    #             if error and error not in {"nan", "none", ""}:
    #                 return "Wrong"
    #             for col in ["Correct lat/long", "KML check", "10 yr KML check"]:
    #                 if str(row.get(col, "")).strip().lower() in {"yes", "true", "pass", "correct"}:
    #                     return "Correct"
    #             return "Correct"
    #         counts = master.apply(quality_label, axis=1).value_counts().rename_axis("Status").reset_index(name="Count")
    #         st.dataframe(counts, width="stretch")
    #     else:
    #         st.info("No quality data available.")

    # with col_r2:
    #     st.subheader("GIS Validation Summary")
    #     kobo_df = safe_read(kobo_val_path)
    #     if not kobo_df.empty:
    #         st.dataframe(kobo_df.head(50), width="stretch")
    #     else:
    #         uuid_df = safe_read(uuid_path)
    #         if not uuid_df.empty:
    #             st.dataframe(uuid_df.head(50), width="stretch")
    #         else:
    #             st.info("No GIS validation data available.")
    col_l2, col_r2 = st.columns(2)

    with col_l2:
        st.subheader("Data Quality")
        if not quality_df.empty and "Issue" in quality_df.columns and "Count" in quality_df.columns:
            fig = px.bar(quality_df, x="Count", y="Issue", orientation="h", text="Count")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data quality data available.")

    with col_r2:
        st.subheader("GIS Validation")
        kobo_df = safe_read(kobo_val_path)
        if not kobo_df.empty and "Status" in kobo_df.columns:
            gis = kobo_df["Status"].value_counts().reset_index()
            gis.columns = ["Status", "Count"]
            fig = px.pie(gis, names="Status", values="Count", hole=0.5)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No GIS validation data available.")

    st.markdown("---")

    # ── Village Summary + Block Summary ──────────────────────────────────────
    col_l3, col_r3 = st.columns(2)

    with col_l3:
        st.subheader("Village Summary")
        if not master.empty and "Village_Name" in master.columns:
            vcols = [c for c in ["Village_Name", "Farmer_Name", "Total_Trees", "Claimed_Area"] if c in master.columns]
            village_sum = (
                master.groupby("Village_Name")
                .agg({c: ("nunique" if c == "Farmer_Name" else "sum") for c in vcols if c != "Village_Name"})
                .reset_index()
                .sort_values("Total_Trees" if "Total_Trees" in master.columns else vcols[1], ascending=False)
            )
            st.dataframe(village_sum.rename(columns={"Farmer_Name": "Farmers"}), width="stretch")
        else:
            st.info("No village data available.")

    with col_r3:
        st.subheader("Block Summary")
        if not master.empty and "Block_Name" in master.columns:
            bcols = [c for c in ["Block_Name", "Farmer_Name", "Total_Trees", "Claimed_Area"] if c in master.columns]
            block_sum = (
                master.groupby("Block_Name")
                .agg({c: ("nunique" if c == "Farmer_Name" else "sum") for c in bcols if c != "Block_Name"})
                .reset_index()
                .sort_values("Total_Trees" if "Total_Trees" in master.columns else bcols[1], ascending=False)
            )
            st.dataframe(village_sum.rename(columns={"Farmer_Name": "Farmers"}), width="stretch")
        else:
            st.info("No block data available.")

    st.markdown("---")

    # ── Interactive GIS Map ───────────────────────────────────────────────────
    # lat_cols = [c for c in master.columns if "lat" in c.lower()]
    # lon_cols = [c for c in master.columns if "lon" in c.lower() or "lng" in c.lower()]
    # st.write("lat cols:", lat_cols)
    # st.write("lon cols:", lon_cols)
    # if lat_cols and lon_cols:
    #     st.write(master[[lat_cols[0], lon_cols[0]]].head(10))
    #     st.write(master[[lat_cols[0], lon_cols[0]]].dtypes)
    st.subheader("Interactive GIS Map")
    kml_df = load_kml_points(kml_path)
    if not kml_df.empty:
        st.map(kml_df[["lat", "lon"]], zoom=10)
        with st.expander("Points detail"):
            st.dataframe(kml_df, width="stretch")
    else:
        st.info("No points found in KML.")

    # ── Key Findings & Insights ───────────────────────────────────────────────
    st.subheader("Key Findings & Insights")

    insights = []

    # species insight — own guard
    if not species_df.empty and "tree_cat" in species_df.columns and "Trees" in species_df.columns:
        species_df["Trees"] = pd.to_numeric(species_df["Trees"], errors="coerce").fillna(0)
        top3 = species_df.groupby("tree_cat")["Trees"].sum().nlargest(3).index.tolist()
        insights.append(f"Top 3 species by tree count: **{', '.join(top3)}**")

    # area insight — own guard, independent of species
    if not master.empty and "Claimed_Area" in master.columns and "Actual_Area" in master.columns:
        claimed = pd.to_numeric(master["Claimed_Area"], errors="coerce").sum()
        actual  = pd.to_numeric(master["Actual_Area"],  errors="coerce").sum()
        if claimed > 0:
            diff_pct = (actual - claimed) / claimed * 100
            insights.append(f"Actual area is **{diff_pct:+.1f}%** vs claimed area across all records.")

    # village insight
    if not master.empty and "Village_Name" in master.columns:
        top_village = master.groupby("Village_Name").size().idxmax()
        insights.append(f"Most active village: **{top_village}**")

    # farmer insight — verify real trees col name first (see note below)
    if not master.empty and "Farmer_Name" in master.columns:
        trees_col = "Trees count " if "Trees count " in master.columns else ("Total_Trees" if "Total_Trees" in master.columns else None)
        if trees_col:
            master[trees_col] = pd.to_numeric(master[trees_col], errors="coerce").fillna(0)
            top_farmer = master.groupby("Farmer_Name")[trees_col].sum().idxmax()
            insights.append(f"Highest tree-count farmer: **{top_farmer}**")

    if not insights:
        insights.append("Load output Excel files to see insights.")

    for i in insights:
        st.markdown(f"- {i}")


def tab_reports():

    st.subheader("Reports")

    report_sections = [
    ("Completion Report",       completion_path),
    ("Farmer Summary",          farmer_summary_path),
    ("Species Summary",         species_path),
    ("UUID GIS Report",         uuid_path),
    ("Kobo Validation",         kobo_val_path),
    ("Data Quality",            data_quality_path),
    ("Overlap Analysis",        overlap_path),
    ("Duplicate UUIDs",         duplicate_uuid_path),
    ("Invalid Phone Numbers",   invalid_mobile_path),
    ("Missing Farmer Names",    missing_name_path),
    ("Master Cleaned Data",     master_path)]

    for label, path in report_sections:
        with st.expander(label):
            df = safe_read(path)
            if df.empty:
                st.warning("Report not available.")
                continue

            st.caption(f"{len(df)} rows · {len(df.columns)} columns")

            plot_report(label, df)   # 2 args only — matches plot_reports.py signature

            if st.checkbox("View Data", key=f"view_{label}"):
                st.dataframe(df, width="stretch")

            st.download_button(
                "Download CSV",
                df.to_csv(index=False).encode(),
                file_name=f"{label}.csv",
                mime="text/csv",
                key=f"dl_{label}"
            )


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title="Greenipath Farmer Dashboard",
        layout="wide"
    )

    st.title("Greenipath Farmer Dashboard")
    st.caption("Farmer records · Species · GIS validation · Carbon estimates")

    tab1, tab2 = st.tabs(["Dashboard", "Reports"])

    with tab1:
        tab_dashboard()

    with tab2:
        tab_reports()


if __name__ == "__main__":
    main()
