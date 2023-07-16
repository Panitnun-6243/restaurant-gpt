# Note: The openai-python library support for Azure OpenAI is in preview.
import os
import openai
import json

from dotenv import load_dotenv

load_dotenv()

openai.api_type = os.getenv(
    "OPENAI_TYPE"
)  # From Go to Azure AI Studio -> Playground then we can use the API into our application
openai.api_base = os.getenv(
    "OPENAI_BASE_URL"
)  # From Go to Azure AI Studio -> Playground then we can use the API into our application
openai.api_version = os.getenv(
    "OPENAI_VERSION"
)  # From Go to Azure AI Studio -> Playground then we can use the API into our application
openai.api_key = os.getenv(
    "OPENAI_KEY"
)  # From Go to Azure AI Studio -> Playground then we can use the API into our application

completion_engine = os.getenv("OPENAI_COMPLETION_ENGINE")


def ask_azure_gpt(question):
    response = openai.Completion.create(
        engine=completion_engine,
        prompt=question,
        temperature=1,
        max_tokens=1000,
        top_p=0.5,
        frequency_penalty=0,
        presence_penalty=0,
        stop=None,
    )

    return response["choices"][0]["text"].strip()


def ask_azure_dalle(question):
    response = openai.Image.create(prompt=question, size="512x512", n=2)
    return response["data"][0]["url"]


def load_mock_daily_sales():
    with open("./data/mock_daily_sales.json", "r", encoding="utf-8") as file:
        data = json.load(file)
    return data


def load_mock_ingredients():
    with open("./data/mock_ingredients.json", "r", encoding="utf-8") as file:
        data = json.load(file)
    # Convert quantity values to integers
    for ingredient in data["ingredients"]:
        ingredient["quantity"] = int(ingredient["quantity"])

    return data
