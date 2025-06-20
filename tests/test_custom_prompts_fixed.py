"""
カスタムプロンプト関連のテスト（修正版）
"""
import unittest
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from pathlib import Path
import sys
import json

# テスト対象のmain.pyをインポートするためのパス設定
sys.path.insert(0, str(Path(__file__).parent.parent))

import discord


class TestCustomPromptFixed(unittest.IsolatedAsyncioTestCase):
    """カスタムプロンプト機能のテスト（修正版）"""
    
    def setUp(self):
        """テスト前の準備"""
        self.mock_interaction = AsyncMock(spec=discord.Interaction)
        self.mock_user = MagicMock(spec=discord.Member)
        self.mock_user.id = 67890
        self.mock_user.name = "TestUser"
        self.mock_interaction.user = self.mock_user
        self.mock_interaction.response.send_modal = AsyncMock()
        self.mock_interaction.response.send_message = AsyncMock()
        
        # Temporary directory for test data
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """テスト後のクリーンアップ"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    async def test_custom_prompt_commands_registration(self):
        """カスタムプロンプトコマンドの登録確認"""
        from main import bot
        
        expected_commands = [
            "set_custom_prompt_x_post",
            "set_custom_prompt_article"
        ]
        
        registered_commands = [cmd.name for cmd in bot.tree.get_commands()]
        
        for expected_cmd in expected_commands:
            self.assertIn(expected_cmd, registered_commands, 
                         f"Command '{expected_cmd}' is not registered")

    async def test_custom_prompt_modal_classes(self):
        """カスタムプロンプトモーダルクラスのテスト"""
        from main import CustomPromptModal, CustomArticlePromptModal
        
        # X投稿用モーダル
        x_post_modal = CustomPromptModal()
        self.assertEqual(x_post_modal.title, "X投稿用カスタムプロンプト設定")
        self.assertTrue(hasattr(x_post_modal, 'prompt_input'))
        
        # 記事作成用モーダル
        article_modal = CustomArticlePromptModal()
        self.assertEqual(article_modal.title, "記事作成用カスタムプロンプト設定")
        self.assertTrue(hasattr(article_modal, 'prompt_input'))

    @patch('main.load_user_data')
    async def test_custom_prompt_modal_with_existing_data(self, mock_load_user):
        """既存データがある場合のモーダルテスト"""
        from main import CustomPromptModal
        
        # 既存ユーザーデータ
        existing_user_data = {
            "user_id": "67890",
            "username": "TestUser",
            "custom_prompt_x_post": "既存のプロンプト"
        }
        mock_load_user.return_value = existing_user_data
        
        # モーダルを作成
        modal = CustomPromptModal()
        
        # デフォルト値が設定されることを確認
        self.assertIsNotNone(modal.prompt_input.default)

    @patch('main.script_dir')
    @patch('main.save_user_data')
    @patch('main.load_user_data')
    async def test_modal_submit_functionality(self, mock_load_user, mock_save_user, mock_script_dir):
        """モーダル送信機能のテスト"""
        from main import CustomPromptModal
        
        # 新規ユーザー
        mock_load_user.return_value = None
        
        # モーダルのインスタンス作成
        modal = CustomPromptModal()
        modal.prompt_input.value = "新しいカスタムプロンプト"
        
        # on_submitメソッドをテスト
        await modal.on_submit(self.mock_interaction)
        
        # save_user_dataが呼ばれることを確認
        mock_save_user.assert_called_once()
        
        # 保存されるデータの確認
        save_call_args = mock_save_user.call_args
        user_id, user_data = save_call_args[0]
        
        self.assertEqual(user_id, "67890")
        self.assertEqual(user_data["custom_prompt_x_post"], "新しいカスタムプロンプト")

    async def test_custom_prompt_commands_via_bot(self):
        """Botオブジェクト経由でのコマンド実行テスト"""
        from main import bot
        
        # コマンドを取得
        x_post_cmd = None
        article_cmd = None
        
        for command in bot.tree.get_commands():
            if command.name == "set_custom_prompt_x_post":
                x_post_cmd = command.callback
            elif command.name == "set_custom_prompt_article":
                article_cmd = command.callback
        
        # コマンドが存在することを確認
        self.assertIsNotNone(x_post_cmd, "set_custom_prompt_x_post command not found")
        self.assertIsNotNone(article_cmd, "set_custom_prompt_article command not found")
        
        if x_post_cmd:
            with patch('main.load_user_data', return_value=None):
                # X投稿コマンド実行
                await x_post_cmd(self.mock_interaction)
                
                # モーダルが送信されることを確認
                self.mock_interaction.response.send_modal.assert_called()

    async def test_user_data_integration(self):
        """ユーザーデータ統合テスト"""
        from main import save_user_data, load_user_data
        
        # テスト用データ
        test_user_id = "67890"
        test_data = {
            "user_id": test_user_id,
            "username": "TestUser",
            "custom_prompt_x_post": "X投稿用プロンプト",
            "custom_prompt_article": "記事作成用プロンプト",
            "status": "free"
        }
        
        with patch('main.script_dir', Path(self.temp_dir)):
            # データ保存
            save_user_data(test_user_id, test_data)
            
            # データ読み込み
            loaded_data = load_user_data(test_user_id)
            
            # カスタムプロンプトが正しく保存・読み込みされることを確認
            self.assertEqual(loaded_data["custom_prompt_x_post"], "X投稿用プロンプト")
            self.assertEqual(loaded_data["custom_prompt_article"], "記事作成用プロンプト")

    @patch('main.script_dir')
    async def test_modal_empty_submit(self, mock_script_dir):
        """空のプロンプト送信テスト"""
        from main import CustomPromptModal
        
        # モーダルのインスタンス作成
        modal = CustomPromptModal()
        modal.prompt_input.value = ""  # 空の値
        
        with patch('main.load_user_data', return_value=None):
            # on_submitメソッドをテスト
            await modal.on_submit(self.mock_interaction)
            
            # メッセージが送信されることを確認
            self.mock_interaction.response.send_message.assert_called_once()
            
            # デフォルトプロンプトメッセージの確認
            call_args = self.mock_interaction.response.send_message.call_args
            message = call_args[0][0]
            self.assertIn("デフォルト", message)

    async def test_error_handling(self):
        """エラーハンドリングのテスト"""
        from main import CustomPromptModal
        
        # モーダルのインスタンス作成
        modal = CustomPromptModal()
        modal.prompt_input.value = "テストプロンプト"
        
        with patch('main.load_user_data', return_value=None), \
             patch('main.save_user_data', side_effect=Exception("保存エラー")):
            
            # on_submitメソッドをテスト
            await modal.on_submit(self.mock_interaction)
            
            # エラーメッセージが送信されることを確認
            self.mock_interaction.response.send_message.assert_called_once()
            call_args = self.mock_interaction.response.send_message.call_args
            message = call_args[0][0]
            self.assertIn("エラー", message)


class TestCustomPromptWorkflow(unittest.IsolatedAsyncioTestCase):
    """カスタムプロンプトワークフローテスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.mock_interaction = AsyncMock(spec=discord.Interaction)
        self.mock_user = MagicMock(spec=discord.Member)
        self.mock_user.id = 67890
        self.mock_user.name = "TestUser"
        self.mock_interaction.user = self.mock_user
        self.mock_interaction.response.send_modal = AsyncMock()
        self.mock_interaction.response.send_message = AsyncMock()

    async def test_complete_custom_prompt_workflow(self):
        """カスタムプロンプト設定の完全なワークフローテスト"""
        from main import bot, save_user_data, load_user_data
        
        # 1. コマンド実行 → モーダル表示
        x_post_cmd = None
        for command in bot.tree.get_commands():
            if command.name == "set_custom_prompt_x_post":
                x_post_cmd = command.callback
                break
        
        if x_post_cmd:
            with patch('main.load_user_data', return_value=None):
                await x_post_cmd(self.mock_interaction)
                
                # モーダルが送信されることを確認
                self.mock_interaction.response.send_modal.assert_called_once()
                
                # 送信されたモーダルを取得
                modal_call_args = self.mock_interaction.response.send_modal.call_args
                modal = modal_call_args[0][0]
                
                # 2. モーダル送信 → データ保存
                modal.prompt_input.value = "ワークフローテスト用プロンプト"
                
                self.mock_interaction.response.send_message.reset_mock()
                
                with patch('main.save_user_data') as mock_save:
                    await modal.on_submit(self.mock_interaction)
                    
                    # データが保存されることを確認
                    mock_save.assert_called_once()
                    
                    # 成功メッセージが送信されることを確認
                    self.mock_interaction.response.send_message.assert_called_once()


if __name__ == '__main__':
    unittest.main()