"""JARVIS LLM summarization pipeline using Google GenAI SDK (gemini-2.5-flash)."""

import os
import json
from typing import List, Optional, Dict, Any
from datetime import datetime

from config import Config
from modules.base import BaseModule
from utils.models import EmailMessage, JarvisBriefing, ActionItem, EmailBrief
from utils.logger import print_status, print_warning, print_error, print_success

JARVIS_SYSTEM_INSTRUCTION = """
You are J.A.R.V.I.S. (Just A Rather Very Intelligent System), the world's most sophisticated AI personal assistant, serving your principal ({user_name}).

Your primary duty is to analyze incoming emails, extract critical intelligence, prioritize urgency, identify actionable tasks with deadlines, and deliver an executive briefing.

Personality & Tone:
- Address the user respectfully as "{user_name}".
- Tone: Highly articulate, refined, razor-sharp, calm, efficient, with subtle British wit and sophistication (reminiscent of Tony Stark's JARVIS).
- Zero fluff: Dismiss marketing spam, newsletters, and routine notifications with a brief note, while emphasizing mission-critical alerts, financial approvals, team requests, and security warnings.
- Highlight specific senders, firm deadlines, and required actions.

Format Requirements for your briefing:
1. Executive Briefing: A sharp 2-3 sentence high-level overview of the inbox status.
2. 🚨 Critical & Urgent Items: Bulleted high-priority items requiring immediate action or authorization today/soon.
3. 📋 Itemized Intelligence Breakdown: For each key email:
   - **Sender**: [Name & Organization]
   - **Subject**: [Subject Line]
   - **Urgency**: [Critical / High / Medium / Low]
   - **Key Takeaway**: [1-2 concise bullet points]
   - **Action Required**: [Exact next step or 'None - FYI']
   - **Deadline**: [Explicit deadline or 'N/A']
4. 💡 Strategic Recommendation: JARVIS's suggested order of operations or next steps.
"""


