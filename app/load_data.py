import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import *
import sys
import streamlit as st
import pandas as pd

def load_data() -> pd.DataFrame:
    df1 = pd.read_excel(data1, sheet_name=0)
    df2 = pd.read_excel(data2, sheet_name=0)
    df = master_cleaned_df
    df["Farmer_Mobile"] = df["Farmer_Mobile"]
    df["Claimed_Area"] = df.get("Claimed_Area")
    df["Actual_Area"] = df.get("Actual_Area")
    df["Tree_area_in_acre"] = df.get("Tree_area_in_acre").apply(to_number)
    df["Trees/acre"] = df.get("Trees/acre").apply(to_number)
    df["Spacing_ft"] = df.get("Spacing_ft") if "Spacing_ft" in df.columns else df.get("Spacing")
    if df["Spacing_ft"].dtype == object:
        df["Spacing_ft"] = df["Spacing_ft"].apply(to_number)
    df["Tree_Count"] = df.get("Tree_Count").apply(to_number) if "Tree_Count" in df.columns else np.nan
    df["Total_Trees"] = df["Tree_Count"].fillna(0)

    
    species_cols = find_species_indicator_columns(df)
    species_rows = []
    for _, row in df.iterrows():
        species_counts = row_species_counts(row, species_cols)
        for species, count in species_counts.items():
            species_rows.append({
                "UUID": row.get("_uuid"),
                "Farmer_Name": row.get("Farmer_Name"),
                "Block_Name": row.get("Block_Name"),
                "Village_Name": row.get("Village_Name"),
                "Species": species,
                "Count": count,
                "Area_acre": row.get("Tree_area_in_acre") or row.get("Claimed_Area") or row.get("Actual_Area"),
                "Spacing_ft": row.get("Spacing_ft"),
                "Trees_per_acre": row.get("Trees/acre"),
                "Quality": quality_label(row),
                "Error": row.get("Error"),
            })
    species_df = pd.DataFrame(species_rows)
    # species_df["Estimated_Carbon_mt"] = species_df["Species"].map(lambda s: SPECIES_FACTORS.get(s, 0.09) * species_df["Count"])
    species_df["Carbon_Factor"] = species_df["Species"].map(lambda s: SPECIES_FACTORS.get(s, 0.09))
    species_df["Estimated_Carbon_mt"] = species_df["Carbon_Factor"] * species_df["Count"]
    return df, species_df