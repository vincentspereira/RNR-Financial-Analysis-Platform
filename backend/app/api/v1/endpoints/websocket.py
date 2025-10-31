"""
WebSocket endpoints for real-time communication
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.responses import HTMLResponse

from app.core.websocket import websocket_manager, market_data_streamer, WebSocketMessage, MessageType
from app.core.logging import get_logger

router = APIRouter()
websocket_logger = get_logger("websocket.api")


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint"""
    connection_id = None
    
    try:
        # Accept connection
        connection_id = await websocket_manager.connect(websocket)
        
        # Start market data streaming if not already started
        if not market_data_streamer.streaming_task:
            await market_data_streamer.start_streaming()
        
        # Handle messages
        while True:
            try:
                data = await websocket.receive_text()
                await websocket_manager.handle_message(connection_id, data)
            except WebSocketDisconnect:
                break
            except Exception as e:
                websocket_logger.error(f"Error handling WebSocket message: {str(e)}")
                # Send error message to client
                if connection_id in websocket_manager.connections:
                    error_msg = WebSocketMessage(
                        type=MessageType.ERROR,
                        data={"error": "Message processing failed"}
                    )
                    await websocket_manager.connections[connection_id].send_message(error_msg)
    
    except Exception as e:
        websocket_logger.error(f"WebSocket connection error: {str(e)}")
    
    finally:
        # Clean up connection
        if connection_id:
            await websocket_manager.disconnect(connection_id)


