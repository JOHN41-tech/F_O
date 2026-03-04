import os
import requests

class PerplexityClient:
    """
    Groq client — uses Groq's OpenAI-compatible API for ultra-fast inference.
    API reference: https://console.groq.com/docs/openai
    """
    def __init__(self, api_key=None, base_url="https://api.groq.com/openai/v1"):
        self.api_key = api_key or os.getenv("GROQ_API_KEY") or os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            # For demonstration, we'll allow it to initialize but warn later
            # This prevents the app from crashing on startup
            print("WARNING: GROQ_API_KEY or PERPLEXITY_API_KEY not found in .env file.")
            self.api_key = "placeholder_key"
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def chat_completion(self, messages, model="llama-3.3-70b-versatile", temperature=0.2):
        """
        Send a chat completion request to the Groq API.
        Popular models: llama-3.3-70b-versatile, mixtral-8x7b-32768, gemma2-9b-it
        """
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature
        }

        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error calling Groq API: {e}")
            raise

    def generate_roadmap(self, topic, difficulty="Intermediate"):
        """
        Generate a structured learning roadmap for a topic.
        """
        system_prompt = (
            "You are an expert curriculum designer. "
            f"Create a structured learning roadmap for the given topic at an {difficulty} level. "
            "Return the response as a clear, numbered list of main topics, "
            "with sub-points for each. Do not include conversational filler."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": f"Create a learning roadmap for: {topic}"}
        ]
        result = self.chat_completion(messages)
        return result['choices'][0]['message']['content']
