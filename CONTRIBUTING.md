# Contribuer à Postulo

Merci de ton intérêt ! Postulo est un projet open source et bénévole. Toute contribution est bienvenue : signalement de bug, idée, documentation, code.

## Avant de commencer

- Lis le cahier des charges [docs/SPEC.md](docs/SPEC.md), en particulier la section 0 (règles) et la section 1 (principes).
- Lis [CLAUDE.md](CLAUDE.md) : commandes, architecture et conventions.
- Pour une modification importante, ouvre d'abord une issue pour en discuter.

## Règles non négociables

Postulo n'accepte aucune contribution qui :

- contourne une protection anti-robot ou un CAPTCHA ;
- aspire LinkedIn, Indeed ou tout site qui l'interdit ;
- envoie un message ou une candidature automatiquement ;
- invente un élément du parcours de l'utilisateur ;
- collecte en masse des données personnelles de tiers ;
- ajoute de la télémétrie ou une dépendance payante obligatoire.

## Mettre en place l'environnement

Voir le [README](README.md) et, sous Windows, [docs/dev-windows.md](docs/dev-windows.md).

## Avant chaque commit

```
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
pnpm -C frontend lint
pnpm -C frontend typecheck
pnpm -C frontend test
```

Les tests ne doivent faire **aucun appel réseau ni aucun appel IA réel** : utilise le fournisseur `MockProvider`. Les tests qui touchent une vraie API sont marqués `@pytest.mark.network` et désactivés par défaut.

## Conventions

- Code, noms et commentaires en anglais. Textes de l'interface uniquement dans `frontend/src/i18n/fr.json` et `en.json`.
- Messages de commit au format [Conventional Commits](https://www.conventionalcommits.org/fr/) (`feat:`, `fix:`, `docs:`, `test:`, `ci:`...).
- Petits commits, une intention par commit.
- Interface sobre : pas d'emoji, icônes lucide uniquement, couleurs via les jetons de design.

## Signaler une faille de sécurité

N'ouvre pas d'issue publique : utilise le signalement privé de GitHub (onglet « Security » du dépôt).
