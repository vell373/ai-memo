# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands and Development

### Bot Operations
```bash
# Run the bot manually (ensure virtual environment is activated first)
python3 main.py  # macOS/Linux
python main.py   # Windows

# Use automated scripts (recommended - handles venv setup)
./run.sh         # macOS/Linux
ai-keisuke.bat   # Windows (Japanese)
start-en.bat     # Windows (English - avoids mojibake)
```

### Virtual Environment Setup
```bash
# Create and activate virtual environment
python3 -m venv ai-keisuke-env
source ai-keisuke-env/bin/activate  # macOS/Linux
ai-keisuke-env\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### Testing and Debugging
- Monitor `log.txt` for runtime errors and bot activity
- Test slash commands in dedicated test channel after `/activate`
- Check user data in `data/user_data/{user_id}.json` for state debugging

### Website Updates
- Website source: `/Users/keisukeohno/Dropbox/xPersonal/project/mp0059_program/20250613_ai_keisuke/webpage/`
- Main file: `index.html` (all styles embedded)
- Deploy changes by pushing to GitHub (ai-keisuke repository)

## Architecture Overview

### Core Bot Structure
The bot uses a reaction-based architecture where users interact via emoji reactions (👍🎤❓❤️✏️) on messages. Key components:

1. **Premium System**: Triple-layered authentication
   - Discord role check in community server
   - Owner user ID fallback (settings.json)
   - Server owner auto-detection

2. **Content Processing Pipeline**:
   - `extract_embed_content()`: Processes Discord embeds
   - `read_text_attachment()`: Async file reading with encoding detection
   - Each reaction handler processes: original message → attachments → embeds

3. **File Generation**: All file uploads now include descriptive messages for mobile compatibility
   - Transcription files: "📄 文字起こし結果のテキストファイルです！"
   - Praise images: "🎉 褒め画像をお作りしました！"
   - Memo files: "📝 メモファイルを作成しました！"

### OpenAI Integration
- Free users: `gpt-4.1-mini`
- Premium users: `gpt-4.1`
- Whisper API for audio transcription
- Custom prompts loaded from `prompt/` directory

### Data Management
- Server settings: `data/server_data/{server_id}.json`
- User data: `data/user_data/{user_id}.json` (includes usage tracking)
- Temporary files: `attachments/` (auto-cleaned after use)

### Development Workflow
- Production branch: `main` (running in `/ai-keisuke/`)
- Development branch: `develop` (working in `/ai-keisuke-dev/`)
- Use git worktree for parallel development without disrupting production

## Critical Implementation Notes

1. **File Upload Messages**: Always include descriptive text with file uploads for mobile Discord compatibility

2. **Japanese Filename Handling**: Discord strips Japanese characters from filenames. Solution: use English filenames with Japanese content inside files

3. **Premium Authentication**: Check premium status in this order:
   - Is user the configured owner? (owner_user_id)
   - Does user have premium role in community server?
   - Is user the server owner? (fallback)

4. **Encoding**: Handle both UTF-8 and Shift-JIS for text file reading

5. **Rate Limiting**: Free users limited to 5 uses/day, tracked in user data JSON