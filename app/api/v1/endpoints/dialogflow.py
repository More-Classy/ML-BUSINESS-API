# app/api/v1/endpoints/dialogflow.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Optional

from app.services.dialogflow_service import DialogflowService
from app.models.schemas import DialogflowRequest, DialogflowResponse

router = APIRouter()

@router.post(
    "/chat",
    response_model=DialogflowResponse,
    summary="Chat with AI support",
    description="Send a message to the AI support system with Dialogflow and ChatGPT fallback",
    tags=["AI Support"]
)
async def chat_with_support(
    request: DialogflowRequest,
    dialogflow_service: DialogflowService = Depends()
):
    """
    Chat with the AI support system.
    
    - **message**: The user's message
    - **session_id**: Optional session ID for maintaining conversation context
    """
    try:
        # Use provided session ID or generate one
        session_id = request.session_id
        if not session_id:
            import uuid
            session_id = str(uuid.uuid4())
        
        # Get response from Dialogflow with ChatGPT fallback
        response = await dialogflow_service.detect_intent(session_id, request.message)
        
        return DialogflowResponse(
            response=response["fulfillment_text"],
            session_id=session_id,
            intent=response["intent"],
            confidence=response["confidence"],
            source=response["source"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}"
        )

@router.get(
    "/contextual-help/{business_id}",
    response_model=DialogflowResponse,
    summary="Get contextual help for a business",
    description="Get AI-powered contextual help specific to a business",
    tags=["AI Support"]
)
async def get_contextual_help(
    business_id: str,
    query: str,
    dialogflow_service: DialogflowService = Depends()
):
    """Get contextual help for a business-related query"""
    try:
        response = await dialogflow_service.get_contextual_help(business_id, query)
        
        return DialogflowResponse(
            response=response["fulfillment_text"],
            session_id=f"business_{business_id}",
            intent=response["intent"],
            confidence=response["confidence"],
            source=response["source"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get contextual help: {str(e)}"
        )