import streamlit as st
import boto3
import json
import uuid
from typing import Generator

# Initialize session state
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'show_tool_usage' not in st.session_state:
    st.session_state.show_tool_usage = True

# Configuration
AGENT_ARN = "arn:aws:bedrock-agentcore:us-east-1:975050047634:runtime/my_strands_agent-366VYQ9G8U"
AWS_REGION = "us-east-1"

# Initialize the Bedrock AgentCore client
@st.cache_resource
def get_agentcore_client():
    return boto3.client('bedrock-agentcore', region_name=AWS_REGION)

def invoke_agent(prompt: str, session_id: str) -> Generator[tuple, None, None]:
    """Invoke the AgentCore agent and yield streaming responses with metadata."""
    client = get_agentcore_client()
    
    # Prepare the payload
    payload = json.dumps({"prompt": prompt}).encode()
    
    try:
        # Invoke the agent
        response = client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_ARN,
            runtimeSessionId=session_id,
            payload=payload
        )
        
        # Process streaming response
        if "text/event-stream" in response.get("contentType", ""):
            # Handle streaming response
            for line in response["response"].iter_lines(chunk_size=10):
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        line = line[6:]
                        
                        # Raw response analysis mode
                        if show_raw_response:
                            yield ('raw', f"RAW LINE: {line}")
                        
                        # Parse the JSON and extract text content
                        try:
                            data = json.loads(line)
                            
                            # Raw data analysis mode
                            if show_raw_response:
                                yield ('raw', f"PARSED DATA: {json.dumps(data, indent=2)}")
                            
                            if isinstance(data, dict):
                                # Check for initialization events
                                if data.get('init_event_loop') or data.get('start') or data.get('start_event_loop'):
                                    yield ('init', data)
                                
                                # Check for message events
                                elif 'event' in data:
                                    event = data['event']
                                    
                                    # Message start
                                    if 'messageStart' in event:
                                        yield ('message_start', event['messageStart'])
                                    
                                    # Text streaming
                                    elif 'contentBlockDelta' in event:
                                        text = event['contentBlockDelta'].get('delta', {}).get('text', '')
                                        if text:
                                            yield ('text', text)
                                    
                                    # Tool use streaming (contentBlockDelta with toolUse)
                                    elif 'contentBlockDelta' in event and 'delta' in event['contentBlockDelta']:
                                        delta = event['contentBlockDelta']['delta']
                                        if 'toolUse' in delta:
                                            # Tool use delta - skip these as they're partial
                                            pass
                                    
                                    # Tool use start (contentBlockStart with toolUse) - this is the main tool event
                                    elif 'contentBlockStart' in event:
                                        start = event['contentBlockStart'].get('start', {})
                                        if 'toolUse' in start:
                                            tool_info = start['toolUse']
                                            yield ('tool_use', {
                                                'name': tool_info.get('name', 'Unknown Tool'),
                                                'id': tool_info.get('toolUseId', ''),
                                                'input': tool_info.get('input', {})
                                            })
                                    
                                    # Content block stop event
                                    elif 'contentBlockStop' in event:
                                        yield ('content_block_stop', event['contentBlockStop'])
                                    
                                    # Message stop
                                    elif 'messageStop' in event:
                                        yield ('message_stop', event['messageStop'])
                                    
                                    # Metadata (usage and metrics)
                                    elif 'metadata' in event:
                                        yield ('metadata', event['metadata'])
                                
                                # Check for Strands Agent tool events
                                elif 'tool_name' in data and data.get('type') == 'tool_use':
                                    yield ('strands_tool', {
                                        'name': data['tool_name'],
                                        'debug_data': data.get('debug_data', {})
                                    })
                                
                                # Strands internal event (contains event loop info)
                                elif 'event_loop_cycle_id' in str(data):
                                    yield ('strands_internal', data)
                                elif 'message' in data and 'content' in data['message']:
                                    # Complete message - only extract toolUse, not text (to avoid duplication)
                                    for content in data['message']['content']:
                                        if 'toolUse' in content:
                                            # Extract tool information from toolUse object
                                            tool_use = content['toolUse']
                                            yield ('tool_use', {
                                                'name': tool_use.get('name', 'Unknown Tool'),
                                                'id': tool_use.get('toolUseId', ''),
                                                'input': tool_use.get('input', {})
                                            })
                                elif 'data' in data and isinstance(data['data'], str):
                                    # Simple text data
                                    yield ('text', data['data'])
                                elif isinstance(data, str):
                                    # Direct text content
                                    yield ('text', data)
                        except json.JSONDecodeError:
                            # Raw response analysis for non-JSON
                            if show_raw_response:
                                yield ('raw', f"NON-JSON LINE: {line}")
                            
                            # Handle Strands internal events that come as strings
                            if "'event_loop_cycle_id'" in line:
                                yield ('strands_internal', line)
                            elif not line.startswith("{'") and not line.startswith('{"'):
                                yield ('text', line)
        
        elif response.get("contentType") == "application/json":
            # Handle standard JSON response
            content = []
            for chunk in response.get("response", []):
                content.append(chunk.decode('utf-8'))
            result = json.loads(''.join(content))
            if isinstance(result, dict) and 'message' in result:
                yield ('text', result['message'])
            else:
                yield ('text', str(result))
        
        else:
            # Yield raw response for other content types
            yield ('text', str(response))
            
    except Exception as e:
        yield ('error', f"Error: {str(e)}")

