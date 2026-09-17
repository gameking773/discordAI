import discord
from AIProvider import AIProvider


class ChatSession:

  def __init__(self, channel: discord.TextChannel):
    self.channel = channel
    self.parse_topic()
    self.reset_history()

  def parse_topic(self):
    topic = self.channel.topic or ""
    self.provider = "groq"
    self.model = ""
    self.local_base = ""
    self.system_prompt = ""

    parts = topic.split("|")
    for part in parts:
      part = part.strip()
      if part.startswith("provider:"):
        self.provider = part.replace("provider:", "").strip()
      elif part.startswith("model:"):
        self.model = part.replace("model:", "").strip()
      elif part.startswith("localbase:"):
        self.local_base = part.replace("localbase:", "").strip()
      elif part.startswith("system:"):
        self.system_prompt = part.replace("system:", "").strip()

  def refresh(self):
    self.parse_topic()

  def reset_history(self):
    self.history = []
    if self.system_prompt:
      self.history.append({"role": "system", "content": self.system_prompt})

  def add_message(self, role: str, content: str):
    self.history.append({"role": role, "content": content})

    system_messages = [m for m in self.history if m["role"] == "system"]
    chat_messages = [m for m in self.history if m["role"] != "system"]

    max_messages = 20
    if len(chat_messages) > max_messages:
      chat_messages = chat_messages[-max_messages:]

    self.history = system_messages + chat_messages

  def clear(self):
    self.reset_history()

  def get_reply(self, user_message: str, user_config: dict) -> str:
    self.refresh()
    self.add_message("user", user_message)

    provider = user_config.get("provider") or self.provider
    model = user_config.get("model") or self.model
    apikey = user_config.get("apikey", "")
    local_base = user_config.get("local_base") or self.local_base

    reply = AIProvider.generate(
        provider, model, apikey, local_base, self.history
    )

    self.add_message("assistant", reply)
    return reply