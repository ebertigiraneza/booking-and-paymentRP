# run_all.py

import uvicorn
from multiprocessing import Process
import time

def run_app(app: str, port: int):
    uvicorn.run(app, host="0.0.0.0", port=port, workers=1)

if __name__ == "__main__":
    # Service principal (doit être sur le port Render par défaut)
    Process(target=run_app, args=("main:app", 8000)).start()
    
    # Microservices (ports internes)
    Process(target=run_app, args=("wallet.main:app", 8001)).start()
    Process(target=run_app, args=("authentification.main:app", 8002)).start()
    Process(target=run_app, args=("booking.main:app", 8003)).start()
    Process(target=run_app, args=("payment.main:app", 8004)).start()

    # Garder le processus principal actif
    while True:
        time.sleep(3600)  # 1 heure    