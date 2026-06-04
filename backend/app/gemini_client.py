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
    Keep existing context unless the user clearly changes it-add the new parameter to the previous context.
    The conversation is continuous.
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
    "clarification_question": null
    }}

    Allowed intents:
    recommendation, explanation, comparison, similarity, out_of_scope, clarification

    Rules:
    - Hebrew input -> language "he"; English input -> "en".
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
- Keep the answer clear, helpful, and not too long.
- If the user asks about shapes, explain actual diamond shapes such as Round, Cushion, Princess, Oval, Emerald, Pear, Radiant, Heart and others when relevant.
- If the user asks about a specific parameter, explain that parameter.
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
            "clarification_question": (
                "יש כרגע עומס זמני על מנגנון הבנת השפה שלי 😊\n"
                "אפשר לכתוב לי שוב בצורה קצרה, למשל: יהלום עגול עד 1000 דולר?"
            )
        }