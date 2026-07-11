"""
AutoDiag Sonore — Serveur web
Sert l'interface (3 écrans : enregistrement / analyse / résultat) et expose
une API /api/diagnose qui reçoit un enregistrement audio et renvoie le
diagnostic du moteur.

Lancement local :
    pip install -r requirements.txt
    python app.py

Déploiement (Render, Docker) :
    Le port est fourni par la variable d'environnement PORT.
    ffmpeg doit être installé sur le système (voir Dockerfile).
"""

import os
import subprocess
import tempfile
import uuid

import joblib
import numpy as np
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from audio_features import extract_features

app = Flask(__name__)
CORS(app, origins = ["https:/autodiag2.vercel.app"])

MODEL_PATH = os.path.join("models", "autodiag_sonore_model.joblib")
LABELS_PATH = os.path.join("models", "autodiag_sonore_labels.joblib")

model = joblib.load(MODEL_PATH)
label_encoder = joblib.load(LABELS_PATH)

# En local sur Windows, tu peux définir la variable d'environnement FFMPEG_PATH
# si "ffmpeg" n'est pas dans le PATH système. En production (Docker/Render),
# ffmpeg est installé au niveau système et accessible directement par son nom.
FFMPEG_PATH = os.environ.get("FFMPEG_PATH", "ffmpeg")

# Recommandation affichée en bas de l'écran de résultat, selon le diagnostic.
RECOMMENDATIONS = {
    "sain": {
        "titre": "Moteur en bon état",
        "message": (
            "Aucune anomalie détectée dans le son du moteur. "
            "Continuez l'entretien régulier (vidange, filtre à air) "
            "pour le maintenir dans cet état."
        ),
    },
    "anomalie": {
        "titre": "Anomalie détectée",
        "message": (
            "Le son du moteur présente des caractéristiques inhabituelles. "
            "Faites vérifier le véhicule par un mécanicien avant votre "
            "prochain trajet pour éviter une panne coûteuse."
        ),
    },
}


def convert_to_wav(input_path, output_path):
    """
    Convertit n'importe quel format audio envoyé par le téléphone
    (webm/opus, ogg, m4a...) en WAV mono 16 kHz, le format utilisé
    à l'entraînement du modèle.
    """
    subprocess.run(
        [
            FFMPEG_PATH, "-y", "-i", input_path,
            "-ac", "1",           # mono
            "-ar", "16000",       # 16 kHz, identique au dataset d'entraînement
            output_path,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/diagnose", methods=["POST"])
def diagnose():
    if "audio" not in request.files:
        return jsonify({"error": "Aucun fichier audio reçu."}), 400

    audio_file = request.files["audio"]
    session_id = uuid.uuid4().hex

    with tempfile.TemporaryDirectory() as tmp_dir:
        input_path = os.path.join(tmp_dir, f"{session_id}_input")
        wav_path = os.path.join(tmp_dir, f"{session_id}.wav")
        audio_file.save(input_path)

        try:
            convert_to_wav(input_path, wav_path)
        except subprocess.CalledProcessError:
            return jsonify({
                "error": "Impossible de lire l'enregistrement audio. Réessayez."
            }), 400
        except FileNotFoundError:
            return jsonify({
                "error": "ffmpeg est introuvable sur le serveur."
            }), 500

        try:
            features = extract_features(wav_path).reshape(1, -1)
        except Exception as e:
            return jsonify({"error": f"Erreur d'analyse audio : {e}"}), 500

    probabilities = model.predict_proba(features)[0]
    predicted_idx = int(np.argmax(probabilities))
    predicted_label = label_encoder.inverse_transform([predicted_idx])[0]
    confidence = float(probabilities[predicted_idx])

    all_scores = {
        label_encoder.inverse_transform([i])[0]: float(p)
        for i, p in enumerate(probabilities)
    }

    recommendation = RECOMMENDATIONS.get(predicted_label, {
        "titre": predicted_label,
        "message": "Résultat obtenu, mais aucune recommandation n'est définie pour cette classe.",
    })

    return jsonify({
        "diagnostic": predicted_label,
        "confiance": confidence,
        "scores": all_scores,
        "recommandation": recommendation,
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)