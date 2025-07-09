#!/bin/bash
# 重命名脚本：从 gpt-image-mcp 更名为 image-gen-mcp

echo "🔄 开始重命名项目：gpt-image-mcp -> image-gen-mcp"
echo "================================================"

# 主要重命名映射
OLD_NAME="gpt-image-mcp"
NEW_NAME="image-gen-mcp"
OLD_DISPLAY="GPT Image MCP"
NEW_DISPLAY="Image Gen MCP"
OLD_DESCRIPTION="GPT Image MCP Server"
NEW_DESCRIPTION="Image Gen MCP Server"

echo "📋 重命名计划："
echo "  项目名称: $OLD_NAME -> $NEW_NAME"
echo "  显示名称: $OLD_DISPLAY -> $NEW_DISPLAY"
echo "  服务描述: $OLD_DESCRIPTION -> $NEW_DESCRIPTION"
echo

# 需要更新的文件列表
FILES_TO_UPDATE=(
    "pyproject.toml"
    "README.md"
    "CLAUDE.md"
    "SYSTEM_DESIGN.md"
    "gpt_image_mcp/config/settings.py"
    "gpt_image_mcp/server.py"
    "gpt_image_mcp/__init__.py"
    "gpt_image_mcp/types/models.py"
    "gpt_image_mcp/types/enums.py"
    "gpt_image_mcp/types/__init__.py"
    "scripts/dev.py"
    "tests/unit/test_config.py"
    "tests/__init__.py"
    "tests/conftest.py"
    "deploy/VPS_DEPLOYMENT_GUIDE.md"
    ".env.example"
)

echo "📁 将更新以下文件："
for file in "${FILES_TO_UPDATE[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file (不存在)"
    fi
done

echo
echo "🚀 开始执行重命名操作..."
echo "================================"

# 执行文件内容替换
for file in "${FILES_TO_UPDATE[@]}"; do
    if [ -f "$file" ]; then
        echo "📝 更新 $file"
        
        # 创建备份
        cp "$file" "$file.backup"
        
        # 执行替换
        sed -i "s|$OLD_NAME|$NEW_NAME|g" "$file"
        sed -i "s|$OLD_DISPLAY|$NEW_DISPLAY|g" "$file"
        sed -i "s|$OLD_DESCRIPTION|$NEW_DESCRIPTION|g" "$file"
        
        echo "  ✅ 完成"
    else
        echo "  ⚠️  跳过不存在的文件: $file"
    fi
done

echo
echo "🎯 特殊处理..."
echo "=================="

# 更新服务器描述中的旧模型引用
if [ -f "gpt_image_mcp/server.py" ]; then
    echo "📝 更新服务器描述以反映多模型支持"
    sed -i 's/using OpenAI'\''s gpt-image-1 model/using multiple AI models (OpenAI, Gemini, etc.)/g' gpt_image_mcp/server.py
    echo "  ✅ 完成"
fi

# 更新 README.md 中的描述
if [ -f "README.md" ]; then
    echo "📝 更新 README.md 描述"
    sed -i 's/GPT Image MCP Server bridges this gap/Image Gen MCP Server bridges this gap/g' README.md
    sed -i 's/\*\*GPT Image MCP Server solves this by providing:\*\*/\*\*Image Gen MCP Server solves this by providing:\*\*/g' README.md
    echo "  ✅ 完成"
fi

echo
echo "🧹 清理备份文件..."
echo "==================="
read -p "是否删除备份文件? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    for file in "${FILES_TO_UPDATE[@]}"; do
        if [ -f "$file.backup" ]; then
            rm "$file.backup"
            echo "  🗑️  删除 $file.backup"
        fi
    done
    echo "  ✅ 备份文件已清理"
else
    echo "  📁 备份文件保留在 *.backup"
fi

echo
echo "🎉 重命名完成！"
echo "==============="
echo "✅ 项目已成功重命名为: $NEW_NAME"
echo "✅ 显示名称已更新为: $NEW_DISPLAY"
echo
echo "📋 后续步骤："
echo "1. 检查更新后的文件是否正确"
echo "2. 更新 git 远程仓库名称（如果需要）"
echo "3. 运行测试确保功能正常"
echo "4. 提交更改: git add . && git commit -m 'Rename project to image-gen-mcp'"
echo
echo "🔍 如果发现问题，可以从 *.backup 文件恢复"