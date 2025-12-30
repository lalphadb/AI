# Analyse du code

Effectue une analyse complète pour trouver les problèmes:

1. **Complexité cyclomatique** (fonctions trop complexes):
```bash
python3 -c "
import ast
import os

def analyze_complexity(filepath):
    with open(filepath) as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Compter les branches
            branches = sum(1 for n in ast.walk(node) if isinstance(n, (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With)))
            if branches > 10:
                print(f'⚠️ {filepath}:{node.lineno} - {node.name}() complexité={branches}')

for root, dirs, files in os.walk('backend'):
    for f in files:
        if f.endswith('.py'):
            try:
                analyze_complexity(os.path.join(root, f))
            except: pass
"
```

2. **Fonctions trop longues** (>50 lignes):
```bash
python3 -c "
import ast
import os

for root, dirs, files in os.walk('backend'):
    for f in files:
        if f.endswith('.py'):
            try:
                with open(os.path.join(root, f)) as file:
                    tree = ast.parse(file.read())
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        lines = node.end_lineno - node.lineno if hasattr(node, 'end_lineno') else 0
                        if lines > 50:
                            print(f'⚠️ {os.path.join(root, f)}:{node.lineno} - {node.name}() {lines} lignes')
            except: pass
"
```

3. **Code dupliqué** (patterns répétés):
```bash
grep -rn "def " backend/*.py | cut -d: -f3 | sort | uniq -c | sort -rn | head -10
```

4. **TODO/FIXME oubliés**:
```bash
grep -rn "TODO\|FIXME\|XXX\|HACK" backend/ --include="*.py"
```

5. **Docstrings manquantes**:
```bash
python3 -c "
import ast
import os

for root, dirs, files in os.walk('backend'):
    for f in files:
        if f.endswith('.py') and not f.startswith('__'):
            try:
                with open(os.path.join(root, f)) as file:
                    tree = ast.parse(file.read())
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if not ast.get_docstring(node) and not node.name.startswith('_'):
                            print(f'📝 {os.path.join(root, f)}:{node.lineno} - {node.name}() sans docstring')
            except: pass
" | head -20
```

Pour chaque problème trouvé, propose une solution et implémente-la si approprié.
