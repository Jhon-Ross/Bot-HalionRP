import discord
from discord.ext import commands
# <--- CERTIFIQUE-SE DE IMPORTAR A VIEW AQUI
from views.whitelist_view import WhitelistView
import os
from dotenv import load_dotenv
import asyncio
import logging
from datetime import datetime, timezone
import traceback
import sys
import random
import ctypes
import aiohttp

if sys.platform == 'win32':
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleOutputCP(65001)

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
try:
    GUILD_ID = int(os.getenv("DISCORD_GUILD_ID"))
except (TypeError, ValueError):
    logging.critical(
        "DISCORD_GUILD_ID não definido ou inválido no .env! Encerrando.")
    sys.exit("Erro: DISCORD_GUILD_ID ausente ou inválido.")


class CustomBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
            chunk_guilds_at_startup=False
        )
        self.persistent_views_added = False
        self.guild_id = GUILD_ID

    async def on_message(self, message):
        pass

    async def setup_hook(self):
        # --- REGISTRO DE VIEWS PERSISTENTES ---
        if not self.persistent_views_added:
            # Adicione instâncias de TODAS as suas views persistentes aqui
            self.add_view(WhitelistView())  # <--- ESSA LINHA É CRUCIAL!
            # self.add_view(OutraView())     # <--- Você provavelmente já tem linhas para as outras views
            # self.add_view(MaisUmaView())

            logging.info("Views persistentes registradas.")  # Use seu logger
            self.persistent_views_added = True
        # ------------------------------------
        await self.load_extensions()

    async def load_extensions(self):
        log_header("CARREGANDO EXTENSÕES", "📦")
        loaded = 0
        skipped = 0
        cogs_dir = "./cogs"

        if not os.path.isdir(cogs_dir):
            logging.warning(f"Diretório de cogs '{cogs_dir}' não encontrado.")
            return

        for filename in os.listdir(cogs_dir):
            if filename.endswith(".py") and not filename.startswith("_"):
                cog_path = os.path.join(cogs_dir, filename)
                cog_name = f"cogs.{filename[:-3]}"
                try:
                    if os.path.getsize(cog_path) > 0:
                        await self.load_extension(cog_name)
                        log_status(f"Carregado: {cog_name}", "success")
                        loaded += 1
                    else:
                        log_status(f"Ignorado (vazio): {cog_name}", "warning")
                        skipped += 1
                except commands.ExtensionAlreadyLoaded:
                    log_status(f"Já carregado: {cog_name}", "info")
                except commands.ExtensionNotFound:
                    log_status(f"Não encontrado: {cog_name}", "error")
                except commands.NoEntryPointError:
                    log_status(
                        f"Sem ponto de entrada (setup): {cog_name}", "error")
                except commands.ExtensionFailed as e:
                    log_status(
                        f"Falha no setup de {cog_name}: {type(e.original).__name__}", "error")
                    logging.error(
                        f"Erro ao carregar {cog_name}:\n{traceback.format_exc()}")
                except Exception as e:
                    log_status(
                        f"Erro inesperado em {cog_name}: {type(e).__name__}", "error")
                    logging.error(
                        f"Erro inesperado ao carregar {cog_name}:\n{traceback.format_exc()}")

        log_status(f"Total carregado: {loaded} | Ignorados: {skipped}", "info")


bot = CustomBot()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8', mode='a'),
        logging.StreamHandler()
    ]
)


def log_header(message, emoji="ℹ️"):
    logging.info(f"\n{emoji} {'=' * 50}")
    logging.info(f"{emoji} {message.center(48)}")
    logging.info(f"{emoji} {'=' * 50}")


def log_status(message, status="success"):
    emojis = {"success": "✅", "error": "❌",
              "warning": "⚠️", "info": "ℹ️", "loading": "🔄"}
    level = logging.ERROR if status == "error" else logging.WARNING if status == "warning" else logging.INFO
    logging.log(level, f"{emojis.get(status, 'ℹ️')} {message}")


async def send_log_discord(embed_content):
    try:
        logs_channel_id_str = os.getenv("LOGS_DISCORD")
        if logs_channel_id_str:
            try:
                channel_id = int(logs_channel_id_str)
                channel = bot.get_channel(channel_id)
                if channel:
                    await channel.send(embed=embed_content)
                else:
                    log_status(
                        f"Canal de logs Discord (ID: {channel_id}) não encontrado no cache.", "warning")
            except ValueError:
                log_status(
                    f"LOGS_DISCORD ('{logs_channel_id_str}') é inválido.", "error")
            except discord.Forbidden:
                log_status(
                    f"Permissão negada para enviar mensagens no canal de logs (ID: {logs_channel_id_str}).", "error")
            except discord.HTTPException as e:
                log_status(
                    f"Erro HTTP ao enviar log para Discord: {e}", "error")
            except Exception as e:
                log_status(
                    f"Erro inesperado ao enviar log para Discord: {e}", "error")
                logging.error(traceback.format_exc())
    except Exception as e:
        log_status(
            f"Erro crítico ao tentar enviar log para Discord: {str(e)}", "error")


