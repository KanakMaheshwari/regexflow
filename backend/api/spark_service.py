import os

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, regexp_extract, regexp_replace


DEFAULT_SPARK_PARTITIONS = 4


def get_spark_session():
    return (
        SparkSession.builder
        .appName("NLtoRegex")
        .master("local[*]")
        .config(
            "spark.sql.shuffle.partitions",
            str(DEFAULT_SPARK_PARTITIONS)
        )
        .config(
            "spark.default.parallelism",
            str(DEFAULT_SPARK_PARTITIONS)
        )
        .config(
            "spark.driver.memory",
            "1g"
        )
        .getOrCreate()
    )


def calculate_partition_count(file_path):
    file_size = os.path.getsize(file_path)
    megabyte = 1024 * 1024

    if file_size < 50 * megabyte:
        return 4

    if file_size < 250 * megabyte:
        return 8

    if file_size < 1024 * megabyte:
        return 16

    return 32


def find_matching_columns(
    dataframe_columns,
    target_columns
):
    column_lookup = {
        column.lower(): column
        for column in dataframe_columns
    }

    matching_columns = []
    missing_columns = []

    for target_column in target_columns:
        matching_column = column_lookup.get(
            target_column.lower()
        )

        if matching_column is None:
            missing_columns.append(
                target_column
            )
        else:
            matching_columns.append(
                matching_column
            )

    if missing_columns:
        raise ValueError(
            "Target column(s) not found: "
            + ", ".join(missing_columns)
        )

    return matching_columns


def apply_replace_transformation(
    dataframe,
    matching_columns,
    regex,
    replacement
):
    for matching_column in matching_columns:
        dataframe = dataframe.withColumn(
            matching_column,
            regexp_replace(
                col(matching_column),
                regex,
                replacement
            )
        )

    return dataframe


def apply_extract_transformation(
    dataframe,
    matching_columns,
    regex
):
    for matching_column in matching_columns:
        dataframe = dataframe.withColumn(
            matching_column,
            regexp_extract(
                col(matching_column),
                regex,
                0
            )
        )

    return dataframe


def apply_mask_transformation(
    dataframe,
    matching_columns,
    regex
):
    for matching_column in matching_columns:
        dataframe = dataframe.withColumn(
            matching_column,
            regexp_replace(
                col(matching_column),
                regex,
                "********"
            )
        )

    return dataframe


def apply_transformation(
    dataframe,
    matching_columns,
    regex,
    replacement,
    transformation_type
):
    if transformation_type == "replace":
        return apply_replace_transformation(
            dataframe,
            matching_columns,
            regex,
            replacement
        )

    if transformation_type == "extract":
        return apply_extract_transformation(
            dataframe,
            matching_columns,
            regex
        )

    if transformation_type == "mask":
        return apply_mask_transformation(
            dataframe,
            matching_columns,
            regex
        )

    raise ValueError(
        f"Unsupported transformation type: "
        f"{transformation_type}"
    )


def apply_regex_with_spark(
    input_path,
    output_path,
    regex,
    replacement,
    target_columns,
    transformation_type="replace"
):
    spark = get_spark_session()

    try:
        partition_count = calculate_partition_count(
            input_path
        )

        print(
            f"Spark partition count: "
            f"{partition_count}",
            flush=True
        )

        dataframe = (
            spark.read
            .option("header", True)
            .option("inferSchema", False)
            .csv(input_path)
        )

        dataframe = dataframe.repartition(
            partition_count
        )

        print(
            f"Spark DataFrame partitions: "
            f"{dataframe.rdd.getNumPartitions()}",
            flush=True
        )

        matching_columns = find_matching_columns(
            dataframe.columns,
            target_columns
        )

        print(
            f"Spark target columns: "
            f"{matching_columns}",
            flush=True
        )

        print(
            f"Transformation type: "
            f"{transformation_type}",
            flush=True
        )

        dataframe = apply_transformation(
            dataframe=dataframe,
            matching_columns=matching_columns,
            regex=regex,
            replacement=replacement,
            transformation_type=transformation_type
        )

        (
            dataframe
            .write
            .mode("overwrite")
            .option("header", True)
            .csv(output_path)
        )

        return output_path

    finally:
        spark.stop()