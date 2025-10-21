#!/usr/bin/env python3
"""
Pandora Custom HTTP Server - Port 80
HTTP server that serves Vue.js frontend
"""

from http.server import HTTPServer, SimpleHTTPRequestHandler
import os
import json
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import mimetypes
import urllib.request
import urllib.error

class PandoraHTTPHandler(SimpleHTTPRequestHandler):
    """Custom HTTP handler for serving Vue.js app"""
    
    # Backend API configuration
    BACKEND_URL = 'http://localhost:8000'  # User Backend API
    
    def __init__(self, *args, **kwargs):
        # Set directory to Vue.js build output
        super().__init__(*args, directory=self.get_vue_directory(), **kwargs)
    
    @staticmethod
    def get_vue_directory():
        """Get Vue.js frontend directory"""
        # In development: serve from Vue dev server proxy
        # In production: serve from dist folder
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        
        # Try dist folder first (production build)
        dist_path = os.path.join(project_root, 'frontend', 'dist')
        if os.path.exists(dist_path):
            return dist_path
        
        # Fallback to frontend folder
        frontend_path = os.path.join(project_root, 'frontend')
        if os.path.exists(frontend_path):
            return frontend_path
        
        # Fallback to current directory
        return script_dir
    
    def do_GET(self):
        """Handle GET requests - AUTO REDIRECT ALL to HTTPS (Port 443)"""
        # Extract host from headers (default to localhost if not found)
        host = self.headers.get('Host', 'localhost').split(':')[0]
        
        # Build HTTPS URL
        https_url = f"https://{host}:443{self.path}"
        
        # Send 301 Permanent Redirect
        self.send_response(301)
        self.send_header('Location', https_url)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        # Send HTML response explaining redirect
        response_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Redirecting to HTTPS</title>
            <meta http-equiv="refresh" content="0; url={https_url}">
            <style>
                body {{
                    background: #000;
                    color: #FFD700;
                    font-family: 'Courier New', monospace;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    height: 100vh;
                    margin: 0;
                }}
                .container {{
                    text-align: center;
                    border: 3px solid #FFD700;
                    padding: 40px;
                    max-width: 600px;
                }}
                h1 {{ font-size: 2em; margin-bottom: 20px; }}
                a {{ color: #FFA500; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔒 Redirecting to Secure Connection</h1>
                <p>This site requires HTTPS (encrypted connection)</p>
                <p>You will be automatically redirected to:</p>
                <p><a href="{https_url}">{https_url}</a></p>
                <p><small>If not redirected, click the link above</small></p>
            </div>
        </body>
        </html>
        """
        self.wfile.write(response_body.encode('utf-8'))
    
    def do_POST(self):
        """Handle POST requests - Redirect to HTTPS"""
        self.send_https_redirect()
    
    def do_PUT(self):
        """Handle PUT requests - Redirect to HTTPS"""
        self.send_https_redirect()
    
    def do_DELETE(self):
        """Handle DELETE requests - Redirect to HTTPS"""
        self.send_https_redirect()
    
    def serve_vue_app(self, parsed_path):
        """Serve Vue.js single page application"""
        # For SPA, always serve index.html for non-file paths
        if '.' not in os.path.basename(parsed_path.path):
            self.path = '/index.html'
        
        # Serve static files
        try:
            super().do_GET()
        except Exception as e:
            self.send_error(500, f"Error serving file: {str(e)}")
    
    def handle_api_request(self, parsed_path):
        """Handle API requests"""
        path = parsed_path.path
        
        if path == '/api/status':
            self.send_json_response({
                'status': 'online',
                'protocol': 'HTTP',
                'port': 80,
                'server': 'Pandora Custom Python Server',
                'timestamp': datetime.now().isoformat(),
                'warning': 'Unencrypted connection - Consider using HTTPS'
            })
        
        elif path == '/api/health':
            self.send_json_response({'health': 'ok', 'port': 80})
        
        elif path == '/api/server-info':
            self.send_json_response({
                'name': 'Pandora HTTP Server',
                'version': '1.0.0',
                'type': 'Custom Python',
                'port': 80,
                'protocol': 'HTTP',
                'vue_integration': True,
                'client_ip': self.client_address[0],
                'server_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        
        else:
            self.send_json_response({
                'error': 'API endpoint not found'
            }, status=404)
    
    def proxy_to_backend(self, method):
        """Proxy request to backend API"""
        try:
            # Read request body for POST/PUT
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else None
            
            # Build backend URL
            backend_url = f"{self.BACKEND_URL}{self.path}"
            
            # Create request
            req = urllib.request.Request(
                backend_url,
                data=body,
                method=method
            )
            
            # Copy headers
            for header, value in self.headers.items():
                if header.lower() not in ['host', 'connection']:
                    req.add_header(header, value)
            
            # Make request to backend
            try:
                with urllib.request.urlopen(req, timeout=30) as response:
                    # Send response status
                    self.send_response(response.status)
                    
                    # Copy response headers
                    for header, value in response.headers.items():
                        if header.lower() not in ['connection', 'transfer-encoding']:
                            self.send_header(header, value)
                    
                    # Add CORS headers
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
                    self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                    
                    self.end_headers()
                    
                    # Send response body
                    self.wfile.write(response.read())
                    
            except urllib.error.HTTPError as e:
                # Forward error response from backend
                self.send_response(e.code)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                error_body = e.read()
                self.wfile.write(error_body)
                
        except Exception as e:
            print(f"[ERROR] Proxy failed: {e}")
            self.send_error(502, f"Bad Gateway: {str(e)}")
    
    def send_https_redirect(self):
        """Send redirect to HTTPS version"""
        host = self.headers.get('Host', 'localhost').split(':')[0]
        https_url = f"https://{host}:443{self.path}"
        
        self.send_response(301)
        self.send_header('Location', https_url)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        
        self.wfile.write(f"Redirecting to HTTPS: {https_url}".encode('utf-8'))
    
    def send_json_response(self, data, status=200):
        """Send JSON response"""
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def log_message(self, format, *args):
        """Custom logging"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[HTTP-80] {timestamp} | {self.client_address[0]} | {format % args}")
    
    def end_headers(self):
        """Add security headers"""
        # Add basic security headers
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'SAMEORIGIN')
        super().end_headers()


