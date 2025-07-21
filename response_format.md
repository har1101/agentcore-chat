# AgentCore レスポンス形式分析

このドキュメントは、AgentCoreからのストリーミングレスポンスの詳細な形式を説明します。実際のレスポンスデータ（`agentcore_response_6ce9ce98.json`）を基に分析しています。

## 基本構造

AgentCoreのレスポンスは`text/event-stream`形式で送信され、各行は以下の形式になります：

```
data: {JSON_OBJECT}
```

## イベントタイプ別詳細

### 1. 初期化イベント

```json
data: {"init_event_loop": true}
data: {"start": true}
data: {"start_event_loop": true}
```

### 2. メッセージ開始イベント

```json
data: {"event": {"messageStart": {"role": "assistant"}}}
```

### 3. テキストストリーミング（contentBlockDelta）

```json
data: {"event": {"contentBlockDelta": {"delta": {"text": "Bedrock Agent"}, "contentBlockIndex": 0}}}
```

**特徴：**
- `contentBlockIndex`: テキストブロックのインデックス（通常0から開始）
- `delta.text`: 追加されるテキスト片
- 連続するイベントでテキストが段階的に構築される

### 4. Strandsエージェント内部イベント

```json
data: "{'data': 'Bedrock Agent', 'delta': {'text': 'Bedrock Agent'}, 'agent': <strands.agent.agent.Agent object at 0xffff8a4eb230>, 'event_loop_cycle_id': UUID('ffe68ef9-dc65-4d6d-90f1-303202bd0c99'), 'request_state': {}, 'event_loop_cycle_trace': <strands.telemetry.metrics.Trace object at 0xffff88b51160>, 'event_loop_cycle_span': _Span(name=\"execute_event_loop_cycle\", context=SpanContext(trace_id=0x687b4c40a83ec90e8ca9d690ba5d5c72, span_id=0x869003b7115ed777, trace_flags=0x01, trace_state=[], is_remote=False))}"
```

**特徴：**
- Strandsエージェントの内部状態情報
- `event_loop_cycle_id`: イベントループサイクルの一意識別子
- `event_loop_cycle_trace`: OpenTelemetryトレース情報
- Pythonオブジェクトの文字列表現が含まれる

### 5. メッセージ停止イベント（ツール使用時）

```json
data: {"event": {"messageStop": {"stopReason": "tool_use"}}}
```

### 6. メタデータイベント（使用量と性能情報）

```json
data: {"event": {"metadata": {"usage": {"inputTokens": 1643, "outputTokens": 117, "totalTokens": 1760}, "metrics": {"latencyMs": 2617}}}}
```

**含まれる情報：**
- `usage`: トークン使用量統計
  - `inputTokens`: 入力トークン数
  - `outputTokens`: 出力トークン数
  - `totalTokens`: 総トークン数
- `metrics`: 性能メトリクス
  - `latencyMs`: レスポンス時間（ミリ秒）

### 7. ツール使用イベント（Strandsエージェント生成）

```json
data: {"tool_name": "AWS Documentation Search", "type": "tool_use", "debug_data": {"message": {"role": "assistant", "content": [{"text": "..."}, {"toolUse": {"toolUseId": "tooluse_NHP8c04pTzWPVL0iGUHDhA", "name": "aws___search_documentation", "input": {"search_phrase": "Bedrock AgentCore", "limit": 10}}}]}}}
```

**特徴：**
- Strandsエージェントによって生成される独自のツール検出イベント
- `tool_name`: 人間が読みやすいツール名
- `debug_data.message.content`: toolUseオブジェクトを含む配列

### 8. 完全メッセージイベント（ツール使用含む）

```json
data: {"message": {"role": "assistant", "content": [{"text": "..."}, {"toolUse": {"toolUseId": "tooluse_NHP8c04pTzWPVL0iGUHDhA", "name": "aws___search_documentation", "input": {"search_phrase": "Bedrock AgentCore", "limit": 10}}}]}}
```

**重要：** これがツール検出の主要パターンです。

