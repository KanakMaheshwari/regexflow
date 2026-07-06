import pandas as pd
from .parser import parse_instruction


def apply_instruction(df, instruction):

    commands = parse_instruction(instruction)

    for command in commands:

        action = command.get("action")

        if action == "uppercase":

            for col in df.select_dtypes(include="object").columns:
                df[col] = df[col].astype(str).str.upper()

        elif action == "lowercase":

            for col in df.select_dtypes(include="object").columns:
                df[col] = df[col].astype(str).str.lower()

        elif action == "remove_empty_rows":

            df = df.dropna(how="all")

        elif action == "remove_duplicates":

            df = df.drop_duplicates()

        elif action == "replace":

            old = command.get("old")
            new = command.get("new")

            for col in df.select_dtypes(include="object").columns:
                df[col] = (
                    df[col]
                    .astype(str)
                    .str.replace(old, new, regex=False)
                )

        elif action == "rename_column":

            old = command.get("old")
            new = command.get("new")

            for col in df.columns:

                if col.lower() == old.lower():

                    df.rename(
                        columns={
                            col: new
                        },
                        inplace=True
                    )

                    break

        elif action == "delete_column":

            column = command.get("column")

            for col in df.columns:

                if col.lower() == column.lower():

                    df.drop(
                        columns=[col],
                        inplace=True
                    )

                    break

        elif action == "keep_columns":

            requested = [
                c.lower()
                for c in command.get("columns", [])
            ]

            keep = []

            for col in df.columns:

                if col.lower() in requested:

                    keep.append(col)

            if keep:
                df = df[keep]

        else:

            print(f"Unknown action: {action}")

    return df