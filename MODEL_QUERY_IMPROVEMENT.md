# 模型查询工具改进说明

## 🎯 问题解决

您指出的问题非常关键：在 `@mcp.tool` 的 `model` 参数描述中硬编码模型名称会误导 LLM 生成错误的输入参数。

## ✅ 解决方案

### 1. 改进前的问题
```python
model: Optional[str] = Field(
    default=None,
    description="AI model to use: gpt-image-1, imagen-4, imagen-4-ultra, imagen-3, dall-e-3, dall-e-2. If not specified, uses configured default model."
)
```

**问题:** 
- 硬编码了所有可能的模型名称
- LLM 可能会选择当前不可用的模型
- 不能反映实际的运行时配置

### 2. 改进后的解决方案
```python
model: Optional[str] = Field(
    default=None,
    description="AI model to use for image generation. Available models depend on configured providers. If not specified, uses the configured default model."
)
```

**改进:**
- 描述更加通用和准确
- 不会误导 LLM 使用不存在的模型
- 引导 LLM 先查询可用模型

### 3. 新增 list_available_models 工具

新增了一个专门的工具来查询当前可用的模型：

```python
@mcp.tool(
    title="List Available Models",
    description="Get information about all available image generation models and their capabilities"
)
async def list_available_models() -> dict[str, Any]:
    """
    List all available image generation models with their capabilities.
    
    Returns information about:
    - Available models by provider
    - Model capabilities (sizes, qualities, formats)
    - Provider status and configuration
    - Cost estimates and features
    """
```

## 🔄 推荐的工作流

现在 LLM 应该按照以下步骤操作：

1. **首先查询可用模型**
   ```python
   # 调用 list_available_models()
   available_models = await list_available_models()
   ```

2. **根据需求选择模型**
   - 查看每个模型的 capabilities
   - 考虑 cost_estimate
   - 检查 provider 和 available 状态

3. **生成图像**
   ```python
   # 使用查询到的可用模型
   result = await generate_image(
       prompt="A beautiful landscape",
       model="imagen-4"  # 从可用模型列表中选择
   )
   ```

## 📊 list_available_models 输出示例

```json
{
    "summary": {
        "total_providers": 2,
        "available_providers": 2,
        "total_models": 4,
        "providers": {
            "openai": {
                "available": true,
                "models": ["gpt-image-1", "dall-e-3"]
            },
            "gemini": {
                "available": true,
                "models": ["imagen-4", "imagen-4-ultra"]
            }
        }
    },
    "models": {
        "gpt-image-1": {
            "provider": "openai",
            "available": true,
            "capabilities": {
                "sizes": ["auto", "1024x1024", "1536x1024", "1024x1536"],
                "qualities": ["auto", "high", "medium", "low"],
                "formats": ["png", "jpeg", "webp"],
                "max_images": 1,
                "supports_style": true,
                "supports_background": true
            },
            "cost_estimate": 0.07,
            "features": {
                "moderation": ["auto", "low"],
                "style": ["vivid", "natural"],
                "background": ["auto", "transparent", "opaque"]
            }
        },
        "imagen-4": {
            "provider": "gemini",
            "available": true,
            "capabilities": {
                "sizes": ["auto", "1024x1024", "1536x1024", "1024x1536"],
                "qualities": ["auto", "high", "medium", "low"],
                "formats": ["png", "jpeg", "webp"],
                "max_images": 1,
                "supports_style": false,
                "supports_background": false
            },
            "cost_estimate": 0.04,
            "features": {
                "aspect_ratio": ["1:1", "3:4", "4:3", "9:16", "16:9"],
                "enhance_prompt": [true, false]
            }
        }
    },
    "default_model": "gpt-image-1"
}
```

## 🎉 优势

1. **动态模型发现**: LLM 可以实时了解当前可用的模型
2. **准确的参数选择**: 基于实际能力而非硬编码列表
3. **成本意识**: 显示每个模型的成本估算
4. **能力匹配**: 根据需求选择最合适的模型
5. **错误减少**: 避免尝试使用不存在或不可用的模型

这样的设计让 LLM 能够做出更智能、更准确的模型选择决策！