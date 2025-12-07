#!/usr/bin/env node
/**
 * ChromaDB MCP Server v2.0.0
 * Migré vers la nouvelle API McpServer (SDK v1.23+)
 * Supporte à la fois Open WebUI (RAG) et Claude (mémoire)
 * Date: 2025-11-30
 */

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import { ChromaClient } from 'chromadb';

// Configuration
const CHROMA_HOST = process.env.CHROMA_HOST || 'localhost';
const CHROMA_PORT = process.env.CHROMA_PORT || '8000';

const client = new ChromaClient({
  path: `http://${CHROMA_HOST}:${CHROMA_PORT}`
});

// Créer le serveur MCP
const server = new McpServer({
  name: 'chromadb-mcp',
  version: '2.0.0'
});

// ============================================
// TOOL: create_collection
// ============================================
server.tool(
  'create_collection',
  'Créer une nouvelle collection dans ChromaDB pour stocker des documents',
  {
    name: z.string().describe('Nom de la collection'),
    metadata: z.record(z.string()).optional().describe('Métadonnées optionnelles')
  },
  async ({ name, metadata }) => {
    await client.createCollection({
      name,
      metadata: metadata || {}
    });
    return {
      content: [{ type: 'text', text: `✅ Collection "${name}" créée avec succès!` }]
    };
  }
);

// ============================================
// TOOL: list_collections
// ============================================
server.tool(
  'list_collections',
  'Lister toutes les collections disponibles dans ChromaDB',
  {},
  async () => {
    const collections = await client.listCollections();
    if (collections.length === 0) {
      return {
        content: [{ type: 'text', text: 'Aucune collection trouvée dans ChromaDB.' }]
      };
    }
    const list = collections.map(c => `- ${c.name}`).join('\n');
    return {
      content: [{ type: 'text', text: `📚 Collections disponibles:\n${list}` }]
    };
  }
);

// ============================================
// TOOL: add_documents
// ============================================
server.tool(
  'add_documents',
  'Ajouter des documents à une collection avec embeddings automatiques',
  {
    collection: z.string().describe('Nom de la collection'),
    documents: z.array(z.string()).describe('Liste des documents texte à ajouter'),
    ids: z.array(z.string()).describe('IDs uniques pour chaque document'),
    metadatas: z.array(z.record(z.unknown())).optional().describe('Métadonnées pour chaque document')
  },
  async ({ collection, documents, ids, metadatas }) => {
    const col = await client.getOrCreateCollection({ name: collection });
    await col.add({
      ids,
      documents,
      metadatas: metadatas || documents.map(() => ({}))
    });
    return {
      content: [{
        type: 'text',
        text: `✅ ${documents.length} document(s) ajouté(s) à la collection "${collection}"`
      }]
    };
  }
);

// ============================================
// TOOL: search_documents
// ============================================
server.tool(
  'search_documents',
  'Rechercher des documents similaires dans une collection par requête textuelle',
  {
    collection: z.string().describe('Nom de la collection'),
    query: z.string().describe('Texte de recherche'),
    n_results: z.number().default(5).describe('Nombre de résultats')
  },
  async ({ collection, query, n_results }) => {
    const col = await client.getCollection({ name: collection });
    const results = await col.query({
      queryTexts: [query],
      nResults: n_results
    });

    if (!results.documents[0] || results.documents[0].length === 0) {
      return {
        content: [{
          type: 'text',
          text: `Aucun résultat trouvé pour "${query}" dans "${collection}"`
        }]
      };
    }

    const formattedResults = results.documents[0].map((doc, i) => {
      const distance = results.distances?.[0]?.[i]?.toFixed(4) || 'N/A';
      const id = results.ids[0][i];
      const meta = results.metadatas?.[0]?.[i] ? JSON.stringify(results.metadatas[0][i]) : '';
      return `[${i + 1}] (score: ${distance}) ID: ${id}\n${doc}\n${meta ? `Meta: ${meta}` : ''}`;
    }).join('\n---\n');

    return {
      content: [{
        type: 'text',
        text: `🔍 Résultats pour "${query}":\n\n${formattedResults}`
      }]
    };
  }
);

