import discord
from Session import ChatSession


class DiscordAIBot(discord.Client):

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.sessions = {}

  async def on_ready(self):
    print(f"Bot connected and ready : {self.user}")

  def get_session(self, channel: discord.TextChannel) -> ChatSession:
    if channel.id not in self.sessions:
      self.sessions[channel.id] = ChatSession(channel)
    return self.sessions[channel.id]

  async def on_message(self, message):
    if message.author == self.user:
      return

    if not isinstance(message.channel, discord.TextChannel):
      return

    if self.user in message.mentions:
      prompt = message.content.replace(f"<@{self.user.id}>", "").strip()
      if not prompt:
        return

      session = self.get_session(message.channel)

      async with message.channel.typing():
        reply = session.get_reply(prompt)

      if len(reply) > 2000:
        reply = reply[:1997] + "..."

      await message.reply(reply)

  async def on_guild_channel_update(self, before, after):
    if isinstance(after, discord.TextChannel) and after.id in self.sessions:
      self.sessions[after.id].refresh()


if __name__ == "__main__":
  token = input("Enter your Discord Token : ").strip()

  intents = discord.Intents.default()
  intents.message_content = True

  bot = DiscordAIBot(intents=intents)
  bot.run(token)