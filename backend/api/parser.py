import re


def parse_instruction(instruction):

    commands = []

    lines = instruction.lower().split("\n")

    for line in lines:

        line = line.strip()

        if not line:
            continue

        if line == "uppercase":
            commands.append({
                "action": "uppercase"
            })
            continue

        if line == "lowercase":
            commands.append({
                "action": "lowercase"
            })
            continue

        if line == "remove duplicates":
            commands.append({
                "action": "remove_duplicates"
            })
            continue

        if line == "remove empty rows":
            commands.append({
                "action": "remove_empty_rows"
            })
            continue

        match = re.match(
            r"replace (.+) with (.+)",
            line
        )

        if match:

            commands.append({
                "action": "replace",
                "old": match.group(1).strip(),
                "new": match.group(2).strip()
            })

            continue

        match = re.match(
            r"rename (.+) to (.+)",
            line
        )

        if match:

            commands.append({
                "action": "rename_column",
                "old": match.group(1).strip(),
                "new": match.group(2).strip()
            })

            continue

        match = re.match(
            r"delete column (.+)",
            line
        )

        if match:

            commands.append({
                "action": "delete_column",
                "column": match.group(1).strip()
            })

            continue

    return commands