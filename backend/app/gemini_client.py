import os
import json
import re
from dotenv import load_dotenv
from google import genai
from google.genai import errors

dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path)

class GeminiClient:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            self.is_available = False
            self.client = None
            self.model = None
            return

        self.is_available = True
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-3.1-flash-lite"

    def generate_text(self, prompt: str) -> str | None:
        if not self.is_available:
            return None

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )

            if not response or not response.text:
                return None

            return response.text.strip()

        except errors.ClientError as error:
            print(f"Gemini client error: {error}")
            return None

        except errors.ServerError as error:
            print(f"Gemini server error: {error}")
            return None

        except Exception as error:
            print(f"Unexpected Gemini error: {error}")
            return None

    def extract_user_intent(self, user_message: str, session_context: dict | None = None) -> dict:
        session_context = session_context or {}

        active_context = {
            key: value
            for key, value in session_context.items()
            if value is not None
        }

        prompt = f"""
    You are the NLU layer of a Diamond Advisor Agent.

    Task:
    Return ONLY valid JSON. No explanations.

    Understand Hebrew, English, transliteration, spelling mistakes, and partial answers.
    Extract diamond intent and parameters.
    Keep existing context unless the user explicitly provides a new value.
    If the user provides a new value for an existing field, the new value must override the previous value.
    Do not keep old values from explanation topics as recommendation filters unless the user clearly asks to use them.
    The conversation is continuous.
    The user may switch between Hebrew and English during the same session.
    Keep the context, filters and previous intent when relevant, but update the response language according to the current user message.
    Decide whether the user is starting a new independent diamond request or continuing the current one.
    If the user starts a separate search for another/different/new diamond, return "is_new_request": true.
    If the user only adds, updates, or refines filters in the current search, return "is_new_request": false.
    If the user gives a short reply such as confirmation, rejection,
    agreement, or a partial answer, interpret it according to the previous
    agent message and session context.

    Examples:
    Agent: Would you like to know how cut affects price?
    User: Sure
    => continue explaining cut impact, do not start a new recommendation flow.

    Agent: Which currency?
    User: Euro
    => update currency only.
    Normalize extracted values to dataset-style English values.
    Do not expose internal field names to the user.

    Context:
    {json.dumps(active_context, ensure_ascii=False)}

    User:
    {user_message}

    Return exactly:
    {{
    "intent": "recommendation",
    "is_diamond_related": true,
    "language": "he",
    "budget": null,
    "currency": null,
    "shape": null,
    "cut": null,
    "color": null,
    "clarity": null,
    "carat": null,
    "depth": null,
    "table": null,
    "polish": null,
    "symmetry": null,
    "girdle": null,
    "diamond_type": null,
    "length_width_ratio": null,
    "preference": null,
    "topic": null,
    "needs_clarification": false,
    "is_new_request": false,
    "clarification_question": null
    }}

    Allowed intents:
    recommendation, explanation, comparison, similarity, out_of_scope, clarification, conversation_end
    Rules:
    - Hebrew input -> language "he"; English input -> "en".
    Always detect the language of the current user message.
    The "language" field must reflect the language of the current message, not necessarily the previous session language.
    If the user switches language during the conversation, keep the existing diamond context but answer in the new language.
    - Clarification questions must be in the same language as the user.
    - Non-diamond topic -> is_diamond_related false, intent out_of_scope.
    - Explanation question -> intent explanation and fill topic.
    - Recommendation/search/choose/find diamond -> intent recommendation.
    - If the user asks about shapes, cuts, clarity, color, carat, polish, symmetry, girdle, fluorescence, depth, table or any other diamond parameter, it is diamond-related.
    - If user writes only a number and context last_question is budget -> budget.
    - If user writes only currency and budget exists -> currency.
    - Currency normalization: dollar/usd/דולר -> USD, shekel/ils/nis/שקל/שח/ש"ח -> ILS, euro/eur/יורו -> EUR, pound/gbp/פאונד -> GBP.
    - Return diamond values in English dataset format only, not Hebrew.
    - Examples: עגול/ראונד/round -> Round, אובל/oval -> Oval, אמרלד/emerald -> Emerald, קושן/cushion -> Cushion, פרינסס/princess -> Princess.
    - Color: D/E/F/G/H/I/J etc.
    - Clarity: IF, VVS1, VVS2, VS1, VS2, SI1, SI2 etc.
    - Carat examples: 4 קראט, 4ct, 4 carat -> 4.
    - 2 קראט -> carat: 2, budget: null, currency: null
    - If the agent previously asked whether the user needs anything else, and the user answers negatively such as "לא", "לא תודה", "no", "no thanks", understand that the conversation is ending.
    - In that case return intent: "conversation_end", is_diamond_related: true, needs_clarification: false.
    - Explicit user values always override previous context values.
    - If is_new_request is true, return only the values from the new request and do not reuse old recommendation filters from context.
    - If is_new_request is false, keep the previous context and update only explicitly provided values.
    - If the previous topic was an explanation, do not use explained values as recommendation filters unless the user repeats them in the recommendation request.
    - Example:
    Context: topic = "Fair cut", last_intent = "explanation"
    User: "אני מחפשת יהלום שהוא חיתוך ideal ועולה עד 3000 דולר"
    => intent: "recommendation", cut: "Ideal", budget: 3000, currency: "USD"
    - Never return cut: "Fair" in this case.
    Important numeric extraction rules:
    - Never assume that a standalone number is a budget.
    - A number followed by carat, ct, קראט, קרט means diamond carat only.
    - A number followed by $, dollar, usd, דולר means budget in USD.
    - A number followed by שקל, שח, ש"ח, nis, ils means budget in ILS.
    - A number followed by euro, eur, יורו means budget in EUR.
    - A number followed by pound, gbp, פאונד means budget in GBP.
    - If the user gives carat without price, fill carat and leave budget null.
    - If the user gives price without currency, fill budget but currency must stay null.
    Diamond type / certificate normalization:
    GIA, GIA Lab-Grown, IGI Lab-Grown.
    - If user says natural or טבעי -> GIA.
    - If user says lab grown / מעבדה without a lab name -> GIA Lab-Grown.
    - If user says IGI lab grown -> IGI Lab-Grown.
    - If user says GIA lab grown -> GIA Lab-Grown.
    """

        raw_response = self.generate_text(prompt)

        if not raw_response:
            return self._fallback_intent()

        return self._parse_json_response(raw_response)
    
    def generate_diamond_explanation(
        self,
        user_message: str,
        topic: str | None,
        language: str = "he",
        session_context: dict | None = None
    ) -> str | None:
        session_context = session_context or {}

        prompt = f"""
You are a professional Diamond Advisor Agent.

Answer the user's diamond-related question naturally and professionally.

Rules:
- Answer only about diamonds.
- Do not use a fixed answer bank.
- Do not invent diamond inventory or prices.
- Keep answers concise but include practical information that helps users choose diamonds.
- If the user asks about shapes, explain actual diamond shapes such as Round, Cushion, Princess, Oval, Emerald, Pear, Radiant, Heart and others when relevant.
- If the user asks about a specific parameter, explain that parameter.
- When explaining diamond parameters, include common example values when useful.
- Do not present the examples as the complete list unless the user asks for all options.

Parameter examples:
Shape:
Round, Oval, Princess, Cushion, Emerald, Pear, Radiant, Heart.
Cut:
Ideal, Excellent, Very Good, Good, Fair.
Color:
D, E, F, G, H, I, J.
Explain that D is the highest color grade and values progress toward more visible color.
Clarity:
FL, IF, VVS1, VVS2, VS1, VS2, SI1, SI2.
Explain the difference is related to visibility and amount of inclusions.
Polish:
Excellent, Very Good, Good, Fair.
Symmetry:
Excellent, Very Good, Good, Fair.
Girdle:
Extremely Thin, Very Thin, Thin, Medium, Slightly Thick, Thick.
Culet:
None, Very Small, Small, Medium, Large.
Type / certificate examples:
GIA, GIA Lab-Grown, IGI Lab-Grown.
Explain that GIA usually represents a natural diamond certificate in this dataset, while GIA Lab-Grown and IGI Lab-Grown represent lab-grown diamond certificates.
Carat:
Numeric weight measurement, for example 0.5, 1, 2 carat.
Depth/Table:
Percentage measurements that describe diamond proportions.
Length width ratio:
Numeric ratio describing the diamond outline, for example 1.0 for a round appearance or higher values for elongated shapes.
- Respond in this language: {language}
- Every response MUST end with one natural follow-up question that continues the conversation.
- Do not expose internal JSON, field names, code, dataset names, or CSV names.

Current session context:
{json.dumps(session_context, ensure_ascii=False)}

Topic:
{topic}

User message:
{user_message}
"""

        return self.generate_text(prompt)

    def _parse_json_response(self, text: str) -> dict:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.DOTALL)

            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    return self._fallback_intent()

            return self._fallback_intent()

    def _fallback_intent(self) -> dict:
        return {
            "intent": "clarification",
            "is_diamond_related": True,
            "language": "he",
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
            "needs_clarification": True,
            "is_new_request": False,
            "clarification_question": (
                "יש כרגע עומס זמני על מנגנון הבנת השפה שלי 😊\n"
                "אפשר לכתוב לי שוב בצורה קצרה, למשל: יהלום עגול עד 1000 דולר?"
            )
        }