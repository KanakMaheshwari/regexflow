import json
import re

import requests

from .regex_validator import validate_regex_safety


OLLAMA_URL = "http://host.docker.internal:11434/api/generate"
MODEL_NAME = "llama3:latest"

MAX_RETRIES = 3


def generate_regex(prompt, sample_values=None):

    sample_values = sample_values or []

    previous_regex = ""
    feedback = ""

    for attempt in range(MAX_RETRIES):

        samples_text = "\n".join(
            str(value)
            for value in sample_values[:10]
        )

        llm_prompt = f"""
You are an expert Python regular expression generator.

Convert the user's natural-language request into ONE Python-compatible regular expression.

Return ONLY valid JSON in exactly this format:

{{"regex": "pattern"}}

Rules:
- Return JSON only.
- Do not include markdown.
- Do not include explanations.
- Return exactly one regex pattern.
- The regex must work with Python re and pandas str.replace.
- Generate the regex based on the user's instruction.
- Use the sample values only to understand the data format.
- Do not generate a regex that matches every value unless the instruction requires it.
- Avoid nested quantifiers that may cause catastrophic backtracking.
- Avoid unnecessarily complex regex patterns.

User instruction:
{prompt}

Sample values from the dataset:
{samples_text}

Previous failed regex:
{previous_regex}

Failure feedback:
{feedback}
"""

        try:
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

            regex_data = json.loads(
                generated_text
            )

        except requests.exceptions.RequestException:
            raise

        except (
            json.JSONDecodeError,
            KeyError,
            TypeError
        ) as error:

            feedback = (
                f"Invalid LLM response: {error}"
            )

            print(
                f"Attempt {attempt + 1}: "
                f"invalid LLM response.",
                flush=True
            )

            continue

        if "regex" not in regex_data:

            feedback = (
                "Response did not contain "
                "a regex field."
            )

            continue

        regex = regex_data["regex"]

        if not isinstance(regex, str):

            feedback = (
                "Generated regex was not "
                "a string."
            )

            continue

        try:
            validate_regex_safety(regex)

            compiled_regex = re.compile(regex)

        except ValueError as error:

            previous_regex = regex
            feedback = str(error)

            print(
                f"Attempt {attempt + 1}: "
                f"unsafe or invalid regex rejected: "
                f"{regex}",
                flush=True
            )

            continue

        if sample_values:

            matches = [
                value
                for value in sample_values
                if compiled_regex.search(
                    str(value)
                )
            ]

            if len(matches) == 0:

                previous_regex = regex

                feedback = (
                    "The regex matched zero sample values. "
                    "Generate a corrected regex that matches "
                    "values satisfying the user's instruction."
                )

                print(
                    f"Attempt {attempt + 1}: "
                    f"regex matched zero samples: "
                    f"{regex}",
                    flush=True
                )

                continue

            print(
                f"Regex matched "
                f"{len(matches)} sample values.",
                flush=True
            )

        print(
            f"Valid regex generated on "
            f"attempt {attempt + 1}: "
            f"{regex}",
            flush=True
        )

        return {
            "regex": regex
        }

    raise ValueError(
        "Unable to generate a valid and safe "
        "regex after 3 attempts."
    )