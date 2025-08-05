#!/usr/bin/env python3
"""
Add health endpoint to MCP server
"""

import sys

# Read the main.py file
with open('main.py', 'r') as f:
    content = f.read()

# Check if health endpoint already exists
if '@app.get("/health")' in content or 'def health(' in content:
    print("Health endpoint already exists")
    sys.exit(0)

# Find where to insert the health endpoint (after mcp initialization)
insert_pos = content.find('register_order_tools(mcp)')
if insert_pos == -1:
    print("Could not find insertion point")
    sys.exit(1)

# Find the end of that line
line_end = content.find('\n', insert_pos)

# Create the health endpoint code
health_code = '''

# Add health endpoint for monitoring
@mcp.get("/health")
async def health():
    """Health check endpoint for monitoring"""
    return {"status": "healthy", "service": "mcp-server"}
'''

# Insert the health endpoint
new_content = content[:line_end] + health_code + content[line_end:]

# Write back
with open('main.py', 'w') as f:
    f.write(new_content)

print("✅ Added health endpoint to MCP server")