from app.services.diamond_service import DiamondService

class RecommendationService:
    def __init__(self):
        self.diamond_service = DiamondService()

    def recommend_by_budget(self, budget: float, preference: str = "balanced"):
        diamonds = self.diamond_service.get_diamonds_by_budget(budget)

        if diamonds.empty:
            return []

        min_price = budget * 0.7
        preferred_diamonds = diamonds[diamonds["price"] >= min_price].copy()

        if preferred_diamonds.empty:
            preferred_diamonds = diamonds.copy()

        preferred_diamonds["quality_score"] = (
            preferred_diamonds["cut_encoded"]
            + preferred_diamonds["color_encoded"]
            + preferred_diamonds["clarity_encoded"]
        )

        preferred_diamonds["value_score"] = (
            preferred_diamonds["carat"] / preferred_diamonds["price"]
        )

        if preference == "largest":
            recommended = preferred_diamonds.sort_values(
                by=["carat", "quality_score", "price"],
                ascending=[False, False, True]
            ).head(5)

        elif preference == "quality":
            recommended = preferred_diamonds.sort_values(
                by=["quality_score", "carat", "price"],
                ascending=[False, False, True]
            ).head(5)

        elif preference == "value":
            recommended = preferred_diamonds.sort_values(
                by=["value_score", "quality_score", "carat"],
                ascending=[False, False, False]
            ).head(5)

        else:
            recommended = preferred_diamonds.sort_values(
                by=["quality_score", "carat", "price"],
                ascending=[False, False, True]
            ).head(5)

        return recommended[
            ["carat", "cut", "color", "clarity", "price"]
        ].to_dict(orient="records")

    def recommend_from_diamonds2(self, budget: float, preference: str = "balanced", shape: str = None):
        diamonds = self.diamond_service.get_diamonds2_by_budget(budget)

        if diamonds.empty:
            return []

        if shape:
            diamonds = diamonds[
                diamonds["Shape"].astype(str).str.lower() == shape.lower()
            ].copy()

        if diamonds.empty:
            return []

        min_price = budget * 0.7
        preferred_diamonds = diamonds[diamonds["Price"] >= min_price].copy()

        if preferred_diamonds.empty:
            preferred_diamonds = diamonds.copy()

        if preference == "largest":
            recommended = preferred_diamonds.sort_values(
                by=["Carat Weight", "Price"],
                ascending=[False, True]
            ).head(5)

        elif preference == "quality":
            recommended = preferred_diamonds.sort_values(
                by=["Cut", "Color", "Clarity", "Carat Weight"],
                ascending=[True, True, True, False]
            ).head(5)

        else:
            recommended = preferred_diamonds.sort_values(
                by=["Carat Weight", "Price"],
                ascending=[False, True]
            ).head(5)

        return recommended[
            [
                "Shape",
                "Carat Weight",
                "Cut",
                "Color",
                "Clarity",
                "Polish",
                "Symmetry",
                "Girdle",
                "Price",
                "Type"
            ]
        ].to_dict(orient="records")