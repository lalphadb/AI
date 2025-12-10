#!/usr/bin/env python3
"""
📊 Self-Improvement Metrics Exporter
Expose les métriques pour Prometheus/Grafana
Port: 9101
"""

import json
import time
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

REPORTS_DIR = Path("/home/lalpha/projets/ai-tools/self-improvement/reports")
PORT = 9101

class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/metrics':
            metrics = self.get_prometheus_metrics()
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(metrics.encode())
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status":"healthy"}')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Silence les logs
    
    def get_prometheus_metrics(self):
        """Génère les métriques au format Prometheus"""
        lines = []
        lines.append("# HELP selfimprovement_score Score de santé du système (0-100)")
        lines.append("# TYPE selfimprovement_score gauge")
        
        lines.append("# HELP selfimprovement_alerts_total Nombre d'alertes actives")
        lines.append("# TYPE selfimprovement_alerts_total gauge")
        
        lines.append("# HELP selfimprovement_last_run_timestamp Timestamp du dernier rapport")
        lines.append("# TYPE selfimprovement_last_run_timestamp gauge")
        
        # Charger le dernier rapport
        report = self.get_latest_report()
        
        if report:
            score = report.get('score', 0)
            alerts_count = len(report.get('alerts', []))
            timestamp = datetime.fromisoformat(report.get('timestamp', datetime.now().isoformat())).timestamp()
            status = report.get('status', 'unknown')
            
            # Métriques principales
            lines.append(f'selfimprovement_score{{status="{status}"}} {score}')
            lines.append(f'selfimprovement_alerts_total {alerts_count}')
            lines.append(f'selfimprovement_last_run_timestamp {timestamp}')
            
            # Métriques détaillées
            metrics = report.get('metrics', {})
            if metrics:
                lines.append("")
                lines.append("# HELP selfimprovement_cpu_percent CPU usage percentage")
                lines.append("# TYPE selfimprovement_cpu_percent gauge")
                lines.append(f'selfimprovement_cpu_percent {metrics.get("cpu_percent", 0)}')
                
                lines.append("# HELP selfimprovement_memory_percent Memory usage percentage")
                lines.append("# TYPE selfimprovement_memory_percent gauge")
                lines.append(f'selfimprovement_memory_percent {metrics.get("memory_percent", 0)}')
                
                lines.append("# HELP selfimprovement_disk_percent Disk usage percentage")
                lines.append("# TYPE selfimprovement_disk_percent gauge")
                lines.append(f'selfimprovement_disk_percent {metrics.get("disk_root_percent", 0)}')
                
                if metrics.get('gpu_util') is not None:
                    lines.append("# HELP selfimprovement_gpu_percent GPU utilization percentage")
                    lines.append("# TYPE selfimprovement_gpu_percent gauge")
                    lines.append(f'selfimprovement_gpu_percent {metrics.get("gpu_util", 0)}')
                    
                    lines.append("# HELP selfimprovement_gpu_memory_percent GPU memory percentage")
                    lines.append("# TYPE selfimprovement_gpu_memory_percent gauge")
                    lines.append(f'selfimprovement_gpu_memory_percent {metrics.get("gpu_mem_percent", 0)}')
                    
                    lines.append("# HELP selfimprovement_gpu_temp GPU temperature")
                    lines.append("# TYPE selfimprovement_gpu_temp gauge")
                    lines.append(f'selfimprovement_gpu_temp {metrics.get("gpu_temp", 0)}')
                
                docker = metrics.get('docker', {})
                if docker:
                    lines.append("# HELP selfimprovement_docker_running Running containers")
                    lines.append("# TYPE selfimprovement_docker_running gauge")
                    lines.append(f'selfimprovement_docker_running {docker.get("running", 0)}')
                    
                    lines.append("# HELP selfimprovement_docker_stopped Stopped containers")
                    lines.append("# TYPE selfimprovement_docker_stopped gauge")
                    lines.append(f'selfimprovement_docker_stopped {docker.get("stopped", 0)}')
            
            # Alertes par niveau
            alerts = report.get('alerts', [])
            critical = len([a for a in alerts if a.get('level') == 'critical'])
            warning = len([a for a in alerts if a.get('level') == 'warning'])
            info = len([a for a in alerts if a.get('level') == 'info'])
            
            lines.append("")
            lines.append("# HELP selfimprovement_alerts_by_level Alerts by severity level")
            lines.append("# TYPE selfimprovement_alerts_by_level gauge")
            lines.append(f'selfimprovement_alerts_by_level{{level="critical"}} {critical}')
            lines.append(f'selfimprovement_alerts_by_level{{level="warning"}} {warning}')
            lines.append(f'selfimprovement_alerts_by_level{{level="info"}} {info}')
        else:
            lines.append('selfimprovement_score{status="unknown"} 0')
            lines.append('selfimprovement_alerts_total 0')
            lines.append(f'selfimprovement_last_run_timestamp {time.time()}')
        
        return '\n'.join(lines) + '\n'
    
    def get_latest_report(self):
        """Récupère le dernier rapport"""
        try:
            reports = sorted(REPORTS_DIR.glob("report_*.json"), reverse=True)
            if reports:
                with open(reports[0]) as f:
                    return json.load(f)
        except Exception as e:
            print(f"Erreur lecture rapport: {e}")
        return None


def main():
    print(f"📊 Self-Improvement Metrics Exporter")
    print(f"   Port: {PORT}")
    print(f"   Endpoint: http://localhost:{PORT}/metrics")
    
    server = HTTPServer(('0.0.0.0', PORT), MetricsHandler)
    print(f"✅ Serveur démarré...")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Arrêt...")
        server.shutdown()


if __name__ == "__main__":
    main()
