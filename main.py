import discord
from discord.ext import commands
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import urllib.parse
import requests
from datetime import datetime
import logging
import asyncio
import tempfile
from pydub import AudioSegment
from PIL import Image, ImageDraw, ImageFont
import random
import re
import io

# スクリプトのディレクトリを基準に.envファイルを読み込む
script_dir = Path(__file__).parent
env_path = script_dir / '.env'

# 既存の環境変数をクリアしてから.envファイルを読み込む
if 'OPENAI_API_KEY' in os.environ:
    del os.environ['OPENAI_API_KEY']
if 'DISCORD_BOT_TOKEN' in os.environ:
    del os.environ['DISCORD_BOT_TOKEN']

load_dotenv(env_path, override=True)

# 環境変数からトークンを取得
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# OpenAIモデル設定
FREE_USER_MODEL = "gpt-4.1-mini"
PREMIUM_USER_MODEL = "gpt-4.1"

# テストサーバーID（スラッシュコマンドの即座反映用）
# Botが参加しているサーバーのIDに変更してください
TEST_GUILD_ID = 1383696841450721442  # Botがこのサーバーに招待されている必要があります

# settings.jsonから設定を読み込む
settings_path = script_dir / "settings.json"
if settings_path.exists():
    with open(settings_path, 'r', encoding='utf-8') as f:
        settings = json.load(f)
        FREE_USER_DAILY_LIMIT = settings.get("free_user_daily_limit", 5)
else:
    FREE_USER_DAILY_LIMIT = 5  # デフォルト値

# ログ設定
log_file = script_dir / "log.txt"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()  # コンソールにも出力
    ]
)
logger = logging.getLogger(__name__)

# OpenAIクライアントの初期化
client_openai = None
if OPENAI_API_KEY:
    client_openai = OpenAI(api_key=OPENAI_API_KEY)


# Intentsの設定
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True

# Botの初期化
bot = commands.Bot(command_prefix='!', intents=intents)

def load_server_data(server_id):
    """サーバーデータを読み込む"""
    file_path = script_dir / "data" / "server_data" / f"{server_id}.json"
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def save_server_data(server_id, data):
    """サーバーデータを保存する"""
    data_dir = script_dir / "data" / "server_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    file_path = data_dir / f"{server_id}.json"
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def is_channel_active(server_id, channel_id):
    """チャンネルが有効かどうかをチェック"""
    server_data = load_server_data(server_id)
    if server_data and 'active_channel_ids' in server_data:
        return str(channel_id) in server_data['active_channel_ids']
    return False

def migrate_user_data(user_data, user_id, username):
    """古いユーザーデータを新しいフォーマットにマイグレーション"""
    # 必要なフィールドのデフォルト値
    default_fields = {
        "user_id": str(user_id),
        "username": username,
        "custom_prompt_x_post": "",
        "status": "free",
        "last_used_date": "",
        "daily_usage_count": 0
    }
    
    # 不足しているフィールドを追加
    updated = False
    for field, default_value in default_fields.items():
        if field not in user_data:
            user_data[field] = default_value
            updated = True
            logger.info(f"マイグレーション: ユーザー {user_id} に {field} フィールドを追加")
    
    # 古いフィールド名の変換
    if "custom_x_post_prompt" in user_data:
        user_data["custom_prompt_x_post"] = user_data.pop("custom_x_post_prompt")
        updated = True
        logger.info(f"マイグレーション: ユーザー {user_id} の custom_x_post_prompt を custom_prompt_x_post に変換")
    
    return user_data, updated

def load_user_data(user_id):
    """ユーザーデータを読み込む"""
    file_path = script_dir / "data" / "user_data" / f"{user_id}.json"
    if file_path.exists():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"ユーザーデータ読み込みエラー {user_id}: {e}")
            return None
    return None

def save_user_data(user_id, data):
    """ユーザーデータを保存する"""
    data_dir = script_dir / "data" / "user_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    file_path = data_dir / f"{user_id}.json"
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def is_premium_user(user_id):
    """ユーザーがプレミアムかどうかを判定"""
    try:
        # コミュニティサーバーからユーザー情報を取得
        community_guild = bot.get_guild(int(settings.get("community_server_id")))
        if not community_guild:
            logger.warning(f"Community server not found: {settings.get('community_server_id')}")
            return False
        
        logger.info(f"Debug: Checking user {user_id} in guild {community_guild.name}")
        
        member = community_guild.get_member(int(user_id))
        if not member:
            logger.warning(f"User {user_id} not found in community server {community_guild.name}")
            logger.info(f"Debug: Guild has {community_guild.member_count} members")
            logger.info(f"Debug: This may be due to the user having a role higher than the Bot's role")
            return False
        
        logger.info(f"Debug: Found member {member.name}#{member.discriminator}")
        logger.info(f"Debug: Member roles: {[f'{role.name}({role.id})' for role in member.roles]}")
        
        # プレミアムロールの確認
        premium_role_id = int(settings.get("premium_role_id"))
        logger.info(f"Debug: Looking for premium role ID: {premium_role_id}")
        
        has_premium_role = any(role.id == premium_role_id for role in member.roles)
        
        logger.info(f"Premium check for user {user_id} ({member.name}): {has_premium_role}")
        return has_premium_role
        
    except Exception as e:
        logger.error(f"Error checking premium status for user {user_id}: {e}")
        return False

