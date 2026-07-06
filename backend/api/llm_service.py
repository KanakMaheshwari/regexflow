import json
import re
import requests


OLLAMA_URL = "http://host.docker.internal:11434/api/generate"
MODEL_NAME = "llama3:latest"

MAX_RETRIES = 3


def generate_regex(prompt):

    previous_regex = ""

    for attempt in range(MAX_RETRIES):

        llm_prompt = f"""
You are an expert Python regular expression generator.

Convert the user's natural-language request into ONE Python-compatible regular expression.

Return ONLY JSON:

{{"regex": "pattern"}}

Rules:
- Return valid JSON only.
- Do not include markdown.
- Do not include explanations.
- The regex must work with Python re and pandas str.replace.
- Do not include quotes, commas, colons, or other JSON syntax inside the regex unless required by the user's pattern.

User request:
{prompt}

Previous incorrect regex:
{previous_regex}
"""

        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": llm_prompt,
                "stream": False,
                "format": "json"
            },
            timeout=120
        )

        response.raise_for_status()

        result = response.json()

        generated_text = result["response"]

        regex_data = json.loads(generated_text)

        if "regex" not in regex_data:
            previous_regex = "Missing regex field"
            continue

        regex = regex_data["regex"]

        if not isinstance(regex, str):
            previous_regex = str(regex)
            continue

        try:
            re.compile(regex)

        except re.error:
            previous_regex = regex
            continue

        if validate_regex(prompt, regex):

            print(
                f"Valid regex generated on attempt {attempt + 1}: {regex}",
                flush=True
            )

            return {
                "regex": regex
            }

        print(
            f"Regex failed validation: {regex}",
            flush=True
        )

        previous_regex = regex

    raise ValueError(
        "Unable to generate a valid regex after 3 attempts."
    )


def validate_regex(prompt, regex):

    prompt = prompt.lower()

    if "email" in prompt:

        positive_examples = [
            "john@gmail.com",
            "sarah.jones@yahoo.com",
            "user123@outlook.com"
        ]

        negative_examples = [
            "not-an-email",
            "john@gmail",
            "@gmail.com"
        ]

        for example in positive_examples:

            if not re.search(regex, example):
                return False

        for example in negative_examples:

            if re.search(regex, example):
                return False

    return True