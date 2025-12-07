#!/usr/bin/env node
/**
 * Filesystem MCP Server v2.0.0
 * Migré vers la nouvelle API McpServer (SDK v1.23+)
 * Date: 2025-11-30
 */

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import { promises as fs } from 'fs';
import path from 'path';
import { glob } from 'glob';

const server = new McpServer({
  name: 'filesystem-analyzer',
  version: '2.0.0'
});

// ============================================
// TOOL: analyze_directory
// ============================================
server.tool(
  'analyze_directory',
  'Analyse un dossier pour trouver les fichiers inutilisés',
  {
    directory: z.string().describe('Chemin du dossier'),
    deep: z.boolean().default(true).describe('Analyse en profondeur')
  },
  async ({ directory }) => {
    const result = {
      totalFiles: 0,
      unusedFiles: [],
      emptyDirs: [],
      largeFiles: [],
      oldFiles: []
    };

    const files = await glob('**/*', {
      cwd: directory,
      absolute: true,
      nodir: false,
      stat: true
    });

    for (const file of files) {
      const stat = await fs.stat(file).catch(() => null);
      if (!stat) continue;

      if (stat.isDirectory()) {
        const contents = await fs.readdir(file).catch(() => []);
        if (contents.length === 0) {
          result.emptyDirs.push(file);
        }
      } else {
        result.totalFiles++;

        // Fichiers volumineux (>10MB)
        if (stat.size > 10485760) {
          result.largeFiles.push({
            path: file,
            size: `${(stat.size / 1048576).toFixed(2)}MB`
          });
        }

        // Fichiers anciens (>180 jours)
        const daysSinceModified = (Date.now() - stat.mtime) / 86400000;
        if (daysSinceModified > 180) {
          result.oldFiles.push({
            path: file,
            lastModified: stat.mtime.toISOString(),
            daysOld: Math.floor(daysSinceModified)
          });
        }

        // Détection fichiers potentiellement inutilisés
        const unused = ['.bak', '.tmp', '.cache', '.log', '~', '.swp'];
        if (unused.some(ext => file.endsWith(ext))) {
          result.unusedFiles.push(file);
        }
      }
    }

    return {
      content: [{ type: 'text', text: JSON.stringify(result, null, 2) }]
    };
  }
);

// ============================================
// TOOL: find_duplicates
// ============================================
server.tool(
  'find_duplicates',
  'Trouve les fichiers dupliqués',
  {
    directory: z.string().describe('Chemin du dossier à analyser')
  },
  async ({ directory }) => {
    const fileHashes = new Map();
    const files = await glob('**/*', { cwd: directory, absolute: true, nodir: true });

    for (const file of files) {
      try {
        const stat = await fs.stat(file);
        const content = await fs.readFile(file, 'utf8').catch(() => null);
        if (!content) continue;

        const hash = Buffer.from(content).toString('base64').substring(0, 32);
        const key = `${stat.size}-${hash}`;

        if (!fileHashes.has(key)) {
          fileHashes.set(key, []);
        }
        fileHashes.get(key).push(file);
      } catch { /* ignore */ }
    }

    const duplicates = Array.from(fileHashes.entries())
      .filter(([_, files]) => files.length > 1)
      .map(([_, files]) => ({ duplicates: files }));

    return {
      content: [{ type: 'text', text: JSON.stringify(duplicates, null, 2) }]
    };
  }
);

// ============================================
// TOOL: check_dependencies
// ============================================
server.tool(
  'check_dependencies',
  'Vérifie les dépendances non utilisées',
  {
    directory: z.string().describe('Chemin du projet')
  },
  async ({ directory }) => {
    const packagePath = path.join(directory, 'package.json');
    try {
      const pkg = JSON.parse(await fs.readFile(packagePath, 'utf8'));
      const allDeps = {
        ...pkg.dependencies || {},
        ...pkg.devDependencies || {}
      };

      const jsFiles = await glob('**/*.{js,jsx,ts,tsx}', { cwd: directory });
      const usedDeps = new Set();

      for (const file of jsFiles) {
        const content = await fs.readFile(path.join(directory, file), 'utf8');
        Object.keys(allDeps).forEach(dep => {
          if (content.includes(`'${dep}'`) || content.includes(`"${dep}"`)) {
            usedDeps.add(dep);
          }
        });
      }

      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            unused: Object.keys(allDeps).filter(dep => !usedDeps.has(dep)),
            total: Object.keys(allDeps).length,
            used: usedDeps.size
          }, null, 2)
        }]
      };
    } catch {
      return {
        content: [{ type: 'text', text: JSON.stringify({ error: 'No package.json found or invalid' }) }]
      };
    }
  }
);

// ============================================
// TOOL: disk_usage
// ============================================
server.tool(
  'disk_usage',
  "Analyse l'utilisation disque",
  {
    directory: z.string().describe('Chemin du dossier')
  },
  async ({ directory }) => {
    const result = [];

    async function calculateSize(dirPath) {
      let size = 0;
      const items = await fs.readdir(dirPath, { withFileTypes: true });

      for (const item of items) {
        const itemPath = path.join(dirPath, item.name);
        if (item.isDirectory()) {
          size += await calculateSize(itemPath);
        } else {
          const stat = await fs.stat(itemPath).catch(() => ({ size: 0 }));
          size += stat.size;
        }
      }
      return size;
    }

    const items = await fs.readdir(directory, { withFileTypes: true });
    for (const item of items) {
      if (item.isDirectory()) {
        const size = await calculateSize(path.join(directory, item.name));
        result.push({
          name: item.name,
          size: `${(size / 1048576).toFixed(2)}MB`,
          bytes: size
        });
      }
    }

    const sorted = result.sort((a, b) => b.bytes - a.bytes).slice(0, 20);

    return {
      content: [{ type: 'text', text: JSON.stringify(sorted, null, 2) }]
    };
  }
);

// ============================================
// DÉMARRAGE DU SERVEUR
// ============================================
const transport = new StdioServerTransport();
await server.connect(transport);
console.error('Filesystem MCP Server v2.0 running on stdio');
