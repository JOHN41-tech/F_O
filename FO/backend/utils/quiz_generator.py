from backend.api.perplexity import PerplexityClient
import json
import re

class QuizGenerator:
    def __init__(self):
        self.client = PerplexityClient()
    
    def generate_quiz(self, topic, step_title, step_details):
        """Generate a quiz for a specific learning step"""
        prompt = f"""Create a quiz to test understanding of this learning step:

Topic: {topic}
Step: {step_title}
Details: {step_details}

Generate 5 multiple-choice questions. For each question:
1. Create a clear, specific question
2. Provide 4 answer options (A, B, C, D)
3. Mark the correct answer

Format your response EXACTLY as follows:
Q1: [Question text]
A) [Option A]
B) [Option B]
C) [Option C]
D) [Option D]
Correct: [A/B/C/D]

Q2: [Question text]
...and so on for all 5 questions.

Make questions practical and test real understanding, not just memorization."""

        messages = [{"role": "user", "content": prompt}]
        response = self.client.chat_completion(messages, temperature=0.7)
        quiz_text = response['choices'][0]['message']['content']
        
        return self._parse_quiz(quiz_text)
    
    def _parse_quiz(self, quiz_text):
        """Parse the quiz text into structured format"""
        questions = []
        current_question = None
        
        lines = quiz_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Match question pattern
            q_match = re.match(r'Q(\d+):\s*(.+)', line)
            if q_match:
                if current_question:
                    questions.append(current_question)
                current_question = {
                    'number': int(q_match.group(1)),
                    'question': q_match.group(2),
                    'options': {},
                    'correct': None
                }
                continue
            
            # Match option pattern
            opt_match = re.match(r'([A-D])\)\s*(.+)', line)
            if opt_match and current_question:
                current_question['options'][opt_match.group(1)] = opt_match.group(2)
                continue
            
            # Match correct answer pattern
            corr_match = re.match(r'Correct:\s*([A-D])', line, re.IGNORECASE)
            if corr_match and current_question:
                current_question['correct'] = corr_match.group(1)
                continue
        
        # Add last question
        if current_question:
            questions.append(current_question)
        
        return questions
    
    def check_answer(self, question, user_answer):
        """Check if the user's answer is correct"""
        return user_answer.upper() == question['correct'].upper()
