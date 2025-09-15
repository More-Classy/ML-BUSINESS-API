import os
import logging
from typing import Dict, Optional

try:
    from google.cloud import dialogflow
    from google.api_core.exceptions import GoogleAPICallError
except ImportError:
    dialogflow = None

from openai import OpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

class DialogflowService:
    def __init__(self):
        self.project_id = settings.DIALOGFLOW_PROJECT_ID

        # Set credentials path so Dialogflow can authenticate
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.GOOGLE_APPLICATION_CREDENTIALS

        if dialogflow:
            try:
                self.session_client = dialogflow.SessionsClient()
            except Exception as e:
                logger.error(f"Failed to initialize Dialogflow client: {e}")
                self.session_client = None
        else:
            self.session_client = None
            logger.warning("Dialogflow module is not available")

        # Initialize OpenAI client for fallback
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None

    async def detect_intent(
        self, session_id: str, text: str, language_code: str = "en"
    ) -> Optional[Dict]:
        """Detect intent from user text using Dialogflow with ChatGPT fallback."""
        if not self.session_client or not self.project_id:
            return await self._chatgpt_fallback(text)

        try:
            session = self.session_client.session_path(self.project_id, session_id)

            text_input = dialogflow.TextInput(text=text, language_code=language_code)
            query_input = dialogflow.QueryInput(text=text_input)

            response = self.session_client.detect_intent(
                request={"session": session, "query_input": query_input}
            )

            if (
                response.query_result.intent_detection_confidence > 0.7
                and response.query_result.fulfillment_text
            ):
                return {
                    "intent": response.query_result.intent.display_name,
                    "confidence": response.query_result.intent_detection_confidence,
                    "fulfillment_text": response.query_result.fulfillment_text,
                    "parameters": dict(response.query_result.parameters),
                    "source": "dialogflow",
                }
            else:
                return await self._chatgpt_fallback(text)

        except GoogleAPICallError as e:
            logger.error(f"Dialogflow API error: {str(e)}")
            return await self._chatgpt_fallback(text)
        except Exception as e:
            logger.error(f"Dialogflow service error: {str(e)}")
            return await self._chatgpt_fallback(text)

    async def _chatgpt_fallback(self, text: str) -> Optional[Dict]:
        """Fallback to ChatGPT when Dialogflow doesn't have a good match."""
        if not self.openai_client:
            logger.error("OpenAI client not configured for fallback")
            return {
                "intent": "fallback",
                "confidence": 0.5,
                "fulfillment_text": "I'm sorry, I'm having trouble connecting to my knowledge base. Please try again later.",
                "parameters": {},
                "source": "fallback",
            }

        try:
            prompt = f"""
            You are a customer support assistant for a business directory platform.
            The user asked: "{text}"

            Provide a helpful, professional response. If you don't have enough information,
            ask clarifying questions or suggest contacting human support.

            Response guidelines:
            - Be concise but helpful
            - Maintain professional tone
            - If unsure, don't make up information
            - Keep response under 100 words
            """

            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": prompt}],
                max_tokens=150,
                temperature=0.7,
            )

            return {
                "intent": "chatgpt_fallback",
                "confidence": 0.8,
                "fulfillment_text": response.choices[0].message.content.strip(),
                "parameters": {},
                "source": "chatgpt",
            }

        except Exception as e:
            logger.error(f"ChatGPT fallback failed: {str(e)}")
            return {
                "intent": "error",
                "confidence": 0.0,
                "fulfillment_text": "I apologize, but I'm experiencing technical difficulties. Please try again later or contact our support team.",
                "parameters": {},
                "source": "error",
            }

    async def get_contextual_help(self, business_id: int, user_query: str) -> Dict:
        """Get contextual help for business-related queries."""
        session_id = f"business_{business_id}"
        return await self.detect_intent(session_id, user_query)
