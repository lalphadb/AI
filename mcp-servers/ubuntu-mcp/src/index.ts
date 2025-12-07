#!/usr/bin/env node
/**
 * Ubuntu MCP Server v2.0.0
 * Migré vers la nouvelle API McpServer (SDK v1.23+)
 * Date: 2025-11-30
 */

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import { exec } from 'child_process';
import { promisify } from 'util';
import si from 'systeminformation';

const execAsync = promisify(exec);

// Créer le serveur MCP avec la nouvelle API
const server = new McpServer({
  name: 'ubuntu-mcp-server',
  version: '2.0.0',
});

// ============================================
// TOOL: system_info
// ============================================
server.tool(
  'system_info',
  'Obtenir des informations détaillées sur le système Ubuntu (CPU, mémoire, disque, OS)',
  {
    category: z.enum(['all', 'cpu', 'memory', 'disk', 'os', 'network'])
      .default('all')
      .describe("Catégorie d'informations à récupérer")
  },
  async ({ category }) => {
    const info: Record<string, unknown> = {};

    if (category === 'all' || category === 'cpu') {
      info.cpu = await si.cpu();
      info.cpuLoad = await si.currentLoad();
    }
    if (category === 'all' || category === 'memory') {
      info.memory = await si.mem();
    }
    if (category === 'all' || category === 'disk') {
      info.diskLayout = await si.diskLayout();
      info.fsSize = await si.fsSize();
    }
    if (category === 'all' || category === 'os') {
      info.os = await si.osInfo();
      info.versions = await si.versions();
    }
    if (category === 'all' || category === 'network') {
      info.networkInterfaces = await si.networkInterfaces();
    }

    return {
      content: [{ type: 'text', text: JSON.stringify(info, null, 2) }]
    };
  }
);

// ============================================
// TOOL: list_processes
// ============================================
server.tool(
  'list_processes',
  "Lister les processus en cours d'exécution avec détails (PID, CPU, mémoire)",
  {
    sortBy: z.enum(['cpu', 'memory', 'name']).default('cpu').describe('Critère de tri'),
    limit: z.number().default(20).describe('Nombre de processus à retourner')
  },
  async ({ sortBy, limit }) => {
    const processes = await si.processes();
    let sorted = processes.list;

    if (sortBy === 'cpu') {
      sorted.sort((a, b) => (b.cpu || 0) - (a.cpu || 0));
    } else if (sortBy === 'memory') {
      sorted.sort((a, b) => (b.mem || 0) - (a.mem || 0));
    } else if (sortBy === 'name') {
      sorted.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
    }

    const limitedProcesses = sorted.slice(0, limit);

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          total: processes.all,
          running: processes.running,
          processes: limitedProcesses.map(p => ({
            pid: p.pid,
            name: p.name,
            cpu: p.cpu,
            mem: p.mem,
            state: p.state,
            command: p.command
          }))
        }, null, 2)
      }]
    };
  }
);

// ============================================
// TOOL: execute_command
// ============================================
server.tool(
  'execute_command',
  'Exécuter une commande shell sur le serveur Ubuntu',
  {
    command: z.string().describe('Commande à exécuter'),
    timeout: z.number().default(30000).describe('Timeout en millisecondes')
  },
  async ({ command, timeout }) => {
    try {
      const { stdout, stderr } = await execAsync(command, {
        timeout,
        maxBuffer: 1024 * 1024 * 10,
      });

      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            command,
            stdout: stdout.trim(),
            stderr: stderr.trim(),
            success: true
          }, null, 2)
        }]
      };
    } catch (error: unknown) {
      const execError = error as { stdout?: string; stderr?: string; message?: string };
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            command,
            stdout: execError.stdout?.trim() || '',
            stderr: execError.stderr?.trim() || execError.message,
            success: false
          }, null, 2)
        }]
      };
    }
  }
);

