import discord
from discord.ext import commands
from discord import app_commands
import os
import logging
from datetime import datetime, timezone
import asyncio
# import csv # Removido
import io

# --- Funções Auxiliares ---


def has_allowed_role(user: discord.Member, allowed_ids: list[int]) -> bool:
    if not allowed_ids:
        return False
    user_role_ids = {role.id for role in user.roles}
    return any(role_id in user_role_ids for role_id in allowed_ids)

# REMOVIDA: Função generate_transcript_csv

# --- Views Persistentes ---


class TicketControlView(discord.ui.View):
    def __init__(self, cog_instance):
        super().__init__(timeout=None)
        self.cog = cog_instance

    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket_button")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        channel = interaction.channel
        user = interaction.user

        if not isinstance(user, discord.Member) or not isinstance(channel, discord.TextChannel):
            try:
                await interaction.response.send_message("Ocorreu um erro.", ephemeral=True)
            except discord.HTTPException:
                pass
            return

        if not has_allowed_role(user, self.cog.allowed_mod_role_ids):
            await interaction.response.send_message("Apenas membros da equipe designada podem fechar este ticket.", ephemeral=True)
            return

        if not self.cog.ticket_category_id or not self.cog.allowed_mod_role_ids:
            await interaction.response.send_message("Erro crítico na configuração do bot.", ephemeral=True)
            return

        # Defer inicial
        await interaction.response.defer(ephemeral=True, thinking=True)

        # --- Buscar Histórico para Transcript ---
        messages = []
        try:
            async for message in channel.history(limit=None, oldest_first=True):
                messages.append(message)
            logging.info(
                f"Histórico de {len(messages)} mensagens obtido para {channel.name}.")
        except discord.Forbidden:
            logging.error(
                f"Sem permissão para ler histórico do canal {channel.id} para transcript.")
            messages = None  # Indica que não foi possível obter o histórico
        except discord.HTTPException as e:
            logging.error(
                f"Erro HTTP ao buscar histórico do canal {channel.id}: {e}")
            messages = None
        except Exception as e:
            logging.exception(
                f"Erro inesperado ao buscar histórico do canal {channel.id}:")
            messages = None

        # --- Enviar Embed Inicial de Fechamento ---
        closed_log_channel = None
        if self.cog.closed_ticket_log_channel_id:
            closed_log_channel = guild.get_channel(
                self.cog.closed_ticket_log_channel_id)
            # Validações do canal de log
            if not closed_log_channel or not isinstance(closed_log_channel, discord.TextChannel):
                logging.warning(
                    f"Canal de log de tickets fechados (ID: {self.cog.closed_ticket_log_channel_id}) inválido ou não encontrado.")
                closed_log_channel = None
            elif not closed_log_channel.permissions_for(guild.me).send_messages:
                logging.warning(
                    f"Sem permissão de Enviar Mensagens no canal de log {closed_log_channel.name}.")
                closed_log_channel = None

        # Cria o Embed
        embed_log_closed = discord.Embed(
            title="🎫 Ticket Fechado",
            description=f"O ticket `#{channel.name}` foi fechado.",
            color=discord.Color.dark_red(),
            timestamp=datetime.now(timezone.utc)
        )
        embed_log_closed.add_field(
            name="Fechado por", value=user.mention, inline=True)
        # Lógica para buscar criador
        creator_mention = "Não identificado"
        creator_id = "N/A"
        if channel.name.startswith("ticket-"):
            try:
                creator_id = channel.name.split('-')[-1]
                user_id_int = int(creator_id)
                ticket_creator = await guild.fetch_member(user_id_int)
                creator_mention = ticket_creator.mention if ticket_creator else f"ID: {creator_id} (Não enc.)"
            except Exception:
                pass
        embed_log_closed.add_field(
            name="Criado por", value=creator_mention, inline=True)
        embed_log_closed.add_field(
            name="ID do Criador", value=f"`{creator_id}`", inline=False)
        embed_log_closed.add_field(
            name="ID do Canal", value=f"`{channel.id}`", inline=False)
        embed_log_closed.set_footer(text="Horário do Fechamento (UTC)")

        # Envia o Embed inicial (se o canal de log for válido)
        embed_sent_ok = False
        if closed_log_channel:
            try:
                await closed_log_channel.send(embed=embed_log_closed)
                logging.info(
                    f"Embed de fechamento do ticket {channel.name} enviado para {closed_log_channel.name}.")
                embed_sent_ok = True
            except discord.Forbidden:
                logging.error(
                    f"Sem permissão para enviar embed de fechamento para {closed_log_channel.name}.")
            except discord.HTTPException as e:
                logging.error(
                    f"Erro HTTP ao enviar embed de fechamento para {closed_log_channel.name}: {e}")
            except Exception as e:
                logging.exception(
                    f"Erro inesperado ao enviar embed de fechamento para {closed_log_channel.name}:")

        # --- MODIFICADO: Enviar Transcript como Mensagens ---
        transcript_sent_ok = False
        # Só envia transcript se o embed foi ok e o histórico foi pego
        if closed_log_channel and messages is not None and embed_sent_ok:
            if not messages:
                try:
                    await closed_log_channel.send("*Nenhuma mensagem encontrada no ticket para transcrever.*")
                    transcript_sent_ok = True  # Considera sucesso se não havia nada a enviar
                except Exception as e:
                    logging.error(
                        f"Erro ao enviar msg 'Nenhuma mensagem' para {closed_log_channel.name}: {e}")
            else:
                transcript_chunks = []
                current_chunk = "```\n--- Transcrição do Ticket ---\n\n"  # Inicia bloco de código
                char_limit = 1950  # Limite seguro por chunk

                for msg in messages:
                    # Formata a linha da mensagem
                    aware_dt = msg.created_at.astimezone(timezone.utc)
                    timestamp = aware_dt.strftime("%d/%m/%Y %H:%M:%S UTC")
                    author = str(msg.author)
                    # Evita quebrar o bloco de código com ``` dentro da msg
                    content = msg.clean_content.replace(
                        '`', '\\`') if msg.clean_content else "(mensagem vazia)"
                    attachments_str = ""
                    if msg.attachments:
                        # Lista apenas nomes de anexos
                        attachments_list = [
                            f"[Anexo: {att.filename}]" for att in msg.attachments]
                        attachments_str = "\n  " + \
                            "\n  ".join(attachments_list)

                    # Simplifica embeds para texto
                    embeds_str = ""
                    if msg.embeds:
                        embeds_str = f"\n  [Embed: {msg.embeds[0].title if msg.embeds[0].title else '(sem título)'}]"

                    formatted_line = f"[{timestamp}] {author}:\n  {content}{attachments_str}{embeds_str}\n\n"

                    # Verifica tamanho do chunk
                    if len(current_chunk) + len(formatted_line) > char_limit:
                        # Fecha chunk atual e inicia novo
                        current_chunk += "```"
                        transcript_chunks.append(current_chunk)
                        current_chunk = "```\n"  # Começa novo bloco

                    current_chunk += formatted_line

                # Adiciona último chunk
                current_chunk += "--- Fim da Transcrição ---\n```"
                transcript_chunks.append(current_chunk)

                # Envia os chunks
                logging.info(
                    f"Enviando transcrição de {channel.name} em {len(transcript_chunks)} chunks para {closed_log_channel.name}...")
                all_chunks_sent = True
                try:
                    for i, chunk in enumerate(transcript_chunks):
                        await closed_log_channel.send(chunk)
                        logging.debug(
                            f"Chunk {i+1}/{len(transcript_chunks)} enviado para {closed_log_channel.name}.")
                        # Delay entre mensagens para evitar rate limit
                        await asyncio.sleep(0.7)
                    transcript_sent_ok = True
                    logging.info(
                        f"Transcrição completa de {channel.name} enviada com sucesso.")
                except discord.Forbidden:
                    logging.error(
                        f"Sem permissão para enviar chunks da transcript para {closed_log_channel.name}.")
                    all_chunks_sent = False
                    await closed_log_channel.send("⚠️ *Não foi possível enviar a transcrição completa (sem permissão).*")
                except discord.HTTPException as e:
                    logging.error(
                        f"Erro HTTP ao enviar chunks da transcript para {closed_log_channel.name}: {e}")
                    all_chunks_sent = False
                    await closed_log_channel.send(f"⚠️ *Erro ({e.status}) ao enviar a transcrição completa.*")
                except Exception as e:
                    logging.exception(
                        f"Erro inesperado ao enviar chunks da transcript para {closed_log_channel.name}:")
                    all_chunks_sent = False
                    try:
                        await closed_log_channel.send("⚠️ *Erro inesperado ao enviar a transcrição completa.*")
                    except Exception:
                        pass  # Ignora se não conseguir nem enviar o erro

        elif messages is None and closed_log_channel:  # Se houve erro ao buscar histórico
            try:
                await closed_log_channel.send("⚠️ *Não foi possível gerar a transcrição (erro ao ler histórico do ticket).*")
            except Exception:
                pass

        # --- Mensagem de Aviso e Deleção do Canal ---
        closing_embed = discord.Embed(
            title="🚨 Fechando Ticket", description=f"Este ticket será **excluído** em 5 segundos por {user.mention}.\nUma transcrição foi salva (se aplicável).", color=discord.Color.orange())
        try:
            await channel.send(embed=closing_embed)
        except discord.HTTPException:
            pass
        await asyncio.sleep(5)

        # --- Deleção do Canal e Log Simples ---
        delete_reason = f"Ticket fechado por {user.name} ({user.id})"
        followup_message = "Ticket fechado e transcrição enviada (se aplicável)." if transcript_sent_ok else "Ticket fechado (falha ao enviar transcrição)."
        try:
            await channel.delete(reason=delete_reason)
            logging.info(
                f"Canal de ticket excluído: {channel.name} ({channel.id})")
            # Log Simples
            if self.cog.ticket_log_channel_id and self.cog.ticket_log_channel_id != self.cog.closed_ticket_log_channel_id:
                log_channel_simple = guild.get_channel(
                    self.cog.ticket_log_channel_id)
                if log_channel_simple and isinstance(log_channel_simple, discord.TextChannel):
                    embed_simple = discord.Embed(description=f"🎫 Ticket `#{channel.name}` fechado por {user.mention}.", color=discord.Color.red(
                    ), timestamp=datetime.now(timezone.utc))
                    try:
                        await log_channel_simple.send(embed=embed_simple)
                    except Exception:
                        pass
        except discord.Forbidden:
            followup_message = "Erro: Sem permissão para deletar canal."
            logging.error(f"Sem permissão para deletar {channel.id}")
        except discord.NotFound:
            followup_message = "Canal já foi deletado."
            logging.warning(f"Canal {channel.id} não encontrado para delete.")
        except Exception as e:
            followup_message = "Erro inesperado ao deletar canal."
            logging.exception(f"Erro ao deletar {channel.id}:")

        # Envia o Followup final para quem fechou
        try:
            await interaction.followup.send(followup_message, ephemeral=True)
        except discord.HTTPException:
            pass


