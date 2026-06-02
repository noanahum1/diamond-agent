import os
import json
import re
from dotenv import load_dotenv
from google import genai
from google.genai import errors

load_dotenv()

class GeminiClient:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            self.is_available = False
            self.client = None
            self.model = None
            return

        self.is_available = True
        self.client = genai.Client(api_key=api_key, http_options={'api_version': 'v1b'})
        self.model = "models/gemini-1.5-flash"

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

        prompt = f"""
You are a language understanding layer for a Diamond Advisor Agent.

Return ONLY valid JSON.
Do not recommend diamonds.
Do not invent diamond data.
Do not calculate prices.
Do not add explanations outside the JSON.

Current session context:
{json.dumps(session_context, ensure_ascii=False)}

User message:
{user_message}

Return JSON with this exact structure:
{{
  "intent": "recommendation",
  "is_diamond_related": true,
  "budget": null,
  "currency": null,
  "shape": null,
  "cut": null,
  "color": null,
  "clarity": null,
  "polish": null,
  "symmetry": null,
  "preference": null,
  "topic": null,
  "needs_clarification": false,
  "clarification_question": null
}}

Allowed intents:
recommendation, explanation, comparison, similarity, out_of_scope, clarification

Rules:
- עגול, עגולה, ראונד = round
- קושיין, כושיין, כושין, קושין = cushion
- דולר, usd, dollar = USD
- שקל, שח, nis, ils = ILS
- יורו, euro, eur = EUR
- פאונד, pound, gbp = GBP
- If the user writes only a number and the session context indicates budget is missing, treat it as budget.
- If the user asks about a non-diamond topic, set intent to out_of_scope and is_diamond_related to false.
- If the user asks for an explanation of a diamond parameter, set intent to explanation and fill topic.
"""

        raw_response = self.generate_text(prompt)

        if not raw_response:
            return self._fallback_intent()

        return self._parse_json_response(raw_response)

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
            "needs_clarification": True,
            "clarification_question": (
                "יש כרגע עומס זמני על מנגנון הבנת השפה שלי 😊\n"
                "אפשר לכתוב לי שוב בצורה קצרה, למשל: יהלום עגול עד 1000 דולר."
            )
        }

if __name__ == "__main__":
    client = GeminiClient()

    result = client.extract_user_intent(
        "אני מחפשת יהלום עגול עד 5000 שקל",
        {"last_question": None}
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))