// ============================================
// TOOL: service_status
// ============================================
server.tool(
  'service_status',
  "Vérifier le statut d'un service systemd",
  {
    service: z.string().describe('Nom du service (ex: nginx, apache2, mysql)')
  },
  async ({ service }) => {
    try {
      const { stdout } = await execAsync(`systemctl status ${service}`);
      return { content: [{ type: 'text', text: stdout }] };
    } catch (error: unknown) {
      const execError = error as { stdout?: string; message?: string };
      return { content: [{ type: 'text', text: execError.stdout || execError.message || 'Erreur' }] };
    }
  }
);

// ============================================
// TOOL: service_control
// ============================================
server.tool(
  'service_control',
  'Contrôler un service systemd (start, stop, restart, enable, disable)',
  {
    service: z.string().describe('Nom du service'),
    action: z.enum(['start', 'stop', 'restart', 'enable', 'disable', 'reload']).describe('Action à effectuer')
  },
  async ({ service, action }) => {
    const { stdout, stderr } = await execAsync(`sudo systemctl ${action} ${service}`);
    return {
      content: [{
        type: 'text',
        text: JSON.stringify({ service, action, success: true, output: stdout || stderr }, null, 2)
      }]
    };
  }
);

// ============================================
// TOOL: disk_usage
// ============================================
server.tool(
  'disk_usage',
  "Analyser l'utilisation du disque par répertoire",
  {
    path: z.string().default('/').describe('Chemin du répertoire à analyser'),
    depth: z.number().default(1).describe("Profondeur de l'analyse")
  },
  async ({ path: dirPath, depth }) => {
    const { stdout } = await execAsync(`du -h --max-depth=${depth} ${dirPath} | sort -hr`);
    return { content: [{ type: 'text', text: stdout }] };
  }
);

// ============================================
// TOOL: network_info
// ============================================
server.tool(
  'network_info',
  'Obtenir des informations réseau (interfaces, connexions actives, ports ouverts)',
  {
    detailed: z.boolean().default(false).describe('Inclure les détails des connexions')
  },
  async ({ detailed }) => {
    const networkInterfaces = await si.networkInterfaces();
    const networkStats = await si.networkStats();

    const result: Record<string, unknown> = {
      interfaces: networkInterfaces,
      stats: networkStats
    };

    if (detailed) {
      const { stdout: connections } = await execAsync('ss -tuln');
      result.connections = connections;
    }

    return {
      content: [{ type: 'text', text: JSON.stringify(result, null, 2) }]
    };
  }
);

// ============================================
// TOOL: log_analyzer
// ============================================
server.tool(
  'log_analyzer',
  'Analyser les logs système',
  {
    logFile: z.string().default('/var/log/syslog').describe('Chemin du fichier de log'),
    lines: z.number().default(100).describe('Nombre de lignes à récupérer'),
    filter: z.string().optional().describe('Filtrer les logs (grep pattern)')
  },
  async ({ logFile, lines, filter }) => {
    let command = `tail -n ${lines} ${logFile}`;
    if (filter) {
      command += ` | grep "${filter}"`;
    }
    const { stdout } = await execAsync(command);
    return { content: [{ type: 'text', text: stdout }] };
  }
);

// ============================================
// TOOL: docker_status
// ============================================
server.tool(
  'docker_status',
  'Obtenir le statut des conteneurs Docker',
  {
    all: z.boolean().default(false).describe('Inclure les conteneurs arrêtés')
  },
  async ({ all }) => {
    try {
      const command = all ? 'docker ps -a --format json' : 'docker ps --format json';
      const { stdout } = await execAsync(command);

      const containers = stdout.trim().split('\n')
        .filter(line => line.trim())
        .map(line => JSON.parse(line));

      return {
        content: [{ type: 'text', text: JSON.stringify({ containers }, null, 2) }]
      };
    } catch (error: unknown) {
      const execError = error as { message?: string };
      if (execError.message?.includes('command not found')) {
        return { content: [{ type: 'text', text: "Docker n'est pas installé sur ce système" }] };
      }
      throw error;
    }
  }
);

