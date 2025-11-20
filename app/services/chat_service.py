import logging
from typing import Dict, Optional, List
from datetime import datetime
import aiomysql
from app.services.dialogflow_service import DialogflowService
from app.database.connection import database

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self, db_pool=None):
        self.db_pool = db_pool
        self.dialogflow_service = DialogflowService()
    
    async def create_or_get_session(
        self,
        session_id: str,
        email: Optional[str] = None,
        name: Optional[str] = None,
        browser_fingerprint: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict:
        """Create a new chat session or get existing one"""
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    # Check if session exists
                    await cursor.execute(
                        """
                        SELECT * FROM chat_sessions 
                        WHERE session_id = %s
                        """,
                        (session_id,)
                    )
                    session = await cursor.fetchone()
                    
                    if session:
                        # Update last access
                        await cursor.execute(
                            """
                            UPDATE chat_sessions 
                            SET updated_at = %s, status = 'active'
                            WHERE session_id = %s
                            """,
                            (datetime.utcnow(), session_id)
                        )
                        return {
                            "session_id": session["session_id"],
                            "user_id": session.get("user_id"),
                            "email": session.get("email"),
                            "name": session.get("name"),
                            "is_returning_user": True,
                            "existing_session": True
                        }
                    
                    # Check for returning user by email or browser fingerprint
                    user_id = None
                    is_returning_user = False
                    existing_email = None
                    existing_name = None
                    
                    if email:
                        await cursor.execute(
                            """
                            SELECT id FROM chat_sessions 
                            WHERE email = %s 
                            ORDER BY created_at DESC 
                            LIMIT 1
                            """,
                            (email,)
                        )
                        existing = await cursor.fetchone()
                        if existing:
                            is_returning_user = True
                            existing_email = email
                    
                    if not is_returning_user and browser_fingerprint:
                        await cursor.execute(
                            """
                            SELECT email, name FROM chat_sessions 
                            WHERE browser_fingerprint = %s 
                            AND email IS NOT NULL
                            ORDER BY created_at DESC 
                            LIMIT 1
                            """,
                            (browser_fingerprint,)
                        )
                        existing = await cursor.fetchone()
                        if existing:
                            is_returning_user = True
                            existing_email = existing.get("email")
                            existing_name = existing.get("name")
                    
                    # Use existing user info if found
                    final_email = existing_email or email
                    final_name = existing_name or name
                    
                    # Get user_id if exists
                    if final_email:
                        await cursor.execute(
                            """
                            SELECT Id FROM users2 
                            WHERE Email = %s
                            LIMIT 1
                            """,
                            (final_email,)
                        )
                        user = await cursor.fetchone()
                        if user:
                            user_id = user["Id"]  # Note: users2 uses 'Id' with capital I
                    
                    # Create new session
                    await cursor.execute(
                        """
                        INSERT INTO chat_sessions 
                        (session_id, user_id, email, name, browser_fingerprint, ip_address, user_agent, status, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, 'active', %s, %s)
                        """,
                        (
                            session_id,
                            user_id,
                            final_email,
                            final_name,
                            browser_fingerprint,
                            ip_address,
                            user_agent,
                            datetime.utcnow(),
                            datetime.utcnow()
                        )
                    )
                    
                    return {
                        "session_id": session_id,
                        "user_id": user_id,
                        "email": final_email,
                        "name": final_name,
                        "is_returning_user": is_returning_user,
                        "existing_session": False
                    }
        except Exception as e:
            logger.error(f"Error creating/getting session: {str(e)}")
            raise
    
    async def save_message(
        self,
        session_id: str,
        message: str,
        sender: str,
        intent: Optional[str] = None,
        confidence: Optional[float] = None,
        source: Optional[str] = None,
        message_type: str = "text",
        metadata: Optional[Dict] = None
    ) -> int:
        """Save a chat message to database"""
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    # Verify session exists before saving message
                    await cursor.execute(
                        """
                        SELECT session_id FROM chat_sessions 
                        WHERE session_id = %s
                        """,
                        (session_id,)
                    )
                    session_exists = await cursor.fetchone()
                    
                    if not session_exists:
                        logger.warning(f"Session {session_id} does not exist. Creating it now.")
                        # Create a minimal session
                        await cursor.execute(
                            """
                            INSERT INTO chat_sessions 
                            (session_id, status, created_at, updated_at)
                            VALUES (%s, 'active', %s, %s)
                            """,
                            (session_id, datetime.utcnow(), datetime.utcnow())
                        )
                    import json
                    metadata_json = json.dumps(metadata) if metadata else None
                    
                    await cursor.execute(
                        """
                        INSERT INTO chat_messages 
                        (session_id, message, sender, message_type, intent, confidence, source, metadata, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            session_id,
                            message,
                            sender,
                            message_type,
                            intent,
                            confidence,
                            source,
                            metadata_json,
                            datetime.utcnow()
                        )
                    )
                    message_id = cursor.lastrowid
                    
                    # Update session last_message_at
                    await cursor.execute(
                        """
                        UPDATE chat_sessions 
                        SET last_message_at = %s, updated_at = %s
                        WHERE session_id = %s
                        """,
                        (datetime.utcnow(), datetime.utcnow(), session_id)
                    )
                    
                    return message_id
        except Exception as e:
            logger.error(f"Error saving message: {str(e)}")
            raise
    
    async def get_chat_history(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[Dict]:
        """Get chat history for a session"""
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(
                        """
                        SELECT id, message, sender, message_type, intent, confidence, source, created_at
                        FROM chat_messages 
                        WHERE session_id = %s
                        ORDER BY created_at ASC
                        LIMIT %s
                        """,
                        (session_id, limit)
                    )
                    messages = await cursor.fetchall()
                    
                    # Convert datetime to string for JSON serialization
                    for msg in messages:
                        if msg.get("created_at"):
                            msg["timestamp"] = msg["created_at"].isoformat() if isinstance(msg["created_at"], datetime) else str(msg["created_at"])
                            msg["created_at"] = msg["timestamp"]
                    
                    return messages
        except Exception as e:
            logger.error(f"Error getting chat history: {str(e)}")
            return []
    
    async def send_message(
        self,
        session_id: str,
        message: str,
        user_email: Optional[str] = None,
        user_name: Optional[str] = None
    ) -> Dict:
        """Send a message and get AI response"""
        try:
            # Ensure session exists - create if it doesn't
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(
                        """
                        SELECT session_id FROM chat_sessions 
                        WHERE session_id = %s
                        """,
                        (session_id,)
                    )
                    existing_session = await cursor.fetchone()
                    
                    if not existing_session:
                        # Create session if it doesn't exist
                        await cursor.execute(
                            """
                            INSERT INTO chat_sessions 
                            (session_id, email, name, status, created_at, updated_at)
                            VALUES (%s, %s, %s, 'active', %s, %s)
                            """,
                            (
                                session_id,
                                user_email,
                                user_name,
                                datetime.utcnow(),
                                datetime.utcnow()
                            )
                        )
            
            # Save user message
            await self.save_message(
                session_id=session_id,
                message=message,
                sender="user"
            )
            
            # Get AI response from Dialogflow
            response = await self.dialogflow_service.detect_intent(
                session_id=session_id,
                text=message
            )
            
            # Save bot response
            await self.save_message(
                session_id=session_id,
                message=response.get("fulfillment_text", ""),
                sender="bot",
                intent=response.get("intent"),
                confidence=response.get("confidence"),
                source=response.get("source")
            )
            
            # Personalize response with user name if available
            fulfillment_text = response.get("fulfillment_text", "")
            if user_name and user_name not in fulfillment_text and response.get("source") == "chatgpt":
                # Only personalize ChatGPT responses to avoid duplication
                pass  # Could add personalization here if needed
            
            return {
                "response": fulfillment_text,
                "session_id": session_id,
                "intent": response.get("intent"),
                "confidence": response.get("confidence"),
                "source": response.get("source")
            }
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            error_message = "I apologize, but I'm experiencing technical difficulties. Please try again later."
            
            # Save error message
            try:
                await self.save_message(
                    session_id=session_id,
                    message=error_message,
                    sender="bot",
                    source="error"
                )
            except:
                pass
            
            return {
                "response": error_message,
                "session_id": session_id,
                "intent": "error",
                "confidence": 0.0,
                "source": "error"
            }
    
    async def get_user_sessions(
        self,
        email: Optional[str] = None,
        browser_fingerprint: Optional[str] = None
    ) -> List[Dict]:
        """Get all sessions for a user"""
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    if email:
                        await cursor.execute(
                            """
                            SELECT session_id, name, email, created_at, last_message_at, status
                            FROM chat_sessions 
                            WHERE email = %s
                            ORDER BY created_at DESC
                            """,
                            (email,)
                        )
                    elif browser_fingerprint:
                        await cursor.execute(
                            """
                            SELECT session_id, name, email, created_at, last_message_at, status
                            FROM chat_sessions 
                            WHERE browser_fingerprint = %s
                            ORDER BY created_at DESC
                            """,
                            (browser_fingerprint,)
                        )
                    else:
                        return []
                    
                    sessions = await cursor.fetchall()
                    for session in sessions:
                        if session.get("created_at"):
                            session["created_at"] = session["created_at"].isoformat() if isinstance(session["created_at"], datetime) else str(session["created_at"])
                        if session.get("last_message_at"):
                            session["last_message_at"] = session["last_message_at"].isoformat() if isinstance(session["last_message_at"], datetime) else str(session["last_message_at"])
                    
                    return sessions
        except Exception as e:
            logger.error(f"Error getting user sessions: {str(e)}")
            return []