class CreateTicketView(discord.ui.View):
    def __init__(self, cog_instance):
        super().__init__(timeout=None)
        self.cog = cog_instance

    @discord.ui.button(label="Abrir Ticket", style=discord.ButtonStyle.primary, custom_id="create_ticket_button", emoji="🎫")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        if not isinstance(user, discord.Member):
            return  # Deve ser membro
        await interaction.response.defer(ephemeral=True, thinking=True)

        # Validação de config
        if not self.cog.ticket_category_id or not self.cog.allowed_mod_role_ids:
            logging.critical(
                f"Criação ticket falhou (user: {user.id}): Config ausente no Cog.")
            await interaction.followup.send("Erro: Sistema de tickets não configurado.", ephemeral=True)
            return
        category = guild.get_channel(self.cog.ticket_category_id)
        allowed_mod_roles = [guild.get_role(r_id)
                             for r_id in self.cog.allowed_mod_role_ids]
        # Filtra roles não encontrados
        allowed_mod_roles = [r for r in allowed_mod_roles if r]
        if not category or not allowed_mod_roles:
            logging.error(
                f"Criação ticket falhou (user: {user.id}): Categoria ou roles inválidos/não encontrados.")
            await interaction.followup.send("Erro: Configuração de categoria/cargos inválida.", ephemeral=True)
            return

        # Verifica ticket existente
        ticket_channel_name = f"ticket-{user.id}"
        existing_channel = discord.utils.get(
            guild.text_channels, name=ticket_channel_name, category=category)
        if existing_channel:
            await interaction.followup.send(f"Você já tem um ticket aberto: {existing_channel.mention if existing_channel else '#' + ticket_channel_name}", ephemeral=True)
            return

        # Permissões
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(
                read_messages=True, send_messages=True, manage_channels=True, manage_messages=True, read_message_history=True, attach_files=True)
        }
        for mod_role in allowed_mod_roles:
            overwrites[mod_role] = discord.PermissionOverwrite(
                read_messages=True, send_messages=True, manage_messages=True, attach_files=True, embed_links=True, read_message_history=True, manage_channels=False)

        # Criação do Canal
        try:
            topic = f"Ticket de {user.name} ({user.id}) | Criado em: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
            channel = await guild.create_text_channel(
                name=ticket_channel_name, category=category, overwrites=overwrites,
                topic=topic, reason=f"Ticket criado por {user.name}"
            )
            logging.info(
                f"Ticket criado: {channel.name} ({channel.id}) por {user.name}")

            # Mensagem Inicial
            embed_ticket = discord.Embed(
                title=f"👋 Bem-vindo ao seu Ticket, {user.display_name}!",
                description="Por favor, descreva seu problema ou dúvida em detalhes.\nNossa equipe irá atendê-lo assim que possível.",
                color=discord.Color.blurple(),
                timestamp=datetime.now(timezone.utc)
            )
            embed_ticket.set_footer(text=f"ID do Ticket: {channel.id}")
            mentions_str = ' '.join(
                [r.mention for r in allowed_mod_roles]) if allowed_mod_roles else "a equipe"
            # Passa o cog para a view de controle
            control_view = TicketControlView(self.cog)
            await channel.send(
                content=f"{user.mention}, seu ticket foi criado! {mentions_str}",
                embed=embed_ticket, view=control_view
            )
            await interaction.followup.send(f"✅ Ticket criado em {channel.mention}!", ephemeral=True)

            # Log Simples Opcional
            if self.cog.ticket_log_channel_id:
                log_channel = guild.get_channel(self.cog.ticket_log_channel_id)
                if log_channel and isinstance(log_channel, discord.TextChannel):
                    embed_log = discord.Embed(
                        title="🎫 Novo Ticket Aberto", description=f"{user.mention} em {channel.mention}",
                        color=discord.Color.green(), timestamp=datetime.now(timezone.utc)
                    )
                    embed_log.add_field(
                        name="User ID", value=f"`{user.id}`", inline=True)
                    embed_log.add_field(
                        name="Chan ID", value=f"`{channel.id}`", inline=True)
                    try:
                        await log_channel.send(embed=embed_log)
                    except Exception:
                        pass  # Ignora erro no log simples

        except Exception as e:  # Captura genérica para logar o erro
            logging.exception(f"Erro ao criar ticket para {user.name}:")
            try:
                await interaction.followup.send("Erro inesperado ao criar o ticket.", ephemeral=True)
            except discord.HTTPException:
                pass  # Ignora se interação expirar


