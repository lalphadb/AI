"""
MCP Orchestrator - Système de coordination multi-MCP
Version: 1.0.0
Date: 2025-09-23

Orchestration avancée pour chaîner et coordonner plusieurs MCP
- Workflows configurables
- Exécution parallèle/séquentielle
- Gestion d'erreurs intelligente
- Retry automatique
- État persistant
"""

import json
import asyncio
import uuid
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum
import logging
import yaml

logger = logging.getLogger('MCP-Orchestrator')

class WorkflowStatus(Enum):
    """États possibles d'un workflow"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"

class StepType(Enum):
    """Types d'étapes dans un workflow"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    LOOP = "loop"
    TRY_CATCH = "try_catch"

class MCPWorkflowStep:
    """Représente une étape dans un workflow MCP"""
    
    def __init__(self, name: str, mcp: str, method: str, params: Dict[str, Any], 
                 step_type: StepType = StepType.SEQUENTIAL):
        self.id = str(uuid.uuid4())
        self.name = name
        self.mcp = mcp
        self.method = method
        self.params = params
        self.step_type = step_type
        self.status = WorkflowStatus.PENDING
        self.result = None
        self.error = None
        self.retries = 0
        self.max_retries = 3
        self.timeout = 30
        self.dependencies = []
        self.condition = None
    
    def add_dependency(self, step_id: str):
        """Ajouter une dépendance à cette étape"""
        self.dependencies.append(step_id)
    
    def set_condition(self, condition: Callable):
        """Définir une condition pour l'exécution"""
        self.condition = condition
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir en dictionnaire"""
        return {
            'id': self.id,
            'name': self.name,
            'mcp': self.mcp,
            'method': self.method,
            'params': self.params,
            'status': self.status.value,
            'result': self.result,
            'error': self.error,
            'retries': self.retries
        }

class MCPWorkflow:
    """Workflow orchestrant plusieurs MCP"""
    
    def __init__(self, name: str, description: str = ""):
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.steps = []
        self.status = WorkflowStatus.PENDING
        self.context = {}  # Contexte partagé entre les étapes
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.error_handler = None
    
    def add_step(self, step: MCPWorkflowStep):
        """Ajouter une étape au workflow"""
        self.steps.append(step)
        return step.id
    
    def set_error_handler(self, handler: Callable):
        """Définir un gestionnaire d'erreurs global"""
        self.error_handler = handler
    
    def get_step(self, step_id: str) -> Optional[MCPWorkflowStep]:
        """Récupérer une étape par son ID"""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir le workflow en dictionnaire"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'status': self.status.value,
            'steps': [step.to_dict() for step in self.steps],
            'context': self.context,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

