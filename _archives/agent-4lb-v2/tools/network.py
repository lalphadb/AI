"""
🌐 Outils Réseau - LangChain Tools
"""
from .system import execute_command


def check_url(url: str, timeout: int = 10) -> str:
    """Vérifier l'accessibilité d'une URL."""
    return execute_command(
        f"curl -sI -o /dev/null -w 'HTTP %{{http_code}} - %{{time_total}}s - %{{size_download}} bytes' --max-time {timeout} {url}"
    )


def get_ssl_info(domain: str) -> str:
    """Obtenir les informations SSL d'un domaine."""
    return execute_command(
        f"echo | openssl s_client -connect {domain}:443 2>/dev/null | openssl x509 -noout -dates -subject -issuer 2>/dev/null"
    )


def ping(host: str, count: int = 4) -> str:
    """Ping un hôte."""
    return execute_command(f"ping -c {count} {host}", timeout=count + 5)


def dns_lookup(domain: str, record_type: str = "A") -> str:
    """Effectuer une requête DNS."""
    return execute_command(f"dig +short {domain} {record_type}")


def port_scan(host: str, port: int) -> str:
    """Vérifier si un port est ouvert."""
    return execute_command(f"nc -zv -w 5 {host} {port} 2>&1")


def netstat_listen() -> str:
    """Lister les ports en écoute."""
    return execute_command("ss -tlnp")


def traceroute(host: str) -> str:
    """Tracer la route vers un hôte."""
    return execute_command(f"traceroute -m 15 {host}", timeout=60)


def curl_get(url: str, headers: dict = None) -> str:
    """Effectuer une requête GET."""
    header_args = ""
    if headers:
        for k, v in headers.items():
            header_args += f" -H '{k}: {v}'"
    return execute_command(f"curl -s{header_args} '{url}'", timeout=30)


def curl_post(url: str, data: str, content_type: str = "application/json") -> str:
    """Effectuer une requête POST."""
    return execute_command(
        f"curl -s -X POST -H 'Content-Type: {content_type}' -d '{data}' '{url}'",
        timeout=30
    )


def whois(domain: str) -> str:
    """Effectuer une requête WHOIS."""
    return execute_command(f"whois {domain}", timeout=15)
