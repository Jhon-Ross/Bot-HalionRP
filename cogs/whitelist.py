import discord
from discord import Interaction, app_commands
from discord.ext import commands
from views.whitelist_view import WhitelistView
import os
import logging

try:
    from cogs.verificacao import check_user_has_mod_role, get_allowed_mod_role_ids
except ImportError:
    logging.critical(
        "Falha ao importar 'check_user_has_mod_role' de cogs.verificacao. Verifique a estrutura de pastas.")

    async def check_user_has_mod_role(interaction: Interaction) -> bool:
        logging.error("Função check_user_has_mod_role não pôde ser importada!")
        return False

logger = logging.getLogger(__name__)


class Whitelist(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="whitelist", description="Envia a mensagem de whitelist para o canal atual.")
    @app_commands.check(check_user_has_mod_role)
    async def whitelist(self, interaction: discord.Interaction):
        """Envia o painel de whitelist com botão"""
        try:
            embed = discord.Embed(
                title="🏙️ Sua história em Halion RP está esperando por você!",
                description=(
                    "Se você quer fazer parte de um RP imersivo, com liberdade para criar sua própria jornada, "
                    "o primeiro passo é iniciar seu teste de whitelist!\n\n"
                    "✅ **Se estiver pronto(a) para viver numa cidade cheia de oportunidades, personagens únicos e histórias épicas, a decisão é sua!**\n\n"
                    "⚠️ **Atenção total necessária!** Você terá apenas **20 minutos** para concluir o teste.\n"
                    "❌ Se o tempo acabar, a whitelist será fechada e você só poderá tentar novamente após **30 minutos**.\n\n"
                    "📍 **Dicas para não perder sua chance:**\n"
                    "- ✨ Escolha um local tranquilo, sem distrações.\n"
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
            logger.info(
                f"Comando /whitelist executado por {interaction.user} no canal {interaction.channel.name}")

        except Exception as e:
            logger.error(
                f"Erro ao executar /whitelist por {interaction.user}: {e}", exc_info=True)
            error_message = "❌ Ocorreu um erro ao tentar enviar o painel de whitelist."
            if not interaction.response.is_done():
                await interaction.response.send_message(error_message, ephemeral=True)
            else:
                try:
                    await interaction.followup.send(error_message, ephemeral=True)
                except discord.NotFound:
                    logger.warning(
                        f"Não foi possível enviar mensagem de erro do /whitelist para {interaction.user} (interação não encontrada).")

    async def cog_app_command_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        """Trata erros para todos os comandos de aplicativo neste Cog."""
        if isinstance(error, app_commands.CheckFailure):
            command_name = interaction.command.name if interaction.command else "desconhecido"
            logger.debug(
                f"Handler pegou CheckFailure para o comando '{command_name}' por {interaction.user} no WhitelistCog.")

            custom_error_message = "🚫 Você não tem permissão para usar este comando (cargo não autorizado)."
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(custom_error_message, ephemeral=True)
                else:
                    await interaction.followup.send(custom_error_message, ephemeral=True)
            except discord.NotFound:
                logger.warning(
                    f"Não foi possível enviar mensagem de erro de permissão (whitelist) para {interaction.user} (interação não encontrada).")
            except Exception as e_resp:
                logger.error(
                    f"Erro ao enviar mensagem de erro de permissão (whitelist) para {interaction.user}: {e_resp}", exc_info=True)
            return

        else:
            command_name = interaction.command.name if interaction.command else "comando desconhecido"
            logger.error(
                f"Erro inesperado ao executar '{command_name}' no WhitelistCog por {interaction.user}: {error}",
                exc_info=True
            )
            generic_error_message = "❌ Ocorreu um erro inesperado ao processar este comando."
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(generic_error_message, ephemeral=True)
                else:
                    await interaction.followup.send(generic_error_message, ephemeral=True)
            except discord.NotFound:
                logger.warning(
                    f"Não foi possível enviar mensagem de erro genérico (whitelist) para {interaction.user} (interação não encontrada).")
            except Exception as e_resp:
                logger.error(
                    f"Erro ao enviar mensagem de erro genérico (whitelist) para {interaction.user}: {e_resp}", exc_info=True)

    async def cog_load(self):
        if hasattr(self.bot, 'guild_id') and self.bot.guild_id:
            try:
                guild = discord.Object(id=self.bot.guild_id)
                await self.bot.tree.sync(guild=guild)
                logger.info(
                    f"Comandos do WhitelistCog sincronizados para a guilda {self.bot.guild_id}")
            except Exception as e:
                logger.error(
                    f"Falha ao sincronizar comandos do WhitelistCog para a guilda {self.bot.guild_id}: {e}", exc_info=True)
        else:
            logger.warning(
                "Não foi possível sincronizar comandos do WhitelistCog: self.bot.guild_id não definido.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Whitelist(bot))
    logger.info("Cog Whitelist carregado.")
