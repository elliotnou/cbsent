import os
from typing import List
from openai import OpenAI
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

class SentenceAnalysis(BaseModel):
    text: str = Field(description="The original sentence from paragraph")
    topic: str = Field(description="Primary topic: Inflation, Growth, Employment, Guidance, or Boilerplate")
    score: float = Field(description="Hawkish/Dovish score (-1.0 to 1.0)")
    weight: float = Field(description="Importance weight from 0.0 to 1.0 based on market impact")
    reasoning: str = Field(description="Brief logic for the classification")

class ParagraphAnalysis(BaseModel):
    sentences: List[SentenceAnalysis]

class ToneAnalyzer:
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.model = "gpt-4o-mini"

    def analyze_paragraph(self, text: str) -> ParagraphAnalysis:
        prompt = f"""
        Analyze this central bank paragraph sentence-by-sentence as a Senior Macro Quant.
        
        1. Assign weights:
        - 1.0: Interest Rate Guidance & Inflation (Critical)
        - 0.7: Employment & GDP Growth (Important)
        - 0.4: Global Risks / External Factors (Secondary)
        - 0.0: Boilerplate
        
        2. Assign score:
        Assign a float between -1.0 and 1.0. 
        
        Use this intensity scale for your calculation:
        - ±0.1 to 0.3: Subtle lean. Uses cautious modality ("noted", "monitored", "appears").
        - ±0.4 to 0.6: Clear stance. Uses active verbs ("expects", "indicates", "projected").
        - ±0.7 to 0.9: Aggressive signal. Uses urgent adjectives ("essential", "robust", "deteriorating").
        
        3. Reasoning requirements:
        Before assigning the score, identify:
        - Directionality: (Hawkish vs Dovish)
        - Modality: How certain is the bank? (e.g., 'might' vs 'will')
        - Intensity of adverbs: How fast or strong is the move? (e.g., 'gradually' vs 'rapidly')
        
        Paragraph: {text}
        """
        try:
            completion = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a high-precision macro sentiment engine. You do not use rounded numbers, you provide justified scores."},
                    {"role": "user", "content": prompt}
                ],
                response_format=ParagraphAnalysis,
            )
            return completion.choices[0].message.parsed
        except Exception as e:
            print(f"Error: {e}")
            return None