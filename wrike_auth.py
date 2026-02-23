#!/usr/bin/env python3
"""Wrike OAuth2 auth — browser-based token exchange to bypass proxy blocks."""

import http.server
import json
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path
from urllib.parse import urlparse, parse_qs

TOKEN_FILE = Path('/Users/j0s028j/Documents/Projects/hvac-tnt-dashboard/.wrike_tokens.json')
CLIENT_ID = 'jyrxE3LL'
CLIENT_SECRET = 'A1wnbgNz1BqJzSOhqzaIybI'
REDIRECT_URI = 'http://localhost:8765'
PROXY = 'http://sysproxy.wal-mart.com:8080'

token_saved = False

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global token_saved
        query = parse_qs(urlparse(self.path).query)
        
        if 'code' in query:
            code = query['code'][0]
            # Return a page that does the token exchange in the browser
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            page = f'''<!DOCTYPE html>
<html><head><title>Wrike Auth</title></head>
<body style="font-family:-apple-system,sans-serif;text-align:center;padding:60px;background:#f3f4f6;">
<div style="max-width:500px;margin:0 auto;background:white;border-radius:12px;padding:40px;box-shadow:0 4px 6px rgba(0,0,0,0.1);">
    <div id="status">
        <h2 style="color:#0071dc;">🔄 Exchanging token...</h2>
        <p style="color:#666;">Please wait...</p>
    </div>
</div>
<script>
async function exchangeToken() {{
    try {{
        const resp = await fetch('https://login.wrike.com/oauth2/token', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/x-www-form-urlencoded' }},
            body: 'client_id={CLIENT_ID}&client_secret={CLIENT_SECRET}&grant_type=authorization_code&code={code}&redirect_uri={REDIRECT_URI}'
        }});
        const data = await resp.json();
        if (data.access_token) {{
            // Send tokens back to local server
            await fetch('http://localhost:8765/save', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify(data)
            }});
            document.getElementById('status').innerHTML = '<h2 style="color:#2a8703;">✅ Connected to Wrike!</h2><p style="color:#666;">You can close this tab.</p>';
        }} else {{
            throw new Error(data.error_description || data.error || 'Unknown error');
        }}
    }} catch(e) {{
        // CORS blocked? Show manual fallback
        document.getElementById('status').innerHTML = `
            <h2 style="color:#f59e0b;">⚠️ Auto-exchange blocked (CORS)</h2>
            <p style="color:#666;">Copy the code below and paste it in the terminal:</p>
            <input type="text" value="{code}" readonly 
                   style="width:100%;padding:12px;font-family:monospace;font-size:14px;border:2px solid #0071dc;border-radius:8px;text-align:center;"
                   onclick="this.select()">
            <p style="color:#999;font-size:12px;margin-top:8px;">Error: ${{e.message}}</p>
        `;
    }}
}}
exchangeToken();
</script>
</body></html>'''
            self.wfile.write(page.encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        global token_saved
        if self.path == '/save':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            token_data = json.loads(body)
            token_data['saved_at'] = time.time()
            with open(TOKEN_FILE, 'w') as f:
                json.dump(token_data, f, indent=2)
            os.chmod(TOKEN_FILE, 0o600)
            token_saved = True
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_OPTIONS(self):
        # Handle CORS preflight
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def log_message(self, *a): pass


def main():
    import subprocess
    
    print('\n🔑 Wrike OAuth2 Authorization')
    print('=' * 40)
    
    # Check existing tokens
    if TOKEN_FILE.exists():
        try:
            with open(TOKEN_FILE) as f:
                tokens = json.load(f)
            if tokens.get('refresh_token'):
                # Try refresh
                print('   Found existing tokens, refreshing...')
                result = subprocess.run([
                    'curl', '-s', '--proxy', PROXY, '--proxy-negotiate', '-u', ':',
                    '-X', 'POST', 'https://www.wrike.com/oauth2/token',
                    '-d', f'client_id={CLIENT_ID}&client_secret={CLIENT_SECRET}&grant_type=refresh_token&refresh_token={tokens["refresh_token"]}',
                    '-H', 'Content-Type: application/x-www-form-urlencoded'
                ], capture_output=True, text=True)
                if result.stdout.strip():
                    new_tokens = json.loads(result.stdout)
                    if 'access_token' in new_tokens:
                        new_tokens['saved_at'] = time.time()
                        with open(TOKEN_FILE, 'w') as f:
                            json.dump(new_tokens, f, indent=2)
                        os.chmod(TOKEN_FILE, 0o600)
                        print('   ✅ Tokens refreshed successfully!')
                        # Test
                        test = subprocess.run([
                            'curl', '-s', '--proxy', PROXY,
                            '-H', f'Authorization: Bearer {new_tokens["access_token"]}',
                            'https://www.wrike.com/api/v4/contacts?me=true'
                        ], capture_output=True, text=True)
                        me = json.loads(test.stdout)
                        name = me['data'][0].get('firstName','') + ' ' + me['data'][0].get('lastName','')
                        print(f'   🎉 Authenticated as: {name.strip()}')
                        return
        except Exception as e:
            print(f'   Refresh failed: {e}, starting fresh...')
    
    # Start server that handles multiple requests
    server = http.server.HTTPServer(('localhost', 8765), Handler)
    server.timeout = 120
    
    auth_url = f'https://login.wrike.com/oauth2/authorize/v4?client_id={CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}'
    print(f'\n   🌐 Opening browser...')
    webbrowser.open(auth_url)
    print('   Waiting for authorization + token exchange...')
    
    # Handle requests until token is saved or timeout
    start = time.time()
    while not token_saved and (time.time() - start) < 120:
        server.handle_request()
    
    server.server_close()
    
    if token_saved:
        print('   ✅ Tokens saved!')
        # Verify
        with open(TOKEN_FILE) as f:
            tokens = json.load(f)
        test = subprocess.run([
            'curl', '-s', '--proxy', PROXY,
            '-H', f'Authorization: Bearer {tokens["access_token"]}',
            'https://www.wrike.com/api/v4/contacts?me=true'
        ], capture_output=True, text=True)
        try:
            me = json.loads(test.stdout)
            name = me['data'][0].get('firstName','') + ' ' + me['data'][0].get('lastName','')
            print(f'\n   🎉 Success! Authenticated as: {name.strip()}')
            print(f'   Tokens saved to {TOKEN_FILE}')
            print(f'   You can now run: python3 refresh.py')
        except:
            print(f'   Tokens saved but API test failed. Response: {test.stdout[:200]}')
    else:
        # Check if user needs to paste code manually
        print('\n   ⏰ Timeout or CORS blocked the exchange.')
        code = input('   Paste the auth code from the browser: ').strip()
        if code:
            # Exchange via browser-accessible endpoint
            print('   This requires browser access to login.wrike.com.')
            print('   Try running the auth from a non-VPN network, or use the manual export workflow.')

if __name__ == '__main__':
    main()
