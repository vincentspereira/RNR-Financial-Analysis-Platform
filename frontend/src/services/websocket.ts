/**
 * WebSocket client for real-time communication
 */

export enum MessageType {
  // Connection management
  CONNECT = 'connect',
  DISCONNECT = 'disconnect',
  PING = 'ping',
  PONG = 'pong',
  
  // Authentication
  AUTHENTICATE = 'authenticate',
  AUTHENTICATED = 'authenticated',
  UNAUTHORIZED = 'unauthorized',
  
  // Market data
  MARKET_DATA_SUBSCRIBE = 'market_data_subscribe',
  MARKET_DATA_UNSUBSCRIBE = 'market_data_unsubscribe',
  MARKET_DATA_UPDATE = 'market_data_update',
  
  // Portfolio updates
  PORTFOLIO_SUBSCRIBE = 'portfolio_subscribe',
  PORTFOLIO_UNSUBSCRIBE = 'portfolio_unsubscribe',
  PORTFOLIO_UPDATE = 'portfolio_update',
  
  // Notifications
  NOTIFICATION = 'notification',
  ALERT = 'alert',
  
  // Collaboration
  USER_JOINED = 'user_joined',
  USER_LEFT = 'user_left',
  USER_TYPING = 'user_typing',
  CHAT_MESSAGE = 'chat_message',
  
  // System
  ERROR = 'error',
  SUCCESS = 'success',
}

export interface WebSocketMessage {
  type: MessageType;
  data: Record<string, any>;
  timestamp?: string;
  message_id?: string;
}

export interface WebSocketConfig {
  url?: string;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  pingInterval?: number;
  debug?: boolean;
}

