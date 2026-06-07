import discord, random, aiohttp
from discord import app_commands
from discord.ext import commands
from data.literary_data import frase_aleatoria, poesia_aleatoria, GENEROS, PERSONAGENS, TOP50
from utils.api import buscar_livros
from utils.embeds import CORES, embed_erro, FOOTER
from utils.autor_info import buscar_autor, buscar_personagem

# ─── Animais disponíveis ──────────────────────────────────────────────────────
# APIs gratuitas, sem chave:
# 🐱 Gato   → thecatapi.com
# 🐶 Cachorro → dog.ceo
# 🦊 Raposa → randomfox.ca
# 🦆 Pato   → random-d.uk
# 🐼 Panda  → some-random-api.com
# 🦁 Foto aleatória de animal → Unsplash (fallback estático)
ANIMAIS_DISPONIVEIS = ['gato', 'cachorro', 'raposa', 'pato', 'panda']
ANIMAL_EMOJIS = {
    'gato': '🐱', 'cachorro': '🐶', 'raposa': '🦊',
    'pato': '🦆', 'panda': '🐼',
}
ANIMAL_FALLBACKS = {
    'gato':    'https://upload.wikimedia.org/wikipedia/commons/thumb/4/4d/Cat_November_2010-1a.jpg/1200px-Cat_November_2010-1a.jpg',
    'cachorro':'https://upload.wikimedia.org/wikipedia/commons/thumb/2/26/YellowLabradorLooking_new.jpg/1200px-YellowLabradorLooking_new.jpg',
    'raposa':  'https://upload.wikimedia.org/wikipedia/commons/thumb/0/03/Vulpes_vulpes_laying_in_snow.jpg/1200px-Vulpes_vulpes_laying_in_snow.jpg',
    'pato':    'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a1/Mallard2.jpg/1200px-Mallard2.jpg',
    'panda':   'https://upload.wikimedia.org/wikipedia/commons/thumb/0/0f/Grosser_Panda.JPG/1200px-Grosser_Panda.JPG',
}

# ─── Views ───────────────────────────────────────────────────────────────────

