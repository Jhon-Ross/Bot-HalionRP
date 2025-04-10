import discord
from discord import Interaction, app_commands, Forbidden, NotFound
from discord.ext import commands
from discord.ui import Button, View
import os
import logging
from datetime import datetime
from typing import Set

logger = logging.getLogger(__name__)

# --- Carregamento do ID do canal de Verificação ---
VERIFICAR_CHANNEL_ID = None
try:
    _verificar_id_str = os.getenv("VERIFICAR_ID")
    if _verificar_id_str:
        VERIFICAR_CHANNEL_ID = int(_verificar_id_str)
        logging.info(
            f"ID do canal de Verificação carregado: {VERIFICAR_CHANNEL_ID}")
    else:
        logging.error(
            "VERIFICAR_ID não definido no .env! O comando /verificar não funcionará.")
except (TypeError, ValueError):
    logging.error("VERIFICAR_ID inválido no .env! Deve ser um número inteiro.")
    VERIFICAR_CHANNEL_ID = None
# --- Fim do Carregamento do ID ---


# --- Início das Funções Auxiliares de Verificação de Cargo ---
def get_allowed_mod_role_ids() -> Set[int]:
    """Lê e processa a variável de ambiente ALLOWED_MOD_ROLE_IDS."""
    allowed_roles_str = os.getenv("ALLOWED_MOD_ROLE_IDS")
    if not allowed_roles_str:
        logger.warning("ALLOWED_MOD_ROLE_IDS não está definido no .env.")
        return set()
    role_ids = set()
    id_strings = allowed_roles_str.split(',')
    for id_str in id_strings:
        id_str = id_str.strip()
        if id_str.isdigit():
            role_ids.add(int(id_str))
        elif id_str:
            logger.warning(
                f"Valor inválido '{id_str}' em ALLOWED_MOD_ROLE_IDS.")
    return role_ids


async def check_user_has_mod_role(interaction: Interaction) -> bool:
    """Verifica se o usuário possui um dos cargos definidos em ALLOWED_MOD_ROLE_IDS."""
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        return False
    allowed_role_ids = get_allowed_mod_role_ids()
    if not allowed_role_ids:
        logger.debug(
            f"Check de cargo falhou para {interaction.user}: Nenhum cargo permitido.")
        return False
    user_role_ids = {role.id for role in interaction.user.roles}
    if user_role_ids.intersection(allowed_role_ids):
        logger.debug(f"Check de cargo OK para {interaction.user}.")
        return True
    else:
        logger.warning(
            f"Check de cargo falhou para {interaction.user}: Sem cargo permitido.")
        return False
# --- Fim das Funções Auxiliares de Verificação de Cargo ---


