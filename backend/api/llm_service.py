import re

def generate_regex(prompt):

    prompt = prompt.lower()

    if "email" in prompt:
        return {
            "regex": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
        }

    elif "phone" in prompt:
        return {
            "regex": r"\b\d{10}\b"
        }

    elif "date" in prompt:
        return {
            "regex": r"\d{2}/\d{2}/\d{4}"
        }

    elif "url" in prompt:
        return {
            "regex": r"https?://[^\s]+"
        }

    else:
        return {
            "regex": prompt
        }