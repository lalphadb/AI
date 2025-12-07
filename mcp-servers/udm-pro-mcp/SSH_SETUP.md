# 🔑 Configuration SSH pour UDM-Pro

## Commande SSH pour se connecter

```bash
ssh -i ~/.ssh/id_rsa_udm root@10.10.10.1
```

## Configuration Initiale de la Clé SSH

### Option 1: Créer une nouvelle clé

```bash
# Générer une nouvelle clé SSH
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa_udm -N ""

# Afficher la clé publique
cat ~/.ssh/id_rsa_udm.pub
```

### Option 2: Utiliser une clé existante

Si vous avez déjà une clé qui fonctionne:

```bash
# Copier la clé existante
cp /chemin/vers/votre/cle ~/.ssh/id_rsa_udm
cp /chemin/vers/votre/cle.pub ~/.ssh/id_rsa_udm.pub

# Corriger les permissions
chmod 600 ~/.ssh/id_rsa_udm
chmod 644 ~/.ssh/id_rsa_udm.pub
```

## Ajouter la clé sur le UDM-Pro

### Méthode 1: ssh-copy-id (recommandé)

```bash
ssh-copy-id -i ~/.ssh/id_rsa_udm.pub root@10.10.10.1
```

### Méthode 2: Manuel

1. **Afficher votre clé publique:**
   ```bash
   cat ~/.ssh/id_rsa_udm.pub
   ```

2. **Se connecter au UDM-Pro:**
   ```bash
   ssh root@10.10.10.1
   ```

3. **Sur le UDM-Pro, ajouter la clé:**
   ```bash
   # Créer le dossier si nécessaire
   mkdir -p ~/.ssh
   chmod 700 ~/.ssh
   
   # Ajouter votre clé publique
   echo "COLLEZ_VOTRE_CLE_PUBLIQUE_ICI" >> ~/.ssh/authorized_keys
   
   # Corriger les permissions
   chmod 600 ~/.ssh/authorized_keys
   ```

### Méthode 3: Via l'interface UniFi

1. Se connecter à l'interface web du UDM-Pro
2. Aller dans Settings > System > Advanced
3. Chercher "SSH Keys" ou "Device Authentication"
4. Ajouter votre clé publique

## Tester la Connexion

### Test rapide

```bash
ssh -i ~/.ssh/id_rsa_udm root@10.10.10.1 'hostname && uptime'
```

### Test avec le script fourni

```bash
cd /home/lalpha/projets/udm-pro-mcp-server
chmod +x test-ssh.sh
./test-ssh.sh
```

## Dépannage

### Permission denied (publickey)

**Cause:** La clé publique n'est pas sur le UDM-Pro ou les permissions sont incorrectes.

**Solution:**
```bash
# Sur votre machine locale
cat ~/.ssh/id_rsa_udm.pub

# Sur le UDM-Pro
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
cat ~/.ssh/authorized_keys  # Vérifier que votre clé est présente
```

### Connection timeout

**Cause:** Le UDM-Pro n'est pas accessible ou SSH est désactivé.

**Solution:**
```bash
# Tester la connectivité
ping 10.10.10.1

# Tester le port SSH
nc -zv 10.10.10.1 22
# ou
telnet 10.10.10.1 22
```

### Host key verification failed

**Solution:**
```bash
ssh-keygen -R 10.10.10.1
```

## Configuration SSH Avancée

### Créer un alias SSH

Ajoutez dans `~/.ssh/config`:

```
Host udm-pro
    HostName 10.10.10.1
    User root
    IdentityFile ~/.ssh/id_rsa_udm
    StrictHostKeyChecking no
```

Puis vous pouvez simplement utiliser:
```bash
ssh udm-pro
```

### Désactiver la vérification de l'host key (pour lab seulement)

```bash
ssh -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa_udm root@10.10.10.1
```

⚠️ **Attention:** Ne faites ceci que dans un environnement de test/lab.

## Sécurité

### Bonnes pratiques

1. **Permissions strictes:**
   ```bash
   chmod 700 ~/.ssh
   chmod 600 ~/.ssh/id_rsa_udm
   chmod 644 ~/.ssh/id_rsa_udm.pub
   ```

2. **Clé dédiée:** Utilisez une clé SSH différente pour chaque usage

3. **Passphrase:** Ajoutez une passphrase à votre clé (optionnel):
   ```bash
   ssh-keygen -p -f ~/.ssh/id_rsa_udm
   ```

4. **Limitation d'accès:** Sur le UDM-Pro, limitez l'accès SSH si possible

## Vérification Finale

Checklist avant d'utiliser le serveur MCP:

- [ ] Clé SSH générée dans `~/.ssh/id_rsa_udm`
- [ ] Permissions correctes (600 pour la clé privée)
- [ ] Clé publique ajoutée sur le UDM-Pro
- [ ] Test SSH manuel réussi
- [ ] `./test-ssh.sh` réussi

Une fois tous ces points validés, vous pouvez installer et utiliser le serveur MCP:

```bash
cd /home/lalpha/projets/udm-pro-mcp-server
./install.sh
```
