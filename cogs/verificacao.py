# Arquivo: cogs/verificacao.py

import discord
from discord import Interaction, app_commands  # Import Interaction
from discord.ext import commands
from discord.ui import Button, View
import os
import logging
from datetime import datetime
from typing import Set  # Import Set

# Configure o logger para este módulo
logger = logging.getLogger(__name__)

# --- FUNÇÕES DE VERIFICAÇÃO DE CARGO (Copiadas de moderacao.py) ---


def get_allowed_mod_role_ids() -> Set[int]:
    """Lê e processa a variável de ambiente ALLOWED_MOD_ROLE_IDS."""
    allowed_roles_str = os.getenv("ALLOWED_MOD_ROLE_IDS")
    if not allowed_roles_str:
        logger.warning(
            "ALLOWED_MOD_ROLE_IDS não está definido no .env. Ninguém poderá usar os comandos restritos por cargo.")
        return set()

    role_ids = set()
    id_strings = allowed_roles_str.split(',')
    for id_str in id_strings:
        id_str = id_str.strip()
        if id_str.isdigit():
            role_ids.add(int(id_str))
        elif id_str:
            logger.warning(
                f"Valor inválido encontrado em ALLOWED_MOD_ROLE_IDS: '{id_str}' será ignorado.")

    if not role_ids:
        logger.warning(
            f"Nenhum ID de cargo válido encontrado em ALLOWED_MOD_ROLE_IDS='{allowed_roles_str}'.")

    return role_ids


async def check_user_has_mod_role(interaction: Interaction) -> bool:
    """Verifica se o usuário possui um dos cargos definidos em ALLOWED_MOD_ROLE_IDS."""
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        return False

    allowed_role_ids = get_allowed_mod_role_ids()
    if not allowed_role_ids:
        logger.debug(
            f"Verificação de cargo falhou para {interaction.user} (comando: {interaction.command.name}): Nenhum cargo permitido configurado.")
        return False

    user_role_ids = {role.id for role in interaction.user.roles}

    if user_role_ids.intersection(allowed_role_ids):
        logger.debug(
            f"Verificação de cargo bem-sucedida para {interaction.user} (comando: {interaction.command.name}).")
        return True
    else:
        # Usamos warning aqui pois é uma falha de permissão esperada
        logger.warning(
            f"Usuário {interaction.user} (ID: {interaction.user.id}) negado acesso ao comando '{interaction.command.name}'. Não possui cargos permitidos ({allowed_role_ids}).")
        return False

# --- VIEW DE VERIFICAÇÃO (Permanece igual) ---