# Streamlit UI
st.title("🤖 Bedrock AgentCore Chat Interface")

# Session info
with st.sidebar:
    st.header("Session Information")
    st.text(f"Session ID: {st.session_state.session_id[:8]}...")
    
    if st.button("New Session"):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()
    
    st.divider()
    
    # Tool usage settings
    st.header("Display Settings")
    st.session_state.show_tool_usage = st.checkbox(
        "Show tool usage", 
        value=st.session_state.show_tool_usage,
        help="Display when the agent uses MCP tools"
    )
    
    show_debug = st.checkbox(
        "Show debug info", 
        value=False,
        help="Display raw event data for debugging"
    )
    
    show_raw_response = st.checkbox(
        "Show raw response format", 
        value=False,
        help="Display complete raw response structure for analysis"
    )
    
    st.divider()
    st.caption("This app connects to your deployed AgentCore agent")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask your agent anything..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Display assistant response
    with st.chat_message("assistant"):
        # Use a single container for all chronological events
        main_container = st.container()
        full_response = ""
        raw_info = []
        
        # Track events for display
        displayed_tools = {}  # Track displayed tools by ID
        metadata_info = None
        debug_events = []
        thinking_placeholder = None  # Placeholder for thinking status
        active_tool_placeholders = {}  # Track active tool execution status
        message_placeholder = None  # Will be created when text starts
        text_started = False  # Track if text output has started
        
        # Stream the response
        for response_type, response_chunk in invoke_agent(prompt, st.session_state.session_id):
            if response_type == 'init':
                # Initialization events - show agent is starting
                if not thinking_placeholder:
                    with main_container:
                        thinking_placeholder = st.empty()
                thinking_placeholder.info("🚀 エージェントを起動中...", icon="🚀")
                if show_debug:
                    debug_events.append(('🚀 エージェント初期化中...', response_chunk))
            
            elif response_type == 'message_start':
                # Message start event - show thinking status
                if thinking_placeholder:
                    thinking_placeholder.empty()
                with main_container:
                    thinking_placeholder = st.empty()
                thinking_placeholder.info("🤔 思考中...", icon="🤔")
                if show_debug:
                    debug_events.append(('💬 メッセージ開始', response_chunk))
            
            elif response_type == 'tool_use' and st.session_state.show_tool_usage:
                # Tool usage event with details
                tool_data = response_chunk
                tool_id = tool_data.get('id', '')
                tool_name = tool_data['name']
                
                # Skip if we've already displayed this tool
                if tool_id and tool_id in displayed_tools:
                    continue
                
                # Format tool name for display
                if tool_name.startswith('aws___'):
                    # AWS MCP tools
                    if 'search_documentation' in tool_name:
                        display_name = "🔍 AWS Documentation検索を実行中..."
                    elif 'read_documentation' in tool_name:
                        display_name = "📖 AWS Documentationを読み込み中..."
                    elif 'recommend' in tool_name:
                        display_name = "💡 AWS Documentation推奨を取得中..."
                    else:
                        display_name = f"📚 AWS Tool: {tool_name.replace('aws___', '')}を実行中..."
                else:
                    # Other tools
                    display_name = f"🔧 {tool_name}を実行中..."
                
                # Clear thinking status and display the tool
                if thinking_placeholder:
                    thinking_placeholder.empty()
                    thinking_placeholder = None
                
                # Display the tool immediately
                if tool_id:
                    displayed_tools[tool_id] = True
                    with main_container:
                        # Show a progress message for the tool
                        tool_status_placeholder = st.empty()
                        tool_status_placeholder.info(display_name, icon="⏳")
                        active_tool_placeholders[tool_id] = (tool_status_placeholder, display_name)
                        
                        # Show tool details in expander
                        with st.expander(f"📋 {tool_name}の詳細", expanded=False):
                            # Only show input if it has actual content
                            input_data = tool_data.get('input', {})
                            if input_data:
                                st.json({
                                    'tool_name': tool_name,
                                    'tool_id': tool_id,
                                    'input': input_data
                                })
                            else:
                                st.json({
                                    'tool_name': tool_name,
                                    'tool_id': tool_id
                                })
            
            elif response_type == 'strands_tool' and st.session_state.show_tool_usage:
                # Strands tool event
                tool_data = response_chunk
                display_name = f"🔧 {tool_data['name']}を実行中..."
                # Check if already displayed
                tool_key = f"strands_{tool_data['name']}"
                if tool_key not in displayed_tools:
                    displayed_tools[tool_key] = True
                    with main_container:
                        with st.expander(display_name, expanded=False):
                            if tool_data.get('debug_data'):
                                st.json(tool_data['debug_data'])
                            else:
                                st.write(f"Tool: {tool_data['name']}")
            
            elif response_type == 'strands_internal':
                # Strands internal event - show processing status
                if thinking_placeholder:
                    thinking_placeholder.info("⚙️ 内部処理を実行中...", icon="⚙️")
                elif not text_started:
                    with main_container:
                        thinking_placeholder = st.empty()
                    thinking_placeholder.info("⚙️ 内部処理を実行中...", icon="⚙️")
                if show_debug:
                    debug_events.append(('⚙️ 内部処理実行中...', response_chunk))
            
            elif response_type == 'metadata':
                # Store metadata for display at the end
                metadata_info = response_chunk
            
            elif response_type == 'message_stop':
                # Message stop event
                if show_debug:
                    stop_reason = response_chunk.get('stopReason', 'unknown')
                    debug_events.append((f'✅ メッセージ完了 (理由: {stop_reason})', response_chunk))
            
            elif response_type == 'text' and response_chunk.strip():
                # Clear thinking status when text starts
                if thinking_placeholder and not text_started:
                    thinking_placeholder.empty()
                    thinking_placeholder = None
                
                # Create message placeholder if this is the first text
                if not text_started:
                    text_started = True
                    with main_container:
                        message_placeholder = st.empty()
                
                full_response += response_chunk
                # Update the placeholder with the accumulated response
                if message_placeholder:
                    message_placeholder.markdown(full_response + "▌")
            
            elif response_type == 'error':
                st.error(response_chunk)
            
            elif response_type == 'content_block_stop':
                # Content block stopped - could be tool completion
                # Check if this is a tool completion
                if active_tool_placeholders:
                    # Clear the last active tool placeholder and show completion
                    for tool_id, (placeholder, tool_name) in list(active_tool_placeholders.items()):
                        placeholder.success(f"✅ {tool_name}の実行が完了しました", icon="✅")
                        # Remove after a short delay (Streamlit will handle this)
                        del active_tool_placeholders[tool_id]
                        break  # Only process the first one
            
            elif response_type == 'raw' and show_raw_response:
                # Display raw response format analysis
                raw_info.append(response_chunk)
        
        # Display debug events if enabled
        if show_debug and debug_events:
            with main_container:
                with st.expander("🔧 デバッグ情報", expanded=False):
                    for event_name, event_data in debug_events:
                        st.write(f"**{event_name}**")
                        st.json(event_data)
        
        # Display metadata at the end if available
        if metadata_info:
            with main_container:
                with st.expander("📊 使用統計とパフォーマンス", expanded=False):
                    usage = metadata_info.get('usage', {})
                    metrics = metadata_info.get('metrics', {})
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("入力トークン", usage.get('inputTokens', 0))
                        st.metric("出力トークン", usage.get('outputTokens', 0))
                    with col2:
                        st.metric("合計トークン", usage.get('totalTokens', 0))
                        st.metric("レイテンシ", f"{metrics.get('latencyMs', 0)}ms")
        
        # Display raw response analysis if enabled
        if show_raw_response and raw_info:
            with main_container:
                with st.expander("🔍 Raw Response Analysis", expanded=True):
                    for raw_msg in raw_info:
                        st.code(raw_msg, language="json")
        
        # Clear any remaining thinking status
        if thinking_placeholder:
            thinking_placeholder.empty()
        
        # Clear any remaining tool status
        for tool_id, (placeholder, tool_name) in active_tool_placeholders.items():
            placeholder.success(f"✅ {tool_name}の実行が完了しました", icon="✅")
        
        # Remove the cursor by updating with final response (no cursor)
        if full_response and message_placeholder:
            message_placeholder.markdown(full_response)
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": full_response})