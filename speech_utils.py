import random
import re
from typing import List
from prompts import natural_laughter, add_speech_imperfections, blend_languages

def process_speech(text: str, user_input: str, mode: str = "chaotic") -> str:
    """
    Process text to make it sound more natural:
    - Adds laughter when earned
    - Adds speech imperfections
    - Blends Kiswahili & English if user code-switches
    """
    if not text or text.strip() == "":
        return text
    
    # Step 1: Add natural laughter where appropriate
    text = add_natural_laughter(text, mode, user_input)
    
    # Step 2: Add speech imperfections (fillers, pauses)
    text = add_speech_imperfections(text, mode)
    
    # Step 3: Blend languages if user used Kiswahili
    text = blend_languages(text, user_input)
    
    return text

def add_natural_laughter(text: str, mode: str, user_input: str) -> str:
    """
    Add laughter naturally if user’s message or response context calls for it
    """
    laughter_triggers = [
        r"😂", r"🤣", r"lol", r"lmao", r"hilarious", r"haha", 
        r"joke", r"funny", r"banter", r"wild"
    ]
    
    sentences = re.split(r'(?<=[.!?])\s+', text)
    result = []
    
    for sentence in sentences:
        should_laugh = any(re.search(trigger, user_input.lower()) for trigger in laughter_triggers)
        random_laugh = random.random() < 0.15 and len(sentence.split()) > 3
        
        if should_laugh or random_laugh:
            laughter_intensity = "medium"
            if any(word in user_input.lower() for word in ["hilarious", "dying", "lmao"]):
                laughter_intensity = "high"
            
            position = random.choice(["start", "middle", "end"])
            if position == "start":
                laughter = natural_laughter(laughter_intensity, mode) + ", "
                sentence = laughter + sentence
            elif position == "middle" and len(sentence.split()) > 4:
                words = sentence.split()
                insert_pos = random.randint(2, len(words) - 2)
                words.insert(insert_pos, natural_laughter(laughter_intensity, mode))
                sentence = " ".join(words)
            else:
                sentence = sentence + " " + natural_laughter(laughter_intensity, mode)
        
        result.append(sentence)
    
    return " ".join(result)
