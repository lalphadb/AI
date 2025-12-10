"""
🔄 Module GitOps - Gestion versionnée de l'infrastructure

Outils disponibles:
- gitops_init: Initialiser Git sur un projet
- gitops_status: Voir le statut Git
- gitops_commit: Commit les changements
- gitops_rollback: Revenir à une version précédente
- gitops_setup_hooks: Configurer les hooks de déploiement
- gitops_log: Voir l'historique des commits
"""

import os
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
import logging

from config.settings import (
    INFRA_DIR, GITOPS_REMOTE, GITOPS_BRANCH, 
    GITOPS_AUTO_COMMIT, SCRIPTS_DIR
)

logger = logging.getLogger(__name__)


class GitOpsTools:
    """Outils GitOps pour la gestion versionnée"""
    
    def __init__(self):
        self.default_repo = INFRA_DIR
    
    def _run_git(self, args: List[str], cwd: Optional[Path] = None) -> Dict[str, Any]:
        """Exécuter une commande git"""
        cwd = cwd or self.default_repo
        
        try:
            result = subprocess.run(
                ["git"] + args,
                capture_output=True,
                text=True,
                cwd=str(cwd),
                timeout=60
            )
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "returncode": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Timeout Git"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # === 1. GITOPS INIT ===
    def gitops_init(self, path: Optional[str] = None) -> Dict[str, Any]:
        """
        Initialiser un dépôt Git pour GitOps
        
        Args:
            path: Chemin du répertoire (default: INFRA_DIR)
            
        Returns:
            Dict avec le statut de l'initialisation
        """
        repo_path = Path(path) if path else self.default_repo
        
        try:
            # Vérifier si déjà un repo Git
            if (repo_path / ".git").exists():
                return {
                    "success": True,
                    "message": f"Dépôt Git déjà initialisé: {repo_path}",
                    "already_exists": True
                }
            
            # Initialiser le repo
            result = self._run_git(["init"], cwd=repo_path)
            if not result["success"]:
                return result
            
            # Créer .gitignore
            gitignore_content = """# Secrets
.env
*.env
secrets/
*.pem
*.key

# Logs
logs/
*.log

# Backups
backups/
*.bak

# Cache
__pycache__/
.cache/
node_modules/

# IDE
.vscode/
.idea/

# Volumes Docker
volumes/
data/
"""
            gitignore_path = repo_path / ".gitignore"
            gitignore_path.write_text(gitignore_content)
            
            # Premier commit
            self._run_git(["add", "."], cwd=repo_path)
            self._run_git(["commit", "-m", "🎉 Initial GitOps setup"], cwd=repo_path)
            
            logger.info(f"GitOps initialisé: {repo_path}")
            
            return {
                "success": True,
                "message": f"Dépôt Git initialisé: {repo_path}",
                "path": str(repo_path)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # === 2. GITOPS STATUS ===
    def gitops_status(self, path: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtenir le statut Git du dépôt
        
        Args:
            path: Chemin du dépôt
            
        Returns:
            Dict avec le statut détaillé
        """
        repo_path = Path(path) if path else self.default_repo
        
        try:
            # Vérifier si c'est un repo Git
            if not (repo_path / ".git").exists():
                return {
                    "success": False,
                    "error": f"Pas un dépôt Git: {repo_path}",
                    "hint": "Utilisez gitops_init() pour initialiser"
                }
            
            # Statut
            status_result = self._run_git(["status", "--porcelain"], cwd=repo_path)
            
            # Branch actuelle
            branch_result = self._run_git(["branch", "--show-current"], cwd=repo_path)
            
            # Dernier commit
            log_result = self._run_git(
                ["log", "-1", "--format=%H|%s|%ci"], 
                cwd=repo_path
            )
            
            # Parser le statut
            changes = {
                "modified": [],
                "added": [],
                "deleted": [],
                "untracked": []
            }
            
            if status_result["stdout"]:
                for line in status_result["stdout"].split("\n"):
                    if line:
                        status_code = line[:2]
                        file_path = line[3:]
                        
                        if "M" in status_code:
                            changes["modified"].append(file_path)
                        elif "A" in status_code:
                            changes["added"].append(file_path)
                        elif "D" in status_code:
                            changes["deleted"].append(file_path)
                        elif "?" in status_code:
                            changes["untracked"].append(file_path)
            
            # Parser le dernier commit
            last_commit = None
            if log_result["success"] and log_result["stdout"]:
                parts = log_result["stdout"].split("|")
                if len(parts) >= 3:
                    last_commit = {
                        "hash": parts[0][:8],
                        "message": parts[1],
                        "date": parts[2]
                    }
            
            has_changes = any(changes[k] for k in changes)
            
            return {
                "success": True,
                "path": str(repo_path),
                "branch": branch_result.get("stdout", "unknown"),
                "has_changes": has_changes,
                "changes": changes,
                "last_commit": last_commit,
                "is_clean": not has_changes
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # === 3. GITOPS COMMIT ===
    def gitops_commit(
        self, 
        message: str, 
        path: Optional[str] = None,
        files: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Commit les changements
        
        Args:
            message: Message de commit
            path: Chemin du dépôt
            files: Liste de fichiers spécifiques (ou tous si None)
            
        Returns:
            Dict avec le résultat du commit
        """
        repo_path = Path(path) if path else self.default_repo
        
        try:
            # Vérifier le statut d'abord
            status = self.gitops_status(str(repo_path))
            if not status["success"]:
                return status
            
            if not status["has_changes"]:
                return {
                    "success": True,
                    "message": "Aucun changement à committer",
                    "committed": False
                }
            
            # Ajouter les fichiers
            if files:
                for f in files:
                    self._run_git(["add", f], cwd=repo_path)
            else:
                self._run_git(["add", "-A"], cwd=repo_path)
            
            # Commit
            result = self._run_git(["commit", "-m", message], cwd=repo_path)
            
            if not result["success"]:
                return result
            
            # Obtenir le hash du commit
            hash_result = self._run_git(["rev-parse", "--short", "HEAD"], cwd=repo_path)
            
            logger.info(f"GitOps commit: {message}")
            
            return {
                "success": True,
                "message": f"Commit créé: {message}",
                "hash": hash_result.get("stdout", "unknown"),
                "committed": True
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # === 4. GITOPS ROLLBACK ===
    def gitops_rollback(
        self, 
        target: str = "HEAD~1",
        path: Optional[str] = None,
        hard: bool = False
    ) -> Dict[str, Any]:
        """
        Revenir à une version précédente
        
        Args:
            target: Commit cible (ex: HEAD~1, abc1234)
            path: Chemin du dépôt
            hard: Reset hard (supprime les changements non commités)
            
        Returns:
            Dict avec le résultat du rollback
        """
        repo_path = Path(path) if path else self.default_repo
        
        try:
            # Backup avant rollback
            backup_branch = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self._run_git(["branch", backup_branch], cwd=repo_path)
            
            # Type de reset
            reset_type = "--hard" if hard else "--soft"
            
            # Rollback
            result = self._run_git(["reset", reset_type, target], cwd=repo_path)
            
            if not result["success"]:
                return result
            
            logger.warning(f"GitOps rollback vers {target}")
            
            return {
                "success": True,
                "message": f"Rollback effectué vers {target}",
                "target": target,
                "backup_branch": backup_branch,
                "warning": "Utilisez git branch -D {backup_branch} pour supprimer le backup"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # === 5. GITOPS SETUP HOOKS ===
    def gitops_setup_hooks(self, path: Optional[str] = None) -> Dict[str, Any]:
        """
        Configurer les hooks Git pour auto-déploiement
        
        Args:
            path: Chemin du dépôt
            
        Returns:
            Dict avec le statut de configuration
        """
        repo_path = Path(path) if path else self.default_repo
        hooks_dir = repo_path / ".git" / "hooks"
        
        try:
            if not hooks_dir.exists():
                return {
                    "success": False,
                    "error": f"Pas un dépôt Git: {repo_path}"
                }
            
            # Hook post-commit: Déploiement automatique
            post_commit = """#!/bin/bash
# 🚀 Hook post-commit - Auto-deploy

echo "📦 Déploiement automatique..."

# Chemin du script de déploiement
DEPLOY_SCRIPT="${SCRIPTS_DIR}/docker/deploy_4lb_stack.sh"

if [ -f "$DEPLOY_SCRIPT" ]; then
    echo "Exécution de $DEPLOY_SCRIPT"
    bash "$DEPLOY_SCRIPT"
else
    echo "Script de déploiement non trouvé: $DEPLOY_SCRIPT"
    echo "Déploiement manuel requis: docker compose up -d"
fi

echo "✅ Déploiement terminé"
"""
            
            # Hook pre-commit: Validation
            pre_commit = """#!/bin/bash
# 🔍 Hook pre-commit - Validation

echo "🔍 Validation avant commit..."

# Vérifier la syntaxe docker-compose
if [ -f "docker-compose.yml" ]; then
    docker compose config -q
    if [ $? -ne 0 ]; then
        echo "❌ Erreur de syntaxe dans docker-compose.yml"
        exit 1
    fi
    echo "✅ docker-compose.yml valide"
fi

# Vérifier les fichiers YAML
for f in $(git diff --cached --name-only | grep -E '\\.(yml|yaml)$'); do
    python3 -c "import yaml; yaml.safe_load(open('$f'))" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "❌ Erreur YAML dans $f"
        exit 1
    fi
done

echo "✅ Validation OK"
exit 0
"""
            
            # Écrire les hooks
            hooks_created = []
            
            post_commit_path = hooks_dir / "post-commit"
            post_commit_path.write_text(post_commit.replace("${SCRIPTS_DIR}", str(SCRIPTS_DIR)))
            post_commit_path.chmod(0o755)
            hooks_created.append("post-commit")
            
            pre_commit_path = hooks_dir / "pre-commit"
            pre_commit_path.write_text(pre_commit)
            pre_commit_path.chmod(0o755)
            hooks_created.append("pre-commit")
            
            logger.info(f"Hooks GitOps configurés: {hooks_created}")
            
            return {
                "success": True,
                "message": "Hooks Git configurés",
                "hooks": hooks_created,
                "path": str(hooks_dir)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # === 6. GITOPS LOG ===
    def gitops_log(
        self, 
        path: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Voir l'historique des commits
        
        Args:
            path: Chemin du dépôt
            limit: Nombre de commits à afficher
            
        Returns:
            Dict avec la liste des commits
        """
        repo_path = Path(path) if path else self.default_repo
        
        try:
            result = self._run_git(
                ["log", f"-{limit}", "--format=%H|%s|%an|%ci"],
                cwd=repo_path
            )
            
            if not result["success"]:
                return result
            
            commits = []
            for line in result["stdout"].split("\n"):
                if line:
                    parts = line.split("|")
                    if len(parts) >= 4:
                        commits.append({
                            "hash": parts[0][:8],
                            "full_hash": parts[0],
                            "message": parts[1],
                            "author": parts[2],
                            "date": parts[3]
                        })
            
            return {
                "success": True,
                "commits": commits,
                "count": len(commits),
                "path": str(repo_path)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}


# Instance singleton
gitops_tools = GitOpsTools()
