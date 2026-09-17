from anthropic import Anthropic
from google import genai
from groq import Groq
from openai import OpenAI


class AIProvider:

  @staticmethod
  def _handle_local(
      apikey: str, model: str, history: list, local_base: str
  ) -> str:
    client = OpenAI(
        base_url=local_base or "http://localhost:8000/v1",
        api_key=apikey or "not-needed",
    )
    response = client.chat.completions.create(
        model=model or "default", messages=history
    )
    return response.choices[0].message.content

  @staticmethod
  def _handle_openai(
      apikey: str, model: str, history: list, local_base: str
  ) -> str:
    client = OpenAI(api_key=apikey)
    response = client.chat.completions.create(
        model=model or "gpt-4o-mini", messages=history
    )
    return response.choices[0].message.content

  @staticmethod
  def _handle_groq(
      apikey: str, model: str, history: list, local_base: str
  ) -> str:
    client = Groq(api_key=apikey)
    response = client.chat.completions.create(
        model=model or "llama-3.3-70b-versatile", messages=history
    )
    return response.choices[0].message.content

  @staticmethod
  def _handle_openrouter(
      apikey: str, model: str, history: list, local_base: str
  ) -> str:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=apikey,
    )
    response = client.chat.completions.create(
        model=model or "meta-llama/llama-3.3-70b-instruct:free",
        messages=history,
    )
    return response.choices[0].message.content

  @staticmethod
  def _handle_huggingface(
      apikey: str, model: str, history: list, local_base: str
  ) -> str:
    client = OpenAI(
        base_url="https://router.huggingface.co/hf-inference/v1",
        api_key=apikey,
    )
    response = client.chat.completions.create(
        model=model or "Qwen/Qwen2.5-Coder-32B-Instruct",
        messages=history,
    )
    return response.choices[0].message.content

  @staticmethod
  def _handle_gemini(
      apikey: str, model: str, history: list, local_base: str
  ) -> str:
    client = genai.Client(api_key=apikey)
    prompt = history[-1]["content"] if history else ""
    response = client.models.generate_content(
        model=model or "gemini-2.5-flash", contents=prompt
    )
    return response.text

  @staticmethod
  def _handle_claude(
      apikey: str, model: str, history: list, local_base: str
  ) -> str:
    client = Anthropic(api_key=apikey)
    system_prompt = next(
        (m["content"] for m in history if m["role"] == "system"), None
    )
    filtered_history = [m for m in history if m["role"] != "system"]

    response = client.messages.create(
        model=model or "claude-3-5-sonnet-20241022",
        max_tokens=1024,
        system=system_prompt or "",
        messages=filtered_history,
    )
    return response.content[0].text

  @classmethod
  def generate(
      cls,
      provider: str,
      model: str,
      apikey: str,
      local_base: str,
      history: list,
  ) -> str:
    provider = provider.lower().strip()

    if not apikey and provider != "local":
      return "Missing API Key. use `/config`."[cite: 4]

    handlers = {
        "openai": cls._handle_openai,
        "chatgpt": cls._handle_openai,
        "groq": cls._handle_groq,
        "openrouter": cls._handle_openrouter,
        "huggingface": cls._handle_huggingface,
        "hf": cls._handle_huggingface,
        "gemini": cls._handle_gemini,
        "claude": cls._handle_claude,
        "local": cls._handle_local,
    }

    handler = handlers.get(provider)

    if not handler:
      return f"Unknown Provider : `{provider}`"[cite: 4]

    try:
      return handler(apikey, model, history, local_base)
    except Exception as e:
      return f"API Error ({provider}) : `{str(e)}`"