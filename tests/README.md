# テストスイート

AI けいすけ Bot のスラッシュコマンドをテストするためのテストスイートです。

## テスト内容

### 1. スラッシュコマンドテスト (`test_slash_commands.py`)
- `/help` - ヘルプメッセージ表示
- `/activate` - チャンネル有効化（新規・既存サーバー）
- `/deactivate` - チャンネル無効化
- `/status` - 有効チャンネル一覧表示
- `/stats` - 統計情報表示（オーナー専用）
- 権限チェック（管理者・非管理者）

### 2. カスタムプロンプトテスト (`test_custom_prompts.py`)
- `/set_custom_prompt_x_post` - X投稿用プロンプト設定
- `/set_custom_prompt_article` - 記事作成用プロンプト設定
- モーダル送信処理
- エラーハンドリング

## テスト実行方法

### 1. テスト用依存関係のインストール
```bash
pip install -r test_requirements.txt
```

### 2. テスト実行
```bash
# 個別テスト実行
python -m pytest tests/test_slash_commands.py -v
python -m pytest tests/test_custom_prompts.py -v

# 全テスト実行
python -m pytest tests/ -v

# カバレッジ付きテスト実行
python -m pytest --cov=main --cov-report=term-missing tests/

# 簡単実行スクリプト
python run_tests.py
```

## テスト構造

```
tests/
├── __init__.py              # テストモジュール
├── .gitkeep                 # フォルダ構造維持
├── README.md                # このファイル
├── test_slash_commands.py   # スラッシュコマンドテスト
└── test_custom_prompts.py   # カスタムプロンプトテスト
```

## モックについて

- Discord API: `discord.Interaction`, `discord.User`, `discord.Guild` をモック
- ファイルI/O: `pathlib.Path`, `open()` をモック
- Bot機能: `main.py` の関数をインポートしてテスト

## 注意事項

- テストは実際のDiscord APIを使用しません
- テストデータは一時ディレクトリに保存されます
- 本番環境のデータには影響しません