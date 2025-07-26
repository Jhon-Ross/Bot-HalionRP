# Halion RP Bot

Este é um bot para Discord desenvolvido para gerenciar diversas funcionalidades de um servidor Roleplay (RP) chamado Halion RP. Ele inclui recursos como sistema de whitelist, gerenciamento de tickets, comunicação oficial, verificação de usuários e moderação.

---

## 📋 Funcionalidades

### 1. **Sistema de Whitelist**
- **Descrição:** Permite que os usuários iniciem um processo de whitelist para ingressar no servidor, respondendo a um questionário em um canal privado temporário.
- **Comando:** `/whitelist` (enviado por um moderador no canal configurado).
- **Fluxo:**
    - O usuário clica no botão "Quero fazer whitelist".
    - Um canal de texto privado é criado para o usuário.
    - O usuário responde a uma série de perguntas em um tempo limitado (20 minutos).
    - As respostas são salvas em `whitelist_respostas.csv` e enviadas para um canal de staff (`respostas-whitelist`).
    - Um cooldown de 30 minutos é aplicado após cada tentativa.
- **Arquivos Relacionados:** `cogs/whitelist.py`, `views/whitelist_view.py`, `handlers/questionnaire.py`, `whitelist_respostas.csv`, `whitelist_last_attempt_id.txt`.

### 2. **Sistema de Tickets**
- **Descrição:** Permite que os usuários abram tickets para suporte ou dúvidas, criando canais privados para comunicação com a equipe.
- **Comando:** `/setup_ticket` (para configurar a mensagem de abertura de ticket em um canal).
- **Fluxo:**
    - O usuário clica no botão "Abrir Ticket".
    - Um canal de texto privado é criado na categoria de tickets.
    - A equipe pode fechar o ticket usando um botão no canal.
    - Ao fechar, uma transcrição da conversa é gerada e enviada para um canal de logs de tickets fechados.
- **Arquivos Relacionados:** `cogs/ticket_system.py`.

### 3. **Comunicação Oficial**
- **Descrição:** Permite que a equipe envie ou atualize comunicados e avisos oficiais em canais designados.
- **Comando:** `/comunicados <texto>`
- **Funcionalidade:**
    - Atualiza uma mensagem existente no canal de comunicados ou envia uma nova.
    - Pode enviar avisos para um canal de avisos separado.
- **Arquivos Relacionados:** `cogs/communication.py`, `data/comunicados_message_id.txt`.

### 4. **Verificação de Usuários**
- **Descrição:** Sistema para verificar novos membros e atribuir cargos automaticamente, além de enviar mensagens de boas-vindas.
- **Comando:** `/verificar` (para enviar o painel de verificação).
- **Fluxo:**
    - O usuário clica no botão "Verificar-se".
    - O cargo de "Visitante" é removido e o cargo de "Turista" é atribuído.
    - Mensagens de boas-vindas personalizadas são enviadas para novos membros, incluindo links para regras e verificação, e redes sociais.
- **Arquivos Relacionados:** `cogs/verificacao.py`.

### 5. **Moderação**
- **Descrição:** Oferece ferramentas básicas de moderação para a equipe.
- **Comando:** `/excluir <quantidade>`
- **Funcionalidade:**
    - Exclui uma quantidade específica de mensagens (1-100) do canal atual.
    - Registra as ações de exclusão em um canal de logs.
- **Arquivos Relacionados:** `cogs/moderacao.py`.

### 6. **Conexão ao Servidor**
- **Descrição:** Fornece informações rápidas sobre como se conectar ao servidor Halion RP.
- **Comando:** `/connect`
- **Funcionalidade:**
    - Exibe o link de conexão FiveM direto.
    - Inclui um botão para acessar o site oficial do Halion RP.
- **Arquivos Relacionados:** `cogs/conectar.py`, `views/connect_view.py` (implícita no `conectar.py`).

---

## ⚙️ Configuração

### 1. **Pré-requisitos**
- Python 3.10 ou superior.
- Biblioteca `discord.py` (versão 2.5.2 ou compatível).
- Biblioteca `python-dotenv` para carregar variáveis de ambiente.
- Biblioteca `aiohttp` para requisições HTTP.
- Biblioteca `ctypes` (para Windows, já inclusa no Python).

### 2. **Instalação**
1. Clone este repositório:
   ```bash
   git clone https://github.com/Jhon-Ross/Bot-HalionRP.git
   cd Bot-HalionRP
   ```