# --- Cog Principal ---
class TicketSystemCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ticket_category_id = None
        self.allowed_mod_role_ids = []
        self.closed_ticket_log_channel_id = None
        self.ticket_log_channel_id = None
        self.load_config()  # Carrega config na inicialização

    def load_config(self):
        """Carrega a configuração do .env para atributos da instância."""
        try:
            # Essenciais
            cat_id_str = os.getenv("TICKET_CATEGORY_ID")
            if not cat_id_str:
                raise ValueError("TICKET_CATEGORY_ID não definido no .env")
            self.ticket_category_id = int(cat_id_str)

            allowed_ids_str = os.getenv("ALLOWED_MOD_ROLE_IDS")
            if not allowed_ids_str:
                raise ValueError("ALLOWED_MOD_ROLE_IDS não definido no .env")
            self.allowed_mod_role_ids = [
                int(r.strip()) for r in allowed_ids_str.split(',') if r.strip()]
            if not self.allowed_mod_role_ids:
                raise ValueError("ALLOWED_MOD_ROLE_IDS vazio ou mal formatado")

            # Opcionais
            cl_id = os.getenv("CLOSED_TICKET_LOG_CHANNEL_ID")
            self.closed_ticket_log_channel_id = int(cl_id) if cl_id else None
            tl_id = os.getenv("TICKET_LOG_CHANNEL_ID")
            self.ticket_log_channel_id = int(tl_id) if tl_id else None

            logging.info("Configuração do TicketSystem carregada com sucesso.")

        except (ValueError, TypeError) as e:  # Pega erros de conversão e ausência
            logging.critical(
                f"!!! TicketSystem: Erro CRÍTICO ao carregar configuração: {e}")
            # Garante que os valores essenciais sejam resetados em caso de erro
            self.ticket_category_id = None
            self.allowed_mod_role_ids = []
            self.closed_ticket_log_channel_id = None
            self.ticket_log_channel_id = None

    @commands.Cog.listener()
    async def on_ready(self):
        # Valida se a configuração essencial foi carregada com sucesso no __init__
        if not self.ticket_category_id or not self.allowed_mod_role_ids:
            logging.error(
                "!!! TicketSystem INATIVO: Falha ao carregar configuração essencial do .env.")
        else:
            log_status = "configurado"
            if self.closed_ticket_log_channel_id:
                log_status += " (com log de transcripts)"
            else:
                log_status += " (SEM log de transcripts)"
            if self.ticket_log_channel_id:
                log_status += " (com log geral)"
            else:
                log_status += " (SEM log geral)"
            logging.info(f"Cog TicketSystem carregado e {log_status}.")
            # Registra as views aqui, somente se a config estiver OK
            try:
                self.bot.add_view(CreateTicketView(self))
                self.bot.add_view(TicketControlView(self))
                logging.info(
                    "Views do TicketSystem registradas para persistência.")
            except Exception as e:
                logging.exception("Erro ao registrar views do TicketSystem:")

    @commands.hybrid_command(name="setup_ticket", description="Configura a mensagem para abrir tickets em um canal.")
    @app_commands.describe(canal="O canal onde a mensagem de criação de ticket será enviada.")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def setup_ticket(self, ctx: commands.Context, canal: discord.TextChannel):
        """Envia a mensagem de criação de ticket para o canal especificado."""
        if not self.ticket_category_id or not self.allowed_mod_role_ids:
            await ctx.send("Erro: Sistema de tickets não configurado ou ativo.", ephemeral=True)
            return

        view = CreateTicketView(self)
        embed = discord.Embed(
            title="🎫 Central de Atendimento",
            description="Precisa de ajuda ou tem alguma dúvida?\nClique no botão abaixo para abrir um ticket privado com nossa equipe.",
            color=discord.Color.blue(),
        )
        embed.set_footer(
            text="Seu ticket será confidencial entre você e a equipe.")

        try:
            await canal.send(embed=embed, view=view)
            await ctx.send(f"✅ Mensagem enviada para {canal.mention}!", ephemeral=True)
        except discord.Forbidden:
            await ctx.send(f"Erro: Sem permissão em {canal.mention}.", ephemeral=True)
        except Exception as e:
            await ctx.send(f"Erro inesperado: {e}", ephemeral=True)
            logging.exception(f"Erro no comando setup_ticket:")

    @setup_ticket.error
    async def setup_ticket_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Sem permissão de Admin.", ephemeral=True)
        elif isinstance(error, commands.ChannelNotFound):
            await ctx.send(f"Canal não encontrado: `{error.argument}`.", ephemeral=True)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Uso: `{ctx.prefix or '/'}setup_ticket canal:<#canal>`", ephemeral=True)
        else:  # Erro genérico para outros casos
            logging.error(f"Erro não tratado no setup_ticket: {error}")
            await ctx.send(f"Erro inesperado.", ephemeral=True)


# Função setup para adicionar o Cog ao bot
async def setup(bot: commands.Bot):
    await bot.add_cog(TicketSystemCog(bot))
