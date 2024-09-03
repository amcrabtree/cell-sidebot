"""
    This script runs the main app for querying data. 

    Script adapted from https://github.com/jcheng5/py-sidebot/blob/main/shared.py
"""
from pathlib import Path

import duckdb
import pandas as pd

duckdb.query("SET allow_community_extensions = false;")

here = Path(__file__).parent
cells_df = pd.read_csv(here / "test/cell_data.txt", sep="\t")
slides_df = pd.read_csv(here / "test/slide_data.txt", sep="\t")
print("slides_df columns:", slides_df.columns.tolist())
cells_df = pd.merge(cells_df, slides_df, on='Image', how='left')

# Query data for DuckDb 
#cells_df = cells_df.groupby(['Image', 'Parent', 'Class', 'PD-L1 Status']).size().reset_index(name='Count')
duckdb.register("cells", cells_df)
