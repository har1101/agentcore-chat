# Bedrock AgentCore + Strands Agents 統合プロジェクト

このプロジェクトは、AWS Bedrock AgentCoreとStrands Agents SDKを統合し、高度なAIエージェントアプリケーションを構築するための包括的なソリューションです。

## プロジェクト構成

### 🤖 メインエージェント (`my_strands_agent.py`)
- Strands Agents SDKを使用したAIエージェント実装
- AWS Knowledge MCPツールの統合
- AWS Bedrock AgentCoreとの連携

### 📊 Streamlitインターフェース (`streamlit_app.py`)
- リアルタイムチャットインターフェース
- ツール使用状況の可視化
- 折りたたみ式トレース表示
- デバッグとモニタリング機能

## 主要機能

### エージェント機能
- **AWS Knowledge統合**: AWS公式ドキュメントの検索・読み込み・推奨
- **リアルタイム対話**: ストリーミングレスポンス対応
- **ツール連携**: MCPプロトコル対応の拡張可能なツールシステム

### UI/UX機能
- **🚀 状態表示**: エージェント起動・思考・ツール実行の可視化
- **📋 詳細情報**: 折りたたみ式でツール実行詳細を表示
- **⚙️ デバッグ支援**: 生レスポンス分析とイベント追跡
- **📊 メトリクス**: トークン使用量とレイテンシの監視

## クイックスタート

### 1. 環境構築

```bash
# 依存関係のインストール
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
uv pip install -r streamlit_requirements.txt
```

### 2. AWS設定

```bash
# AWS認証情報の設定
aws configure
```

### 3. エージェントのデプロイ

詳しい手順は以下ブログ参照。
- [Strands Agents SDK×Bedrock AgentCore Runtimeで最先端のAIエージェント開発を楽しもう！](https://qiita.com/har1101/items/73fa749e05c4cb38bb6e)
- [Amazon Bedrock AgentCoreって何？StrandsAgentでLine Bot作ってデプロイしてみよう！](https://qiita.com/Syoitu/items/e85c9d9bd389c987d7bc)

```bash
# エージェントをAgentCoreにデプロイ
# Docker Desktopを起動し、AgentCore用IAMサービスロールを準備しておく
export IAM_ROLE_ARN=<作成したIAMロールのARN>

agentcore configure --entrypoint my_strands_agents.py -er $IAM_ROLE_ARN

agentcore launch
```

### 4. Streamlitアプリの起動

```bash
# UIアプリケーションの起動
streamlit run streamlit_app.py
```

## 技術スタック

- **AWS Bedrock AgentCore**: エンタープライズグレードのAIエージェント基盤
- **Strands Agents SDK**: Pythonベースのエージェント開発フレームワーク
- **AWS Knowledge MCP**: AWS公式ドキュメントアクセスツール
- **Streamlit**: リアルタイムWebインターフェース
- **boto3**: AWS SDK for Python

## アーキテクチャ

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Streamlit UI  │◄──►│ AgentCore        │◄──►│ Strands Agent   │
│                 │    │ Runtime          │    │ + MCP Tools     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
        │                        │                        │
        ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Real-time       │    │ Streaming        │    │ AWS Knowledge   │
│ Monitoring      │    │ Responses        │    │ Base            │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 最新の改善点（2025年版）

### 折りたたみ式トレース表示
- Bedrock Agent Runtime互換のexpander UI実装
- ツール使用時の概要表示 + 詳細情報の展開
- エージェント処理フローの可視化

### リアルタイム状態表示
- **🚀 エージェント起動中**: 初期化プロセスの表示
- **🤔 思考中**: エージェントの推論フェーズ
- **⚙️ 内部処理実行中**: Strands内部ワークフロー
- **⏳ ツール実行中**: MCPツール呼び出し状況
- **✅ 実行完了**: 各処理の完了ステータス

### AgentCoreレスポンス分析
- `response_format.md`: 詳細なレスポンス構造分析
- イベントタイプ別の適切な処理実装
- ツール検出アルゴリズムの高度化

### パフォーマンス最適化
- 重複表示の防止メカニズム
- 効率的なストリーミング処理
- メタデータとメトリクスの可視化

## 使用例

### 基本的な質問応答
```
ユーザー: "AWS Lambdaについて教えて"
🔍 AWS Documentation Search実行中...
✅ AWS Documentation Search完了
📖 AWS Documentation Reader実行中...
✅ AWS Documentation Reader完了
エージェント: "AWS Lambdaはサーバーレスコンピューティングサービスで..."
```

### デバッグモード
```json
{
  "event": {
    "contentBlockStart": {
      "start": {
        "toolUse": {
          "toolUseId": "tooluse_abc123",
          "name": "aws___search_documentation",
          "input": {
            "search_phrase": "AWS Lambda",
            "limit": 10
          }
        }
      }
    }
  }
}
```

## 設定とカスタマイズ

### エージェント設定
- `my_strands_agent.py`: メインエージェントロジック
- MCPツールの追加・削除
- プロンプトテンプレートのカスタマイズ

### UI設定
- `streamlit_app.py`: インターフェース設定
- 表示オプションの調整
- デバッグ機能の有効/無効

## トラブルシューティング

### 一般的な問題
1. **認証エラー**: AWS認証情報の確認
2. **権限エラー**: IAMポリシーの確認
3. **ツール検出失敗**: デバッグモードでイベント分析
4. **レスポンス遅延**: メトリクス監視で原因特定

### デバッグ手順
1. Streamlitの「デバッグ情報を表示」を有効化
2. 「生レスポンス形式を表示」でイベント構造確認
3. `response_format.md`と照合してパターン分析

## ドキュメント

- [`streamlit_README.md`](streamlit_README.md): Streamlitアプリの詳細ドキュメント
- [`response_format.md`](response_format.md): AgentCoreレスポンス形式の分析
