import discord
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

      if len(reply) > 2000:
        reply = reply[:1997] + "..."

      await message.reply(reply)

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


if __name__ == "__main__":
  token = input("Enter your Discord Token : ").strip()
  bot.run(token)