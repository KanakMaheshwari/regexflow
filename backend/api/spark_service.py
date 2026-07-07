import os

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, regexp_replace
from pyspark.sql.types import StringType


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


def apply_regex_with_spark(
    input_path,
    output_path,
    regex,
    replacement,
    target_column=None
):
    spark = get_spark_session()

    try:
        partition_count = calculate_partition_count(
            input_path
        )

        print(
            f"Spark partition count: {partition_count}",
            flush=True
        )

        df = (
            spark.read
            .option("header", True)
            .option("inferSchema", False)
            .csv(input_path)
        )

        df = df.repartition(partition_count)

        print(
            f"Spark DataFrame partitions: "
            f"{df.rdd.getNumPartitions()}",
            flush=True
        )

        if target_column:
            matching_column = None

            for column in df.columns:
                if column.lower() == target_column.lower():
                    matching_column = column
                    break

            if matching_column is None:
                raise ValueError(
                    f"Target column "
                    f"'{target_column}' not found."
                )

            df = df.withColumn(
                matching_column,
                regexp_replace(
                    col(matching_column),
                    regex,
                    replacement
                )
            )

        else:
            for field in df.schema.fields:
                if isinstance(
                    field.dataType,
                    StringType
                ):
                    df = df.withColumn(
                        field.name,
                        regexp_replace(
                            col(field.name),
                            regex,
                            replacement
                        )
                    )

        (
            df
            .write
            .mode("overwrite")
            .option("header", True)
            .csv(output_path)
        )

        return output_path

    finally:
        spark.stop()