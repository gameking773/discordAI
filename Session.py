import discord
from providers import AIProvider


class ChatSession:

  def __init__(self, channel: discord.TextChannel):
    self.channel = channel
    self.parse_topic()
    self.reset_history()

  def parse_topic(self):
    topic = self.channel.topic or ""
    self.provider = "groq"
    self.model = ""
    self.apikey = ""
    self.local_base = ""
    self.system_prompt = ""

    parts = topic.split("|")
    for part in parts:
      part = part.strip()
      if part.startswith("provider:"):
        self.provider = part.replace("provider:", "").strip()
      elif part.startswith("model:"):
        self.model = part.replace("model:", "").strip()
      elif part.startswith("apikey:"):
        self.apikey = part.replace("apikey:", "").strip()
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

  def get_reply(self, user_message: str) -> str:
    self.refresh()

    self.add_message("user", user_message)

    reply = AIProvider.generate(
        self.provider, self.model, self.apikey, self.local_base, self.history
    )

    self.add_message("assistant", reply)
    return reply