# --- Início da Classe VerificarView (Botão Persistente) ---
class VerificarView(View):
    def __init__(self, *args, **kwargs):
        super().__init__(timeout=None)  # Define a view como persistente

    # --- Início do Callback do Botão de Verificação ---
    @discord.ui.button(label="Verificar-se", style=discord.ButtonStyle.green, emoji="✅", custom_id="verificar_botao")
    async def verificar_callback(self, interaction: Interaction, button: Button):
        """Lógica executada quando o botão 'Verificar-se' é pressionado."""
        await interaction.response.defer(ephemeral=True, thinking=True)
        member = interaction.user
        try:
            # Carrega IDs e valida configuração
            turista_id_str = os.getenv("TURISTA_ID")
            visitante_id_str = os.getenv("VISITANTE_ID")
            if not turista_id_str or not visitante_id_str:
                await interaction.followup.send("❌ Sistema de verificação não configurado (IDs ausentes).", ephemeral=True)
                logger.error(
                    "TURISTA_ID ou VISITANTE_ID não encontrado no .env")
                return
            try:
                turista_role_id = int(turista_id_str)
                visitante_role_id = int(visitante_id_str)
            except ValueError:
                await interaction.followup.send("❌ IDs de cargos configurados são inválidos.", ephemeral=True)
                logger.error(
                    f"IDs inválidos: Turista='{turista_id_str}', Visitante='{visitante_id_str}'")
                return

            # Obtém objetos Role e valida existência
            turista_role = interaction.guild.get_role(turista_role_id)
            visitante_role = interaction.guild.get_role(visitante_role_id)
            if not turista_role or not visitante_role:
                await interaction.followup.send("❌ Cargos de verificação não encontrados no servidor.", ephemeral=True)
                logger.error(
                    f"Cargo Turista {'não ' if not turista_role else ''}encontrado (ID: {turista_role_id}). Visitante {'não ' if not visitante_role else ''}encontrado (ID: {visitante_role_id}).")
                return

            # Verifica cargos do membro
            if turista_role in member.roles:
                await interaction.followup.send(f"⚠️ Você já está verificado com o cargo {turista_role.mention}!", ephemeral=True)
                return
            if visitante_role not in member.roles:
                await interaction.followup.send(f"⚠️ Apenas membros com o cargo {visitante_role.mention} precisam se verificar.", ephemeral=True)
                logger.info(
                    f"Verificação (botão) ignorada para {member.name}: não possui cargo Visitante.")
                return

            # Executa a troca de cargos
            logger.info(
                f"Iniciando troca de cargos (botão) para {member.name}: Visitante -> Turista")
            removido_visitante = False
            try:
                await member.add_roles(turista_role, reason="Verificação via botão")
                logger.info(
                    f"Cargo '{turista_role.name}' adicionado a {member.name}")
                try:
                    await member.remove_roles(visitante_role, reason="Verificado, recebeu Turista")
                    logger.info(
                        f"Cargo '{visitante_role.name}' removido de {member.name}")
                    removido_visitante = True
                except Exception as e_rem:
                    logger.error(
                        f"Erro ao REMOVER cargo Visitante de {member.name}: {e_rem}", exc_info=True)
            except Exception as e_add:
                await interaction.followup.send("❌ Erro ao tentar adicionar o cargo de Turista.", ephemeral=True)
                logger.error(
                    f"Erro ao ADICIONAR cargo Turista a {member.name}: {e_add}", exc_info=True)
                return

            # Envia mensagem de sucesso
            mensagem_sucesso = f"✅ Verificação concluída! Você recebeu {turista_role.mention}."
            if removido_visitante:
                mensagem_sucesso += f" O cargo {visitante_role.mention} foi removido."
            else:
                mensagem_sucesso += f" (O cargo {visitante_role.mention} não pôde ser removido)."
            await interaction.followup.send(mensagem_sucesso, ephemeral=True)

            # Envia Log para Discord (se configurado)
            logs_channel_id_str = os.getenv("LOGS_DISCORD")
            if logs_channel_id_str:
                try:
                    logs_channel_id = int(logs_channel_id_str)
                    channel_log = interaction.guild.get_channel(
                        logs_channel_id)
                    if channel_log:
                        embed_log = discord.Embed(
                            description=f"🎟️ {member.mention} se verificou.\n➕ Recebeu: {turista_role.mention}\n{f'➖ Removido: {visitante_role.mention}' if removido_visitante else f'⚠️ Falha ao remover: {visitante_role.mention}'}",
                            color=discord.Color.green() if removido_visitante else discord.Color.orange(),
                            timestamp=datetime.now()
                        )
                        embed_log.set_author(
                            name=f"{member.name} ({member.id})", icon_url=member.display_avatar.url)
                        embed_log.set_footer(
                            text="Sistema de Verificação (Botão)")
                        await channel_log.send(embed=embed_log)
                except Exception as e_log_disc:
                    logger.error(
                        f"Erro ao enviar log de verificação (botão) para Discord: {e_log_disc}", exc_info=True)

        except Forbidden as e:
            logger.error(
                f"Erro de permissão no callback de verificação para {member.name}: {e}", exc_info=True)
            try:
                await interaction.followup.send("❌ Bot sem permissão para gerenciar cargos.", ephemeral=True)
            except Exception:
                pass
        except Exception as e:
            logger.critical(
                f"Erro GERAL no callback de verificação para {member.name}", exc_info=True)
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("⚠️ Erro inesperado no sistema de verificação.", ephemeral=True)
                else:
                    await interaction.followup.send("⚠️ Erro inesperado no sistema de verificação.", ephemeral=True)
            except Exception as e_inner:
                logger.error(
                    f"Falha ao notificar {member.name} sobre erro na verificação: {e_inner}")
    # --- Fim do Callback do Botão de Verificação ---

