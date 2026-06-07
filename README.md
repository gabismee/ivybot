# 📚 BookBot — Bot de Livros para Discord

Bot completo de livros para Discord, 100% gratuito.

---

## ✅ Funcionalidades

| Módulo | Comandos |
|--------|----------|
| 🔍 **Busca** | `/buscar`, `/livro` |
| ❤️ **Wishlist** | `/desejo adicionar/remover/listar/ver` |
| 🔔 **Alertas** | `/alerta`, `/meus-alertas` |
| 📚 **Estante** | `/estante adicionar/ver/stats`, `/avaliar` |
| 🤖 **Recomendações** | `/recomendar`, `/similar`, `/encontrar` |
| 📖 **Clube** | `/clube criar/status/progresso/ranking/votar` |
| 🏆 **Rankings** | `/ranking`, `/top-promocoes` |
| 🔥 **Promoções** | `/promocoes`, `/gratuitos` |
| 👤 **Perfil** | `/configurar`, `/perfil` |
| ⚙️ **Admin** | `/config canal-promocoes/canal-clube/ver` |
| ❓ **Ajuda** | `/ajuda` |

---

## 🚀 Como Configurar (Passo a Passo)

### 1. Criar o Bot no Discord

1. Acesse https://discord.com/developers/applications
2. Clique em **"New Application"** → dê um nome (ex: BookBot)
3. Vá em **"Bot"** → clique **"Add Bot"**
4. Clique em **"Reset Token"** e copie o token
5. Ative as seguintes **Privileged Gateway Intents**:
   - ✅ Server Members Intent
   - ✅ Message Content Intent
6. Vá em **"OAuth2" → "URL Generator"**:
   - Scopes: `bot`, `applications.commands`
   - Permissões: `Send Messages`, `Embed Links`, `Read Message History`
7. Copie o link gerado e adicione o bot ao seu servidor

### 2. Instalar as dependências

```bash
# Precisa de Python 3.11+
python --version

# Instalar dependências
pip install -r requirements.txt
```

### 3. Configurar o Token

Abra `bot.py` e troque `SEU_TOKEN_AQUI` pelo seu token:

```python
TOKEN = "seu_token_aqui"
```

Ou use variável de ambiente (mais seguro):

```bash
# Linux/Mac
export DISCORD_TOKEN="seu_token_aqui"

# Windows
set DISCORD_TOKEN=seu_token_aqui
```

### 4. Iniciar o Bot

```bash
# Primeiro: inicializa o banco de dados
python setup.py

# Depois: inicia o bot
python bot.py
```

---

## 🆓 Hospedagem Gratuita

### Opção 1: Render.com (recomendado)
1. Crie conta em https://render.com
2. Novo serviço → **Background Worker**
3. Conecte seu repositório GitHub
4. Build Command: `pip install -r requirements.txt`
5. Start Command: `python setup.py && python bot.py`
6. Adicione variável de ambiente: `DISCORD_TOKEN=seu_token`

### Opção 2: Railway.app
1. Crie conta em https://railway.app
2. Novo projeto → Deploy from GitHub
3. Adicione variável: `DISCORD_TOKEN=seu_token`
4. Deploy automático

### Opção 3: Rodar no seu PC
Só deixar o terminal aberto com `python bot.py` rodando.

---

## ⚙️ Configuração no Servidor

Após o bot entrar, configure os canais com comandos admin:

```
/config canal-promocoes #promoções-livros
/config canal-clube     #clube-do-livro
/config canal-ebooks    #ebooks-grátis
```

---

## 📁 Estrutura do Projeto

```
bookbot/
├── bot.py              ← Arquivo principal
├── setup.py            ← Inicializa banco de dados
├── requirements.txt    ← Dependências
├── data/
│   └── bookbot.db      ← Banco SQLite (criado automaticamente)
├── utils/
│   ├── db.py           ← Banco de dados
│   ├── api.py          ← Google Books API + links de lojas
│   └── embeds.py       ← Embeds do Discord
└── cogs/
    ├── busca.py        ← Pesquisa de livros
    ├── wishlist.py     ← Lista de desejos
    ├── alertas.py      ← Alertas de preço
    ├── biblioteca.py   ← Estante pessoal
    ├── clube.py        ← Clube do livro
    ├── ranking.py      ← Rankings
    ├── onboarding.py   ← Configuração de perfil
    ├── ia.py           ← Recomendações
    ├── promocoes.py    ← Promoções automáticas
    └── admin.py        ← Configurações do servidor
```

---

## 🛍️ Lojas Confiáveis Suportadas

- 🛒 Amazon Brasil
- 📚 Livraria Cultura
- 📖 Estante Virtual
- 🏬 Saraiva
- 🟡 Mercado Livre
- 📱 Google Play Livros

---

## 📌 Requisitos

- Python 3.11+
- Conexão com internet
- Conta no Discord Developer Portal (gratuito)

## Painéis e embeds personalizados

### Criar embed personalizado
Use pelo slash command:

```txt
/embed criar
```

Ou por prefixo:

```txt
!embed criar #canal | Título | Descrição | #D8B4FE | imagem_url | thumbnail_url | footer
```

Campos opcionais podem ficar vazios. Exemplo:

```txt
!embed criar #comandos | 📖 Central de Comandos | Use !ajuda para ver todos os comandos da Ivy. | #D8B4FE
```

### Criar painel de cargos
Use:

```txt
/painel cargos
```

Ou:

```txt
!painel cargos #cargos | 🌷 Escolha seus cargos! | Clique nos botões abaixo para receber ou remover cargos do seu perfil. | #D8B4FE | imagem_url
```

O painel mostra todos os cargos disponíveis e cria botões. Quando a pessoa clica, o cargo é adicionado ao perfil dela. Clicando de novo, o cargo é removido.

Importante: o cargo da Ivy precisa estar acima dos cargos que ela vai entregar e o bot precisa da permissão **Gerenciar cargos**.
