#!/usr/bin/env python3
"""
テスト実行スクリプト
Discord Botのスラッシュコマンドをテストします
"""
import subprocess
import sys
from pathlib import Path

def main():
    """テストを実行"""
    print("🧪 AI けいすけ Bot テストスイート")
    print("=" * 50)
    
    # テストディレクトリの確認
    test_dir = Path(__file__).parent / "tests"
    if not test_dir.exists():
        print("❌ testsディレクトリが見つかりません")
        return 1
    
    # pytest実行
    try:
        print("📋 スラッシュコマンドテストを実行中...")
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/test_slash_commands.py",
            "-v"
        ], cwd=Path(__file__).parent)
        
        if result.returncode != 0:
            print("❌ スラッシュコマンドテストが失敗しました")
            return result.returncode
        
        print("📝 カスタムプロンプトテストを実行中...")
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/test_custom_prompts.py",
            "-v"
        ], cwd=Path(__file__).parent)
        
        if result.returncode != 0:
            print("❌ カスタムプロンプトテストが失敗しました")
            return result.returncode
        
        print("\n✅ すべてのテストが成功しました！")
        print("\n📊 カバレッジレポートを生成中...")
        
        # カバレッジレポート生成（オプション）
        subprocess.run([
            sys.executable, "-m", "pytest",
            "--cov=main",
            "--cov-report=term-missing",
            "tests/"
        ], cwd=Path(__file__).parent)
        
        return 0
        
    except FileNotFoundError:
        print("❌ pytestが見つかりません")
        print("以下のコマンドでインストールしてください:")
        print("pip install -r test_requirements.txt")
        return 1
    except Exception as e:
        print(f"❌ テスト実行中にエラーが発生しました: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())