# --- Fim da Classe VerificarView ---


# --- Início da Classe VerificacaoCog ---
class VerificacaoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.verificar_channel_id = VERIFICAR_CHANNEL_ID
        logger.info(
            f"Verificacao Cog iniciado. Canal alvo ID: {self.verificar_channel_id or 'NÃO CONFIGURADO!'}")

    # --- Início do Comando /verificar ---
    @app_commands.command(name="verificar", description="Envia o painel de verificação no canal correto.")
    @app_commands.check(check_user_has_mod_role)
    async def verificar(self, interaction: Interaction):
        """Envia o painel de verificação com botão persistente."""

        # Verificação 1: ID do canal configurado?
        if self.verificar_channel_id is None:
            logger.error(
                f"Usuário {interaction.user} tentou /verificar sem VERIFICAR_ID configurado.")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Erro de Configuração: Canal `/verificar` não definido.", ephemeral=True)
            return

        # Verificação 2: Comando usado no canal correto?
        if interaction.channel_id != self.verificar_channel_id:
            correct_channel_mention = f"<#{self.verificar_channel_id}>"
            logger.warning(
                f"Usuário {interaction.user} usou /verificar no canal errado ({interaction.channel.name}). Correto: {self.verificar_channel_id}")
            if not interaction.response.is_done():
                await interaction.response.send_message(f"⚠️ Comando só pode ser usado em {correct_channel_mention}.", ephemeral=True)
            return

        # Lógica principal do comando
        try:
            embed = discord.Embed(
                title="🚀 Bem-vindo ao nosso servidor!",
                description="Para nossa segurança 🔒, mostre que você não é um robô assim como eu 🤭! Clique no botão abaixo para se verificar.✅",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed, view=VerificarView())
            logger.info(
                f"Painel de verificação enviado por {interaction.user} em {interaction.channel.name}")

        except Forbidden as e:
            logger.error(
                f"Erro de permissão ao executar /verificar por {interaction.user}: {e}", exc_info=True)
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ Bot sem permissão neste canal.", ephemeral=True)
            except Exception:
                pass
        except Exception as e:
            logger.error(
                f"Erro inesperado no comando /verificar por {interaction.user}: {e}", exc_info=True)
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ Erro ao enviar painel.", ephemeral=True)
                else:
                    try:
                        await interaction.followup.send("❌ Erro ao enviar painel.", ephemeral=True)
                    except Exception:
                        pass
            except Exception:
                pass
    # --- Fim do Comando /verificar ---

