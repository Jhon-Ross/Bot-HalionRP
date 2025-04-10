import discord
from discord import Interaction, app_commands, Forbidden, NotFound
from discord.ext import commands
from views.whitelist_view import WhitelistView
import os
import logging

# --- Início: Carregamento de Configurações e Verificações Iniciais ---

WHITELIST_CHANNEL_ID = None
try:
    _whitelist_id_str = os.getenv("WHITELIST_ID")
    if _whitelist_id_str:
        WHITELIST_CHANNEL_ID = int(_whitelist_id_str)
        logging.info(
            f"ID do canal de Whitelist carregado: {WHITELIST_CHANNEL_ID}")
    else:
        logging.error(
            "WHITELIST_ID não definido no .env! O comando /whitelist não funcionará.")
except (TypeError, ValueError):
    logging.error("WHITELIST_ID inválido no .env! Deve ser um número inteiro.")
    WHITELIST_CHANNEL_ID = None


try:
    from cogs.verificacao import check_user_has_mod_role
    logging.info(
        "Função check_user_has_mod_role importada de cogs.verificacao.")
except ImportError:
    logging.critical(
        "Falha ao importar 'check_user_has_mod_role' de cogs.verificacao. Verifique a estrutura de pastas e o arquivo.")
    # --- Início: Função Fallback de Verificação de Cargo ---

    async def check_user_has_mod_role(interaction: Interaction) -> bool:
        logging.error(
            "Função check_user_has_mod_role (fallback) ativada devido a erro de importação!")
        if not interaction.response.is_done():
            try:
                await interaction.response.send_message("❌ Erro crítico de configuração do bot (verificação de permissão). Contate um administrador.", ephemeral=True)
            except Exception:
                pass
        return False
    # --- Fim: Função Fallback de Verificação de Cargo ---

logger = logging.getLogger(__name__)

# --- Fim: Carregamento de Configurações e Verificações Iniciais ---


