from discord.ext import commands
from discord import app_commands
import discord
from views.whitelist_view import WhitelistView


class Whitelist(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        if not bot.persistent_views_added:
            bot.add_view(WhitelistView())
            bot.persistent_views_added = True

    @app_commands.command(name="whitelist", description="Envia a mensagem de whitelist para o canal atual.")
    @app_commands.checks.has_permissions(administrator=True)
    async def whitelist(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🏙️ Sua história em Halion RP está esperando por você!",
            description=(
                "Se você quer fazer parte de um RP imersivo, com liberdade para criar sua própria jornada, "
                "o primeiro passo é iniciar seu teste de whitelist!\n\n"
                "✅ **Se estiver pronto(a) para viver numa cidade cheia de oportunidades, personagens únicos e histórias épicas, a decisão é sua!**\n\n"
                "⚠️ **Atenção total necessária!** Você terá apenas **20 minutos** para concluir o teste.\n"
                "❌ Se o tempo acabar, a whitelist será fechada e você só poderá tentar novamente após **30 minutos**.\n\n"
                "📍 **Dicas para não perder sua chance:**\n"
                "- Escolha um local tranquilo, sem distrações.\n"
                "- 🎧 Use fones para maior concentração.\n"
                "- 📝 Leia cada pergunta com atenção – não dá pra voltar atrás!\n\n"
                "🔘 **Clique no botão \"Quero fazer whitelist\" APENAS quando estiver:**\n"
                "✔ 100% focado(a)\n"
                "✔ Com tempo suficiente\n"
                "✔ Pronto(a) para encarar o desafio!\n\n"
                "_\"Uma vaga na cidade é conquistada por quem se prepara. Você vai encarar esse teste com a seriedade que ele merece?\"_"
            ),
            color=discord.Color.blue()
        )

        await interaction.response.send_message(embed=embed, view=WhitelistView())

    async def cog_load(self):
        # Sincroniza os comandos apenas com a guilda definida
        guild = discord.Object(id=self.bot.guild_id)
        self.bot.tree.copy_global_to(guild=guild)
        await self.bot.tree.sync(guild=guild)


async def setup(bot: commands.Bot):
    await bot.add_cog(Whitelist(bot))
