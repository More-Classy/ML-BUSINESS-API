import httpx
import os
import logging
from typing import Dict, Optional
import re

try:
    from google.cloud import dialogflow_v2beta1 as dialogflow
    from google.api_core.exceptions import GoogleAPICallError
except ImportError:
    dialogflow = None

from openai import OpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

class DialogflowService:
    def __init__(self):
        self.project_id = settings.DIALOGFLOW_PROJECT_ID
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

        self.dialogflow = dialogflow
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None

    async def detect_intent(self, session_id: str, text: str, language_code: str = "en") -> Optional[Dict]:
        if not self.session_client or not self.project_id:
            logger.error("Dialogflow client not initialized or project ID missing")
            return await self._chatgpt_fallback(text)

        try:
            session = self.session_client.session_path(self.project_id, session_id)
            logger.info(f"Using session: {session}")

            text_input = self.dialogflow.TextInput(text=text, language_code=language_code)
            query_input = self.dialogflow.QueryInput(text=text_input)

            knowledge_base_path = f"projects/{self.project_id}/knowledgeBases/{settings.DIALOGFLOW_KNOWLEDGE_BASE_ID}"
            query_params = self.dialogflow.QueryParameters(
                knowledge_base_names=[knowledge_base_path]
            )

            response = self.session_client.detect_intent(
                request={
                    "session": session,
                    "query_input": query_input,
                    "query_params": query_params
                }
            )

            result = response.query_result
            logger.info(f"Dialogflow result: {result}")

            # Check Knowledge Base answers
            if result.knowledge_answers.answers:
                top_answer = result.knowledge_answers.answers[0]
                confidence = top_answer.match_confidence

                if confidence >= 0.75:
                    return {
                        "intent": result.intent.display_name if result.intent else "knowledge_base_answer",
                        "confidence": confidence,
                        "fulfillment_text": top_answer.answer,
                        "parameters": {},
                        "source": "knowledge_base"
                    }
                else:
                    logger.info(f"Low KB confidence ({confidence}). Trying homepage context...")

            # Check Dialogflow intents
            if (
                result.intent.display_name
                and result.intent_detection_confidence > 0.7
                and result.fulfillment_text
            ):
                return {
                    "intent": result.intent.display_name,
                    "confidence": result.intent_detection_confidence,
                    "fulfillment_text": result.fulfillment_text,
                    "parameters": dict(result.parameters),
                    "source": "dialogflow"
                }

            # Inject business homepage context here
            homepage_answer = await self._check_homepage_business_context(text)
            if homepage_answer:
                return homepage_answer

            # Fallback
            return await self._chatgpt_fallback(text)

        except GoogleAPICallError as e:
            logger.error(f"Dialogflow API error: {str(e)}")
            return await self._chatgpt_fallback(text)
        except Exception as e:
            logger.error(f"Dialogflow service error: {str(e)}")
            return await self._chatgpt_fallback(text)
    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r'[^a-z0-9\s]', '', text.lower())
    
    async def _check_homepage_business_context(self, query: str) -> Optional[Dict]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://more.co.ke/dotnet-api/api/Business/home-listing",
                    json={"pageNumber": 1, "pageSize": 8, "sortBy": "random"},
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )

                data = response.json()
                businesses = data.get("data", {}).get("items", [])

                query_clean = self._normalize(query)
                query_words = set(query_clean.split())

                for biz in businesses:
                    name = self._normalize(biz.get("name", ""))
                    desc = self._normalize(biz.get("description", ""))
                    tags = [self._normalize(tag.get("tagName", "")) for tag in biz.get("businessTags", [])]
                    attrs = [self._normalize(attr.get("attributeName", "")) for attr in biz.get("businessAttributes", [])]

                    # Combine all searchable fields
                    searchable_blob = f"{name} {desc} {' '.join(tags)} {' '.join(attrs)}"
                    searchable_words = set(searchable_blob.split())

                    if query_words & searchable_words:
                        return {
                            "intent": "business_homepage_context",
                            "confidence": 0.9,
                            "fulfillment_text": f"{biz['name']} is located in {biz.get('city', '')} at {biz.get('address', '')}. "
                                                f"{biz.get('description', '')} Contact: {biz.get('phoneNumber', '')}. "
                                                f"Status: {biz.get('openCloseHours', {}).get('message', '')}",
                            "parameters": {"businessID": biz.get("businessID")},
                            "source": "homepage_context"
                        }

        except Exception as e:
            logger.error(f"Failed to fetch homepage business data: {str(e)}")

        return None



    async def _chatgpt_fallback(self, text: str) -> Optional[Dict]:
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
        session_id = f"business_{business_id}"
        return await self.detect_intent(session_id, user_query)
