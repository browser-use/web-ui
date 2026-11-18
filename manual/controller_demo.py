import asyncio
import pdb
import sys
import time

sys.path.append(".")

from dotenv import load_dotenv

load_dotenv()


async def test_mcp_client():
    from src.utils.mcp_client import setup_mcp_client_and_tools, create_tool_param_model

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
                "args": [
                    "-y",
                    "@wonderwhy-er/desktop-commander"
                ]
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

    mcp_tools, mcp_client = await setup_mcp_client_and_tools(test_server_config)

    for tool in mcp_tools:
        tool_param_model = create_tool_param_model(tool)
        print(tool.name)
        print(tool.description)
        print(tool_param_model.model_json_schema())
    pdb.set_trace()


async def test_controller_with_mcp():
    import os
    from src.controller.custom_controller import CustomController
    from browser_use.controller.registry.views import ActionModel

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
                "args": [
                    "-y",
                    "@wonderwhy-er/desktop-commander"
                ]
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
    params = {"command": f"python ./tmp/test.py"
              }
    validated_params = param_model(**params)
    ActionModel_ = controller.registry.create_action_model()
    # Create ActionModel instance with the validated parameters
    action_model = ActionModel_(**{action_name: validated_params})
    result = await controller.act(action_model)
    result = result.extracted_content
    print(result)
    if result and "Command is still running. Use read_output to get more output." in result and "PID" in \
            result.split("\n")[0]:
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


if __name__ == '__main__':
    # asyncio.run(test_mcp_client())
    asyncio.run(test_controller_with_mcp())
