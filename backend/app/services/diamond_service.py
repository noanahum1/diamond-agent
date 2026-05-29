import pandas as pd
from pathlib import Path

class DiamondService:
    def __init__(self):
        base_path = Path(__file__).resolve().parents[3]

        self.diamonds1 = pd.read_csv(base_path / "data" / "processed" / "diamonds1.csv")
        self.diamonds2 = pd.read_csv(base_path / "data" / "processed" / "diamonds2.csv")

        self.diamonds1 = self.diamonds1.loc[:, ~self.diamonds1.columns.str.contains("^Unnamed")]

    def get_diamonds_by_budget(self, budget: float):
        return self.diamonds1[self.diamonds1["price"] <= budget].copy()
    
    def get_diamonds2_by_budget(self, budget: float):
        return self.diamonds2[self.diamonds2["Price"] <= budget].copy()