class EmailSummarizer(BaseModule):
    """Summarization pipeline powered by Google Gemini (gemini-2.5-flash)."""

    def __init__(self, model_name: Optional[str] = None, api_key: Optional[str] = None):
        super().__init__(name="EmailSummarizer", description="Generates executive email briefings using Gemini 2.5 Flash")
        # Resolved at runtime so Config.reload() / .env edits take effect.
        self.model_name = model_name or Config.GEMINI_MODEL
        self.api_key = api_key or Config.GEMINI_API_KEY
        self.client = None
        self._sdk_type = None  # 'genai' or 'generativeai'

    def initialize(self) -> bool:
        """Initialize Google GenAI client."""
        if not self.api_key:
            self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

        if not self.api_key:
            print_warning("GEMINI_API_KEY is not configured in .env or environment.")
            print_status("Tip: Obtain an API key from Google AI Studio (https://aistudio.google.com) and set GEMINI_API_KEY in .env.")
            self.is_initialized = False
            return False

        # Attempt 1: Modern google-genai SDK
        try:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
            self._sdk_type = "genai"
            self.is_initialized = True
            print_success(f"Google GenAI client initialized ({self.model_name}).")
            return True
        except ImportError:
            pass
        except Exception as e:
            print_warning(f"Failed to initialize google.genai: {e}. Trying google.generativeai...")

        # Attempt 2: google.generativeai fallback
        try:
            import google.generativeai as gai
            gai.configure(api_key=self.api_key)
            self.client = gai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=JARVIS_SYSTEM_INSTRUCTION.format(user_name=Config.USER_NAME),
            )
            self._sdk_type = "generativeai"
            self.is_initialized = True
            print_success(f"Google GenerativeAI client initialized ({self.model_name}).")
            return True
        except Exception as e:
            print_error(f"Failed to configure Gemini LLM SDK: {e}")
            self.is_initialized = False
            return False

    def execute(self, emails: List[EmailMessage]) -> JarvisBriefing:
        """Process and summarize a list of emails.

        Raises:
            RuntimeError: if the Gemini API key is missing or the API call fails.
                No fake/placeholder briefing is ever returned — callers must
                surface the error so misconfiguration is never mistaken for
                a working briefing.
        """
        if not emails:
            return JarvisBriefing(
                executive_summary=f"Inbox is completely clear, {Config.USER_NAME}. No unread messages require your attention at this time.",
                total_emails_processed=0,
                raw_response=f"Good day, {Config.USER_NAME}. Your inbox is completely clear. All systems operating at peak efficiency.",
            )

        # LLM client must be initialized — no silent heuristic fallback.
        if not self.is_initialized:
            if not self.initialize():
                raise RuntimeError(
                    "GEMINI_API_KEY is not configured or Gemini client failed to initialize. "
                    "Run `python setup.py` to configure your API key. "
                    "Get a key at https://aistudio.google.com/"
                )

        prompt = self._build_prompt(emails)

        # Let API errors propagate as RuntimeError (no placeholder text).
        try:
            raw_text = self._call_llm(prompt)
        except Exception as e:
            raise RuntimeError(
                f"Gemini API call failed: {e}. "
                "Check GEMINI_API_KEY / GEMINI_MODEL in .env (run `python setup.py`), "
                "then retry. No offline placeholder briefing is shown by design."
            ) from e

        if not raw_text or not raw_text.strip():
            raise RuntimeError(
                "Gemini API returned an empty response. Retry, or check your model/quota. "
                "No placeholder briefing is shown by design."
            )

        briefing = self._build_briefing_object(emails, raw_text)
        return briefing

    def _build_prompt(self, emails: List[EmailMessage]) -> str:
        """Format emails into a structured prompt for Gemini."""
        prompt_parts = [
            f"Good day. Below are {len(emails)} unread email messages retrieved from the queue.\n",
            "Please analyze them and produce the JARVIS Executive Briefing according to your instructions.\n",
            "--- INCOMING EMAIL QUEUE ---\n",
        ]

        for i, email_msg in enumerate(emails, start=1):
            date_str = email_msg.date.strftime('%Y-%m-%d %H:%M') if email_msg.date else "Unknown Date"
            attachments_info = ", ".join(a.filename for a in email_msg.attachments) if email_msg.attachments else "None"
            
            prompt_parts.append(f"""
EMAIL #{i} [ID: {email_msg.id}]
- From: {email_msg.sender}
- To: {email_msg.recipient}
- Date: {date_str}
- Subject: {email_msg.subject}
- Attachments: {attachments_info}
- Body:
\"\"\"
{email_msg.body_text}
\"\"\"
---------------------------------------------
""")

        prompt_parts.append(f"\nPlease compile the executive briefing for {Config.USER_NAME} now.")
        return "".join(prompt_parts)

    def _call_llm(self, prompt: str) -> str:
        """Invoke Gemini LLM with the prompt and model fallbacks."""
        system_prompt = JARVIS_SYSTEM_INSTRUCTION.format(user_name=Config.USER_NAME)
        models_to_try = [self.model_name]
        for fallback in ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.5-flash"]:
            if fallback not in models_to_try:
                models_to_try.append(fallback)

        last_error = None
        for model in models_to_try:
            try:
                if self._sdk_type == "genai":
                    from google.genai import types
                    response = self.client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=system_prompt,
                            temperature=0.3,
                        ),
                    )
                    return response.text or ""

                elif self._sdk_type == "generativeai":
                    response = self.client.generate_content(prompt)
                    return response.text or ""
            except Exception as e:
                last_error = e
                continue

        if last_error:
            raise last_error
        raise RuntimeError("LLM SDK not properly configured.")

    def _build_briefing_object(self, emails: List[EmailMessage], raw_response: str) -> JarvisBriefing:
        """Construct a JarvisBriefing model containing raw markdown and parsed metadata."""
        return JarvisBriefing(
            executive_summary=f"Processed {len(emails)} unread emails.",
            total_emails_processed=len(emails),
            raw_response=raw_response,
            timestamp=datetime.now(),
        )