class VerificarView(View):
    def __init__(self, *args, **kwargs):
        super().__init__(timeout=None)

    @discord.ui.button(label="Verificar-se", style=discord.ButtonStyle.green, emoji="✅", custom_id="verificar_botao")
    async def verificar_callback(self, interaction: Interaction, button: Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        member = interaction.user

        try:
            # Obter Cargo Turista
            turista_id_str = os.getenv("TURISTA_ID")
            if not turista_id_str:
                await interaction.followup.send("❌ Sistema de verificação (cargo Turista) não configurado.", ephemeral=True)
                logger.error("TURISTA_ID não encontrado no .env")
                return
            try:
                turista_role_id = int(turista_id_str)
            except ValueError:
                await interaction.followup.send("❌ ID do cargo Turista configurado é inválido.", ephemeral=True)
                logger.error(f"TURISTA_ID ('{turista_id_str}') inválido.")
                return
            turista_role = interaction.guild.get_role(turista_role_id)
            if not turista_role:
                await interaction.followup.send("❌ Cargo de Turista não encontrado.", ephemeral=True)
                logger.error(
                    f"Cargo Turista (ID: {turista_role_id}) não encontrado.")
                return

            # Obter Cargo Visitante
            visitante_id_str = os.getenv("VISITANTE_ID")
            if not visitante_id_str:
                await interaction.followup.send("❌ Sistema de verificação (cargo Visitante) não configurado.", ephemeral=True)
                logger.error("VISITANTE_ID não encontrado no .env")
                return
            try:
                visitante_role_id = int(visitante_id_str)
            except ValueError:
                await interaction.followup.send("❌ ID do cargo Visitante configurado é inválido.", ephemeral=True)
                logger.error(f"VISITANTE_ID ('{visitante_id_str}') inválido.")
                return
            visitante_role = interaction.guild.get_role(visitante_role_id)
            if not visitante_role:
                await interaction.followup.send("❌ Cargo de Visitante não encontrado.", ephemeral=True)
                logger.error(
                    f"Cargo Visitante (ID: {visitante_role_id}) não encontrado.")
                return

            # LÓGICA PRINCIPAL DA VERIFICAÇÃO
            if turista_role in member.roles:
                await interaction.followup.send(f"⚠️ Você já possui o cargo {turista_role.mention}!", ephemeral=True)
                return
            if visitante_role not in member.roles:
                await interaction.followup.send(f"⚠️ Esta verificação é apenas para membros com o cargo {visitante_role.mention}.", ephemeral=True)
                logger.info(
                    f"Verificação (botão) bloqueada para {member.name}: não possui cargo Visitante.")
                return

            # Proceder com a troca
            logger.info(
                f"Iniciando troca de cargos (botão) para {member.name}: Visitante -> Turista")
            removido_visitante = False
            try:
                await member.add_roles(turista_role, reason="Verificação via botão (Visitante -> Turista)")
                logger.info(
                    f"Cargo '{turista_role.name}' adicionado a {member.name}")
                try:
                    await member.remove_roles(visitante_role, reason="Verificado, recebeu cargo Turista")
                    logger.info(
                        f"Cargo '{visitante_role.name}' removido de {member.name}")
                    removido_visitante = True
                except Exception as e_rem:
                    logger.error(
                        f"Erro ao REMOVER cargo Visitante de {member.name} após verificação: {e_rem}", exc_info=True)

            except Exception as e_add:
                await interaction.followup.send("❌ Erro ao tentar adicionar o cargo de Turista.", ephemeral=True)
                logger.error(
                    f"Erro ao ADICIONAR cargo Turista a {member.name} na verificação: {e_add}", exc_info=True)
                return

            mensagem_sucesso = f"✅ Verificação concluída! Você recebeu o cargo {turista_role.mention}."
            if removido_visitante:
                mensagem_sucesso += f" O cargo {visitante_role.mention} foi removido."
            else:
                mensagem_sucesso += f" (Não foi possível remover o cargo {visitante_role.mention}, mas você está verificado)."
            await interaction.followup.send(mensagem_sucesso, ephemeral=True)

            logs_channel_id_str = os.getenv("LOGS_DISCORD")
            if logs_channel_id_str:
                try:
                    logs_channel_id = int(logs_channel_id_str)
                    channel_log = interaction.guild.get_channel(
                        logs_channel_id)
                    if channel_log:
                        embed_log = discord.Embed(
                            description=f"🎟️ {member.mention} se verificou (Visitante -> Turista).\n"
                            f"➕ Recebeu: {turista_role.mention}\n"
                            f"{f'➖ Removido: {visitante_role.mention}' if removido_visitante else f'⚠️ Falha ao remover: {visitante_role.mention}'}",
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

        except Exception as e:
            logger.critical(
                f"[ERRO GERAL] Callback de verificação falhou para {member.name} (ID: {member.id}) no guild '{interaction.guild.name}' (ID: {interaction.guild.id})\n"
                f"Canal: {interaction.channel.name if interaction.channel else 'Desconhecido'} (ID: {interaction.channel.id if interaction.channel else 'N/A'})",
                exc_info=True
            )

            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "⚠️ O sistema de verificação está temporariamente indisponível. Por favor, tente novamente mais tarde.",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        "⚠️ O sistema de verificação está temporariamente indisponível. Por favor, tente novamente mais tarde.",
                        ephemeral=True
                    )
            except Exception as e_inner:
                logger.error(
                    f"Falha ao notificar usuário {member.name} sobre erro na verificação: {e_inner}", exc_info=True
                )


# --- CLASSE DO COG ---


class VerificacaoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Logger já definido no nível do módulo

    # --- COMANDO /verificar COM A VERIFICAÇÃO DE CARGO ---
    @app_commands.command(name="verificar", description="Envia o painel de verificação")
    # REMOVA ou COMENTE a linha abaixo:
    # @app_commands.checks.has_permissions(manage_messages=True)
    # ADICIONE a linha abaixo:
    @app_commands.check(check_user_has_mod_role)
    async def verificar(self, interaction: Interaction):
        """Envia o painel de verificação com botão"""
        try:
            embed = discord.Embed(
                title="🚀 Bem-vindo ao nosso servidor!",
                description="Para nossa segurança 🔒, clique no botão abaixo se você for um novo visitante para se verificar.✅",
                color=discord.Color.blue()
            )
            embed.set_footer(
                text="Apenas para usuários com o cargo 'Visitante'.")

            # Usa a classe VerificarView diretamente aqui
            await interaction.response.send_message(embed=embed, view=VerificarView())
            logger.info(
                f"Painel de verificação enviado por {interaction.user} no canal {interaction.channel.name}")
        except Exception as e:
            logger.error(f"Erro no comando /verificar: {e}", exc_info=True)
            # Tenta responder ao erro se possível
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Ocorreu um erro ao criar o painel.", ephemeral=True)
            else:
                try:
                    await interaction.followup.send("❌ Ocorreu um erro ao criar o painel.", ephemeral=True)
                except discord.NotFound:
                    logger.warning(
                        "Não foi possível enviar erro do /verificar (interação não encontrada).")

    # --- LISTENER on_member_join (Permanece igual) ---

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Envia mensagem de boas-vindas personalizada"""
        if member.bot:
            return
        try:
            # ... (Código do on_member_join como estava na versão anterior) ...
            channel_id_str = os.getenv("BOAS_VINDAS_ID")
            if not channel_id_str:
                logger.warning("BOAS_VINDAS_ID não definido no .env")
                return
            try:
                channel_id = int(channel_id_str)
            except ValueError:
                logger.error(
                    f"BOAS_VINDAS_ID ('{channel_id_str}') não é um ID numérico válido.")
                return
            channel = self.bot.get_channel(channel_id)
            if not channel:
                logger.warning(
                    f"Canal de Boas Vindas (ID: {channel_id}) não encontrado.")
                return

            regras_channel_mention = "📚・𝗥𝗘𝗚𝗥𝗔𝗦-𝗗𝗜𝗦𝗖𝗢𝗥𝗗"
            verificar_channel_mention = "✅・𝗩𝗲𝗿𝗶𝗳𝗶𝗰𝗮𝗿"
            regras_id = os.getenv("REGRAS_ID")
            verificar_id = os.getenv("VERIFICAR_ID")
            if regras_id:
                try:
                    regras_channel_mention = f"<#{int(regras_id)}>"
                except ValueError:
                    logger.warning(
                        f"REGRAS_ID ('{regras_id}') inválido, usando nome padrão.")
            if verificar_id:
                try:
                    verificar_channel_mention = f"<#{int(verificar_id)}>"
                except ValueError:
                    logger.warning(
                        f"VERIFICAR_ID ('{verificar_id}') inválido, usando nome padrão.")

            instagram_url = "https://www.instagram.com/jhonross.tv/"
            tiktok_url = "https://www.tiktok.com/@halionrp"

            embed = discord.Embed(
                title=f"🎉 BEM-VINDO À {member.guild.name}! 🌆",
                description=(
                    f"👋 Olá, {member.mention}! Bem-vindo(a)!\n\n"
                    "📜 **Primeiros passos:**\n"
                    f"• Leia as regras: {regras_channel_mention}\n"
                    f"• Faça a verificação: {verificar_channel_mention}\n\n"
                    "📱 **Siga-nos nas Redes Sociais:**\n"
                    f"• [Instagram]({instagram_url})\n"
                    f"• [TikTok]({tiktok_url})\n\n"
                    "🚀 Prepare-se para uma ótima experiência!\n\n"
                    f"**{member.guild.name}** – Sua jornada começa aqui!"
                ),
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )
            if member.display_avatar:
                embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"{member.guild.name}")

            await channel.send(embed=embed)
            logger.info(
                f"Mensagem de boas-vindas enviada para {member.name} ({member.id})")

        except Exception as e:
            logger.error(
                f"Erro em on_member_join (Boas Vindas): {e}", exc_info=True)

    # --- HANDLER DE ERRO DO COG ---
    async def cog_app_command_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        """Trata erros para todos os comandos de aplicativo neste Cog."""
        # Erro específico da nossa verificação de cargo
        # Adicionamos uma verificação para garantir que o erro veio do check correto
        if isinstance(error, app_commands.CheckFailure) and hasattr(error, 'check') and error.check == check_user_has_mod_role:
            logger.warning(
                f"Usuário {interaction.user} falhou na verificação de cargo para o comando '{interaction.command.name}'.")
            # Verifica se já respondeu (ex: defer falhou por permissão)
            if not interaction.response.is_done():
                await interaction.response.send_message("🚫 Você não possui o cargo necessário para usar este comando.", ephemeral=True)
            # Não usar followup aqui, pois a resposta inicial pode ter falhado
            return

        # Trata outros erros genéricos (opcional, pode deixar para um handler global se tiver)
        else:
            logger.error(
                f"Erro não tratado para '{interaction.command.name}' no VerificacaoCog por {interaction.user}: {error}", exc_info=True)
            error_message = "❌ Ocorreu um erro inesperado ao processar este comando."
            if not interaction.response.is_done():
                await interaction.response.send_message(error_message, ephemeral=True)
            else:
                try:
                    # Tenta followup se já houve defer bem-sucedido antes do erro
                    await interaction.followup.send(error_message, ephemeral=True)
                except discord.NotFound:
                    pass  # Ignora se a interação original sumiu

# --- FUNÇÃO SETUP (Registra a View persistente aqui também) ---


async def setup(bot):
    cog = VerificacaoCog(bot)
    await bot.add_cog(cog)
    # É crucial registrar a View persistente aqui ou no setup_hook do bot
    # Vamos garantir que ela só seja adicionada uma vez
    view_instance = VerificarView()
    # Verifica se uma view com o mesmo custom_id já foi adicionada
    # (Uma abordagem simples, pode ser aprimorada se tiver muitas views)
    found = False
    for existing_view in bot.persistent_views:
        if isinstance(existing_view, VerificarView):
            first_item = existing_view.children[0] if existing_view.children else None
            if first_item and hasattr(first_item, 'custom_id') and first_item.custom_id == "verificar_botao":
                found = True
                break
    if not found:
        bot.add_view(view_instance)
        logger.info("View VerificarView registrada para persistência.")
    else:
        logger.info(
            "View VerificarView já registrada, ignorando adição duplicada.")

    logger.info("Cog VerificacaoCog carregado com sucesso.")
