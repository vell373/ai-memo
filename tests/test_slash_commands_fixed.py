"""
Discord Bot スラッシュコマンドのテストスイート（修正版）
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


class TestSlashCommandsFixed(unittest.IsolatedAsyncioTestCase):
    """スラッシュコマンドのテストクラス（修正版）"""
    
    def setUp(self):
        """テスト前の準備"""
        # Mock Discord objects
        self.mock_guild = MagicMock(spec=discord.Guild)
        self.mock_guild.id = 12345
        self.mock_guild.name = "Test Guild"
        
        self.mock_user = MagicMock(spec=discord.Member)
        self.mock_user.id = 67890
        self.mock_user.name = "TestUser"
        self.mock_user.guild_permissions = MagicMock()
        self.mock_user.guild_permissions.administrator = True
        
        self.mock_interaction = AsyncMock(spec=discord.Interaction)
        self.mock_interaction.guild = self.mock_guild
        self.mock_interaction.user = self.mock_user
        self.mock_interaction.channel = MagicMock()
        self.mock_interaction.channel.id = 98765
        self.mock_interaction.response.send_message = AsyncMock()
        
        # Temporary directory for test data
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """テスト後のクリーンアップ"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.exists')
    async def test_help_functionality(self, mock_exists, mock_file):
        """helpコマンドの機能テスト（直接関数呼び出し）"""
        # プロンプトファイルの存在をモック
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = "テスト用プロンプト"
        
        # main.pyからBot取得関数をインポート
        from main import bot
        
        # helpコマンドを直接実行
        help_command_func = None
        for command in bot.tree.get_commands():
            if command.name == "help":
                help_command_func = command.callback
                break
        
        if help_command_func:
            await help_command_func(self.mock_interaction)
            
            # レスポンスが送信されたことを確認
            self.mock_interaction.response.send_message.assert_called_once()
            
            # 呼び出し引数を取得
            call_args = self.mock_interaction.response.send_message.call_args
            
            # embedが含まれていることを確認
            self.assertIn('embed', call_args.kwargs)
            embed = call_args.kwargs['embed']
            self.assertIsInstance(embed, discord.Embed)

    async def test_server_data_functions(self):
        """サーバーデータ関連の関数テスト"""
        from main import save_server_data, load_server_data
        
        # テスト用データ
        test_server_id = "12345"
        test_data = {
            "server_id": test_server_id,
            "active_channel_ids": ["98765", "11111"]
        }
        
        with patch('main.script_dir', Path(self.temp_dir)):
            # データ保存テスト
            save_server_data(test_server_id, test_data)
            
            # データ読み込みテスト
            loaded_data = load_server_data(test_server_id)
            
            self.assertEqual(loaded_data["server_id"], test_server_id)
            self.assertIn("98765", loaded_data["active_channel_ids"])
            self.assertIn("11111", loaded_data["active_channel_ids"])

    async def test_user_data_functions(self):
        """ユーザーデータ関連の関数テスト"""
        from main import save_user_data, load_user_data
        
        # テスト用データ
        test_user_id = "67890"
        test_data = {
            "user_id": test_user_id,
            "username": "TestUser",
            "status": "premium",
            "custom_prompt_x_post": "テスト用プロンプト"
        }
        
        with patch('main.script_dir', Path(self.temp_dir)):
            # データ保存テスト
            save_user_data(test_user_id, test_data)
            
            # データ読み込みテスト
            loaded_data = load_user_data(test_user_id)
            
            self.assertEqual(loaded_data["user_id"], test_user_id)
            self.assertEqual(loaded_data["username"], "TestUser")
            self.assertEqual(loaded_data["status"], "premium")
            self.assertEqual(loaded_data["custom_prompt_x_post"], "テスト用プロンプト")

    async def test_channel_active_check(self):
        """チャンネル有効性チェック関数のテスト"""
        from main import is_channel_active
        
        test_server_data = {
            "server_id": "12345",
            "active_channel_ids": ["98765", "11111"]
        }
        
        with patch('main.load_server_data', return_value=test_server_data):
            # 有効なチャンネル
            self.assertTrue(is_channel_active("12345", "98765"))
            self.assertTrue(is_channel_active("12345", "11111"))
            
            # 無効なチャンネル
            self.assertFalse(is_channel_active("12345", "99999"))

    @patch('main.script_dir')
    async def test_stats_manager_functionality(self, mock_script_dir):
        """統計管理機能のテスト"""
        from main import StatsManager
        
        # StatsManagerのインスタンス作成
        stats_manager = StatsManager()
        
        with patch('pathlib.Path.mkdir'), \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('pathlib.Path.exists', return_value=False):
            
            # ユーザーアクティビティ記録テスト
            await stats_manager.record_user_activity("12345")
            
            # ファイルが書き込まれることを確認
            mock_file.assert_called()

    async def test_premium_check_logic(self):
        """プレミアムチェックロジックのテスト"""
        from main import check_premium_status
        
        # モックのコミュニティサーバー
        mock_guild = MagicMock()
        mock_guild.owner_id = 67890
        mock_guild.name = "Community Server"
        mock_guild.get_member.return_value = None
        
        with patch('main.bot') as mock_bot:
            mock_bot.get_guild.return_value = mock_guild
            
            with patch('main.settings_path.exists', return_value=True):
                settings_data = {
                    "community_server_id": "12345",
                    "premium_role_id": "98765",
                    "owner_user_id": "67890"
                }
                
                with patch('builtins.open', mock_open(read_data=json.dumps(settings_data))):
                    # オーナーのプレミアムステータスチェック
                    result = await check_premium_status("67890")
                    self.assertTrue(result)
                    
                    # 非オーナーのプレミアムステータスチェック
                    result = await check_premium_status("99999")
                    self.assertFalse(result)


