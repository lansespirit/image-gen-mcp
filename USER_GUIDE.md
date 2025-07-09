# Image Gen MCP Server - User Guide

## 🎯 What is Image Gen MCP Server?

Image Gen MCP Server is an intelligent image generation service that enables your AI assistant (like Claude Desktop) to create images. Simply describe what you want in text, and the AI will create it for you.

### ✨ Key Features

- **Text-to-Image Generation**: Describe your desired image and AI creates it instantly
- **Multiple AI Models**: Support for OpenAI and Google's latest image generation models
- **High-Quality Output**: Generate professional-grade images
- **Easy to Use**: Works out of the box with minimal setup

## 🚀 Quick Start

### Step 1: Get API Keys

You need at least one AI provider's API key:

**OpenAI (Recommended):**
1. Visit [OpenAI's website](https://platform.openai.com/)
2. Sign up and log in to your account
3. Go to the API Keys page
4. Click "Create new secret key"
5. Copy the generated key (format: sk-xxxxx)

**Google Gemini (Optional):**
1. Visit [Google AI Studio](https://aistudio.google.com/)
2. Sign up and create a project
3. Generate your API key

### Step 2: Install the Server

**Requirements:**
- Python 3.10 or higher
- [UV package manager](https://docs.astral.sh/uv/) (recommended)

**Installation Steps:**
```bash
# 1. Download the project
git clone <repository-url>
cd image-gen-mcp

# 2. Install dependencies
uv sync

# 3. Configure API keys
cp .env.example .env
# Edit the .env file with your text editor and add your API keys
```

### Step 3: Configure Claude Desktop

1. Open Claude Desktop settings
2. Find the MCP settings section
3. Add the following configuration:

```json
{
  "mcpServers": {
    "image-gen": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/your/image-gen-mcp",
        "run",
        "image-gen-mcp"
      ]
    }
  }
}
```

## 🎨 How to Use

### Basic Image Generation

In Claude Desktop, you can directly request image generation:

**Example Conversation:**
```
You: Please generate an image of a mountain landscape at sunset

Claude: I'll generate a mountain sunset landscape image for you.
[Calls image generation tool]
[Displays the generated image]
```

### Advanced Features

**Specify AI Model:**
```
You: Use OpenAI's latest model to generate a cute cat image

You: Use Google's Imagen model to create an abstract artwork
```

**Check Available Models:**
```
You: What image generation models are available?

Claude: Let me check the currently available image generation models for you.
[Shows all available models and their capabilities]
```

**Custom Parameters:**
```
You: Generate a high-quality landscape image in 1536x1024 resolution

You: Create a product image with transparent background
```

## 🔧 Configuration

### Environment Variables

Edit the `.env` file and configure these key settings:

```bash
# OpenAI Configuration (Recommended)
PROVIDERS__OPENAI__API_KEY=sk-your-openai-key
PROVIDERS__OPENAI__ENABLED=true

# Gemini Configuration (Optional)
PROVIDERS__GEMINI__API_KEY=your-gemini-key
PROVIDERS__GEMINI__ENABLED=true

# Image Settings
IMAGES__DEFAULT_MODEL=gpt-image-1
IMAGES__DEFAULT_QUALITY=high
IMAGES__DEFAULT_SIZE=1536x1024
```

### Supported Models

**OpenAI Models:**
- `gpt-image-1`: Latest and most powerful image generation model
- `dall-e-3`: High-quality creative image generation
- `dall-e-2`: Classic image generation model

**Google Gemini Models:**
- `imagen-4`: Google's latest image generation model
- `imagen-4-ultra`: Enhanced high-quality version
- `imagen-3`: Previous generation stable model

## 💡 Tips for Better Results

### Writing Good Prompts

**Be Specific:**
- ✅ Good: An orange Persian cat sitting on a sunny windowsill
- ❌ Poor: A cat

**Include Style:**
- "In watercolor painting style..."
- "Photography style..."
- "Cartoon animation style..."

**Specify Details:**
- "Soft lighting"
- "Blue color palette"
- "Minimalist style"

### Common Use Cases

**Social Media Images:**
```
Generate a square Instagram-style food image showing elegant pasta, warm tones, professional photography style
```

**Business Presentations:**
```
Create a minimalist business chart background with blue gradient, suitable for PowerPoint
```

**Creative Design:**
```
Design a modern minimalist logo concept with geometric shapes, black and white color scheme
```

## 🔍 Troubleshooting

### Common Issues

**Issue 1: Image Generation Fails**
- Check if API keys are correct
- Verify account has sufficient balance
- Ensure prompt follows content policies

**Issue 2: Server Won't Start**
- Check Python version (requires 3.10+)
- Ensure all dependencies are installed
- Review error logs for details

**Issue 3: Claude Desktop Can't Connect**
- Verify MCP configuration path is correct
- Confirm server is running
- Restart Claude Desktop

### Getting Help

**View Logs:**
```bash
# Run server with debug logging
uv run python -m gpt_image_mcp.server --log-level DEBUG
```

**Test Connection:**
```bash
# Test API keys
uv run python scripts/dev.py test
```

## 📞 Technical Support

If you encounter technical issues:

1. **Check Logs**: Run with `--log-level DEBUG` parameter
2. **Verify Configuration**: Ensure `.env` file settings are correct
3. **Restart Service**: Sometimes a simple restart solves the problem
4. **Community Help**: Submit an Issue on the project's GitHub page

## 🌟 Model Comparison

| Model | Provider | Generation | Editing | Best For |
|-------|----------|------------|---------|----------|
| gpt-image-1 | OpenAI | ✅ | ✅ | Latest features, highest quality |
| dall-e-3 | OpenAI | ✅ | ❌ | Creative, artistic images |
| dall-e-2 | OpenAI | ✅ | ✅ | Simple images, editing tasks |
| imagen-4 | Google | ✅ | ❌ | Alternative style, high quality |
| imagen-4-ultra | Google | ✅ | ❌ | Premium quality Imagen |
| imagen-3 | Google | ✅ | ❌ | Stable, reliable generation |

## 🎉 Start Creating

You're now ready to start generating images with AI! Remember:
- Detailed descriptions lead to better results
- Try different models to find what works best
- Experiment with various styles and parameters
- Have fun with AI-powered creativity!

---

**Pro Tip:** If you're new to AI image generation, start with simple descriptions and gradually explore more advanced features and parameters. Happy creating! 🎨✨

---

## 📚 Additional Resources

- **System Documentation**: See `SYSTEM_DESIGN.md` for technical details
- **API Reference**: Check `docs/multi_provider_api_guide.md` for complete API documentation
- **Deployment Guide**: See `deploy/VPS_DEPLOYMENT_GUIDE.md` for server deployment
- **Chinese Guide**: See `USER_GUIDE_CN.md` for the Chinese version of this guide