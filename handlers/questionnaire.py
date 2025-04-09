import discord
import asyncio
import csv
import os
import logging
# Adicionado timedelta e timezone para manipulação de fuso horário
from datetime import datetime, timedelta, timezone

# --- Configurações ---
CSV_FILENAME = "whitelist_respostas.csv"
STAFF_CHANNEL_NAME = "respostas-whitelist"
COOLDOWN_MINUTES = 30
QUESTIONNAIRE_TIMEOUT_MINUTES = 20
DELETE_DELAY = 10
ATTEMPT_ID_FILE = "whitelist_last_attempt_id.txt"

# --- Variáveis Globais ---
cooldowns = {}
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s')
logger = logging.getLogger(__name__)

# --- Fuso Horário de Brasília (UTC-3) ---
# ATENÇÃO: Assume que o fuso é fixo UTC-3. Considere pytz para regras mais complexas (ex: horário de verão).
BRASILIA_TZ = timezone(timedelta(hours=-3))


# --- Perguntas ---
questions = [
    "Qual ID foi apresentado para você na hora que tentou entrar na cidade?",
    "O que você faz se outro jogador quebrar as regras do servidor?",
    "Cite 3 regras importantes do servidor e explique por que são essenciais.",
    "É permitido 'combate aleatório' (RDM) na cidade? Justifique.",
    "Descreva como você reagiria se fosse assaltado por um criminoso (sem recorrer a metagaming).",
    "O que é 'powergaming' e como você pode evitá-lo durante suas interações?",
    "Se um policial devidamente identificado solicitar sua identificação durante uma abordagem RP, qual seria sua reação?",
    "Descreva brevemente seu personagem: inclua nome, idade aproximada, profissão ou ocupação principal e um defeito notável de personalidade.",
    "Qual é a principal motivação do seu personagem para ter escolhido morar ou permanecer nesta cidade?",
    "Como seu personagem reagiria ao presenciar uma emergência médica grave, como um tiroteio nas proximidades?",
    "Você encontra uma mala abandonada que parece conter uma grande quantia de dinheiro de origem ilegal. O que seu personagem faz?",
    "Um amigo próximo do seu personagem pede sua ajuda para cometer um ato criminoso. Como seu personagem responde a esse pedido?",
    "Como você, interpretando seu personagem, reagiria se fosse vítima de um erro claro por parte de um policial (por exemplo, uma prisão considerada injusta)?",
    "Qual procedimento você seguiria para reportar um bug ou um problema técnico que encontrou no servidor?",
    "Existe algum comando específico que você pode usar dentro do jogo para consultar as regras rapidamente? Se sim, qual?",
    "Explique, com suas palavras, como geralmente funcionam os sistemas de empregos legais disponíveis no servidor.",
    "Você está ciente e concorda que suas ações e interações RP dentro do servidor podem ser gravadas por membros da staff para fins de análise e avaliação?",
    "Qual é a sua posição sobre o uso de cheats, hacks, exploits ou qualquer tipo de modificação ilegal que ofereça vantagem injusta?",
    "Caso receba uma punição (como um banimento), você se compromete a ler atentamente os motivos apresentados pela staff antes de buscar um recurso ou apelação?"
]

# --- Funções de ID Sequencial ---


def get_next_attempt_id() -> int:
    last_id = 0
    try:
        if os.path.exists(ATTEMPT_ID_FILE):
            with open(ATTEMPT_ID_FILE, 'r') as f:
                content = f.read().strip()
                if content:
                    last_id = int(content)
    except (IOError, ValueError) as e:
        logger.error(
            f"Erro ao ler o arquivo de ID de tentativa ({ATTEMPT_ID_FILE}): {e}. Resetando para 0.")
        last_id = 0
    return last_id + 1


def update_last_attempt_id(last_id_used: int):
    try:
        with open(ATTEMPT_ID_FILE, 'w') as f:
            f.write(str(last_id_used))
    except IOError as e:
        logger.error(
            f"Falha ao atualizar o arquivo de ID de tentativa ({ATTEMPT_ID_FILE}) para {last_id_used}: {e}")


# --- Função para Salvar no CSV (Modificada para formato local) ---
def save_to_csv(attempt_id: int, completion_time_local: datetime, member: discord.Member, responses: list):
    """Salva as respostas do membro em um arquivo CSV, incluindo ID da tentativa e timestamp local formatado."""
    file_exists = os.path.isfile(CSV_FILENAME)
    # Formato personalizado: YYYY-MM-DD HH:MM:SS (agora usando o tempo local passado)
    completion_time_str = completion_time_local.strftime(
        "%Y-%m-%d %H:%M:%S")  # <--- MODIFICADO

    try:
        with open(CSV_FILENAME, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)

            # Escreve o novo cabeçalho se o arquivo não existir ou estiver vazio
            if not file_exists or os.path.getsize(CSV_FILENAME) == 0:
                # Indica que o timestamp é local no cabeçalho
                writer.writerow(['AttemptID', 'CompletionTimestampLocal', 'UserID',  # <--- MODIFICADO
                                'Username', 'QuestionNumber', 'QuestionText', 'AnswerText'])

            # Escreve as respostas do membro, usando o timestamp local formatado
            for i, (question_text, answer) in enumerate(responses, 1):
                writer.writerow(
                    [attempt_id, completion_time_str, member.id, str(member), i, question_text, answer])
        logger.info(
            # Log atualizado
            f"Respostas da tentativa {attempt_id} de {member} salvas em {CSV_FILENAME} com timestamp local.")
    except IOError as e:
        logger.error(
            f"Erro ao escrever no arquivo CSV {CSV_FILENAME} para tentativa {attempt_id}: {e}")
    except Exception as e:
        logger.error(
            f"Erro inesperado ao salvar CSV para tentativa {attempt_id} de {member}: {e}")

