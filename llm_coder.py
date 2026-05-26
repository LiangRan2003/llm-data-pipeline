import os
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Initialize OpenAI Client
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
)

def generate_cleaning_script(df_sample: pd.DataFrame, requirements: str, error_feedback: str = None, previous_code: str = None) -> str:
    """
    Calls the LLM to generate or fix a Python script for cleaning the data.
    """
    sample_csv = df_sample.head(5).to_csv(index=False)
    
    prompt = f"""
You are a Data Engineering AI. Your task is to write a Python script using pandas to clean a messy dataset.
Here is a sample of the raw dataset in CSV format:
{sample_csv}

Requirements for the cleaned data:
{requirements}

Output requirements:
- Write a Python function named `clean_data(df: pd.DataFrame) -> pd.DataFrame`.
- The function must take a pandas DataFrame as input and return the cleaned DataFrame.
- Do NOT output any markdown blocks (like ```python ... ```). Output ONLY the raw Python code.
"""

    if error_feedback and previous_code:
        prompt += f"""
        
The previous code you generated failed with the following error:
{error_feedback}

Here is the previous code:
{previous_code}

Please fix the error and provide the corrected Python code. Output ONLY the raw Python code.
"""
    
    # We use deepseek-chat if using deepseek, else gpt-3.5-turbo/gpt-4o depending on the key.
    # We will use the standard compatible model name parameter, or let the user override it in .env.
    model_name = os.getenv("LLM_MODEL_NAME", "deepseek-chat") 
    
    print(f"Calling LLM ({model_name}) to generate cleaning script...")
    
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "You are a senior data engineer."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1
    )
    
    code = response.choices[0].message.content.strip()
    
    # Simple cleanup if LLM still wrapped it in markdown
    if code.startswith("```python"):
        code = code[9:]
    if code.startswith("```"):
        code = code[3:]
    if code.endswith("```"):
        code = code[:-3]
        
    return code.strip()

