from backend.core.roadmap import Roadmap
from backend.api.perplexity import PerplexityClient

class LearningSession:
    def __init__(self, persona="General", difficulty="Intermediate"):
        self.client = PerplexityClient()
        self.roadmap = None
        self.current_step_index = -1
        self.persona = persona
        self.difficulty = difficulty

    def start_new_topic(self, topic):
        print(f"Generating {self.difficulty} roadmap for '{topic}'...")
        raw_roadmap = self.client.generate_roadmap(topic, self.difficulty)
        self.roadmap = Roadmap(topic, raw_roadmap)
        self.current_step_index = 0
        return self.roadmap

    def get_current_step(self):
        if not self.roadmap:
            return None
        return self.roadmap.get_step(self.current_step_index)

    def next_step(self):
        if not self.roadmap:
            return None
        if self.current_step_index < self.roadmap.total_steps - 1:
            self.current_step_index += 1
            return self.get_current_step()
        return None

    def get_detailed_guide_for_step(self):
        """
        Asks Perplexity for a detailed guide on the current step.
        """
        step = self.get_current_step()
        if not step:
            return "No active step."
        
        persona_prompts = {
            "General": "beginner-friendly",
            "Scientist": "highly technical, focused on academic rigor and precise details",
            "ELI5": "very simple, using analogies that a 5-year-old would understand",
            "Socratic": "challenging, using questions to prompt me to think deeper"
        }
        
        persona_instruction = persona_prompts.get(self.persona, "beginner-friendly")
        
        prompt = (
            f"I am learning about {self.roadmap.topic} at an {self.difficulty} level. "
            f"You are a mentor with a {self.persona} teaching style. "
            f"Please provide a detailed, {persona_instruction} guide for step {step['number']}: '{step['title']}'. "
            "Include examples or exercises if applicable. "
            "CRITICAL: Do not use any markdown formatting like hashtags (#), asterisks (*), or bolding. "
            "Use clear, plain text with simple numbering or bullet points using dashes (-) if needed."
        )
        
        messages = [{"role": "user", "content": prompt}]
        response = self.client.chat_completion(messages)
        content = response['choices'][0]['message']['content']
        
        # Clean up any remaining markdown characters
        content = content.replace('#', '').replace('*', '').replace('`', '')
        return content.strip()