# --- Início do Listener on_member_join (Boas Vindas) ---

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Envia mensagem de boas-vindas personalizada ao novo membro."""
        if member.bot:
            return
        try:
            channel_id_str = os.getenv("BOAS_VINDAS_ID")
            if not channel_id_str:
                logger.warning("BOAS_VINDAS_ID não definido.")
                return
            try:
                channel_id = int(channel_id_str)
            except ValueError:
                logger.error(f"BOAS_VINDAS_ID ('{channel_id_str}') inválido.")
                return
            channel = self.bot.get_channel(channel_id)
            if not channel:
                logger.warning(
                    f"Canal de Boas Vindas (ID: {channel_id}) não encontrado.")
                return

            regras_channel_mention = "⁠📚・𝗥𝗘𝗚𝗥𝗔𝗦-𝗗𝗜𝗦𝗖𝗢𝗥𝗗"
            verificar_channel_mention = "⁠✅・𝗩𝗲𝗿𝗶𝗳𝗶𝗰𝗮𝗿"
            try:
                regras_id_str = os.getenv("REGRAS_ID")
                if regras_id_str:
                    regras_id = int(regras_id_str)
                    regras_channel_mention = f"<#{regras_id}>"
            except (ValueError, TypeError):
                logger.warning(
                    "REGRAS_ID inválido ou não definido, usando nome padrão.")
            try:
                if self.verificar_channel_id:
                    verificar_channel_mention = f"<#{self.verificar_channel_id}>"
            except Exception:
                logger.warning(
                    "Erro ao obter VERIFICAR_ID para Boas Vindas, usando nome padrão.")

            # --- Definindo URLs das Redes Sociais ---
            instagram_url = "https://www.instagram.com/halionrp/"
            tiktok_url = "https://www.tiktok.com/@halionrp"
            # --- Fim da definição das URLs ---

            embed = discord.Embed(
                title="🎉 BEM-VINDO À **Halion RP**! 🌆",  # <- Halion RP em negrito
                description=(
                    # <- Adicionado \n extra aqui para espaçamento
                    f"👋 Olá, {member.mention}! Bem-vindo(a)!\n\n"
                    "📜 **Primeiros passos:**\n"  # <- Opcional: Deixar "Primeiros passos" em negrito também
                    f" • Leia as regras: {regras_channel_mention}\n"
                    f" • Faça a verificação: {verificar_channel_mention}\n\n"
                    "📱 **Siga-nos nas Redes Sociais:**\n"  # <- Opcional: Deixar em negrito
                    # --- Links inseridos usando Markdown ---
                    f" • [Instagram]({instagram_url})\n"
                    f" • [TikTok]({tiktok_url})\n\n"
                    # --- Fim dos links ---
                    "🚀 Prepare-se para uma ótima experiência!\n\n"
                    "**Halion RP** – Sua jornada começa aqui!"  # <- Halion RP em negrito
                ),
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )
            if member.display_avatar:
                embed.set_thumbnail(url=member.display_avatar.url)

            embed.set_footer(text="Halion RP")

            await channel.send(embed=embed)
            logger.info(f"Mensagem de boas-vindas enviada para {member.name}")

        except Exception as e:
            logger.error(
                f"Erro em on_member_join (Boas Vindas): {e}", exc_info=True)
    # --- Fim do Listener on_member_join (Boas Vindas) ---

    # --- Início do Tratador de Erros do Cog ---

    async def cog_app_command_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        """Trata erros para comandos de aplicativo neste Cog, principalmente CheckFailure."""
        command_name = interaction.command.name if interaction.command else "desconhecido"

        if isinstance(error, app_commands.CheckFailure):
            logger.warning(
                f"CheckFailure para '{command_name}' por {interaction.user}.")
            custom_error_message = "🚫 Você não tem permissão (cargo não autorizado) para usar este comando."
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(custom_error_message, ephemeral=True)
                else:
                    await interaction.followup.send(custom_error_message, ephemeral=True)
            except Exception as e_resp:
                logger.error(
                    f"Erro ao enviar msg de erro CheckFailure para {interaction.user}: {e_resp}")
            return

        logger.error(
            f"Erro inesperado (cog handler) no comando '{command_name}' por {interaction.user}: {error}", exc_info=True)
        generic_error_message = "❌ Ocorreu um erro inesperado ao processar este comando."
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(generic_error_message, ephemeral=True)
            else:
                await interaction.followup.send(generic_error_message, ephemeral=True)
        except Exception as e_resp:
            logger.error(
                f"Erro ao enviar msg de erro genérico (cog handler) para {interaction.user}: {e_resp}")
    # --- Fim do Tratador de Erros do Cog ---

# --- Fim da Classe VerificacaoCog ---


# --- Início da Função setup (Carregamento do Cog) ---
async def setup(bot):
    """Função chamada pelo bot para carregar este Cog."""
    # Verificação essencial: ID do canal configurado?
    if VERIFICAR_CHANNEL_ID is None:
        logging.error("*"*50)
        logging.error(
            "Cog VerificacaoCog NÃO será carregado: VERIFICAR_ID ausente/inválido no .env.")
        logging.error("*"*50)
        return  # Impede o carregamento do Cog

    # Adiciona o Cog ao Bot
    cog = VerificacaoCog(bot)
    await bot.add_cog(cog)

    # Registra a View Persistente se ainda não existir
    view_instance = VerificarView()
    found = False
    for existing_view in bot.persistent_views:
        if isinstance(existing_view, VerificarView) and existing_view.children:
            first_button = next((child for child in existing_view.children if isinstance(
                child, Button) and child.custom_id == "verificar_botao"), None)
            if first_button:
                found = True
                break
    if not found:
        bot.add_view(view_instance)
        logger.info("View VerificarView registrada para persistência.")
    else:
        logger.info(
            "View VerificarView (ou similar) já registrada, ignorando adição duplicada.")

    logger.info("Cog VerificacaoCog carregado com sucesso.")
# --- Fim da Função setup ---