class MCPOrchestrator:
    """Orchestrateur principal pour gérer les workflows MCP"""
    
    def __init__(self):
        self.workflows = {}
        self.mcp_clients = {}  # Connexions aux différents MCP
        self.running_workflows = set()
        self.max_concurrent_workflows = 10
    
    def register_mcp(self, name: str, client: Any):
        """Enregistrer un client MCP"""
        self.mcp_clients[name] = client
        logger.info(f"MCP '{name}' enregistré")
    
    async def execute_step(self, step: MCPWorkflowStep, context: Dict[str, Any]) -> Any:
        """Exécuter une étape du workflow"""
        logger.info(f"Exécution de l'étape: {step.name}")
        step.status = WorkflowStatus.RUNNING
        
        try:
            # Vérifier la condition si définie
            if step.condition and not step.condition(context):
                logger.info(f"Condition non remplie, étape {step.name} ignorée")
                step.status = WorkflowStatus.SUCCESS
                return None
            
            # Remplacer les variables dans les paramètres
            resolved_params = self._resolve_params(step.params, context)
            
            # Simuler l'appel MCP (à remplacer par l'implémentation réelle)
            # client = self.mcp_clients.get(step.mcp)
            # result = await client.call(step.method, resolved_params)
            
            # Simulation pour le test
            await asyncio.sleep(0.5)
            result = {
                'success': True,
                'data': f"Résultat de {step.name}",
                'timestamp': datetime.now().isoformat()
            }
            
            step.result = result
            step.status = WorkflowStatus.SUCCESS
            
            # Ajouter le résultat au contexte
            context[f"step_{step.name}_result"] = result
            
            logger.info(f"✅ Étape {step.name} terminée avec succès")
            return result
            
        except Exception as e:
            logger.error(f"❌ Erreur dans l'étape {step.name}: {e}")
            step.error = str(e)
            step.status = WorkflowStatus.FAILED
            step.retries += 1
            
            # Retry si possible
            if step.retries < step.max_retries:
                logger.info(f"🔄 Retry {step.retries}/{step.max_retries} pour {step.name}")
                step.status = WorkflowStatus.RETRYING
                await asyncio.sleep(2 ** step.retries)  # Backoff exponentiel
                return await self.execute_step(step, context)
            
            raise
    
    def _resolve_params(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Résoudre les variables dans les paramètres"""
        resolved = {}
        for key, value in params.items():
            if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
                # Variable du contexte
                var_name = value[2:-2].strip()
                resolved[key] = context.get(var_name, value)
            elif isinstance(value, dict):
                resolved[key] = self._resolve_params(value, context)
            else:
                resolved[key] = value
        return resolved
    
    async def execute_workflow(self, workflow: MCPWorkflow) -> Dict[str, Any]:
        """Exécuter un workflow complet"""
        if workflow.id in self.running_workflows:
            raise Exception(f"Workflow {workflow.id} déjà en cours")
        
        if len(self.running_workflows) >= self.max_concurrent_workflows:
            raise Exception("Trop de workflows en cours")
        
        self.running_workflows.add(workflow.id)
        workflow.status = WorkflowStatus.RUNNING
        workflow.started_at = datetime.now()
        
        logger.info(f"🚀 Démarrage du workflow: {workflow.name}")
        
        try:
            # Grouper les étapes par type
            sequential_steps = []
            parallel_groups = []
            current_parallel = []
            
            for step in workflow.steps:
                if step.step_type == StepType.PARALLEL:
                    current_parallel.append(step)
                else:
                    if current_parallel:
                        parallel_groups.append(current_parallel)
                        current_parallel = []
                    sequential_steps.append(step)
            
            if current_parallel:
                parallel_groups.append(current_parallel)
            
            # Exécuter les étapes
            for step in sequential_steps:
                # Vérifier les dépendances
                for dep_id in step.dependencies:
                    dep_step = workflow.get_step(dep_id)
                    if dep_step and dep_step.status != WorkflowStatus.SUCCESS:
                        raise Exception(f"Dépendance {dep_id} non satisfaite")
                
                await self.execute_step(step, workflow.context)
            
            # Exécuter les groupes parallèles
            for group in parallel_groups:
                tasks = [self.execute_step(step, workflow.context) for step in group]
                await asyncio.gather(*tasks)
            
            workflow.status = WorkflowStatus.SUCCESS
            workflow.completed_at = datetime.now()
            
            duration = (workflow.completed_at - workflow.started_at).total_seconds()
            logger.info(f"✅ Workflow {workflow.name} terminé en {duration:.2f}s")
            
            return {
                'success': True,
                'workflow': workflow.to_dict(),
                'duration': duration
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur dans le workflow {workflow.name}: {e}")
            workflow.status = WorkflowStatus.FAILED
            workflow.completed_at = datetime.now()
            
            if workflow.error_handler:
                await workflow.error_handler(e, workflow)
            
            return {
                'success': False,
                'error': str(e),
                'workflow': workflow.to_dict()
            }
        
        finally:
            self.running_workflows.discard(workflow.id)
    
    def create_workflow_from_yaml(self, yaml_config: str) -> MCPWorkflow:
        """Créer un workflow depuis une configuration YAML"""
        config = yaml.safe_load(yaml_config)
        
        workflow = MCPWorkflow(
            name=config['name'],
            description=config.get('description', '')
        )
        
        for step_config in config['steps']:
            step = MCPWorkflowStep(
                name=step_config['name'],
                mcp=step_config['mcp'],
                method=step_config['method'],
                params=step_config.get('params', {}),
                step_type=StepType[step_config.get('type', 'SEQUENTIAL').upper()]
            )
            
            if 'dependencies' in step_config:
                for dep in step_config['dependencies']:
                    step.add_dependency(dep)
            
            workflow.add_step(step)
        
        return workflow


# Exemples de workflows prédéfinis
class PredefinedWorkflows:
    """Bibliothèque de workflows prédéfinis"""
    
    @staticmethod
    def backup_and_optimize_workflow() -> MCPWorkflow:
        """Workflow de backup et optimisation"""
        workflow = MCPWorkflow(
            "Backup & Optimize",
            "Sauvegarde complète et optimisation du système"
        )
        
        # Étape 1: Vérifier l'espace disque
        check_space = MCPWorkflowStep(
            "check_disk_space",
            "studiosdb",
            "check_disk",
            {}
        )
        workflow.add_step(check_space)
        
        # Étape 2: Backup de la base de données
        backup_db = MCPWorkflowStep(
            "backup_database",
            "studiosdb",
            "mysql_backup",
            {"compress": True}
        )
        backup_db.add_dependency(check_space.id)
        workflow.add_step(backup_db)
        
        # Étape 3: Backup des fichiers (en parallèle)
        backup_files = MCPWorkflowStep(
            "backup_files",
            "filesystem",
            "create_archive",
            {"source": "/home/studiosdb", "destination": "/backup"},
            StepType.PARALLEL
        )
        workflow.add_step(backup_files)
        
        # Étape 4: Optimiser la base de données
        optimize_db = MCPWorkflowStep(
            "optimize_database",
            "studiosdb",
            "optimize_tables",
            {}
        )
        optimize_db.add_dependency(backup_db.id)
        workflow.add_step(optimize_db)
        
        # Étape 5: Nettoyer les logs
        clean_logs = MCPWorkflowStep(
            "clean_logs",
            "filesystem",
            "clean_old_files",
            {"directory": "/var/log", "days": 30}
        )
        workflow.add_step(clean_logs)
        
        return workflow
    
    @staticmethod
    def deploy_cloudflare_worker() -> MCPWorkflow:
        """Workflow de déploiement Cloudflare Worker"""
        workflow = MCPWorkflow(
            "Deploy Worker",
            "Déploiement automatisé d'un Cloudflare Worker"
        )
        
        # Étapes du workflow...
        # À implémenter selon les besoins
        
        return workflow


# Test et démonstration
if __name__ == "__main__":
    # Configuration du logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    async def test_orchestrator():
        print("🎭 Test de l'Orchestrateur MCP\n")
        
        # Créer l'orchestrateur
        orchestrator = MCPOrchestrator()
        
        # Créer un workflow de test
        workflow = PredefinedWorkflows.backup_and_optimize_workflow()
        
        # Exécuter le workflow
        result = await orchestrator.execute_workflow(workflow)
        
        # Afficher les résultats
        print("\n📊 Résultats du workflow:")
        print(json.dumps(result, indent=2))
    
    # Lancer le test
    asyncio.run(test_orchestrator())
