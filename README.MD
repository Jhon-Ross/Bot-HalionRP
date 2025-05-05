# Halion RP Bot

Este é um bot para Discord desenvolvido para gerenciar diversas funcionalidades de um servidor Roleplay (RP) chamado Halion RP. Ele inclui recursos como sistema de whitelist, gerenciamento de tickets, comunicação oficial, verificação de usuários e moderação.

---

## 📋 Funcionalidades

### 1. **Sistema de Whitelist**
- Permite que os usuários iniciem um processo de whitelist para ingressar no servidor.
- Cria canais temporários para cada usuário, onde eles respondem a um questionário.
- As respostas são registradas em um arquivo CSV (`whitelist_respostas.csv`) para análise posterior pela equipe.

### 2. **Sistema de Tickets**
- Usuários podem abrir tickets para suporte ou dúvidas.
- Tickets são criados como canais privados, acessíveis apenas ao usuário e à equipe de moderação.
- Inclui funcionalidade para fechar tickets e gerar transcrições.

### 3. **Comunicação Oficial**
- Permite que administradores enviem ou atualizem comunicados oficiais em um canal designado.
- Mensagens são persistentes e podem ser editadas.

### 4. **Verificação de Usuários**
- Sistema de verificação para garantir que novos membros não sejam bots.
- Usuários clicam em um botão para se verificar e recebem cargos automaticamente.

### 5. **Moderação**
- Comandos para excluir mensagens em massa.
- Logs de ações de moderação são enviados para um canal específico.

### 6. **Boas-Vindas**
- Envia mensagens de boas-vindas personalizadas para novos membros.
- Inclui links para regras e verificação.

---

## ⚙️ Configuração

### 1. **Pré-requisitos**
- Python 3.10 ou superior.
- Biblioteca `discord.py` versão 2.5.2.
- Biblioteca `python-dotenv` para carregar variáveis de ambiente.

### 2. **Instalação**
1. Clone este repositório:
   ```bash
   git clone https://github.com/seu-usuario/Bot-HalionRP.git
   cd Bot-HalionRP
   ```
2. Crie um arquivo `.env` na raiz do projeto e adicione as seguintes variáveis:
   ```
   DISCORD_TOKEN=seu_token_aqui
   DISCORD_GUILD_ID=123456789012345678
   WHITELIST_ID=123456789012345678
   ```
   
---

## 🛠️ Estrutura do Projeto
