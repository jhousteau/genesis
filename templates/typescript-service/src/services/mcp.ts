/**
 * Genesis MCP (Model Context Protocol) Foundation Support
 *
 * Foundation for MCP protocol integration in TypeScript services,
 * preparing for claude-talk migration and agent communication.
 */

import { EventEmitter } from 'events';
import WebSocket from 'ws';
import { v4 as uuidv4 } from 'uuid';

import { Logger } from '../utils/logger';
import { Config } from '../config';
import { GenesisError, ValidationError, TimeoutError } from '../types/errors';

// MCP Protocol Types
export interface MCPMessage {
  id: string;
  type: 'request' | 'response' | 'notification';
  method?: string;
  params?: any;
  result?: any;
  error?: {
    code: number;
    message: string;
    data?: any;
  };
}

export interface MCPTool {
  name: string;
  description: string;
  parameters?: {
    type: 'object';
    properties: Record<string, any>;
    required?: string[];
  };
}

export interface MCPResource {
  uri: string;
  name: string;
  description?: string;
  mimeType?: string;
}

export interface MCPCapabilities {
  tools?: {
    listChanged?: boolean;
  };
  resources?: {
    subscribe?: boolean;
    listChanged?: boolean;
  };
  prompts?: {
    listChanged?: boolean;
  };
  logging?: {
    level?: 'debug' | 'info' | 'notice' | 'warning' | 'error' | 'critical' | 'alert' | 'emergency';
  };
}

// MCP Client for outgoing connections
export class MCPClient extends EventEmitter {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private pingInterval: NodeJS.Timeout | null = null;
  private pendingRequests = new Map<string, {
    resolve: (value: any) => void;
    reject: (error: Error) => void;
    timeout: NodeJS.Timeout;
  }>();
  private logger: Logger;
  private capabilities: MCPCapabilities = {};

  constructor(url: string) {
    super();
    this.url = url;
    this.logger = Logger.getInstance('mcp-client');
  }

  /**
   * Connect to MCP server
   */
  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.logger.info('Connecting to MCP server', { url: this.url });

        this.ws = new WebSocket(this.url);

        this.ws.on('open', async () => {
          this.logger.info('MCP connection established');
          this.reconnectAttempts = 0;
          this.setupPing();

          try {
            // Initialize connection with server
            await this.initialize();
            this.emit('connected');
            resolve();
          } catch (error) {
            this.logger.error('MCP initialization failed', { error: error.message });
            reject(error);
          }
        });

        this.ws.on('message', (data: Buffer) => {
          try {
            const message: MCPMessage = JSON.parse(data.toString());
            this.handleMessage(message);
          } catch (error) {
            this.logger.error('Failed to parse MCP message', {
              error: error.message,
              data: data.toString()
            });
          }
        });

        this.ws.on('close', (code: number, reason: Buffer) => {
          this.logger.warn('MCP connection closed', {
            code,
            reason: reason.toString()
          });
          this.cleanup();
          this.emit('disconnected', { code, reason: reason.toString() });

          if (this.shouldReconnect(code)) {
            this.scheduleReconnect();
          }
        });

