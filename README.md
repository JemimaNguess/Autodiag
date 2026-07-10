# AutoDiag Sonore — Application web

Application de diagnostic sonore du moteur en 3 écrans :
1. **Enregistrement** — gros bouton pour capturer 10 à 15 s de son moteur
2. **Analyse** — écran de chargement pendant que l'IA traite l'enregistrement
3. **Résultat** — diagnostic (sain / anomalie), score de confiance, et recommandation en bas d'écran

## Installation

```bash
pip install -r requirements.txt
```

Il faut aussi **ffmpeg** installé sur la machine (pour convertir l'audio du navigateur en WAV) :
- Mac : `brew install ffmpeg`
- Windows : télécharger sur https://ffmpeg.org/download.html et l'ajouter au PATH
- Linux : `sudo apt install ffmpeg`

## Lancement

```bash
python app.py
```

Le serveur démarre sur `http://localhost:5000`.

## Tester depuis un téléphone (recommandé pour la démo)

1. Connecte ton téléphone au **même réseau Wi-Fi** que l'ordinateur qui fait tourner le serveur
2. Trouve l'adresse IP locale de l'ordinateur :
   - Mac/Linux : `ifconfig` ou `ip a`
   - Windows : `ipconfig`
3. Sur le téléphone, ouvre le navigateur et va sur `http://<IP-de-l-ordinateur>:5000`

⚠️ **Important** : la plupart des navigateurs mobiles exigent une connexion **HTTPS** pour autoriser l'accès au micro, sauf en `localhost`. Si le micro ne fonctionne pas depuis le téléphone, deux solutions rapides :
- Utiliser un tunnel HTTPS gratuit comme [ngrok](https://ngrok.com/) : `ngrok http 5000`, puis ouvrir l'URL `https://...` fournie sur le téléphone
- Faire la démo directement depuis l'ordinateur (webcam/micro de l'ordinateur), projeté à l'écran pour le jury

## Structure du projet

```
webapp/
├── app.py                  # Serveur Flask + API /api/diagnose
├── audio_features.py       # Extraction de features (identique à l'entraînement)
├── models/
│   ├── autodiag_sonore_model.joblib
│   └── autodiag_sonore_labels.joblib
├── templates/
│   └── index.html          # Les 3 écrans
└── static/
    ├── css/style.css
    └── js/app.js            # Enregistrement micro + appel API
```

## Remplacer le modèle

Si tu ré-entraînes le modèle avec `train_autodiag.py`, remplace simplement les
deux fichiers dans `models/` par les nouveaux `.joblib` générés — l'application
les charge automatiquement au démarrage.
