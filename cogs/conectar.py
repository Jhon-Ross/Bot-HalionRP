import discord
from discord import app_commands, Interaction, Forbidden
from discord.ext import commands
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class ConnectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(
            label="🌐 Acesse nosso site",
            url="https://halionrp.com.br",
            style=discord.ButtonStyle.link
        ))


class ConnectCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="connect", description="Mostra as informações de conexão ao servidor.")
    async def connect(self, interaction: Interaction):
        try:
            embed = discord.Embed(
                title="🌆 Conecte-se ao Halion RP",
                description=(
                    "**Seja bem-vindo ao Halion RP!**\n\n"
                    "📥 Para entrar diretamente no servidor, use:\n"
                    "```\n"
                    "fivem://connect/163.5.124.34\n"
                    "```\n\n"
                    "Ou acesse nosso site abaixo para mais informações.\n\n"
                    "⚠️ Certifique-se de estar com a whitelist aprovada!"
                ),
                color=discord.Color.dark_teal(),
                timestamp=datetime.now(timezone.utc)
            )

            embed.set_thumbnail(url="https://media.discordapp.net/attachments/1305316341619757127/1361785119056335008/Halionlogocity.png?ex=680004b9&is=67feb339&hm=ccc2c52278aec77152fca37ae434d2f4cf8fd2842f4b0e76cfcbb6683c616422&=&format=webp&quality=lossless&width=968&height=968")
            embed.set_footer(text="Halion RP • Conexão Rápida")

            view = ConnectView()
            await interaction.response.send_message(embed=embed, view=view)

            logger.info(
                f"/connect usado por {interaction.user} ({interaction.user.id})")

        except Forbidden as e:
            logger.error(
                f"Permissão negada no /connect para {interaction.user}: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Permissão negada para enviar a embed.")

        except Exception as e:
            logger.critical(f"Erro no comando /connect: {e}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Erro ao executar o comando /connect.")


async def setup(bot: commands.Bot):
    await bot.add_cog(ConnectCog(bot))
