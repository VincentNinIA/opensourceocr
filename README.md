# OCR Mistral AI avec Streamlit

Application web pour extraire du texte de documents PDF et images en utilisant l'OCR de Mistral AI (modèle Pixtral-12B).

## Fonctionnalités

- Upload de fichiers PDF ou images (PNG, JPG, JPEG)
- **Deux moteurs OCR** : OCR dédié Mistral ou Pixtral avec prompt personnalisé
- **Détection automatique des tableaux** : Utilise PaddleOCR pour détecter et extraire les tableaux avant l'OCR
- Upscaling et padding automatique pour améliorer la précision
- Extraction de texte avec validation de qualité
- Visualisation côte à côte du document et du texte extrait
- Téléchargement du texte extrait au format Markdown ou TXT

## Installation

### 1. Cloner ou télécharger le projet

```bash
cd "OCR Sovotec test"
```

### 2. Créer un environnement virtuel (recommandé)

```bash
python -m venv venv
source venv/bin/activate  # Sur macOS/Linux
# ou
venv\Scripts\activate  # Sur Windows
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Configuration de la clé API

Créez un fichier `.env` à la racine du projet:

```bash
cp .env.example .env
```

Éditez le fichier `.env` et ajoutez votre clé API Mistral:

```
MISTRAL_API_KEY=votre_clé_api_ici
```

Pour obtenir une clé API Mistral:
1. Allez sur [console.mistral.ai](https://console.mistral.ai/)
2. Créez un compte ou connectez-vous
3. Générez une clé API dans la section API Keys

## Utilisation

### Lancer l'application

```bash
streamlit run app.py
```

L'application s'ouvrira automatiquement dans votre navigateur par défaut à l'adresse `http://localhost:8501`

### Workflow

1. Choisissez le moteur OCR (OCR dédié ou Pixtral)
2. Activez la détection automatique des tableaux si nécessaire (images uniquement)
3. Sélectionnez le type de fichier (PDF ou Image)
4. Uploadez votre document
5. Cliquez sur "Lancer l'OCR"
6. Visualisez le texte extrait (onglets Markdown formaté / Texte brut)
7. Téléchargez le résultat au format .md ou .txt

### Détection automatique des tableaux

Lorsque activée, l'application :
- Détecte automatiquement les tableaux dans l'image avec PaddleOCR
- Découpe chaque tableau avec padding
- Applique un upscaling pour améliorer la qualité
- Traite chaque tableau séparément
- Valide la qualité du résultat (nombre de colonnes stable, plausibilité des valeurs)
- Identifie le type de tableau (chemistry, mechanical, generic)

## Structure du projet

```
.
├── app.py              # Application Streamlit principale
├── table_chunker.py    # Module de détection et extraction de tableaux
├── requirements.txt    # Dépendances Python
├── .env               # Configuration (à créer)
├── .env.example       # Exemple de configuration
├── .gitignore         # Fichiers à ignorer par Git
├── CLAUDE.md          # Documentation pour Claude Code
└── README.md          # Documentation
```

## Dépendances principales

- **streamlit**: Interface web
- **mistralai**: Client API Mistral AI
- **paddleocr**: Détection de layout et tableaux
- **opencv-python**: Traitement d'images
- **numpy**: Calculs numériques
- **python-dotenv**: Gestion des variables d'environnement

## Modèles utilisés

L'application utilise deux modèles Mistral AI :
- **mistral-ocr-latest**: OCR dédié, rapide et structuré
- **Pixtral-12B** (`pixtral-12b-2409`): Modèle multimodal avec contrôle via prompt

## Limitations

- Les PDFs très volumineux peuvent prendre du temps à convertir
- La qualité de l'extraction dépend de la qualité du document source
- Nécessite une connexion internet pour l'API Mistral

## Dépannage

### Erreur lors de l'installation de PaddleOCR

Si l'installation de PaddleOCR échoue, installez les dépendances système :

**macOS:**
```bash
# Aucune dépendance supplémentaire normalement requise
```

**Ubuntu/Debian:**
```bash
sudo apt-get install libglib2.0-0 libsm6 libxext6 libxrender-dev
```

**Windows:**
Suivez les instructions sur [PaddleOCR GitHub](https://github.com/PaddlePaddle/PaddleOCR)

### Erreur d'API

Vérifiez que:
- Votre clé API est correcte dans le fichier `.env`
- Vous avez des crédits disponibles sur votre compte Mistral AI
- Votre connexion internet fonctionne

## Déploiement sur Render

### Configuration requise

L'application nécessite un environnement Linux pour fonctionner avec PaddleOCR (incompatible avec Apple Silicon/ARM).

### Étapes de déploiement

1. **Créez un compte sur [Render](https://render.com)**

2. **Créez un nouveau Web Service**
   - Connectez votre repository GitHub
   - Ou uploadez les fichiers du projet

3. **Configuration du service**
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `streamlit run app.py`
   - **Environment**: Python 3.12

4. **Variables d'environnement**

   Ajoutez dans l'onglet "Environment" de Render :
   ```
   MISTRAL_API_KEY=votre_clé_api_mistral
   DISABLE_MODEL_SOURCE_CHECK=True
   ```

5. **Déployez !**

   Render va automatiquement :
   - Installer les dépendances système (via `packages.txt`)
   - Installer Python 3.12 (via `runtime.txt`)
   - Installer les packages Python (via `requirements.txt`)
   - Télécharger les modèles PaddleOCR au premier lancement (~10min)
   - Lancer l'application

### Notes importantes

- **Premier démarrage** : Peut prendre 10-15 minutes pour télécharger tous les modèles PaddleOCR
- **Modèles en cache** : Les modèles sont sauvegardés et réutilisés aux redémarrages suivants
- **Plan gratuit** :
  - ⚠️ **Limitation importante** : Le plan gratuit (512MB RAM) peut être insuffisant pour PaddleOCR
  - L'application fonctionnera en mode standard (sans détection automatique de tableaux)
  - Si la détection de tableaux est activée, l'app basculera automatiquement en mode standard si PaddleOCR échoue
  - Suffisant pour OCR standard, mais peut mettre l'app en veille après inactivité
- **Plan payant** :
  - Recommandé pour utiliser la détection automatique de tableaux (nécessite 2GB+ RAM)
  - Starter plan ($7/mois) ou supérieur recommandé pour utilisation en production

### Fichiers de déploiement

- `packages.txt` : Dépendances système Linux
- `runtime.txt` : Version Python
- `.streamlit/config.toml` : Configuration Streamlit pour Render

## Support

Pour toute question ou problème, ouvrez une issue sur le dépôt du projet.
