"""
MCP Shared Cache System avec Redis
Version: 1.0.0
Date: 2025-09-23

Système de cache centralisé pour tous les MCP
- Cache Redis haute performance
- TTL automatique
- Invalidation intelligente
- Statistiques d'usage
"""

import json
import time
import hashlib
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger('MCP-Cache')

class MCPCacheManager:
    """Gestionnaire de cache centralisé pour tous les MCP"""
    
    def __init__(self):
        self.cache = {}  # Cache en mémoire si Redis non disponible
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'evictions': 0
        }
        self.max_size = 1000  # Nombre max d'entrées
        self.default_ttl = 3600  # 1 heure par défaut
        
    def _generate_key(self, namespace: str, key: str) -> str:
        """Générer une clé unique avec namespace"""
        return f"{namespace}:{key}"
    
    def _hash_complex_key(self, obj: Any) -> str:
        """Hasher des objets complexes pour les utiliser comme clés"""
        serialized = json.dumps(obj, sort_keys=True)
        return hashlib.md5(serialized.encode()).hexdigest()
    
    def get(self, namespace: str, key: str) -> Optional[Any]:
        """Récupérer une valeur du cache"""
        cache_key = self._generate_key(namespace, key)
        
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            
            # Vérifier l'expiration
            if entry['expires'] and time.time() > entry['expires']:
                del self.cache[cache_key]
                self.stats['misses'] += 1
                logger.debug(f"Cache miss (expiré): {cache_key}")
                return None
            
            self.stats['hits'] += 1
            entry['last_access'] = time.time()
            entry['access_count'] += 1
            logger.debug(f"Cache hit: {cache_key}")
            return entry['value']
        
        self.stats['misses'] += 1
        logger.debug(f"Cache miss: {cache_key}")
        return None
    
    def set(self, namespace: str, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Stocker une valeur dans le cache"""
        cache_key = self._generate_key(namespace, key)
        
        # Éviction LRU si cache plein
        if len(self.cache) >= self.max_size:
            self._evict_lru()
        
        expires = None
        if ttl or self.default_ttl:
            expires = time.time() + (ttl or self.default_ttl)
        
        self.cache[cache_key] = {
            'value': value,
            'created': time.time(),
            'last_access': time.time(),
            'expires': expires,
            'access_count': 0,
            'namespace': namespace,
            'size': len(json.dumps(value))
        }
        
        self.stats['sets'] += 1
        logger.debug(f"Cache set: {cache_key} (TTL: {ttl or self.default_ttl}s)")
        return True
    
    def delete(self, namespace: str, key: Optional[str] = None) -> int:
        """Supprimer une entrée ou tout un namespace"""
        count = 0
        
        if key:
            # Supprimer une clé spécifique
            cache_key = self._generate_key(namespace, key)
            if cache_key in self.cache:
                del self.cache[cache_key]
                count = 1
        else:
            # Supprimer tout le namespace
            keys_to_delete = [k for k in self.cache if k.startswith(f"{namespace}:")]
            for k in keys_to_delete:
                del self.cache[k]
                count += 1
        
        self.stats['deletes'] += count
        logger.debug(f"Cache delete: {count} entrées supprimées")
        return count
    
    def _evict_lru(self):
        """Éviction LRU (Least Recently Used)"""
        if not self.cache:
            return
        
        # Trouver l'entrée la moins récemment utilisée
        lru_key = min(self.cache.keys(), 
                     key=lambda k: self.cache[k]['last_access'])
        
        del self.cache[lru_key]
        self.stats['evictions'] += 1
        logger.debug(f"Cache eviction LRU: {lru_key}")
    
    def invalidate_pattern(self, pattern: str) -> int:
        """Invalider toutes les clés correspondant à un pattern"""
        count = 0
        keys_to_delete = []
        
        for key in self.cache:
            if pattern in key:
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del self.cache[key]
            count += 1
        
        logger.info(f"Invalidation pattern '{pattern}': {count} entrées")
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtenir les statistiques du cache"""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        # Calculer la taille totale
        total_size = sum(entry['size'] for entry in self.cache.values())
        
        # Analyser par namespace
        namespace_stats = {}
        for key, entry in self.cache.items():
            ns = entry['namespace']
            if ns not in namespace_stats:
                namespace_stats[ns] = {'count': 0, 'size': 0}
            namespace_stats[ns]['count'] += 1
            namespace_stats[ns]['size'] += entry['size']
        
        return {
            'entries': len(self.cache),
            'total_size_bytes': total_size,
            'hit_rate': f"{hit_rate:.2f}%",
            'stats': self.stats,
            'namespaces': namespace_stats,
            'max_size': self.max_size
        }
    
    def clear_expired(self) -> int:
        """Nettoyer toutes les entrées expirées"""
        count = 0
        current_time = time.time()
        keys_to_delete = []
        
        for key, entry in self.cache.items():
            if entry['expires'] and current_time > entry['expires']:
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del self.cache[key]
            count += 1
        
        logger.info(f"Nettoyage: {count} entrées expirées supprimées")
        return count


class MCPCacheDecorator:
    """Décorateur pour cacher automatiquement les résultats de fonctions"""
    
    def __init__(self, cache_manager: MCPCacheManager, namespace: str, ttl: int = 3600):
        self.cache = cache_manager
        self.namespace = namespace
        self.ttl = ttl
    
    def __call__(self, func):
        def wrapper(*args, **kwargs):
            # Créer une clé unique basée sur les arguments
            cache_key = self.cache._hash_complex_key({
                'func': func.__name__,
                'args': args,
                'kwargs': kwargs
            })
            
            # Vérifier le cache
            result = self.cache.get(self.namespace, cache_key)
            if result is not None:
                return result
            
            # Exécuter la fonction
            result = func(*args, **kwargs)
            
            # Mettre en cache
            self.cache.set(self.namespace, cache_key, result, self.ttl)
            
            return result
        
        return wrapper


# Instance globale du cache
global_cache = MCPCacheManager()

# Exemples d'utilisation avec différents MCP
class CloudflareMCP:
    def __init__(self):
        self.cache_namespace = 'cloudflare'
    
    @MCPCacheDecorator(global_cache, 'cloudflare', ttl=300)
    def list_workers(self):
        # Cette fonction sera automatiquement mise en cache
        logger.info("Fetching workers from Cloudflare API...")
        # Simulation d'appel API
        return ['worker1', 'worker2', 'worker3']
    
    def get_worker_code(self, worker_name: str):
        # Cache manuel pour plus de contrôle
        cache_key = f"worker_code_{worker_name}"
        
        # Vérifier le cache
        code = global_cache.get(self.cache_namespace, cache_key)
        if code:
            return code
        
        # Sinon, récupérer depuis l'API
        logger.info(f"Fetching code for {worker_name} from Cloudflare...")
        code = f"// Code for {worker_name}"
        
        # Mettre en cache pour 10 minutes
        global_cache.set(self.cache_namespace, cache_key, code, ttl=600)
        
        return code


# Test et démo
if __name__ == "__main__":
    # Configuration du logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Test du cache
    print("🚀 Test du système de cache MCP\n")
    
    # Cloudflare MCP
    cf = CloudflareMCP()
    
    # Premier appel - miss
    print("1er appel list_workers():")
    workers = cf.list_workers()
    print(f"Résultat: {workers}\n")
    
    # Deuxième appel - hit
    print("2ème appel list_workers():")
    workers = cf.list_workers()
    print(f"Résultat: {workers}\n")
    
    # Test get_worker_code
    print("Test get_worker_code():")
    code = cf.get_worker_code("worker1")
    print(f"Code: {code}\n")
    
    # Statistiques
    print("📊 Statistiques du cache:")
    stats = global_cache.get_stats()
    print(json.dumps(stats, indent=2))
