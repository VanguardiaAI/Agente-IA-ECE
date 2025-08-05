#!/bin/bash

echo "🔍 Debugging MCP server crash..."

# Check MCP server logs in detail
echo "📜 MCP server full logs:"
docker logs eva-mcp-prod --tail 50

# Check if it's a Python error
echo -e "\n❌ Looking for Python errors:"
docker logs eva-mcp-prod 2>&1 | grep -E "Error|Exception|Traceback|Failed" | tail -20

# Check the container's exit code
echo -e "\n🔢 Container exit details:"
docker inspect eva-mcp-prod | grep -A5 "State"

# Try running the MCP server manually to see the error
echo -e "\n🔧 Testing MCP server startup manually:"
docker run --rm -it \
  --network agente-ia-ece_eva_network \
  -e POSTGRES_HOST=postgres \
  -e POSTGRES_USER=eva_user \
  -e POSTGRES_PASSWORD=chatbot_secure_2025! \
  -e POSTGRES_DB=eva_db \
  -e OPENAI_API_KEY="${OPENAI_API_KEY}" \
  -v $(pwd)/knowledge:/app/knowledge:ro \
  agente-ia-ece-mcp-server \
  python main.py 2>&1 | head -50