from app.services.diamond_service import DiamondService
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler
import numpy as np

class RecommendationService:
    def __init__(self):
        self.diamond_service = DiamondService()

    def recommend_by_budget(
        self,
        budget: float,
        preference: str = "balanced",
        cut: str = None,
        color: str = None,
        clarity: str = None,
        carat: float = None,
        depth: float = None,
        table: float = None
    ):
        diamonds = self.diamond_service.get_diamonds_by_budget(budget)

        if diamonds.empty:
            return []

        diamonds = self._filter_exact(diamonds, "cut", cut)
        diamonds = self._filter_exact(diamonds, "color", color)
        diamonds = self._filter_exact(diamonds, "clarity", clarity)
        diamonds = self._filter_numeric_range(diamonds, "carat", carat, tolerance=0.05)
        diamonds = self._filter_numeric_range(diamonds, "depth", depth, tolerance=1.0)
        diamonds = self._filter_numeric_range(diamonds, "table", table, tolerance=1.0)

        if diamonds.empty:
            return []

        diamonds = self._filter_by_price_range(
            diamonds=diamonds,
            price_column="price",
            budget=budget
        )

        if diamonds.empty:
            return []

        numeric_columns = [
            "carat",
            "cut_encoded",
            "color_encoded",
            "clarity_encoded",
            "depth",
            "table",
            "price"
        ]

        diamonds = self._rank_diamonds1(
            diamonds=diamonds,
            numeric_columns=numeric_columns,
            budget=budget,
            preference=preference
        )

        return diamonds.head(3)[
            ["carat", "cut", "color", "clarity", "depth", "table", "price", "x", "y", "z"]
        ].to_dict(orient="records")

    def recommend_from_diamonds2(
        self,
        budget: float,
        preference: str = "balanced",
        shape: str = None,
        cut: str = None,
        color: str = None,
        clarity: str = None,
        carat: float = None,
        depth: float = None,
        table: float = None,
        polish: str = None,
        symmetry: str = None,
        girdle: str = None,
        diamond_type: str = None,
        length_width_ratio: float = None
    ):
        diamonds = self.diamond_service.get_diamonds2_by_budget(budget)

        if diamonds.empty:
            return []

        diamonds = self._filter_exact(diamonds, "Shape", shape)
        diamonds = self._filter_exact(diamonds, "Cut", cut)
        diamonds = self._filter_exact(diamonds, "Color", color)
        diamonds = self._filter_exact(diamonds, "Clarity", clarity)
        diamonds = self._filter_exact(diamonds, "Polish", polish)
        diamonds = self._filter_exact(diamonds, "Symmetry", symmetry)
        diamonds = self._filter_exact(diamonds, "Girdle", girdle)
        diamonds = self._filter_exact(diamonds, "Type", diamond_type)

        diamonds = self._filter_numeric_range(diamonds, "Carat", carat, tolerance=0.05)
        diamonds = self._filter_numeric_range(diamonds, "Depth %", depth, tolerance=1.0)
        diamonds = self._filter_numeric_range(diamonds, "Table %", table, tolerance=1.0)
        diamonds = self._filter_numeric_range(
            diamonds,
            "Length/Width Ratio",
            length_width_ratio,
            tolerance=0.05
        )

        if diamonds.empty:
            return []

        diamonds = self._filter_by_price_range(
            diamonds=diamonds,
            price_column="Price",
            budget=budget
        )

        if diamonds.empty:
            return []

        numeric_columns = [
            "Carat",
            "Cut_encoded",
            "Color_encoded",
            "Clarity_encoded",
            "Polish_encoded",
            "Symmetry_encoded",
            "Price"
        ]

        categorical_columns = [
            "Shape",
            "Cut",
            "Color",
            "Clarity",
            "Polish",
            "Symmetry",
            "Girdle",
            "Type"
        ]

        diamonds = self._rank_diamonds2(
            diamonds=diamonds,
            numeric_columns=numeric_columns,
            categorical_columns=categorical_columns,
            budget=budget,
            preference=preference
        )

        return diamonds.head(3)[
            [
                "Shape", "Carat", "Cut", "Color",
                "Clarity", "Polish", "Symmetry",
                "Girdle", "Price", "Type",
                "Depth %", "Table %", "Length/Width Ratio",
                "Length", "Width", "Height"
            ]
        ].to_dict(orient="records")

    def _filter_exact(self, diamonds, column_name: str, value):
        if value is None:
            return diamonds

        if column_name not in diamonds.columns:
            return diamonds

        return diamonds[
            diamonds[column_name].astype(str).str.lower().str.strip()
            == str(value).lower().strip()
        ].copy()

    def _filter_numeric_range(self, diamonds, column_name: str, value, tolerance: float):
        if value is None:
            return diamonds

        if column_name not in diamonds.columns:
            return diamonds

        numeric_values = diamonds[column_name].astype(float)

        return diamonds[
            np.isclose(
                numeric_values,
                float(value),
                atol=tolerance
            )
        ].copy()

    def _filter_by_price_range(self, diamonds, price_column: str, budget: float):
        if price_column not in diamonds.columns:
            return diamonds

        close_to_budget = diamonds[
            diamonds[price_column] <= budget
        ].copy()

        if close_to_budget.empty:
            return diamonds.copy()

        preferred_85 = close_to_budget[
            close_to_budget[price_column] >= budget * 0.85
        ].copy()

        if not preferred_85.empty:
            return preferred_85

        preferred_80 = close_to_budget[
            close_to_budget[price_column] >= budget * 0.80
        ].copy()

        if not preferred_80.empty:
            return preferred_80

        return close_to_budget.copy()

    def _rank_diamonds1(self, diamonds, numeric_columns, budget, preference):
        diamonds = diamonds.copy()

        available_columns = [
            column for column in numeric_columns
            if column in diamonds.columns
        ]

        if len(available_columns) < 5:
            diamonds["final_score"] = 0
            diamonds["price_distance"] = (diamonds["price"] - budget).abs()
            return diamonds.sort_values(by=["price_distance"], ascending=True)

        diamonds[available_columns] = diamonds[available_columns].apply(
            lambda col: col.fillna(col.median())
        )

        scaler = MinMaxScaler()
        matrix = scaler.fit_transform(diamonds[available_columns])

        target = self._build_target_vector(
            diamonds=diamonds,
            columns=available_columns,
            price_column="price",
            carat_column="carat",
            budget=budget,
            preference=preference
        )

        cosine_scores = cosine_similarity(matrix, [target]).flatten()
        euclidean_distances = np.linalg.norm(matrix - target, axis=1)
        euclidean_scores = 1 / (1 + euclidean_distances)

        price_distance = (diamonds["price"] - budget).abs()
        price_scores = 1 / (1 + price_distance)

        diamonds["final_score"] = (
            0.45 * cosine_scores
            + 0.35 * euclidean_scores
            + 0.20 * price_scores
        )

        return diamonds.sort_values(by=["final_score"], ascending=False)

    def _rank_diamonds2(self, diamonds, numeric_columns, categorical_columns, budget, preference):
        diamonds = diamonds.copy()

        available_numeric = [
            column for column in numeric_columns
            if column in diamonds.columns
        ]

        if len(available_numeric) < 5:
            diamonds["final_score"] = 0
            diamonds["price_distance"] = (diamonds["Price"] - budget).abs()
            return diamonds.sort_values(by=["price_distance"], ascending=True)

        diamonds[available_numeric] = diamonds[available_numeric].apply(
            lambda col: col.fillna(col.median())
        )

        scaler = MinMaxScaler()
        numeric_matrix = scaler.fit_transform(diamonds[available_numeric])

        target = self._build_target_vector(
            diamonds=diamonds,
            columns=available_numeric,
            price_column="Price",
            carat_column="Carat",
            budget=budget,
            preference=preference
        )

        cosine_scores = cosine_similarity(numeric_matrix, [target]).flatten()

        jaccard_scores = self._calculate_jaccard_scores(
            diamonds=diamonds,
            categorical_columns=categorical_columns
        )

        price_distance = (diamonds["Price"] - budget).abs()
        price_scores = 1 / (1 + price_distance)

        diamonds["final_score"] = (
            0.45 * cosine_scores
            + 0.35 * jaccard_scores
            + 0.20 * price_scores
        )

        return diamonds.sort_values(by=["final_score"], ascending=False)

    def _build_target_vector(self, diamonds, columns, price_column, carat_column, budget, preference):
        target_row = diamonds.iloc[0].copy()

        closest_to_budget = diamonds.iloc[
            (diamonds[price_column] - budget).abs().argsort().iloc[0]
        ]

        target_row[columns] = closest_to_budget[columns]

        if price_column in columns:
            target_row[price_column] = budget

        if preference == "largest" and carat_column in columns:
            target_row[carat_column] = diamonds[carat_column].max()

        return target_row[columns].astype(float).values

    def _calculate_jaccard_scores(self, diamonds, categorical_columns):
        available_columns = [
            column for column in categorical_columns
            if column in diamonds.columns
        ]

        if len(available_columns) == 0:
            return np.zeros(len(diamonds))

        reference = diamonds.iloc[0][available_columns].astype(str).str.lower().to_dict()
        scores = []

        for _, row in diamonds.iterrows():
            row_values = row[available_columns].astype(str).str.lower().to_dict()

            matches = sum(
                1 for column in available_columns
                if row_values.get(column) == reference.get(column)
            )

            scores.append(matches / len(available_columns))

        return np.array(scores)