**構造詳細：**
- `message.role`: 常に"assistant"
- `message.content`: 配列形式
  - `{text: "..."}`: テキストコンテンツ
  - `{toolUse: {...}}`: ツール使用オブジェクト
    - `toolUseId`: ツール呼び出しの一意識別子
    - `name`: 実際のツール名（例：`aws___search_documentation`）
    - `input`: ツールへの入力パラメータ

## ツール使用の検出パターン

### パターン1: `message.content`配列内のtoolUseオブジェクト（推奨）

```javascript
if (data.message && data.message.content) {
  for (const content of data.message.content) {
    if (content.toolUse) {
      const toolName = content.toolUse.name;
      const toolId = content.toolUse.toolUseId;
      const input = content.toolUse.input;
      // ツール使用を処理
    }
  }
}
```

### パターン2: Strandsエージェント生成イベント

```javascript
if (data.tool_name && data.type === "tool_use") {
  const toolName = data.tool_name;
  const debugData = data.debug_data;
  // ツール使用を処理
}
```

## AWS MCPツールの識別

AWS Knowledge MCPツールは以下のパターンで識別できます：

- `aws___search_documentation`: 🔍 AWS Documentation Search
- `aws___read_documentation`: 📖 AWS Documentation Reader  
- `aws___recommend`: 💡 AWS Documentation Recommendations

## レスポンス処理のベストプラクティス

### 1. イベント分類

```javascript
if (data.event) {
  if (data.event.contentBlockDelta) {
    // テキストストリーミング
    const text = data.event.contentBlockDelta.delta.text;
  } else if (data.event.messageStop) {
    // メッセージ終了
    const stopReason = data.event.messageStop.stopReason;
  } else if (data.event.metadata) {
    // メタデータ（使用量・性能）
    const usage = data.event.metadata.usage;
  }
} else if (data.message) {
  // 完全メッセージ（ツール使用検出に重要）
  // Pattern 1の処理を実行
} else if (data.tool_name) {
  // Strandsエージェント生成のツールイベント
  // Pattern 2の処理を実行
}
```

### 2. エラーハンドリング

```javascript
try {
  const parsed = JSON.parse(jsonString);
  // 処理
} catch (e) {
  // 非JSONデータやエラーの処理
  if (jsonString.includes("'MCPAgentTool' object")) {
    // 既知のエラーパターン
  }
}
```

### 3. パフォーマンス考慮

- `contentBlockDelta`イベントは頻繁に発生するため、効率的な文字列結合を使用
- `event_loop_cycle_trace`などの大きなオブジェクトはログ出力時に注意
- ツール検出は`message.content`配列をチェックするだけで十分

## 実装例（Streamlit）

```python
def process_agentcore_response(data):
    if isinstance(data, dict):
        # ツール使用検出（メインパターン）
        if 'message' in data and 'content' in data['message']:
            for content in data['message']['content']:
                if 'toolUse' in content:
                    tool_use = content['toolUse']
                    tool_name = tool_use.get('name', 'Unknown Tool')
                    
                    # AWS MCPツールの識別
                    if tool_name.startswith('aws___'):
                        if 'search_documentation' in tool_name:
                            return ('tool_use', "🔍 AWS Documentation Search")
                        elif 'read_documentation' in tool_name:
                            return ('tool_use', "📖 AWS Documentation Reader")
                        # ...
        
        # テキストストリーミング
        elif 'event' in data and 'contentBlockDelta' in data['event']:
            text = data['event']['contentBlockDelta'].get('delta', {}).get('text', '')
            if text:
                return ('text', text)
        
        # Strandsツールイベント
        elif 'tool_name' in data and data.get('type') == 'tool_use':
            return ('tool_use', f"🔧 {data['tool_name']}")
    
    return None
```

## 注意事項

1. **文字エンコーディング**: Unicode文字（日本語など）は`\u`エスケープされて送信される
2. **JSON vs 文字列**: 一部のイベント（Strands内部）は文字列として送信される
3. **順序**: `messageStop`イベントの後に`message`イベントが送信される
4. **タイミング**: ツール使用検出は`message.content`配列のチェックが最も確実