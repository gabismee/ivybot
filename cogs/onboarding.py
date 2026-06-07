import discord
from discord import app_commands
from discord.ext import commands
from utils.db import salvar_perfil, get_perfil, init_db
from utils.embeds import embed_sucesso

GENEROS_1 = ["Fantasia", "Ficção Científica", "Romance", "Terror", "Suspense", "Mistério", "História"]
GENEROS_2 = ["Desenvolvimento Pessoal", "Negócios", "Programação", "Ciência", "Biografias", "Mangás / HQs", "Infantil / Juvenil"]

class OnboardingModal(discord.ui.Modal, title="📚 Seus Autores Favoritos"):
    autores = discord.ui.TextInput(
        label="Autores favoritos (separados por vírgula)",
        placeholder="Ex: Brandon Sanderson, Stephen King, Machado de Assis",
        required=False,
        max_length=300
    )

    def __init__(self, dados_parciais: dict):
        super().__init__()
        self.dados = dados_parciais

    async def on_submit(self, interaction: discord.Interaction):
        self.dados["autores"] = [a.strip() for a in self.autores.value.split(",") if a.strip()]
        try:
            init_db()
            salvar_perfil(interaction.user.id, interaction.user.name, self.dados)
            embed = discord.Embed(
                title="✅ Perfil criado com sucesso!",
                description=(
                    f"**Bem-vindo(a), {interaction.user.display_name}!** 🎉\n\n"
                    "Seu perfil foi configurado. Agora você pode:\n"
                    "• `/buscar` — Pesquisar livros\n"
                    "• `/desejo adicionar` — Criar wishlist\n"
                    "• `/alerta` — Alertas de preço\n"
                    "• `/recomendar` — Receber recomendações personalizadas\n"
                    "• `/estante adicionar` — Organizar sua biblioteca\n"
                    "• `/perfil` — Ver seu perfil completo"
                ),
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"❌ Erro ao salvar perfil: {e}",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )

