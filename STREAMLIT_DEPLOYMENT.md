# 🚀 Streamlit Deployment Guide

This guide covers deploying your LinkedIn Job Application Agent using Streamlit.

## 📋 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Up Environment Variables
Create a `.env` file in the project root:
```bash
# Required
OPENAI_API_KEY=your_openai_api_key_here

# Optional (with defaults)
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=2000

# Optional endpoints
OPENAI_ENDPOINT=https://api.openai.com/v1
ANTHROPIC_ENDPOINT=https://api.anthropic.com
```

### 3. Run the Application

#### Option A: Using the Runner Script (Recommended)
```bash
python run_streamlit.py
```

#### Option B: Direct Streamlit Command
```bash
streamlit run streamlit_app.py --server.port 8501
```

### 4. Access the Application
Open your browser to: **http://localhost:8501**

## 🌐 Deployment Options

### Local Development
- Use `python run_streamlit.py` for local development
- The application runs on `localhost:8501` by default
- Browser window will open automatically

### Streamlit Cloud (Free)
1. Push your code to GitHub
2. Connect to [Streamlit Cloud](https://streamlit.io/cloud)
3. Deploy directly from your repository
4. Add environment variables in Streamlit Cloud settings

### Docker Deployment
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### Cloud Platforms

#### Heroku
1. Create `Procfile`:
```
web: streamlit run streamlit_app.py --server.port=$PORT --server.address=0.0.0.0
```

2. Deploy:
```bash
heroku create your-app-name
git push heroku main
```

#### AWS/GCP/Azure
- Use container deployment with the Docker image
- Set environment variables in cloud platform
- Configure load balancing if needed

## ⚙️ Configuration

### Streamlit Configuration
The app includes a `.streamlit/config.toml` file with optimized settings:
- Custom theme colors
- Performance optimizations
- Security settings
- Upload limits

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | ✅ | - | Your OpenAI API key |
| `LLM_PROVIDER` | ❌ | `openai` | AI provider (openai/anthropic) |
| `LLM_MODEL` | ❌ | `gpt-4o` | Model to use |
| `LLM_TEMPERATURE` | ❌ | `0.1` | Response creativity |
| `LLM_MAX_TOKENS` | ❌ | `2000` | Max response length |

## 🔒 Security Considerations

### API Keys
- ⚠️ **Never** commit API keys to version control
- Use environment variables or secure secret management
- Consider using cloud platform secret managers

### Browser Automation
- The app runs browser automation (Playwright)
- Ensure proper firewall settings in production
- Consider running in containerized environments

### File Uploads
- Resume uploads are limited to 200MB
- Files are stored locally in `data/documents/`
- Implement cleanup policies for production

## 🚀 Performance Optimization

### Caching
```python
@st.cache_data
def load_profile_data():
    # Cache expensive operations
    pass
```

### Session State
- Profile data is stored in Streamlit session state
- Browser instances are reused when possible
- Cleanup happens automatically on session end

### Resource Management
- Browser instances are properly closed
- Temporary files are cleaned up
- Memory usage is optimized with streaming responses

## 🐛 Troubleshooting

### Common Issues

#### "Module not found" errors
```bash
pip install -r requirements.txt
```

#### Browser automation fails
- Check if Playwright browsers are installed:
```bash
playwright install
```

#### Streamlit won't start
- Check port 8501 is available
- Verify Python version (3.8+ required)
- Check environment variables are set

#### LLM connection fails
- Verify API key is correct and has credits
- Check network connectivity
- Ensure correct model name

### Debug Mode
Add to your environment:
```bash
STREAMLIT_DEBUG=true
```

### Logs
Check application logs in:
- Local: Terminal output
- Cloud: Platform-specific logs
- Docker: `docker logs <container_name>`

## 📊 Monitoring

### Application Health
- Built-in health checks in config tab
- LLM connection testing
- Environment variable validation

### Usage Tracking
- Application history is automatically tracked
- Export functionality for analytics
- Session state debugging tools

## 🔄 Migration from Gradio

The Streamlit version maintains all functionality from the original Gradio version:

### Key Differences
- **UI Framework**: Streamlit vs Gradio
- **Session Management**: Streamlit session state vs custom manager
- **Deployment**: More deployment options with Streamlit
- **Performance**: Generally faster with better caching

### Data Compatibility
- All profile data remains compatible
- Application history format unchanged
- Configuration files can be imported/exported

## 📈 Scaling

### Single User
- Perfect for personal use
- Local or cloud deployment
- Minimal resource requirements

### Multi-User (Enterprise)
- Deploy on cloud platforms
- Consider user authentication
- Implement data isolation
- Use container orchestration

### High Availability
- Load balancer setup
- Database for shared state
- Redis for session management
- Container clustering

## 📝 Development

### Local Development
```bash
# Install in development mode
pip install -e .

# Run with auto-reload
streamlit run streamlit_app.py --server.runOnSave=true
```

### Adding Features
- Components are in `src/webui/streamlit_components/`
- Follow existing patterns for state management
- Test with different browsers and screen sizes

### Testing
```bash
# Unit tests
python -m pytest tests/

# Integration tests
python -m pytest tests/test_streamlit_integration.py
```

## 🆘 Support

For issues and questions:
1. Check this documentation
2. Review environment variable setup
3. Test LLM connection in config tab
4. Check application logs
5. Open an issue on GitHub

## 🎯 Next Steps

After successful deployment:
1. Set up your profile in the Profile Settings tab
2. Configure browser settings as needed
3. Test with a few job applications
4. Review application history
5. Export configurations for backup 