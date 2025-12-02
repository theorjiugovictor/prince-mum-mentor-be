"""
WebSocket Endpoint for AI Chat
Handles real-time communication for AI chat sessions.
"""

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, WebSocketException


router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    # Add your auth/db dependencies here if needed
):
    """
    Handles WebSocket connections for AI chat.

    Establishes a WebSocket connection, receives messages from the client,
    processes them (e.g., sends to an AI service), and streams responses back.
    Manages connection lifecycle including disconnections and errors.

    Args:
        websocket: The WebSocket connection object.
    """
    await websocket.accept()
    logger.info("WebSocket connection established")

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            logger.info("Received: %s", data)

            # Parse the message (adjust based on your needs)
            try:
                message_data = json.loads(data)
                # Process your AI chat logic here
                # This is where you'd call your AI service

                # Send response back
                response = {"type": "message", "content": f"Received: {message_data}"}
                await websocket.send_json(response)

            except json.JSONDecodeError:
                await websocket.send_json(
                    {"type": "error", "message": "Invalid JSON format"}
                )

    except WebSocketDisconnect:
        logger.info("WebSocket connection closed")
    except WebSocketException as e:
        logger.error("WebSocket error: %s", str(e))
        await websocket.close()
