#!/usr/bin/env python3
"""
Pandora IDS Engine
Network packet sniffer and attack detector using Scapy
Requires: sudo/admin privileges
"""

from scapy.all import sniff, IP, TCP, UDP, ICMP
from collections import defaultdict, deque
from datetime import datetime, timedelta
import threading
import time
import sys
import os

# Add backend-admin to path (IDS logs to Admin database)
backend_admin_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend-admin'))
sys.path.insert(0, backend_admin_dir)

from database.database import SessionLocal
from models.attack import AttackLog
from services.geoip_service import geoip_service
from services.elasticsearch_service import elasticsearch_service
from config import settings

class IDSEngine:
    """Intrusion Detection System Engine"""
    
    def __init__(self, interface=None, ports_to_monitor='all'):
        self.interface = interface
        self.ports_to_monitor = ports_to_monitor
        
        # Get local network info
        self.local_ips = self._get_local_ips()
        print(f"[INIT] Local IPs detected: {', '.join(self.local_ips)}")
        
        # Attack detection tracking
        self.syn_tracker = defaultdict(lambda: {'count': 0, 'last_seen': None, 'ports': set()})
        self.port_scan_tracker = defaultdict(lambda: deque(maxlen=100))
        self.connection_tracker = defaultdict(int)
        
        # Critical ports to monitor (common attack targets)
        self.CRITICAL_PORTS = {
            22: 'SSH',
            23: 'Telnet',
            80: 'HTTP',
            443: 'HTTPS',
            3306: 'MySQL',
            5432: 'PostgreSQL',
            3389: 'RDP',
            21: 'FTP',
            25: 'SMTP',
            9000: 'Backend',
            5173: 'Frontend',
            27009: 'Monitor'
        }
        
        # Thresholds (more sensitive)
        self.PORT_SCAN_THRESHOLD = 3  # ports in time_window
        self.PORT_SCAN_TIME_WINDOW = 60  # seconds
        self.SYN_FLOOD_THRESHOLD = 20  # SYNs in time_window
        self.SYN_FLOOD_TIME_WINDOW = 10  # seconds
        self.SUSPICIOUS_CONNECTION_THRESHOLD = 5  # connections to same port
        
        # Cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_old_data, daemon=True)
        self.cleanup_thread.start()
    
    def _get_local_ips(self):
        """Get all local IP addresses of this machine"""
        import socket
        
        local_ips = set()
        
        # Add localhost
        local_ips.add('127.0.0.1')
        local_ips.add('::1')
        
        try:
            # Get hostname IP
            hostname = socket.gethostname()
            host_ip = socket.gethostbyname(hostname)
            local_ips.add(host_ip)
            
            # Try to get all IPs by connecting to external
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ips.add(s.getsockname()[0])
            s.close()
            
            # Also try gethostbyname_ex for all IPs
            hostname_info = socket.gethostbyname_ex(hostname)
            for ip in hostname_info[2]:
                local_ips.add(ip)
                
        except Exception as e:
            print(f"[WARNING] Failed to get all local IPs: {e}")
        
        return local_ips
    
    def _is_local_ip(self, ip):
        """Check if IP is local to this machine"""
        return ip in self.local_ips
    
    def _is_private_network(self, ip):
        """Check if IP is in private network range"""
        # Private IP ranges: 10.x.x.x, 172.16-31.x.x, 192.168.x.x
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        
        try:
            first = int(parts[0])
            second = int(parts[1])
            
            if first == 10:
                return True
            if first == 172 and 16 <= second <= 31:
                return True
            if first == 192 and second == 168:
                return True
        except:
            pass
        
        return False
    
    def detect_attack_type(self, packet):
        """Detect type of attack from packet - ONLY NEW INBOUND connections"""
        if not packet.haslayer(IP):
            return None
        
        src_ip = packet[IP].src
        dst_ip = packet[IP].dst
        
        # CRITICAL: Only monitor INBOUND traffic (external -> local)
        # Skip if source is local (this is OUTBOUND traffic)
        if self._is_local_ip(src_ip):
            return None
        
        # Skip if destination is NOT local (this is transit traffic)
        if not self._is_local_ip(dst_ip):
            return None
        
                
        if not packet.haslayer(TCP):
            return None
        
    
        tcp_flags = packet[TCP].flags
        src_port = packet[TCP].sport
        dst_port = packet[TCP].dport
        
        if src_port in [53, 80, 443, 8080, 8443, 25, 587]:
            return None
        
        has_syn = 'S' in str(tcp_flags)
        is_to_critical_port = dst_port in self.CRITICAL_PORTS
        
        if not has_syn and not is_to_critical_port:
            return None
        
        # Critical port probe detection (HTTP, HTTPS, SSH, etc)
        if dst_port in self.CRITICAL_PORTS:
            result = self._detect_critical_port_probe(packet, src_ip, dst_port)
            if result:
                return result
        
        # SYN scan detection (nmap -sS)
        if packet[TCP].flags == 'S':
            return self._detect_syn_scan(packet, src_ip)
        
        # Port scan detection (general)
        return self._detect_port_scan(packet, src_ip)
    
    def _detect_syn_scan(self, packet, src_ip):
        """Detect SYN scan (nmap stealth scan)"""
        tracker = self.syn_tracker[src_ip]
        tracker['ports'].add(packet[TCP].dport)
        tracker['count'] += 1
        tracker['last_seen'] = datetime.now()
        
        # If many SYNs to different ports = port scan
        if len(tracker['ports']) >= self.PORT_SCAN_THRESHOLD:
            return {
                'type': 'port_scan',
                'tool': 'nmap',
                'severity': 'high',
                'confidence': 90,
                'details': f"SYN scan detected: {len(tracker['ports'])} ports scanned"
            }
        
        # If many SYNs to same port = SYN flood
        if tracker['count'] >= self.SYN_FLOOD_THRESHOLD:
            return {
                'type': 'syn_flood',
                'tool': 'unknown',
                'severity': 'critical',
                'confidence': 95,
                'details': f"SYN flood: {tracker['count']} packets"
            }
        
        return None
    
    def _detect_port_scan(self, packet, src_ip):
        """Detect port scanning patterns"""
        dst_port = packet[TCP].dport
        self.port_scan_tracker[src_ip].append({
            'port': dst_port,
            'time': datetime.now()
        })
        
        # Check if multiple ports hit in time window
        recent_ports = set()
        cutoff_time = datetime.now() - timedelta(seconds=self.PORT_SCAN_TIME_WINDOW)
        
        for entry in self.port_scan_tracker[src_ip]:
            if entry['time'] > cutoff_time:
                recent_ports.add(entry['port'])
        
        if len(recent_ports) >= self.PORT_SCAN_THRESHOLD:
            # Detect scan type by port pattern
            sequential = self._is_sequential_scan(recent_ports)
            
            return {
                'type': 'port_scan',
                'tool': 'nmap' if sequential else 'masscan',
                'severity': 'high',
                'confidence': 85 if sequential else 70,
                'details': f"Port scan: {len(recent_ports)} ports in {self.PORT_SCAN_TIME_WINDOW}s"
            }
        
        return None
    
    def _detect_critical_port_probe(self, packet, src_ip, dst_port):
        """Detect suspicious connections to critical ports"""
        port_name = self.CRITICAL_PORTS.get(dst_port, 'Unknown')
        
        # Track connections to this port from this IP
        key = f"{src_ip}:{dst_port}"
        self.connection_tracker[key] += 1
        
        # Detect reconnaissance/probing
        if self.connection_tracker[key] >= self.SUSPICIOUS_CONNECTION_THRESHOLD:
            # Determine tool and severity based on port
            tool = 'unknown'
            severity = 'medium'
            
            if dst_port == 23:
                tool = 'telnet'
                severity = 'high'
            elif dst_port in [80, 443]:
                tool = 'http_probe'
                severity = 'medium'
            elif dst_port == 22:
                tool = 'ssh_probe'
                severity = 'high'
            elif dst_port in [3306, 5432]:
                tool = 'db_probe'
                severity = 'high'
            elif dst_port == 3389:
                tool = 'rdp_probe'
                severity = 'critical'
            
            return {
                'type': f'{port_name.lower()}_probe',
                'tool': tool,
                'severity': severity,
                'confidence': 85,
                'details': f"Multiple connection attempts to {port_name} (port {dst_port})"
            }
        
        # Log first attempt to critical ports (reconnaissance)
        if self.connection_tracker[key] == 1 and packet[TCP].flags == 'S':
            return {
                'type': f'{port_name.lower()}_reconnaissance',
                'tool': 'scanner',
                'severity': 'low',
                'confidence': 70,
                'details': f"Reconnaissance attempt on {port_name} (port {dst_port})"
            }
        
        return None
    
    def _is_sequential_scan(self, ports):
        """Check if ports are sequential (typical nmap behavior)"""
        sorted_ports = sorted(ports)
        sequential_count = 0
        for i in range(len(sorted_ports) - 1):
            if sorted_ports[i+1] - sorted_ports[i] <= 10:
                sequential_count += 1
        return sequential_count / len(sorted_ports) > 0.5
    
    def _cleanup_old_data(self):
        """Periodically clean old tracking data"""
        while True:
            time.sleep(300)  # Every 5 minutes
            cutoff = datetime.now() - timedelta(minutes=10)
            
            # Clean SYN tracker
            for ip in list(self.syn_tracker.keys()):
                if self.syn_tracker[ip]['last_seen'] and self.syn_tracker[ip]['last_seen'] < cutoff:
                    del self.syn_tracker[ip]
            
            # Clean connection tracker (reset counts every 10 minutes)
            self.connection_tracker.clear()
            
            print(f"[CLEANUP] Tracker data cleaned at {datetime.now()}")
    
    def extract_payload(self, packet):
        """Extract and sanitize packet payload"""
        if packet.haslayer(TCP):
            payload = bytes(packet[TCP].payload)
        elif packet.haslayer(UDP):
            payload = bytes(packet[UDP].payload)
        else:
            return ""
        
        # Take first 200 bytes, sanitize
        sample = payload[:200]
        try:
            # Decode and remove NULL bytes (PostgreSQL TEXT fields cannot contain \x00)
            decoded = sample.decode('utf-8', errors='ignore')
            # Remove NULL bytes
            sanitized = decoded.replace('\x00', '')
            return sanitized
        except:
            return repr(sample)
    
    def packet_handler(self, packet):
        """Main packet processing handler"""
        try:
            if not packet.haslayer(IP):
                return
            
            # Detect attack
            attack_info = self.detect_attack_type(packet)
            
            if attack_info:
                self.log_attack(packet, attack_info)
        
        except Exception as e:
            print(f"[ERROR] Packet handler error: {e}")
    
    def log_attack(self, packet, attack_info):
        """Log detected attack to database"""
        try:
            src_ip = packet[IP].src
            dst_ip = packet[IP].dst
            
            # Get GeoIP info
            geo_info = geoip_service.lookup(src_ip)
            
            # Extract packet details
            src_port = packet[TCP].sport if packet.haslayer(TCP) else packet[UDP].sport if packet.haslayer(UDP) else 0
            dst_port = packet[TCP].dport if packet.haslayer(TCP) else packet[UDP].dport if packet.haslayer(UDP) else 0
            protocol = packet[IP].proto
            flags = str(packet[TCP].flags) if packet.haslayer(TCP) else ""
            
            # Sanitize function to remove NULL bytes from strings
            def sanitize_string(s):
                """Remove NULL bytes from string for PostgreSQL compatibility"""
                if s is None:
                    return None
                return str(s).replace('\x00', '')
            
            # Create log entry
            db = SessionLocal()
            try:
                # Check if recent attack from same IP exists
                recent_attack = db.query(AttackLog).filter(
                    AttackLog.source_ip == src_ip,
                    AttackLog.attack_type == attack_info['type'],
                    AttackLog.detected_at > datetime.now() - timedelta(minutes=5)
                ).first()
                
                if recent_attack:
                    # Update existing
                    recent_attack.packet_count += 1
                    recent_attack.last_seen = datetime.now()
                else:
                    # Create new
                    attack_log = AttackLog(
                        source_ip=src_ip,
                        source_port=src_port,
                        target_ip=dst_ip,
                        target_port=dst_port,
                        attack_type=attack_info['type'],
                        severity=attack_info['severity'],
                        packet_count=1,
                        protocol={6: 'TCP', 17: 'UDP', 1: 'ICMP'}.get(protocol, 'OTHER'),
                        flags=sanitize_string(flags),
                        payload_sample=sanitize_string(self.extract_payload(packet)),
                        country=sanitize_string(geo_info.get('country')),
                        city=sanitize_string(geo_info.get('city')),
                        latitude=str(geo_info.get('latitude', 0)),
                        longitude=str(geo_info.get('longitude', 0)),
                        detected_tool=sanitize_string(attack_info['tool']),
                        confidence=attack_info['confidence'],
                        raw_packet_info={
                            'src_ip': src_ip,
                            'dst_ip': dst_ip,
                            'src_port': src_port,
                            'dst_port': dst_port,
                            'details': sanitize_string(attack_info['details'])
                        }
                    )
                    db.add(attack_log)
                    
                    # Trigger email notification
                    from services.email_service import send_attack_alert
                    threading.Thread(
                        target=send_attack_alert,
                        args=(attack_log,),
                        daemon=True
                    ).start()
                
                db.commit()
                print(f"[ATTACK DETECTED] {attack_info['type']} from {src_ip}:{src_port} -> {dst_ip}:{dst_port}")
                
                # Also log to Elasticsearch (async, non-blocking)
                try:
                    es_data = {
                        'source_ip': src_ip,
                        'source_port': src_port,
                        'target_ip': dst_ip,
                        'target_port': dst_port,
                        'attack_type': attack_info['type'],
                        'severity': attack_info['severity'],
                        'packet_count': 1,
                        'protocol': {6: 'TCP', 17: 'UDP', 1: 'ICMP'}.get(protocol, 'OTHER'),
                        'flags': sanitize_string(flags),
                        'payload_sample': sanitize_string(self.extract_payload(packet)),
                        'country': sanitize_string(geo_info.get('country')),
                        'city': sanitize_string(geo_info.get('city')),
                        'latitude': str(geo_info.get('latitude', 0)),
                        'longitude': str(geo_info.get('longitude', 0)),
                        'detected_tool': sanitize_string(attack_info['tool']),
                        'confidence': attack_info['confidence'],
                        'raw_packet_info': {
                            'src_ip': src_ip,
                            'dst_ip': dst_ip,
                            'src_port': src_port,
                            'dst_port': dst_port,
                            'details': sanitize_string(attack_info['details'])
                        },
                        'detected_at': datetime.now().isoformat()
                    }
                    
                    # Send to Elasticsearch in background thread
                    def send_to_es():
                        try:
                            elasticsearch_service.log_attack(es_data)
                        except:
                            pass  # Fail silently
                    
                    threading.Thread(target=send_to_es, daemon=True).start()
                except Exception as e:
                    print(f"[ELASTICSEARCH] Failed to send attack log: {e}")
                
            finally:
                db.close()
        
        except Exception as e:
            print(f"[ERROR] Failed to log attack: {e}")
    
    def start(self):
        """Start packet sniffing"""
        print("="*70)
        print("[IDS] Pandora Intrusion Detection System v2.2 - INBOUND + STATE")
        print("="*70)
        print(f"[OK] Interface: {self.interface or 'all'}")
        print(f"[OK] Local IPs: {', '.join(sorted(self.local_ips))}")
        print(f"[OK] Monitoring: INBOUND traffic only (External -> Local)")
        print("[OK] Attack detection: ACTIVE")
        print("="*70)
        print("[DETECTION] Enabled:")
        print(f"  • Port Scan (>= {self.PORT_SCAN_THRESHOLD} ports in {self.PORT_SCAN_TIME_WINDOW}s)")
        print(f"  • SYN Flood (>= {self.SYN_FLOOD_THRESHOLD} packets in {self.SYN_FLOOD_TIME_WINDOW}s)")
        print(f"  • Critical Ports: {', '.join([f'{p}({n})' for p, n in sorted(self.CRITICAL_PORTS.items())])}")
        print(f"  • Suspicious Connections (>= {self.SUSPICIOUS_CONNECTION_THRESHOLD} attempts)")
        print("="*70)
        print("[FILTER] Traffic ignored:")
        print("  X OUTBOUND (Local -> External) - Normal user traffic")
        print("  X TRANSIT (External -> External) - Not our business")
        print("  X WEBSERVER RESPONSES (port 80/443) - Return traffic")
        print("  X ESTABLISHED CONNECTIONS (no SYN) - Ongoing connections")
        print("  OK NEW INBOUND (External -> Local + SYN) - MONITORED!")
        print("="*70)
        print("[WARNING] Running with packet capture - requires admin/root")
        print("="*70)
        
        # Build filter
        filter_str = "ip"  # Basic IP filter
        
        try:
            sniff(
                iface=self.interface,
                filter=filter_str,
                prn=self.packet_handler,
                store=False
            )
        except PermissionError:
            print("[ERROR] Permission denied. Please run with sudo/admin privileges")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n[SHUTDOWN] IDS engine stopped")
        except Exception as e:
            print(f"[ERROR] Sniffer error: {e}")
            sys.exit(1)

if __name__ == '__main__':
    engine = IDSEngine()
    engine.start()

