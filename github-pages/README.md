# Mise en ligne GitHub Pages

Ce dossier est pret a etre publie sur GitHub Pages.

## Contenu

- `index.html`
- `style.css`
- `script.js`
- `data.json`
- `assets/`

## Etapes

1. Creez un depot GitHub.
2. Deposez le contenu de ce dossier a la racine du depot.
3. Ouvrez `Settings > Pages`.
4. Dans `Build and deployment`, choisissez :
   - `Source` : `Deploy from a branch`
   - `Branch` : `main` (ou `master`)
   - `Folder` : `/ (root)`
5. Enregistrez.

GitHub publiera ensuite le site sur une adresse du type :

`https://votre-compte.github.io/nom-du-depot/`

## Mise a jour des sujets

Quand vous regenez la base locale :

1. relancez le script de construction ;
2. recopiez `index.html`, `style.css`, `script.js`, `data.json` et le dossier `assets/` dans ce dossier ;
3. envoyez les fichiers mis a jour sur GitHub.

## Important

Le site charge les donnees depuis `data.json`.
Sur GitHub Pages, cela fonctionne normalement.
En ouvrant directement `index.html` avec `file://`, certains navigateurs peuvent bloquer ce chargement.
