import re

class Roadmap:
    def __init__(self, topic, raw_content):
        self.topic = topic
        self.steps = self._parse_content(raw_content)
        self.total_steps = len(self.steps)

    def _parse_content(self, raw_content):
        """
        Parses the raw text content into a list of steps.
        Assumes a numbered list format (1. Step One...).
        """
        steps = []
        lines = raw_content.split('\n')
        
        current_step = None
        
        for line in lines:
            line = line.strip()
            # Match lines starting with "1. ", "2. ", etc.
            match = re.match(r'^(\d+)\.\s+(.*)', line)
            if match:
                if current_step:
                    steps.append(current_step)
                
                # Clean title of any markdown residue
                title = match.group(2).replace('*', '').replace('#', '').replace('`', '').strip()
                
                current_step = {
                    "number": int(match.group(1)),
                    "title": title,
                    "details": []
                }
            elif current_step and line:
                # Clean detail of any markdown residue
                detail = line.replace('*', '').replace('#', '').replace('`', '').strip()
                if detail:
                    current_step["details"].append(detail)
        
        if current_step:
            steps.append(current_step)
            
        return steps

    def get_step(self, index):
        if 0 <= index < self.total_steps:
            return self.steps[index]
        return None
