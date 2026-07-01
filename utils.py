import time
import random
import requests
from stem import Signal
from stem.control import Controller

# Configuration correspondant à votre docker-compose
TOR_NODES = [
    {"socks_port": 9050, "ctrl_port": 9051, "password": "mypass"},
    {"socks_port": 9052, "ctrl_port": 9053, "password": "mypass"},
    {"socks_port": 9054, "ctrl_port": 9055, "password": "mypass"},
]

def renew_tor_ip(ctrl_port: int, password: str):
    """
    Se connecte au port de contrôle Tor pour demander une nouvelle identité (nouvelle IP).
    """
    try:
        with Controller.from_port(port=ctrl_port) as controller:
            controller.authenticate(password=password)
            controller.signal(Signal.NEWNYM)
            print(f"🔄 Nouvelle IP demandée sur le port de contrôle {ctrl_port}")
            time.sleep(5)  # Laisser le temps à Tor de construire un nouveau circuit
    except Exception as e:
        print(f"⚠️ Erreur lors du renouvellement de l'IP (port {ctrl_port}) : {e}")

def get_tor_session(node: dict) -> requests.Session:
    """
    Retourne une session requests routée via un nœud Tor spécifique.
    """
    session = requests.Session()
    # Utilisation de socks5h pour que la résolution DNS se fasse aussi par Tor
    proxy_url = f"socks5h://127.0.0.1:{node['socks_port']}"
    
    session.proxies = {
        'http': proxy_url,
        'https': proxy_url
    }
    
    # Reprendre les headers de votre fichier consult.py
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*"
    })
    return session