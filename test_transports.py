#!/usr/bin/env python3
"""Test script for GPT Image MCP Server with different transports."""

import asyncio
import json
import sys
import time
from typing import Dict, Any

import httpx


async def test_http_transport(host: str = "localhost", port: int = 3001) -> Dict[str, Any]:
    """Test the HTTP transport endpoint."""
    base_url = f"http://{host}:{port}"
    
    print(f"🧪 Testing HTTP transport at {base_url}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test health check
            print("  📋 Testing health check...")
            health_response = await client.post(
                f"{base_url}/",
                headers={
                    "Content-Type": "application/json",
                },
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "health_check",
                        "arguments": {}
                    }
                }
            )
            
            if health_response.status_code == 200:
                health_data = health_response.json()
                print(f"  ✅ Health check: {health_data.get('result', {}).get('status', 'unknown')}")
            else:
                print(f"  ❌ Health check failed: {health_response.status_code}")
                return {"status": "failed", "error": f"HTTP {health_response.status_code}"}
            
            # Test server info
            print("  📋 Testing server info...")
            info_response = await client.post(
                f"{base_url}/",
                headers={
                    "Content-Type": "application/json",
                },
                json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "server_info",
                        "arguments": {}
                    }
                }
            )
            
            if info_response.status_code == 200:
                info_data = info_response.json()
                server_info = info_data.get('result', {})
                print(f"  📊 Server: {server_info.get('server', {}).get('name', 'Unknown')}")
                print(f"  📊 Version: {server_info.get('server', {}).get('version', 'Unknown')}")
                capabilities = server_info.get('capabilities', {})
                print(f"  🔧 Capabilities: {', '.join([k for k, v in capabilities.items() if v])}")
            else:
                print(f"  ⚠️  Server info failed: {info_response.status_code}")
            
            # Test tools list
            print("  📋 Testing tools list...")
            tools_response = await client.post(
                f"{base_url}/",
                headers={
                    "Content-Type": "application/json",
                },
                json={
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/list",
                    "params": {}
                }
            )
            
            if tools_response.status_code == 200:
                tools_data = tools_response.json()
                tools = tools_data.get('result', {}).get('tools', [])
                print(f"  🔧 Available tools: {len(tools)}")
                for tool in tools[:3]:  # Show first 3 tools
                    print(f"    - {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')[:50]}...")
            else:
                print(f"  ⚠️  Tools list failed: {tools_response.status_code}")
            
            return {
                "status": "success",
                "health": health_data.get('result', {}),
                "server_info": info_data.get('result', {}),
                "tools_count": len(tools_data.get('result', {}).get('tools', []))
            }
    
    except Exception as e:
        print(f"  ❌ HTTP test failed: {e}")
        return {"status": "failed", "error": str(e)}


def test_stdio_import():
    """Test that the server can be imported and configured for stdio."""
    print("🧪 Testing stdio import and configuration...")
    
    try:
        # Test importing the server module
        print("  📦 Importing server module...")
        import gpt_image_mcp.server
        print("  ✅ Server module imported successfully")
        
        # Test argument parsing
        print("  📋 Testing argument parsing...")
        import argparse
        from unittest.mock import patch
        
        # Mock sys.argv for stdio
        with patch('sys.argv', ['server.py', '--transport', 'stdio', '--log-level', 'INFO']):
            args = gpt_image_mcp.server.parse_arguments()
            assert args.transport == 'stdio'
            assert args.log_level == 'INFO'
            print("  ✅ STDIO arguments parsed correctly")
        
        # Mock sys.argv for HTTP
        with patch('sys.argv', ['server.py', '--transport', 'streamable-http', '--port', '3001']):
            args = gpt_image_mcp.server.parse_arguments()
            assert args.transport == 'streamable-http'
            assert args.port == 3001
            print("  ✅ HTTP arguments parsed correctly")
        
        return {"status": "success"}
    
    except Exception as e:
        print(f"  ❌ STDIO test failed: {e}")
        return {"status": "failed", "error": str(e)}


async def main():
    """Main test runner."""
    print("🚀 GPT Image MCP Server Transport Tests")
    print("=" * 50)
    
    results = {}
    
    # Test 1: STDIO import and configuration
    print("\n1️⃣  STDIO Transport Test")
    results['stdio'] = test_stdio_import()
    
    # Test 2: HTTP transport (if available)
    print("\n2️⃣  HTTP Transport Test")
    
    # Check if server is running on default port
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(('localhost', 3001))
        sock.close()
        
        if result == 0:
            print("  🔗 Server appears to be running on localhost:3001")
            results['http'] = await test_http_transport()
        else:
            print("  ⚠️  No server running on localhost:3001")
            print("  💡 Start server with: ./run.sh dev")
            results['http'] = {"status": "skipped", "reason": "Server not running"}
    
    except Exception as e:
        print(f"  ❌ Port check failed: {e}")
        results['http'] = {"status": "failed", "error": str(e)}
    
    # Test summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    for transport, result in results.items():
        status = result.get('status', 'unknown')
        if status == 'success':
            print(f"✅ {transport.upper()}: {status}")
        elif status == 'skipped':
            print(f"⚠️  {transport.upper()}: {status} ({result.get('reason', 'Unknown')})")
        else:
            print(f"❌ {transport.upper()}: {status} ({result.get('error', 'Unknown')})")
    
    # Show next steps
    print("\n🎯 Next Steps:")
    if results.get('stdio', {}).get('status') == 'success':
        print("  • STDIO transport ready for Claude Desktop integration")
        print("  • Use: python -m gpt_image_mcp.server --transport stdio")
    
    if results.get('http', {}).get('status') == 'success':
        print("  • HTTP transport working for web deployment")
        print("  • Server accessible at: http://localhost:3001")
    elif results.get('http', {}).get('status') == 'skipped':
        print("  • Start HTTP server with: ./run.sh dev")
        print("  • Then test with: python test_transports.py")
    
    print("\n📚 Available commands:")
    print("  • ./run.sh dev      # Development server (HTTP)")
    print("  • ./run.sh stdio    # Claude Desktop (STDIO)")
    print("  • ./run.sh prod     # Production deployment")
    print("  • ./run.sh test     # Run full test suite")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test runner failed: {e}")
        sys.exit(1)