def can_use_feature(user_data, is_premium):
    """機能使用可能かチェックし、使用回数を更新"""
    today = datetime.now().strftime("%Y-%m-%d")
    
    # プレミアムユーザーは無制限（ただし使用回数はカウント）
    if is_premium:
        last_used_date = user_data.get("last_used_date", "")
        daily_usage_count = user_data.get("daily_usage_count", 0)
        
        # 日付が変わった場合はカウントをリセット
        if last_used_date != today:
            user_data["last_used_date"] = today
            user_data["daily_usage_count"] = 1
        else:
            # 同じ日の場合は使用回数を増加
            user_data["daily_usage_count"] = daily_usage_count + 1
        
        return True, None
    
    # 無料ユーザーの制限チェック
    last_used_date = user_data.get("last_used_date", "")
    daily_usage_count = user_data.get("daily_usage_count", 0)
    
    # 日付が変わった場合はカウントをリセット
    if last_used_date != today:
        user_data["last_used_date"] = today
        user_data["daily_usage_count"] = 1
        return True, None
    
    # 同じ日の場合は制限チェック
    if daily_usage_count >= FREE_USER_DAILY_LIMIT:
        remaining = max(0, FREE_USER_DAILY_LIMIT - daily_usage_count)
        return False, f"❌ 無料プランの1日利用制限（{FREE_USER_DAILY_LIMIT}回）に達しました。\n残り回数: {remaining}回"
    
    # 使用回数を増加
    user_data["daily_usage_count"] = daily_usage_count + 1
    return True, None

