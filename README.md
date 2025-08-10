# Claude Multi-Tab Voice Bot

A sophisticated multi-tab voice interface for Claude AI with real-time speech recognition, text-to-speech, and session management. Built for power users who need multiple concurrent AI conversations with voice interaction.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/flask-3.0.0-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## 🚀 Features

### Core Functionality
- **4 Independent Claude Sessions**: Each tab maintains its own conversation context
- **Real-time Voice Recognition**: Powered by Web Speech API with automatic 2-second silence detection
- **Text-to-Speech Synthesis**: Natural voice responses using Microsoft Edge TTS (en-US-AriaNeural)
- **Smart Tab Management**: Voice input routes to the originating tab, even when switching mid-speech

### User Interface
- **Visual Feedback**: 
  - 🔴 Red recording indicator during voice capture
  - 🟡 Yellow tab highlighting for unread messages
  - 🔵 Blue chat bubbles for Claude's responses
  - ✨ Neon green cyberpunk theme with glowing effects
- **Interactive Elements**:
  - Double-click tabs to rename
  - Keyboard shortcuts for efficiency
  - Cross-tab notification chimes
  - Responsive design with smooth animations

### Technical Features
- **WebSocket Communication**: Real-time bidirectional messaging
- **SSL/HTTPS**: Secure connections for microphone access
- **Session Persistence**: Conversations maintained across browser refreshes
- **Auto-Approval Mode**: Bash commands execute without manual confirmation

## 📋 Prerequisites

- Python 3.8 or higher
- Claude CLI installed and configured
- Modern web browser (Chrome/Edge recommended)
- Microphone access
- SSL certificates (self-signed or valid)

## 🛠️ Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/Corptech02/Multi-voice-bot.git
   cd Multi-voice-bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Generate SSL certificates** (for local development)
   ```bash
   openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
   ```

4. **Start the services**
   ```bash
   # Terminal 1 - TTS Server
   python3 edge_tts_server_https.py
   
   # Terminal 2 - Main Application
   python3 multi_tab_voice_exact_replica.py
   ```

5. **Access the interface**
   ```
   https://localhost:8444
   ```

## 📖 Documentation

- **[Installation Guide](INSTALLATION.md)** - Detailed setup instructions
- **[Usage Guide](USAGE.md)** - How to use all features
- **[Architecture Overview](ARCHITECTURE.md)** - Technical design and data flow
- **[Troubleshooting](TROUBLESHOOTING.md)** - Common issues and solutions

## 🎯 Use Cases

### Development & Coding
- Tab 1: Main development task
- Tab 2: Documentation writing
- Tab 3: Debugging assistance
- Tab 4: Code review and refactoring

### Research & Learning
- Tab 1: Primary research topic
- Tab 2: Related concepts exploration
- Tab 3: Practical examples
- Tab 4: Q&A and clarifications

### Content Creation
- Tab 1: Article/blog drafting
- Tab 2: Fact-checking and research
- Tab 3: Code examples and snippets
- Tab 4: SEO and formatting

## 🔧 Configuration

### Changing Ports
Edit the following files to change default ports:
- Main app (8444): `multi_tab_voice_exact_replica.py`
- TTS server (5001): `edge_tts_server_https.py`

### IP Address
Default uses `192.168.40.232`. To change:
```python
# In multi_tab_voice_exact_replica.py
app.run(host='0.0.0.0', port=8444, ssl_context=context)
```

### Voice Settings
Modify TTS voice in `edge_tts_server_https.py`:
```python
voice = "en-US-AriaNeural"  # Change to preferred voice
```

## 🏗️ Project Structure

```
Multi-voice-bot/
├── multi_tab_voice_exact_replica.py  # Main application server
├── orchestrator_simple_v2.py         # Session management
├── claude_memory_wrapper.py          # Claude CLI wrapper
├── edge_tts_server_https.py          # Text-to-speech server
├── requirements.txt                  # Python dependencies
├── README.md                         # This file
├── INSTALLATION.md                   # Installation guide
├── USAGE.md                         # Usage documentation
├── ARCHITECTURE.md                  # Technical architecture
└── .gitignore                       # Git ignore rules
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

### Development Setup
1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Anthropic](https://www.anthropic.com/) for Claude AI
- [Microsoft Edge TTS](https://azure.microsoft.com/en-us/services/cognitive-services/text-to-speech/) for voice synthesis
- [Flask-SocketIO](https://flask-socketio.readthedocs.io/) for real-time communication
- Web Speech API for browser-based voice recognition

## 🐛 Known Issues

- Self-signed certificates require manual browser acceptance
- WebRTC/microphone access requires HTTPS
- Some browsers may have compatibility issues with Web Speech API
- Session limit of 4 concurrent Claude instances

## 🚧 Roadmap

- [ ] Dynamic session creation (more than 4 tabs)
- [ ] User authentication and session persistence
- [ ] Docker containerization
- [ ] Cloud deployment guide
- [ ] Mobile responsive design
- [ ] Custom voice selection UI
- [ ] Export conversation history
- [ ] Keyboard shortcut customization

## 📞 Support

For issues and questions:
- Open an issue on [GitHub](https://github.com/Corptech02/Multi-voice-bot/issues)
- Check existing issues for solutions
- Review the troubleshooting guide

---

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>