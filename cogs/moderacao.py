# Arquivo: cogs/moderacao.py

import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import List
import os  # <--- ADICIONE ESTA LINHA


class ModeracaoCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)

    @app_commands.command(name="excluir", description="Exclui uma quantidade específica de mensagens do canal atual (1-100).")
    @app_commands.describe(quantidade="Número de mensagens a excluir (máximo 100).")
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.checks.bot_has_permissions(manage_messages=True)
    async def excluir(self, interaction: discord.Interaction, quantidade: app_commands.Range[int, 1, 100]):
        """
        Exclui um número especificado de mensagens no canal onde o comando foi invocado.
        """
        await interaction.response.defer(ephemeral=True, thinking=True)
        channel = interaction.channel

        try:
            deleted_messages: List[discord.Message] = await channel.purge(limit=quantidade)
            num_deleted = len(deleted_messages)

            await interaction.followup.send(f"✅ {num_deleted} {'mensagem foi excluída' if num_deleted == 1 else 'mensagens foram excluídas'} com sucesso!", ephemeral=True)
            self.logger.info(
                f"{interaction.user} ({interaction.user.id}) usou /excluir para apagar {num_deleted} mensagens em #{channel.name} ({channel.id})")

            # Log no canal de logs do Discord
            logs_channel_id_str = os.getenv(
                "LOGS_DISCORD")  # Agora o 'os' está definido
            if logs_channel_id_str:
                try:
                    logs_channel_id = int(logs_channel_id_str)
                    log_channel = self.bot.get_channel(logs_channel_id)
                    if log_channel:
                        embed_log = discord.Embed(
                            title="🗑️ Mensagens Excluídas",
                            description=f"**{num_deleted}** mensagens foram excluídas em {channel.mention}.",
                            color=discord.Color.orange(),
                            timestamp=discord.utils.utcnow()
                        )
                        embed_log.add_field(
                            name="Moderador", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=False)
                        embed_log.set_footer(text="Comando /excluir")
                        await log_channel.send(embed=embed_log)
                except ValueError:
                    self.logger.error(
                        f"LOGS_DISCORD ('{logs_channel_id_str}') é inválido no .env para log de moderação.")
                except Exception as e_log:
                    self.logger.error(
                        f"Erro ao enviar log de exclusão para Discord: {e_log}", exc_info=True)

        except discord.Forbidden as e:
            self.logger.warning(
                f"Permissão 'Manage Messages' faltando para /excluir em #{channel.name} pelo bot {self.bot.user}")
            await interaction.followup.send("❌ **Erro:** Eu não tenho a permissão `Gerenciar Mensagens` neste canal.", ephemeral=True)
        except discord.HTTPException as e:
            self.logger.error(
                f"Erro HTTP durante /excluir em #{channel.name}: {e}", exc_info=True)
            await interaction.followup.send("❌ **Erro:** Ocorreu um problema de comunicação com o Discord.", ephemeral=True)
        except Exception as e:
            self.logger.error(
                f"Erro inesperado durante /excluir em #{channel.name}: {e}", exc_info=True)
            await interaction.followup.send("❌ **Erro:** Um erro inesperado aconteceu.", ephemeral=True)

    @excluir.error
    async def excluir_error_handler(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Trata erros específicos do comando /excluir."""
        if isinstance(error, app_commands.MissingPermissions):
            self.logger.warning(
                f"Usuário {interaction.user} tentou usar /excluir sem permissão 'Manage Messages' em #{interaction.channel.name}")
            await interaction.response.send_message("🚫 Você não tem a permissão `Gerenciar Mensagens`.", ephemeral=True)
        elif isinstance(error, app_commands.BotMissingPermissions):
            self.logger.warning(
                f"Bot não tem permissão 'Manage Messages' para /excluir em #{interaction.channel.name}")
            if not interaction.response.is_done():
                await interaction.response.send_message("🛠️ **Aviso:** Eu não tenho a permissão `Gerenciar Mensagens` necessária.", ephemeral=True)
            else:
                await interaction.followup.send("🛠️ **Aviso:** Eu não tenho a permissão `Gerenciar Mensagens` necessária.", ephemeral=True)
        elif isinstance(error, app_commands.CommandInvokeError) and isinstance(error.original, discord.errors.NotFound) and "Unknown Interaction" in str(error.original):
            self.logger.warning(
                f"Erro 'Unknown Interaction' ao responder /excluir para {interaction.user}.")
        else:
            self.logger.error(
                f"Erro não tratado no handler de /excluir: {error}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Ocorreu um erro inesperado.", ephemeral=True)
            else:
                try:
                    await interaction.followup.send("❌ Ocorreu um erro inesperado.", ephemeral=True)
                except discord.errors.NotFound:
                    pass


async def setup(bot: commands.Bot):
    await bot.add_cog(ModeracaoCog(bot))
    logging.info("Cog ModeracaoCog carregado com sucesso.")
