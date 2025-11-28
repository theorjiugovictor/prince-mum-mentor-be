from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
import json
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    # Add your auth/db dependencies here if needed
):
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            logger.info(f"Received: {data}")
            
            # Parse the message (adjust based on your needs)
            try:
                message_data = json.loads(data)
                # Process your AI chat logic here
                # This is where you'd call your AI service
                
                # Send response back
                response = {
                    "type": "message",
                    "content": f"Received: {message_data}"
                }
                await websocket.send_json(response)
                
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })
                
    except WebSocketDisconnect:
        logger.info("WebSocket connection closed")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        await websocket.close()
