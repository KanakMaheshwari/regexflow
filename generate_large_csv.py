import csv


TOTAL_ROWS = 500000


with open(
    "large_test_data.csv",
    "w",
    newline="",
    encoding="utf-8"
) as file:

    writer = csv.writer(file)

    writer.writerow([
        "ID",
        "Name",
        "Email",
        "Employee_ID",
        "Department"
    ])

    departments = [
        "Engineering",
        "Finance",
        "Marketing",
        "HR"
    ]

    for i in range(1, TOTAL_ROWS + 1):

        writer.writerow([
            i,
            f"User {i}",
            f"user{i}@example.com",
            f"EMP-{i:06d}",
            departments[i % len(departments)]
        ])


print(
    f"Created large_test_data.csv with "
    f"{TOTAL_ROWS} rows."
)