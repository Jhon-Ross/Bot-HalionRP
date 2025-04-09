import discord
import asyncio
import logging
import re
import os  # <<< Adicionar import OS
from discord.ui import View, Button, button
from datetime import datetime, timedelta, timezone

try:
    import sys
    # Ajuste este path se necessário conforme sua estrutura de projeto
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
        super().__init__(timeout=None)

    @button(label="Quero fazer whitelist", style=discord.ButtonStyle.success, custom_id="start_whitelist")
    async def start_whitelist_button(self, interaction: discord.Interaction, button_obj: Button):
        member = interaction.user
        guild = interaction.guild
        now = datetime.now(timezone.utc)

        # ----- ETAPA 1: Deferir -----
        await interaction.response.defer(ephemeral=True, thinking=True)

        # ----- ETAPA 2: Verificar Cooldown -----
        if member.id in cooldowns and cooldowns[member.id] > now:
            # ... (código de tratamento de cooldown - sem alterações) ...
            remaining_delta = cooldowns[member.id] - now
            remaining_seconds = remaining_delta.total_seconds()
            remaining_minutes = int(
                remaining_seconds // 60) + (1 if remaining_seconds % 60 > 0 else 0)
            logger.info(
                f"Usuário {member} (ID: {member.id}) tentou whitelist mas está em cooldown por ~{remaining_minutes} min.")
            await interaction.followup.send(
                f"❌ Você ainda está em cooldown! Por favor, aguarde mais **{remaining_minutes} minuto(s)** para tentar novamente.",
                ephemeral=True
            )
            return

        whitelist_channel = None
        analise_role = None  # Variável para guardar o objeto Role

        try:
            # ----- ETAPA 3: Verificar Canal Existente -----
            internal_check_name = f"wl-{member.id}"
            existing_channel = discord.utils.get(
                guild.text_channels, name=internal_check_name)

            if existing_channel:
                # ... (código de tratamento de canal existente - sem alterações) ...
                await interaction.followup.send(
                    f"❗ Você já tem um canal de whitelist aberto: {existing_channel.mention}. Conclua ou peça ajuda à staff.",
                    ephemeral=True
                )
                logger.warning(
                    f"Tentativa de iniciar whitelist por {member} (ID: {member.id}), mas canal {existing_channel.name} (verificado por ID) já existe.")
                return

            # ----- ETAPA 4: ATRIBUIR CARGO DE ANÁLISE -----
            analise_role_id_str = os.getenv("ANALISE_ID")
            if not analise_role_id_str:
                logger.critical(
                    "Variável de ambiente ANALISE_ID não definida no .env! Não é possível atribuir o cargo.")
                # Informar o usuário sobre o erro de configuração é importante
                await interaction.followup.send("❌ Erro de configuração do bot: Cargo 'Análise' não definido. Avise a staff.", ephemeral=True)
                return  # Interrompe se o ID não estiver configurado

            try:
                analise_role_id = int(analise_role_id_str)
                analise_role = guild.get_role(analise_role_id)

                if not analise_role:
                    logger.error(
                        f"O cargo 'Análise' com ID {analise_role_id} não foi encontrado no servidor {guild.name}.")
                    await interaction.followup.send(f"❌ Erro de configuração do bot: O cargo 'Análise' (ID: {analise_role_id}) não existe neste servidor. Avise a staff.", ephemeral=True)
                    return  # Interrompe se o cargo não existe

                # Tenta adicionar o cargo
                if analise_role not in member.roles:  # Evita tentar adicionar se já tiver
                    logger.info(
                        f"Atribuindo cargo '{analise_role.name}' para {member} (ID: {member.id}).")
                    await member.add_roles(analise_role, reason="Iniciou processo de Whitelist")
                    logger.info(
                        f"Cargo '{analise_role.name}' atribuído com sucesso para {member}.")
                else:
                    logger.info(
                        f"Membro {member} já possui o cargo '{analise_role.name}'.")

            except ValueError:
                logger.error(
                    f"O valor de ANALISE_ID ('{analise_role_id_str}') no .env não é um número de ID válido.")
                await interaction.followup.send("❌ Erro de configuração do bot: ID do cargo 'Análise' inválido. Avise a staff.", ephemeral=True)
                return  # Interrompe se o ID for inválido
            except discord.Forbidden:
                logger.error(
                    f"Sem permissão para adicionar o cargo '{analise_role.name if analise_role else analise_role_id}' para {member}. Verifique as permissões de 'Manage Roles'.")
                # Decide se continua mesmo sem conseguir dar o cargo, ou para. Vamos continuar, mas avisar.
                await interaction.followup.send("⚠️ Não foi possível atribuir o cargo 'Análise' (verifique permissões do bot), mas o processo de whitelist continuará.", ephemeral=True)
                # Não retorna aqui, permite continuar sem o cargo. Se preferir parar, adicione 'return'
            except Exception as e_role:
                logger.error(
                    f"Erro inesperado ao tentar atribuir cargo 'Análise' para {member}: {e_role}", exc_info=True)
                await interaction.followup.send("⚠️ Ocorreu um erro ao tentar atribuir o cargo 'Análise', mas o processo de whitelist continuará.", ephemeral=True)
                # Não retorna aqui, permite continuar.

            # ----- ETAPA 5: Preparar e Criar o Canal -----
            sanitized_username = sanitize_channel_name(member.display_name)
            last_4_id = str(member.id)[-4:]
            display_channel_name = f"wl-{sanitized_username[:80]}-{last_4_id}"

            logger.info(
                f"Tentando criar canal '{display_channel_name}' para {member} (ID: {member.id})...")

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                guild.me: discord.PermissionOverwrite(
                    read_messages=True, send_messages=True, manage_messages=True, embed_links=True)
            }
            category = discord.utils.get(
                guild.categories, name="WHITELIST")  # Opcional

            whitelist_channel = await guild.create_text_channel(
                name=display_channel_name,
                overwrites=overwrites,
                category=category,  # Remova se não usar
                topic=f"WL para {member.display_name} ({member.id}) | CheckID: {internal_check_name}"
            )
            logger.info(
                f"Canal '{whitelist_channel.name}' criado com sucesso para {member}.")

            # ----- ETAPA 6: Informar Usuário e Iniciar Questionário -----
            # Envia a confirmação APÓS todo o setup (cargo + canal)
            await interaction.followup.send(
                f"✅ Seu canal de whitelist foi criado: {whitelist_channel.mention}"
                # Mensagem dinâmica
                f"{' e o cargo de Análise foi atribuído!' if analise_role and analise_role in member.roles else '.'}",
                ephemeral=True
            )

            await start_questionnaire(member, whitelist_channel, interaction.client)

        except discord.Forbidden as e:
            # Este Forbidden é provavelmente da criação do CANAL
            logger.error(
                f"Erro de PERMISSÃO ao tentar criar canal '{display_channel_name}' para {member}. Detalhes: {e}", exc_info=True)
            try:
                await interaction.followup.send("❌ **Erro Crítico:** Permissão negada ao criar canal. Contate um admin.", ephemeral=True)
            except discord.NotFound:
                logger.warning(
                    f"Followup erro (Forbidden Canal) falhou para {member}.")
            # Tenta remover o cargo se ele foi dado e a criação do canal falhou
            if analise_role and analise_role in member.roles:
                try:
                    await member.remove_roles(analise_role, reason="Falha na criação do canal de Whitelist")
                    logger.info(
                        f"Cargo '{analise_role.name}' removido de {member} devido à falha na criação do canal.")
                except Exception as e_rem:
                    logger.error(
                        f"Não foi possível remover cargo de {member} após falha na criação do canal: {e_rem}")

        except ImportError:
            logger.critical(
                "Erro fatal: Falha na importação de 'handlers.questionnaire'.")
            try:
                await interaction.followup.send("❌ **Erro Interno do Bot:** Falha ao iniciar whitelist. Avise a staff.", ephemeral=True)
            except discord.NotFound:
                logger.warning(
                    f"Followup erro (ImportError) falhou para {member}.")

        except Exception as e:
            logger.error(
                f"Erro inesperado durante setup da whitelist para {member}: {e}", exc_info=True)
            try:
                await interaction.followup.send("❌ Erro inesperado no setup. Tente mais tarde ou contate a staff.", ephemeral=True)
            except discord.NotFound:
                logger.warning(
                    f"Followup erro (Geral Setup) falhou para {member}.")
            # Tenta limpar canal se criado
            if whitelist_channel:
                try:
                    await whitelist_channel.delete(reason="Falha inesperada no setup")
                    logger.info(
                        f"Canal {whitelist_channel.name} deletado - erro setup.")
                except Exception as e_del:
                    logger.error(
                        f"Não deletou canal {whitelist_channel.name} após erro setup: {e_del}")
            # Tenta remover o cargo se foi dado e algo deu errado depois
            if analise_role and analise_role in member.roles:
                try:
                    await member.remove_roles(analise_role, reason="Falha no setup da Whitelist")
                    logger.info(
                        f"Cargo '{analise_role.name}' removido de {member} devido à falha no setup.")
                except Exception as e_rem:
                    logger.error(
                        f"Não foi possível remover cargo de {member} após falha no setup: {e_rem}")