# --- Início: Definição da Classe Cog 'Whitelist' ---
class Whitelist(commands.Cog):
    # --- Início: Método Construtor __init__ ---
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.whitelist_channel_id = WHITELIST_CHANNEL_ID
        logger.info(
            f"Whitelist Cog iniciado. Canal alvo ID: {self.whitelist_channel_id or 'NÃO CONFIGURADO!'}")
    # --- Fim: Método Construtor __init__ ---

    # --- Início: Comando de Aplicação /whitelist ---
    @app_commands.command(name="whitelist", description="Envia a mensagem de whitelist para o canal correto.")
    @app_commands.check(check_user_has_mod_role)
    async def whitelist(self, interaction: discord.Interaction):
        """Envia o painel de whitelist com botão"""

        if self.whitelist_channel_id is None:
            logger.error(
                f"Usuário {interaction.user} tentou usar /whitelist, mas WHITELIST_ID não está configurado ou é inválido.")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ **Erro de Configuração:** O canal para o comando whitelist não foi definido corretamente no bot. Avise um administrador.",
                    ephemeral=True
                )
            return

        if interaction.channel_id != self.whitelist_channel_id:
            correct_channel_mention = f"<#{self.whitelist_channel_id}>"
            logger.warning(
                f"Usuário {interaction.user} tentou usar /whitelist no canal errado ({interaction.channel.name}/{interaction.channel_id}). Canal correto: {self.whitelist_channel_id}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"⚠️ **Canal Incorreto!** Este comando só pode ser utilizado no canal {correct_channel_mention}.",
                    ephemeral=True
                )
            return

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
                f"Comando /whitelist executado com sucesso por {interaction.user} no canal {interaction.channel.name}")

        except Forbidden as e:
            logger.error(
                f"Erro de permissão ao executar /whitelist por {interaction.user} no canal {interaction.channel.name}: {e}", exc_info=True)
            error_message = "❌ O bot não tem permissão para enviar mensagens ou embeds neste canal."
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(error_message, ephemeral=True)
                else:
                    logger.warning(
                        "Não foi possível notificar sobre erro de permissão pois a interação já foi respondida.")
            except Exception as inner_e:
                logger.error(
                    f"Erro ao tentar enviar mensagem de erro de permissão (whitelist): {inner_e}")

        except Exception as e:
            logger.error(
                f"Erro inesperado ao executar /whitelist por {interaction.user} no canal {interaction.channel.name}: {e}", exc_info=True)
            error_message = "❌ Ocorreu um erro inesperado ao tentar enviar o painel de whitelist."
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(error_message, ephemeral=True)
                else:
                    try:
                        await interaction.followup.send(error_message, ephemeral=True)
                    except (NotFound, Forbidden):
                        logger.warning(
                            f"Não foi possível enviar followup de erro do /whitelist para {interaction.user} (interação/permissão).")
                    except Exception as follow_e:
                        logger.error(
                            f"Erro no followup de erro /whitelist: {follow_e}")
            except Exception as resp_e:
                logger.error(
                    f"Erro ao tentar enviar mensagem de erro genérico (whitelist): {resp_e}")
    # --- Fim: Comando de Aplicação /whitelist ---

    # --- Início: Tratador de Erros do Cog (cog_app_command_error) ---
    async def cog_app_command_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        """Trata erros para os comandos de aplicativo neste Cog, principalmente CheckFailure."""
        command_name = interaction.command.name if interaction.command else "desconhecido"

        if isinstance(error, app_commands.CheckFailure):
            logger.warning(
                f"CheckFailure pego por cog_app_command_error para o comando '{command_name}' por {interaction.user}. Verificação de cargo falhou.")

            custom_error_message = "🚫 Você não tem permissão (cargo não autorizado) para usar este comando."
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(custom_error_message, ephemeral=True)
                else:
                    await interaction.followup.send(custom_error_message, ephemeral=True)
            except (NotFound, Forbidden):
                logger.warning(
                    f"Não foi possível enviar mensagem de erro de permissão (whitelist CheckFailure) para {interaction.user}.")
            except Exception as e_resp:
                logger.error(
                    f"Erro ao enviar mensagem de erro de permissão (whitelist CheckFailure) para {interaction.user}: {e_resp}", exc_info=True)
            return

        logger.error(
            f"Erro inesperado não tratado pego por cog_app_command_error no comando '{command_name}' por {interaction.user}: {error}",
            exc_info=True
        )
        generic_error_message = "❌ Ocorreu um erro inesperado e não tratado ao processar este comando."
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(generic_error_message, ephemeral=True)
            else:
                await interaction.followup.send(generic_error_message, ephemeral=True)
        except (NotFound, Forbidden):
            logger.warning(
                f"Não foi possível enviar mensagem de erro genérico (whitelist cog_app_command_error) para {interaction.user}.")
        except Exception as e_resp:
            logger.error(
                f"Erro ao enviar mensagem de erro genérico (whitelist cog_app_command_error) para {interaction.user}: {e_resp}", exc_info=True)
    # --- Fim: Tratador de Erros do Cog (cog_app_command_error) ---

# --- Fim: Definição da Classe Cog 'Whitelist' ---


# --- Início: Função setup (Carregamento do Cog) ---
async def setup(bot: commands.Bot):
    if WHITELIST_CHANNEL_ID is None:
        logging.error("*"*50)
        logging.error(
            "Cog Whitelist NÃO será carregado porque WHITELIST_ID está ausente ou inválido no .env.")
        logging.error("*"*50)
        return

    if 'check_user_has_mod_role' not in globals() or not callable(check_user_has_mod_role):
        logging.warning("*"*50)
        logging.warning("Cog Whitelist será carregado, mas a função de verificação de cargo 'check_user_has_mod_role' não foi importada corretamente (usando fallback). A permissão pode não funcionar como esperado.")
        logging.warning("*"*50)

    await bot.add_cog(Whitelist(bot))
    logger.info("Cog Whitelist carregado com sucesso.")
# --- Fim: Função setup (Carregamento do Cog) ---
