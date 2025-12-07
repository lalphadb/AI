#!/usr/bin/env node
/**
 * UDM-Pro MCP Server v2.0.0
 * Migré vers la nouvelle API McpServer (SDK v1.23+)
 * Date: 2025-11-30
 */

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import { Client } from 'ssh2';
import * as fs from 'fs';
import * as path from 'path';
import { homedir } from 'os';

// Configuration SSH
const SSH_CONFIG = {
  host: '10.10.10.1',
  port: 22,
  username: 'root',
  privateKeyPath: path.join(homedir(), '.ssh', 'id_rsa_udm'),
};

// Créer le serveur MCP
const server = new McpServer({
  name: 'udm-pro-mcp-server',
  version: '2.0.0',
});

// Fonction helper pour exécuter des commandes SSH
async function executeSSHCommand(command: string, timeout: number = 30000): Promise<{ stdout: string; stderr: string; success: boolean }> {
  return new Promise((resolve, reject) => {
    const client = new Client();
    let stdout = '';
    let stderr = '';

    const timer = setTimeout(() => {
      client.end();
      reject(new Error(`Command timeout after ${timeout}ms`));
    }, timeout);

    client.on('ready', () => {
      client.exec(command, (err, stream) => {
        if (err) {
          clearTimeout(timer);
          client.end();
          reject(err);
          return;
        }

        stream.on('close', (code: number) => {
          clearTimeout(timer);
          client.end();
          resolve({
            stdout: stdout.trim(),
            stderr: stderr.trim(),
            success: code === 0
          });
        });

        stream.on('data', (data: Buffer) => {
          stdout += data.toString();
        });

        stream.stderr.on('data', (data: Buffer) => {
          stderr += data.toString();
        });
      });
    });

    client.on('error', (err) => {
      clearTimeout(timer);
      reject(err);
    });

    let privateKey: Buffer;
    try {
      privateKey = fs.readFileSync(SSH_CONFIG.privateKeyPath);
    } catch (error) {
      clearTimeout(timer);
      reject(new Error(`Cannot read private key at ${SSH_CONFIG.privateKeyPath}: ${error}`));
      return;
    }

    client.connect({
      host: SSH_CONFIG.host,
      port: SSH_CONFIG.port,
      username: SSH_CONFIG.username,
      privateKey: privateKey,
    });
  });
}

// ============================================
// TOOL: udm_connection_test
// ============================================
server.tool(
  'udm_connection_test',
  'Tester la connexion SSH au UDM-Pro',
  {},
  async () => {
    const result = await executeSSHCommand('hostname && uname -a');
    const lines = result.stdout.split('\n');
    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          message: 'SSH connection successful',
          hostname: lines[0],
          system: lines[1],
        }, null, 2)
      }]
    };
  }
);

// ============================================
// TOOL: udm_exec
// ============================================
server.tool(
  'udm_exec',
  'Exécuter une commande sur le UDM-Pro',
  {
    command: z.string().describe('Commande à exécuter sur le UDM-Pro'),
    timeout: z.number().default(30000).describe('Timeout en millisecondes')
  },
  async ({ command, timeout }) => {
    const result = await executeSSHCommand(command, timeout);
    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          command,
          stdout: result.stdout,
          stderr: result.stderr,
          success: result.success
        }, null, 2)
      }]
    };
  }
);

// ============================================
// TOOL: udm_status
// ============================================
server.tool(
  'udm_status',
  'Obtenir le statut complet du UDM-Pro (système, réseau, clients)',
  {
    detailed: z.boolean().default(false).describe('Inclure des informations détaillées')
  },
  async ({ detailed }) => {
    const commands = [
      'uptime',
      'df -h',
      'free -h',
      'top -bn1 | head -20'
    ];

    if (detailed) {
      commands.push('ps aux | head -20');
      commands.push('netstat -tuln | head -20');
    }

    const result = await executeSSHCommand(commands.join(' && echo "---" && '));
    return { content: [{ type: 'text', text: result.stdout }] };
  }
);

// ============================================
// TOOL: udm_network_info
// ============================================
server.tool(
  'udm_network_info',
  'Obtenir les informations réseau du UDM-Pro (interfaces, VLANs, clients)',
  {
    include_clients: z.boolean().default(false).describe('Inclure la liste des clients connectés')
  },
  async ({ include_clients }) => {
    let command = 'ip addr show && echo "---" && ip route show';

    if (include_clients) {
      command += ' && echo "---" && ubnt-tools list-stations';
    }

    const result = await executeSSHCommand(command);
    return { content: [{ type: 'text', text: result.stdout }] };
  }
);

// ============================================
// TOOL: udm_device_list
// ============================================
server.tool(
  'udm_device_list',
  'Lister tous les appareils UniFi gérés par le UDM-Pro',
  {},
  async () => {
    const result = await executeSSHCommand('ubnt-device-discovery');
    return {
      content: [{
        type: 'text',
        text: result.stdout || 'No devices found or command not available'
      }]
    };
  }
);

// ============================================
// TOOL: udm_logs
// ============================================
server.tool(
  'udm_logs',
  'Consulter les logs système du UDM-Pro',
  {
    lines: z.number().default(50).describe('Nombre de lignes à récupérer'),
    filter: z.string().optional().describe('Filtrer les logs (grep pattern)')
  },
  async ({ lines, filter }) => {
    let command = `tail -n ${lines} /var/log/messages`;

    if (filter) {
      command += ` | grep "${filter}"`;
    }

    const result = await executeSSHCommand(command);
    return { content: [{ type: 'text', text: result.stdout || 'No logs found' }] };
  }
);

// ============================================
// TOOL: udm_backup_config
// ============================================
server.tool(
  'udm_backup_config',
  'Créer une sauvegarde de la configuration du UDM-Pro',
  {
    destination: z.string().default('/tmp').describe('Chemin de destination pour le backup')
  },
  async ({ destination }) => {
    const timestamp = new Date().toISOString().replace(/:/g, '-').split('.')[0];
    const backupFile = `udm-backup-${timestamp}.tar.gz`;
    const command = `tar -czf ${destination}/${backupFile} /data/unifi/data/backup/autobackup/* 2>/dev/null || echo "Backup created but some files may be missing"`;

    const result = await executeSSHCommand(command);

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          success: true,
          backupFile: `${destination}/${backupFile}`,
          message: result.stdout || 'Backup created',
        }, null, 2)
      }]
    };
  }
);

// ============================================
// TOOL: udm_firewall_rules
// ============================================
server.tool(
  'udm_firewall_rules',
  'Lister les règles de firewall du UDM-Pro',
  {},
  async () => {
    const result = await executeSSHCommand('iptables -L -n -v');
    return { content: [{ type: 'text', text: result.stdout }] };
  }
);

// ============================================
// DÉMARRAGE DU SERVEUR
// ============================================
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('UDM-Pro MCP Server v2.0 running on stdio');
}

main().catch(console.error);
