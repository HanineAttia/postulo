# Postulo

> Projet en cours de développement (phase 2 : atelier de candidature). Nom provisoire.

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

Au premier lancement, un assistant en 5 étapes t'aide à choisir l'IA, à importer ton CV et à définir ton objectif. Tu peux le passer et y revenir depuis Réglages.

Pas besoin d'activer l'environnement virtuel : utilise `uv run ...`, ou `.venv\Scripts\python.exe -m postulo` sous Windows.

### Windows et Smart App Control

Sous Windows 11, **Smart App Control** peut bloquer des bibliothèques Python compilées (SQLAlchemy, pydantic, mypy...). Le message ressemble à :

```
ImportError: DLL load failed while importing _util_cy: Une stratégie de contrôle d'application a bloqué ce fichier.
```

Solutions : utiliser WSL2, ou désactiver Smart App Control (irréversible sans réinitialiser Windows). Détails dans [docs/dev-windows.md](docs/dev-windows.md).

## Mon parcours

La page **Mon parcours** contient tout ton parcours : identité et liens, objectif, formation, expériences, projets, compétences et langues, certifications et prix, engagements et publications. Chaque élément est une carte que tu peux déplier, modifier, supprimer et réordonner (glisser-déposer, ou flèches).

- **Import de CV** (PDF, DOCX, TXT) : Postulo lit le texte, l'IA le structure, puis tu vois un aperçu avant d'enregistrer. Deux choix : « Ajouter à ma bibliothèque » (fusion sans doublons, tes champs déjà remplis sont gardés) ou « Remplacer ». Un PDF scanné (une image) est détecté et signalé. Rien n'est inventé : un champ absent du CV reste vide.
- **Qualité du parcours** : un score sur 100 et des conseils concrets (réalisations chiffrées, au moins deux projets, liens...).
- **Sauvegarde** : export en JSON ou YAML, restauration avec aperçu, et un profil d'exemple fictif (« Camille Exemple »).

## Atelier : préparer une candidature

Dans **Atelier**, colle le texte d'une offre (ou clique sur « Utiliser l'offre d'exemple » en mode démo), choisis la langue (français ou anglais) et le modèle (Moderne ou Classique), puis « Préparer ma candidature ». Tu suis chaque étape en direct :

1. **Rédaction** : un seul appel à l'IA prépare le CV, la lettre, l'e-mail et des conseils. L'IA ne renvoie que des références vers ton parcours : organisations, dates, écoles, villes et liens viennent toujours de ta bibliothèque. Une compétence, un centre d'intérêt ou un chiffre absent de ton parcours est retiré et signalé.
2. **Mise en page** : PDF en une colonne avec Typst (polices Inter et Source Serif 4 intégrées), liens cliquables, sans ligature ni césure, réduit automatiquement pour tenir sur une page (deux pour un profil confirmé).
3. **Contrôle ATS** : Postulo relit le PDF comme un logiciel de recrutement (texte, nom en première ligne, coordonnées, liens, intitulés, dates, caractères illisibles) et mesure la couverture des mots-clés de l'offre.
4. **Jury simulé** : trois rôles (recrutement, manager, spécialiste ATS) notent la candidature sur 100 à partir du texte extrait.
5. **Correction** : sous le seuil (82 par défaut), une révision est faite une fois, puis tout est contrôlé et noté à nouveau. Tu vois la note avant et après.

Ensuite : aperçu des PDF, téléchargement, ouverture du dossier, e-mail modifiable (bouton « Ouvrir dans ma messagerie »), conseils et lacunes. L'onglet **Éditer** permet de modifier le titre, l'accroche, les puces ou la lettre et de régénérer les PDF **sans nouvel appel à l'IA**. Rien n'est envoyé à ta place : quand tu as envoyé ta candidature, clique sur « J'ai envoyé ».

Chaque candidature a son dossier (`applications/<id>` dans tes données) avec l'offre, le brouillon d'origine de l'IA, la révision, les rapports et les PDF (`CV_Prenom-Nom_Organisation.pdf`, `Lettre_Prenom-Nom_Organisation.pdf`).

Dans **Réglages > Documents** : moteur de rendu (Typst, ou HTML de secours qui imprime avec Microsoft Edge ou Google Chrome), modèle et langue par défaut, jury, correction et seuil.

## Choisir l'IA

Dans **Réglages**, choisis le fournisseur puis clique sur « Tester la connexion » :

- **Démo** (par défaut) : réponses simulées, sans compte ni coût.
- **API Anthropic** : ta propre clé API, facturée à l'usage. Modèle par défaut : Claude Sonnet 5.5 (modifiable). La clé est rangée dans le gestionnaire d'identifiants de ton système (keyring), jamais dans un fichier. À défaut, Postulo lit la variable d'environnement `ANTHROPIC_API_KEY`.
- **Claude Code** (usage personnel, désactivé par défaut) : utilise la commande `claude` installée et connectée sur ton ordinateur. Postulo la lance dans un dossier temporaire vide, sans aucun outil : Claude ne peut ni lire ni modifier tes fichiers. Les conditions d'Anthropic limitent l'utilisation d'un abonnement Claude dans des produits tiers : vérifie-les avant d'activer cette option.

## Où sont mes données ?

- Windows : `%APPDATA%\Postulo`
- Linux, WSL et macOS : `~/.local/share/postulo`
- Ou le dossier indiqué par la variable d'environnement `POSTULO_HOME`.

Les données ne sont jamais enregistrées dans le dépôt.

## Limites connues

- Phase 2 : la bibliothèque de parcours, l'import de CV, les fournisseurs d'IA et l'atelier de candidature sont disponibles. Les offres, le marché caché et le suivi arrivent dans les phases suivantes (voir [docs/SPEC.md](docs/SPEC.md)).
- En mode démo, les documents et les notes du jury sont simulés (74 puis 84) : ils montrent le fonctionnement, pas la qualité réelle d'une candidature.
- La lettre est un texte libre : Postulo signale les chiffres absents de ton parcours et de l'offre, mais relis-la toujours avant d'envoyer.
- Le moteur LaTeX facultatif et l'export DOCX ne sont pas encore disponibles.
- L'import ne lit pas les PDF scannés (pas de reconnaissance de caractères) ni le format `.doc` ancien : exporte ton CV en PDF texte ou en DOCX.
- Les liens cliquables d'un PDF ne sont pas encore extraits : seuls les liens écrits en toutes lettres sont repris.

## Contribuer

Voir [CONTRIBUTING.md](CONTRIBUTING.md).

## Mention

Projet indépendant, non affilié à Anthropic, France Travail ni aux plateformes citées.

Licence : [MIT](LICENSE).
