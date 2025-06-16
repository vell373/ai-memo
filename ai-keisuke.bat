@echo off
REM AI けいすけ Bot 起動スクリプト (Windows)
REM このスクリプトは仮想環境を自動的に有効化してBotを実行します

echo ==============================
echo   AI けいすけ Bot 起動中...
echo ==============================

REM スクリプトのディレクトリに移動
cd /d %~dp0

REM 仮想環境が存在するかチェック
if not exist "ai-keisuke-env\Scripts\activate.bat" (
    echo [エラー] 仮想環境が見つかりません。
    echo 以下のいずれかのコマンドで作成できます：
    echo.
    echo   python -m venv ai-keisuke-env
    echo   python3 -m venv ai-keisuke-env
    echo   py -m venv ai-keisuke-env
    echo.
    echo 自動的に仮想環境を作成します...
    
    REM 異なるPythonコマンドを試す
    python -m venv ai-keisuke-env 2>nul
    if not exist "ai-keisuke-env\Scripts\activate.bat" (
        python3 -m venv ai-keisuke-env 2>nul
    )
    if not exist "ai-keisuke-env\Scripts\activate.bat" (
        py -m venv ai-keisuke-env 2>nul
    )
    
    if not exist "ai-keisuke-env\Scripts\activate.bat" (
        echo.
        echo [エラー] 仮想環境の作成に失敗しました。
        echo Python 3.8以上をインストールしてから再度実行してください。
        echo.
        pause
        exit /b 1
    )
    echo [成功] 仮想環境を作成しました！
)

REM .envファイルが存在するかチェック
if not exist ".env" (
    echo [エラー] .envファイルが見つかりません。
    echo 以下の内容で.envファイルを作成してください：
    echo DISCORD_BOT_TOKEN=your_discord_bot_token_here
    echo OPENAI_API_KEY=your_openai_api_key_here
    echo.
    pause
    exit /b 1
)

echo [情報] 仮想環境を有効化しています...
call ai-keisuke-env\Scripts\activate.bat

echo [情報] 依存関係をチェックしています...
pip install -r requirements.txt --quiet

echo [情報] AI けいすけ Bot を起動しています...
echo [情報] 終了するには Ctrl+C を押してください
echo.
python main.py

echo.
echo [情報] Bot が終了しました。
pause