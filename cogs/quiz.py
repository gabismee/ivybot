import discord, json, random, asyncio, os
from discord import app_commands
from discord.ext import commands
from utils.db import add_xp, atualizar_quiz_score, get_quiz_ranking
from utils.embeds import FOOTER

QUEST_PATH=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'quiz_literatura.json')

class QuizView(discord.ui.View):
    def __init__(self, correct):
        super().__init__(timeout=45); self.correct=correct; self.answers={}
        for l in 'ABCD':
            b=discord.ui.Button(label=l, style=discord.ButtonStyle.secondary)
            b.callback=self._make(l); self.add_item(b)
    def _make(self, letter):
        async def cb(interaction):
            if interaction.user.id in self.answers:
                return await interaction.response.send_message('Você já respondeu essa pergunta.', ephemeral=True)
            ok=letter==self.correct; self.answers[interaction.user.id]=ok
            try: await interaction.message.add_reaction('✅' if ok else '❌')
            except Exception: pass
            await interaction.response.send_message('✅ Acertou!' if ok else f'❌ Errou! Resposta certa: {self.correct}', ephemeral=True)
        return cb

class Quiz(commands.Cog):
    def __init__(self, bot): self.bot=bot
    def _load(self):
        with open(QUEST_PATH,encoding='utf-8') as f: return json.load(f)

    quiz=app_commands.Group(name='quiz', description='🎲 Quiz literário')

    @quiz.command(name='iniciar', description='Inicia um quiz com perguntas embaralhadas')
    async def iniciar(self, interaction, quantidade:int=10):
        quantidade=max(1,min(20,quantidade)); perguntas=random.sample(self._load(), quantidade)
        await interaction.response.send_message(f'🎲 Quiz iniciado com **{quantidade}** perguntas! Cada uma vale 20 XP e tem 45s.')
        scores={}
        for i,q in enumerate(perguntas,1):
            pares=list(zip('ABCD',q['opcoes'])); random.shuffle(pares)
            correct=next(l for l,opt in pares if opt==q['opcoes']['ABCD'.index(q['resposta'])])
            desc='\n'.join([f'**{l})** {opt}' for l,opt in pares])
            e=discord.Embed(title=f'📚 Pergunta {i}/{quantidade}', description=f"**{q['pergunta']}**\n\n{desc}\n\n⏳ 45 segundos", color=discord.Color.purple())
            e.set_footer(text=FOOTER)
            view=QuizView(correct)
            msg=await interaction.channel.send(embed=e, view=view)
            await asyncio.sleep(45)
            for child in view.children: child.disabled=True
            try: await msg.edit(view=view)
            except Exception: pass
            acertadores=[uid for uid,ok in view.answers.items() if ok]
            if acertadores:
                for uid in acertadores:
                    scores[uid]=scores.get(uid,0)+1
                    member=interaction.guild.get_member(uid)
                    add_xp(uid, member.display_name if member else str(uid), 20)
                    atualizar_quiz_score(interaction.guild_id, uid, 1, 1, False)
                await interaction.channel.send('✅ Pontuaram: ' + ', '.join(f'<@{u}>' for u in acertadores))
            else:
                await interaction.channel.send(f'⏰ Tempo esgotado! Ninguém pontuou. Resposta: **{correct}**')
        if scores:
            winner=max(scores, key=scores.get); add_xp(winner, interaction.guild.get_member(winner).display_name if interaction.guild.get_member(winner) else str(winner), 100)
            for uid,p in scores.items(): atualizar_quiz_score(interaction.guild_id, uid, 0, 0, True)
            ranking='\n'.join([f'**{i}.** <@{uid}> — {p} ponto(s)' for i,(uid,p) in enumerate(sorted(scores.items(), key=lambda x:x[1], reverse=True),1)])
            await interaction.channel.send(embed=discord.Embed(title='🏆 Ranking do Quiz', description=ranking+f'\n\n👑 Vencedor: <@{winner}> (+100 XP)', color=discord.Color.gold()))
        else:
            await interaction.channel.send('Ninguém pontuou no quiz inteiro. Triste, mas acontece kkk')

    @quiz.command(name='ranking', description='Ranking geral do quiz')
    async def ranking(self, interaction):
        rows=get_quiz_ranking(interaction.guild_id,10)
        e=discord.Embed(title='🏆 Ranking geral do Quiz', color=discord.Color.gold())
        if not rows: e.description='Ainda não há pontuações.'
        for i,r in enumerate(rows,1): e.add_field(name=f'{i}. <@{r["user_id"]}>', value=f"{r['pontos']} pontos • {r['acertos']} acertos", inline=False)
        e.set_footer(text=FOOTER); await interaction.response.send_message(embed=e)
async def setup(bot): await bot.add_cog(Quiz(bot))
