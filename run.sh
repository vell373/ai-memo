#!/bin/bash
# AI けいすけ Bot 起動スクリプト (macOS/Linux)
# このスクリプトは仮想環境を自動的に有効化してBotを実行します

echo "=============================="
echo "  AI けいすけ Bot 起動中..."
echo "=============================="

# スクリプトのディレクトリに移動
cd "$(dirname "$0")"

# 仮想環境が存在するかチェック
if [ ! -f "ai-keisuke-env/bin/activate" ]; then
    echo "[エラー] 仮想環境が見つかりません。"
    echo "自動的に仮想環境を作成します..."
    
    # Pythonコマンドを検出して仮想環境を作成
    if command -v python3 &> /dev/null; then
        python3 -m venv ai-keisuke-env
    elif command -v python &> /dev/null; then
        python -m venv ai-keisuke-env
    else
        echo ""
        echo "[エラー] Pythonが見つかりません。"
        echo "Python 3.8以上をインストールしてください。"
        echo ""
        read -p "Enterキーを押して終了..."
        exit 1
    fi
    
    if [ ! -f "ai-keisuke-env/bin/activate" ]; then
        echo ""
        echo "[エラー] 仮想環境の作成に失敗しました。"
        echo ""
        read -p "Enterキーを押して終了..."
        exit 1
    fi
    echo "[成功] 仮想環境を作成しました！"
fi

# .envファイルが存在するかチェック
if [ ! -f ".env" ]; then
    echo "[エラー] .envファイルが見つかりません。"
    echo "以下の内容で.envファイルを作成してください："
    echo "DISCORD_BOT_TOKEN=your_discord_bot_token_here"
    echo "OPENAI_API_KEY=your_openai_api_key_here"
    echo ""
    read -p "Enterキーを押して終了..."
    exit 1
fi

echo "[情報] 仮想環境を有効化しています..."
source ai-keisuke-env/bin/activate

echo "[情報] 依存関係をチェックしています..."
pip install -r requirements.txt --quiet

echo "[情報] AI けいすけ Bot を起動しています..."
echo "[情報] 終了するには Ctrl+C を押してください"
echo ""
python3 main.py

echo ""
echo "[情報] Bot が終了しました。"
read -p "Enterキーを押して終了..."