"""AI-powered endpoints for CognitoForge Labs.

This module provides AI-related endpoints, including direct Gemini API access.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from backend.app.services.gemini_service import generate_gemini_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["ai"])


class GeminiRequest(BaseModel):
    """Request payload for Gemini AI queries."""

    prompt: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="The prompt to send to Gemini AI",
        examples=["Explain what a SQL injection attack is"]
    )


class GeminiSuccessResponse(BaseModel):
    """Success response from Gemini AI."""

    success: bool = Field(default=True, description="Indicates successful response")
    response: str = Field(..., description="The AI-generated response text")
    model: Optional[str] = Field(None, description="The Gemini model used")
    metadata: Optional[dict] = Field(None, description="Additional response metadata")


class GeminiErrorResponse(BaseModel):
    """Error response from Gemini AI."""

    success: bool = Field(default=False, description="Indicates failed response")
    error: str = Field(..., description="Error message describing what went wrong")
    details: Optional[str] = Field(None, description="Additional error details")


@router.post(
    "/gemini",
    response_model=GeminiSuccessResponse,
    responses={
        200: {
            "description": "Successful Gemini AI response",
            "model": GeminiSuccessResponse,
        },
        500: {
            "description": "Server error or Gemini API error",
            "model": GeminiErrorResponse,
        },
    },
    summary="Query Gemini AI",
    description="""
    Send a prompt to Google's Gemini AI and receive a response.

    This endpoint uses the Gemini REST API to generate AI-powered responses
    for security analysis, vulnerability explanations, attack vector descriptions,
    and other AI-assisted tasks.

    **Example Request:**
    ```json
    {
        "prompt": "Explain what a cross-site scripting (XSS) attack is"
    }
    ```

    **Example Response:**
    ```json
    {
        "success": true,
        "response": "Cross-site scripting (XSS) is a security vulnerability...",
        "model": "gemini-pro",
        "metadata": {
            "prompt_length": 52,
            "response_length": 243
        }
    }
    ```

    **Requirements:**
    - `GEMINI_API_KEY` must be configured in environment variables
    - Prompt must be between 1 and 10,000 characters

    **Rate Limits:**
    - Gemini API rate limits apply
    - 30-second timeout per request
    """,
)
async def query_gemini(request: GeminiRequest) -> GeminiSuccessResponse:
    """
    Query Gemini AI with a custom prompt.

    This endpoint provides direct access to Google's Gemini AI for
    generating responses to security-related queries, vulnerability
    explanations, and other AI-assisted tasks.

    Args:
        request: The Gemini request containing the prompt

    Returns:
        GeminiSuccessResponse: Success response with AI-generated text

    Raises:
        HTTPException: 500 error if Gemini API fails or configuration is missing

    Example:
        >>> response = await query_gemini(GeminiRequest(prompt="Explain SQL injection"))
        >>> print(response.response)
    """
    logger.info(
        "Gemini AI query requested",
        extra={
            "endpoint": "/api/gemini",
            "prompt_length": len(request.prompt),
        },
    )

    try:
        # Call Gemini service in threadpool to avoid blocking
        result = await run_in_threadpool(generate_gemini_response, request.prompt)

        # Check if Gemini returned an error
        if "error" in result:
            error_msg = result["error"]
            error_details = result.get("details", result.get("exception", "No additional details"))

            logger.error(
                "Gemini API returned error",
                extra={
                    "endpoint": "/api/gemini",
                    "error": error_msg,
                    "details": str(error_details)[:200],  # Limit log size
                },
            )

            raise HTTPException(
                status_code=500,
                detail={
                    "success": False,
                    "error": error_msg,
                    "details": str(error_details),
                },
            )

        # Extract response text
        response_text = result.get("text", "")
        model_name = result.get("model", "unknown")

        # Build success response
        success_response = GeminiSuccessResponse(
            success=True,
            response=response_text,
            model=model_name,
            metadata={
                "prompt_length": len(request.prompt),
                "response_length": len(response_text),
                "candidates": len(result.get("candidates", [])),
            },
        )

        logger.info(
            "Gemini AI response generated successfully",
            extra={
                "endpoint": "/api/gemini",
                "model": model_name,
                "response_length": len(response_text),
            },
        )

        return success_response

    except HTTPException:
        # Re-raise HTTP exceptions (already handled above)
        raise

    except ValueError as exc:
        # Configuration error (e.g., missing API key)
        error_msg = "Gemini API configuration error"
        logger.error(
            error_msg,
            extra={
                "endpoint": "/api/gemini",
                "error": str(exc),
            },
        )
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": error_msg,
                "details": str(exc),
            },
        ) from exc

    except Exception as exc:  # noqa: BLE001
        # Unexpected error
        error_msg = "Unexpected error processing Gemini request"
        logger.exception(
            error_msg,
            extra={
                "endpoint": "/api/gemini",
                "error_type": type(exc).__name__,
            },
        )
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": error_msg,
                "details": f"{type(exc).__name__}: {str(exc)}",
            },
        ) from exc