def run_server(host='0.0.0.0', port=80):
    """Run HTTP server"""
    try:
        server_address = (host, port)
        httpd = HTTPServer(server_address, PandoraHTTPHandler)
        
        print("="*70)
        print("[PANDORA HTTP SERVER]")
        print("="*70)
        print(f"[OK] Server started on port {port}")
        print(f"[OK] Protocol: HTTP")
        print(f"[OK] Host: {host}")
        print(f"[OK] Access: http://localhost")
        print(f"[WARNING] This is an unencrypted connection!")
        print(f"[INFO] Serving Vue.js frontend")
        print("="*70)
        print(f"[INFO] Endpoints:")
        print(f"  • http://localhost          - Vue.js App")
        print(f"  • http://localhost/api/status    - Server status")
        print(f"  • http://localhost/api/health    - Health check")
        print(f"  • http://localhost/api/server-info - Server info")
        print("="*70)
        print(f"[INFO] Press Ctrl+C to stop server")
        print("="*70)
        
        httpd.serve_forever()
        
    except KeyboardInterrupt:
        print("\n[STOP] Server stopped by user")
        httpd.server_close()
    except PermissionError:
        print(f"\n[ERROR] Permission denied for port {port}")
        print("[FIX] Run as Administrator (ports < 1024 require admin rights)")
    except OSError as e:
        print(f"\n[ERROR] {e}")
        print(f"[FIX] Port {port} might be in use. Stop other services using this port.")
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")


if __name__ == '__main__':
    import sys
    
    # Parse arguments
    port = 80
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"[ERROR] Invalid port number: {sys.argv[1]}")
            sys.exit(1)
    
    run_server(port=port)