class TestSlashCommandIntegration(unittest.IsolatedAsyncioTestCase):
    """統合テスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.mock_interaction = AsyncMock(spec=discord.Interaction)
        self.mock_guild = MagicMock(spec=discord.Guild)
        self.mock_guild.id = 12345
        self.mock_user = MagicMock(spec=discord.Member)
        self.mock_user.id = 67890
        self.mock_user.guild_permissions = MagicMock()
        self.mock_user.guild_permissions.administrator = True
        
        self.mock_interaction.guild = self.mock_guild
        self.mock_interaction.user = self.mock_user
        self.mock_interaction.channel = MagicMock()
        self.mock_interaction.channel.id = 98765
        self.mock_interaction.response.send_message = AsyncMock()

    async def test_bot_command_registration(self):
        """Botにコマンドが正しく登録されているかテスト"""
        from main import bot
        
        expected_commands = [
            "help", "activate", "deactivate", "status", "stats",
            "set_custom_prompt_x_post", "set_custom_prompt_article"
        ]
        
        registered_commands = [cmd.name for cmd in bot.tree.get_commands()]
        
        for expected_cmd in expected_commands:
            self.assertIn(expected_cmd, registered_commands, 
                         f"Command '{expected_cmd}' is not registered")

    @patch('main.script_dir')
    async def test_workflow_activate_to_status(self, mock_script_dir):
        """activate → statusの一連の流れをテスト"""
        from main import bot
        
        # activateコマンドを取得
        activate_cmd = None
        status_cmd = None
        
        for command in bot.tree.get_commands():
            if command.name == "activate":
                activate_cmd = command.callback
            elif command.name == "status":
                status_cmd = command.callback
        
        if activate_cmd and status_cmd:
            with patch('main.load_server_data', return_value=None), \
                 patch('main.save_server_data') as mock_save:
                
                # 1. activateコマンド実行
                await activate_cmd(self.mock_interaction)
                
                # save_server_dataが呼ばれることを確認
                mock_save.assert_called_once()
                
                # 保存されるデータを取得
                save_call_args = mock_save.call_args
                saved_data = save_call_args[0][1]
                
                # 2. statusコマンド実行（保存されたデータを使用）
                self.mock_interaction.response.send_message.reset_mock()
                
                with patch('main.load_server_data', return_value=saved_data), \
                     patch('main.bot') as mock_bot:
                    
                    # Mock channel
                    mock_channel = MagicMock()
                    mock_channel.name = "test-channel"
                    mock_bot.get_channel.return_value = mock_channel
                    
                    await status_cmd(self.mock_interaction)
                    
                    # statusコマンドのレスポンスを確認
                    self.mock_interaction.response.send_message.assert_called_once()


if __name__ == '__main__':
    unittest.main()