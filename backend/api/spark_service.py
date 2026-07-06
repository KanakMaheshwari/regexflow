from pyspark.sql import SparkSession
from pyspark.sql.functions import col, regexp_replace
from pyspark.sql.types import StringType


def get_spark_session():
    return (
        SparkSession.builder
        .appName("NLtoRegex")
        .master("local[*]")
        .config("spark.driver.memory", "1g")
        .getOrCreate()
    )


def apply_regex_with_spark(
    input_path,
    output_path,
    regex,
    replacement,
    target_column=None
):

    spark = get_spark_session()

    try:

        df = (
            spark.read
            .option("header", True)
            .option("inferSchema", False)
            .csv(input_path)
        )

        if target_column:

            matching_column = None

            for column in df.columns:

                if column.lower() == target_column.lower():
                    matching_column = column
                    break

            if matching_column is None:

                raise ValueError(
                    f"Target column '{target_column}' not found."
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

                if isinstance(field.dataType, StringType):

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
            .coalesce(1)
            .write
            .mode("overwrite")
            .option("header", True)
            .csv(output_path)
        )

        return output_path

    finally:

        spark.stop()