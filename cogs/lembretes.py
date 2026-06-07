import re
from datetime import datetime, timedelta
import discord
from discord import app_commands
from discord.ext import commands, tasks
from utils.db import criar_lembrete, lembretes_pendentes, concluir_lembrete
from utils.embeds import CORES, embed_sucesso, embed_erro, FOOTER

TIME_RE = re.compile(r'^(\d+)(m|min|h|hora|horas|d|dia|dias)$', re.I)

def parse_tempo(s: str):
    m = TIME_RE.match((s or '').strip())
    if not m: return None
    n = int(m.group(1)); unit = m.group(2).lower()
    if unit in ('m','min'): return timedelta(minutes=n)
    if unit in ('h','hora','horas'): return timedelta(hours=n)
    if unit in ('d','dia','dias'): return timedelta(days=n)
    return None

class Lembretes(commands.Cog):
    def __init__(self, bot):
        self.bot=bot
        self.checar_lembretes.start()
    def cog_unload(self): self.checar_lembretes.cancel()

    @tasks.loop(minutes=1)
    async def checar_lembretes(self):
        await self.bot.wait_until_ready()
        for row in lembretes_pendentes():
            user = self.bot.get_user(row['user_id']) or await self.bot.fetch_user(row['user_id'])
            e=discord.Embed(title='⏰ Lembrete da Ivy', description=row['mensagem'], color=CORES['roxo'])
            e.set_footer(text=FOOTER)
            try: await user.send(embed=e)
            except Exception: pass
            concluir_lembrete(row['id'])

    async def _add(self, destino, user, tempo, mensagem):
        delta=parse_tempo(tempo)
        if not delta: 
            msg=embed_erro('Use tempo tipo `20m`, `2h` ou `1d`. Ex: `!lembrar 20m ler 10 páginas`')
            return await (destino.response.send_message(embed=msg, ephemeral=True) if hasattr(destino,'response') else destino.send(embed=msg))
        quando=datetime.utcnow()+delta
        criar_lembrete(user.id, mensagem[:500], quando)
        msg=embed_sucesso(f'Vou te lembrar em **{tempo}**: {mensagem[:180]}')
        return await (destino.response.send_message(embed=msg, ephemeral=True) if hasattr(destino,'response') else destino.send(embed=msg))

    @app_commands.command(name='lembrar', description='⏰ Cria um lembrete. Ex: 20m ler 10 páginas')
    async def lembrar(self, interaction, tempo: str, mensagem: str):
        await self._add(interaction, interaction.user, tempo, mensagem)

    @commands.command(name='lembrar', aliases=['lembrete'])
    async def lembrar_p(self, ctx, tempo: str=None, *, mensagem: str=''):
        if not tempo or not mensagem: return await ctx.send(embed=embed_erro('Use: `!lembrar 20m ler 10 páginas`'))
        await self._add(ctx, ctx.author, tempo, mensagem)

async def setup(bot): await bot.add_cog(Lembretes(bot))
