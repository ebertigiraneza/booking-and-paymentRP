# Étape 1 - Builder pour optimiser l'image
FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Étape 2 - Image finale
FROM python:3.11-slim

WORKDIR /app

# Copie les dépendances installées depuis le builder
COPY --from=builder /root/.local /root/.local
COPY . .

# Garantit que les scripts sont exécutables
RUN chmod +x run_all.py

# Exposition des ports (principal + microservices)
EXPOSE 8000 8001 8002 8003 8004

# Commande pour lancer TOUS les services
CMD ["python", "run_all.py"]