# app/api/v1/endpoints/chat.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional, List
import uuid
import logging
from app.services.chat_service import ChatService
from app.models.schemas import (
    ChatSessionCreate,
    ChatSessionResponse,
    ChatMessageRequest,
    ChatMessageResponse,
    ChatHistoryResponse,
    ChatMessageItem
)
from app.database.connection import database

logger = logging.getLogger(__name__)

router = APIRouter()

def get_chat_service() -> ChatService:
    """Dependency to get ChatService instance"""
    if not database.pool:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available"
        )
    return ChatService(db_pool=database.pool)

@router.post(
    "/session",
    response_model=ChatSessionResponse,
    summary="Create or get chat session",
    description="Create a new chat session or retrieve existing one",
    tags=["Chat"]
)
async def create_session(
    request: ChatSessionCreate,
    chat_service: ChatService = Depends(get_chat_service)
):
    """Create or get a chat session"""
    try:
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())
        
        result = await chat_service.create_or_get_session(
            session_id=session_id,
            email=request.email,
            name=request.name,
            browser_fingerprint=request.browser_fingerprint,
            ip_address=request.ip_address,
            user_agent=request.user_agent
        )
        
        return ChatSessionResponse(**result)
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {str(e)}"
        )

@router.post(
    "/message",
    response_model=ChatMessageResponse,
    summary="Send a chat message",
    description="Send a message and get AI response",
    tags=["Chat"]
)
async def send_message(
    request: ChatMessageRequest,
    chat_service: ChatService = Depends(get_chat_service)
):
    """Send a chat message and get AI response"""
    try:
        result = await chat_service.send_message(
            session_id=request.session_id,
            message=request.message,
            user_email=request.user_email,
            user_name=request.user_name
        )
        
        return ChatMessageResponse(**result)
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {str(e)}"
        )

@router.get(
    "/history/{session_id}",
    response_model=ChatHistoryResponse,
    summary="Get chat history",
    description="Get chat history for a session",
    tags=["Chat"]
)
async def get_history(
    session_id: str,
    limit: int = 50,
    chat_service: ChatService = Depends(get_chat_service)
):
    """Get chat history for a session"""
    try:
        messages = await chat_service.get_chat_history(
            session_id=session_id,
            limit=limit
        )
        
        return ChatHistoryResponse(
            messages=messages,
            session_id=session_id
        )
    except Exception as e:
        logger.error(f"Error getting history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get history: {str(e)}"
        )

@router.get(
    "/sessions",
    summary="Get user sessions",
    description="Get all sessions for a user (by email or browser fingerprint)",
    tags=["Chat"]
)
async def get_user_sessions(
    email: Optional[str] = None,
    browser_fingerprint: Optional[str] = None,
    chat_service: ChatService = Depends(get_chat_service)
):
    """Get all sessions for a user"""
    try:
        if not email and not browser_fingerprint:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either email or browser_fingerprint must be provided"
            )
        
        sessions = await chat_service.get_user_sessions(
            email=email,
            browser_fingerprint=browser_fingerprint
        )
        
        return {"sessions": sessions}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user sessions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user sessions: {str(e)}"
        )
