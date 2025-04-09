import discord
import asyncio
from discord.ui import View, Button
from handlers.questionnaire import start_questionnaire


class WhitelistView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Quero fazer whitelist", style=discord.ButtonStyle.success, custom_id="start_whitelist")
    async def start_whitelist(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message(
            "📝 Criando seu canal de whitelist, aguarde...",
            ephemeral=True
        )

        guild = interaction.guild
        member = interaction.user

        # Verifica se o canal já existe para o usuário
        existing_channel = discord.utils.get(
            guild.text_channels,
            name=f"whitelist-{member.id}"
        )
        if existing_channel:
            await interaction.followup.send(
                "❗ Você já tem um canal de whitelist em andamento.",
                ephemeral=True
            )
            return

        # Permissões do canal
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True)
        }

        # Criação do canal privado
        channel = await guild.create_text_channel(
            name=f"whitelist-{member.id}",
            overwrites=overwrites,
            topic=f"Canal de whitelist para {member.display_name}"
        )

        await channel.send(f"👋 Olá {member.mention}, bem-vindo ao seu teste de whitelist!")
        await asyncio.sleep(2)
        await channel.send("⏳ Você terá **20 minutos** para concluir. Boa sorte!")

        # Inicia o questionário
        await start_questionnaire(member, channel, interaction.client)
