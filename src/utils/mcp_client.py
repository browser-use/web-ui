import logging
from typing import Dict, List, Optional, Any
from browser_use.mcp import MCPClient
from browser_use import Controller

logger = logging.getLogger(__name__)


class MCPManager:
    """
    Manages multiple MCP server connections using browser-use's native MCP implementation.
    """
    
    def __init__(self):
        self.clients: Dict[str, MCPClient] = {}
        self.connected_servers: List[str] = []
    
    async def setup_mcp_servers(self, mcp_server_config: Dict[str, Any]) -> bool:
        """
        Set up MCP servers from configuration.
        
        Args:
            mcp_server_config: Configuration dict with server definitions
            
        Returns:
            bool: True if setup successful, False otherwise
        """
        try:
            if not mcp_server_config:
                logger.warning("No MCP server configuration provided")
                return False
                
            # Handle nested mcpServers structure
            servers_config = mcp_server_config
            if "mcpServers" in mcp_server_config:
                servers_config = mcp_server_config["mcpServers"]
            
            logger.info(f"Setting up {len(servers_config)} MCP servers...")
            
            # Clear existing clients
            await self.disconnect_all()
            
            # Create and connect clients
            for server_name, server_config in servers_config.items():
                try:
                    command = server_config.get("command")
                    args = server_config.get("args", [])
                    env = server_config.get("env", {})
                    
                    if not command:
                        logger.warning(f"No command specified for MCP server '{server_name}', skipping")
                        continue
                    
                    logger.info(f"Creating MCP client for server '{server_name}' with command: {command}")
                    
                    # Create MCP client
                    client = MCPClient(
                        server_name=server_name,
                        command=command,
                        args=args,
                        env=env
                    )
                    
                    # Connect to the server
                    await client.connect()
                    
                    # Store client
                    self.clients[server_name] = client
                    self.connected_servers.append(server_name)
                    
                    logger.info(f"Successfully connected to MCP server '{server_name}'")
                    
                except Exception as e:
                    logger.error(f"Failed to setup MCP server '{server_name}': {e}", exc_info=True)
                    continue
            
            logger.info(f"Successfully connected to {len(self.connected_servers)} MCP servers: {self.connected_servers}")
            return len(self.connected_servers) > 0
            
        except Exception as e:
            logger.error(f"Failed to setup MCP servers: {e}", exc_info=True)
            return False
    
    def register_tools_to_controller(self, controller: Controller, tool_filter: Optional[List[str]] = None) -> int:
        """
        Register MCP tools to a browser-use controller.
        
        Args:
            controller: Browser-use controller instance
            tool_filter: Optional list of tool names to include (None = all tools)
            
        Returns:
            int: Number of tools registered
        """
        total_tools = 0
        
        try:
            for server_name, client in self.clients.items():
                try:
                    # Register tools with server name prefix
                    client.register_to_controller(
                        controller=controller,
                        tool_filter=tool_filter,
                        prefix=f"mcp_{server_name}_"
                    )
                    
                    # Note: browser-use doesn't provide a direct way to count registered tools
                    # We'll estimate based on successful registration
                    logger.info(f"Registered MCP tools from server '{server_name}' to controller")
                    total_tools += 1  # Increment per server for now
                    
                except Exception as e:
                    logger.error(f"Failed to register tools from MCP server '{server_name}': {e}")
                    continue
            
            logger.info(f"Total MCP servers registered to controller: {total_tools}")
            return total_tools
            
        except Exception as e:
            logger.error(f"Failed to register MCP tools to controller: {e}", exc_info=True)
            return 0
    
    async def disconnect_all(self):
        """Disconnect from all MCP servers."""
        for server_name, client in self.clients.items():
            try:
                await client.disconnect()
                logger.info(f"Disconnected from MCP server '{server_name}'")
            except Exception as e:
                logger.error(f"Error disconnecting from MCP server '{server_name}': {e}")
        
        self.clients.clear()
        self.connected_servers.clear()
    
    def get_connected_servers(self) -> List[str]:
        """Get list of connected server names."""
        return self.connected_servers.copy()
    
    def is_connected(self, server_name: str) -> bool:
        """Check if a specific server is connected."""
        return server_name in self.connected_servers


# Global MCP manager instance
_mcp_manager: Optional[MCPManager] = None


def get_mcp_manager() -> MCPManager:
    """Get or create the global MCP manager instance."""
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = MCPManager()
    return _mcp_manager


async def setup_mcp_client_and_tools(mcp_server_config: Dict[str, Any]) -> MCPManager:
    """
    Compatibility function that sets up MCP servers and returns the manager.
    
    Args:
        mcp_server_config: MCP server configuration dictionary
        
    Returns:
        MCPManager: The MCP manager instance
    """
    manager = get_mcp_manager()
    await manager.setup_mcp_servers(mcp_server_config)
    return manager
