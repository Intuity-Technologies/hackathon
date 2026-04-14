import pandas as pd


def minmax_score(series: pd.Series) -> pd.Series:
    min_val = series.min()
    max_val = series.max()

    if pd.isna(min_val) or pd.isna(max_val) or max_val == min_val:
        return pd.Series([0.0] * len(series), index=series.index)

    return ((series - min_val) / (max_val - min_val)) * 100.0
