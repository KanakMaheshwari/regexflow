import re


DANGEROUS_PATTERNS = [
    r"\([^)]*[+*][^)]*\)[+*]",
    r"\.\*[+*]",
    r"\.\+[+*]",
]


def validate_regex_safety(regex):

    if not isinstance(regex, str):
        raise ValueError("Regex must be a string.")

    if len(regex) > 500:
        raise ValueError("Generated regex is too long.")

    try:
        re.compile(regex)

    except re.error as error:
        raise ValueError(
            f"Invalid regex syntax: {error}"
        )

    for dangerous_pattern in DANGEROUS_PATTERNS:

        if re.search(
            dangerous_pattern,
            regex
        ):
            raise ValueError(
                "Potentially unsafe regex detected."
            )

    return True