        this.ws.on('error', (error: Error) => {
          this.logger.error('MCP connection error', { error: error.message });
          this.emit('error', error);
          reject(error);
        });

      } catch (error) {
        this.logger.error('Failed to create MCP connection', { error: error.message });
        reject(error);
      }
    });
  }

  /**
   * Disconnect from MCP server
   */
  async disconnect(): Promise<void> {
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.cleanup();
    }
  }

  /**
   * Send request to MCP server
   */
  async request(method: string, params?: any): Promise<any> {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new GenesisError('MCP client not connected', 503);
    }

    return new Promise((resolve, reject) => {
      const id = uuidv4();
      const message: MCPMessage = {
        id,
        type: 'request',
        method,
        params
      };

      // Set up timeout
      const timeout = setTimeout(() => {
        this.pendingRequests.delete(id);
        reject(new TimeoutError(`MCP request ${method}`, 30000));
      }, 30000);

      // Store pending request
      this.pendingRequests.set(id, { resolve, reject, timeout });

      try {
        this.ws!.send(JSON.stringify(message));
        this.logger.debug('MCP request sent', { method, id, params });
      } catch (error) {
        this.pendingRequests.delete(id);
        clearTimeout(timeout);
        reject(new GenesisError(`Failed to send MCP request: ${error.message}`, 500));
      }
    });
  }

  /**
   * Send notification to MCP server
   */
  notify(method: string, params?: any): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new GenesisError('MCP client not connected', 503);
    }

    const message: MCPMessage = {
      id: uuidv4(),
      type: 'notification',
      method,
      params
    };

    try {
      this.ws.send(JSON.stringify(message));
      this.logger.debug('MCP notification sent', { method, params });
    } catch (error) {
      this.logger.error('Failed to send MCP notification', {
        method,
        error: error.message
      });
    }
  }

  /**
   * List available tools from server
   */
  async listTools(): Promise<MCPTool[]> {
    try {
      const response = await this.request('tools/list');
      return response.tools || [];
    } catch (error) {
      this.logger.error('Failed to list MCP tools', { error: error.message });
      throw error;
    }
  }

  /**
   * Call a tool on the server
   */
  async callTool(name: string, arguments_?: any): Promise<any> {
    try {
      const response = await this.request('tools/call', {
        name,
        arguments: arguments_ || {}
      });
      return response.result;
    } catch (error) {
      this.logger.error('Failed to call MCP tool', {
        name,
        arguments: arguments_,
        error: error.message
      });
      throw error;
    }
  }

  /**
   * List available resources from server
   */
  async listResources(): Promise<MCPResource[]> {
    try {
      const response = await this.request('resources/list');
      return response.resources || [];
    } catch (error) {
      this.logger.error('Failed to list MCP resources', { error: error.message });
      throw error;
    }
  }

  /**
   * Read a resource from the server
   */
  async readResource(uri: string): Promise<any> {
    try {
      const response = await this.request('resources/read', { uri });
      return response.contents;
    } catch (error) {
      this.logger.error('Failed to read MCP resource', {
        uri,
        error: error.message
      });
      throw error;
    }
  }

  // Private methods

  private async initialize(): Promise<void> {
    const initParams = {
      protocolVersion: '2024-11-05',
      capabilities: {
        tools: {},
        resources: {}
      },
      clientInfo: {
        name: Config.getInstance().serviceName,
        version: Config.getInstance().version
      }
    };

    const response = await this.request('initialize', initParams);
    this.capabilities = response.capabilities || {};

    this.logger.info('MCP client initialized', {
      serverCapabilities: this.capabilities
    });
  }

  private handleMessage(message: MCPMessage): void {
    this.logger.debug('MCP message received', {
      type: message.type,
      method: message.method,
      id: message.id
    });

    if (message.type === 'response') {
      this.handleResponse(message);
    } else if (message.type === 'request') {
      this.handleRequest(message);
    } else if (message.type === 'notification') {
      this.handleNotification(message);
    }
  }

  private handleResponse(message: MCPMessage): void {
    const pending = this.pendingRequests.get(message.id);
    if (!pending) {
      this.logger.warn('Received response for unknown request', { id: message.id });
      return;
    }

    this.pendingRequests.delete(message.id);
    clearTimeout(pending.timeout);

    if (message.error) {
      const error = new GenesisError(
        message.error.message,
        message.error.code,
        undefined,
        message.error.data
      );
      pending.reject(error);
    } else {
      pending.resolve(message.result);
    }
  }

  private handleRequest(message: MCPMessage): void {
    // Handle requests from server (if needed)
    this.emit('request', message);
  }

  private handleNotification(message: MCPMessage): void {
    // Handle notifications from server
    this.emit('notification', message);

    // Handle specific notifications
    switch (message.method) {
      case 'notifications/tools/list_changed':
        this.emit('tools_changed');
        break;
      case 'notifications/resources/list_changed':
        this.emit('resources_changed');
        break;
      case 'notifications/resources/updated':
        this.emit('resource_updated', message.params);
        break;
    }
  }

  private setupPing(): void {
    this.pingInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.ping();
      }
    }, 30000); // Ping every 30 seconds
  }

  private cleanup(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }

    // Reject all pending requests
    for (const [id, pending] of this.pendingRequests) {
      clearTimeout(pending.timeout);
      pending.reject(new GenesisError('Connection closed', 503));
    }
    this.pendingRequests.clear();
  }

  private shouldReconnect(code: number): boolean {
    // Don't reconnect on normal closure or auth failures
    return code !== 1000 && code !== 1002 && code !== 1003;
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      this.logger.error('Max reconnect attempts reached');
      this.emit('max_reconnects_exceeded');
      return;
    }

    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts);
    this.reconnectAttempts++;

    this.logger.info('Scheduling MCP reconnect', {
      attempt: this.reconnectAttempts,
      delay
    });

    setTimeout(() => {
      this.connect().catch(error => {
        this.logger.error('MCP reconnect failed', { error: error.message });
      });
    }, delay);
  }
}

