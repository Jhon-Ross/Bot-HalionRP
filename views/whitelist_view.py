import discord
from discord.ui import View, Button


class WhitelistView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Quero fazer whitelist", style=discord.ButtonStyle.success, custom_id="start_whitelist")
    async def start_whitelist(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message(
            "📝 Em breve você será redirecionado para o teste da whitelist!",
            ephemeral=True
        )
        # Aqui futuramente chamamos o início do teste