// ============================================
// TOOL: file_search
// ============================================
server.tool(
  'file_search',
  'Rechercher des fichiers sur le système',
  {
    pattern: z.string().describe('Pattern de recherche (nom de fichier)'),
    directory: z.string().default('/home').describe('Répertoire de recherche'),
    maxDepth: z.number().default(5).describe('Profondeur maximale')
  },
  async ({ pattern, directory, maxDepth }) => {
    const { stdout } = await execAsync(
      `find ${directory} -maxdepth ${maxDepth} -name "${pattern}" 2>/dev/null`
    );
    return { content: [{ type: 'text', text: stdout || 'Aucun fichier trouvé' }] };
  }
);

// ============================================
// TOOL: security_check
// ============================================
server.tool(
  'security_check',
  'Vérifier la sécurité du système (updates, ports ouverts, users)',
  {
    checkType: z.enum(['updates', 'ports', 'users', 'firewall', 'all'])
      .default('all')
      .describe('Type de vérification')
  },
  async ({ checkType }) => {
    const results: Record<string, unknown> = {};

    if (checkType === 'all' || checkType === 'updates') {
      try {
        const { stdout } = await execAsync('apt list --upgradable 2>/dev/null | grep -c upgradable');
        results.updates = { available: parseInt(stdout.trim()) || 0 };
      } catch {
        results.updates = { error: 'Impossible de vérifier les mises à jour' };
      }
    }

    if (checkType === 'all' || checkType === 'ports') {
      const { stdout } = await execAsync('ss -tuln | grep LISTEN');
      results.openPorts = stdout;
    }

    if (checkType === 'all' || checkType === 'users') {
      const { stdout } = await execAsync('cat /etc/passwd | grep -v nologin | grep -v false');
      results.users = stdout;
    }

    if (checkType === 'all' || checkType === 'firewall') {
      try {
        const { stdout } = await execAsync('sudo ufw status');
        results.firewall = stdout;
      } catch {
        results.firewall = 'UFW non disponible ou non installé';
      }
    }

    return {
      content: [{ type: 'text', text: JSON.stringify(results, null, 2) }]
    };
  }
);

// ============================================
// TOOL: backup_manager
// ============================================
server.tool(
  'backup_manager',
  'Gérer les sauvegardes (créer, lister, restaurer)',
  {
    action: z.enum(['create', 'list', 'info']).describe('Action de backup'),
    source: z.string().optional().describe('Répertoire source pour backup'),
    destination: z.string().optional().describe('Destination du backup')
  },
  async ({ action, source, destination }) => {
    switch (action) {
      case 'create': {
        if (!source || !destination) {
          throw new Error('Source et destination requises pour créer un backup');
        }
        const timestamp = new Date().toISOString().replace(/:/g, '-');
        const backupName = `backup-${timestamp}.tar.gz`;
        const backupPath = `${destination}/${backupName}`;

        await execAsync(`tar -czf ${backupPath} ${source}`);
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({
              action: 'create',
              success: true,
              backupPath,
              message: 'Backup créé avec succès'
            }, null, 2)
          }]
        };
      }

      case 'list': {
        const listPath = destination || '/home/backups';
        const { stdout: files } = await execAsync(
          `ls -lh ${listPath}/*.tar.gz 2>/dev/null || echo "Aucun backup trouvé"`
        );
        return { content: [{ type: 'text', text: files }] };
      }

      case 'info': {
        if (!source) {
          throw new Error('Chemin du backup requis');
        }
        const { stdout: info } = await execAsync(`tar -tzf ${source} | head -20`);
        return { content: [{ type: 'text', text: `Contenu du backup ${source}:\n${info}` }] };
      }

      default:
        throw new Error(`Action inconnue: ${action}`);
    }
  }
);

// ============================================
// DÉMARRAGE DU SERVEUR
// ============================================
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('Ubuntu MCP Server v2.0 running on stdio');
}

main().catch(console.error);
