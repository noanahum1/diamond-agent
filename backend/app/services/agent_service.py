import re
from app.services.recommendation_service import RecommendationService
from app.gemini_client import GeminiClient

class AgentService:
    def __init__(self):
        self.recommendation_service = RecommendationService()
        self.gemini = GeminiClient()
        self.sessions = {}

        self.currency_rates_to_usd = {
            "USD": 1,
            "ILS": 1 / 2.81,
            "NIS": 1 / 2.81,
            "EUR": 1 / 3.28,
            "GBP": 1 / 3.79,
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

        if gemini_data.get("needs_clarification"):
            return {
                "answer": gemini_data.get("clarification_question")
                or "לא הצלחתי להבין לגמרי את הבקשה 😊 תוכלי לנסח אותה שוב?",
                "intent": "clarification"
            }

        if not gemini_data.get("is_diamond_related", True):
            session["last_intent"] = "out_of_scope"
            return {
                "answer": (
                    "נראה שהשאלה שלך אינה קשורה לעולם היהלומים 😊\n\n"
                    "אני מתמחה בבחירת יהלומים, השוואת מחירים, הבנת מאפיינים כמו קראט, צבע, ניקיון וחיתוך, "
                    "ואשמח לעזור בכל שאלה בתחום הזה."
                ),
                "intent": "out_of_scope"
            }

        self._update_session_from_gemini(session, gemini_data)

        intent = gemini_data.get("intent")

        if intent == "explanation":
            return self._handle_explanation(session)

        if intent in ["similarity", "comparison"]:
            return {
                "answer": (
                    "אני יכולה לעזור בזה 💎\n\n"
                    "בשלב הבא נוסיף מנגנון השוואה ודמיון בין יהלומים לפי מאפיינים כמו קראט, צבע, ניקיון, חיתוך וצורה."
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
                "answer": (
                    "המחירים במאגר הם בדולרים 💎\n\n"
                    "באיזה מטבע התקציב שכתבת?\n"
                    "אפשר לכתוב: דולר, שקל, יורו או פאונד."
                ),
                "intent": "missing_currency"
            }

        budget_usd = self._convert_to_usd(budget, currency)

        if budget_usd is None:
            session["last_question"] = "currency"
            return {
                "answer": (
                    "לא הצלחתי לזהות את המטבע 😊\n\n"
                    "אפשר לכתוב אחד מהבאים: דולר, שקל, יורו או פאונד."
                ),
                "intent": "missing_currency"
            }

        shape = session.get("shape")
        preference = session.get("preference") or "balanced"

        if self._requires_diamonds2(session):
            recommendations = self.recommendation_service.recommend_from_diamonds2(
                budget=budget_usd,
                preference=preference,
                shape=session.get("shape"),
                cut=session.get("cut"),
                color=session.get("color"),
                clarity=session.get("clarity"),
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
                clarity=session.get("clarity")
            )

        if not recommendations:
            session["last_intent"] = "no_results"
            return {
                "answer": (
                    "לא מצאתי יהלום שעומד בדיוק בכל הדרישות שבחרת 💎\n\n"
                    "אפשר לנסות לשנות אחד מהפרמטרים, למשל להגדיל מעט את התקציב, לבחור צבע אחר, "
                    "להתגמש ברמת הניקיון או לבחור צורה נוספת.\n\n"
                    "רוצה שאנסה לחפש לפי פחות מגבלות?"
                ),
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
            "polish": None,
            "symmetry": None,
            "preference": None,
            "topic": None,
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
            "polish",
            "symmetry",
            "preference",
            "topic"
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
            "symmetry"
            "girdle",
            "diamond_type",
            "length_width_ratio"
        ]

        return any(session.get(field) for field in diamonds2_only_fields)

    def _format_recommendations(self, recommendations, original_budget, currency):
        answer = (
            f"מצאתי 5 יהלומים שמתאימים הכי קרוב לבקשה שלך, "
            f"בהתאם לתקציב של {original_budget:,.0f} {currency} 💎\n\n"
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
                    f"   מחיר: {diamond.get('Price')}$\n\n"
                )
            else:
                answer += (
                    f"{i}. קראט: {diamond.get('carat')}\n"
                    f"   חיתוך: {diamond.get('cut')}\n"
                    f"   צבע: {diamond.get('color')}\n"
                    f"   ניקיון: {diamond.get('clarity')}\n"
                    f"   מחיר: {diamond.get('price')}$\n\n"
                )

        answer += (
            "רוצה שאדייק את ההמלצה לפי פרמטר נוסף כמו צבע, ניקיון, חיתוך או צורה?"
        )

        return answer

    def _handle_explanation(self, session):
        topic = session.get("topic")

        explanations = {
            "carat": "קראט הוא מדד למשקל היהלום. בדרך כלל ככל שהקראט גבוה יותר, היהלום גדול ויקר יותר 💎",
            "cut": "חיתוך מתאר את איכות החיתוך של היהלום, והוא משפיע מאוד על הברק והניצוץ שלו.",
            "color": "צבע היהלום מתאר עד כמה היהלום חסר צבע. לרוב, ככל שהיהלום קרוב יותר לחסר צבע, הוא נחשב איכותי יותר.",
            "clarity": "ניקיון מתאר את כמות הפגמים הפנימיים או החיצוניים ביהלום. ככל שיש פחות פגמים, רמת הניקיון גבוהה יותר.",
            "shape": "צורה מתארת את המבנה החיצוני של היהלום, למשל Round, Oval, Cushion או Princess.",
            "polish": "Polish מתאר את איכות הגימור והליטוש של פני היהלום.",
            "symmetry": "Symmetry מתארת עד כמה חלקי היהלום סימטריים ומדויקים ביחס אחד לשני.",
            "fluorescence": "Fluorescence מתארת תגובה של היהלום לאור אולטרה־סגול. בחלק מהמקרים זה יכול להשפיע על המראה והמחיר.",
            "girdle": "Girdle הוא החלק ההיקפי שמפריד בין החלק העליון והתחתון של היהלום."
        }

        answer = explanations.get(
            topic,
            "אני יכולה להסביר על מאפיינים כמו קראט, צבע, ניקיון, חיתוך, צורה, ליטוש וסימטריה 💎\nעל איזה פרמטר תרצי הסבר?"
        )

        return {
            "answer": answer,
            "intent": "explanation"
        }