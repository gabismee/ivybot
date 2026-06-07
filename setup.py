"""
Script de inicialização — rode uma vez antes de iniciar o bot
para criar o banco de dados.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from utils.db import init_db

if __name__ == "__main__":
    init_db()
    print("✅ Pronto! Agora rode: python bot.py")
