# Syllablaze Multi-Backend STT - Beta Announcement Draft

## 🎉 Exciting News: Multi-Backend Speech-to-Text Support!

We've been hard at work on a major feature update for Syllablaze, and it's ready for testing! The `feature/multi-backend-stt` branch now supports multiple STT backends beyond just Whisper.

### What's New

**🎯 Multiple Backend Support**
- **Whisper** (OpenAI) - The classic, now with optimized settings
- **Liquid AI LFM2.5-Audio** - New multimodal audio model support
- **Qwen2-Audio** - Alibaba's audio-language model with configurable generation parameters
- **Granite Speech** - IBM's enterprise speech models

**⚙️ Per-Backend Settings**
Each backend now has its own dedicated settings tab:
- **General**: Language, device (CPU/CUDA)
- **Whisper**: Compute type, beam size, VAD filter, word timestamps
- **Liquid**: Temperature, top-k, max tokens
- **Qwen**: Temperature, top-p, top-k, max tokens, repetition penalty

**🔧 Backend Health Monitoring**
New dependency management system checks which backends are available and provides clear install instructions for missing dependencies.

**🐛 Bug Fixes**
- Fixed multiprocessing crashes during transcription
- Fixed blank settings tabs
- Improved error handling and recovery

### Try It Out

```bash
git fetch origin
git checkout feature/multi-backend-stt
# Install new dependencies if needed
pip install -r requirements.txt
```

### Feedback Welcome

This is a significant architectural change. We'd love your feedback on:
- Backend switching performance
- Settings UI usability
- Any stability issues

Let us know what you think! 🚀

---
*This is a feature branch - your testing helps us get this ready for the main release.*
