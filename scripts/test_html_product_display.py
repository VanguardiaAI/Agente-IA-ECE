#!/usr/bin/env python3
"""
Test script to verify HTML product display is working correctly
"""

import asyncio
import json
from datetime import datetime
from websockets import connect
import requests
from colorama import init, Fore, Style

init()

class TestProductDisplay:
    def __init__(self):
        self.base_url = "http://localhost:8080"
        self.ws_url = "ws://localhost:8080/ws/chat/test_client_123"
        
    async def test_product_search_via_websocket(self):
        """Test product search through WebSocket to verify HTML formatting"""
        print(f"\n{Fore.CYAN}Testing Product Search via WebSocket...{Style.RESET_ALL}")
        
        try:
            async with connect(self.ws_url) as websocket:
                print(f"{Fore.GREEN}✓ Connected to WebSocket{Style.RESET_ALL}")
                
                # Wait for welcome message
                welcome = await websocket.recv()
                welcome_data = json.loads(welcome)
                print(f"{Fore.BLUE}Welcome message received: {welcome_data['type']}{Style.RESET_ALL}")
                
                # Test queries
                test_queries = [
                    "busco un diferencial",
                    "necesito cables",
                    "interruptores automáticos"
                ]
                
                for query in test_queries:
                    print(f"\n{Fore.YELLOW}Testing query: '{query}'{Style.RESET_ALL}")
                    
                    # Send search query
                    message = {
                        "message": query,
                        "timestamp": datetime.now().isoformat(),
                        "client_id": "test_client_123",
                        "platform": "wordpress"
                    }
                    
                    await websocket.send(json.dumps(message))
                    print(f"{Fore.GREEN}✓ Query sent{Style.RESET_ALL}")
                    
                    # Receive response
                    response = await websocket.recv()
                    response_data = json.loads(response)
                    
                    if response_data['type'] == 'agent_response':
                        message_content = response_data['message']
                        
                        # Check if response contains HTML
                        if '<div class="eva-product-card"' in message_content:
                            print(f"{Fore.GREEN}✓ HTML product cards detected in response{Style.RESET_ALL}")
                            
                            # Count product cards
                            card_count = message_content.count('eva-product-card')
                            print(f"{Fore.BLUE}  Found {card_count} product cards{Style.RESET_ALL}")
                            
                            # Check for key HTML elements
                            html_elements = [
                                ('Product images', '<img src='),
                                ('Product names', '<h3 style='),
                                ('Prices', '€'),
                                ('Links', '<a href='),
                                ('Styled containers', 'eva-products-list')
                            ]
                            
                            for element_name, element_marker in html_elements:
                                if element_marker in message_content:
                                    print(f"{Fore.GREEN}  ✓ {element_name} found{Style.RESET_ALL}")
                                else:
                                    print(f"{Fore.RED}  ✗ {element_name} not found{Style.RESET_ALL}")
                            
                            # Save sample response for debugging
                            filename = f"test_response_{query.replace(' ', '_')}.html"
                            with open(filename, 'w', encoding='utf-8') as f:
                                f.write(f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Test Response: {query}</title>
    <style>
        body {{ font-family: Arial, sans-serif; padding: 20px; background: #f5f5f5; }}
        .message-content {{ background: white; padding: 20px; border-radius: 8px; }}
    </style>
</head>
<body>
    <h1>Test Response for: "{query}"</h1>
    <div class="message-content">
        {message_content}
    </div>
</body>
</html>
                                """)
                            print(f"{Fore.BLUE}  Response saved to: {filename}{Style.RESET_ALL}")
                            
                        else:
                            print(f"{Fore.YELLOW}⚠ No HTML product cards in response{Style.RESET_ALL}")
                            print(f"{Fore.BLUE}  Response preview: {message_content[:200]}...{Style.RESET_ALL}")
                    
                    # Small delay between queries
                    await asyncio.sleep(2)
                
        except Exception as e:
            print(f"{Fore.RED}✗ WebSocket test failed: {e}{Style.RESET_ALL}")
            return False
        
        return True
    
    async def test_direct_api(self):
        """Test the chat API directly"""
        print(f"\n{Fore.CYAN}Testing Direct API...{Style.RESET_ALL}")
        
        try:
            # Test chat endpoint
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "message": "busco magnetotérmicos",
                    "session_id": "test_session_456"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if data['success']:
                    message = data['response']
                    
                    if '<div class="eva-product-card"' in message:
                        print(f"{Fore.GREEN}✓ API returns HTML formatted products{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.YELLOW}⚠ API response doesn't contain HTML products{Style.RESET_ALL}")
                        print(f"{Fore.BLUE}  Response: {message[:200]}...{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}✗ API returned error: {data.get('error')}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}✗ API request failed: {response.status_code}{Style.RESET_ALL}")
                
        except Exception as e:
            print(f"{Fore.RED}✗ API test failed: {e}{Style.RESET_ALL}")
            return False
        
        return True
    
    def check_server_running(self):
        """Check if the server is running"""
        try:
            response = requests.get(f"{self.base_url}/api/health")
            return response.status_code == 200
        except:
            return False

async def main():
    tester = TestProductDisplay()
    
    print(f"{Fore.CYAN}=== HTML Product Display Test ==={Style.RESET_ALL}")
    
    # Check if server is running
    if not tester.check_server_running():
        print(f"{Fore.RED}✗ Server is not running at {tester.base_url}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Please start the server with: python app.py{Style.RESET_ALL}")
        return
    
    print(f"{Fore.GREEN}✓ Server is running{Style.RESET_ALL}")
    
    # Run tests
    ws_success = await tester.test_product_search_via_websocket()
    api_success = await tester.test_direct_api()
    
    # Summary
    print(f"\n{Fore.CYAN}=== Test Summary ==={Style.RESET_ALL}")
    if ws_success and api_success:
        print(f"{Fore.GREEN}✓ All tests passed!{Style.RESET_ALL}")
        print(f"\n{Fore.YELLOW}Next steps:{Style.RESET_ALL}")
        print("1. Open the generated HTML files in a browser to visually verify the formatting")
        print("2. Test the chat interface at http://localhost:8080")
        print("3. Search for products and verify they display as formatted cards")
    else:
        print(f"{Fore.RED}✗ Some tests failed{Style.RESET_ALL}")
        print(f"\n{Fore.YELLOW}Debugging tips:{Style.RESET_ALL}")
        print("1. Check the agent logs for any errors")
        print("2. Verify the database has products indexed")
        print("3. Check that wordpress_utils.py is being imported correctly")

if __name__ == "__main__":
    asyncio.run(main())