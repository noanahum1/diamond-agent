from app.services.recommendation_service import RecommendationService
from app.gemini_client import GeminiClient

class AgentService:
    def __init__(self):
        self.recommendation_service = RecommendationService()
        self.gemini = GeminiClient()
        self.sessions = {}

        self.currency_rates_to_usd = {
            "USD": 1,
            "ILS": 1 / 3.7,
            "NIS": 1 / 3.7,
            "EUR": 1.08,
            "GBP": 1.27,
        }

    def process_message(self, message, session_id=None):
        if not message or not message.strip():
            return {
                "answer": "אשמח לעזור 😊 אפשר לכתוב לי מה תרצי לדעת על יהלומים?",
                "intent": "empty_message"
            }

        message = message.strip()

        if session_id not in self.sessions:
            self.sessions[session_id] = self._create_empty_session()

        session = self.sessions[session_id]

        gemini_data = self.gemini.extract_user_intent(message, session)
        self._update_session_from_gemini(session, gemini_data)

        language = session.get("language") or "he"

        if gemini_data.get("needs_clarification"):
            return {
                "answer": gemini_data.get("clarification_question")
                or self._default_clarification_question(language),
                "intent": "clarification"
            }

        if not gemini_data.get("is_diamond_related", True):
            session["last_intent"] = "out_of_scope"
            return {
                "answer": self._out_of_scope_message(language),
                "intent": "out_of_scope"
            }

        intent = gemini_data.get("intent")

        if intent == "explanation":
            return self._handle_explanation(message, session)

        if intent in ["similarity", "comparison"]:
            return {
                "answer": (
                    "אני יכולה לעזור להשוות או למצוא יהלומים דומים לפי הפרמטרים שתבחרי 💎\n\n"
                    "כתבי לי את התקציב והמאפיינים החשובים לך, למשל צורה, קראט, צבע, ניקיון או חיתוך, "
                    "ואחזיר לך יהלומים שמתאימים כמה שיותר לבקשה.\n\n"
                    "איזה יהלום או אילו פרמטרים תרצי שאבדוק?"
                ),
                "intent": intent
            }

        budget = session.get("budget")
        currency = session.get("currency")

        if not budget:
            session["last_question"] = "budget"
            return {
                "answer": (
                    "אשמח לעזור לך לבחור יהלום 😊\n\n"
                    "מה התקציב המשוער שלך?"
                ),
                "intent": "missing_budget"
            }

        if not currency:
            session["last_question"] = "currency"
            return {
                "answer": self._missing_currency_message(language),
                "intent": "missing_currency"
            }

        budget_usd = self._convert_to_usd(budget, currency)

        if budget_usd is None:
            session["last_question"] = "currency"
            return {
                "answer": self._missing_currency_message(language),
                "intent": "missing_currency"
            }

        preference = session.get("preference") or "balanced"

        if self._requires_diamonds2(session):
            recommendations = self.recommendation_service.recommend_from_diamonds2(
                budget=budget_usd,
                preference=preference,
                shape=session.get("shape"),
                cut=session.get("cut"),
                color=session.get("color"),
                clarity=session.get("clarity"),
                carat=session.get("carat"),
                depth=session.get("depth"),
                table=session.get("table"),
                polish=session.get("polish"),
                symmetry=session.get("symmetry"),
                girdle=session.get("girdle"),
                diamond_type=session.get("diamond_type"),
                length_width_ratio=session.get("length_width_ratio")
            )
        else:
            recommendations = self.recommendation_service.recommend_by_budget(
                budget=budget_usd,
                preference=preference,
                cut=session.get("cut"),
                color=session.get("color"),
                clarity=session.get("clarity"),
                carat=session.get("carat"),
                depth=session.get("depth"),
                table=session.get("table")
            )

        if not recommendations:
            session["last_intent"] = "no_results"
            return {
                "answer": self._no_results_message(session, budget, currency),
                "intent": "no_results"
            }

        answer = self._format_recommendations(recommendations, budget, currency)

        session["last_intent"] = "recommendation"
        session["last_question"] = "additional_filters"

        return {
            "answer": answer,
            "intent": "recommendation"
        }

    def _create_empty_session(self):
        return {
            "budget": None,
            "currency": None,
            "shape": None,
            "cut": None,
            "color": None,
            "clarity": None,
            "carat": None,
            "depth": None,
            "table": None,
            "polish": None,
            "symmetry": None,
            "girdle": None,
            "diamond_type": None,
            "length_width_ratio": None,
            "preference": None,
            "topic": None,
            "language": "he",
            "last_question": None,
            "last_intent": None
        }

    def _update_session_from_gemini(self, session, gemini_data):
        fields = [
            "budget",
            "currency",
            "shape",
            "cut",
            "color",
            "clarity",
            "carat",
            "depth",
            "table",
            "polish",
            "symmetry",
            "girdle",
            "diamond_type",
            "length_width_ratio",
            "preference",
            "topic",
            "language"
        ]

        for field in fields:
            value = gemini_data.get(field)
            if value is not None:
                session[field] = value

    def _convert_to_usd(self, budget, currency):
        if not currency:
            return None

        currency = str(currency).upper()
        rate = self.currency_rates_to_usd.get(currency)

        if rate is None:
            return None

        return float(budget) * rate

    def _requires_diamonds2(self, session):
        diamonds2_only_fields = [
            "shape",
            "polish",
            "symmetry",
            "girdle",
            "diamond_type",
            "length_width_ratio"
        ]

        return any(session.get(field) for field in diamonds2_only_fields)

    def _format_recommendations(self, recommendations, original_budget, currency):
        answer = (
            f"מצאתי את היהלומים שמתאימים הכי קרוב לבקשה שלך, "
            f"בהתאם לתקציב של {float(original_budget):,.0f} {currency} 💎\n\n"
        )

        for i, diamond in enumerate(recommendations, start=1):
            if "Shape" in diamond:
                answer += (
                    f"{i}. צורה: {diamond.get('Shape')}\n"
                    f"   קראט: {diamond.get('Carat')}\n"
                    f"   חיתוך: {diamond.get('Cut')}\n"
                    f"   צבע: {diamond.get('Color')}\n"
                    f"   ניקיון: {diamond.get('Clarity')}\n"
                    f"   ליטוש: {diamond.get('Polish')}\n"
                    f"   סימטריה: {diamond.get('Symmetry')}\n"
                    f"   Girdle: {diamond.get('Girdle')}\n"
                    f"   סוג: {diamond.get('Type')}\n"
                    f"   מחיר: {diamond.get('Price')}$\n\n"
                )
            else:
                answer += (
                    f"{i}. קראט: {diamond.get('carat')}\n"
                    f"   חיתוך: {diamond.get('cut')}\n"
                    f"   צבע: {diamond.get('color')}\n"
                    f"   ניקיון: {diamond.get('clarity')}\n"
                    f"   עומק: {diamond.get('depth')}\n"
                    f"   Table: {diamond.get('table')}\n"
                    f"   מחיר: {diamond.get('price')}$\n\n"
                )

        answer += "רוצה שאדייק את ההמלצה לפי פרמטר נוסף כמו קראט, צבע, ניקיון, חיתוך או צורה?"

        return answer

    def _handle_explanation(self, message, session):
        language = session.get("language") or "he"
        topic = session.get("topic")

        answer = self.gemini.generate_diamond_explanation(
            user_message=message,
            topic=topic,
            language=language,
            session_context=session
        )

        if not answer:
            answer = (
                "אני יכולה להסביר על מאפיינים שונים של יהלומים כמו קראט, צבע, ניקיון, חיתוך, צורה, "
                "ליטוש, סימטריה ויחס אורך-רוחב 💎\n\n"
                "על איזה פרמטר תרצי שאסביר?"
            )

        session["last_intent"] = "explanation"
        return {
            "answer": answer,
            "intent": "explanation"
        }

    def _missing_currency_message(self, language):
        if language == "en":
            return (
                "The prices in the database are in USD 💎\n\n"
                "Which currency did you mean: dollar, shekel, euro, or pound?"
            )

        return (
            "המחירים במאגר הם בדולרים 💎\n\n"
            "באיזה מטבע התקציב שכתבת?\n"
            "אפשר לכתוב: דולר, שקל, יורו או פאונד."
        )

    def _default_clarification_question(self, language):
        if language == "en":
            return "I did not fully understand the request 😊 Could you rephrase it?"

        return "לא הצלחתי להבין לגמרי את הבקשה 😊 תוכלי לנסח אותה שוב?"

    def _out_of_scope_message(self, language):
        if language == "en":
            return (
                "It looks like your question is not related to diamonds 😊\n\n"
                "I specialize in choosing diamonds, comparing prices, and explaining parameters like carat, color, clarity, cut and shape.\n\n"
                "Would you like help choosing or understanding a diamond?"
            )

        return (
            "נראה שהשאלה שלך אינה קשורה לעולם היהלומים 😊\n\n"
            "אני מתמחה בבחירת יהלומים, השוואת מחירים, והבנת מאפיינים כמו קראט, צבע, ניקיון, חיתוך וצורה.\n\n"
            "תרצי שאעזור לך לבחור יהלום או להבין פרמטר מסוים?"
        )

    def _no_results_message(self, session, budget, currency):
        requirements = self._describe_requirements(session)

        return (
            "לא מצאתי יהלום שעומד בכל הדרישות שבחרת 💎\n\n"
            f"הדרישות שחיפשתי לפיהן הן: {requirements}, בתקציב של עד {budget:,.0f} {currency}.\n\n"
            "רוצה שאנסה לחפש לפי פחות מגבלות, למשל להתגמש בקראט, בצבע, בניקיון או בתקציב?"
        )

    def _describe_requirements(self, session):
        labels = {
            "shape": "צורה",
            "cut": "חיתוך",
            "color": "צבע",
            "clarity": "ניקיון",
            "carat": "קראט",
            "depth": "עומק",
            "table": "Table",
            "polish": "ליטוש",
            "symmetry": "סימטריה",
            "girdle": "Girdle",
            "diamond_type": "סוג",
            "length_width_ratio": "יחס אורך-רוחב"
        }

        parts = []

        for field, label in labels.items():
            value = session.get(field)
            if value is not None:
                parts.append(f"{label}: {value}")

        if not parts:
            return "תקציב בלבד"

        return ", ".join(parts)