@bot.event
async def on_ready():
    try:
        log_header(f"BOT {bot.user.name} INICIADO", "🤖")
        log_status(f"ID: {bot.user.id}")
        log_status(f"Discord.py v{discord.__version__}")
        log_status(f"Conectado a {len(bot.guilds)} servidor(es)")
        current_time = datetime.now()
        log_status(
            f"Horário (Log Interno): {current_time.strftime('%d/%m/%Y %H:%M:%S')}")

        member_count_str = "N/A"
        target_guild = bot.get_guild(GUILD_ID)
        if target_guild:
            member_count_str = f"{target_guild.member_count} membros"
            log_status(
                f"Membros em {target_guild.name}: {target_guild.member_count}")
        else:
            try:
                target_guild = await bot.fetch_guild(GUILD_ID)
                if target_guild:
                    member_count_str = f"{target_guild.member_count} membros"
                    log_status(
                        f"Membros em {target_guild.name} (fetched): {target_guild.member_count}")
                else:
                    log_status(
                        f"Servidor com ID {GUILD_ID} não encontrado (fetch falhou).", "warning")
            except Exception as e_fetch:
                log_status(
                    f"Erro ao buscar servidor {GUILD_ID}: {e_fetch}", "warning")
                logging.error(f"Erro fetch guild: {traceback.format_exc()}")

        embed_ready = discord.Embed(
            title="🟢 Bot Iniciado",
            description=f"**{bot.user.name}** está online e pronto para operar!",
            color=discord.Color.green(),
            timestamp=current_time
        )
        if bot.user.display_avatar:
            embed_ready.set_thumbnail(url=bot.user.display_avatar.url)

        embed_ready.add_field(name="🆔 ID do Bot",
                              value=f"`{bot.user.id}`", inline=False)
        embed_ready.add_field(name="👥 Total no Servidor",
                              value=member_count_str, inline=False)
        unix_timestamp = int(current_time.timestamp())
        embed_ready.add_field(
            name="📅 Horário", value=f"<t:{unix_timestamp}:F>", inline=False)
        embed_ready.set_footer(text="Genesis RP System")

        await send_log_discord(embed_ready)
        log_status(
            "Mensagem de inicialização enviada para o canal de logs", "success")

        log_header("SINCRONIZANDO COMANDOS SLASH", "🔄")
        try:
            guild_obj = discord.Object(id=GUILD_ID)
            bot.tree.copy_global_to(guild=guild_obj)
            synced = await bot.tree.sync(guild=guild_obj)
            log_status(
                f"Comandos sincronizados para a Guild {GUILD_ID}: {len(synced)}", "success")
        except Exception as e:
            log_status(f"Falha ao sincronizar comandos: {e}", "error")
            logging.error(f"Erro sync: {traceback.format_exc()}")

        log_header("BOT PRONTO PARA USO", "🚀")

    except Exception as e:
        log_status(
            f"ERRO CRÍTICO EM ON_READY: {type(e).__name__} - {str(e)}", "error")
        logging.critical(
            f"Erro fatal durante on_ready:\n{traceback.format_exc()}")


