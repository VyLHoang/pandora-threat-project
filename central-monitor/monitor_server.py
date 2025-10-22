"""
Central Monitoring Server - NO JAVASCRIPT VERSION
Port 27009 - Server-Side Rendered with Jinja2 Templates
PURE PYTHON + HTML + CSS - Maximum Security
WITH AUTHENTICATION
"""

from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from flask_cors import CORS
from datetime import datetime, timedelta
from collections import deque
from sqlalchemy import create_engine, func, desc, and_
from sqlalchemy.orm import sessionmaker
from functools import wraps
import sys
import os
import requests

# Import auth config
from auth_config import AuthConfig

# Add parent to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import backend models from Admin Backend
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend-admin'))
from models.attack import AttackLog
from models.honeypot import HoneypotLog
try:
    from config import settings
except ImportError:
    from config_simple import settings
    print("[INFO] Using simple config (SQLite) for Central Monitor")

# Setup Flask app with templates and static folder
app = Flask(__name__, 
            template_folder='templates',
            static_folder='admin-ui',
            static_url_path='/static')

# Session configuration
app.config['SECRET_KEY'] = AuthConfig.SESSION_SECRET_KEY
app.config['SESSION_COOKIE_NAME'] = AuthConfig.SESSION_COOKIE_NAME
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=AuthConfig.SESSION_LIFETIME_HOURS)

CORS(app)

# Add timedelta to Jinja2 globals for timezone conversion (Vietnam = UTC+7)
app.jinja_env.globals.update(timedelta=timedelta)

# Database setup
DATABASE_URL = settings.DATABASE_URL.replace('postgresql+psycopg://', 'postgresql://')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# In-memory logs (last 200)
recent_logs = deque(maxlen=200)
stats = {
    'total_events': 0,
    'services': {},
    'ports': {},
}