// ============================================
// TOOL: delete_collection
// ============================================
server.tool(
  'delete_collection',
  'Supprimer une collection et tous ses documents',
  {
    name: z.string().describe('Nom de la collection à supprimer')
  },
  async ({ name }) => {
    await client.deleteCollection({ name });
    return {
      content: [{ type: 'text', text: `🗑️ Collection "${name}" supprimée.` }]
    };
  }
);

// ============================================
// TOOL: get_collection_info
// ============================================
server.tool(
  'get_collection_info',
  "Obtenir les informations et statistiques d'une collection",
  {
    name: z.string().describe('Nom de la collection')
  },
  async ({ name }) => {
    const collection = await client.getCollection({ name });
    const count = await collection.count();
    return {
      content: [{
        type: 'text',
        text: `📊 Collection "${name}":\n- Documents: ${count}\n- ID: ${collection.id}`
      }]
    };
  }
);

// ============================================
// TOOL: store_memory (NOUVEAU - pour Claude)
// ============================================
server.tool(
  'store_memory',
  'Stocker une mémoire/conversation dans ChromaDB pour Claude',
  {
    content: z.string().describe('Contenu de la mémoire à stocker'),
    topic: z.string().optional().describe('Sujet/catégorie de la mémoire'),
    tags: z.array(z.string()).optional().describe('Tags pour catégoriser')
  },
  async ({ content, topic, tags }) => {
    const collection = await client.getOrCreateCollection({ 
      name: 'claude-memory',
      metadata: { description: 'Mémoires Claude Desktop' }
    });

    const id = `memory-${Date.now()}`;
    const metadata = {
      timestamp: new Date().toISOString(),
      topic: topic || 'general',
      tags: tags?.join(',') || ''
    };

    await collection.add({
      ids: [id],
      documents: [content],
      metadatas: [metadata]
    });

    return {
      content: [{
        type: 'text',
        text: `🧠 Mémoire stockée avec succès!\nID: ${id}\nTopic: ${metadata.topic}`
      }]
    };
  }
);

// ============================================
// TOOL: recall_memory (NOUVEAU - pour Claude)
// ============================================
server.tool(
  'recall_memory',
  'Rechercher dans les mémoires stockées de Claude',
  {
    query: z.string().describe('Ce que vous cherchez'),
    topic: z.string().optional().describe('Filtrer par sujet'),
    limit: z.number().default(5).describe('Nombre de résultats max')
  },
  async ({ query, topic, limit }) => {
    try {
      const collection = await client.getCollection({ name: 'claude-memory' });

      const whereFilter = topic ? { topic: { $eq: topic } } : undefined;

      const results = await collection.query({
        queryTexts: [query],
        nResults: limit,
        where: whereFilter
      });

      if (!results.documents[0] || results.documents[0].length === 0) {
        return {
          content: [{ type: 'text', text: `Aucune mémoire trouvée pour "${query}"` }]
        };
      }

      const memories = results.documents[0].map((doc, i) => {
        const meta = results.metadatas?.[0]?.[i];
        const distance = results.distances?.[0]?.[i]?.toFixed(4) || 'N/A';
        return `📝 [Pertinence: ${distance}] ${meta?.timestamp || ''}\nTopic: ${meta?.topic || 'N/A'}\n${doc}`;
      }).join('\n\n---\n\n');

      return {
        content: [{
          type: 'text',
          text: `🧠 Mémoires retrouvées:\n\n${memories}`
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Collection claude-memory non trouvée. Utilisez store_memory d'abord.`
        }]
      };
    }
  }
);

// ============================================
// TOOL: delete_document
// ============================================
server.tool(
  'delete_document',
  'Supprimer un ou plusieurs documents par leurs IDs',
  {
    collection: z.string().describe('Nom de la collection'),
    ids: z.array(z.string()).describe('Liste des IDs à supprimer')
  },
  async ({ collection, ids }) => {
    const col = await client.getCollection({ name: collection });
    await col.delete({ ids });
    return {
      content: [{
        type: 'text',
        text: `🗑️ ${ids.length} document(s) supprimé(s) de "${collection}"`
      }]
    };
  }
);

// ============================================
// DÉMARRAGE DU SERVEUR
// ============================================
const transport = new StdioServerTransport();
await server.connect(transport);
console.error(`ChromaDB MCP Server v2.0 running (${CHROMA_HOST}:${CHROMA_PORT})`);