// MCP Server for incoming connections
export class MCPServer extends EventEmitter {
  private server: WebSocket.Server;
  private clients = new Set<WebSocket>();
  private tools = new Map<string, MCPTool>();
  private resources = new Map<string, MCPResource>();
  private logger: Logger;
  private capabilities: MCPCapabilities;

  constructor(port: number = 3001) {
    super();
    this.logger = Logger.getInstance('mcp-server');
    this.capabilities = {
      tools: { listChanged: true },
      resources: { subscribe: true, listChanged: true },
      logging: { level: 'info' }
    };

    this.server = new WebSocket.Server({ port });
    this.setupServer();

    this.logger.info('MCP server started', { port });
  }

  /**
   * Register a tool
   */
  registerTool(tool: MCPTool, handler: (params: any) => Promise<any>): void {
    this.tools.set(tool.name, { ...tool, handler } as any);
    this.logger.info('MCP tool registered', { name: tool.name });

    // Notify clients of tool list change
    this.broadcast('notifications/tools/list_changed');
  }

  /**
   * Register a resource
   */
  registerResource(resource: MCPResource, provider: () => Promise<any>): void {
    this.resources.set(resource.uri, { ...resource, provider } as any);
    this.logger.info('MCP resource registered', { uri: resource.uri });

    // Notify clients of resource list change
    this.broadcast('notifications/resources/list_changed');
  }

  /**
   * Broadcast notification to all clients
   */
  broadcast(method: string, params?: any): void {
    const message: MCPMessage = {
      id: uuidv4(),
      type: 'notification',
      method,
      params
    };

    const messageStr = JSON.stringify(message);

    for (const client of this.clients) {
      if (client.readyState === WebSocket.OPEN) {
        try {
          client.send(messageStr);
        } catch (error) {
          this.logger.error('Failed to broadcast to client', { error: error.message });
        }
      }
    }
  }

  /**
   * Stop the server
   */
  async stop(): Promise<void> {
    return new Promise((resolve) => {
      this.server.close(() => {
        this.logger.info('MCP server stopped');
        resolve();
      });
    });
  }

  // Private methods

  private setupServer(): void {
    this.server.on('connection', (ws: WebSocket) => {
      this.logger.info('MCP client connected');

      this.clients.add(ws);
      this.emit('client_connected', ws);

      ws.on('message', (data: Buffer) => {
        try {
          const message: MCPMessage = JSON.parse(data.toString());
          this.handleClientMessage(ws, message);
        } catch (error) {
          this.logger.error('Failed to parse client message', {
            error: error.message
          });
          this.sendError(ws, 'parse_error', 'Failed to parse JSON');
        }
      });

      ws.on('close', () => {
        this.logger.info('MCP client disconnected');
        this.clients.delete(ws);
        this.emit('client_disconnected', ws);
      });

      ws.on('error', (error: Error) => {
        this.logger.error('MCP client error', { error: error.message });
        this.clients.delete(ws);
      });
    });
  }

  private async handleClientMessage(ws: WebSocket, message: MCPMessage): Promise<void> {
    this.logger.debug('MCP client message', {
      type: message.type,
      method: message.method
    });

    try {
      if (message.type === 'request') {
        await this.handleRequest(ws, message);
      } else if (message.type === 'notification') {
        this.handleNotification(ws, message);
      }
    } catch (error) {
      this.logger.error('Error handling client message', { error: error.message });
      this.sendError(ws, message.id, error.message);
    }
  }