def make_praise_image(praise_text):
    """褒めメッセージ画像を生成する"""
    try:
        logger.info(f"画像生成開始: テキスト='{praise_text}'")
        
        # 画像のサイズを指定
        width = 1080
        height = 1520
        
        # 画像の背景色を指定
        background_color = (255, 255, 255)
        
        # 画像を生成
        image = Image.new("RGB", (width, height), background_color)
        logger.info("ベース画像作成完了")
        
        # images_homehomeフォルダの中のjpgファイル一覧を取得
        images_dir = script_dir / "images_homehome"
        logger.info(f"画像フォルダパス: {images_dir}")
        
        if images_dir.exists():
            files = [f for f in os.listdir(images_dir) if f.endswith('.jpg')]
            logger.info(f"見つかった画像ファイル数: {len(files)}")
            
            if files:
                # ランダムに1つ選ぶ
                file = random.choice(files)
                logger.info(f"選択された画像: {file}")
                
                # 画像を開く
                img_path = images_dir / file
                logger.info(f"画像パス: {img_path}")
                img = Image.open(img_path)
                
                # imageに貼り付ける
                image.paste(img, (0, 0))
                logger.info("背景画像貼り付け完了")
            else:
                logger.warning("jpg画像が見つかりませんでした")
        else:
            logger.error(f"画像フォルダが存在しません: {images_dir}")
        
        # フォントを設定（システムフォントを使用）
        try:
            # Macの場合 - より安全なフォントを使用
            font = ImageFont.truetype("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc", 30)
            logger.info("ヒラギノフォント読み込み成功")
        except Exception as e:
            logger.warning(f"ヒラギノフォント読み込み失敗: {e}")
            try:
                # Macの別のフォント
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 30)
                logger.info("Helveticaフォント読み込み成功")
            except Exception as e:
                logger.warning(f"Helveticaフォント読み込み失敗: {e}")
                try:
                    # Windowsの場合
                    font = ImageFont.truetype("C:/Windows/Fonts/msgothic.ttc", 30)
                    logger.info("MSゴシックフォント読み込み成功")
                except Exception as e:
                    logger.warning(f"MSゴシックフォント読み込み失敗: {e}")
                    # デフォルトフォント
                    font = ImageFont.load_default()
                    logger.info("デフォルトフォント使用")
        
        # テキストを処理（絵文字や特殊文字を除去）
        # 絵文字と特殊文字を除去し、ひらがな、カタカナ、漢字、英数字、基本記号のみ残す
        original_text = praise_text
        text = re.sub(r'[^\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF\u0021-\u007E]', '', praise_text)
        text = text.replace("。", "").replace("、", "").replace(" ", "").replace("ー", "┃").replace("\n", "")
        logger.info(f"テキスト処理: '{original_text}' → '{text}'")
        
        # 36文字以内に調整
        if len(text) > 36:
            text = text[:36]
            logger.info(f"36文字に短縮: '{text}'")
        
        # 9文字ずつ4行に分割
        lines = []
        for i in range(0, min(len(text), 36), 9):
            lines.append(text[i:i+9])
        
        # 4行に満たない場合は空行を追加
        while len(lines) < 4:
            lines.append("")
        
        logger.info(f"分割された行: {lines}")
        
        # 各行を縦書きに変換
        vertical_lines = []
        for line in lines:
            vertical_lines.append("\n".join(list(line)))
        
        # テキストを画像に描画
        draw = ImageDraw.Draw(image)
        
        start_x = 855
        start_y = 415
        font_size = 30
        font_offset = 4
        
        # 行数が少ない場合のオフセット調整
        start_x -= (font_size + font_offset) * (4 - len([line for line in lines if line])) // 2
        
        # 各行を縦書きで描画
        for i, vertical_line in enumerate(vertical_lines):
            x_pos = start_x - (font_size + font_offset) * i
            draw.text((x_pos, start_y), vertical_line, font=font, fill=(0, 0, 0))
            logger.info(f"行{i+1}描画完了: x={x_pos}, テキスト='{vertical_line.replace(chr(10), '')}'")
        
        # 一時ファイルとして保存
        temp_path = script_dir / "temp_praise_image.jpg"
        image.save(temp_path)
        logger.info(f"画像保存完了: {temp_path}")
        
        return str(temp_path)
        
    except Exception as e:
        logger.error(f"画像生成エラー: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def shorten_url(long_url):
    """is.gdを使ってURLを短縮する"""
    try:
        logger.info(f"URL短縮開始 - 元のURL長: {len(long_url)}文字")
        
        # is.gd APIを使用（POSTでリクエスト）
        api_url = "https://is.gd/create.php"
        data = {
            'format': 'simple',
            'url': long_url
        }
        
        response = requests.post(api_url, data=data, timeout=10)
        logger.info(f"is.gd応答ステータス: {response.status_code}")
        
        if response.status_code == 200:
            short_url = response.text.strip()
            # エラーメッセージの場合は失敗扱い
            if short_url.startswith('Error:') or not short_url.startswith('http'):
                logger.warning(f"is.gd短縮失敗 - エラー: {short_url}")
                return long_url  # 短縮失敗時は元のURLを返す
            
            logger.info(f"短縮成功: {short_url}")
            return short_url
        else:
            logger.warning(f"is.gd短縮失敗 - ステータス: {response.status_code}")
            return long_url  # 短縮失敗時は元のURLを返す
    except requests.exceptions.Timeout:
        logger.warning("URL短縮タイムアウト")
        return long_url
    except requests.exceptions.RequestException as e:
        logger.error(f"URL短縮接続エラー: {e}")
        return long_url
    except Exception as e:
        logger.error(f"URL短縮予期しないエラー: {e}")
        return long_url

async def transcribe_audio(message, channel):
    """音声ファイルを文字起こしする"""
    try:
        
        # 音声ファイルを検索
        AUDIO_EXTS = ('.mp3', '.m4a', '.ogg', '.webm', '.wav')
        audio_attachment = None
        
        for attachment in message.attachments:
            if attachment.filename.lower().endswith(AUDIO_EXTS):
                audio_attachment = attachment
                break
        
        if not audio_attachment:
            await channel.send("⚠️ 音声ファイルが見つかりません。対応形式: mp3, m4a, ogg, webm, wav")
            return
        
        # ファイルサイズチェック（25MB制限）
        if audio_attachment.size > 25 * 1024 * 1024:
            await channel.send("❌ ファイルサイズが25MBを超えています。")
            return
        
        await channel.send("🎤 音声の文字起こしを開始するよ〜！ちょっと待っててね")
        
        # 一時ディレクトリ作成
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # 音声ファイルをダウンロード
            file_extension = audio_attachment.filename.split('.')[-1]
            audio_file_path = temp_path / f"audio.{file_extension}"
            await audio_attachment.save(audio_file_path)
            
            logger.info(f"音声ファイルダウンロード完了: {audio_attachment.filename} ({audio_attachment.size} bytes)")
            
            # 音声ファイルを読み込み
            try:
                audio = AudioSegment.from_file(audio_file_path)
            except Exception as e:
                logger.error(f"音声ファイル読み込みエラー: {e}")
                await channel.send("❌ 音声ファイルの読み込みに失敗しました。対応形式か確認してください。")
                return
            
            # 音声の長さを確認し、分割処理を決定
            audio_length_ms = len(audio)
            audio_length_sec = audio_length_ms / 1000
            logger.info(f"音声長: {audio_length_sec:.2f}秒")
            
            # 15分（900秒）単位で分割
            split_count = max(1, int(audio_length_ms // (900 * 1000)))
            logger.info(f"{split_count}分割で処理します")
            
            # 音声ファイルを分割
            parts = []
            part_duration = audio_length_ms // split_count
            
            for i in range(split_count):
                start_time = i * part_duration
                end_time = min((i + 1) * part_duration, audio_length_ms)
                part_audio = audio[start_time:end_time]
                part_file_path = temp_path / f"part_{i}.mp3"
                part_audio.export(part_file_path, format="mp3")
                parts.append(part_file_path)
                logger.info(f"分割ファイル作成: part_{i}.mp3 ({start_time}ms～{end_time}ms)")
            
            # Whisperで各分割ファイルを文字起こし
            logger.info("Whisperによる文字起こし開始")
            full_transcription = ""
            
            for idx, part_file_path in enumerate(parts):
                logger.info(f"{idx+1}/{split_count}: {part_file_path.name} 文字起こし中...")
                
                with open(part_file_path, "rb") as audio_file:
                    transcription = client_openai.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        language="ja"  # 日本語指定
                    )
                    full_transcription += transcription.text + "\n"
                    logger.info(f"パート {idx+1} の文字起こし完了")
            
            logger.info(f"文字起こし完了: {len(full_transcription)}文字")
            
            # 文字起こし結果をテキストファイルとして保存
            original_name = os.path.splitext(audio_attachment.filename)[0]
            transcript_filename = f"{original_name}_transcript.txt"
            transcript_path = temp_path / transcript_filename
            
            with open(transcript_path, 'w', encoding='utf-8') as f:
                f.write(f"音声ファイル: {audio_attachment.filename}\n")
                f.write(f"音声長: {audio_length_sec:.2f}秒\n")
                f.write(f"処理日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("-" * 50 + "\n\n")
                f.write(full_transcription)
            
            # 結果をDiscordに分割送信（1000文字ずつ）
            await channel.send("🎉 文字起こしが完了したよ〜！")
            await channel.send("-" * 30)
            
            if full_transcription.strip():
                # 1000文字ずつに分割して送信
                for chunk in [full_transcription[j:j+1000] for j in range(0, len(full_transcription), 1000)]:
                    await channel.send(chunk)
                    await asyncio.sleep(1)  # 連続送信を避けるためのウェイト
            else:
                await channel.send("⚠️ 文字起こし結果が空でした。")
            
            await channel.send("-" * 30)
            await channel.send("📄 テキストファイルもダウンロードできるよ〜！")
            await channel.send(file=discord.File(transcript_path))
            
    except Exception as e:
        logger.error(f"音声文字起こしエラー: {e}")
        await channel.send("❌ 文字起こし処理中にエラーが発生しました。")

@bot.event
async def on_ready():
    """Bot起動時の処理"""
    print(f'{bot.user} にログインしました')
    
    # 登録されているコマンドを確認
    print(f"登録されているコマンド数: {len(bot.tree.get_commands())}")
    for cmd in bot.tree.get_commands():
        print(f"- {cmd.name}: {cmd.description}")
    
    # スラッシュコマンドを強制的に書き換え
    try:
        test_guild = discord.Object(id=TEST_GUILD_ID)
        
        # Step 1: 既存のギルドコマンドを完全にクリア
        print("=== 既存コマンドのクリア処理開始 ===")
        bot.tree.clear_commands(guild=test_guild)
        empty_sync = await bot.tree.sync(guild=test_guild)
        print(f"テストサーバーのコマンドをクリア完了: {len(empty_sync)} 個")
        
        # Step 2: 新しいコマンドを追加
        print("=== 新しいコマンドの追加処理開始 ===")
        synced_guild = await bot.tree.sync(guild=test_guild)
        print(f'テストサーバー ({TEST_GUILD_ID}) に {len(synced_guild)} 個のスラッシュコマンドを強制同期しました')
        for cmd in synced_guild:
            print(f"  ✅ {cmd['name']}: {cmd.get('description', 'N/A')}")
        
        # Step 3: グローバルにも同期
        print("=== グローバル同期処理開始 ===")
        synced_global = await bot.tree.sync()
        print(f'グローバルに {len(synced_global)} 個のスラッシュコマンドを同期しました')
        
        print("=== コマンド同期処理完了 ===")
        
    except Exception as e:
        logger.error(f'❌ スラッシュコマンドの同期に失敗しました: {e}')
        import traceback
        logger.error(traceback.format_exc())

@bot.tree.command(name="help", description="利用可能なコマンド一覧を表示します")
async def help_command(interaction: discord.Interaction):
    """ヘルプコマンド"""
    embed = discord.Embed(
        title="🤖 Bot コマンド一覧",
        description="利用可能なコマンド:",
        color=0x00ff00
    )
    
    embed.add_field(
        name="/help", 
        value="このヘルプメッセージを表示", 
        inline=False
    )
    embed.add_field(
        name="/activate", 
        value="このチャンネルでBotを有効化（管理者のみ）", 
        inline=False
    )
    embed.add_field(
        name="/deactivate", 
        value="このチャンネルでBotを無効化（管理者のみ）", 
        inline=False
    )
    embed.add_field(
        name="/status", 
        value="サーバー内の有効チャンネル一覧を表示（管理者のみ）", 
        inline=False
    )
    embed.add_field(
        name="/set_custom_prompt_x_post", 
        value="X投稿用のカスタムプロンプトを設定（空白入力で無効化）", 
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

# カスタムプロンプト設定用のModalクラス
class CustomPromptModal(discord.ui.Modal, title='X投稿用カスタムプロンプト設定'):
    def __init__(self):
        super().__init__()

    # テキスト入力エリア（複数行対応）
    prompt_input = discord.ui.TextInput(
        label='カスタムプロンプト',
        placeholder='X投稿生成用のプロンプトを入力してください...\n改行も使用できます。\n\n※ 空白のみを入力するとカスタムプロンプトが無効になり、デフォルトプロンプトが使用されます。',
        style=discord.TextStyle.paragraph,  # 複数行入力
        max_length=2000,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            prompt = self.prompt_input.value.strip()  # 前後の空白を削除
            
            # ユーザーデータを読み込み（存在しない場合は新規作成）
            user_id = interaction.user.id
            user_data = load_user_data(user_id)
            if user_data is None:
                user_data = {
                    "custom_prompt_x_post": "",
                    "status": "free",
                    "last_used_date": "",
                    "daily_usage_count": 0
                }
            
            # カスタムプロンプトを更新
            user_data["custom_prompt_x_post"] = prompt
            
            # ユーザーデータを保存
            save_user_data(user_id, user_data)
            
            # 設定内容に応じてメッセージを変更
            if prompt:
                print(f"ユーザー {interaction.user.name} ({user_id}) がカスタムプロンプトを設定しました")
                print(f"プロンプト内容: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
                await interaction.response.send_message("✅ カスタムプロンプトを設定しました！", ephemeral=True)
            else:
                print(f"ユーザー {interaction.user.name} ({user_id}) がカスタムプロンプトを無効化しました")
                await interaction.response.send_message("✅ カスタムプロンプトを無効化しました。デフォルトプロンプトを使用します。", ephemeral=True)
            
        except Exception as e:
            logger.error(f"カスタムプロンプト設定エラー: {e}")
            await interaction.response.send_message("❌ エラーが発生しました。管理者にお問い合わせください。", ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        logger.error(f"Modal エラー: {error}")
        await interaction.response.send_message("❌ エラーが発生しました。管理者にお問い合わせください。", ephemeral=True)

@bot.tree.command(name="set_custom_prompt_x_post", description="X投稿用のカスタムプロンプトを設定します")
async def set_custom_prompt_x_post_command(interaction: discord.Interaction):
    """カスタムプロンプト設定コマンド"""
    modal = CustomPromptModal()
    await interaction.response.send_modal(modal)

@bot.tree.command(name="activate", description="このチャンネルでBotを有効化します")
async def activate_command(interaction: discord.Interaction):
    """アクティベートコマンド"""
    # 管理者権限チェック
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ このコマンドは管理者のみ使用できます。", ephemeral=True)
        return
    
    server_id = str(interaction.guild.id)
    channel_id = str(interaction.channel.id)
    
    # サーバーデータを読み込み
    server_data = load_server_data(server_id)
    if server_data is None:
        server_data = {
            "server_id": server_id,
            "server_name": interaction.guild.name,
            "active_channel_ids": []
        }
    
    # server_nameを更新（サーバー名が変更された場合に対応）
    server_data['server_name'] = interaction.guild.name
    
    # チャンネルIDを追加
    if channel_id not in server_data['active_channel_ids']:
        server_data['active_channel_ids'].append(channel_id)
        save_server_data(server_id, server_data)
        await interaction.response.send_message(f"✅ このチャンネル（{interaction.channel.name}）でBotを有効化しました。")
    else:
        await interaction.response.send_message(f"ℹ️ このチャンネル（{interaction.channel.name}）は既に有効です。")

@bot.tree.command(name="deactivate", description="このチャンネルでBotを無効化します")
async def deactivate_command(interaction: discord.Interaction):
    """ディアクティベートコマンド"""
    # 管理者権限チェック
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ このコマンドは管理者のみ使用できます。", ephemeral=True)
        return
    
    server_id = str(interaction.guild.id)
    channel_id = str(interaction.channel.id)
    
    # サーバーデータを読み込み
    server_data = load_server_data(server_id)
    if server_data is None:
        await interaction.response.send_message("❌ サーバーデータが見つかりません。")
        return
    
    # チャンネルIDを削除
    if channel_id in server_data['active_channel_ids']:
        server_data['active_channel_ids'].remove(channel_id)
        save_server_data(server_id, server_data)
        await interaction.response.send_message(f"✅ このチャンネル（{interaction.channel.name}）でBotを無効化しました。")
    else:
        await interaction.response.send_message(f"ℹ️ このチャンネル（{interaction.channel.name}）は既に無効です。")

@bot.tree.command(name="status", description="サーバー内の有効チャンネル一覧を表示します")
async def status_command(interaction: discord.Interaction):
    """ステータスコマンド"""
    # 管理者権限チェック
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ このコマンドは管理者のみ使用できます。", ephemeral=True)
        return
    
    server_id = str(interaction.guild.id)
    server_data = load_server_data(server_id)
    
    embed = discord.Embed(
        title="🔍 Bot ステータス",
        color=0x0099ff
    )
    
    if server_data is None or not server_data.get('active_channel_ids'):
        embed.add_field(
            name="有効チャンネル",
            value="なし",
            inline=False
        )
    else:
        channel_list = []
        for channel_id in server_data['active_channel_ids']:
            channel = bot.get_channel(int(channel_id))
            if channel:
                channel_list.append(f"#{channel.name}")
            else:
                channel_list.append(f"不明なチャンネル（ID: {channel_id}）")
        
        embed.add_field(
            name="有効チャンネル",
            value="\n".join(channel_list) if channel_list else "なし",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

@bot.event
async def on_raw_reaction_add(payload):
    """リアクション追加時の処理"""
    # Botのリアクションは無視
    if payload.user_id == bot.user.id:
        return
    
    # リアクションの種類をチェック
    if payload.emoji.name in ['👍', '🎤', '❤️', '❓', '✏️']:
        server_id = str(payload.guild_id)
        channel_id = str(payload.channel_id)
        
        # チャンネルが有効かチェック
        if is_channel_active(server_id, channel_id):
            # チャンネルとメッセージを取得
            channel = bot.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            user = await bot.fetch_user(payload.user_id)
            
            logger.info(f"{payload.emoji.name} リアクションを検知しました！")
            logger.info(f"サーバー: {message.guild.name}")
            logger.info(f"チャンネル: {channel.name}")
            logger.info(f"ユーザー: {user.name if user else '不明'}")
            logger.info(f"メッセージ: {message.content if message.content else '(空のメッセージ)'}")
            logger.info("-" * 50)
            
            # 共通ユーザーデータ処理
            user_data = load_user_data(user.id)
            if user_data is None:
                # 新規ユーザー
                user_data = {
                    "user_id": str(user.id),
                    "username": user.name,
                    "custom_prompt_x_post": "",
                    "status": "free",
                    "last_used_date": "",
                    "daily_usage_count": 0
                }
                save_user_data(user.id, user_data)
                logger.info(f"新規ユーザー {user.name} ({user.id}) のデータを作成しました")
            else:
                # 既存ユーザーのマイグレーション
                user_data, migration_needed = migrate_user_data(user_data, user.id, user.name)
                if migration_needed:
                    save_user_data(user.id, user_data)
                    logger.info(f"ユーザー {user.name} ({user.id}) のデータをマイグレーションしました")
            
            # プレミアム状態確認
            is_premium = is_premium_user(user.id)
            
            # ユーザー情報とstatusを更新
            user_data["user_id"] = str(user.id)
            user_data["username"] = user.name
            user_data["status"] = "premium" if is_premium else "free"
            
            # 使用制限チェック
            can_use, limit_message = can_use_feature(user_data, is_premium)
            if not can_use:
                await channel.send(limit_message)
                return
            
            # 使用回数更新
            save_user_data(user.id, user_data)
            
            # 👍 サムズアップ：X投稿要約
            if payload.emoji.name == '👍':
                if message.content:
                    # モデルを選択
                    model = PREMIUM_USER_MODEL if is_premium else FREE_USER_MODEL
                    
                    # 処理開始メッセージを送信
                    await channel.send("X用の投稿を作ってあげるね〜！ちょっと待っててね")
                    
                    # X投稿用プロンプトを読み込み（カスタムプロンプトを優先）
                    x_prompt = None
                    
                    # 1. ユーザーのカスタムプロンプトをチェック
                    if user_data and user_data.get('custom_prompt_x_post'):
                        x_prompt = user_data['custom_prompt_x_post']
                        logger.info(f"ユーザー {user.name} のカスタムプロンプトを使用")
                    
                    # 2. カスタムプロンプトがない場合はデフォルトプロンプトファイルを使用
                    if not x_prompt:
                        prompt_path = script_dir / "prompt" / "x_post.txt"
                        if prompt_path.exists():
                            with open(prompt_path, 'r', encoding='utf-8') as f:
                                x_prompt = f.read()
                            logger.info("デフォルトプロンプトファイルを使用")
                        else:
                            x_prompt = "あなたはDiscordの投稿をX（旧Twitter）用に要約するアシスタントです。140文字以内で簡潔に要約してください。"
                            logger.info("フォールバックプロンプトを使用")
                    
                    # プロンプトにJSON出力指示を追加
                    x_prompt += "\n\n出力は以下のJSON形式で返してください：\n{\"content\": \"X投稿用のテキスト\"}"
                    
                    # OpenAI APIで要約を生成
                    if client_openai:
                        try:
                            response = client_openai.chat.completions.create(
                                model=model,
                                messages=[
                                    {"role": "system", "content": x_prompt},
                                    {"role": "user", "content": message.content}
                                ],
                                max_tokens=1000,
                                temperature=0.9,
                                response_format={"type": "json_object"}
                            )
                            
                            # JSONレスポンスをパース
                            response_content = response.choices[0].message.content
                            try:
                                response_json = json.loads(response_content)
                                summary = response_json.get("content", response_content)
                            except json.JSONDecodeError:
                                logger.warning(f"JSON解析エラー、生のレスポンスを使用: {response_content}")
                                summary = response_content
                            
                            # X投稿用のURLを生成
                            x_intent_url = f"https://twitter.com/intent/tweet?text={urllib.parse.quote(summary)}"
                            
                            # URLを短縮
                            shortened_url = shorten_url(x_intent_url)
                            
                            # 結果を送信（Discord制限に合わせて文字数制限）
                            # embed descriptionは4096文字制限、fieldは1024文字制限
                            display_summary = summary[:4000] + "..." if len(summary) > 4000 else summary
                            
                            embed = discord.Embed(
                                title="📝 X投稿用要約",
                                description=display_summary,
                                color=0x1DA1F2
                            )
                            
                            embed.add_field(
                                name="X投稿リンク👇",
                                value=f"[クリックして投稿]({shortened_url})",
                                inline=False
                            )
                            
                            # 完了メッセージと結果を送信
                            await channel.send("🎉 できたよ〜！Xに投稿する場合は下のリンクをクリックしてね！")
                            await channel.send(embed=embed)
                            
                        except Exception as e:
                            logger.error(f"OpenAI API エラー: {e}")
                            await channel.send("❌ 要約の生成中にエラーが発生しました。")
                    else:
                        logger.error("エラー: OpenAI APIキーが設定されていません")
                        await channel.send("❌ エラーが発生しました。管理者にお問い合わせください。")
                else:
                    await channel.send("⚠️ メッセージに内容がありません。")
            
            # 🎤 マイク：音声文字起こし
            elif payload.emoji.name == '🎤':
                # 音声ファイルがあるかチェック
                if message.attachments:
                    await transcribe_audio(message, channel)
                else:
                    await channel.send("⚠️ 音声ファイルが添付されたメッセージにリアクションしてください。")
            
            # ❤️ ハート：絶賛モード
            elif payload.emoji.name == '❤️':
                if message.content:
                    # モデルを選択
                    model = PREMIUM_USER_MODEL if is_premium else FREE_USER_MODEL
                    
                    
                    # 褒めプロンプトを読み込み
                    praise_prompt = None
                    prompt_path = script_dir / "prompt" / "heart_praise.txt"
                    if prompt_path.exists():
                        with open(prompt_path, 'r', encoding='utf-8') as f:
                            praise_prompt = f.read()
                        logger.info("褒めプロンプトファイルを使用")
                    else:
                        praise_prompt = "あなたはDiscordメッセージの内容について極めて熱烈に褒めまくるアシスタントです。どんな内容でも強烈に・熱烈に・感動的に褒めてください。ユーザーのモチベーション向上に特化した内容で、800文字以内で褒めてください。"
                        logger.info("フォールバック褒めプロンプトを使用")
                    
                    # OpenAI APIで褒めメッセージを生成（JSONモード）
                    if client_openai:
                        try:
                            response = client_openai.chat.completions.create(
                                model=model,
                                messages=[
                                    {"role": "system", "content": praise_prompt},
                                    {"role": "user", "content": message.content}
                                ],
                                max_tokens=1500,
                                temperature=0.9,
                                response_format={"type": "json_object"}
                            )
                            
                            # JSONレスポンスをパース
                            response_content = response.choices[0].message.content
                            try:
                                praise_json = json.loads(response_content)
                                long_praise = praise_json.get("long_praise", "")
                                short_praise = praise_json.get("short_praise", "")
                            except json.JSONDecodeError:
                                logger.warning(f"JSON解析エラー、フォールバックを使用: {response_content}")
                                long_praise = response_content[:400]
                                short_praise = response_content[:20]
                            
                            # 1. まず400字の激烈褒めをDiscordに投稿
                            if len(long_praise) > 400:
                                long_praise = long_praise[:400] + "..."
                            
                            await channel.send(long_praise)
                            
                            # 2. 25字の短文褒めで画像を生成
                            if len(short_praise) > 25:
                                short_praise = short_praise[:25]
                            
                            # 画像生成用テキスト処理（絵文字除去）
                            image_text = re.sub(r'[^\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF\u0021-\u007E]', '', short_praise)
                            image_text = image_text.replace("。", "").replace("、", "").replace(" ", "").replace("\n", "")
                            
                            # 褒め画像を生成
                            image_path = make_praise_image(image_text)
                            
                            # 3. 画像を送信
                            if image_path and os.path.exists(image_path):
                                try:
                                    await channel.send(file=discord.File(image_path))
                                    logger.info("褒め画像送信成功")
                                    # 一時ファイルを削除
                                    try:
                                        os.remove(image_path)
                                        logger.info("一時ファイル削除完了")
                                    except Exception as e:
                                        logger.warning(f"一時ファイル削除失敗: {e}")
                                except Exception as e:
                                    logger.error(f"画像送信エラー: {e}")
                                    await channel.send("※ 画像の生成に失敗しましたが、褒めメッセージは送れました！")
                            else:
                                logger.warning("画像パスが無効か、ファイルが存在しません")
                                await channel.send("※ 画像の生成に失敗しましたが、褒めメッセージは送れました！")
                            
                        except Exception as e:
                            logger.error(f"OpenAI API エラー (褒め機能): {e}")
                            await channel.send("❌ 褒めメッセージの生成中にエラーが発生しました。")
                    else:
                        logger.error("エラー: OpenAI APIキーが設定されていません")
                        await channel.send("❌ エラーが発生しました。管理者にお問い合わせください。")
                else:
                    await channel.send("⚠️ メッセージに内容がありません。")
            
            # ❓ 疑問符：AI説明
            elif payload.emoji.name == '❓':
                if message.content:
                    # モデルを選択
                    model = PREMIUM_USER_MODEL if is_premium else FREE_USER_MODEL
                    
                    # 処理開始メッセージを送信
                    await channel.send("🤔 投稿内容について詳しく解説するね〜！ちょっと待っててね")
                    
                    # 解説用プロンプトを読み込み
                    explain_prompt = None
                    prompt_path = script_dir / "prompt" / "question_explain.txt"
                    if prompt_path.exists():
                        with open(prompt_path, 'r', encoding='utf-8') as f:
                            explain_prompt = f.read()
                        logger.info("解説プロンプトファイルを使用")
                    else:
                        explain_prompt = "あなたはDiscordメッセージの内容について詳しく解説するアシスタントです。投稿内容をわかりやすく、丁寧に解説してください。専門用語があれば説明し、背景情報も補足してください。"
                        logger.info("フォールバック解説プロンプトを使用")
                    
                    # OpenAI APIで解説を生成
                    if client_openai:
                        try:
                            response = client_openai.chat.completions.create(
                                model=model,
                                messages=[
                                    {"role": "system", "content": explain_prompt},
                                    {"role": "user", "content": message.content}
                                ],
                                max_tokens=2000,
                                temperature=0.7
                            )
                            
                            explanation = response.choices[0].message.content
                            
                            # Discord文字数制限対応（2000文字以内に調整）
                            if len(explanation) > 1900:
                                explanation = explanation[:1900] + "..."
                            
                            # 結果を送信
                            embed = discord.Embed(
                                title="🤔 AI解説",
                                description=explanation,
                                color=0xFF6B35
                            )
                            
                            # 元の投稿内容も表示（短縮版）
                            original_content = message.content[:200] + "..." if len(message.content) > 200 else message.content
                            embed.add_field(
                                name="📝 元の投稿",
                                value=original_content,
                                inline=False
                            )
                            
                            await channel.send("💡 解説が完了したよ〜！")
                            await channel.send(embed=embed)
                            
                        except Exception as e:
                            logger.error(f"OpenAI API エラー (解説機能): {e}")
                            await channel.send("❌ 解説の生成中にエラーが発生しました。")
                    else:
                        logger.error("エラー: OpenAI APIキーが設定されていません")
                        await channel.send("❌ エラーが発生しました。管理者にお問い合わせください。")
                else:
                    await channel.send("⚠️ メッセージに内容がありません。")
            
            # ✏️ 鉛筆：Obsidianメモ作成
            elif payload.emoji.name == '✏️':
                if message.content:
                    # 処理開始メッセージ
                    await channel.send("📝 メモを作るよ〜！ちょっと待っててね")
                    
                    # モデルを選択
                    model = PREMIUM_USER_MODEL if is_premium else FREE_USER_MODEL
                    
                    # Obsidianメモ用プロンプトを読み込み
                    memo_prompt = None
                    prompt_path = script_dir / "prompt" / "pencil_memo.txt"
                    if prompt_path.exists():
                        with open(prompt_path, 'r', encoding='utf-8') as f:
                            memo_prompt = f.read()
                        logger.info("Obsidianメモプロンプトファイルを使用")
                    else:
                        memo_prompt = "あなたはDiscordメッセージの内容をObsidianメモとして整理するアシスタントです。内容に忠実にメモ化してください。追加情報は加えず、原文を尊重してください。"
                        logger.info("フォールバックメモプロンプトを使用")
                    
                    # OpenAI APIでメモを生成（JSONモード）
                    if client_openai:
                        try:
                            response = client_openai.chat.completions.create(
                                model=model,
                                messages=[
                                    {"role": "system", "content": memo_prompt},
                                    {"role": "user", "content": message.content}
                                ],
                                max_tokens=2000,
                                temperature=0.3,
                                response_format={"type": "json_object"}
                            )
                            
                            # JSONレスポンスをパース
                            response_content = response.choices[0].message.content
                            try:
                                memo_json = json.loads(response_content)
                                japanese_title = memo_json.get("japanese_title", "無題のメモ")
                                english_title = memo_json.get("english_title", "untitled_memo")
                                content = memo_json.get("content", message.content)
                            except json.JSONDecodeError:
                                logger.warning(f"JSON解析エラー、フォールバックを使用: {response_content}")
                                japanese_title = "無題のメモ"
                                english_title = "untitled_memo"
                                content = message.content
                            
                            # ファイル名を生成（YYYYMMDD_HHMMSS_english_title.md）
                            now = datetime.now()
                            timestamp = now.strftime("%Y%m%d_%H%M%S")
                            # 英語タイトルを安全なファイル名に変換
                            safe_english_title = re.sub(r'[^A-Za-z0-9\-_]', '', english_title)
                            if not safe_english_title:
                                safe_english_title = "memo"
                            filename = f"{timestamp}_{safe_english_title}.md"
                            
                            # attachmentsフォルダにファイルを保存
                            attachments_dir = script_dir / "attachments"
                            attachments_dir.mkdir(exist_ok=True)
                            file_path = attachments_dir / filename
                            
                            # ファイル内容：1行目に日本語タイトル、その下にコンテンツ
                            file_content = f"# {japanese_title}\n\n{content}"
                            
                            # UTF-8でファイル保存
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(file_content)
                            
                            logger.info(f"メモファイル作成: {file_path}")
                            
                            try:
                                # 結果を送信
                                embed = discord.Embed(
                                    title="📝 Obsidianメモを作成しました",
                                    description=f"**タイトル**: {japanese_title}\n**ファイル名**: `{filename}`",
                                    color=0x7C3AED
                                )
                                
                                # 内容のプレビュー（最初の200文字）
                                preview = content[:200] + "..." if len(content) > 200 else content
                                embed.add_field(
                                    name="📄 内容プレビュー",
                                    value=preview,
                                    inline=False
                                )
                                
                                await channel.send(embed=embed)
                                
                                # ファイルをアップロード
                                with open(file_path, 'rb') as f:
                                    file_data = f.read()
                                
                                file_obj = io.BytesIO(file_data)
                                await channel.send("📎 メモファイル:", file=discord.File(file_obj, filename=filename))
                                
                                # Discord投稿後、attachmentsフォルダの中身を削除
                                for attachment_file in attachments_dir.iterdir():
                                    if attachment_file.is_file():
                                        attachment_file.unlink()
                                        logger.info(f"添付ファイル削除: {attachment_file}")
                                
                            except Exception as upload_error:
                                logger.error(f"ファイル投稿エラー: {upload_error}")
                                # エラーが発生してもファイルは削除する
                                try:
                                    file_path.unlink()
                                    logger.info(f"エラー後のファイル削除: {file_path}")
                                except Exception as cleanup_error:
                                    logger.warning(f"ファイル削除エラー: {cleanup_error}")
                                raise upload_error
                            
                        except Exception as e:
                            logger.error(f"OpenAI API エラー (メモ機能): {e}")
                            await channel.send("❌ メモの生成中にエラーが発生しました。")
                    else:
                        logger.error("エラー: OpenAI APIキーが設定されていません")
                        await channel.send("❌ エラーが発生しました。管理者にお問い合わせください。")
                else:
                    await channel.send("⚠️ メッセージに内容がありません。")


if __name__ == "__main__":
    if TOKEN is None:
        logger.error("エラー: DISCORD_BOT_TOKEN 環境変数が設定されていません")
    else:
        try:
            logger.info("Botを起動しています...")
            bot.run(TOKEN)
        except Exception as e:
            logger.error(f"Bot起動エラー: {e}")
            import traceback
            logger.error(traceback.format_exc())