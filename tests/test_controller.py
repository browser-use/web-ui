import asyncio
import pdb
import sys
import time

sys.path.append(".")

from dotenv import load_dotenv

load_dotenv()


async def test_mcp_client():
    from src.web_ui.utils.mcp_client import create_tool_param_model, setup_mcp_client_and_tools

    test_server_config = {
        "mcpServers": {
            # "markitdown": {
            #     "command": "docker",
            #     "args": [
            #         "run",
            #         "--rm",
            #         "-i",
            #         "markitdown-mcp:latest"
            #     ]
            # },
            "desktop-commander": {
                "command": "npx",
                "args": ["-y", "@wonderwhy-er/desktop-commander"],
            },
            # "filesystem": {
            #     "command": "npx",
            #     "args": [
            #         "-y",
            #         "@modelcontextprotocol/server-filesystem",
            #         "/Users/xxx/ai_workspace",
            #     ]
            # },
        }
    }

    mcp_client = await setup_mcp_client_and_tools(test_server_config)

    if not mcp_client:
        print("Failed to setup MCP client")
        return

    # Get tools from the client
    mcp_tools = []
    if hasattr(mcp_client, "clients") and hasattr(mcp_client.clients, "items"):
        for _server_name, server_client in mcp_client.clients.items():  # type: ignore[attr-defined]
            tools = await server_client.list_tools()  # type: ignore[attr-defined]
            mcp_tools.extend(tools)
    else:
        # Alternative approach if clients attribute doesn't exist
        try:
            tools = await mcp_client.list_tools()  # type: ignore[attr-defined]
            mcp_tools.extend(tools)
        except Exception as e:
            print(f"Failed to get tools: {e}")
            return

    for tool in mcp_tools:
        tool_param_model = create_tool_param_model(tool)
        print(tool.name)
        print(tool.description)
        try:
            print(tool_param_model.model_json_schema())
        except AttributeError:
            # Fallback for older Pydantic versions
            print(tool_param_model().schema())  # type: ignore[deprecated]
    pdb.set_trace()


async def test_controller_with_mcp():
    from src.web_ui.controller.custom_controller import CustomController

    mcp_server_config = {
        "mcpServers": {
            # "markitdown": {
            #     "command": "docker",
            #     "args": [
            #         "run",
            #         "--rm",
            #         "-i",
            #         "markitdown-mcp:latest"
            #     ]
            # },
            "desktop-commander": {
                "command": "npx",
                "args": ["-y", "@wonderwhy-er/desktop-commander"],
            },
            # "filesystem": {
            #     "command": "npx",
            #     "args": [
            #         "-y",
            #         "@modelcontextprotocol/server-filesystem",
            #         "/Users/xxx/ai_workspace",
            #     ]
            # },
        }
    }

    controller = CustomController()
    await controller.setup_mcp_client(mcp_server_config)
    action_name = "mcp.desktop-commander.execute_command"
    action_info = controller.registry.registry.actions[action_name]
    param_model = action_info.param_model
    print(param_model.model_json_schema())
    params = {"command": "python ./tmp/test.py"}
    validated_params = param_model(**params)
    ActionModel_ = controller.registry.create_action_model()
    # Create ActionModel instance with the validated parameters
    action_model = ActionModel_(**{action_name: validated_params})
    result = await controller.act(action_model)
    result = result.extracted_content
    print(result)
    if (
        result
        and "Command is still running. Use read_output to get more output." in result
        and "PID" in result.split("\n")[0]
    ):
        pid = int(result.split("\n")[0].split("PID")[-1].strip())
        action_name = "mcp.desktop-commander.read_output"
        action_info = controller.registry.registry.actions[action_name]
        param_model = action_info.param_model
        print(param_model.model_json_schema())
        params = {"pid": pid}
        validated_params = param_model(**params)
        action_model = ActionModel_(**{action_name: validated_params})
        output_result = ""
        while True:
            time.sleep(1)
            result = await controller.act(action_model)
            result = result.extracted_content
            if result:
                pdb.set_trace()
                output_result = result
                break
        print(output_result)
        pdb.set_trace()
    await controller.close_mcp_client()
    pdb.set_trace()


if __name__ == "__main__":
    # asyncio.run(test_mcp_client())
    asyncio.run(test_controller_with_mcp())
