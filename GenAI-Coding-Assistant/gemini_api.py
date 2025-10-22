import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
# Securely fetching the API key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

genai.configure(api_key=GOOGLE_API_KEY)

model = genai.GenerativeModel("gemini-1.5-flash")

def generate_hint(question, user_code):
    prompt = f"""
You are a coding tutor. A student is trying to solve the following problem:

{question}

They submitted this code:
{user_code}

Please provide constructive feedback or a hint without giving the full answer.
"""
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating feedback: {e}"
