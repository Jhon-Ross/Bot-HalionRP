import discord
from discord.ext import commands
from discord import app_commands
import os
import logging
from datetime import datetime
import traceback
from typing import List, Set

# --- Início: Variáveis Globais e Carregamento de Configurações ---
MESSAGE_ID_FILE = "data/comunicados_message_id.txt"
COMUNICADOS_CHANNEL_ID = None
AVISOS_CHANNEL_ID = None  # Novo canal de avisos
ALLOWED_ROLE_IDS: Set[int] = set()

try:
    _channel_id_str = os.getenv("COMUNICADOS_ID")
    if _channel_id_str:
        COMUNICADOS_CHANNEL_ID = int(_channel_id_str)
    else:
        logging.error(
            "COMUNICADOS_ID não definido no .env! O comando /comunicados pode não funcionar.")
except (TypeError, ValueError):
    logging.error("COMUNICADOS_ID inválido no .env! Deve ser um número.")
    COMUNICADOS_CHANNEL_ID = None

# Novo: carregar o ID do canal AVISOS
try:
    _avisos_id_str = os.getenv("AVISOS_ID")
    if _avisos_id_str:
        AVISOS_CHANNEL_ID = int(_avisos_id_str)
    else:
        logging.warning("AVISOS_ID não definido no .env! O comando /comunicados não funcionará no canal de avisos.")
except (TypeError, ValueError):
    logging.error("AVISOS_ID inválido no .env! Deve ser um número.")
    AVISOS_CHANNEL_ID = None

_allowed_roles_str = os.getenv("ALLOWED_MOD_ROLE_IDS", "")
if _allowed_roles_str:
    try:
        ALLOWED_ROLE_IDS = {int(role_id.strip()) for role_id in _allowed_roles_str.split(
            ',') if role_id.strip()}
        if not ALLOWED_ROLE_IDS:
            logging.warning(
                "ALLOWED_MOD_ROLE_IDS está definido mas vazio ou contém apenas espaços/vírgulas.")
        else:
            logging.info(
                f"Carregados IDs de cargos permitidos para /comunicados: {ALLOWED_ROLE_IDS}")
    except ValueError:
        logging.error(
            "Erro ao converter ALLOWED_MOD_ROLE_IDS. Certifique-se de que são IDs numéricos separados por vírgula.")
        ALLOWED_ROLE_IDS = set()
else:
    logging.warning(
        "ALLOWED_MOD_ROLE_IDS não definido no .env. O comando /comunicados não terá restrição de cargo específica.")
# --- Fim: Variáveis Globais e Carregamento de Configurações ---


# --- Início: Função de Verificação de Permissão (check_if_user_has_allowed_role) ---
async def check_if_user_has_allowed_role(interaction: discord.Interaction) -> bool:
    """Verifica se o usuário possui algum dos cargos permitidos."""
    if not ALLOWED_ROLE_IDS:
        logging.error(
            f"Tentativa de uso de /comunicados por {interaction.user}, mas nenhum cargo permitido foi configurado ou carregado (ALLOWED_MOD_ROLE_IDS).")
        return False

    if not isinstance(interaction.user, discord.Member):
        logging.warning(
            f"Tentativa de uso de /comunicados por usuário fora de um servidor? User: {interaction.user}")
        return False

    user_role_ids = {role.id for role in interaction.user.roles}

    if user_role_ids.isdisjoint(ALLOWED_ROLE_IDS):
        logging.warning(
            f"Usuário {interaction.user} (ID: {interaction.user.id}) tentou usar /comunicados sem um cargo permitido. Cargos: {user_role_ids}")
        return False
    else:
        return True
# --- Fim: Função de Verificação de Permissão ---