export type MessageHandler = (message: WebSocketMessage) => void;
export type ConnectionHandler = () => void;
export type ErrorHandler = (error: Event) => void;

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private config: Required<WebSocketConfig>;
  private messageHandlers: Map<MessageType, MessageHandler[]> = new Map();
  private connectionHandlers: ConnectionHandler[] = [];
  private disconnectionHandlers: ConnectionHandler[] = [];
  private errorHandlers: ErrorHandler[] = [];
  
  private reconnectAttempts = 0;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private pingTimer: NodeJS.Timeout | null = null;
  private isConnecting = false;
  private isAuthenticated = false;
  private connectionId: string | null = null;
  
  constructor(config: WebSocketConfig = {}) {
    this.config = {
      url: config.url || this.getWebSocketUrl(),
      reconnectInterval: config.reconnectInterval || 5000,
      maxReconnectAttempts: config.maxReconnectAttempts || 10,
      pingInterval: config.pingInterval || 30000,
      debug: config.debug || false,
    };
  }
  
  private getWebSocketUrl(): string {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    return `${protocol}//${host}/api/v1/ws`;
  }
  
  private log(message: string, ...args: any[]): void {
    if (this.config.debug) {
      console.log(`[WebSocket] ${message}`, ...args);
    }
  }
  
  private logError(message: string, ...args: any[]): void {
    console.error(`[WebSocket] ${message}`, ...args);
  }
  
  public connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        resolve();
        return;
      }
      
      if (this.isConnecting) {
        reject(new Error('Connection already in progress'));
        return;
      }
      
      this.isConnecting = true;
      this.log('Connecting to WebSocket server...');
      
      try {
        this.ws = new WebSocket(this.config.url);
        
        this.ws.onopen = () => {
          this.log('WebSocket connected');
          this.isConnecting = false;
          this.reconnectAttempts = 0;
          this.startPingTimer();
          this.connectionHandlers.forEach(handler => handler());
          resolve();
        };
        
        this.ws.onmessage = (event) => {
          this.handleMessage(event.data);
        };
        
        this.ws.onclose = (event) => {
          this.log('WebSocket disconnected', event.code, event.reason);
          this.isConnecting = false;
          this.isAuthenticated = false;
          this.connectionId = null;
          this.stopPingTimer();
          this.disconnectionHandlers.forEach(handler => handler());
          
          // Attempt to reconnect if not a clean close
          if (event.code !== 1000 && this.reconnectAttempts < this.config.maxReconnectAttempts) {
            this.scheduleReconnect();
          }
        };
        
        this.ws.onerror = (error) => {
          this.logError('WebSocket error', error);
          this.isConnecting = false;
          this.errorHandlers.forEach(handler => handler(error));
          reject(error);
        };
        
      } catch (error) {
        this.isConnecting = false;
        this.logError('Failed to create WebSocket connection', error);
        reject(error);
      }
    });
  }
  
  public disconnect(): void {
    this.log('Disconnecting WebSocket...');
    
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    
    this.stopPingTimer();
    
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }
    
    this.isAuthenticated = false;
    this.connectionId = null;
    this.reconnectAttempts = 0;
  }
  
  private scheduleReconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }
    
    this.reconnectAttempts++;
    const delay = Math.min(this.config.reconnectInterval * this.reconnectAttempts, 30000);
    
    this.log(`Scheduling reconnect attempt ${this.reconnectAttempts} in ${delay}ms`);
    
    this.reconnectTimer = setTimeout(() => {
      this.log(`Reconnect attempt ${this.reconnectAttempts}`);
      this.connect().catch(error => {
        this.logError('Reconnect failed', error);
      });
    }, delay);
  }
  
  private startPingTimer(): void {
    this.stopPingTimer();
    this.pingTimer = setInterval(() => {
      this.ping();
    }, this.config.pingInterval);
  }
  
  private stopPingTimer(): void {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }
  
  private handleMessage(data: string): void {
    try {
      const message: WebSocketMessage = JSON.parse(data);
      this.log('Received message', message);
      
      // Handle system messages
      switch (message.type) {
        case MessageType.CONNECT:
          this.connectionId = message.data.connection_id;
          break;
        case MessageType.AUTHENTICATED:
          this.isAuthenticated = true;
          break;
        case MessageType.UNAUTHORIZED:
          this.isAuthenticated = false;
          break;
        case MessageType.PONG:
          // Pong received, connection is alive
          break;
      }
      
      // Call registered handlers
      const handlers = this.messageHandlers.get(message.type) || [];
      handlers.forEach(handler => {
        try {
          handler(message);
        } catch (error) {
          this.logError('Error in message handler', error);
        }
      });
      
    } catch (error) {
      this.logError('Failed to parse WebSocket message', error);
    }
  }
  
  public send(message: Partial<WebSocketMessage>): boolean {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      this.logError('Cannot send message: WebSocket not connected');
      return false;
    }
    
    const fullMessage: WebSocketMessage = {
      type: message.type!,
      data: message.data || {},
      timestamp: new Date().toISOString(),
      message_id: this.generateMessageId(),
    };
    
    try {
      this.ws.send(JSON.stringify(fullMessage));
      this.log('Sent message', fullMessage);
      return true;
    } catch (error) {
      this.logError('Failed to send message', error);
      return false;
    }
  }
  
  private generateMessageId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }
  
  public ping(): boolean {
    return this.send({ type: MessageType.PING });
  }
  
  public authenticate(token: string): boolean {
    return this.send({
      type: MessageType.AUTHENTICATE,
      data: { token },
    });
  }
  
  public subscribeToMarketData(symbols: string[]): boolean {
    return this.send({
      type: MessageType.MARKET_DATA_SUBSCRIBE,
      data: { symbols },
    });
  }
  
  public unsubscribeFromMarketData(symbols: string[]): boolean {
    return this.send({
      type: MessageType.MARKET_DATA_UNSUBSCRIBE,
      data: { symbols },
    });
  }
  
  public subscribeToPortfolio(portfolioId: string): boolean {
    return this.send({
      type: MessageType.PORTFOLIO_SUBSCRIBE,
      data: { portfolio_id: portfolioId },
    });
  }
  
  public unsubscribeFromPortfolio(portfolioId: string): boolean {
    return this.send({
      type: MessageType.PORTFOLIO_UNSUBSCRIBE,
      data: { portfolio_id: portfolioId },
    });
  }
  
  public sendChatMessage(roomId: string, message: string): boolean {
    return this.send({
      type: MessageType.CHAT_MESSAGE,
      data: { room_id: roomId, message },
    });
  }
  
  public sendTypingIndicator(roomId: string, isTyping: boolean): boolean {
    return this.send({
      type: MessageType.USER_TYPING,
      data: { room_id: roomId, is_typing: isTyping },
    });
  }
  
  // Event handlers
  public onMessage(type: MessageType, handler: MessageHandler): () => void {
    if (!this.messageHandlers.has(type)) {
      this.messageHandlers.set(type, []);
    }
    this.messageHandlers.get(type)!.push(handler);
    
    // Return unsubscribe function
    return () => {
      const handlers = this.messageHandlers.get(type);
      if (handlers) {
        const index = handlers.indexOf(handler);
        if (index > -1) {
          handlers.splice(index, 1);
        }
      }
    };
  }
  
  public onConnect(handler: ConnectionHandler): () => void {
    this.connectionHandlers.push(handler);
    return () => {
      const index = this.connectionHandlers.indexOf(handler);
      if (index > -1) {
        this.connectionHandlers.splice(index, 1);
      }
    };
  }
  
  public onDisconnect(handler: ConnectionHandler): () => void {
    this.disconnectionHandlers.push(handler);
    return () => {
      const index = this.disconnectionHandlers.indexOf(handler);
      if (index > -1) {
        this.disconnectionHandlers.splice(index, 1);
      }
    };
  }
  
  public onError(handler: ErrorHandler): () => void {
    this.errorHandlers.push(handler);
    return () => {
      const index = this.errorHandlers.indexOf(handler);
      if (index > -1) {
        this.errorHandlers.splice(index, 1);
      }
    };
  }
  
  // Getters
  public get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
  
  public get isReconnecting(): boolean {
    return this.reconnectTimer !== null;
  }
  
  public get authenticated(): boolean {
    return this.isAuthenticated;
  }
  
  public get id(): string | null {
    return this.connectionId;
  }
  
  public getConnectionStats(): {
    connected: boolean;
    authenticated: boolean;
    connectionId: string | null;
    reconnectAttempts: number;
    isReconnecting: boolean;
  } {
    return {
      connected: this.isConnected,
      authenticated: this.isAuthenticated,
      connectionId: this.connectionId,
      reconnectAttempts: this.reconnectAttempts,
      isReconnecting: this.isReconnecting,
    };
  }
}