class OnboardingView(discord.ui.View):
    def __init__(self, etapa: int = 1, dados: dict = None):
        super().__init__(timeout=300)
        self.etapa = etapa
        self.dados = dados or {}
        self._construir()

    def _construir(self):
        self.clear_items()
        if self.etapa == 1:
            self._etapa_formato()
        elif self.etapa == 2:
            self._etapa_generos_1()
        elif self.etapa == 3:
            self._etapa_generos_2()
        elif self.etapa == 4:
            self._etapa_orcamento()
        elif self.etapa == 5:
            self._etapa_objetivo()
        elif self.etapa == 6:
            self._etapa_livros_ano()

    def _etapa_formato(self):
        opcoes = [
            discord.SelectOption(label="📚 Livro Físico", value="fisico",  emoji="📚"),
            discord.SelectOption(label="📱 Ebook",        value="ebook",   emoji="📱"),
            discord.SelectOption(label="🎧 Audiobook",    value="audio",   emoji="🎧"),
            discord.SelectOption(label="🌐 Todos",        value="todos",   emoji="🌐"),
        ]
        s = discord.ui.Select(placeholder="Formato preferido...", options=opcoes)
        s.callback = self._cb_formato
        self.add_item(s)

    async def _cb_formato(self, interaction: discord.Interaction):
        self.dados["formato"] = interaction.data["values"][0]
        self.etapa = 2
        self._construir()
        await interaction.response.edit_message(embed=self._embed_etapa(), view=self)

    def _etapa_generos_1(self):
        opcoes = [discord.SelectOption(label=g, value=g) for g in GENEROS_1]
        s = discord.ui.Select(
            placeholder="Gêneros — Parte 1 (escolha até 3)...",
            options=opcoes, min_values=0, max_values=3
        )
        s.callback = self._cb_generos_1
        self.add_item(s)

    async def _cb_generos_1(self, interaction: discord.Interaction):
        self.dados["generos"] = interaction.data["values"]
        self.etapa = 3
        self._construir()
        await interaction.response.edit_message(embed=self._embed_etapa(), view=self)

    def _etapa_generos_2(self):
        opcoes = [discord.SelectOption(label=g, value=g) for g in GENEROS_2]
        s = discord.ui.Select(
            placeholder="Gêneros — Parte 2 (escolha até 3 mais)...",
            options=opcoes, min_values=0, max_values=3
        )
        s.callback = self._cb_generos_2
        self.add_item(s)

    async def _cb_generos_2(self, interaction: discord.Interaction):
        self.dados["generos"] = self.dados.get("generos", []) + interaction.data["values"]
        self.etapa = 4
        self._construir()
        await interaction.response.edit_message(embed=self._embed_etapa(), view=self)

    def _etapa_orcamento(self):
        opcoes = [
            discord.SelectOption(label="💚 Até R$20",       value="ate_20"),
            discord.SelectOption(label="💛 Até R$50",       value="ate_50"),
            discord.SelectOption(label="🧡 Até R$100",      value="ate_100"),
            discord.SelectOption(label="❤️ Acima de R$100", value="acima_100"),
        ]
        s = discord.ui.Select(placeholder="Orçamento por livro...", options=opcoes)
        s.callback = self._cb_orcamento
        self.add_item(s)

    async def _cb_orcamento(self, interaction: discord.Interaction):
        self.dados["orcamento"] = interaction.data["values"][0]
        self.etapa = 5
        self._construir()
        await interaction.response.edit_message(embed=self._embed_etapa(), view=self)

    def _etapa_objetivo(self):
        opcoes = [
            discord.SelectOption(label="🎮 Ler por diversão",           value="diversao"),
            discord.SelectOption(label="🎓 Aprender habilidades",        value="aprender"),
            discord.SelectOption(label="💼 Desenvolvimento profissional", value="profissional"),
            discord.SelectOption(label="📝 Estudos / Vestibular",        value="estudos"),
            discord.SelectOption(label="📜 Concurso público",            value="concurso"),
        ]
        s = discord.ui.Select(placeholder="Objetivo principal...", options=opcoes)
        s.callback = self._cb_objetivo
        self.add_item(s)

    async def _cb_objetivo(self, interaction: discord.Interaction):
        self.dados["objetivo"] = interaction.data["values"][0]
        self.etapa = 6
        self._construir()
        await interaction.response.edit_message(embed=self._embed_etapa(), view=self)

    def _etapa_livros_ano(self):
        opcoes = [
            discord.SelectOption(label="1 a 5 livros/ano",   value="1-5"),
            discord.SelectOption(label="6 a 10 livros/ano",  value="6-10"),
            discord.SelectOption(label="11 a 20 livros/ano", value="11-20"),
            discord.SelectOption(label="Mais de 20/ano",     value="20+"),
        ]
        s = discord.ui.Select(placeholder="Quantos livros você lê por ano?", options=opcoes)
        s.callback = self._cb_livros_ano
        self.add_item(s)

    async def _cb_livros_ano(self, interaction: discord.Interaction):
        self.dados["livros_ano"] = interaction.data["values"][0]
        await interaction.response.send_modal(OnboardingModal(self.dados))

    def _embed_etapa(self) -> discord.Embed:
        titulos = {
            1: "📖 Formato preferido",
            2: "🏷️ Gêneros favoritos — Parte 1",
            3: "🏷️ Gêneros favoritos — Parte 2",
            4: "💰 Orçamento",
            5: "🎯 Objetivo",
            6: "📅 Meta de leitura",
        }
        descricoes = {
            1: "Qual tipo de livro você prefere consumir?",
            2: "Escolha até 3 gêneros da lista abaixo.",
            3: "Mais alguns gêneros! Escolha até 3 (ou pule).",
            4: "Quanto costuma gastar por livro?",
            5: "Qual é seu principal objetivo ao ler?",
            6: "Quantos livros você costuma ler por ano?",
        }
        embed = discord.Embed(
            title=f"📚 Configurando seu Perfil ({self.etapa}/6) — {titulos.get(self.etapa,'')}",
            description=descricoes.get(self.etapa, ""),
            color=discord.Color.blurple()
        )
        embed.set_footer(text="Suas preferências personalizam recomendações e alertas")
        return embed


class Onboarding(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def iniciar_onboarding(self, member: discord.Member):
        """Enviado automaticamente quando um novo membro entra"""
        perfil = get_perfil(member.id)
        if perfil:
            return

        embed = discord.Embed(
            title=f"📚 Olá, {member.display_name}! Bem-vindo(a)!",
            description=(
                "Sou o **BookBot**, seu assistente literário no Discord!\n\n"
                "Vou te fazer algumas perguntinhas para personalizar sua experiência.\n"
                "Leva menos de 1 minuto! 😊"
            ),
            color=discord.Color.blurple()
        )
        view = OnboardingView()
        try:
            await member.send(embed=embed, view=view)
        except discord.Forbidden:
            pass

    @app_commands.command(name="configurar", description="⚙️ Configura ou atualiza seu perfil de leitor")
    async def configurar(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📚 Configure seu Perfil de Leitor",
            description="Vamos personalizar sua experiência! Responda 6 perguntas rápidas.",
            color=discord.Color.blurple()
        )
        view = OnboardingView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Onboarding(bot))