  private async handleRequest(ws: WebSocket, message: MCPMessage): Promise<void> {
    let result: any;

    switch (message.method) {
      case 'initialize':
        result = {
          protocolVersion: '2024-11-05',
          capabilities: this.capabilities,
          serverInfo: {
            name: Config.getInstance().serviceName,
            version: Config.getInstance().version
          }
        };
        break;

      case 'tools/list':
        result = {
          tools: Array.from(this.tools.values()).map(tool => ({
            name: tool.name,
            description: tool.description,
            parameters: tool.parameters
          }))
        };
        break;

      case 'tools/call':
        result = await this.callTool(message.params?.name, message.params?.arguments);
        break;

      case 'resources/list':
        result = {
          resources: Array.from(this.resources.values()).map(resource => ({
            uri: resource.uri,
            name: resource.name,
            description: resource.description,
            mimeType: resource.mimeType
          }))
        };
        break;

      case 'resources/read':
        result = await this.readResource(message.params?.uri);
        break;

      default:
        throw new ValidationError(`Unknown method: ${message.method}`);
    }

    this.sendResponse(ws, message.id, result);
  }

  private handleNotification(ws: WebSocket, message: MCPMessage): void {
    // Handle notifications from client
    this.emit('client_notification', ws, message);
  }

  private async callTool(name: string, arguments_: any): Promise<any> {
    const tool = this.tools.get(name) as any;
    if (!tool) {
      throw new ValidationError(`Unknown tool: ${name}`);
    }

    try {
      const result = await tool.handler(arguments_);
      return { result };
    } catch (error) {
      throw new GenesisError(`Tool execution failed: ${error.message}`, 500);
    }
  }

  private async readResource(uri: string): Promise<any> {
    const resource = this.resources.get(uri) as any;
    if (!resource) {
      throw new ValidationError(`Unknown resource: ${uri}`);
    }

    try {
      const contents = await resource.provider();
      return { contents };
    } catch (error) {
      throw new GenesisError(`Resource read failed: ${error.message}`, 500);
    }
  }

  private sendResponse(ws: WebSocket, id: string, result: any): void {
    const message: MCPMessage = {
      id,
      type: 'response',
      result
    };

    try {
      ws.send(JSON.stringify(message));
    } catch (error) {
      this.logger.error('Failed to send response', { error: error.message });
    }
  }

  private sendError(ws: WebSocket, id: string, errorMessage: string): void {
    const message: MCPMessage = {
      id,
      type: 'response',
      error: {
        code: -32603,
        message: errorMessage
      }
    };

    try {
      ws.send(JSON.stringify(message));
    } catch (error) {
      this.logger.error('Failed to send error', { error: error.message });
    }
  }
}

/**
 * MCP Manager for unified client and server management
 */
export class MCPManager {
  private static instance: MCPManager;
  private client: MCPClient | null = null;
  private server: MCPServer | null = null;
  private logger: Logger;

  private constructor() {
    this.logger = Logger.getInstance('mcp-manager');
  }

  public static getInstance(): MCPManager {
    if (!MCPManager.instance) {
      MCPManager.instance = new MCPManager();
    }
    return MCPManager.instance;
  }

  /**
   * Initialize MCP client
   */
  async initializeClient(url: string): Promise<MCPClient> {
    if (this.client) {
      await this.client.disconnect();
    }

    this.client = new MCPClient(url);
    await this.client.connect();

    this.logger.info('MCP client initialized', { url });
    return this.client;
  }

  /**
   * Initialize MCP server
   */
  initializeServer(port: number = 3001): MCPServer {
    if (this.server) {
      this.server.stop();
    }

    this.server = new MCPServer(port);
    this.logger.info('MCP server initialized', { port });
    return this.server;
  }

  /**
   * Get current client
   */
  getClient(): MCPClient | null {
    return this.client;
  }

  /**
   * Get current server
   */
  getServer(): MCPServer | null {
    return this.server;
  }

  /**
   * Shutdown all MCP components
   */
  async shutdown(): Promise<void> {
    const promises: Promise<void>[] = [];

    if (this.client) {
      promises.push(this.client.disconnect());
    }

    if (this.server) {
      promises.push(this.server.stop());
    }

    await Promise.all(promises);
    this.logger.info('MCP manager shutdown complete');
  }
}

// Export singleton instance
export const mcpManager = MCPManager.getInstance();
