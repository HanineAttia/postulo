# Postulo — Synthèse des recherches et sources

À placer dans `docs/research.md`. Claude Code s'y réfère pour les règles du CV (section 7 du SPEC) et pour le marché caché (section 9).

## 1. Lecture des CV par les recruteurs
- **Lecture très rapide.** Une étude de suivi oculaire (Ladders) montre que les recruteurs passent quelques secondes sur un premier survol. Ils regardent d'abord le nom, le poste actuel, les dates, puis la formation. Les mises en page simples, en une colonne, avec des intitulés clairs, sont les plus efficaces. Les CV chargés ou en plusieurs colonnes, les moins efficaces. Source : [HR Dive](https://www.hrdive.com/news/eye-tracking-study-shows-recruiters-look-at-resumes-for-7-seconds/).
- **Pratiques françaises pour les étudiants** : formation en premier, titre explicite, une page, accroche courte, centres d'intérêt concrets. Sources : [Guide CV, Université Savoie Mont Blanc](https://www.club-entreprises.univ-smb.fr/content/uploads/LE-CV-2022.pdf), [L'Etudiant, ce que regardent les recruteurs](https://www.letudiant.fr/jobsstages/lettres-de-motivation_1/sondage-exclusif-ce-que-les-recruteurs-regardent-le-plus-sur-les-cv-17376.html).

## 2. ATS (logiciels de recrutement)
- **Échecs de lecture fréquents** : colonnes multiples, tableaux, coordonnées en en-tête ou pied de page, icônes, intitulés non standards, formats de date mélangés. Source : [ATS Verification, 10 échecs fréquents](https://atsverification.com/blog/10-most-common-ats-parsing-failures/).
- **CV en LaTeX** : compatibles ATS à condition de rendre le texte extractible (`glyphtounicode`), de désactiver les ligatures et d'éviter les colonnes. Source : [ATS Verification, LaTeX](https://atsverification.com/blog/latex-resume-ats-friendly/).
- **Typst** : testé pour Postulo. Avec `ligatures: false`, le texte extrait est propre (« office », « efficacité » intacts), les liens `mailto:` et `https://` sont cliquables, et les caractères spéciaux passent sans échappement grâce aux données JSON. Il existe des modèles ATS sous licence MIT, par exemple [atsthetic-cv](https://typst.app/universe/package/atsthetic-cv).

## 3. Marché caché de l'emploi
- **Ampleur** : selon Randstad, environ 41 % des embauches de 2020 en France ont eu lieu sans offre publiée (50 % en 2019). La méthode compare les déclarations d'embauche aux offres collectées. La part varie fortement selon le secteur. Sources : [Randstad (PDF)](https://www.grouperandstad.fr/wp-content/uploads/2021/02/randstad-cp-smartdata-marche-invisible-vf.pdf), [Économie Matin, 2022 : environ 1 embauche sur 3 au premier trimestre](https://www.economiematin.fr/news-recrutement-marche-invisible-2022-reseau-cooptation-candidatures-spontanees).
- **Cadres** : selon l'APEC (2019), 32 % des cadres recrutés en 2018 étaient déjà connus d'un salarié ou recommandés. Les réseaux sociaux professionnels sont utilisés par 53 % des recruteurs (69 % en 2021). L'approche directe est passée de 22 % à 32 % entre 2015 et 2018. Sources : [Université Paris-Saclay, étude APEC](https://www.universite-paris-saclay.fr/actualites/etude-apec-sur-lembauche-des-cadres-les-reseaux-relationnels-toujours-mobilises-vive-le-reseau-des-diplomes), [APEC, pratiques de recrutement (PDF)](https://corporate.apec.fr/files/live/sites/corporate/files/Nos%20%c3%a9tudes/CP%20Apec%20-%20Pratiques%20de%20recrutements%20des%20cadres.pdf).
- **Cooptation** :
  - Selon l'étude Lever, 1 candidat coopté sur 16 est embauché, contre 1 sur 72 pour les candidats approchés et 1 sur 152 pour les candidats qui postulent. Source : [SHRM](https://shrm.org/topics-tools/news/talent-acquisition/lever-study-shows-1-100-candidates-hired).
  - En France (IntoTheMinds, 2023, 500 DRH), 31 % des entreprises ont un programme de cooptation, jugé le canal le moins cher et le plus rapide. Source : [IntoTheMinds](https://www.intotheminds.com/blog/cooptation-etude-sondage-france-drh/).
- **Viviers de talents et finalistes (*silver medalists*)** : les entreprises recontactent en priorité les candidats déjà évalués. C'est plus rapide et moins coûteux. Elles entretiennent aussi des communautés de talents (newsletters, événements, relances). Sources : [Greenhouse](https://www.greenhouse.com/uk/blog/4-reasons-reach-out-previously-candidates), [Welcome to the Jungle, talent nurturing](https://www.welcometothejungle.com/fr/articles/talent-nurturing-comment-entretenir-vivier-candidats).
- **Signaux d'embauche**, de quelques jours à quelques semaines avant les offres : levée de fonds, plusieurs postes ouverts dans une même équipe, arrivée d'un nouveau responsable, adoption d'une technologie, croissance des effectifs, nouveau bureau, départ d'un dirigeant. Ce sont des estimations de praticiens, à utiliser comme indicateurs et non comme garanties. Source : [DEV Community, 7 hiring signals](https://dev.to/nathanhamlett/the-7-hiring-signals-that-predict-budget-before-the-job-posting-goes-up-12d0).
- **Être trouvable** : l'option LinkedIn « Open to Work » en mode « recruteurs uniquement » rend le profil filtrable dans LinkedIn Recruiter, et les intitulés de poste indiqués sont recherchables. Source : [LoopCV](https://www.loopcv.pro/guides/linkedin-open-to-work/).
- **Stage de fin d'études** : le stage sert de période de pré-embauche. Il est conseillé d'aborder le sujet tôt et de faire des points réguliers. Source : [JobTeaser](https://www.jobteaser.com/fr/advices/210-comment-mettre-toutes-les-chances-de-son-cote-pour-etre-recrute-en-stage-de-fin-d-etude).

## 4. Choix techniques
- **Claude Agent SDK** : « Unless previously approved, Anthropic does not allow third party developers to offer claude.ai login or rate limits for their products, including agents built on the Claude Agent SDK. » Le CLI peut être piloté en sous-processus avec `-p`. Source : [Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview).
- **Commande Claude Code utilisée par la v1**, testée et fonctionnelle : `claude -p "<consigne>" --output-format text --no-session-persistence --disallowedTools "mcp__*" --tools ""`, avec le prompt sur stdin. Recherche web : `--tools "WebSearch,WebFetch" --allowedTools "WebSearch,WebFetch"`.

## 5. Règles reconnues pour le CV (SPEC 16.3)

Il n'existe pas de norme internationale unique. Postulo applique un socle commun tiré des guides de Harvard Career Services, la formule XYZ pour les puces, puis une variante selon la langue. Sources :
- [Harvard Extension School, Create impactful resumes and cover letters](https://careerservices.fas.harvard.edu/resources/hes-create-impactful-resumes-and-cover-letters/) (`harvard-hes`).
- [Harvard T.H. Chan School of Public Health, Resume Guide (PDF, 2016)](https://content.sph.harvard.edu/wwwhsph/sites/36/2016/06/Resume-Guide-June-2016.pdf) (`harvard-chan`).
- [Formule XYZ de Laszlo Bock, ancien DRH de Google (Quartz)](https://qz.com/201088/google-just-revealed-the-incredibly-simple-formula-for-killer-resumes) (`bock-xyz`) : « Accomplished [X] as measured by [Y], by doing [Z] ».

Chaque règle a un identifiant stable, repris par le code (`services/documents/rules.py`), les prompts et le jury simulé, qui cite l'identifiant dans ses corrections.

| Id | Règle | Source |
|---|---|---|
| R-01 | Verbes d'action, réalisations plutôt que tâches | harvard-hes, harvard-chan |
| R-02 | Résultats chiffrés quand le parcours les contient ; puces au format XYZ (X accompli, mesuré par Y, en faisant Z) | bock-xyz, harvard-hes |
| R-03 | Pas de pronoms personnels, pas de « responsable de » | harvard-hes, harvard-chan |
| R-04 | Ordre antéchronologique | harvard-hes, harvard-chan |
| R-05 | Cohérence du gras, de l'italique, des majuscules et de la ponctuation des puces (Postulo : aucun point final) | harvard-chan |
| R-06 | Équilibre entre texte et espaces blancs ; page d'un CV remplie entre 85 et 100 % | harvard-chan, SPEC 16.1 |
| R-07 | Même police pour le CV et la lettre | harvard-hes |
| R-08 | Une page pour un étudiant ou un jeune diplômé | harvard-hes, harvard-chan |
| R-09 | Pas de photo, d'âge ni de situation familiale | harvard-hes |
| R-10 | Envoi en PDF | harvard-hes |
| R-11 | Lettre d'une page, adaptée à l'organisation et au poste, qui ne répète pas le CV | harvard-hes |
| R-12 | Variante France : titre explicite, formation d'abord pour un étudiant, lettre « vous / moi / nous » | section 1 ci-dessus, SPEC 7.1 et 7.3 |
| R-13 | Variante internationale (anglais) : section « Summary », mois abrégés en anglais, format A4 ou Letter | harvard-hes |
| R-14 | Mots-clés de l'offre repris avec leur orthographe exacte quand ils décrivent fidèlement le parcours | section 2 ci-dessus |
