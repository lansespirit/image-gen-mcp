"""
Basic usage example for the GPT Image MCP Server.

This example demonstrates how to use the server programmatically.
"""

import asyncio
import os
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client
from mcp import StdioServerParameters


async def main():
    """Example of using the GPT Image MCP Server."""
    
    # Set up OpenAI API key (required)
    if not os.getenv("OPENAI_API_KEY"):
        print("Please set OPENAI_API_KEY environment variable")
        return
    
    # Create server parameters
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "-m", "gpt_image_mcp.server"],
        env={"OPENAI_API_KEY": os.getenv("OPENAI_API_KEY")},
    )
    
    # Connect to the server
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()
            
            print("Connected to GPT Image MCP Server!")
            
            # List available tools
            tools = await session.list_tools()
            print(f"\nAvailable tools: {[tool.name for tool in tools.tools]}")
            
            # List available resources
            resources = await session.list_resources()
            print(f"Available resources: {[resource.name for resource in resources.resources]}")
            
            # List available prompts
            prompts = await session.list_prompts()
            print(f"Available prompts: {[prompt.name for prompt in prompts.prompts]}")
            
            # Example: Generate an image
            print("\n--- Generating an image ---")
            try:
                result = await session.call_tool(
                    "generate_image",
                    arguments={
                        "prompt": "A beautiful sunset over a mountain lake, digital art style",
                        "quality": "medium",
                        "size": "1024x1024",
                        "style": "vivid"
                    }
                )
                print(f"✅ Image generated successfully!")
                print(f"Image ID: {result.content[0].text}")
                
            except Exception as e:
                print(f"❌ Error generating image: {e}")
            
            # Example: Use a prompt template
            print("\n--- Using a prompt template ---")
            try:
                prompt_result = await session.get_prompt(
                    "creative_image_prompt",
                    arguments={
                        "subject": "a magical forest",
                        "style": "watercolor painting",
                        "mood": "mystical",
                        "color_palette": "cool blues and greens"
                    }
                )
                print(f"✅ Generated prompt: {prompt_result.messages[0].content.text}")
                
            except Exception as e:
                print(f"❌ Error using prompt template: {e}")
            
            # Example: Check storage stats
            print("\n--- Checking storage statistics ---")
            try:
                stats_content, _ = await session.read_resource("storage-stats://overview")
                print(f"📊 Storage stats: {stats_content[:200]}...")
                
            except Exception as e:
                print(f"❌ Error reading storage stats: {e}")


if __name__ == "__main__":
    asyncio.run(main())