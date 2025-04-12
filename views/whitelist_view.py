import discord
import asyncio
import logging
import re
import os
from discord.ui import View, Button, button
from datetime import datetime, timedelta, timezone

# Try-except para importações (sem alterações)
try:
    import sys
    sys.path.append(os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..')))
    from handlers.questionnaire import start_questionnaire, cooldowns, COOLDOWN_MINUTES

except ImportError as e:
    logging.critical(
        f"Falha crítica ao importar de handlers.questionnaire: {e}. Verifique a estrutura de pastas e o sys.path.")

    async def start_questionnaire(*args, **kwargs):
        logging.error(
            "Função start_questionnaire FALTANDO devido a erro de import.")
    cooldowns = {}
    COOLDOWN_MINUTES = 30


logger = logging.getLogger(__name__)

# Função sanitize_channel_name (sem alterações)


def sanitize_channel_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r'[\s.]+', '-', name)
    name = re.sub(r'[^a-z0-9_-]+', '', name)
    name = re.sub(r'-{2,}', '-', name)
    name = name.strip('-_')
    if not name:
        return "user"
    return name


class WhitelistView(View):
    def __init__(self):
        # timeout=None é essencial para persistência!
        super().__init__(timeout=None)

    @button(label="Quero fazer whitelist", style=discord.ButtonStyle.success, custom_id="start_whitelist")
    async def start_whitelist_button(self, interaction: discord.Interaction, button_obj: Button):
        member = interaction.user
        guild = interaction.guild
        now = datetime.now(timezone.utc)

        # ----- ETAPA 1: Deferir -----
        # Deferir cedo para evitar "Interaction Failed"
        await interaction.response.defer(ephemeral=True, thinking=True)

        # ----- ETAPA 2: Verificar Cooldown -----
        if member.id in cooldowns and cooldowns[member.id] > now:
            remaining_delta = cooldowns[member.id] - now
            remaining_seconds = remaining_delta.total_seconds()
            # Arredonda para cima os minutos restantes
            remaining_minutes = int(
                remaining_seconds // 60) + (1 if remaining_seconds % 60 > 0 else 0)
            logger.info(
                f"Usuário {member} (ID: {member.id}) tentou whitelist mas está em cooldown por ~{remaining_minutes} min.")
            # Envia a mensagem de cooldown usando followup, pois já deferimos
            await interaction.followup.send(
                f"❌ Você ainda está em cooldown! Por favor, aguarde mais **{remaining_minutes} minuto(s)** para tentar novamente.",
                ephemeral=True
            )
            return

        whitelist_channel = None
        analise_role = None

        try:
            # ----- ETAPA 3: Verificar Canal Existente (MODIFICADO) -----
            logger.debug(
                f"Iniciando verificação de canal existente para {member} (ID: {member.id})")
            # String exata que procuramos no tópico
            check_id_string = f"CheckID: wl-{member.id}"
            existing_channel = None

            # Otimização: Procurar apenas na categoria "WHITELIST" se ela existir
            target_category = discord.utils.get(
                guild.categories, name="WHITELIST")
            search_scope = target_category.text_channels if target_category else guild.text_channels
            logger.debug(
                f"Escopo da busca: {'Categoria WHITELIST' if target_category else 'Todos os canais de texto'}")

            for channel in search_scope:
                # Verifica se o canal tem tópico e se o tópico contém nossa string de ID
                if channel.topic and check_id_string in channel.topic:
                    existing_channel = channel
                    logger.info(
                        f"Canal existente encontrado para {member.id} pelo tópico: {channel.name} (ID: {channel.id})")
                    break  # Encontrou, não precisa continuar procurando

            # Se encontrou um canal existente pelo tópico...
            if existing_channel:
                logger.warning(
                    f"Tentativa de iniciar whitelist por {member} (ID: {member.id}), mas canal '{existing_channel.name}' (ID: {existing_channel.id}) já existe (verificado via tópico).")
                # Envia a mensagem amigável informando o usuário
                await interaction.followup.send(
                    f"❗ Ops! Parece que você já tem um processo de whitelist em andamento no canal {existing_channel.mention}. "
                    "Por favor, conclua o processo lá ou, se precisar de ajuda, mencione a staff no canal.",
                    ephemeral=True
                )
                return  # Interrompe a execução aqui

            logger.debug(
                f"Nenhum canal existente encontrado para {member.id} via tópico.")

            # ----- ETAPA 4: ATRIBUIR CARGO DE ANÁLISE (Sem alterações lógicas) -----
            analise_role_id_str = os.getenv("ANALISE_ID")
            if not analise_role_id_str:
                logger.critical(
                    "Variável de ambiente ANALISE_ID não definida!")
                await interaction.followup.send("❌ Erro de configuração do bot: Cargo 'Análise' não definido. Avise a staff.", ephemeral=True)
                return

            try:
                analise_role_id = int(analise_role_id_str)
                analise_role = guild.get_role(analise_role_id)

                if not analise_role:
                    logger.error(
                        f"Cargo 'Análise' com ID {analise_role_id} não encontrado.")
                    await interaction.followup.send(f"❌ Erro de configuração: Cargo 'Análise' (ID: {analise_role_id}) não existe. Avise a staff.", ephemeral=True)
                    return

                if analise_role not in member.roles:
                    logger.info(
                        f"Atribuindo cargo '{analise_role.name}' para {member} (ID: {member.id}).")
                    await member.add_roles(analise_role, reason="Iniciou processo de Whitelist")
                    logger.info(
                        f"Cargo '{analise_role.name}' atribuído com sucesso para {member}.")
                else:
                    logger.info(
                        f"Membro {member} já possui o cargo '{analise_role.name}'.")

            except ValueError:
                logger.error(f"ANALISE_ID ('{analise_role_id_str}') inválido.")
                await interaction.followup.send("❌ Erro de configuração: ID do cargo 'Análise' inválido. Avise a staff.", ephemeral=True)
                return
            except discord.Forbidden:
                logger.error(
                    f"Sem permissão para adicionar cargo '{analise_role.name if analise_role else analise_role_id}' para {member}.")
                await interaction.followup.send("⚠️ Não foi possível atribuir o cargo 'Análise' (verifique permissões do bot), mas o processo continuará.", ephemeral=True)
            except Exception as e_role:
                logger.error(
                    f"Erro inesperado ao atribuir cargo 'Análise' para {member}: {e_role}", exc_info=True)
                await interaction.followup.send("⚠️ Erro ao atribuir cargo 'Análise', mas o processo continuará.", ephemeral=True)

            # ----- ETAPA 5: Preparar e Criar o Canal (Adicionado 'topic' explicitamente) -----
            sanitized_username = sanitize_channel_name(member.display_name)
            # Limita o nome para evitar erros de comprimento do Discord
            max_name_len = 100
            base_name = f"wl-{sanitized_username}"
            # Pega os últimos 4 digitos do ID para desambiguação
            suffix = f"-{str(member.id)[-4:]}"
            available_len = max_name_len - len(suffix)
            display_channel_name = f"{base_name[:available_len]}{suffix}"

            logger.info(
                f"Preparando para criar canal '{display_channel_name}' para {member} (ID: {member.id}).")

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                # Permissões básicas
                member: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
                guild.me: discord.PermissionOverwrite(
                    # Permissões para o bot
                    read_messages=True, send_messages=True, manage_channels=True, manage_messages=True, embed_links=True)
            }

            # Usa a categoria encontrada anteriormente ou None se não existir
            category_to_use = target_category  # Reutiliza a variável

            # **IMPORTANTE: Definir o TÓPICO na criação**
            # Inclui o CheckID
            channel_topic = f"Whitelist para {member.display_name} ({member.id}) | {check_id_string}"

            whitelist_channel = await guild.create_text_channel(
                name=display_channel_name,
                overwrites=overwrites,
                category=category_to_use,  # Usa a categoria encontrada
                topic=channel_topic  # Define o tópico aqui!
            )
            logger.info(
                f"Canal '{whitelist_channel.name}' criado com sucesso para {member} com tópico definido.")

            # ----- ETAPA 6: Informar Usuário e Iniciar Questionário -----
            confirmation_message = f"✅ Seu canal de whitelist foi criado: {whitelist_channel.mention}"
            if analise_role and analise_role in member.roles:  # Verifica se o cargo foi realmente adicionado
                confirmation_message += " e o cargo de Análise foi atribuído!"
            else:
                confirmation_message += "."

            await interaction.followup.send(confirmation_message, ephemeral=True)

            # Inicia o questionário no novo canal
            await start_questionnaire(member, whitelist_channel, interaction.client)

        # ----- Blocos Except (sem alterações lógicas significativas, apenas garantia de followup) -----
        except discord.Forbidden as e:
            # Forbidden pode ser da criação do canal ou da remoção do cargo
            error_context = "criar canal" if not whitelist_channel else "remover cargo após falha"
            logger.error(
                f"Erro de PERMISSÃO ao tentar {error_context} para {member}. Detalhes: {e}", exc_info=True)
            try:
                # Usa followup pois a interação original já foi respondida com defer
                await interaction.followup.send(f"❌ **Erro Crítico:** Permissão negada ao {error_context}. Contate um admin.", ephemeral=True)
            except discord.NotFound:
                logger.warning(
                    f"Followup de erro (Forbidden {error_context}) falhou para {member}.")

            # Tentar remover o cargo se foi dado e a criação falhou
            if not whitelist_channel and analise_role and analise_role in member.roles:
                try:
                    await member.remove_roles(analise_role, reason="Falha na criação do canal de Whitelist")
                    logger.info(
                        f"Cargo '{analise_role.name}' removido de {member} devido à falha na criação do canal.")
                except Exception as e_rem:
                    logger.error(
                        f"Não foi possível remover cargo de {member} após falha na criação do canal: {e_rem}")

        except ImportError:  # Erro na importação do questionário
            logger.critical(
                "Erro fatal: Falha na importação de 'handlers.questionnaire'.")
            try:
                await interaction.followup.send("❌ **Erro Interno do Bot:** Falha ao iniciar whitelist (módulo ausente). Avise a staff.", ephemeral=True)
            except discord.NotFound:
                logger.warning(
                    f"Followup de erro (ImportError) falhou para {member}.")

        except Exception as e:  # Captura geral para outros erros
            logger.error(
                f"Erro inesperado durante setup da whitelist para {member}: {e}", exc_info=True)
            try:
                await interaction.followup.send("❌ Erro inesperado durante o processo. Tente novamente mais tarde ou contate a staff.", ephemeral=True)
            except discord.NotFound:
                logger.warning(
                    f"Followup de erro (Geral Setup) falhou para {member}.")

            # Limpeza em caso de erro após criação parcial
            if whitelist_channel:  # Se o canal chegou a ser criado
                try:
                    await whitelist_channel.delete(reason="Falha inesperada no setup da whitelist")
                    logger.info(
                        f"Canal {whitelist_channel.name} deletado devido a erro no setup.")
                except Exception as e_del:
                    logger.error(
                        f"Não foi possível deletar o canal {whitelist_channel.name} após erro no setup: {e_del}")
            # Tenta remover o cargo se foi dado e algo deu errado
            if analise_role and analise_role in member.roles:
                try:
                    await member.remove_roles(analise_role, reason="Falha no setup da Whitelist")
                    logger.info(
                        f"Cargo '{analise_role.name}' removido de {member} devido à falha no setup.")
                except Exception as e_rem:
                    logger.error(
                        f"Não foi possível remover cargo de {member} após falha no setup: {e_rem}")
