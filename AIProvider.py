class AIProvider:

    @staticmethod
    def generate(provider: str, model: str, apikey: str, local_base: str, history: list) -> str:
        provider = provider.lower().strip()

        if not apikey:
            return "Api Key missing : add 'apikey:your_key' to the subject of the channel"

        return (
            f"[Provider: **{provider}** | Model: **{model}**]\n"
            f"History : {len(history)} messages."
        )