@router.get("/ws/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics"""
    try:
        stats = websocket_manager.get_connection_stats()
        return {
            "status": "success",
            "data": stats
        }
    except Exception as e:
        websocket_logger.error(f"Failed to get WebSocket stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve WebSocket statistics")


@router.post("/ws/broadcast")
async def broadcast_message(
    message: str,
    channel: str = None,
    room_id: str = None,
    user_id: str = None
):
    """Broadcast message to WebSocket clients (admin endpoint)"""
    try:
        broadcast_msg = WebSocketMessage(
            type=MessageType.NOTIFICATION,
            data={
                "message": message,
                "source": "admin",
                "broadcast_type": "announcement"
            }
        )
        
        sent_count = 0
        
        if channel:
            sent_count = await websocket_manager.broadcast_to_channel(channel, broadcast_msg)
        elif room_id:
            sent_count = await websocket_manager.broadcast_to_room(room_id, broadcast_msg)
        elif user_id:
            sent = await websocket_manager.send_to_user(user_id, broadcast_msg)
            sent_count = 1 if sent else 0
        else:
            sent_count = await websocket_manager.broadcast_to_all(broadcast_msg)
        
        return {
            "status": "success",
            "message": "Message broadcasted successfully",
            "recipients": sent_count
        }
        
    except Exception as e:
        websocket_logger.error(f"Failed to broadcast message: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to broadcast message")


@router.post("/ws/notify-user/{user_id}")
async def notify_user(user_id: str, notification: dict):
    """Send notification to specific user"""
    try:
        notification_msg = WebSocketMessage(
            type=MessageType.NOTIFICATION,
            data=notification
        )
        
        sent = await websocket_manager.send_to_user(user_id, notification_msg)
        
        if sent:
            return {
                "status": "success",
                "message": f"Notification sent to user {user_id}"
            }
        else:
            return {
                "status": "warning",
                "message": f"User {user_id} is not connected"
            }
            
    except Exception as e:
        websocket_logger.error(f"Failed to notify user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to send notification")


@router.post("/ws/market-data/update")
async def update_market_data(symbol: str, data: dict):
    """Update market data for a symbol (external API endpoint)"""
    try:
        market_update = WebSocketMessage(
            type=MessageType.MARKET_DATA_UPDATE,
            data={
                "symbol": symbol,
                **data
            }
        )
        
        channel = f"market_data:{symbol}"
        sent_count = await websocket_manager.broadcast_to_channel(channel, market_update)
        
        return {
            "status": "success",
            "message": f"Market data updated for {symbol}",
            "subscribers": sent_count
        }
        
    except Exception as e:
        websocket_logger.error(f"Failed to update market data for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update market data")


@router.post("/ws/portfolio/update")
async def update_portfolio(portfolio_id: str, data: dict):
    """Update portfolio data (internal API endpoint)"""
    try:
        portfolio_update = WebSocketMessage(
            type=MessageType.PORTFOLIO_UPDATE,
            data={
                "portfolio_id": portfolio_id,
                **data
            }
        )
        
        channel = f"portfolio:{portfolio_id}"
        sent_count = await websocket_manager.broadcast_to_channel(channel, portfolio_update)
        
        return {
            "status": "success",
            "message": f"Portfolio {portfolio_id} updated",
            "subscribers": sent_count
        }
        
    except Exception as e:
        websocket_logger.error(f"Failed to update portfolio {portfolio_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update portfolio")


@router.get("/ws/test")
async def websocket_test_page():
    """WebSocket test page for development"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>WebSocket Test</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 800px; margin: 0 auto; }
            .message-box { 
                border: 1px solid #ccc; 
                height: 300px; 
                overflow-y: scroll; 
                padding: 10px; 
                margin: 10px 0; 
                background: #f9f9f9;
            }
            .input-group { margin: 10px 0; }
            .input-group label { display: inline-block; width: 100px; }
            .input-group input, .input-group select { width: 200px; padding: 5px; }
            button { padding: 10px 20px; margin: 5px; }
            .connected { color: green; }
            .disconnected { color: red; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>WebSocket Test Client</h1>
            
            <div>
                Status: <span id="status" class="disconnected">Disconnected</span>
            </div>
            
            <div>
                <button id="connect-btn" onclick="connect()">Connect</button>
                <button id="disconnect-btn" onclick="disconnect()" disabled>Disconnect</button>
            </div>
            
            <div class="input-group">
                <label>Auth Token:</label>
                <input type="text" id="auth-token" placeholder="JWT token for authentication">
                <button onclick="authenticate()">Authenticate</button>
            </div>
            
            <div class="input-group">
                <label>Symbol:</label>
                <input type="text" id="symbol" value="AAPL" placeholder="Stock symbol">
                <button onclick="subscribeMarketData()">Subscribe</button>
                <button onclick="unsubscribeMarketData()">Unsubscribe</button>
            </div>
            
            <div class="input-group">
                <label>Room ID:</label>
                <input type="text" id="room-id" value="test-room" placeholder="Room ID">
                <button onclick="joinRoom()">Join Room</button>
                <button onclick="leaveRoom()">Leave Room</button>
            </div>
            
            <div class="input-group">
                <label>Chat Message:</label>
                <input type="text" id="chat-message" placeholder="Type a message">
                <button onclick="sendChatMessage()">Send</button>
            </div>
            
            <div class="message-box" id="messages"></div>
            
            <div>
                <button onclick="clearMessages()">Clear Messages</button>
                <button onclick="sendPing()">Send Ping</button>
            </div>
        </div>

        <script>
            let ws = null;
            let connectionId = null;
            
            function connect() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/api/v1/ws`;
                
                ws = new WebSocket(wsUrl);
                
                ws.onopen = function(event) {
                    document.getElementById('status').textContent = 'Connected';
                    document.getElementById('status').className = 'connected';
                    document.getElementById('connect-btn').disabled = true;
                    document.getElementById('disconnect-btn').disabled = false;
                    addMessage('Connected to WebSocket server');
                };
                
                ws.onmessage = function(event) {
                    const message = JSON.parse(event.data);
                    addMessage(`Received: ${JSON.stringify(message, null, 2)}`);
                    
                    if (message.type === 'connect') {
                        connectionId = message.data.connection_id;
                    }
                };
                
                ws.onclose = function(event) {
                    document.getElementById('status').textContent = 'Disconnected';
                    document.getElementById('status').className = 'disconnected';
                    document.getElementById('connect-btn').disabled = false;
                    document.getElementById('disconnect-btn').disabled = true;
                    addMessage('Disconnected from WebSocket server');
                };
                
                ws.onerror = function(error) {
                    addMessage(`WebSocket error: ${error}`);
                };
            }
            
            function disconnect() {
                if (ws) {
                    ws.close();
                }
            }
            
            function authenticate() {
                const token = document.getElementById('auth-token').value;
                if (ws && token) {
                    const message = {
                        type: 'authenticate',
                        data: { token: token }
                    };
                    ws.send(JSON.stringify(message));
                    addMessage(`Sent: ${JSON.stringify(message)}`);
                }
            }
            
            function subscribeMarketData() {
                const symbol = document.getElementById('symbol').value;
                if (ws && symbol) {
                    const message = {
                        type: 'market_data_subscribe',
                        data: { symbols: [symbol] }
                    };
                    ws.send(JSON.stringify(message));
                    addMessage(`Sent: ${JSON.stringify(message)}`);
                }
            }
            
            function unsubscribeMarketData() {
                const symbol = document.getElementById('symbol').value;
                if (ws && symbol) {
                    const message = {
                        type: 'market_data_unsubscribe',
                        data: { symbols: [symbol] }
                    };
                    ws.send(JSON.stringify(message));
                    addMessage(`Sent: ${JSON.stringify(message)}`);
                }
            }
            
            function joinRoom() {
                const roomId = document.getElementById('room-id').value;
                if (ws && roomId) {
                    // Note: Room joining is handled server-side, this is just for demo
                    addMessage(`Joining room: ${roomId}`);
                }
            }
            
            function leaveRoom() {
                const roomId = document.getElementById('room-id').value;
                if (ws && roomId) {
                    // Note: Room leaving is handled server-side, this is just for demo
                    addMessage(`Leaving room: ${roomId}`);
                }
            }
            
            function sendChatMessage() {
                const roomId = document.getElementById('room-id').value;
                const message = document.getElementById('chat-message').value;
                if (ws && roomId && message) {
                    const chatMessage = {
                        type: 'chat_message',
                        data: { 
                            room_id: roomId,
                            message: message 
                        }
                    };
                    ws.send(JSON.stringify(chatMessage));
                    addMessage(`Sent: ${JSON.stringify(chatMessage)}`);
                    document.getElementById('chat-message').value = '';
                }
            }
            
            function sendPing() {
                if (ws) {
                    const message = { type: 'ping' };
                    ws.send(JSON.stringify(message));
                    addMessage(`Sent: ${JSON.stringify(message)}`);
                }
            }
            
            function addMessage(message) {
                const messagesDiv = document.getElementById('messages');
                const timestamp = new Date().toLocaleTimeString();
                messagesDiv.innerHTML += `<div>[${timestamp}] ${message}</div>`;
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }
            
            function clearMessages() {
                document.getElementById('messages').innerHTML = '';
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)