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
        session["language"] = self._detect_message_language(message)

        fast_result = self._try_fast_message(message, session)
        if fast_result:
            return fast_result

        gemini_data = self.gemini.extract_user_intent(message, session)
        self._update_session_from_gemini(session, gemini_data)
        self._normalize_session_values(session)

        if session.get("requested_options_for"):
            return {
                "answer": self._build_available_options_response(
                    session["requested_options_for"],
                    session.get("language") or "he"
                ),
                "intent": "available_options"
            }

        validation_error = self._validate_session_against_dataset(session)

        if validation_error:
            return {
                "answer": self._build_validation_error_response(
                    validation_error,
                    session.get("language") or "he"
                ),
                "intent": "invalid_filter_value"
            }

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

        if intent == "conversation_end":
            session["last_intent"] = "conversation_end"
            return {
                "answer": (
                    "בשמחה 💎😊\n"
                    "אני כאן לכל שאלה נוספת על יהלומים, השוואות, מחירים או בחירת יהלום מתאים."
                ),
                "intent": "conversation_end"
            }

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

        return self._generate_recommendation_response(session)

    def _try_fast_message(self, message, session):
        normalized = message.lower().strip()

        end_messages = [
            "תודה", "תודה רבה", "תודה!", "תודה רבה!",
            "ביי", "בייי", "להתראות", "סיימתי",
            "זהו", "מעולה תודה", "אחלה תודה",
            "thanks", "thank you", "bye", "לא", "לא תודה", "לא, תודה", "no", "no thanks"
        ]

        if normalized in end_messages:
            session["last_intent"] = "conversation_end"
            return {
                "answer": (
                    "בשמחה 💎😊\n"
                    "אני כאן לכל שאלה נוספת על יהלומים, השוואות, מחירים או בחירת יהלום מתאים."
                ),
                "intent": "conversation_end"
            }

        start_messages = [
            "היי", "הי", "שלום", "אהלן",
            "אני רוצה יהלום", "רוצה יהלום",
            "מחפשת יהלום", "מחפש יהלום",
            "צריכה יהלום", "צריך יהלום"
        ]

        if normalized in start_messages:
            session["last_question"] = "budget"
            session["last_intent"] = "start_recommendation"
            return {
                "answer": (
                    "בשמחה 💎\n\n"
                    "מה התקציב המשוער שלך ובאיזה מטבע?\n"
                    "אפשר לכתוב למשל: 5,000 שקל או 1,500 דולר."
                ),
                "intent": "start_recommendation"
            }

        fast_data = None
        if session.get("last_question") == "currency":
            fast_data = self._extract_fast_budget_currency(message)

        if fast_data:
            if fast_data.get("budget") is not None:
                session["budget"] = fast_data["budget"]

            if fast_data.get("currency") is not None:
                session["currency"] = fast_data["currency"]

            self._normalize_session_values(session)

            if session.get("budget") and session.get("currency"):
                return self._generate_recommendation_response(session)

            if session.get("budget") and not session.get("currency"):
                session["last_question"] = "currency"
                return {
                    "answer": self._missing_currency_message(session.get("language") or "he"),
                    "intent": "missing_currency"
                }

        return None

    def _extract_fast_budget_currency(self, message):
        normalized = message.lower().replace(",", "").strip()

        currency = None

        if any(word in normalized for word in ["דולר", "דולרים", "usd", "dollar", "dollars"]):
            currency = "USD"
        elif any(word in normalized for word in ["שקל", "שקלים", "שח", 'ש"ח', "ils", "nis"]):
            currency = "ILS"
        elif any(word in normalized for word in ["יורו", "euro", "eur"]):
            currency = "EUR"
        elif any(word in normalized for word in ["פאונד", "pound", "gbp"]):
            currency = "GBP"

        numbers = re.findall(r"\d+(?:\.\d+)?", normalized)
        budget = float(numbers[0]) if numbers else None

        if budget is None and currency is None:
            return None

        return {
            "budget": budget,
            "currency": currency
        }

    def _generate_recommendation_response(self, session):
        language = session.get("language") or "he"
        budget = session.get("budget")
        currency = session.get("currency")

        if not budget:
            session["last_question"] = "budget"
            return {
                "answer": (
                    "I’d be happy to help you choose a diamond 😊\n\nWhat is your approximate budget?"
                    if language == "en"
                    else "אשמח לעזור לך לבחור יהלום 😊\n\nמה התקציב המשוער שלך?"
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

        session["last_intent"] = "recommendation"
        session["last_question"] = "additional_filters"

        return {
            "answer": self._format_recommendations(
                recommendations,
                budget,
                currency,
                session,
                language
            ),
            "intent": "recommendation"
        }

    def _create_empty_session(self):
        return {
            "budget": None,
            "currency": None,
            # shared / recommendation filters
            "shape": None,
            "cut": None,
            "color": None,
            "clarity": None,
            "carat": None,
            "depth": None,
            "table": None,
            "price": None,
            # diamonds2 specific
            "polish": None,
            "symmetry": None,
            "girdle": None,
            "diamond_type": None,
            "length_width_ratio": None,
            "length": None,
            "width": None,
            "height": None,
            # diamonds1 specific dimensions
            "x": None,
            "y": None,
            "z": None,
            # categories
            "carat_category": None,
            "price_category": None,
            # encoded columns - only for validation if Gemini extracts them
            "cut_encoded": None,
            "color_encoded": None,
            "clarity_encoded": None,
            "carat_category_encoded": None,
            "price_category_encoded": None,
            "polish_encoded": None,
            "symmetry_encoded": None,
            "girdle_encoded": None,
            # conversation state
            "requested_options_for": None,
            "preference": None,
            "topic": None,
            "language": "he",
            "last_question": None,
            "last_agent_message": None,
            "last_intent": None,
            "is_new_request": False
        }

    def _text(self, language, he, en):
        return en if language == "en" else he

    def _detect_message_language(self, message):
        normalized = message.strip()

        hebrew_chars = re.findall(r"[\u0590-\u05FF]", normalized)
        english_chars = re.findall(r"[A-Za-z]", normalized)

        if english_chars and not hebrew_chars:
            return "en"

        if hebrew_chars:
            return "he"

        return "he"

    def _clear_recommendation_filters(self, session):
        fields_to_clear = [
            "budget", "currency", "shape", "cut", "color", "clarity",
            "carat", "depth", "table", "price", "polish", "symmetry", "girdle",
            "diamond_type", "length_width_ratio", "length", "width", "height",
            "x", "y", "z", "carat_category", "price_category",
            "cut_encoded", "color_encoded", "clarity_encoded", "requested_options_for",
            "carat_category_encoded", "price_category_encoded",
            "polish_encoded", "symmetry_encoded", "girdle_encoded", "preference", "topic", "language"
        ]

        for field in fields_to_clear:
            session[field] = None

    def _update_session_from_gemini(self, session, gemini_data):
        if gemini_data.get("intent") == "recommendation" and gemini_data.get("is_new_request"):
            self._clear_recommendation_filters(session)
            session["is_new_request"] = True
        else:
            session["is_new_request"] = False
            
        fields = [
            "budget", "currency", "shape", "cut", "color", "clarity",
            "carat", "depth", "table", "price", "polish", "symmetry", "girdle",
            "diamond_type", "length_width_ratio", "length", "width", "height",
            "x", "y", "z", "carat_category", "price_category",
            "cut_encoded", "color_encoded", "clarity_encoded", "requested_options_for",
            "carat_category_encoded", "price_category_encoded",
            "polish_encoded", "symmetry_encoded", "girdle_encoded", "preference", "topic", "language"
        ]

        for field in fields:
            value = gemini_data.get(field)
            if value is not None:
                session[field] = value

    def _normalize_session_values(self, session):
        shape_mapping = {
            "עגול": "Round",
            "ראונד": "Round",
            "round": "Round",
            "oval": "Oval",
            "אובל": "Oval",
            "princess": "Princess",
            "פרינסס": "Princess",
            "cushion": "Cushion",
            "קושן": "Cushion",
            "קושיין": "Cushion",
            "emerald": "Emerald",
            "אמרלד": "Emerald",
        }

        if session.get("shape"):
            shape = str(session["shape"]).strip()
            session["shape"] = shape_mapping.get(shape.lower(), shape)

        if session.get("cut"):
            session["cut"] = str(session["cut"]).strip()

        if session.get("color"):
            session["color"] = str(session["color"]).strip().upper()

        if session.get("clarity"):
            session["clarity"] = str(session["clarity"]).strip().upper()

        if session.get("currency"):
            session["currency"] = str(session["currency"]).strip().upper()

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
            "shape", "polish", "symmetry", "girdle",
            "diamond_type", "length_width_ratio"
        ]

        return any(session.get(field) for field in diamonds2_only_fields)

    def _get_dataset_validation_rules(self, session):
        return {
            "categorical": {
                "shape": ["Cushion", "Cushion Modified", "Heart", "Princess", "Radiant", "Round"],
                "cut": ["Fair", "Good", "Ideal", "Premium", "Very Good", "Astor", "Excellent"],
                "color": ["D", "E", "F", "G", "H", "I", "J"],
                "clarity": ["I1", "IF", "SI1", "SI2", "VS1", "VS2", "VVS1", "VVS2", "FL"],
                "polish": ["Excellent", "Good", "Very Good"],
                "symmetry": ["Excellent", "Good", "Very Good"],
                "girdle": [
                    "Medium", "Medium to Slightly Thick", "Medium to Thick", "Medium to Very Thick",
                    "Slightly Thick", "Slightly Thick to Thick", "Slightly Thick to Very Thick",
                    "Thick", "Thick to Very Thick", "Thin", "Thin to Medium",
                    "Thin to Slightly Thick", "Thin to Thick", "Thin to Very Thick",
                    "Very Thick", "Very Thin to Slightly Thick", "Very Thin to Thick",
                    "Very Thin to Very Thick"
                ],
                "diamond_type": ["GIA", "GIA Lab-Grown", "IGI Lab-Grown"],
                "carat_category": [
                    "extra extra small", "extra large", "extra small", "large",
                    "medium", "small", "ultra large (3+)"
                ],
                "price_category": ["high", "low", "medium", "very high", "very low"],
            },
            "ranges": {
                "carat": {"min": 0.2, "max": 5.01},
                "depth": {"min": 43.0, "max": 79.0},
                "table": {"min": 43.0, "max": 95.0},
                "price": {"min": 326, "max": 18823},
                "length_width_ratio": {"min": 1.0, "max": 1.38},
                "length": {"min": 5.18, "max": 9.63},
                "width": {"min": 3.68, "max": 58.9},
                "height": {"min": 1.07, "max": 31.8},
                "x": {"min": 3.73, "max": 10.74},
                "y": {"min": 3.68, "max": 58.9},
                "z": {"min": 1.07, "max": 31.8},
            }
        }

    def _validate_session_against_dataset(self, session):
        rules = self._get_dataset_validation_rules(session)

        for field, allowed_values in rules["categorical"].items():
            value = session.get(field)

            if value is None:
                continue

            allowed_lower = [str(v).lower().strip() for v in allowed_values]

            if str(value).lower().strip() not in allowed_lower:
                return {
                    "type": "categorical",
                    "parameter": field,
                    "value": value
                }

        for field, range_rule in rules["ranges"].items():
            value = session.get(field)

            if value is None:
                continue

            try:
                numeric_value = float(value)
            except (TypeError, ValueError):
                return {
                    "type": "range",
                    "parameter": field,
                    "value": value,
                    "min": range_rule["min"],
                    "max": range_rule["max"]
                }

            if numeric_value < range_rule["min"] or numeric_value > range_rule["max"]:
                return {
                    "type": "range",
                    "parameter": field,
                    "value": value,
                    "min": range_rule["min"],
                    "max": range_rule["max"]
                }

        return None

    def _build_validation_error_response(self, error, language):
        parameter = error["parameter"]
        value = error["value"]

        if error["type"] == "range":
            if language == "en":
                return (
                    f'The value "{value}" for "{parameter}" is not available in our current database.\n'
                    f'The available range is between {error["min"]} and {error["max"]}.\n'
                    f"Please choose a value within this range."
                )

            return (
                f'הערך "{value}" עבור הפרמטר "{parameter}" לא קיים במאגר המידע הנוכחי שלנו.\n'
                f'הטווח הקיים הוא בין {error["min"]} ל־{error["max"]}.\n'
                f"אנא בחר ערך בטווח הזה."
            )

        if language == "en":
            return (
                f'The value "{value}" for "{parameter}" does not exist in our current database.\n'
                f"Please choose another value."
            )

        return (
            f'הערך "{value}" עבור הפרמטר "{parameter}" לא קיים במאגר המידע הנוכחי שלנו.\n'
            f"אנא בחר ערך אחר."
        )

    def _build_available_options_response(self, parameter, language):
        rules = self._get_dataset_validation_rules({})
        parameter_key = str(parameter).lower().strip()

        aliases = {
            "shape": "shape",
            "צורה": "shape",
            "cut": "cut",
            "חיתוך": "cut",
            "color": "color",
            "צבע": "color",
            "clarity": "clarity",
            "ניקיון": "clarity",
            "polish": "polish",
            "symmetry": "symmetry",
            "girdle": "girdle",
            "type": "diamond_type",
            "diamond_type": "diamond_type",
            "carat": "carat",
            "קראט": "carat",
            "depth": "depth",
            "עומק": "depth",
            "table": "table",
            "x": "x",
            "y": "y",
            "z": "z",
            "length": "length",
            "width": "width",
            "height": "height",
            "price": "price",
        }

        field = aliases.get(parameter_key, parameter_key)

        if field in rules["categorical"]:
            values = ", ".join(rules["categorical"][field])

            if language == "en":
                return f'The available values for "{field}" are:\n{values}'

            return f'הערכים הקיימים עבור "{field}" הם:\n{values}'

        if field in rules["ranges"]:
            range_rule = rules["ranges"][field]

            if language == "en":
                return (
                    f'The available range for "{field}" is '
                    f'between {range_rule["min"]} and {range_rule["max"]}.'
                )

            return (
                f'הטווח הקיים עבור "{field}" הוא '
                f'בין {range_rule["min"]} ל־{range_rule["max"]}.'
            )

        if language == "en":
            return f'I could not find available values for "{parameter}".'

        return f'לא מצאתי ערכים זמינים עבור "{parameter}".'

    def _format_recommendations(self, recommendations, original_budget, currency, session, language):
        if language == "en":
            return self._format_recommendations_en(
                recommendations,
                original_budget,
                currency,
                session
            )
        answer = (
            f"מצאתי את היהלומים שמתאימים הכי קרוב לבקשה שלך, "
            f"בהתאם לתקציב של {float(original_budget):,.0f} {currency} 💎\n\n"
        )

        requested_extra_fields = {
            "shape": session.get("shape"),
            "depth": session.get("depth"),
            "table": session.get("table"),
            "polish": session.get("polish"),
            "symmetry": session.get("symmetry"),
            "girdle": session.get("girdle"),
            "diamond_type": session.get("diamond_type"),
            "length_width_ratio": session.get("length_width_ratio"),
        }

        for i, diamond in enumerate(recommendations, start=1):
            if "Shape" in diamond:
                if requested_extra_fields["shape"]:
                    answer += f"{i}. צורה: {diamond.get('Shape')}\n"
                else:
                    answer += f"{i}.\n"

                answer += (
                    f"   קראט: {diamond.get('Carat')}\n"
                    f"   חיתוך: {diamond.get('Cut')}\n"
                    f"   צבע: {diamond.get('Color')}\n"
                    f"   ניקיון: {diamond.get('Clarity')}\n"
                )

                if requested_extra_fields["polish"]:
                    answer += f"   ליטוש: {diamond.get('Polish')}\n"

                if requested_extra_fields["symmetry"]:
                    answer += f"   סימטריה: {diamond.get('Symmetry')}\n"

                if requested_extra_fields["girdle"]:
                    answer += f"   Girdle: {diamond.get('Girdle')}\n"

                if requested_extra_fields["diamond_type"]:
                    answer += f"   סוג: {diamond.get('Type')}\n"

                if requested_extra_fields["depth"]:
                    answer += f"   עומק: {diamond.get('Depth %')}\n"

                if requested_extra_fields["table"]:
                    answer += f"   Table: {diamond.get('Table %')}\n"

                if requested_extra_fields["length_width_ratio"]:
                    answer += f"   יחס אורך-רוחב: {diamond.get('Length/Width Ratio')}\n"

                answer += f"   מחיר: {diamond.get('Price')}$\n\n"

            else:
                answer += (
                    f"{i}.\n"
                    f"   קראט: {diamond.get('carat')}\n"
                    f"   חיתוך: {diamond.get('cut')}\n"
                    f"   צבע: {diamond.get('color')}\n"
                    f"   ניקיון: {diamond.get('clarity')}\n"
                )

                if requested_extra_fields["depth"]:
                    answer += f"   עומק: {diamond.get('depth')}\n"

                if requested_extra_fields["table"]:
                    answer += f"   Table: {diamond.get('table')}\n"

                answer += f"   מחיר: {diamond.get('price')}$\n\n"

        answer += "\n\n💎 רוצה שאדייק את ההמלצה לפי פרמטר נוסף? ☺️✨"
        return answer

    def _format_recommendations_en(self, recommendations, original_budget, currency, session):
        answer = (
            f"I found the diamonds that best match your request "
            f"within a budget of {float(original_budget):,.0f} {currency} 💎\n\n"
        )

        for i, diamond in enumerate(recommendations, start=1):
            if "Shape" in diamond:
                answer += (
                    f"{i}.\n"
                    f"   Shape: {diamond.get('Shape')}\n"
                    f"   Carat: {diamond.get('Carat')}\n"
                    f"   Cut: {diamond.get('Cut')}\n"
                    f"   Color: {diamond.get('Color')}\n"
                    f"   Clarity: {diamond.get('Clarity')}\n"
                    f"   Polish: {diamond.get('Polish')}\n"
                    f"   Symmetry: {diamond.get('Symmetry')}\n"
                    f"   Girdle: {diamond.get('Girdle')}\n"
                    f"   Type: {diamond.get('Type')}\n"
                    f"   Price: {diamond.get('Price')}$\n\n"
                )
            else:
                answer += (
                    f"{i}.\n"
                    f"   Carat: {diamond.get('carat')}\n"
                    f"   Cut: {diamond.get('cut')}\n"
                    f"   Color: {diamond.get('color')}\n"
                    f"   Clarity: {diamond.get('clarity')}\n"
                    f"   Price: {diamond.get('price')}$\n\n"
                )

        answer += "Would you like me to refine the recommendation by another parameter? 💎"
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
        session["last_agent_message"] = answer

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
        language = session.get("language") or "he"
        requirements = self._describe_requirements(session, language)

        if language == "en":
            return (
                "I couldn't find a diamond that matches all the requirements you selected 💎\n\n"
                f"The requirements I searched by are: {requirements}, with a budget of up to {budget:,.0f} {currency}.\n\n"
                "Would you like me to search with fewer restrictions, for example by being more flexible with carat, color, clarity, or budget?"
            )

        return (
            "לא מצאתי יהלום שעומד בכל הדרישות שבחרת 💎\n\n"
            f"הדרישות שחיפשתי לפיהן הן: {requirements}, בתקציב של עד {budget:,.0f} {currency}.\n\n"
            "רוצה שאנסה לחפש לפי פחות מגבלות, למשל להתגמש בקראט, בצבע, בניקיון או בתקציב?"
        )

    def _describe_requirements(self, session, language="he"):
        if language == "en":
            labels = {
                "shape": "Shape",
                "cut": "Cut",
                "color": "Color",
                "clarity": "Clarity",
                "carat": "Carat",
                "depth": "Depth",
                "table": "Table",
                "polish": "Polish",
                "symmetry": "Symmetry",
                "girdle": "Girdle",
                "diamond_type": "Type",
                "length_width_ratio": "Length/Width ratio"
            }
        else:
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
            return "budget only" if language == "en" else "תקציב בלבד"

        return ", ".join(parts)

    def _get_dataset_rules(self, session):
        if self._requires_diamonds2(session):
            return {
                "categorical": {
                    "shape": ["Cushion", "Cushion Modified", "Heart", "Princess", "Radiant", "Round"],
                    "cut": ["Astor", "Excellent", "Ideal", "Very Good"],
                    "color": ["D", "E", "F", "G", "H"],
                    "clarity": ["FL", "IF", "VS1", "VS2", "VVS1", "VVS2"],
                    "diamond_type": ["GIA", "GIA Lab-Grown", "IGI Lab-Grown"],
                    "polish": ["Excellent", "Good", "Very Good"],
                    "symmetry": ["Excellent", "Good", "Very Good"],
                    "girdle": [
                        "Medium", "Medium to Slightly Thick", "Medium to Thick", "Medium to Very Thick",
                        "Slightly Thick", "Slightly Thick to Thick", "Slightly Thick to Very Thick",
                        "Thick", "Thick to Very Thick", "Thin", "Thin to Medium",
                        "Thin to Slightly Thick", "Thin to Thick", "Thin to Very Thick",
                        "Very Thick", "Very Thin to Slightly Thick", "Very Thin to Thick",
                        "Very Thin to Very Thick"
                    ],
                },
                "ranges": {
                    "carat": {"min": 1.0, "max": 4.03}
                }
            }

        return {
            "categorical": {
                "cut": ["Fair", "Good", "Ideal", "Premium", "Very Good"],
                "color": ["D", "E", "F", "G", "H", "I", "J"],
                "clarity": ["I1", "IF", "SI1", "SI2", "VS1", "VS2", "VVS1", "VVS2"],
            },
            "ranges": {
                "carat": {"min": 0.2, "max": 5.01}
            }
        }

    def _validate_session_against_dataset(self, session):
        rules = self._get_dataset_rules(session)

        for field, allowed_values in rules["categorical"].items():
            value = session.get(field)

            if value is None:
                continue

            allowed_lower = [str(v).lower().strip() for v in allowed_values]

            if str(value).lower().strip() not in allowed_lower:
                return {
                    "type": "categorical",
                    "parameter": field,
                    "value": value
                }

        for field, range_rule in rules["ranges"].items():
            value = session.get(field)

            if value is None:
                continue

            try:
                numeric_value = float(value)
            except (TypeError, ValueError):
                return {
                    "type": "range",
                    "parameter": field,
                    "value": value,
                    "min": range_rule["min"],
                    "max": range_rule["max"]
                }

            if numeric_value < range_rule["min"] or numeric_value > range_rule["max"]:
                return {
                    "type": "range",
                    "parameter": field,
                    "value": value,
                    "min": range_rule["min"],
                    "max": range_rule["max"]
                }

        return None

    def _build_validation_error_response(self, error, language):
        if error["type"] == "range":
            if language == "en":
                return (
                    f'The value "{error["value"]}" for "{error["parameter"]}" is not available in our current database.\n'
                    f'The available range is between {error["min"]} and {error["max"]}.\n'
                    f"Please choose a value within this range."
                )

            return (
                f'הערך "{error["value"]}" עבור הפרמטר "{error["parameter"]}" לא קיים במאגר המידע הנוכחי שלנו.\n'
                f'הטווח הקיים הוא בין {error["min"]} ל־{error["max"]}.\n'
                f"אנא בחר ערך בטווח הזה."
            )

        if language == "en":
            return (
                f'The value "{error["value"]}" for "{error["parameter"]}" does not exist in our current database.\n'
                f"Please choose another value."
            )

        return (
            f'הערך "{error["value"]}" עבור הפרמטר "{error["parameter"]}" לא קיים במאגר המידע הנוכחי שלנו.\n'
            f"אנא בחר ערך אחר."
        )