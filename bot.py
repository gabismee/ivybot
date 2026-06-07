import discord
from discord.ext import commands
import os
import logging
from keep_alive import keep_alive
from utils.db import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger("Ivy")

TOKEN = os.getenv("DISCORD_TOKEN", "SEU_TOKEN_AQUI")
PREFIX = "!"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.dm_messages = True

class BookBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=PREFIX,
            intents=intents,
            help_command=None,
            description="📚 Ivy — bot gratuito de livros para Discord"
        )

    async def setup_hook(self):
        # Inicializa banco de dados
        try:
            init_db()
            log.info("✅ Banco de dados inicializado com sucesso")
        except Exception as e:
            log.error(f"❌ Erro ao inicializar banco: {e}")
            raise  # para o bot se o banco não funcionar

        # Carrega todos os cogs
        cogs = [
            "cogs.busca",
            "cogs.wishlist",
            "cogs.alertas",
            "cogs.biblioteca",
            "cogs.clube",
            "cogs.ranking",
            "cogs.onboarding",
            "cogs.ia",
            "cogs.promocoes",
            "cogs.quiz",
            "cogs.social",
            "cogs.desafios",
            "cogs.literario",
            "cogs.admin",
            "cogs.welcome",
            "cogs.roleplay",
            "cogs.lembretes",
        ]
        for cog in cogs:
            try:
                await self.load_extension(cog)
                log.info(f"✅ Cog carregado: {cog}")
            except Exception as e:
                log.error(f"❌ Erro ao carregar {cog}: {e}")

        synced = await self.tree.sync()
        log.info(f"🔄 {len(synced)} slash commands sincronizados")

    async def on_ready(self):
        log.info(f"✅ Bot online como {self.user} (ID: {self.user.id})")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="📚 Ivy — /ajuda"
            )
        )

    async def on_member_join(self, member: discord.Member):
        welcome_cog = self.get_cog("Welcome")
        if welcome_cog:
            await welcome_cog.send_welcome(member)
        onboarding_cog = self.get_cog("Onboarding")
        if onboarding_cog:
            await onboarding_cog.iniciar_onboarding(member)

bot = BookBot()

if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
