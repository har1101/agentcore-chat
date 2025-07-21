from strands import Agent
from bedrock_agentcore import BedrockAgentCoreApp
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient
import logging

# ロギング設定をDEBUGレベルに設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = BedrockAgentCoreApp()

# MCPクライアントを作成（セッション管理は各リクエストで行う）
def create_mcp_client():
    return MCPClient(lambda: streamablehttp_client("https://knowledge-mcp.global.api.aws"))

@app.entrypoint
async def agent_invocation(payload):
    """Handler for agent invocation with MCP tools"""
    logger.debug(f"Agent invocation started with payload: {payload}")
    user_message = payload.get(
        "prompt", "No prompt found in input, please guide customer to create a json payload with prompt key"
    )
    logger.info(f"Processing user message: {user_message}")
    
    # MCPクライアントのコンテキスト内でエージェント操作を実行
    logger.debug("Creating MCP client")
    mcp_client = create_mcp_client()
    
    with mcp_client:
        logger.debug("MCP client context entered")
        # MCPサーバーからツールを取得
        tools = mcp_client.list_tools_sync()
        
        # 利用可能なツール情報をログ出力
        tool_names = [tool.tool_name for tool in tools] if tools else []
        logger.info(f"Available tools: {tool_names}")
        
        # ツール詳細情報を安全に取得
        tool_details = []
        for tool in tools if tools else []:
            tool_info = {'name': tool.tool_name}
            # descriptionが存在するかチェック
            if hasattr(tool, 'description'):
                tool_info['description'] = tool.description
            else:
                tool_info['description'] = 'No description available'
            # その他の属性も安全に取得
            if hasattr(tool, 'input_schema'):
                tool_info['input_schema'] = str(tool.input_schema)
            tool_details.append(tool_info)
        
        logger.debug(f"Tool details: {tool_details}")
        
        # MCPツールを含むエージェントを作成
        agent = Agent(tools=tools)
        
        # エージェントをストリーミング実行
        logger.debug(f"Starting agent stream for message: {user_message}")
        stream = agent.stream_async(user_message)
        async for event in stream:
            logger.debug(f"Raw event received: {event}")
            logger.debug(f"Event type: {type(event)}, Event data: {event}")
            
            # ツール使用イベントを特別に処理
            if isinstance(event, dict):
                # Strands Agentのツール使用イベントの詳細検出
                event_type = event.get('type', '')
                event_str = str(event).lower()
                
                # 具体的なツール名を抽出する試み
                tool_name = None
                
                # 1. 直接的なツール名の検出
                if event_type == 'tool_use' or 'tool_use' in event_str:
                    tool_name = event.get('name', event.get('tool_name', event.get('function_name', None)))
                
                # 2. toolオブジェクトからの抽出
                elif 'tool' in event and isinstance(event['tool'], dict):
                    tool_obj = event['tool']
                    tool_name = tool_obj.get('name', tool_obj.get('tool_name', tool_obj.get('function', None)))
                
                # 3. AWS MCP関連の検出
                elif 'aws' in event_str and 'documentation' in event_str:
                    if 'search' in event_str:
                        tool_name = "AWS Documentation Search"
                    elif 'read' in event_str:
                        tool_name = "AWS Documentation Reader"
                    else:
                        tool_name = "AWS Documentation Tool"
                
                # 4. MCP一般的な検出
                elif 'mcp' in event_str and any(keyword in event_str for keyword in ['call', 'invoke', 'execute']):
                    # より具体的な情報を抽出しようと試みる
                    if 'search_documentation' in event_str:
                        tool_name = "Documentation Search"
                    elif 'read_documentation' in event_str:
                        tool_name = "Documentation Reader"
                    elif 'recommend' in event_str:
                        tool_name = "Content Recommender"
                    else:
                        tool_name = "MCP Tool"
                
                # 5. その他のパターン検出
                elif any(keyword in event_str for keyword in ['function_call', 'api_call', 'service_call']):
                    tool_name = "External Service"
                
                # ツール名が見つかった場合のみイベントを送信
                if tool_name and tool_name not in ['Unknown Tool', '']:
                    logger.info(f"Tool detected: {tool_name}")
                    logger.debug(f"Tool event details: {event}")
                    yield {"tool_name": tool_name, "type": "tool_use", "debug_data": event}
            
            # 通常のイベントも送信
            yield (event)

if __name__ == "__main__":
    app.run()
