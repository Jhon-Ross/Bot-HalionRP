import discord
import asyncio
from datetime import datetime, timedelta, timezone

cooldowns = {}

questions = [
    "1️⃣ Qual é a sua idade?",
    "2️⃣ Você já jogou em outros servidores de RP?",
    "3️⃣ O que você entende por 'roleplay'?",
    "4️⃣ Como você reagiria a uma situação de assalto no jogo?",
    "5️⃣ O que você faria se encontrasse um bug no servidor?",
]


async def start_questionnaire(member: discord.Member, channel: discord.TextChannel, bot: discord.Client):
    now = datetime.now(timezone.utc)

    # Verifica se o jogador está em cooldown
    if member.id in cooldowns and cooldowns[member.id] > now:
        remaining = (cooldowns[member.id] - now).seconds // 60
        await channel.send(f"❌ Você precisa esperar **{remaining} minutos** para tentar novamente a whitelist.")
        await asyncio.sleep(10)
        await channel.delete()
        return

    # Define um novo cooldown de 30 minutos
    cooldowns[member.id] = now + timedelta(minutes=30)

    def check(m):
        return m.author == member and m.channel == channel

    respostas = []
    start_time = datetime.now(timezone.utc)
    total_timeout = 20 * 60  # 20 minutos

    for pergunta in questions:
        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        if elapsed >= total_timeout:
            await channel.send("⏰ Tempo total esgotado! Você demorou mais de 20 minutos.")
            cooldowns[member.id] = datetime.now(
                timezone.utc) + timedelta(minutes=30)
            await asyncio.sleep(10)
            await channel.delete()
            return

        await channel.send(pergunta)
        try:
            remaining_time = total_timeout - elapsed
            msg = await bot.wait_for('message', check=check, timeout=remaining_time)
            respostas.append((pergunta, msg.content))
        except asyncio.TimeoutError:
            await channel.send("⏰ Tempo esgotado! Você demorou para responder.")
            cooldowns[member.id] = datetime.now(
                timezone.utc) + timedelta(minutes=30)
            await asyncio.sleep(10)
            await channel.delete()
            return

    await channel.send("✅ Você concluiu o teste! Suas respostas serão avaliadas pela equipe.")

    # Envia para canal da staff
    staff_channel = discord.utils.get(
        channel.guild.text_channels, name="respostas-whitelist")
    if staff_channel:
        embed = discord.Embed(
            title=f"📋 Respostas de {member.display_name} ({member.id})",
            color=discord.Color.green()
        )
        for idx, (pergunta, resposta) in enumerate(respostas, 1):
            embed.add_field(
                name=f"{idx}.", value=f"**{pergunta}**\n{resposta}", inline=False)
        await staff_channel.send(embed=embed)

    await asyncio.sleep(15)
    await channel.delete()