# --- Início: Definição da Classe Cog 'CommunicationCog' ---
class CommunicationCog(commands.Cog):
    # --- Início: Método Construtor __init__ ---
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger(f"{__name__}")
        self.message_id = self._load_message_id()
        self.logger.info(
            f"Cog Communication carregado. ID da mensagem: {self.message_id}.")
    # --- Fim: Método Construtor __init__ ---

    # --- Início: Métodos Auxiliares (_ensure_data_dir, _load_message_id, _save_message_id, _get_comunicados_channel) ---
    def _ensure_data_dir(self):
        if not os.path.exists("data"):
            try:
                os.makedirs("data")
                self.logger.info("Diretório 'data' criado.")
            except OSError as e:
                self.logger.error(
                    f"Não foi possível criar o diretório 'data': {e}")
                return False
        return True

    def _load_message_id(self):
        if not self._ensure_data_dir():
            return None
        try:
            if os.path.exists(MESSAGE_ID_FILE):
                with open(MESSAGE_ID_FILE, "r") as f:
                    content = f.read().strip()
                    if content.isdigit():
                        return int(content)
                    else:
                        self.logger.warning(
                            f"Conteúdo inválido em {MESSAGE_ID_FILE}: '{content}'. Ignorando.")
                        self._save_message_id(None)
                        return None
            return None
        except Exception as e:
            self.logger.error(
                f"Erro ao carregar ID da mensagem de {MESSAGE_ID_FILE}: {e}")
            return None

    def _save_message_id(self, message_id: int | None):
        if not self._ensure_data_dir():
            return
        try:
            with open(MESSAGE_ID_FILE, "w") as f:
                if message_id:
                    f.write(str(message_id))
                    self.message_id = message_id
                    self.logger.info(
                        f"ID da mensagem {message_id} salvo em {MESSAGE_ID_FILE}.")
                else:
                    f.write("")
                    self.message_id = None
                    self.logger.info(
                        f"ID da mensagem removido de {MESSAGE_ID_FILE}.")
        except Exception as e:
            self.logger.error(
                f"Erro ao salvar ID da mensagem em {MESSAGE_ID_FILE}: {e}")

    async def _get_comunicados_channel(self) -> discord.TextChannel | None:
        if not COMUNICADOS_CHANNEL_ID:
            self.logger.error(
                "ID do canal de comunicados não está configurado.")
            return None
        channel = self.bot.get_channel(COMUNICADOS_CHANNEL_ID)
        if not channel:
            try:
                channel = await self.bot.fetch_channel(COMUNICADOS_CHANNEL_ID)
            except (discord.NotFound, discord.Forbidden) as e:
                self.logger.error(
                    f"Não foi possível encontrar ou acessar o canal de comunicados (ID: {COMUNICADOS_CHANNEL_ID}): {e}")
                return None
            except Exception as e:
                self.logger.error(
                    f"Erro ao buscar o canal de comunicados: {e}")
                return None
        if not isinstance(channel, discord.TextChannel):
            self.logger.error(
                f"O ID {COMUNICADOS_CHANNEL_ID} não pertence a um canal de texto.")
            return None
        return channel
    # --- Fim: Métodos Auxiliares ---

    # --- Início: Comando de Aplicação /comunicados ---
    @app_commands.command(name="comunicados", description="Envia ou atualiza o comunicado oficial no canal designado.")
    @app_commands.describe(texto="O conteúdo principal do comunicado.")
    @app_commands.check(check_if_user_has_allowed_role)
    async def set_comunicado(self, interaction: discord.Interaction, texto: str):
        """Comando para definir ou atualizar a mensagem de comunicado."""
        await interaction.response.defer(ephemeral=True, thinking=True)

        # Permitir uso apenas nos canais COMUNICADOS ou AVISOS
        canais_permitidos = set()
        if COMUNICADOS_CHANNEL_ID:
            canais_permitidos.add(COMUNICADOS_CHANNEL_ID)
        if AVISOS_CHANNEL_ID:
            canais_permitidos.add(AVISOS_CHANNEL_ID)

        if not canais_permitidos:
            await interaction.followup.send("❌ Nenhum canal permitido está configurado no bot.", ephemeral=True)
            return

        if interaction.channel_id not in canais_permitidos:
            canais_mencoes = [f"<#{cid}>" for cid in canais_permitidos]
            await interaction.followup.send(f"⚠️ Este comando só pode ser usado nos canais permitidos: {', '.join(canais_mencoes)}.", ephemeral=True)
            return

        # Determinar o canal alvo
        if interaction.channel_id == COMUNICADOS_CHANNEL_ID:
            target_channel = await self._get_comunicados_channel()
        elif interaction.channel_id == AVISOS_CHANNEL_ID:
            target_channel = interaction.channel  # Já está no canal correto
        else:
            target_channel = None

        if not target_channel:
            await interaction.followup.send("❌ Não foi possível encontrar ou acessar o canal configurado.", ephemeral=True)
            return

        embed = discord.Embed(
            title="📢 Comunicado Oficial",
            description=texto,
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        embed.set_footer(
            text=f"Atualizado por: {interaction.user.display_name}")

        # Se for no canal de comunicados, tenta editar a mensagem antiga
        if interaction.channel_id == COMUNICADOS_CHANNEL_ID:
            message_to_edit = None
            if self.message_id:
                try:
                    message_to_edit = await target_channel.fetch_message(self.message_id)
                    self.logger.info(
                        f"Mensagem de comunicado {self.message_id} encontrada para edição.")
                except discord.NotFound:
                    self.logger.warning(
                        f"Mensagem de comunicado {self.message_id} não encontrada. Enviando nova.")
                    self._save_message_id(None)
                    self.message_id = None
                except discord.Forbidden:
                    self.logger.error(
                        f"Sem permissão para buscar a mensagem {self.message_id} no canal {target_channel.name}.")
                    await interaction.followup.send("❌ O bot não tem permissão para ler o histórico de mensagens no canal.", ephemeral=True)
                    return
                except Exception as e:
                    self.logger.error(
                        f"Erro inesperado ao buscar mensagem {self.message_id}: {e}\n{traceback.format_exc()}")
                    await interaction.followup.send("❌ Ocorreu um erro ao tentar buscar a mensagem anterior.", ephemeral=True)
                    return

            try:
                if message_to_edit:
                    await message_to_edit.edit(embed=embed)
                    self.logger.info(
                        f"Mensagem de comunicado {self.message_id} atualizada por {interaction.user}.")
                    await interaction.followup.send("✅ Comunicado atualizado com sucesso!", ephemeral=True)
                else:
                    new_message = await target_channel.send(embed=embed)
                    self._save_message_id(new_message.id)
                    self.logger.info(
                        f"Nova mensagem de comunicado {self.message_id} enviada por {interaction.user}.")
                    await interaction.followup.send("✅ Comunicado enviado com sucesso!", ephemeral=True)

            except discord.Forbidden:
                self.logger.error(
                    f"Sem permissão para enviar/editar mensagens no canal {target_channel.name}.")
                await interaction.followup.send(f"❌ O bot não tem permissão para {'editar' if message_to_edit else 'enviar'} mensagens no canal {target_channel.mention}.", ephemeral=True)
            except discord.HTTPException as e:
                self.logger.error(
                    f"Erro HTTP ao enviar/editar comunicado: {e}\n{traceback.format_exc()}")
                await interaction.followup.send("❌ Ocorreu um erro de comunicação com o Discord.", ephemeral=True)
            except Exception as e:
                self.logger.error(
                    f"Erro inesperado ao enviar/editar comunicado: {e}\n{traceback.format_exc()}")
                await interaction.followup.send("❌ Ocorreu um erro inesperado.", ephemeral=True)
        # Se for no canal AVISOS, apenas envia a embed
        elif interaction.channel_id == AVISOS_CHANNEL_ID:
            try:
                await target_channel.send(embed=embed)
                await interaction.followup.send("✅ Comunicado enviado com sucesso no canal de avisos!", ephemeral=True)
            except discord.Forbidden:
                self.logger.error(
                    f"Sem permissão para enviar mensagens no canal {target_channel.name}.")
                await interaction.followup.send(f"❌ O bot não tem permissão para enviar mensagens no canal {target_channel.mention}.", ephemeral=True)
            except discord.HTTPException as e:
                self.logger.error(
                    f"Erro HTTP ao enviar comunicado: {e}\n{traceback.format_exc()}")
                await interaction.followup.send("❌ Ocorreu um erro de comunicação com o Discord.", ephemeral=True)
            except Exception as e:
                self.logger.error(
                    f"Erro inesperado ao enviar comunicado: {e}\n{traceback.format_exc()}")
                await interaction.followup.send("❌ Ocorreu um erro inesperado.", ephemeral=True)
    # --- Fim: Comando de Aplicação /comunicados ---

    # --- Início: Tratador de Erros para /comunicados (on_comunicado_error) ---
    @set_comunicado.error
    async def on_comunicado_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            if not ALLOWED_ROLE_IDS:
                await interaction.response.send_message("❌ Erro de configuração: Nenhum cargo permitido foi definido para este comando. Contate um administrador.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Você não possui um dos cargos necessários para usar este comando.", ephemeral=True)
        else:
            self.logger.error(
                f"Erro inesperado no comando /comunicados ou seus checks: {error}\n{traceback.format_exc()}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ Ocorreu um erro inesperado ao processar o comando.", ephemeral=True)
                else:
                    await interaction.followup.send("❌ Ocorreu um erro inesperado ao processar o comando.", ephemeral=True)
            except discord.InteractionResponded:
                self.logger.warning(
                    "Não foi possível enviar mensagem de erro para /comunicados pois a interação já foi respondida.")
            except Exception as e_resp:
                self.logger.error(
                    f"Erro ao tentar enviar mensagem de erro para /comunicados: {e_resp}")
    # --- Fim: Tratador de Erros para /comunicados ---

# --- Fim: Definição da Classe Cog 'CommunicationCog' ---


# --- Início: Função setup (Carregamento do Cog) ---
async def setup(bot: commands.Bot):
    if COMUNICADOS_CHANNEL_ID is None:
        logging.warning(
            "Cog Communication não será carregado pois COMUNICADOS_ID está ausente ou inválido.")
        return

    if not ALLOWED_ROLE_IDS:
        logging.warning(
            "ALLOWED_MOD_ROLE_IDS está vazio ou ausente no .env. O comando /comunicados ficará inacessível até que seja configurado.")

    cog = CommunicationCog(bot)
    await bot.add_cog(cog)
    logging.info("Cog Communication adicionado com sucesso.")
# --- Fim: Função setup (Carregamento do Cog) ---

# --- Fim do Arquivo: cogs/communication.py ---