async def send_member_log(member, action):
    try:
        is_join = action == "join"
        color = discord.Color.green() if is_join else discord.Color.red()
        title = f"{'🟢' if is_join else '🔴'} {'Novo Membro' if is_join else 'Membro Saiu'}"

        embed = discord.Embed(
            color=color,
            timestamp=datetime.now()
        )
        embed.set_author(name=f"{member.name} ({member.id})",
                         icon_url=member.display_avatar.url)
        embed.set_thumbnail(url=member.display_avatar.url)

        created_unix = int(member.created_at.timestamp())
        embed.add_field(name="📅 Conta Criada",
                        value=f"<t:{created_unix}:F> (<t:{created_unix}:R>)", inline=False)

        if not is_join and member.joined_at:
            joined_unix = int(member.joined_at.timestamp())
            embed.add_field(name="👋 Entrada no Servidor",
                            value=f"<t:{joined_unix}:F> (<t:{joined_unix}:R>)", inline=False)
            now_utc = datetime.now(timezone.utc)
            time_in_server = now_utc - member.joined_at
            days = time_in_server.days
            duration_str = f"{days} dia(s)" if days > 0 else "Menos de um dia"
            if days < 3:
                hours, remainder = divmod(time_in_server.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                duration_str = f"{days}d {hours}h {minutes}m" if days > 0 else f"{hours}h {minutes}m"

            embed.add_field(name="⏱ Tempo no Servidor",
                            value=duration_str, inline=True)

        current_member_count = member.guild.member_count
        embed.add_field(name="👥 Total Atual", value=str(
            current_member_count), inline=True)

        if not is_join:
            roles = [role.mention for role in sorted(
                member.roles, key=lambda r: r.position, reverse=True) if role.name != "@everyone"]
            role_limit = 10
            roles_str = "Nenhum cargo específico."
            if roles:
                roles_to_show = roles[:role_limit]
                roles_str = " ".join(roles_to_show)
                if len(roles) > role_limit:
                    roles_str += f" (+{len(roles) - role_limit})"

            embed.add_field(
                name=f"🔹 Cargos ({len(roles)})", value=roles_str, inline=False)

        await send_log_discord(embed)

    except Exception as e:
        log_status(
            f"Erro ao criar/enviar log de membro para {member.id} (Ação: {action}): {str(e)}", "error")
        logging.error(traceback.format_exc())


@bot.event
async def on_member_join(member: discord.Member):
    if member.bot:
        log_status(
            f"Bot {member.name} entrou, ignorando processamento de membro.", "info")
        return

    await send_member_log(member, "join")

    visitante_id_str = os.getenv("VISITANTE_ID")
    if visitante_id_str:
        try:
            visitante_role_id = int(visitante_id_str)
            role = member.guild.get_role(visitante_role_id)
            if role:
                log_status(
                    f"Tentando adicionar cargo '{role.name}' para {member.name}...", "loading")
                await asyncio.sleep(random.uniform(0.3, 0.8))
                await member.add_roles(role, reason="Entrada no servidor")
                log_status(
                    f"Cargo '{role.name}' atribuído a {member.name} ({member.id})", "success")

                embed_role = discord.Embed(
                    description=f"✅ {member.mention} recebeu o cargo {role.mention} ao entrar.",
                    color=discord.Color.blue(),
                    timestamp=datetime.now()
                )
                embed_role.set_author(
                    name=f"{member.name} ({member.id})", icon_url=member.display_avatar.url)
                await send_log_discord(embed_role)

            else:
                log_status(
                    f"Cargo Visitante (ID: {visitante_id_str}) não encontrado no servidor.", "warning")
        except ValueError:
            log_status(
                f"VISITANTE_ID ('{visitante_id_str}') é inválido.", "error")
        except discord.Forbidden:
            log_status(
                f"Permissão negada para adicionar cargo Visitante a {member.name}.", "error")
        except discord.HTTPException as e:
            log_status(
                f"Erro HTTP ao adicionar cargo Visitante a {member.name}: {e}", "error")
        except Exception as e:
            log_status(
                f"Erro inesperado ao atribuir cargo Visitante a {member.name}: {str(e)}", "error")
            logging.error(traceback.format_exc())
    else:
        log_status(
            "VISITANTE_ID não definido no .env, cargo não atribuído.", "warning")


@bot.event
async def on_member_remove(member: discord.Member):
    if member.bot:
        return
    log_status(f"Membro {member.name} ({member.id}) saiu.", "info")
    await send_member_log(member, "leave")


async def main():
    async with bot:
        try:
            log_header("INICIANDO BOT HALION RP", "⚡")
            if not TOKEN:
                log_status(
                    "DISCORD_TOKEN não encontrado no .env! Encerrando.", "error")
                return

            log_status("Iniciando conexão com o Discord...", "loading")
            await bot.start(TOKEN)

        except discord.LoginFailure:
            log_status(
                "Falha no login: Token inválido ou faltando intents.", "error")
            logging.critical("Token inválido fornecido. Verifique o .env.")
        except discord.PrivilegedIntentsRequired:
            log_status(
                "Intents privilegiadas (Members/Presence) não habilitadas no Portal do Desenvolvedor.", "error")
            logging.critical(
                "Intents privilegiadas necessárias mas não habilitadas.")
        except Exception as e:
            log_status(
                f"ERRO FATAL NA INICIALIZAÇÃO: {type(e).__name__} - {str(e)}", "error")
            logging.critical(
                f"Erro não tratado durante a inicialização:\n{traceback.format_exc()}")
        finally:
            log_status("Bot encerrado.", "info")

if __name__ == "__main__":
    try:
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(
                asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())

    except KeyboardInterrupt:
        log_status("Desligamento solicitado pelo usuário (Ctrl+C).", "warning")
    except aiohttp.ClientConnectorError as e:
        log_status(
            "❌ Falha ao conectar-se ao Discord. Verifique sua conexão com a internet, DNS ou firewall.", "error")
        logging.error(f"Detalhes técnicos: {type(e).__name__}: {e}")
    except Exception as e:
        log_status(f"Erro crítico fora do loop principal: {e}", "error")
        logging.critical(
            f"Erro fatal antes do asyncio.run:\n{traceback.format_exc()}")