class TopLivrosView(discord.ui.View):
    def __init__(self, paginas):
        super().__init__(timeout=180)
        self.paginas = paginas
        self.idx = 0

    def embed(self):
        ini = self.idx * 10
        linhas = [f'**{ini+i+1}.** {t}' for i, t in enumerate(self.paginas[self.idx])]
        e = discord.Embed(title='📚 Top 50 livros conhecidos/mais lidos', description='\n'.join(linhas), color=CORES['dourado'])
        e.set_footer(text=f'Página {self.idx+1}/{len(self.paginas)} • {FOOTER}')
        return e

    @discord.ui.button(label='◀️ Anterior', style=discord.ButtonStyle.secondary)
    async def anterior(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.idx = (self.idx - 1) % len(self.paginas)
        await interaction.response.edit_message(embed=self.embed(), view=self)

    @discord.ui.button(label='Próxima ▶️', style=discord.ButtonStyle.secondary)
    async def proxima(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.idx = (self.idx + 1) % len(self.paginas)
        await interaction.response.edit_message(embed=self.embed(), view=self)

class HelpView(discord.ui.View):
    CATS = {
        '📚 Livros': [
            '`!livro <título>` / `/livro` — detalhes do livro',
            '`!buscar <termo>` / `/buscar` — busca vários resultados',
            '`!similar <livro>` / `!parecido` — obras parecidas',
            '`!recomendar` / `/recomendar` — recomendações',
            '`!conhecer` / `/conhecer` — livro aleatório',
            '`!promocoes` / `/promocoes` — livros com preço/link',
        ],
        '👤 Perfil e Estante': [
            '`!perfil` / `/perfil` — perfil visual',
            '`!perfil-frase <frase>` — muda frase do perfil',
            '`!perfil-wallpaper <url>` — muda wallpaper',
            '`!estante [status]` / `/estante ver` — sua estante',
            '`!lendo <livro> | <página>` — marca como lendo (página opcional)',
            '`!pagina <número> <livro>` / `/estante pagina` — atualiza página',
            '`!avaliar <1-5> <livro> | comentário` — avalia livro',
            '`!favorito <livro>` / `/favorito` — adiciona aos favoritos',
            '`!abandonado <livro>` — marca como abandonado',
        ],
        '🎲 Jogos e Social': [
            '`!quiz iniciar [n]` / `/quiz iniciar` — inicia quiz',
            '`!quiz finalizar` / `/quiz finalizar` — encerra quiz',
            '`!cookie @user`, `!curtir @user`, `!cartinha @user <msg>`',
            '`!abracar`, `!bater`, `!cafune`, `!cafe`, `!dancar` — roleplay anime',
            '`!ship @u1 @u2`, `!ship-personagem A B`, `!duelo @user`',
        ],
        '🌙 Extras': [
            '`!frase`, `!poesia` — frases/poemas aleatórios',
            '`!genero <nome>` — explica gênero literário',
            '`!autor <nome>` — foto, bio, obras do autor',
            '`!personagem <nome>` — pesquisa personagem',
            '`!toplivros` — top 50 paginado com botões',
            '`!animal` / `/animal` — animal fofo aleatório (gato, cachorro, raposa, pato, panda)',
            '`!gato` / `!cachorro` — foto de animal específico',
        ],
        '⚙️ Admin': [
            '`!boasvindas` — configura boas-vindas',
            '`!painel cargos` — painel de cargos com botões',
            '`!embed criar` — cria embed personalizado (suporta \\n)',
            '`!cor #hex` — cria/aplica cargo de cor',
            '`!setup` — painéis/configuração do servidor',
        ],
    }

    def __init__(self):
        super().__init__(timeout=180)
        for label in self.CATS:
            self.add_item(HelpButton(label))

    @staticmethod
    def make_embed(label):
        e = discord.Embed(title=f'🌷 Ivy — Ajuda | {label}', description='\n'.join(HelpView.CATS[label]), color=CORES['roxo'])
        e.set_footer(text=FOOTER)
        return e

class HelpButton(discord.ui.Button):
    def __init__(self, label):
        super().__init__(label=label, style=discord.ButtonStyle.secondary)
        self.cat_label = label
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=HelpView.make_embed(self.cat_label), view=self.view)

# ─── Cog ─────────────────────────────────────────────────────────────────────

class Literario(commands.Cog):
    def __init__(self, bot): self.bot = bot

    # ── Frase / Poesia ──
    def _frase_embed(self):
        f, obra, autor = frase_aleatoria()
        e = discord.Embed(title='📜 Frase literária', description=f'"{f}"', color=CORES['roxo'])
        e.add_field(name='Obra', value=obra, inline=True)
        e.add_field(name='Autor', value=autor, inline=True)
        e.set_footer(text=FOOTER)
        return e

    @app_commands.command(name='frase', description='📜 Sorteia uma frase literária')
    async def frase(self, interaction): await interaction.response.send_message(embed=self._frase_embed())
    @commands.command(name='frase')
    async def frase_prefix(self, ctx): await ctx.send(embed=self._frase_embed())

    def _poesia_embed(self):
        titulo, autor, txt = poesia_aleatoria()
        e = discord.Embed(title=f'🌙 {titulo}', description=txt, color=CORES['rosa'])
        e.add_field(name='Autor', value=autor)
        e.set_footer(text=FOOTER)
        return e

    @app_commands.command(name='poesia', description='🌙 Sorteia uma poesia/trecho')
    async def poesia(self, interaction): await interaction.response.send_message(embed=self._poesia_embed())
    @commands.command(name='poesia', aliases=['poema'])
    async def poesia_prefix(self, ctx): await ctx.send(embed=self._poesia_embed())

    # ── Gênero ──
    def _genero_embed(self, nome):
        key = nome.lower().strip()
        data = GENEROS.get(key)
        if not data: return None
        e = discord.Embed(title=f'🏷️ {key.title()}', description=data['desc'], color=CORES['azul'])
        e.add_field(name='Autores principais', value='\n'.join(data['autores']), inline=True)
        e.add_field(name='Obras principais',   value='\n'.join(data['obras']),   inline=True)
        e.set_footer(text=FOOTER)
        return e

    @app_commands.command(name='genero', description='🏷️ Explica um gênero literário')
    async def genero(self, interaction, nome: str):
        e = self._genero_embed(nome)
        if not e: return await interaction.response.send_message('Não achei esse gênero. Tente: romance, ficção científica, fantasia, terror, mangá ou mistério.', ephemeral=True)
        await interaction.response.send_message(embed=e)
    @commands.command(name='genero', aliases=['gênero'])
    async def genero_prefix(self, ctx, *, nome: str = None):
        if not nome: return await ctx.send(embed=embed_erro('Use: `!genero <nome>`'))
        e = self._genero_embed(nome)
        if not e: return await ctx.send(embed=embed_erro('Não achei esse gênero.'))
        await ctx.send(embed=e)

    # ── PERSONAGEM ──
    async def _personagem_embed(self, nome):
        # 1. Dicionário local
        p = PERSONAGENS.get(nome.lower().strip())
        if p:
            title, obra, autor, desc = p
            e = discord.Embed(title=f'🔎 {title}', description=desc, color=CORES['verde'])
            e.add_field(name='Obra', value=obra)
            e.add_field(name='Autor', value=autor)
            e.set_footer(text=FOOTER)
            return e

        # 2. Busca automática (Wikipedia + Google Books)
        info = await buscar_personagem(nome)
        if info:
            e = discord.Embed(title=f'🔎 {info["nome"]}', color=CORES['verde'])
            if info.get('obra'):
                e.add_field(name='📖 Obra', value=info['obra'], inline=True)
            if info.get('autor'):
                e.add_field(name='✍️ Autor', value=info['autor'], inline=True)
            if info.get('descricao'):
                e.add_field(name='📝 Descrição', value=info['descricao'][:500], inline=False)
            if info.get('capa_url'):
                e.set_thumbnail(url=info['capa_url'])
            e.set_footer(text=FOOTER)
            return e

        # 3. Fallback: busca livros relacionados
        livros = await buscar_livros(nome, 5, lang='pt')
        if livros:
            e = discord.Embed(title=f'🔎 Pesquisa: {nome}',
                description='Não achei esse personagem cadastrado, mas encontrei obras relacionadas:',
                color=CORES['verde'])
            for l in livros[:4]:
                e.add_field(
                    name=l.get('titulo', 'Sem título')[:70],
                    value=f"✍️ {l.get('autor','Autor desconhecido')}\n📝 {(l.get('sinopse') or 'Sem sinopse')[:140]}...",
                    inline=False)
            e.set_footer(text=FOOTER)
            return e
        return None

    @app_commands.command(name='personagem', description='🔎 Pesquisa um personagem literário/mangá')
    async def personagem(self, interaction, nome: str):
        await interaction.response.defer()
        e = await self._personagem_embed(nome)
        if e: return await interaction.followup.send(embed=e)
        await interaction.followup.send('Não achei esse personagem. Tente o nome completo ou personagem + obra.')

    @commands.command(name='personagem')
    async def personagem_prefix(self, ctx, *, nome: str = None):
        if not nome: return await ctx.send(embed=embed_erro('Use: `!personagem <nome>`'))
        async with ctx.typing():
            e = await self._personagem_embed(nome)
        if e: return await ctx.send(embed=e)
        await ctx.send(embed=embed_erro('Não achei esse personagem. Tente o nome completo ou personagem + obra.'))

    # ── AUTOR ──
    async def _autor_exec(self, destino, nome):
        info = await buscar_autor(nome)
        if info:
            e = discord.Embed(title=f'✍️ {info["nome"]}', color=CORES['laranja'])
            if info.get('nascimento'):
                e.description = f'🗓️ {info["nascimento"]}'
            if info.get('bio'):
                e.add_field(name='📖 Biografia', value=info['bio'][:700], inline=False)
            if info.get('generos'):
                e.add_field(name='🏷️ Gêneros', value=', '.join(info['generos'][:5])[:200], inline=False)
            if info.get('obras'):
                obras_str = '\n'.join(f'• {o}' for o in info['obras'][:8])
                e.add_field(name='📚 Obras principais', value=obras_str[:900], inline=False)
            if info.get('foto_url'):
                e.set_thumbnail(url=info['foto_url'])
            e.set_footer(text=FOOTER)
            await destino.send(embed=e)
            return

        # Fallback puro Google Books
        livros = await buscar_livros(f'inauthor:{nome}', 5, lang='pt')
        if not livros:
            livros = await buscar_livros(nome, 5, lang='pt')
        e = discord.Embed(title=f'✍️ {nome}', description='Obras encontradas:', color=CORES['laranja'])
        if not livros:
            e.description = 'Não encontrei obras desse autor. Tente o nome completo ou verifique a escrita.'
        for l in livros[:5]:
            e.add_field(name=l['titulo'][:60], value=f"{l.get('ano','')} • {l.get('editora','') or 'Editora não informada'}", inline=False)
        e.set_footer(text=FOOTER)
        await destino.send(embed=e)

    @app_commands.command(name='autor', description='✍️ Pesquisa um autor (foto, bio, obras)')
    async def autor(self, interaction, nome: str):
        await interaction.response.defer()
        class Dest:
            async def send(_, **kw): return await interaction.followup.send(**kw)
        await self._autor_exec(Dest(), nome)

    @commands.command(name='autor')
    async def autor_prefix(self, ctx, *, nome: str = None):
        if not nome: return await ctx.send(embed=embed_erro('Use: `!autor <nome>`'))
        async with ctx.typing():
            await self._autor_exec(ctx, nome)

    # ── TOP LIVROS ──
    def _top_view(self):
        paginas = [TOP50[i:i+10] for i in range(0, len(TOP50), 10)]
        return TopLivrosView(paginas)

    @app_commands.command(name='toplivros', description='📚 Exibe 50 livros muito lidos/conhecidos')
    async def toplivros(self, interaction):
        view = self._top_view()
        await interaction.response.send_message(embed=view.embed(), view=view)

    @commands.command(name='toplivros', aliases=['top-livros'])
    async def toplivros_prefix(self, ctx):
        view = self._top_view()
        await ctx.send(embed=view.embed(), view=view)

    # ── ANIMAIS ──────────────────────────────────────────────────────────────
    async def _animal_url(self, tipo: str) -> str:
        """Busca URL de imagem para o tipo de animal. Retorna fallback se falhar."""
        try:
            async with aiohttp.ClientSession(headers={'User-Agent': 'IvyBot/2.0'}) as s:
                if tipo == 'gato':
                    async with s.get('https://api.thecatapi.com/v1/images/search', timeout=aiohttp.ClientTimeout(total=8)) as r:
                        data = await r.json(); return data[0]['url']
                if tipo == 'cachorro':
                    async with s.get('https://dog.ceo/api/breeds/image/random', timeout=aiohttp.ClientTimeout(total=8)) as r:
                        data = await r.json(); return data['message']
                if tipo == 'raposa':
                    async with s.get('https://randomfox.ca/floof/', timeout=aiohttp.ClientTimeout(total=8)) as r:
                        data = await r.json(); return data['image']
                if tipo == 'pato':
                    async with s.get('https://random-d.uk/api/random', timeout=aiohttp.ClientTimeout(total=8)) as r:
                        data = await r.json(); return data['url']
                if tipo == 'panda':
                    async with s.get('https://some-random-api.com/animal/panda', timeout=aiohttp.ClientTimeout(total=8)) as r:
                        data = await r.json(); return data['image']
        except Exception:
            pass
        return ANIMAL_FALLBACKS.get(tipo, ANIMAL_FALLBACKS['gato'])

    async def _animal_send(self, destino, tipo: str):
        if tipo == 'aleatorio':
            tipo = random.choice(ANIMAIS_DISPONIVEIS)
        url = await self._animal_url(tipo)
        emoji = ANIMAL_EMOJIS.get(tipo, '🐾')
        e = discord.Embed(title=f'{emoji} {tipo.title()} fofo', color=CORES['rosa'])
        e.set_image(url=url)
        e.set_footer(text=FOOTER)
        await destino.send(embed=e)

    # Slash: /animal (sorteio aleatório entre todos os animais)
    @app_commands.command(name='animal', description='🐾 Foto de animal fofo aleatório (gato, cachorro, raposa, pato, panda)')
    async def animal_slash(self, interaction):
        class Dest:
            async def send(_, **kw): return await interaction.response.send_message(**kw)
        await self._animal_send(Dest(), 'aleatorio')

    # Slash específicos
    @app_commands.command(name='gato', description='🐱 Foto de gato fofo')
    async def gato_slash(self, interaction):
        class Dest:
            async def send(_, **kw): return await interaction.response.send_message(**kw)
        await self._animal_send(Dest(), 'gato')

    @app_commands.command(name='cachorro', description='🐶 Foto de cachorro fofo')
    async def cachorro_slash(self, interaction):
        class Dest:
            async def send(_, **kw): return await interaction.response.send_message(**kw)
        await self._animal_send(Dest(), 'cachorro')

    # Prefix: !animal (comando principal, aleatório)
    @commands.command(name='animal', aliases=['animalfofo'])
    async def animal_prefix(self, ctx):
        await self._animal_send(ctx, 'aleatorio')

    # Prefix específicos
    @commands.command(name='gato')
    async def gato_prefix(self, ctx): await self._animal_send(ctx, 'gato')
    @commands.command(name='cachorro')
    async def cachorro_prefix(self, ctx): await self._animal_send(ctx, 'cachorro')
    @commands.command(name='raposa')
    async def raposa_prefix(self, ctx): await self._animal_send(ctx, 'raposa')
    @commands.command(name='pato')
    async def pato_prefix(self, ctx): await self._animal_send(ctx, 'pato')
    @commands.command(name='panda')
    async def panda_prefix(self, ctx): await self._animal_send(ctx, 'panda')

    # ── AJUDA ──
    @app_commands.command(name='ajuda', description='📋 Lista comandos da Ivy por categoria')
    async def ajuda_slash(self, interaction):
        view = HelpView()
        first = next(iter(HelpView.CATS))
        await interaction.response.send_message(embed=HelpView.make_embed(first), view=view, ephemeral=True)

    @commands.command(name='ajuda', aliases=['help', 'h', 'comandos'])
    async def ajuda_prefix(self, ctx):
        view = HelpView()
        first = next(iter(HelpView.CATS))
        await ctx.send(embed=HelpView.make_embed(first), view=view)

async def setup(bot): await bot.add_cog(Literario(bot))
