# Postulo

> Projet en cours de développement (phase 0 : fondations). Nom provisoire.

Postulo est une application **open source, locale et gratuite** qui aide à décrocher un stage, une alternance, un CDD, un CDI ou une mission en France, dans tous les métiers : bibliothèque de parcours, offres publiées et marché caché, CV et lettres adaptés et compatibles ATS, préparation aux entretiens, suivi des candidatures.

Principes : rien n'est inventé, c'est toi qui envoies tes candidatures, tes données restent sur ton ordinateur, aucune télémétrie, aucun coût obligatoire.

*English summary: see [README.en.md](README.en.md).*

## Installation (développement)

Prérequis : Python 3.12 ou plus récent ([python.org](https://www.python.org/downloads/)), [uv](https://docs.astral.sh/uv/), Node.js LTS et pnpm (seulement pour développer l'interface).

```
git clone https://github.com/HanineAttia/postulo.git
cd postulo
uv sync
pnpm -C frontend install
pnpm -C frontend build
uv run postulo
```

`uv run postulo` démarre le serveur sur `127.0.0.1` et ouvre ton navigateur. Au premier lancement, l'application est en **mode démo** : l'IA est simulée, aucun compte n'est nécessaire.

Pas besoin d'activer l'environnement virtuel : utilise `uv run ...`, ou `.venv\Scripts\python.exe -m postulo` sous Windows.

### Windows et Smart App Control

Sous Windows 11, **Smart App Control** peut bloquer des bibliothèques Python compilées (SQLAlchemy, pydantic, mypy...). Le message ressemble à :

```
ImportError: DLL load failed while importing _util_cy: Une stratégie de contrôle d'application a bloqué ce fichier.
```

Solutions : utiliser WSL2, ou désactiver Smart App Control (irréversible sans réinitialiser Windows). Détails dans [docs/dev-windows.md](docs/dev-windows.md).

## Où sont mes données ?

- Windows : `%APPDATA%\Postulo`
- Linux, WSL et macOS : `~/.local/share/postulo`
- Ou le dossier indiqué par la variable d'environnement `POSTULO_HOME`.

Les données ne sont jamais enregistrées dans le dépôt.

## Limites connues

- Phase 0 : seules les fondations existent (interface, mode démo, tâches de fond). Les fonctions métier arrivent dans les phases suivantes (voir [docs/SPEC.md](docs/SPEC.md)).

## Contribuer

Voir [CONTRIBUTING.md](CONTRIBUTING.md).

## Mention

Projet indépendant, non affilié à Anthropic, France Travail ni aux plateformes citées.

Licence : [MIT](LICENSE).