# ========================================
# AUTHENTICATION DECORATORS & ROUTES
# ========================================

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and authentication"""
    # If already logged in, redirect to dashboard
    if session.get('logged_in'):
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        # Verify credentials
        if AuthConfig.verify_password(username, password):
            session['logged_in'] = True
            session['username'] = username
            session['login_time'] = datetime.now().isoformat()
            session.permanent = True
            
            print(f"[AUTH] ✓ Login successful: {username} from {request.remote_addr}")
            
            # Redirect to next page or dashboard
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            print(f"[AUTH] ✗ Login failed: {username} from {request.remote_addr}")
            return render_template('login.html', error='Invalid username or password')
    
    # GET request - show login form
    return render_template('login.html')


@app.route('/logout')
def logout():
    """Logout and clear session"""
    username = session.get('username', 'unknown')
    session.clear()
    print(f"[AUTH] Logout: {username}")
    return redirect(url_for('login'))


# ========================================
# TEMPLATE ROUTES (Server-Side Rendered)
# ========================================

@app.route('/')
@login_required
def index():
    """Dashboard home page"""
    db = SessionLocal()
    try:
        # Get statistics
        recent_attacks = db.query(AttackLog).filter(
            AttackLog.detected_at > datetime.now() - timedelta(hours=24)
        ).count()
        
        honeypot_activities = db.query(HoneypotLog).filter(
            HoneypotLog.timestamp > datetime.now() - timedelta(hours=24)
        ).count()
        
        # Get total users from User DB via API
        total_users = 0
        try:
            resp = requests.get('http://localhost:9000/api/v1/users/stats', timeout=2)
            if resp.status_code == 200:
                total_users = resp.json().get('total_users', 0)
        except:
            pass
        
        dashboard_stats = {
            'total_events': stats['total_events'],
            'recent_attacks': recent_attacks,
            'honeypot_activities': honeypot_activities,
            'total_users': total_users
        }
        
        return render_template('index.html', 
                             stats=dashboard_stats,
                             current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    finally:
        db.close()


@app.route('/traffic')
@login_required
def traffic_page():
    """Traffic monitoring page"""
    traffic_stats = {
        'total_events': stats['total_events'],
        'services_count': len(stats['services']),
        'ports_count': len(stats['ports']),
        'services': stats['services']
    }
    
    # Get recent logs
    logs = list(reversed(list(recent_logs)))[:100]
    
    return render_template('traffic.html',
                         stats=traffic_stats,
                         logs=logs,
                         current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


@app.route('/attacks')
@login_required
def attacks_page():
    """IDS attacks monitoring page"""
    db = SessionLocal()
    try:
        # Get filter parameters
        severity = request.args.get('severity', '')
        attack_type = request.args.get('attack_type', '')
        limit = int(request.args.get('limit', 50))
        
        # Build query
        query = db.query(AttackLog)
        
        if severity:
            query = query.filter(AttackLog.severity == severity)
        
        if attack_type:
            query = query.filter(AttackLog.attack_type == attack_type)
        
        # Get attacks
        attacks = query.order_by(desc(AttackLog.detected_at)).limit(limit).all()
        
        # Get statistics
        total_attacks = db.query(AttackLog).count()
        unique_ips = db.query(AttackLog.source_ip).distinct().count()
        critical_attacks = db.query(AttackLog).filter(AttackLog.severity == 'critical').count()
        high_attacks = db.query(AttackLog).filter(AttackLog.severity == 'high').count()
        
        # Get top attackers
        top_attackers = db.query(
            AttackLog.source_ip,
            func.count(AttackLog.id).label('count'),
            AttackLog.city,
            AttackLog.country
        ).group_by(
            AttackLog.source_ip,
            AttackLog.city,
            AttackLog.country
        ).order_by(desc('count')).limit(5).all()
        
        top_attackers_list = [
            {
                'ip': ip,
                'count': count,
                'location': f"{city or 'Unknown'}, {country or 'Unknown'}"
            }
            for ip, count, city, country in top_attackers
        ]
        
        attack_stats = {
            'total_attacks': total_attacks,
            'unique_ips': unique_ips,
            'critical_attacks': critical_attacks,
            'high_attacks': high_attacks,
            'top_attackers': top_attackers_list
        }
        
        return render_template('attacks.html',
                             attacks=attacks,
                             stats=attack_stats,
                             current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    finally:
        db.close()


@app.route('/users')
@login_required
def users_page():
    """User monitoring page"""
    return render_template('users.html')


@app.route('/honeypot')
@login_required
def honeypot_page():
    """Honeypot monitoring page"""
    db = SessionLocal()
    try:
        # Get filter parameters
        activity_type = request.args.get('activity_type', '')
        user_filter = request.args.get('user_filter', '')
        suspicious_only = request.args.get('suspicious_only', '') == 'true'
        limit = int(request.args.get('limit', 20))
        
        # Build query
        query = db.query(HoneypotLog)
        
        if activity_type:
            query = query.filter(HoneypotLog.activity_type == activity_type)
        
        if user_filter == 'authenticated':
            query = query.filter(HoneypotLog.is_authenticated == True)
        elif user_filter == 'anonymous':
            query = query.filter(HoneypotLog.is_authenticated == False)
        
        if suspicious_only:
            query = query.filter(HoneypotLog.suspicious_score >= 50)
        
        # Get logs
        logs = query.order_by(desc(HoneypotLog.timestamp)).limit(limit).all()
        
        # Get statistics
        total_logs = db.query(HoneypotLog).count()
        unique_ips = db.query(HoneypotLog.ip_address).distinct().count()
        authenticated_users = db.query(HoneypotLog).filter(HoneypotLog.is_authenticated == True).count()
        anonymous_users = db.query(HoneypotLog).filter(HoneypotLog.is_authenticated == False).count()
        suspicious_activities = db.query(HoneypotLog).filter(HoneypotLog.suspicious_score >= 50).count()
        
        # Get activity breakdown
        activity_counts = db.query(
            HoneypotLog.activity_type,
            func.count(HoneypotLog.id).label('count')
        ).group_by(HoneypotLog.activity_type).all()
        
        top_activities = {activity: count for activity, count in activity_counts}
        
        # Get top suspicious IPs
        top_suspicious = db.query(
            HoneypotLog.ip_address,
            func.count(HoneypotLog.id).label('activity_count'),
            func.max(HoneypotLog.suspicious_score).label('max_suspicious_score'),
            func.max(HoneypotLog.timestamp).label('last_seen')
        ).filter(
            HoneypotLog.suspicious_score >= 30
        ).group_by(HoneypotLog.ip_address).order_by(desc('max_suspicious_score')).limit(5).all()
        
        top_suspicious_ips = [
            {
                'ip': ip,
                'activity_count': count,
                'max_suspicious_score': max_score,
                'last_seen': last_seen.isoformat()
            }
            for ip, count, max_score, last_seen in top_suspicious
        ]
        
        honeypot_stats = {
            'total_logs': total_logs,
            'unique_ips': unique_ips,
            'authenticated_users': authenticated_users,
            'anonymous_users': anonymous_users,
            'suspicious_activities': suspicious_activities,
            'top_activities': top_activities,
            'top_suspicious_ips': top_suspicious_ips
        }
        
        return render_template('honeypot.html',
                             logs=logs,
                             stats=honeypot_stats,
                             current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    finally:
        db.close()


# ========================================
# API ROUTES (for backend integration)
# ========================================

@app.route('/api/logs', methods=['POST'])
def receive_log():
    """Receive logs from monitored services"""
    try:
        log_data = request.json
        
        # Add timestamp if not present
        if 'timestamp' not in log_data:
            log_data['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Store in memory
        recent_logs.append(log_data)
        
        # Update statistics
        stats['total_events'] += 1
        
        service = log_data.get('service', 'unknown')
        stats['services'][service] = stats['services'].get(service, 0) + 1
        
        port = log_data.get('port', 'unknown')
        stats['ports'][port] = stats['ports'].get(port, 0) + 1
        
        return jsonify({'status': 'ok'}), 200
    
    except Exception as e:
        print(f"[ERROR] Failed to receive log: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats')
def get_stats():
    """Get monitoring statistics"""
    return jsonify({
        'total_events': stats['total_events'],
        'services': stats['services'],
        'ports': stats['ports'],
        'recent_count': len(recent_logs)
    })


@app.route('/api/users/<path:subpath>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy_users_api(subpath):
    """Proxy user monitoring API requests to Admin Backend"""
    try:
        backend_url = f"http://localhost:9000/api/v1/users/{subpath}"
        args = request.args.to_dict()
        
        if request.method == 'GET':
            response = requests.get(backend_url, params=args, timeout=10)
        elif request.method == 'POST':
            response = requests.post(backend_url, json=request.get_json(silent=True), params=args, timeout=10)
        elif request.method == 'PUT':
            response = requests.put(backend_url, json=request.get_json(silent=True), params=args, timeout=10)
        elif request.method == 'DELETE':
            response = requests.delete(backend_url, params=args, timeout=10)
        
        return jsonify(response.json()), response.status_code
    
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Backend request failed: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Proxy error: {str(e)}'}), 500


@app.route('/health')
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'service': 'central-monitor',
        'timestamp': datetime.now().isoformat(),
        'monitoring': {
            'total_events': stats['total_events'],
            'services': len(stats['services'])
        }
    })


if __name__ == '__main__':
    print('='*70)
    print('[CENTRAL MONITOR] Starting Pandora Platform Admin Console')
    print('[SECURE MODE] Server-Side Rendering - NO JAVASCRIPT')
    print('='*70)
    print('[OK] Admin Console:    http://127.0.0.1:27009')
    print('[OK] Traffic Monitor:  http://127.0.0.1:27009/traffic')
    print('[OK] IDS Dashboard:    http://127.0.0.1:27009/attacks')
    print('[OK] Honeypot Monitor: http://127.0.0.1:27009/honeypot')
    print('[OK] User Monitoring:  http://127.0.0.1:27009/users')
    print('[OK] API Logs:         http://127.0.0.1:27009/api/logs')
    print('[OK] API Stats:        http://127.0.0.1:27009/api/stats')
    print('='*70)
    print('[MONITOR] Watching:')
    print('  - Backend API (Port 8000)')
    print('  - Frontend Dev (Port 5173)')
    print('  - PostgreSQL (Port 5432)')
    print('  - Redis (Port 6379)')
    print('  - Port 80/443 (HTTP/HTTPS)')
    print('  - IDS Engine (Network-wide)')
    print('='*70)
    print('[ADMIN] Access restricted to 127.0.0.1 (localhost only)')
    print('[SECURITY] Pure server-side rendering - No client-side JavaScript')
    print('[REFRESH] Auto-refresh every 30 seconds (HTTP meta tag)')
    print('='*70)
    
    app.run(host='127.0.0.1', port=27009, debug=False)