# --- Função Principal do Questionário (Modificada) ---


async def start_questionnaire(member: discord.Member, channel: discord.TextChannel, bot: discord.Client):
    now_utc = datetime.now(timezone.utc)  # Pega a hora atual em UTC

    logger.info(
        f"Iniciando processo de questionário para: {member} (ID: {member.id}) no canal {channel.name}")

    # --- Mensagens Iniciais ---
    try:
        await channel.send(f"👋 Olá {member.mention}, bem-vindo(a) ao seu teste de whitelist!")
        await asyncio.sleep(1)
        await channel.send(
            f"⏳ Você terá **{QUESTIONNAIRE_TIMEOUT_MINUTES} minutos** para responder todas as **{len(questions)} perguntas**. Boa sorte!",
            delete_after=QUESTIONNAIRE_TIMEOUT_MINUTES * 60
        )
        await asyncio.sleep(3)
    except discord.Forbidden:
        logger.error(
            f"Erro de permissão ao enviar mensagens iniciais no canal {channel.name} para {member.id}")
        try:
            await channel.delete(reason="Falha ao enviar mensagens iniciais (permissão)")
        except Exception:
            logger.error(
                f"Falha ao deletar canal {channel.name} após erro de permissão inicial.")
        return
    except Exception as e:
        logger.error(
            f"Erro inesperado ao enviar mensagens iniciais para {member.id}: {e}")
        try:
            await channel.delete(reason="Erro inesperado nas mensagens iniciais")
        except Exception:
            logger.error(
                f"Falha ao deletar canal {channel.name} após erro inesperado inicial.")
        return

    # Define cooldown usando a hora UTC
    cooldowns[member.id] = now_utc + timedelta(minutes=COOLDOWN_MINUTES)

    def check(m):
        return m.author == member and m.channel == channel

    responses_list = []
    start_time_utc = datetime.now(timezone.utc)  # Marca início em UTC
    total_timeout_seconds = QUESTIONNAIRE_TIMEOUT_MINUTES * 60
    question_message = None
    answer_message = None
    questionnaire_completed_successfully = False

    try:
        for i, question_text in enumerate(questions, 1):
            # Calcula tempo restante com base em UTC
            elapsed_seconds = (datetime.now(timezone.utc) -
                               start_time_utc).total_seconds()
            remaining_time_total = total_timeout_seconds - elapsed_seconds

            if remaining_time_total <= 0:
                await channel.send(f"⏰ Tempo total esgotado! Você demorou mais de {QUESTIONNAIRE_TIMEOUT_MINUTES} minutos.", delete_after=DELETE_DELAY + 5)
                raise asyncio.TimeoutError(
                    "Tempo total do questionário excedido.")

            try:
                # Envia pergunta sem tempo restante
                question_message = await channel.send(
                    # <--- MODIFICADO (sem tempo)
                    f"**Pergunta {i}/{len(questions)}:**\n{question_text}"
                )
            except discord.Forbidden:
                logger.error(
                    f"Erro de permissão ao enviar pergunta {i} no canal {channel.name}")
                raise Exception("Falha ao enviar pergunta por permissão.")
            except Exception as e:
                logger.error(
                    f"Erro inesperado ao enviar pergunta {i} para {member.id}: {e}")
                raise

            try:
                # Espera resposta usando tempo restante calculado em UTC
                answer_message = await bot.wait_for('message', check=check, timeout=remaining_time_total)
                responses_list.append((question_text, answer_message.content))

                # Deleta pergunta e resposta
                try:
                    if question_message:
                        await question_message.delete()
                except discord.NotFound:
                    pass
                except discord.Forbidden:
                    logger.warning(
                        f"Sem permissão para deletar msg pergunta {i} ({question_message.id})")
                except Exception as e_del:
                    logger.warning(
                        f"Não foi possível deletar msg pergunta {i}: {e_del}", exc_info=False)

                try:
                    if answer_message:
                        await answer_message.delete()
                except discord.NotFound:
                    pass
                except discord.Forbidden:
                    logger.warning(
                        f"Sem permissão para deletar msg resposta {i} ({answer_message.id})")
                except Exception as e_del:
                    logger.warning(
                        f"Não foi possível deletar msg resposta {i}: {e_del}", exc_info=False)

                question_message = None
                answer_message = None

            except asyncio.TimeoutError:
                logger.warning(
                    f"Timeout (wait_for) durante pergunta {i} para {member} no canal {channel.name}. Tempo total provavelmente esgotado.")
                await channel.send(f"⏰ Tempo total esgotado enquanto aguardava a resposta da pergunta {i}!", delete_after=DELETE_DELAY + 5)
                if question_message:
                    try:
                        await question_message.delete()
                    except Exception:
                        pass
                raise

        # --- Questionário Concluído com Sucesso ---
        questionnaire_completed_successfully = True

        # Registrar hora exata da conclusão EM UTC
        completion_time_utc = datetime.now(timezone.utc)
        # Converter o tempo UTC para o horário de Brasília (para o CSV)
        completion_time_local = completion_time_utc.astimezone(
            BRASILIA_TZ)  # <--- ADICIONADO

        await channel.send("✅ Questionário concluído! Suas respostas foram registradas e serão avaliadas pela equipe.", delete_after=DELETE_DELAY)

        # --- Obter ID e Salvar ---
        current_attempt_id = get_next_attempt_id()
        logger.info(
            f"Questionário concluído por {member}. Atribuindo ID de Tentativa: {current_attempt_id}")

        # Passa o TEMPO LOCAL para salvar no CSV
        save_to_csv(current_attempt_id, completion_time_local,
                    member, responses_list)  # <--- MODIFICADO
        # Atualiza o contador para o próximo
        update_last_attempt_id(current_attempt_id)

        # --- Enviar para Canal da Staff ---
        staff_channel = discord.utils.get(
            channel.guild.text_channels, name=STAFF_CHANNEL_NAME)
        if staff_channel:
            # O embed usa o timestamp UTC, que o Discord formata automaticamente.
            embed = discord.Embed(
                title=f"📋 Novas Respostas Whitelist [Tentativa #{current_attempt_id}]: {member.display_name}",
                # Usar o timestamp UTC aqui <t:ts:F> é o ideal para o Discord
                # <--- Mantém UTC
                description=f"Usuário: {member.mention} (`{member.id}`)\nConcluído em: <t:{int(completion_time_utc.timestamp())}:F>",
                color=discord.Color.green(),
                timestamp=completion_time_utc  # <--- Mantém UTC no rodapé do embed
            )
            # Itera sobre a lista de respostas salvas
            for idx, (pergunta, resposta) in enumerate(responses_list, 1):
                resposta_truncated = (
                    resposta[:1020] + '...') if len(resposta) > 1024 else resposta
                embed.add_field(
                    name=f"{idx}. {pergunta}", value=f">>> {resposta_truncated}", inline=False)

            embed.set_footer(
                text=f"ID do Usuário: {member.id} | ID da Tentativa: {current_attempt_id}")
            try:
                await staff_channel.send(embed=embed)
            except discord.Forbidden:
                logger.error(
                    f"Erro: Sem permissão para enviar embed no canal da staff {STAFF_CHANNEL_NAME}")
            except Exception as e:
                logger.error(
                    f"Erro ao enviar embed para canal da staff: {e}", exc_info=True)
        else:
            logger.warning(
                f"Canal da staff '{STAFF_CHANNEL_NAME}' não encontrado para a tentativa {current_attempt_id}.")

    except asyncio.TimeoutError:
        logger.warning(
            f"Timeout final ou durante questionário para {member} no canal {channel.name}.")
        # Não salva nem incrementa ID em caso de timeout
        await asyncio.sleep(DELETE_DELAY + 5)

    except Exception as e:
        logger.error(
            f"Erro inesperado durante o questionário para {member} no canal {channel.name}: {e}", exc_info=True)
        # Não salva nem incrementa ID em caso de erro
        try:
            await channel.send("❌ Ocorreu um erro inesperado durante o questionário. Por favor, tente novamente mais tarde ou contate um administrador.", delete_after=DELETE_DELAY)
        except discord.Forbidden:
            logger.error(
                f"Erro: Sem permissão para enviar mensagem de erro no canal {channel.name}")
        except Exception:
            pass
        await asyncio.sleep(DELETE_DELAY)

    finally:
        logger.info(
            f"Finalizando questionário para {member}. Tentando deletar canal {channel.name}...")
        await asyncio.sleep(2)  # Pequena pausa antes de deletar
        try:
            await channel.delete(reason="Questionário finalizado, cancelado ou com erro")
            logger.info(f"Canal {channel.name} deletado com sucesso.")
        except discord.NotFound:
            logger.warning(
                f"Aviso: Canal {channel.name} já havia sido deletado.")
        except discord.Forbidden:
            logger.critical(
                f"Erro Crítico: Sem permissão para deletar o canal {channel.name}. Necessário deletar manualmente.")
        except Exception as e:
            logger.error(
                f"Erro inesperado ao tentar deletar canal {channel.name}: {e}", exc_info=True)
