# 🤖 AI けいすけ Bot

Discord上でAI機能を提供するBotです。リアクションベースの直感的な操作で、X投稿生成、音声文字起こし、AI解説、褒めメッセージ生成、Obsidianメモ作成などの機能を利用できます。

## ✨ 機能概要

- 👍 **X投稿生成**: メッセージをX（旧Twitter）投稿用に最適化
- 🎤 **音声文字起こし**: 音声ファイルをテキストに変換
- ❓ **AI解説**: 投稿内容について詳しく解説
- ❤️ **褒めメッセージ**: 投稿を熱烈に褒める画像付きメッセージ
- ✏️ **メモ作成**: 投稿をObsidian用Markdownメモとして保存

## 🎯 プラン比較

| 機能 | 無料プラン | プレミアムプラン |
|------|------------|------------------|
| リアクション機能 | 1日5回まで | 無制限 |
| AIモデル | GPT-4.1-mini | GPT-4.1 |
| カスタムプロンプト | ✅ | ✅ |
| 音声文字起こし | ✅ | ✅ |

## 🚀 クイックスタート（Bot招待）

1. **Botをサーバーに招待**
   - [公式サイト](https://ai-keisuke-bot.github.io/)からBotを招待
   
2. **チャンネルを有効化**
   ```
   /activate
   ```
   
3. **機能を使用**
   - メッセージにリアクション（👍🎤❓❤️✏️）を付けるだけ！

## 🛠️ 開発者向けセットアップ

### 必要な環境

- Python 3.8以上
- Discord Bot Token
- OpenAI API Key
- FFmpeg（音声処理用）

### インストール手順

#### 1. リポジトリの準備
```bash
git clone https://github.com/tejastice/ai-keisuke.git
cd ai-keisuke
```

#### 2. Python仮想環境の作成と有効化
**仮想環境作成:**
```bash
python -m venv ai-keisuke-env
```

**仮想環境の有効化:**
```bash
# macOS/Linux
source ai-keisuke-env/bin/activate

# Windows
ai-keisuke-env\Scripts\activate
```

#### 3. 依存関係のインストール
```bash
pip install -r requirements.txt
```

#### 4. FFmpegのインストール
**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
[FFmpeg公式サイト](https://ffmpeg.org/download.html)からダウンロードしてPATHに追加

#### 5. 環境変数の設定
`.env`ファイルを作成:
```env
DISCORD_BOT_TOKEN=your_discord_bot_token_here
OPENAI_API_KEY=your_openai_api_key_here
```

#### 6. Discord Bot設定

**Discord Developer Portal設定:**
1. [Discord Developer Portal](https://discord.com/developers/applications)でアプリケーション作成
2. **Bot設定:**
   - Server Members Intent を有効化
   - Message Content Intent を有効化
3. **OAuth2設定:**
   ```
   Scopes: bot, applications.commands
   Bot Permissions: 274878286912
   ```

**必要な権限:**
- Send Messages
- Attach Files  
- Read Message History
- Add Reactions
- Use Slash Commands
- View Channels

#### 7. プレミアム機能設定

`settings.json`を設定:
```json
{
  "community_server_id": "YOUR_COMMUNITY_SERVER_ID",
  "premium_role_id": "YOUR_PREMIUM_ROLE_ID", 
  "free_user_daily_limit": 5
}
```

## 📂 ディレクトリ構造

```
ai-keisuke/
├── main.py                 # メインプログラム
├── .env                    # 環境変数（要作成）
├── settings.json           # Bot設定
├── requirements.txt        # 依存パッケージ
├── log.txt                # ログファイル
├── data/                  # データ保存
│   ├── server_data/       # サーバー設定
│   └── user_data/         # ユーザー設定
├── prompt/                # AIプロンプト
│   ├── x_post.txt
│   ├── question_explain.txt
│   ├── heart_praise.txt
│   └── pencil_memo.txt
├── images_homehome/       # 褒め画像背景
└── attachments/           # 一時ファイル
```

## 🚀 起動方法

### 1. 仮想環境の有効化
**毎回Bot起動前に仮想環境を有効化してください：**
```bash
# macOS/Linux
source ai-keisuke-env/bin/activate

# Windows
ai-keisuke-env\Scripts\activate
```

### 2. Botの実行

#### 手動実行
```bash
python main.py
```

#### 自動実行スクリプト（推奨）
**Windows:**
```cmd
ai-keisuke.bat       # 日本語版
start-en.bat         # 英語版（文字化け対策）
```

**macOS/Linux:**
```bash
./run.sh
```

これらのスクリプトは以下を自動で行います：
- 仮想環境の存在確認
- .envファイルの存在確認
- 仮想環境の有効化
- 依存関係のインストール
- Bot実行

### 3. 仮想環境の終了（作業終了時）
```bash
deactivate
```

## 🎮 使い方

### コマンド一覧

| コマンド | 権限 | 説明 |
|----------|------|------|
| `/help` | 全員 | ヘルプメッセージ表示 |
| `/activate` | 管理者 | チャンネル有効化 |
| `/deactivate` | 管理者 | チャンネル無効化 |
| `/status` | 管理者 | 有効チャンネル一覧 |
| `/set_custom_prompt_x_post` | 全員 | カスタムプロンプト設定 |

### リアクション機能

有効化されたチャンネルで以下のリアクションを使用:

- 👍 **X投稿生成**: メッセージをX用に要約
- 🎤 **音声文字起こし**: 音声ファイルをテキスト化
- ❓ **AI解説**: 投稿内容を詳しく解説
- ❤️ **褒めメッセージ**: 画像付きで熱烈に褒める
- ✏️ **メモ作成**: Obsidian用Markdownファイル生成

### カスタムプロンプト

ユーザーごとにX投稿生成のプロンプトをカスタマイズ可能:
```
/set_custom_prompt_x_post
```

## ⚙️ 設定ファイル

### settings.json
```json
{
  "community_server_id": "1383696841450721442",
  "premium_role_id": "1384008198020661278",
  "free_user_daily_limit": 5
}
```

### ユーザーデータ（自動生成）
```json
{
  "user_id": "399123569843372032",
  "username": "ユーザー名",
  "custom_prompt_x_post": "カスタムプロンプト",
  "status": "premium",
  "last_used_date": "2025-06-16",
  "daily_usage_count": 8
}
```

## 🔧 プレミアム機能

### 自動プレミアム判定
- **Discord ロールベース**: コミュニティサーバーのロールで自動判定
- **リアルタイム**: 各機能実行時に即座にチェック
- **自動更新**: プレミアムステータスが自動的にユーザーデータに反映

### プレミアム設定手順
1. ユーザーをコミュニティサーバーに招待
2. プレミアムロールを付与
3. 次回のBot使用時に自動的にプレミアムとして認識

## 🚨 トラブルシューティング

### Botが反応しない
1. `/activate`でチャンネル有効化済みか確認
2. Bot権限（Members Intent含む）を確認
3. `.env`ファイルのトークンを確認
4. `log.txt`でエラーログを確認

### Windows文字化け問題
Windowsで`ai-keisuke.bat`の日本語が文字化けする場合：
1. バッチファイルをShift-JISエンコーディングで保存し直す
2. または、英語版の起動スクリプトを使用する
3. コマンドプロンプトで`chcp 65001`を実行してからバッチファイルを実行

### プレミアム判定が効かない
1. ユーザーがコミュニティサーバーに参加済みか確認
2. プレミアムロールが正しく付与されているか確認
3. BotがユーザーのロールよりDown位にあるか確認（Discord階層制限）
4. `settings.json`の`premium_role_id`が正しいか確認

### 日本語ファイル名について
Discord Botの仕様により、日本語ファイル名は自動的に英語に変換されます。ファイル内容には影響ありません。

### 音声文字起こしエラー
1. FFmpegがインストール済みか確認
2. 対応形式（mp3, m4a, ogg, webm, wav）か確認
3. ファイルサイズが25MB以下か確認

## 📋 システム要件

- **Python**: 3.8以上
- **メモリ**: 512MB以上推奨
- **ストレージ**: 100MB以上（ログ・データ用）
- **ネットワーク**: Discord API・OpenAI APIへのアクセス

## 🔐 セキュリティ

- APIキーは`.env`ファイルで管理
- ユーザーデータは暗号化なしでローカル保存
- プライベートサーバーでの運用を推奨

## 📊 制限事項

- **OpenAI API**: 使用量に応じた課金
- **Discord API**: レート制限あり
- **ファイルサイズ**: Discord制限（25MB）に準拠
- **プレミアム判定**: Botより上位ロールのユーザーは判定不可

## 🌐 関連リンク

- [公式サイト](https://ai-keisuke-bot.github.io/)
- [サポートサーバー](https://discord.gg/7b5g3RbjYv)
- [プライバシーポリシー](https://ai-keisuke-bot.github.io/privacy.html)

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は[LICENSE](LICENSE)ファイルを参照してください。

---

**🚀 今すぐ試す**: [公式サイト](https://ai-keisuke-bot.github.io/)からBotを招待してDiscordサーバーで体験！