2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
3. Crie um arquivo `.env` na raiz do projeto e adicione as seguintes variáveis:

   ```ini
   # Variáveis Essenciais do Bot
   DISCORD_TOKEN=SEU_TOKEN_DO_BOT_AQUI
   DISCORD_GUILD_ID=ID_DO_SEU_SERVIDOR_PRINCIPAL

   # Canais e Cargos (IDs numéricos)
   WHITELIST_ID=ID_DO_CANAL_DE_WHITELIST
   ANALISE_ID=ID_DO_CARGO_DE_ANALISE_DA_WHITELIST
   COMUNICADOS_ID=ID_DO_CANAL_DE_COMUNICADOS_OFICIAIS
   AVISOS_ID=ID_DO_CANAL_DE_AVISOS_OPCIONAL # Opcional: Canal para avisos gerais
   VERIFICAR_ID=ID_DO_CANAL_DE_VERIFICACAO
   TURISTA_ID=ID_DO_CARGO_DE_TURISTA_APOS_VERIFICACAO
   VISITANTE_ID=ID_DO_CARGO_DE_VISITANTE_ANTES_DA_VERIFICACAO
   BOAS_VINDAS_ID=ID_DO_CANAL_DE_BOAS_VINDAS
   REGRAS_ID=ID_DO_CANAL_DE_REGRAS # Opcional: Para linkar nas boas-vindas
   LOGS_DISCORD=ID_DO_CANAL_DE_LOGS_GERAIS_DO_BOT # Para logs de moderação, verificação, etc.

   # Configurações do Sistema de Tickets
   TICKET_CATEGORY_ID=ID_DA_CATEGORIA_ONDE_OS_TICKETS_SERAO_CRIADOS
   CLOSED_TICKET_LOG_CHANNEL_ID=ID_DO_CANAL_DE_LOGS_DE_TICKETS_FECHADOS # Opcional: Para transcrições
   TICKET_LOG_CHANNEL_ID=ID_DO_CANAL_DE_LOGS_GERAIS_DE_TICKETS # Opcional: Para logs de abertura/fechamento simples

   # Cargos Permitidos para Comandos de Staff (IDs separados por vírgula, sem espaços)
   ALLOWED_MOD_ROLE_IDS=ID_CARGO1,ID_CARGO2,ID_CARGO3 # Ex: 123456789012345678,987654321098765432
   ```
   **Importante:** Certifique-se de que os IDs dos canais e cargos são numéricos e corretos. Para `ALLOWED_MOD_ROLE_IDS`, separe múltiplos IDs com vírgulas e **sem espaços**.

### 3. **Execução**
- Para iniciar o bot, execute:
  ```bash
  python main.py
  ```
- No Windows, você também pode usar o arquivo `start.bat`.

---

## 🛠️ Estrutura do Projeto

- `main.py`: Ponto de entrada principal do bot, responsável por carregar os cogs e iniciar o cliente Discord.
- `cogs/`: Contém os módulos (cogs) que implementam as diferentes funcionalidades do bot (whitelist, tickets, moderação, etc.).
    - `communication.py`: Gerencia comunicados oficiais.
    - `conectar.py`: Fornece informações de conexão ao servidor.
    - `moderacao.py`: Contém comandos de moderação.
    - `ticket_system.py`: Implementa o sistema de tickets.
    - `verificacao.py`: Lida com a verificação de usuários e mensagens de boas-vindas.
    - `whitelist.py`: Gerencia o processo de whitelist.
- `data/`: Armazena dados persistentes, como o ID da última mensagem de comunicado.
    - `comunicados_message_id.txt`: Guarda o ID da mensagem do comunicado oficial.
- `database/`: Contém módulos relacionados à interação com o banco de dados (se aplicável).
    - `database.py`: Lógica de conexão e operações de banco de dados.
    - `models.py`: Definição de modelos de dados.
- `handlers/`: Contém a lógica de negócios e manipuladores de eventos.
    - `questionnaire.py`: Lógica do questionário de whitelist, incluindo perguntas, cooldowns e salvamento de respostas.
- `logs/`: Diretório para arquivos de log do bot.
- `utils/`: Módulos com funções e classes utilitárias.
    - `buttons.py`: Definições de botões reutilizáveis.
    - `embeds.py`: Funções para criar embeds padronizados.
    - `logger.py`: Configurações e funções de logging.
- `views/`: Contém as definições de views (botões persistentes) para interações do Discord.
    - `whitelist_view.py`: View para iniciar o processo de whitelist.
- `whitelist_respostas.csv`: Arquivo CSV onde as respostas da whitelist são salvas.
- `whitelist_last_attempt_id.txt`: Armazena o último ID de tentativa de whitelist usado.
- `.gitignore`: Lista de arquivos e diretórios a serem ignorados pelo Git.
- `requirements.txt`: Lista de dependências Python do projeto.
- `start.bat`: Script simples para iniciar o bot no Windows.

---

## 🤝 Contribuição

Sinta-se à vontade para contribuir com melhorias, correções de bugs ou novas funcionalidades. Por favor, abra uma issue ou envie um Pull Request.

---

## 📄 Licença

Este projeto está licenciado sob a [Licença MIT](LICENSE).
