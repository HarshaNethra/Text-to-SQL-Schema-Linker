import os
import re
import time
from typing import Any, Dict, Optional

from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=env_path, override=True)


def clean_extracted_sql(raw_text: str) -> str:
    """
    Extracts clean executable SQL from LLM response text, stripping markdown code fences and extraneous text.
    """
    text = raw_text.strip()

    # If wrapped in markdown code blocks like ```sql ... ``` or ``` ... ```
    sql_match = re.search(r"```(?:sql)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if sql_match:
        text = sql_match.group(1).strip()

    # If response has multiple lines, look for the first valid SQL start statement
    valid_start_pattern = r"^(SELECT|WITH|CREATE|INSERT|UPDATE|DELETE|DROP|ALTER|REPLACE)\b"
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if lines:
        for idx, line in enumerate(lines):
            if re.match(valid_start_pattern, line, re.IGNORECASE):
                text = "\n".join(lines[idx:])
                break

    # If there is a semicolon, we preserve full statement(s)
    if ";" in text:
        parts = text.split(";")
        valid_parts = [p.strip() for p in parts if p.strip()]
        if valid_parts:
            text = ";\n".join(valid_parts) + ";"

    return text.strip()


class LLMClient:
    """
    Dedicated LLM client exclusively powered by Google Gemini.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY is required. Please set GEMINI_API_KEY in your environment or .env file."
            )
        self.model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.provider = "gemini"

    def generate_sql(self, prompt: str) -> Dict[str, Any]:
        """
        Sends prompt to Gemini LLM and returns structured response:
        {
            "sql": str,
            "latency": float,
            "input_tokens": int,
            "output_tokens": int,
            "raw_response": str,
            "error": Optional[str],
            "provider": str
        }
        """
        start_time = time.time()
        return self._call_gemini(prompt, start_time)

    def _call_gemini(self, prompt: str, start_time: float) -> Dict[str, Any]:
        """Calls Google Gemini API using google-genai SDK."""
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )
            raw_text = response.text or ""
            latency = time.time() - start_time
            sql = clean_extracted_sql(raw_text)

            # Extract token metadata if present
            in_tokens = getattr(getattr(response, "usage_metadata", None), "prompt_token_count", len(prompt) // 4)
            out_tokens = getattr(getattr(response, "usage_metadata", None), "candidates_token_count", len(sql) // 4)

            return {
                "sql": sql,
                "latency": round(latency, 4),
                "input_tokens": int(in_tokens or len(prompt) // 4),
                "output_tokens": int(out_tokens or len(sql) // 4),
                "raw_response": raw_text,
                "error": None,
                "provider": f"gemini ({self.model_name})",
            }
        except Exception as e:
            err_msg = f"Gemini API Error: {str(e)}"
            latency = time.time() - start_time
            return {
                "sql": "",
                "latency": round(latency, 4),
                "input_tokens": len(prompt) // 4,
                "output_tokens": 0,
                "raw_response": "",
                "error": err_msg,
                "provider": f"gemini ({self.model_name})",
            }
