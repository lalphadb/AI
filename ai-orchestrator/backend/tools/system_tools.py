"""
Outils système v5.0 - Mode Autonome avec SSH vers hôte
"""

import os
from tools import register_tool
from utils.async_subprocess import run_command_async

HOST = os.getenv("HOST_IP", "host.docker.internal")
USER = os.getenv("HOST_USER", "lalpha")
KEY = "/root/.ssh/id_ed25519"
SSH = f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -i {KEY} {USER}@{HOST}"

HOST_CMDS = {"systemctl", "service", "journalctl", "apt", "apt-get", "dpkg", 
             "nvidia-smi", "sensors", "reboot", "shutdown", "mount", "umount"}


async def ssh(cmd: str, timeout: int = 60) -> tuple:
    return await run_command_async(f'{SSH} "{cmd}"', timeout=timeout)


async def run(cmd: str, timeout: int = 60) -> tuple:
    base = cmd.split()[0].split("/")[-1] if cmd.split() else ""
    if base == "sudo" and len(cmd.split()) > 1:
        base = cmd.split()[1].split("/")[-1]
    if base in HOST_CMDS:
        return await ssh(cmd, timeout)
    return await run_command_async(cmd, timeout)


@register_tool("execute_command")
async def execute_command(params: dict, security_validator=None, **kw) -> str:
    cmd = params.get("command", "")
    if not cmd:
        return "Erreur: commande vide"
    if security_validator:
        ok, reason = security_validator(cmd)
        if not ok:
            return f"🚫 {reason}"
    out, code = await run(cmd, 120)
    return f"{'✅' if code == 0 else '❌'} {cmd[:80]}\n{out[:5000]}"


@register_tool("system_info")
async def system_info(params: dict) -> str:
    out, _ = await ssh("/home/lalpha/scripts/sysinfo.sh", 15)
    info = ["📊 **Système (Hôte)**"]
    labels = {"HOST": "Hostname", "UP": "Uptime", "CPU": "CPU", 
              "RAM": "RAM", "DISK": "Disk", "LOAD": "Load", "GPU": "GPU"}
    for line in out.split("\n"):
        if ":" in line:
            k, v = line.split(":", 1)
            if k in labels:
                info.append(f"**{labels[k]}**: {v.strip()}")
    return "\n".join(info)


@register_tool("service_status")
async def service_status(params: dict) -> str:
    svc = params.get("service", "").replace(".service", "").strip()
    if not svc:
        return "Erreur: service requis"
    out, _ = await ssh(f"systemctl status {svc} --no-pager 2>&1 | head -15", 10)
    if "active (running)" in out:
        st = "🟢 Running"
    elif "inactive" in out:
        st = "⚪ Inactive"
    elif "failed" in out:
        st = "🔴 Failed"
    elif "not be found" in out:
        st = "❓ Not found"
    else:
        st = "⚠️ Unknown"
    return f"**{svc}**: {st}\n```\n{out}\n```"


@register_tool("service_control")
async def service_control(params: dict) -> str:
    svc = params.get("service", "").replace(".service", "").strip()
    action = params.get("action", "")
    if not svc:
        return "Erreur: service requis"
    if action not in ["start", "stop", "restart", "reload", "enable", "disable"]:
        return "Erreur: action invalide"
    out, code = await ssh(f"sudo systemctl {action} {svc} && systemctl is-active {svc}", 30)
    return f"{'✅' if code == 0 else '❌'} systemctl {action} {svc}\n{out}"


@register_tool("disk_usage")
async def disk_usage(params: dict) -> str:
    path = params.get("path", "/home/lalpha")
    depth = min(int(params.get("depth", 1)), 3)
    out, _ = await ssh(f"du -h --max-depth={depth} {path} 2>/dev/null | sort -hr | head -20", 60)
    return f"💾 {path}:\n```\n{out}\n```"


@register_tool("package_install")
async def package_install(params: dict) -> str:
    pkg = params.get("package", "")
    if not pkg:
        return "Erreur: paquet requis"
    out, code = await ssh(f"sudo apt-get install -y {pkg}", 300)
    return f"{'✅' if code == 0 else '❌'} {pkg}\n{out[-2000:]}"


@register_tool("package_update")
async def package_update(params: dict) -> str:
    upgrade = params.get("upgrade", False)
    cmd = "sudo apt-get update" + (" && sudo apt-get upgrade -y" if upgrade else "")
    out, code = await ssh(cmd, 600)
    return f"{'✅' if code == 0 else '❌'} apt update{'+upgrade' if upgrade else ''}\n{out[-2000:]}"


@register_tool("process_list")
async def process_list(params: dict) -> str:
    sort = "-%mem" if params.get("sort") == "mem" else "-%cpu"
    limit = min(int(params.get("limit", 15)), 30)
    out, _ = await ssh(f"ps aux --sort={sort} | head -{limit + 1}", 10)
    return f"📋 Processus:\n```\n{out}\n```"


@register_tool("logs_view")
async def logs_view(params: dict) -> str:
    svc = params.get("service", "")
    lines = min(int(params.get("lines", 50)), 200)
    cmd = f"journalctl -u {svc} -n {lines} --no-pager" if svc else f"journalctl -n {lines} --no-pager"
    out, _ = await ssh(cmd, 15)
    return f"📜 Logs {svc or 'système'}:\n```\n{out[-4000:]}\n```"
