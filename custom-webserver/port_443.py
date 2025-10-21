#!/usr/bin/env python3
"""
Pandora Custom HTTPS Server - Port 443
HTTPS server that serves Vue.js frontend with SSL/TLS encryption
"""

from http.server import HTTPServer, SimpleHTTPRequestHandler
import ssl
import os
import json
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import mimetypes
import urllib.request
import urllib.error
import threading
import requests
import jwt  # PyJWT for token decoding
import sys

# Add backend-admin to path for Elasticsearch service
backend_admin_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend-admin'))
if backend_admin_dir not in sys.path:
    sys.path.insert(0, backend_admin_dir)

try:
    from services.elasticsearch_service import elasticsearch_service
    ELASTICSEARCH_AVAILABLE = True
except ImportError:
    ELASTICSEARCH_AVAILABLE = False
    print("[WARNING] Elasticsearch service not available")

class PandoraHTTPSHandler(SimpleHTTPRequestHandler):
    """Custom HTTPS handler for serving Vue.js app"""
    
    # Backend API configuration
    BACKEND_URL = 'http://localhost:8000'  # User Backend API
    
    def __init__(self, *args, **kwargs):
        # Set directory to Vue.js build output
        super().__init__(*args, directory=self.get_vue_directory(), **kwargs)
    
    @staticmethod
    def get_vue_directory():
        """Get Vue.js frontend directory"""
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

    def log_honeypot_activity(self, method, path, headers, body=None, response_status=None, response_size=None):
        """Log all activities to honeypot backend (async) - ENHANCED with HTTPOnly cookie tracking"""
        try:
            # Extract user info from HTTPOnly cookies
            user_id = None
            username = None
            is_authenticated = False
            cookie_header = headers.get('Cookie', '')
            
            # DEBUG: Print cookie header
            if cookie_header:
                print(f"[DEBUG] Cookie header present: {cookie_header[:100]}...")
            else:
                print(f"[DEBUG] No Cookie header found")
            
            # Try to extract access_token from Cookie header
            if 'access_token=' in cookie_header:
                try:
                    # Extract token from cookie
                    token = None
                    for cookie in cookie_header.split(';'):
                        cookie = cookie.strip()
                        if cookie.startswith('access_token='):
                            token = cookie.split('=', 1)[1]
                            break
                    
                    if token:
                        print(f"[DEBUG] Token extracted: {token[:30]}...")
                        # Decode JWT (without verification for logging purposes)
                        # In production, you should verify signature
                        decoded = jwt.decode(token, options={"verify_signature": False})
                        user_id = decoded.get('sub')  # User ID from token
                        is_authenticated = True
                        print(f"[HONEYPOT] ✓ Authenticated user detected: user_id={user_id}")
                    else:
                        print(f"[DEBUG] Token extraction failed")
                except Exception as e:
                    print(f"[HONEYPOT] ✗ Token decode failed: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"[DEBUG] No access_token in cookie")
            
            # Fallback: Check Authorization header (for API clients)
            if not is_authenticated:
                auth_header = headers.get('Authorization', '')
                if auth_header.startswith('Bearer '):
                    is_authenticated = True

            # Determine activity type
            activity_type = 'page_view' if method == 'GET' and not path.startswith('/api/') else 'api_call'

            if '/api/v1/scan' in path:
                activity_type = 'scan'
            elif '/api/v1/auth/login' in path:
                activity_type = 'login_attempt'
            elif '/api/v1/auth/register' in path:
                activity_type = 'registration'

            # Calculate suspicious score
            suspicious_score, suspicious_reasons = self.calculate_suspicious_score(path, headers, body)

            # Prepare log data with user tracking
            log_data = {
                'user_id': int(user_id) if user_id else None,  # Track authenticated users
                'is_authenticated': is_authenticated,
                'session_id': headers.get('Cookie', '').split('session_id=')[-1].split(';')[0] if 'session_id=' in headers.get('Cookie', '') else None,
                'request_method': method,
                'request_path': path,
                'request_headers': dict(headers),
                'request_body': body[:5000] if body else None,  # Limit body size
                'response_status': response_status,
                'response_size': response_size,
                'activity_type': activity_type,
                'suspicious_score': suspicious_score,
                'suspicious_reasons': suspicious_reasons
            }

            # Send to honeypot backend (async)
            def send_log():
                try:
                    response = requests.post(
                        'http://localhost:9000/api/v1/honeypot/log',  # Admin Backend API
                        json=log_data,
                        timeout=5
                    )
                except:
                    pass  # Fail silently to not break webserver

            # Run in background thread
            threading.Thread(target=send_log, daemon=True).start()
            
            # Also send to Elasticsearch (async, non-blocking)
            if ELASTICSEARCH_AVAILABLE:
                def send_to_elasticsearch():
                    try:
                        es_data = {
                            'user_id': log_data.get('user_id'),
                            'is_authenticated': log_data.get('is_authenticated', False),
                            'session_id': log_data.get('session_id'),
                            'ip_address': self.client_address[0],
                            'user_agent': headers.get('User-Agent', ''),
                            'request_method': method,
                            'request_path': path,
                            'request_headers': dict(headers),
                            'request_body': body[:5000] if body else None,
                            'response_status': response_status,
                            'response_size': response_size,
                            'activity_type': activity_type,
                            'suspicious_score': suspicious_score,
                            'suspicious_reasons': suspicious_reasons,
                            'timestamp': datetime.now().isoformat()
                        }
                        elasticsearch_service.log_honeypot_activity(es_data)
                    except:
                        pass  # Fail silently
                
                threading.Thread(target=send_to_elasticsearch, daemon=True).start()

        except Exception as e:
            # Fail silently to not break webserver
            print(f"[HONEYPOT ERROR] Failed to log activity: {e}")

    def calculate_suspicious_score(self, path, headers, body):
        """Calculate suspicious score based on request patterns"""
        score = 0
        reasons = []

        # SQL injection patterns
        sql_patterns = ["'", '"', ';', 'union', 'select', 'drop', 'insert', 'update', 'delete']
        path_lower = path.lower()

        for pattern in sql_patterns:
            if pattern in path_lower:
                score += 20
                reasons.append(f"Potential SQL injection: {pattern}")
                break

        # Path traversal attempts
        if '../' in path_lower or '..\\' in path_lower:
            score += 30
            reasons.append("Path traversal attempt")

        # Scanner activity
        if '/api/v1/scanner/' in path_lower:
            score += 15
            reasons.append("Scanner activity detected")

        # Unusual user agents
        user_agent = headers.get('User-Agent', '').lower()
        suspicious_uas = ['sqlmap', 'nmap', 'nessus', 'openvas', 'nikto', 'w3af', 'burp']
        for ua in suspicious_uas:
            if ua in user_agent:
                score += 25
                reasons.append(f"Suspicious user agent: {ua}")
                break

        return min(100, score), reasons

    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)

        # Log honeypot activity first
        self.log_honeypot_activity('GET', self.path, self.headers)

        # Proxy API requests to backend
        if parsed_path.path.startswith('/api/v1/'):
            self.proxy_to_backend('GET')
        # Local API endpoints
        elif parsed_path.path.startswith('/api/'):
            self.handle_api_request(parsed_path)
        # Serve Vue.js app
        else:
            self.serve_vue_app(parsed_path)
    
    def do_POST(self):
        """Handle POST requests - proxy to backend"""
        parsed_path = urlparse(self.path)

        # Read request body ONCE
        content_length = int(self.headers.get('Content-Length', 0))
        request_body = self.rfile.read(content_length) if content_length > 0 else None
        
        # Proxy API requests to backend
        if parsed_path.path.startswith('/api/v1/'):
            # Log honeypot activity (non-blocking)
            try:
                body_str = request_body.decode('utf-8', errors='ignore') if request_body else None
                threading.Thread(target=self.log_honeypot_activity, args=('POST', self.path, dict(self.headers), body_str), daemon=True).start()
            except:
                pass
            
            # Proxy with pre-read body
            self.proxy_to_backend('POST', request_body)
        else:
            self.send_error(501, "Unsupported method ('POST')")
    
    def do_PUT(self):
        """Handle PUT requests - proxy to backend"""
        parsed_path = urlparse(self.path)

        # Read request body ONCE
        content_length = int(self.headers.get('Content-Length', 0))
        request_body = self.rfile.read(content_length) if content_length > 0 else None

        if parsed_path.path.startswith('/api/v1/'):
            # Log honeypot activity (non-blocking)
            try:
                body_str = request_body.decode('utf-8', errors='ignore') if request_body else None
                threading.Thread(target=self.log_honeypot_activity, args=('PUT', self.path, dict(self.headers), body_str), daemon=True).start()
            except:
                pass
            
            # Proxy with pre-read body
            self.proxy_to_backend('PUT', request_body)
        else:
            self.send_error(501, "Unsupported method ('PUT')")
    
    def do_DELETE(self):
        """Handle DELETE requests - proxy to backend"""
        parsed_path = urlparse(self.path)

        # Read request body for logging (DELETE usually doesn't have body, but just in case)
        content_length = int(self.headers.get('Content-Length', 0))
        request_body = self.rfile.read(content_length) if content_length > 0 else None
        body_str = request_body.decode('utf-8', errors='ignore') if request_body else None

        # Log honeypot activity
        self.log_honeypot_activity('DELETE', self.path, self.headers, body_str)

        if parsed_path.path.startswith('/api/v1/'):
            self.proxy_to_backend('DELETE')
        else:
            self.send_error(501, "Unsupported method ('DELETE')")
    
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
                'protocol': 'HTTPS',
                'port': 443,
                'server': 'Pandora Custom Python Server',
                'timestamp': datetime.now().isoformat(),
                'encrypted': True,
                'tls_version': getattr(self.request, 'version', lambda: 'TLS')()
            })
        
        elif path == '/api/health':
            self.send_json_response({'health': 'ok', 'port': 443, 'secure': True})
        
        elif path == '/api/server-info':
            self.send_json_response({
                'name': 'Pandora HTTPS Server',
                'version': '1.0.0',
                'type': 'Custom Python',
                'port': 443,
                'protocol': 'HTTPS',
                'encryption': 'TLS/SSL',
                'vue_integration': True,
                'client_ip': self.client_address[0],
                'server_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'secure_connection': True
            })
        
        elif path == '/api/ssl-info':
            # Get SSL/TLS connection info
            try:
                cipher = self.request.cipher()
                self.send_json_response({
                    'cipher_name': cipher[0] if cipher else 'unknown',
                    'protocol': cipher[1] if cipher else 'unknown',
                    'bits': cipher[2] if cipher else 0,
                    'encrypted': True
                })
            except:
                self.send_json_response({
                    'encrypted': True,
                    'info': 'SSL info not available'
                })
        
        else:
            self.send_json_response({
                'error': 'API endpoint not found'
            }, status=404)
    
    def proxy_to_backend(self, method, body=None):
        """Proxy request to backend API"""
        try:
            # Use pre-read body if provided, otherwise read from stream
            if body is None:
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
            print(f"[DEBUG] Proxying to: {backend_url}")
            try:
                with urllib.request.urlopen(req, timeout=30) as response:
                    # Send response status
                    self.send_response(response.status)
                    
                    # Add CORS headers FIRST (before other headers)
                    origin = self.headers.get('Origin')
                    if origin:
                        self.send_header('Access-Control-Allow-Origin', origin)
                        self.send_header('Access-Control-Allow-Credentials', 'true')
                    else:
                        # For cookies to work with localhost, we need specific origin
                        self.send_header('Access-Control-Allow-Origin', 'https://localhost')
                        self.send_header('Access-Control-Allow-Credentials', 'true')
                    self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
                    self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, Cookie')
                    self.send_header('Access-Control-Expose-Headers', 'Set-Cookie')
                    
                    # Copy response headers (INCLUDING Set-Cookie!)
                    for header, value in response.headers.items():
                        if header.lower() not in ['connection', 'transfer-encoding']:
                            self.send_header(header, value)
                    
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
            try:
                self.send_error(502, f"Bad Gateway: {str(e)}")
            except:
                # Connection already closed, just log
                print(f"[ERROR] Cannot send error response (connection closed)")
    
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
        origin = self.headers.get('Origin')
        if origin:
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Access-Control-Allow-Credentials', 'true')
        else:
            # For cookies to work with localhost, we need specific origin
            self.send_header('Access-Control-Allow-Origin', 'https://localhost')
            self.send_header('Access-Control-Allow-Credentials', 'true')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, Cookie')
        self.send_header('Access-Control-Expose-Headers', 'Set-Cookie')
        self.end_headers()
    
    def log_message(self, format, *args):
        """Custom logging with encryption indicator"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[HTTPS-443] {timestamp} | {self.client_address[0]} | {format % args} | Encrypted")
    
    def end_headers(self):
        """Add security headers"""
        # Enhanced security headers for HTTPS
        self.send_header('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'SAMEORIGIN')
        self.send_header('X-XSS-Protection', '1; mode=block')
        super().end_headers()


def run_server(host='0.0.0.0', port=443, certfile=None, keyfile=None):
    """Run HTTPS server with SSL/TLS"""
    try:
        # Use our self-signed certificate in current directory
        if not certfile or not keyfile:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            certfile = certfile or os.path.join(script_dir, 'server.crt')
            keyfile = keyfile or os.path.join(script_dir, 'server.key')
        
        # Verify certificates exist
        if not os.path.exists(certfile):
            print(f"[ERROR] Certificate file not found: {certfile}")
            print("[FIX] Generate certificate with: cd nginx && generate_cert.bat")
            return
        
        if not os.path.exists(keyfile):
            print(f"[ERROR] Key file not found: {keyfile}")
            print("[FIX] Generate key with: cd nginx && generate_cert.bat")
            return
        
        # Create server
        server_address = (host, port)
        httpd = HTTPServer(server_address, PandoraHTTPSHandler)
        
        # Wrap with SSL
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile, keyfile)
        
        # Security settings
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.set_ciphers('HIGH:!aNULL:!MD5')
        
        httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
        
        print("="*70)
        print("[PANDORA HTTPS SERVER]")
        print("="*70)
        print(f"[OK] Server started on port {port}")
        print(f"[OK] Protocol: HTTPS (TLS/SSL)")
        print(f"[OK] Host: {host}")
        print(f"[OK] Access: https://localhost")
        print(f"[OK] Secure encrypted connection!")
        print(f"[OK] Serving Vue.js frontend")
        print("="*70)
        print(f"[SSL] Certificate: {certfile}")
        print(f"[SSL] Key: {keyfile}")
        print(f"[SSL] TLS Version: 1.2+")
        print("="*70)
        print(f"[INFO] Endpoints:")
        print(f"  • https://localhost          - Vue.js App")
        print(f"  • https://localhost/api/status    - Server status")
        print(f"  • https://localhost/api/health    - Health check")
        print(f"  • https://localhost/api/server-info - Server info")
        print(f"  • https://localhost/api/ssl-info    - SSL/TLS info")
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
    except ssl.SSLError as e:
        print(f"\n[ERROR] SSL Error: {e}")
        print("[FIX] Check SSL certificate and key files")
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")


if __name__ == '__main__':
    import sys
    
    # Parse arguments
    port = 443
    certfile = None
    keyfile = None
    
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"[ERROR] Invalid port number: {sys.argv[1]}")
            sys.exit(1)
    
    if len(sys.argv) > 3:
        certfile = sys.argv[2]
        keyfile = sys.argv[3]
    
    run_server(port=port, certfile=certfile, keyfile=keyfile)

