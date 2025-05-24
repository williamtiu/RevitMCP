# RevitMCP - Revit Model Context Protocol Extension

RevitMCP is a pyRevit extension that provides AI-powered assistance for Revit through an integrated chat interface and model context protocol.

## 🚀 Quick Setup

### Prerequisites
- **Revit 2020 or later**
- **pyRevit** installed and configured
- **Python 3.7 or later** (recommended: Python 3.8+)

### Installation

1. **Download/Clone** this extension to your pyRevit extensions folder:
   ```
   %APPDATA%\pyRevit\Extensions\
   ```

2. **Reload pyRevit** or restart Revit to load the extension

3. **Verify Setup** - Run the setup checker:
   ```bash
   python "path/to/RevitMCP/lib/setup_check.py"
   ```
   
   This will automatically:
   - Check your Python version
   - Verify required packages
   - Install missing packages (with your permission)

### Manual Package Installation (if needed)

If automatic installation fails, manually install the required packages:

```bash
pip install -r "path/to/RevitMCP/lib/RevitMCP_ExternalServer/requirements.txt"
```

Or install individual packages:
```bash
pip install flask requests openai anthropic google-generativeai
```

## 🎯 Usage

### Starting the Servers

1. **Start Revit Listener**: Click the "Start Revit Listener" button in the RevitMCP panel
2. **Start External Server**: Click the "Start External Server" button in the RevitMCP panel

### Using the Chat Interface

1. Open a web browser and navigate to: `http://localhost:8000`
2. Configure your API keys in the settings (⚙️ button)
3. Select your preferred AI model
4. Start chatting! The AI can access your Revit project information

### Available AI Models

- **OpenAI**: GPT-4o, GPT-4.1, GPT-4o mini, O1, GPT-4 Turbo, GPT-3.5 Turbo
- **Anthropic**: Claude Opus 4, Claude Sonnet 4, Claude 3.5 Sonnet, Claude 3.5 Haiku
- **Google**: Gemini 2.5 Pro, Gemini 2.5 Flash, Gemini 2.0 Flash, Gemini 2.0 Flash-Lite

## 🔧 Troubleshooting

### "Python executable not found"
- Ensure Python 3.7+ is installed and in your system PATH
- Try installing Python from [python.org](https://python.org) rather than the Microsoft Store
- Run the setup checker script to verify your installation

### "Required packages not found"
- Run the setup checker script: `python lib/setup_check.py`
- Allow automatic package installation when prompted
- Check that you have internet connectivity for package downloads

### "Permission denied" for log files
- This should be automatically resolved (logs are saved to your Documents folder)
- If issues persist, check that you have write permissions to `%USERPROFILE%\Documents\RevitMCP\`

### Server won't start
- Check that ports 8000 and 8001 are not in use by other applications
- Restart Revit and pyRevit
- Check the log files in `%USERPROFILE%\Documents\RevitMCP\listener_logs\`

## 📁 Project Structure

```
RevitMCP/
├── lib/
│   ├── RevitMCP_ExternalServer/    # Flask web server
│   ├── RevitMCP_RevitListener/     # Revit API interface
│   ├── RevitMCP_Tools/             # Revit data extraction tools
│   ├── RevitMCP_UI/                # UI management
│   └── setup_check.py              # Setup verification script
└── RevitMCP.tab/
    ├── Server.panel/               # Server control buttons
    └── Debug.panel/                # Development tools
```

## 🛠️ Development

### Running Setup Check
```bash
python lib/setup_check.py
```

### Testing Components
```bash
# Test UI Manager
python lib/RevitMCP_UI/ui_manager.py

# Test External Server (after installing packages)
python lib/RevitMCP_ExternalServer/server.py
```

### Log Files
- **Listener logs**: `%USERPROFILE%\Documents\RevitMCP\listener_logs\revit_listener.log`
- **Server logs**: Console output when running the external server

## 🤝 Support

If you encounter issues:

1. Run the setup checker script first
2. Check the troubleshooting section above
3. Review log files for detailed error messages
4. Ensure all prerequisites are met

## 📝 Notes

- The extension automatically manages package installation and updates
- Log files are stored in your Documents folder to avoid permission issues
- The system prioritizes system-wide Python installations over Windows Store versions
- All required dependencies are installed automatically with user consent 