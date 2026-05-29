import re
from app.services.recommendation_service import RecommendationService

class AgentService:
    def __init__(self):
        self.recommendation_service = RecommendationService()
        self.sessions = {}

    def process_message(self, message, session_id=None):
        if not message or not message.strip():
            return {
                "answer": "אשמח לעזור 😊 אפשר לכתוב לי מה תרצי לדעת על יהלומים?",
                "intent": "empty_message"
            }

        message = message.strip()

        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "budget": None,
                "preference": None,
                "shape": None,
                "use_diamonds2": False,
                "last_intent": None
            }

        session = self.sessions[session_id]

        extracted_budget = self.extract_budget(message)
        extracted_preference = self.extract_preference(message)
        extracted_shape = self.extract_shape(message)

        is_followup_budget = (
            extracted_budget is not None
            and session.get("last_intent") == "missing_budget"
        )

        if not is_followup_budget and not self.is_diamond_related(message):
            return {
                "answer": (
                    "נראה שהשאלה שלך לא קשורה לעולם היהלומים 😊\n\n"
                    "אני כאן כדי לעזור בבחירת יהלומים, השוואת מחירים, הבנת מאפיינים כמו קראט, צבע, ניקיון וחיתוך, "
                    "ומציאת יהלום שמתאים לתקציב שלך.\n\n"
                    "אפשר לכתוב לי למשל: אני מחפשת יהלום בתקציב של 5,000 דולר."
                ),
                "intent": "out_of_scope"
            }

        if extracted_budget:
            session["budget"] = extracted_budget

        if extracted_preference:
            session["preference"] = extracted_preference

        if extracted_shape:
            session["shape"] = extracted_shape

        if self.should_use_diamonds2(message):
            session["use_diamonds2"] = True

        budget = session.get("budget")
        preference = session.get("preference") or "balanced"
        shape = session.get("shape")
        use_diamonds2 = session.get("use_diamonds2")

        if not budget:
            session["last_intent"] = "missing_budget"

            return {
                "answer": (
                    "אשמח לעזור לך לבחור יהלום 😊\n\n"
                    "כדי שאוכל לתת המלצה מדויקת מתוך הדאטה, תוכלי לכתוב לי מה התקציב המשוער שלך?"
                ),
                "intent": "missing_budget"
            }

        if use_diamonds2:
            recommendations = self.recommendation_service.recommend_from_diamonds2(
                budget=budget,
                preference=preference,
                shape=shape
            )

            if not recommendations:
                return {
                    "answer": (
                        f"לא מצאתי יהלומים מתאימים בתקציב של עד {budget:,.0f} דולר במאגר הנתונים המפורט.\n\n"
                        "אפשר לנסות תקציב גבוה יותר או לשנות מעט את הדרישות."
                    ),
                    "intent": "diamonds2_recommendation"
                }

            answer = f"מצאתי כמה יהלומים מתאימים מתוך מאגר הנתונים המפורט, בתקציב של עד {budget:,.0f} דולר:\n\n"

            for i, diamond in enumerate(recommendations, start=1):
                answer += (
                    f"{i}. צורה: {diamond['Shape']}\n"
                    f"   קראט: {diamond['Carat Weight']}\n"
                    f"   חיתוך: {diamond['Cut']}\n"
                    f"   צבע: {diamond['Color']}\n"
                    f"   ניקיון: {diamond['Clarity']}\n"
                    f"   Polish: {diamond['Polish']}\n"
                    f"   Symmetry: {diamond['Symmetry']}\n"
                    f"   Girdle: {diamond['Girdle']}\n"
                    f"   Type: {diamond['Type']}\n"
                    f"   מחיר: {diamond['Price']}$\n\n"
                )

            session["last_intent"] = "diamonds2_recommendation"

            return {
                "answer": answer,
                "intent": "diamonds2_recommendation"
            }

        recommendations = self.recommendation_service.recommend_by_budget(
            budget,
            preference
        )

        if not recommendations:
            session["last_intent"] = "budget_recommendation"

            return {
                "answer": (
                    f"לא מצאתי יהלומים בתקציב של עד {budget:,.0f} דולר במאגר הנתונים.\n\n"
                    "אפשר לנסות תקציב מעט גבוה יותר או לשנות את הדרישות."
                ),
                "intent": "budget_recommendation"
            }

        answer = f"מצאתי כמה יהלומים שמתאימים לתקציב של עד {budget:,.0f} דולר:\n\n"

        for i, diamond in enumerate(recommendations, start=1):
            answer += (
                f"{i}. קראט: {diamond['carat']}\n"
                f"   חיתוך: {diamond['cut']}\n"
                f"   צבע: {diamond['color']}\n"
                f"   ניקיון: {diamond['clarity']}\n"
                f"   מחיר: {diamond['price']}$\n\n"
            )

        session["last_intent"] = "budget_recommendation"

        return {
            "answer": answer,
            "intent": "budget_recommendation"
        }

    def extract_budget(self, message):
        clean_message = message.replace(",", "")
        numbers = re.findall(r"\d+", clean_message)

        if not numbers:
            return None

        return float(max(numbers, key=lambda x: float(x)))

    def extract_preference(self, message):
        lower_message = message.lower()

        if any(word in lower_message for word in ["גדול", "גדולה", "קראט", "carat"]):
            return "largest"

        if any(word in lower_message for word in ["איכותי", "איכות", "ניקיון", "נקיון", "צבע", "חיתוך", "clarity", "color", "cut"]):
            return "quality"

        if any(word in lower_message for word in ["משתלם", "תמורה", "value", "שווה", "כדאי"]):
            return "value"

        return None

    def extract_shape(self, message):
        lower_message = message.lower()

        shapes = [
            "round", "oval", "princess", "emerald",
            "pear", "marquise", "cushion", "radiant",
            "heart", "asscher"
        ]

        for shape in shapes:
            if shape in lower_message:
                return shape

        return None

    def is_diamond_related(self, message):
        lower_message = message.lower()

        non_diamond_keywords = [
            "מתכון", "בראוניז", "עוגה", "קינוח", "אוכל", "בישול", "אפייה",
            "מסעדה", "מלון", "טיסה", "דירה", "פריז", "טיול"
        ]

        if any(keyword in lower_message for keyword in non_diamond_keywords):
            return False

        diamond_keywords = [
            "יהלום", "יהלומים", "טבעת", "אירוסין",
            "קראט", "קרט", "carat",
            "cut", "חיתוך",
            "color", "צבע",
            "clarity", "ניקיון", "נקיון",
            "price", "מחיר", "תקציב",
            "polish", "symmetry", "shape",
            "girdle", "fluorescence",
            "round", "oval", "princess", "emerald",
            "pear", "marquise", "cushion", "radiant",
            "heart", "asscher"
        ]

        return any(keyword.lower() in lower_message for keyword in diamond_keywords)

    def should_use_diamonds2(self, message):
        lower_message = message.lower()

        diamonds2_keywords = [
            "shape", "צורה", "round", "oval", "princess", "emerald",
            "pear", "marquise", "cushion", "radiant", "heart", "asscher",
            "polish", "symmetry", "girdle", "fluorescence",
            "ליטוש", "סימטריה", "פלורסנס", "תעודה", "type"
        ]

        return any(keyword in lower_message for keyword in diamonds2_keywords)