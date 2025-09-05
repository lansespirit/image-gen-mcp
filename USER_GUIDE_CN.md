# Image Gen MCP Server 使用指南

## 🎯 什么是 Image Gen MCP Server？

Image Gen MCP Server 是一个智能图片生成服务器，它可以让您的AI助手（如Claude Desktop）具备生成图片的能力。只需用文字描述您想要的图片，AI就能为您创建出来。

### ✨ 主要功能

- **文字生成图片**：描述您想要的图片，AI立即为您创建
- **多种AI模型**：支持OpenAI和Google的最新图片生成模型
- **高质量输出**：生成专业级别的图片
- **简单易用**：无需复杂设置，开箱即用

## 🚀 快速开始

### 第一步：获取API密钥

您需要至少一个AI服务商的API密钥：

**OpenAI（推荐）：**
1. 访问 [OpenAI官网](https://platform.openai.com/)
2. 注册账户并登录
3. 进入 API Keys 页面
4. 点击"Create new secret key"
5. 复制生成的密钥（格式：sk-xxxxx）

**Google Gemini（可选）：**
1. 访问 [Google AI Studio](https://aistudio.google.com/)
2. 注册并创建项目
3. 获取API密钥

### 第二步：安装服务器

**环境要求：**
- Python 3.10 或更高版本
- [UV包管理器](https://docs.astral.sh/uv/)（推荐）

**安装步骤：**
```bash
# 1. 下载项目
git clone <项目地址>
cd image-gen-mcp

# 2. 安装依赖
uv sync

# 3. 配置API密钥
cp .env.example .env
# 用文本编辑器打开 .env 文件，填入您的API密钥
```

### 第三步：配置Claude Desktop

1. 打开Claude Desktop设置
2. 找到MCP设置选项
3. 添加以下配置：

```json
{
  "mcpServers": {
    "image-gen": {
      "command": "uv",
      "args": [
        "--directory",
        "/您的项目路径/image-gen-mcp",
        "run",
        "image-gen-mcp"
      ]
    }
  }
}
```

## 🎨 如何使用

### 基础图片生成

在Claude Desktop中，您可以直接要求生成图片：

**示例对话：**
```
您：请为我生成一幅日落时分的山景图片

Claude：我来为您生成一幅日落山景图片。
[调用图片生成工具]
[显示生成的图片]
```

### 高级功能

**指定AI模型：**
```
您：用OpenAI的最新模型生成一只可爱的小猫图片

您：用Google的Imagen模型生成一幅抽象艺术作品
```

**查看可用模型：**
```
您：有哪些图片生成模型可以使用？

Claude：让我为您查看当前可用的图片生成模型。
[显示所有可用模型和功能]
```

**自定义参数：**
```
您：生成一幅1536x1024尺寸的高质量风景画

您：生成一幅透明背景的产品图片
```

## 🔧 配置说明

### 环境变量配置

编辑 `.env` 文件，配置以下关键项目：

```bash
# OpenAI配置（推荐）
PROVIDERS__OPENAI__API_KEY=sk-您的OpenAI密钥
PROVIDERS__OPENAI__ENABLED=true

# Gemini配置（可选）
PROVIDERS__GEMINI__API_KEY=您的Gemini密钥
PROVIDERS__GEMINI__ENABLED=true

# 图片设置
IMAGES__DEFAULT_MODEL=gpt-image-1
IMAGES__DEFAULT_QUALITY=high
IMAGES__DEFAULT_SIZE=1536x1024
```

### 支持的模型

**OpenAI模型：**
- `gpt-image-1`：最新最强的图片生成模型
- `dall-e-3`：高质量创意图片生成
- `dall-e-2`：经典图片生成模型

**Google Gemini模型：**
- `imagen-4`：Google最新图片生成模型
- `imagen-4-ultra`：增强版高质量模型
- `imagen-3`：上一代稳定模型

## 💡 使用技巧

### 如何写好提示词

**具体描述：**
- ✅ 好：一只橙色的波斯猫坐在阳光透过的窗台上
- ❌ 差：一只猫

**包含风格：**
- "水彩画风格的..."
- "摄影作品风格的..."
- "卡通动画风格的..."

**指定细节：**
- "柔和的光线"
- "蓝色调"
- "简约风格"

### 常用场景示例

**社交媒体图片：**
```
生成一幅适合Instagram的正方形美食图片，展示精美的意大利面，暖色调，专业摄影风格
```

**工作演示：**
```
创建一幅简约的商务图表背景，蓝色渐变，适合PPT使用
```

**创意设计：**
```
设计一个现代简约的Logo概念，几何图形，黑白配色
```

## 🔍 故障排除

### 常见问题

**问题1：图片生成失败**
- 检查API密钥是否正确
- 确认账户余额充足
- 提示词是否符合内容政策

**问题2：服务器无法启动**
- 检查Python版本（需要3.10+）
- 确认所有依赖已安装
- 查看错误日志信息

**问题3：Claude Desktop无法连接**
- 检查MCP配置路径是否正确
- 确认服务器正在运行
- 重启Claude Desktop

### 获取帮助

**查看日志：**
```bash
# 运行服务器并查看日志
uv run python -m image_gen_mcp.server --log-level DEBUG
```

**测试连接：**
```bash
# 测试API密钥
uv run python scripts/dev.py test
```

## 📞 技术支持

如果您遇到技术问题：

1. **查看日志**：运行时添加 `--log-level DEBUG` 参数
2. **检查配置**：确认 `.env` 文件设置正确
3. **重启服务**：有时简单重启就能解决问题
4. **社区求助**：在项目GitHub页面提交Issue

## 🎉 开始创作

现在您已经准备好开始使用AI生成图片了！记住：
- 详细的描述能获得更好的结果
- 尝试不同的模型找到最适合的
- 多实验不同的风格和参数
- 享受AI创作的乐趣！

---

**小贴士：** 如果您是第一次使用，建议先从简单的描述开始，逐渐熟悉各种功能和参数。祝您使用愉快！ 🎨✨
