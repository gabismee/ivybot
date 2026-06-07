import discord, asyncio, random
from discord import app_commands
from discord.ext import commands
from data.quiz_questions import QUESTIONS
from utils.db import add_xp, get_quiz_record, salvar_quiz_record
from utils.embeds import CORES, embed_erro, FOOTER

class Quiz(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sessions = {}

    quiz = app_commands.Group(name='quiz', description='🎲 Quiz literário')

    async def _iniciar_quiz(self, guild, channel, autor, perguntas:int=10):
        key = (guild.id, channel.id)
        if key in self.sessions:
            return await channel.send(embed=embed_erro('Já tem quiz rolando aqui. Use `/quiz finalizar` ou `!quiz finalizar`.'))

        record = get_quiz_record(guild.id, channel.id)
        await channel.send(f'🎲 Quiz iniciado! Recorde do canal: **{record} ponto(s)**')
        qs = random.sample(QUESTIONS, min(max(1, perguntas), len(QUESTIONS)))
        self.sessions[key] = {'active': True, 'scores': {}, 'total': len(qs), 'no_answer_streak': 0}

        for idx, q in enumerate(qs, 1):
            sess = self.sessions.get(key)
            if not sess or not sess.get('active'):
                break

            opts = list(enumerate(q['o']))
            random.shuffle(opts)
            correta = [i for i, (orig, _) in enumerate(opts) if orig == q['a']][0]
            letras = 'ABCD'
            desc = '\n'.join(f'**{letras[i]})** {txt}' for i, (_, txt) in enumerate(opts))
            e = discord.Embed(
                title=f'📚 Pergunta {idx}/{len(qs)}',
                description=f"{q['p']}\n\n{desc}\n\n⏳ 45 segundos para responder com A, B, C ou D.",
                color=CORES['azul']
            )
            e.set_footer(text=FOOTER)
            await channel.send(embed=e)

            acertou_user = None
            respondeu_alguem = False

            def check(m):
                return (
                    m.channel.id == channel.id
                    and m.content.strip().upper() in list(letras[:len(opts)])
                    and not m.author.bot
                    and self.sessions.get(key, {}).get('active')
                )

            fim = asyncio.get_event_loop().time() + 45
            while asyncio.get_event_loop().time() < fim and self.sessions.get(key, {}).get('active'):
                try:
                    m = await self.bot.wait_for('message', timeout=max(0.1, fim - asyncio.get_event_loop().time()), check=check)
                except asyncio.TimeoutError:
                    break

                respondeu_alguem = True
                escolha = letras.index(m.content.strip().upper())
                if escolha == correta:
                    acertou_user = m.author
                    self.sessions[key]['scores'][m.author.id] = self.sessions[key]['scores'].get(m.author.id, 0) + 1
                    add_xp(m.author.id, m.author.display_name, 20)
                    try:
                        await m.add_reaction('✅')
                    except Exception:
                        pass
                    await channel.send(f'✅ {m.author.mention} acertou! Resposta: **{letras[correta]}**. Indo para a próxima pergunta...')
                    break
                else:
                    try:
                        await m.add_reaction('❌')
                    except Exception:
                        pass

            if not self.sessions.get(key, {}).get('active'):
                break

            if acertou_user:
                self.sessions[key]['no_answer_streak'] = 0
            elif not respondeu_alguem:
                self.sessions[key]['no_answer_streak'] += 1
                await channel.send(f'⏰ Tempo esgotado! Ninguém respondeu. Resposta: **{letras[correta]}**')
            else:
                self.sessions[key]['no_answer_streak'] = 0
                await channel.send(f'⏰ Tempo esgotado! Ninguém acertou. Resposta: **{letras[correta]}**')

            await channel.send(self._ranking_text(key, parcial=True))

            if self.sessions.get(key, {}).get('no_answer_streak', 0) >= 2:
                await channel.send('🛑 O quiz ficou **2 perguntas seguidas sem ninguém responder**, então finalizei automaticamente.')
                break

            await asyncio.sleep(1.2)

        scores = self.sessions.get(key, {}).get('scores', {})
        total = max(scores.values()) if scores else 0
        novo = salvar_quiz_record(guild.id, channel.id, total)
        if scores:
            vencedor = max(scores, key=scores.get)
            user = guild.get_member(vencedor)
            add_xp(vencedor, user.display_name if user else str(vencedor), 100)
        await channel.send(self._ranking_text(key, parcial=False) + ('\n🏆 **NOVO RECORDE DO CANAL!**' if novo else ''))
        self.sessions.pop(key, None)

    def _ranking_text(self, key, parcial=True):
        scores = self.sessions.get(key, {}).get('scores', {})
        if not scores:
            return '🏆 Ranking parcial: ninguém pontuou ainda.'
        linhas = []
        guild = self.bot.get_guild(key[0])
        for i, (uid, pts) in enumerate(sorted(scores.items(), key=lambda x: x[1], reverse=True)[:10], 1):
            m = guild.get_member(uid) if guild else None
            nome = m.mention if m else f'<@{uid}>'
            linhas.append(f'**{i}.** {nome} — **{pts}** ponto(s)')
        return ('🏆 **Ranking parcial**\n' if parcial else '🏁 **Ranking final**\n') + '\n'.join(linhas)

    @quiz.command(name='iniciar', description='Inicia quiz no canal')
    async def iniciar(self, interaction: discord.Interaction, perguntas: int = 10):
        if (interaction.guild_id, interaction.channel_id) in self.sessions:
            return await interaction.response.send_message('Já tem quiz rolando aqui. Use `/quiz finalizar`.', ephemeral=True)
        await interaction.response.send_message('Preparando quiz...')
        await self._iniciar_quiz(interaction.guild, interaction.channel, interaction.user, perguntas)

    @quiz.command(name='finalizar', description='Finaliza o quiz do canal')
    async def finalizar(self, interaction):
        key = (interaction.guild_id, interaction.channel_id)
        if key not in self.sessions:
            return await interaction.response.send_message('Não tem quiz ativo aqui.', ephemeral=True)
        self.sessions[key]['active'] = False
        await interaction.response.send_message('🛑 Quiz finalizado. Vou parar após a pergunta atual.')

    @commands.group(name='quiz', invoke_without_command=True)
    async def quiz_prefix(self, ctx, subcomando: str = None, perguntas: int = 10):
        if subcomando in (None, 'iniciar', 'start'):
            await self._iniciar_quiz(ctx.guild, ctx.channel, ctx.author, perguntas)
        elif subcomando in ('finalizar', 'parar', 'stop'):
            await self.quiz_finalizar_prefix(ctx)
        else:
            await ctx.send(embed=embed_erro('Use: `!quiz iniciar [perguntas]` ou `!quiz finalizar`'))

    @quiz_prefix.command(name='iniciar')
    async def quiz_iniciar_prefix(self, ctx, perguntas: int = 10):
        await self._iniciar_quiz(ctx.guild, ctx.channel, ctx.author, perguntas)

    @quiz_prefix.command(name='finalizar', aliases=['parar', 'stop'])
    async def quiz_finalizar_prefix(self, ctx):
        key = (ctx.guild.id, ctx.channel.id)
        if key not in self.sessions:
            return await ctx.send('Não tem quiz ativo aqui.')
        self.sessions[key]['active'] = False
        await ctx.send('🛑 Quiz finalizado. Vou parar após a pergunta atual.')

async def setup(bot):
    await bot.add_cog(Quiz(bot))
