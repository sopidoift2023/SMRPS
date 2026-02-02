
def generate_cbt_questions(school_class, subject, num_questions=10):
    """
    Returns a list of dicts: [{text, option_a, option_b, option_c, option_d, correct_option}]
    Uses demo mode if AI_DEMO_MODE is True.
    """
    from django.conf import settings
    if getattr(settings, 'AI_DEMO_MODE', False):
        # Demo/mock questions
        return [
            {
                "text": f"Sample Question {i+1} for {subject.name} in {school_class.name}?",
                "option_a": "Option A",
                "option_b": "Option B",
                "option_c": "Option C",
                "option_d": "Option D",
                "correct_option": "A"
            }
            for i in range(num_questions)
        ]
    # Real API call (pseudo, adapt as needed)
    # You can use DeepSeekService or similar logic here
    # For now, return empty list if not demo
    return []
import json
from django.conf import settings
from openai import OpenAI
from .models import AIConversation, AIContent

class DeepSeekService:
    def __init__(self):
        self.api_key = getattr(settings, 'DEEPSEEK_API_KEY', '')
        self.base_url = getattr(settings, 'DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
        self.model = getattr(settings, 'DEEPSEEK_MODEL', 'deepseek-chat')
        self.demo_mode = getattr(settings, 'AI_DEMO_MODE', False)
        if not self.demo_mode:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        else:
            self.client = None

    def get_system_prompt(self, level):
        """
        Returns a system prompt tuned for WAEC (West African) standards.
        """
        waec_context = (
            "You are an expert educator specializing in the West African curriculum. "
            "You are providing content for a Nigerian school system. "
            "Your output must align with WAEC (WASSCE) for Senior Secondary and BECE for Junior Secondary standards. "
        )
        
        if "Senior" in level or "WASSCE" in level.upper():
            return waec_context + "Focus on Senior WAEC (WASSCE) depth and rigor."
        elif "Junior" in level or "BECE" in level.upper():
            return waec_context + "Focus on Junior WAEC (BECE) standards."
        
        return waec_context

    def generate_questions(self, teacher, subject, level, topic, num_objective=10, num_theory=5):
        """
        Generates exam questions (Objective and Theory).
        """
        system_prompt = self.get_system_prompt(level)
        user_prompt = (
            f"Generate {num_objective} objective (multiple choice) questions and {num_theory} theory (essay) questions "
            f"for {subject} on the topic '{topic}'.\n\n"
            "Format the output clearly using Markdown:\n"
            "## SECTION A: OBJECTIVE QUESTIONS\n"
            "1. [Question Text]\n   A. [Option]\n   B. [Option]\n   C. [Option]\n   D. [Option]\n\n"
            "## SECTION B: THEORY QUESTIONS\n"
            "1. [Question Text]\n\n"
            "Include an answer key at the very end."
        )

        try:
            if self.demo_mode:
                generated_text = (
                    f"## SECTION A: OBJECTIVE QUESTIONS ({level})\n"
                    f"1. What is the primary focus of {topic} in {subject}?\n"
                    "   A. Option 1\n   B. Option 2\n   C. Option 3\n   D. Option 4\n\n"
                    f"2. How does {topic} apply to real-world scenarios?\n"
                    "   A. Industry\n   B. Education\n   C. Research\n   D. All of the above\n\n"
                    "*(Demo Mode: Questions truncated)*\n\n"
                    "## SECTION B: THEORY QUESTIONS\n"
                    f"1. Explain the fundamental principles of {topic}.\n"
                    f"2. Discuss the impact of {subject} on modern society.\n\n"
                    "## ANSWER KEY\n1. D  2. D"
                )
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    stream=False
                )
                generated_text = response.choices[0].message.content
            
            # Save to database
            content = AIContent.objects.create(
                teacher=teacher,
                content_type='QUESTION',
                subject=subject,
                topic=topic,
                level=level,
                generated_text=generated_text
            )
            
            return generated_text, content.id
        except Exception as e:
            return f"Error generating questions: {str(e)}", None

    def generate_lesson_note(self, teacher, subject, level, topic):
        """
        Generates a comprehensive lesson note.
        """
        system_prompt = self.get_system_prompt(level)
        user_prompt = (
            f"Generate a comprehensive lesson note for {subject} on the topic '{topic}' for {level} level.\n\n"
            "Include:\n"
            "- Learning Objectives\n"
            "- Introduction\n"
            "- Content breakdown (with explanations)\n"
            "- Summary\n"
            "- Evaluation/Review Questions."
        )

        try:
            if self.demo_mode:
                generated_text = (
                    f"# Lesson Note: {topic} for {level} {subject}\n\n"
                    "## Learning Objectives\n"
                    f"- Understand the core concepts of {topic}.\n"
                    f"- Identify the relationship between {subject} and {topic}.\n\n"
                    "## Introduction\n"
                    f"{topic} is a critical component of {subject} that governs how systems operate...\n\n"
                    "## Content Breakdown\n"
                    "### Detailed Overview\n"
                    "The following principles are essential to mastery...\n\n"
                    "## Summary\n"
                    f"In this lesson, we explored {topic} and its various applications.\n\n"
                    "## Evaluation\n"
                    "1. Define the topic.\n"
                    "2. List three key features."
                )
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    stream=False
                )
                generated_text = response.choices[0].message.content
            
            # Save to database
            content = AIContent.objects.create(
                teacher=teacher,
                content_type='NOTE',
                subject=subject,
                topic=topic,
                level=level,
                generated_text=generated_text
            )
            
            return generated_text, content.id
        except Exception as e:
            return f"Error generating lesson note: {str(e)}", None

    def chat(self, teacher, session_id, user_message):
        """
        Generic chat integration with conversation history.
        """
        conversation, created = AIConversation.objects.get_or_create(
            teacher=teacher,
            session_id=session_id
        )
        
        history = conversation.history or []
        
        # Limit history to last 10 turns to save tokens
        messages = [{"role": "system", "content": "You are a helpful AI Teacher Assistant for SMRPS."}]
        for turn in history[-10:]:
            messages.append(turn)
        
        messages.append({"role": "user", "content": user_message})

        try:
            if self.demo_mode:
                ai_message = f"I am currently in **Demo Mode**. You asked: '{user_message}'. In a live environment, I would provide a detailed response based on our WAEC-aligned model."
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    stream=False
                )
                ai_message = response.choices[0].message.content
            
            # Update history
            history.append({"role": "user", "content": user_message})
            history.append({"role": "assistant", "content": ai_message})
            conversation.history = history
            conversation.save()
            
            return ai_message
        except Exception as e:
            return f"Error in chat: {str(e)}"
