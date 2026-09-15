import discord
import os
from discord import app_commands, ui
from Session import ChatSession

class ConfigModal(ui.Modal, title="Configuration API (BYOK)"):
  provider = ui.TextInput(
      label="Provider",
      placeholder="ex : groq, gemini, claude, local",
      default="gemini",
      max_length=20,
  )
  model = ui.TextInput(
      label="Model",
      placeholder="ex: llama-3.3-70b-versatile",
      required=False,
      max_length=100,
  )
  apikey = ui.TextInput(
      label="API Key",
      placeholder="Put your API Key",
      style=discord.TextStyle.paragraph,
      required=True,
  )

  def __init__(self, bot_instance):
    super().__init__()
    self.bot_instance = bot_instance

  async def on_submit(self, interaction: discord.Interaction):
    # Stockage sous forme de dictionnaire indexé par le user_id Discord
    self.bot_instance.user_configs[interaction.user.id] = {
        "provider": self.provider.value.strip().lower(),
        "model": self.model.value.strip(),
        "apikey": self.apikey.value.strip(),
    }
    await interaction.response.send_message(
        "Configuration saved !",
        ephemeral=True,
    )

class DiscordAIBot(discord.Client):

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.tree = app_commands.CommandTree(self)
    self.sessions = {}
    self.user_configs = {}

  async def setup_hook(self):
    await self.tree.sync()

  async def on_ready(self):
    print(f"Bot connected and ready : {self.user}")

  def get_session(self, channel: discord.TextChannel) -> ChatSession:
    if channel.id not in self.sessions:
      self.sessions[channel.id] = ChatSession(channel)
    return self.sessions[channel.id]

  @staticmethod
  def split_message(text: str, limit: int = 1900) -> list[str]:
    if len(text) <= limit:
      return [text]

    chunks = []
    current_chunk = []
    current_length = 0
    in_code_block = False
    code_language = ""

    for line in text.split("\n"):
      if line.strip().startswith("```"):
        if not in_code_block:
          in_code_block = True
          code_language = line.strip()[3:]
        else:
          in_code_block = False
          code_language = ""

      if current_length + len(line) + 1 > limit:
        if in_code_block:
          current_chunk.append("```")

        chunks.append("\n".join(current_chunk))
        current_chunk = []
        current_length = 0

        if in_code_block:
          opening = f"```{code_language}"
          current_chunk.append(opening)
          current_length += len(opening) + 1

      current_chunk.append(line)
      current_length += len(line) + 1

    if current_chunk:
      chunks.append("\n".join(current_chunk))

    return chunks

  async def on_message(self, message):
    if message.author == self.user or not isinstance(message.channel, discord.TextChannel):
      return

    if self.user in message.mentions:
      user_config = self.user_configs.get(message.author.id)
      if not user_config:
        await message.reply(
            "You didn't config your API Key ! Use `/config` to add it"
        )
        return
      
      prompt = message.content.replace(f"<@{self.user.id}>", "").strip()
      if not prompt:
        return

      session = self.get_session(message.channel)

      async with message.channel.typing():
        reply = session.get_reply(prompt, user_config)

      chunks = self.split_message(reply)
      for chunk in chunks:
        await message.channel.send(chunk)

  async def on_guild_channel_update(self, before, after):
    if isinstance(after, discord.TextChannel) and after.id in self.sessions:
      self.sessions[after.id].refresh()


intents = discord.Intents.default()
intents.message_content = True

bot = DiscordAIBot(intents=intents)


@bot.tree.command(
    name="config",
    description="Configure your API Key",
)
async def config_command(interaction: discord.Interaction):
  await interaction.response.send_modal(ConfigModal(bot))

@bot.tree.command(
    name="clear", 
    description="Clear channel history from bot memory"
)
async def clear_command(interaction: discord.Interaction):
  if not isinstance(interaction.channel, discord.TextChannel):
    return

  session = bot.get_session(interaction.channel)
  session.clear()
  await interaction.response.send_message(
      "Channel's history cleared", ephemeral=False
  )

@bot.tree.command(
    name="forget", description="Delete API Key from RAM"
)
async def forget_command(interaction: discord.Interaction):
  if interaction.user.id in bot.user_configs:
    del bot.user_configs[interaction.user.id]
    await interaction.response.send_message(
        "configuration and API Key cleared",
        ephemeral=True,
    )
  else:
    await interaction.response.send_message(
        "No key registered", ephemeral=True
    )

if __name__ == "__main__":
  token = os.getenv("DISCORD_TOKEN") or input("Enter your Discord Token : ").strip()
  bot.run(token)