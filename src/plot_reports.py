import pandas as pd
import plotly.express as px
import streamlit as st


# ── helper: forgiving column resolver ───────────────────────────────────────
def resolve_col(df, candidates):
    """
    Find a column matching any name in `candidates`, ignoring case and
    leading/trailing whitespace. Returns actual column name or None.
    Fixes recurring 'Trees' vs 'Total_Trees' vs 'Trees count ' mismatches.
    """
    norm_map = {c.strip().lower(): c for c in df.columns}
    for cand in candidates:
        key = cand.strip().lower()
        if key in norm_map:
            return norm_map[key]
    return None


def plot_report(report_name, df):
    """
    Plot a report based on its name. Falls back to raw table if expected
    columns aren't found (never renders blank silently).

    Parameters
    ----------
    report_name : str
        Report title.
    df : DataFrame
        Report dataframe.
    """

    if df.empty:
        st.warning("No data available.")
        return

    # -------------------------------------------------------
    # Species Summary
    # -------------------------------------------------------
    if report_name == "Species Summary":
        cat_col = resolve_col(df, ["tree_cat", "Species", "Species_Category"])
        val_col = resolve_col(df, ["Trees", "Total_Trees", "Tree_Count"])

        if cat_col and val_col:
            plot_df = df.copy()
            plot_df[val_col] = pd.to_numeric(plot_df[val_col], errors="coerce").fillna(0)
            fig = px.bar(
                plot_df.sort_values(val_col, ascending=False),
                x=cat_col, y=val_col, color=val_col, text=val_col,
                title="Species Distribution"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"Expected species/count columns not found. Columns: {df.columns.tolist()}")
            st.dataframe(df, width="stretch")

    # -------------------------------------------------------
    # Completion Report
    # -------------------------------------------------------
    elif report_name == "Completion Report":
        field_col = resolve_col(df, ["Field"])
        pct_col   = resolve_col(df, ["Completion %", "Completion", "Completion_Pct"])

        if field_col and pct_col:
            plot_df = df.copy()
            plot_df[pct_col] = pd.to_numeric(plot_df[pct_col], errors="coerce").fillna(0)
            fig = px.bar(
                plot_df, x=pct_col, y=field_col, orientation="h",
                color=pct_col, text=pct_col, title="Field Completion Rate"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"Expected Field/Completion columns not found. Columns: {df.columns.tolist()}")
            st.dataframe(df, width="stretch")

    # -------------------------------------------------------
    # Data Quality
    # -------------------------------------------------------
    elif report_name == "Data Quality":
        issue_col = resolve_col(df, ["Issue", "Status", "Error"])
        count_col = resolve_col(df, ["Count", "count"])

        if issue_col and count_col:
            plot_df = df.copy()
            plot_df[count_col] = pd.to_numeric(plot_df[count_col], errors="coerce").fillna(0)
            fig = px.bar(
                plot_df, x=count_col, y=issue_col, orientation="h",
                color=count_col, text=count_col, title="Data Quality Issues"
            )
            st.plotly_chart(fig, use_container_width=True)
        elif issue_col:
            # no explicit count col — derive via value_counts
            vc = df[issue_col].value_counts().reset_index()
            vc.columns = [issue_col, "Count"]
            fig = px.bar(vc, x="Count", y=issue_col, orientation="h",
                          color="Count", text="Count", title="Data Quality Issues")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"Expected Issue/Count columns not found. Columns: {df.columns.tolist()}")
            st.dataframe(df, width="stretch")

    # -------------------------------------------------------
    # Farmer Summary
    # -------------------------------------------------------
    elif report_name == "Farmer Summary":
        name_col  = resolve_col(df, ["Farmer_Name", "Farmer Name"])
        trees_col = resolve_col(df, ["Total_Trees", "Trees", "Trees count", "Trees count "])

        if name_col and trees_col:
            plot_df = df.copy()
            plot_df[trees_col] = pd.to_numeric(plot_df[trees_col], errors="coerce").fillna(0)
            top = plot_df.sort_values(trees_col, ascending=False).head(20)
            fig = px.bar(
                top, x=name_col, y=trees_col, color=trees_col, text=trees_col,
                title="Top Farmers by Tree Count"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"Expected Farmer_Name/Trees columns not found. Columns: {df.columns.tolist()}")
            st.dataframe(df, width="stretch")

    # -------------------------------------------------------
    # Kobo Validation
    # -------------------------------------------------------
    elif report_name == "Kobo Validation":
        status_col = resolve_col(df, ["Status"])

        if status_col:
            status = df[status_col].value_counts().reset_index()
            status.columns = ["Status", "Count"]
            fig = px.pie(status, names="Status", values="Count", hole=0.45,
                         title="Validation Status")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"Expected Status column not found. Columns: {df.columns.tolist()}")
            st.dataframe(df, width="stretch")

    # -------------------------------------------------------
    # UUID GIS Report
    # -------------------------------------------------------
    elif report_name == "UUID GIS Report":
        excel_col = resolve_col(df, ["In_Excel"])
        kml_col   = resolve_col(df, ["In_KML"])

        if excel_col and kml_col:
            in_excel = df[excel_col].astype(bool)
            in_kml   = df[kml_col].astype(bool)
            summary = pd.DataFrame({
                "Status": ["Matched", "Missing KML", "Missing Excel"],
                "Count": [
                    (in_excel & in_kml).sum(),
                    (in_excel & ~in_kml).sum(),
                    (~in_excel & in_kml).sum(),
                ]
            })
            fig = px.pie(summary, names="Status", values="Count", hole=0.45,
                         title="UUID Match Status")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"Expected In_Excel/In_KML columns not found. Columns: {df.columns.tolist()}")
            st.dataframe(df, width="stretch")

    # -------------------------------------------------------
    # Reports that don't have predefined plots
    # -------------------------------------------------------
    else:
        st.dataframe(df, width="stretch")