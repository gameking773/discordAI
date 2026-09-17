import os
import aiohttp
import discord
from discord import app_commands, ui
from Session import ChatSession

class ModelSelectView(ui.View):
  def __init__(self, bot_instance, provider: str, api_key: str, options: list[discord.SelectOption]):
    super().__init__(timeout=120)
    self.bot = bot_instance
    self.provider = provider
    self.api_key = api_key
    self.select_menu.options = options

  @ui.select(placeholder="Select your model...")
  async def select_menu(self, interaction: discord.Interaction, select: ui.Select):
    selected_model = select.values[0]
    self.bot.user_configs[interaction.user.id] = {
        "provider": self.provider,
        "model": selected_model,
        "apikey": self.api_key,
    }
    await interaction.response.send_message(
        f"Configuration saved\n"
        f"• **Provider :** `{self.provider}`\n"
        f"• **Model :** `{selected_model}`",
        ephemeral=True,
    )

class ApiKeyModal(ui.Modal, title="Validation de la Clé API"):
  api_key = ui.TextInput(
      label="API Key / Token",
      placeholder="Paste your API Key here...",
      required=True,
      style=discord.TextStyle.short,
  )

  def __init__(self, bot_instance, provider: str):
    super().__init__()
    self.bot = bot_instance
    self.provider = provider

  async def on_submit(self, interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    key = self.api_key.value.strip()

    models = await self.bot.fetch_models_with_key(self.provider, key)

    if not models:
      await interaction.followup.send(
          f"Can't retrieve models for `{self.provider}`.\n"
          "Check the integrity of your key or use the advances mode.",
          ephemeral=True,
      )
      return

    view = ModelSelectView(self.bot, self.provider, key, models)
    await interaction.followup.send(
        f"Key OK, Choose your model for `{self.provider}` :",
        view=view,
        ephemeral=True,
    )

class AdvancedConfigModal(ui.Modal, title="Advanced configuration (Manual)"):
  provider = ui.TextInput(
      label="Provider",
      placeholder="ex : groq, openrouter, gemini, claude, local",
      required=True,
      max_length=20,
  )
  model = ui.TextInput(
      label="Model",
      placeholder="ex : llama-3.3-70b-versatile",
      required=True,
      max_length=100,
  )
  apikey = ui.TextInput(
      label="API Key",
      placeholder="Your API Key (optional if local)",
      style=discord.TextStyle.short,
      required=False,
  )
  local_base = ui.TextInput(
      label="URL Serveur (Optional)",
      placeholder="http://localhost:8000/v1",
      required=False,
  )

  def __init__(self, bot_instance):
    super().__init__()
    self.bot = bot_instance

  async def on_submit(self, interaction: discord.Interaction):
    p_val = self.provider.value.strip().lower()
    m_val = self.model.value.strip()
    k_val = self.apikey.value.strip()
    b_val = self.local_base.value.strip()

    self.bot.user_configs[interaction.user.id] = {
        "provider": p_val,
        "model": m_val,
        "apikey": k_val,
        "local_base": b_val,
    }

    resp = f"⚙️ **Manual Config saved !**\n• **Provider :** `{p_val}`\n• **Modèle :** `{m_val}`"
    if b_val:
      resp += f"\n• **Base URL :** `{b_val}`"

    await interaction.response.send_message(resp, ephemeral=True)


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
  async def fetch_models_with_key(
      provider: str, api_key: str
  ) -> list[discord.SelectOption]:
    """Interroge l'API du provider avec la clé saisie pour lister les modèles."""
    options = []
    headers = {"Authorization": f"Bearer {api_key}"}
    endpoints = {
        "openai": "https://api.openai.com/v1/models",
        "groq": "https://api.groq.com/openai/v1/models",
        "openrouter": "https://openrouter.ai/api/v1/models",
    }

    try:
      async with aiohttp.ClientSession() as session:
        if provider in endpoints:
          async with session.get(endpoints[provider], headers=headers) as resp:
            if resp.status == 200:
              data = await resp.json()
              models = data.get("data", [])

              if provider == "openrouter":
                free_models = [m for m in models if m["id"].endswith(":free")]
                models = free_models if free_models else models

              for m in models[:25]:
                m_id = m["id"]
                options.append(
                    discord.SelectOption(
                        label=m_id.split("/")[-1][:25],
                        value=m_id,
                        description=m_id[:50],
                    )
                )

        # Hugging Face API
        elif provider == "huggingface":
          url = "https://huggingface.co/api/models?pipeline_tag=text-generation&limit=25"
          async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
              data = await resp.json()
              for m in data[:25]:
                m_id = m["id"]
                options.append(
                    discord.SelectOption(
                        label=m_id.split("/")[-1][:25],
                        value=m_id,
                        description=m_id[:50],
                    )
                )

        # Google Gemini API
        elif provider == "gemini":
          url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
          async with session.get(url) as resp:
            if resp.status == 200:
              data = await resp.json()
              for m in data.get("models", [])[:25]:
                name = m["name"].replace("models/", "")
                options.append(
                    discord.SelectOption(
                        label=name[:25],
                        value=name,
                        description=name[:50],
                    )
                )
    except Exception as e:
      print(f"Erreur fetch_models_with_key ({provider}): {e}")

    return options

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
    if message.author == self.user or not isinstance(
        message.channel, discord.TextChannel
    ):
      return

    if self.user in message.mentions:
      user_config = self.user_configs.get(message.author.id)
      if not user_config:
        await message.reply(
            "API Key not configured ! Use `/config`."
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
  view = ConfigView(bot)
  await interaction.response.send_message(
      "⚙️ **Configuration API (BYOK)**\nChoose your provider or use the advanced mode :",
      view=view,
      ephemeral=True,
  )

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