# Développer Postulo sous Windows

Ce guide décrit l'installation d'un poste de développement sous Windows 11. Deux voies sont possibles :

- **Windows natif** (voie utilisée par la mainteneuse) : la plus simple au quotidien, mais elle exige de désactiver Smart App Control.
- **WSL2 (Ubuntu)** : Smart App Control peut rester actif, mais l'environnement est plus lourd.

## 1. Le problème Smart App Control

Smart App Control (« Contrôle intelligent des applications ») est une protection de Windows 11. Elle bloque les programmes et les DLL qui ne sont pas signés, ou dont la réputation est inconnue de Microsoft. Or de nombreuses bibliothèques Python contiennent des modules compilés (fichiers `.pyd`, c'est-à-dire des DLL) qui ne sont pas signés.

Constaté sur le poste de la mainteneuse, le 10 novembre 2026 :

| Bibliothèque | Résultat |
|---|---|
| pydantic-core, FastAPI, uvicorn, ruff | Fonctionnent |
| SQLAlchemy 2.1 (module `_util_cy`) | **Bloqué** |
| mypy (modules compilés avec mypyc) | **Bloqué** |
| pandas (version 1 de Postulo) | **Bloqué** |

Message typique :

```
ImportError: DLL load failed while importing _util_cy: Une stratégie de contrôle d'application a bloqué ce fichier.
```

Le blocage est irrégulier : une même DLL peut passer une fois puis être refusée, car la réputation est vérifiée en ligne. On ne peut donc pas compter dessus.

Pour connaître l'état de Smart App Control : **Sécurité Windows > Contrôle des applications et du navigateur > Paramètres de Smart App Control**. En PowerShell :

```
(Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\CI\Policy').VerifiedAndReputablePolicyState
```

`0` = désactivé, `1` = activé, `2` = évaluation.

## 2. Voie A : Windows natif

### 2.1 Désactiver Smart App Control (si tu choisis cette voie)

**Sécurité Windows > Contrôle des applications et du navigateur > Paramètres de Smart App Control > Désactivé.**

Conséquence importante : **une fois désactivé, Smart App Control ne peut plus être réactivé sans réinstaller ou réinitialiser Windows.** L'antivirus Microsoft Defender reste actif. Si tu ne veux pas faire ce choix, passe à la voie B (WSL2).

### 2.2 Installer les outils

Dans un terminal PowerShell :

```
winget install --id Python.Python.3.13 -e --scope user
winget install --id astral-sh.uv -e
winget install --id OpenJS.NodeJS.LTS -e
npm install -g pnpm
winget install --id Git.Git -e
```

Ferme puis rouvre le terminal (et VS Code) pour que le `PATH` soit pris en compte. Vérifie :

```
python --version
uv --version
node --version
pnpm --version
```

Préfère le Python de python.org (installeur signé) aux Python téléchargés par uv, qui ne sont pas signés.

### 2.3 Installer le projet

```
git clone https://github.com/HanineAttia/postulo.git
cd postulo
uv sync
pnpm -C frontend install
pnpm -C frontend build
uv run postulo
```

**N'active pas l'environnement virtuel** avec `.venv\Scripts\Activate.ps1` : la politique d'exécution de PowerShell le bloque souvent. Utilise toujours :

- `uv run <commande>` (par exemple `uv run pytest`) ;
- ou le chemin direct : `.venv\Scripts\python.exe -m postulo`.

### 2.4 Développer

```
uv run python scripts/dev.py
```

Ce script lance le backend avec rechargement automatique (port 8765) et le serveur Vite (port 5173). Ouvre http://localhost:5173. Arrêt : Ctrl+C.

Tests :

```
uv run pytest
pnpm -C frontend test
pnpm -C frontend build
pnpm -C frontend exec playwright install chromium
pnpm -C frontend e2e
```

Pour les tests de bout en bout, tu peux utiliser Microsoft Edge (déjà installé et signé) au lieu de Chromium : définis la variable `PLAYWRIGHT_CHANNEL=msedge` (en PowerShell : `$env:PLAYWRIGHT_CHANNEL = "msedge"`).

### 2.5 VS Code

Extensions conseillées : Python, Pylance, Ruff, ESLint, Tailwind CSS IntelliSense. Choisis l'interpréteur `.venv\Scripts\python.exe` (commande « Python: Select Interpreter »).

## 3. Voie B : WSL2 (Ubuntu)

Smart App Control ne s'applique pas aux programmes Linux de WSL.

1. Dans PowerShell (administrateur) : `wsl --install -d Ubuntu`, puis redémarre.
2. Ouvre Ubuntu, crée ton utilisateur, puis :
   ```
   sudo apt update && sudo apt install -y git curl build-essential
   curl -LsSf https://astral.sh/uv/install.sh | sh
   uv python install 3.13
   curl -fsSL https://fnm.vercel.app/install | bash   # gestionnaire de versions Node
   fnm install --lts
   npm install -g pnpm
   ```
3. Clone le dépôt **dans le système de fichiers Linux** (`~/postulo`, pas `/mnt/c/...`, beaucoup plus lent).
4. Dans VS Code, installe l'extension « WSL », puis ouvre le dossier avec `code .` depuis Ubuntu.
5. Mêmes commandes que la section 2.3. Les données vont dans `~/.local/share/postulo`.

`uv run postulo` ouvre le navigateur de Windows si WSL le permet ; sinon, ouvre l'adresse affichée dans le terminal.

## 4. Problèmes fréquents

| Symptôme | Solution |
|---|---|
| `DLL load failed ... Une stratégie de contrôle d'application a bloqué ce fichier` | Smart App Control : voir section 1. |
| `uv` ou `pnpm` introuvable juste après l'installation | Ferme et rouvre le terminal et VS Code. |
| `Activate.ps1 ne peut pas être chargé` | N'active pas l'environnement : `uv run ...`. |
| Accents illisibles dans le terminal | Utilise Windows Terminal ; `uv run postulo` écrit en UTF-8. |
| `git push` : `Failed to connect to github.com port 443` | Problème réseau intermittent : réessaie plus tard, ou depuis un autre réseau. |
| Page « l'interface n'est pas compilée » | `pnpm -C frontend install` puis `pnpm -C frontend build`. |
