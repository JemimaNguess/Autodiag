FROM python:3.11-slim

# ffmpeg est nécessaire pour convertir l'audio envoyé par l'app (webm/m4a -> wav)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render fournit la variable d'environnement PORT au démarrage du conteneur
ENV PORT=5000
EXPOSE 5000

CMD ["python", "app.py"]