// React hook for WebSocket
import { useEffect, useRef, useState } from 'react';

export interface UseWebSocketOptions extends WebSocketConfig {
  autoConnect?: boolean;
  token?: string;
}

export const useWebSocket = (options: UseWebSocketOptions = {}) => {
  const [isConnected, setIsConnected] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [connectionStats, setConnectionStats] = useState<any>(null);
  const wsRef = useRef<WebSocketClient | null>(null);
  
  useEffect(() => {
    const ws = new WebSocketClient(options);
    wsRef.current = ws;
    
    // Set up event handlers
    const unsubscribeConnect = ws.onConnect(() => {
      setIsConnected(true);
      setConnectionStats(ws.getConnectionStats());
      
      // Auto-authenticate if token provided
      if (options.token) {
        ws.authenticate(options.token);
      }
    });
    
    const unsubscribeDisconnect = ws.onDisconnect(() => {
      setIsConnected(false);
      setIsAuthenticated(false);
      setConnectionStats(ws.getConnectionStats());
    });
    
    const unsubscribeAuth = ws.onMessage(MessageType.AUTHENTICATED, () => {
      setIsAuthenticated(true);
      setConnectionStats(ws.getConnectionStats());
    });
    
    const unsubscribeUnauth = ws.onMessage(MessageType.UNAUTHORIZED, () => {
      setIsAuthenticated(false);
      setConnectionStats(ws.getConnectionStats());
    });
    
    // Auto-connect if enabled
    if (options.autoConnect !== false) {
      ws.connect().catch(console.error);
    }
    
    return () => {
      unsubscribeConnect();
      unsubscribeDisconnect();
      unsubscribeAuth();
      unsubscribeUnauth();
      ws.disconnect();
    };
  }, []);
  
  return {
    ws: wsRef.current,
    isConnected,
    isAuthenticated,
    connectionStats,
    connect: () => wsRef.current?.connect(),
    disconnect: () => wsRef.current?.disconnect(),
    send: (message: Partial<WebSocketMessage>) => wsRef.current?.send(message),
    onMessage: (type: MessageType, handler: MessageHandler) => 
      wsRef.current?.onMessage(type, handler),
  };
};

// Global WebSocket instance
export const globalWebSocket = new WebSocketClient({ debug: true });