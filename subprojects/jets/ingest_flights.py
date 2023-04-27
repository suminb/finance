from datetime import datetime
import json
import os
import sys

from pyspark import SparkContext, StorageLevel, SparkFiles
from pyspark.sql import SparkSession, Row
import pyspark.sql.functions as f
from pyspark.sql.types import ArrayType, DateType, DoubleType, LongType, StructField, StructType, StringType, TimestampType, IntegerType
from pyspark.sql.window import Window

#
# Data from flightradar24.com
#

# BASE_PATH = "./flights"
BASE_PATH = "s3a://standard/datasets/jets"
# .master("local[*]") \

spark = SparkSession.builder \
    .master("spark://aria.shortbread.io:7077") \
    .config("spark.executor.cores", "4") \
    .config("spark.executor.memory", "1G") \
    .appName("ingest_flights") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .config("spark.hadoop.fs.s3a.endpoint", "hyperion.shortbread.io:8000") \
    .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.access.key", os.environ["AWS_ACCESS_KEY_ID"]) \
    .config("spark.hadoop.fs.s3a.secret.key", os.environ["AWS_SECRET_ACCESS_KEY"]) \
    .getOrCreate()

# venv_path = SparkFiles.get("pyspark_venv.zip")
# print(f"venv_path = {venv_path}")
# sys.path.append(venv_path)

# from logbook import Logger, StreamHandler
# StreamHandler(sys.stdout).push_application()
# log = Logger("ingest_flights")


def get_airport_code(airport: dict):
    if airport is not None:
        return airport["code"]["iata"]


def get_duration(time_: dict):
    try:
        # return time_["other"]["duration"]
        real = time_["real"]
        arrival = real["arrival"]
        departure = real["departure"]
    except KeyError:
        return None
    if arrival and departure:
        return arrival - departure
    else:
        return None


def parse_timestamp(timestamp: int):
    if timestamp is not None:
        return datetime.fromtimestamp(timestamp)


def parse(args):
    value = args
    try:
        data = json.loads(value)
    except Exception as e:
        # log.error(e)
        print(e)
        return

    try:
        flights = data["result"]["response"]["data"]
        first_row = flights[0]
    except Exception as e:
        # log.error(e)
        print(e)
        return
    for flight in flights:
        yield Row(
            id=flight["identification"]["id"],
            number=flight["identification"]["number"]["default"],
            status=flight["status"]["generic"]["status"]["text"],
            origin=get_airport_code(flight["airport"]["origin"]),
            destination=get_airport_code(flight["airport"]["destination"]),
            scheduled_departure=parse_timestamp(flight["time"]["scheduled"]["departure"]),
            duration=get_duration(flight["time"]),
        )


def parse_datetime(datetime_str, format_="%Y-%m-%d %H:%M:%S"):
    return datetime.strptime(datetime_str, format_)


def main():
    # TODO: Would it be possible to distinguish international/domestic flights?
    data = spark.sparkContext \
        .textFile(f"{BASE_PATH}/flights/") \
        .flatMap(parse) \
        .toDF()
    data = data \
        .filter("id IS NOT NULL") \
        .dropDuplicates(["id"]) \
        .filter(f.col("number").startswith("DL")) \
        .filter("scheduled_departure >= '2020-01-01 00:00:00'") \
        .filter("scheduled_departure < '2023-01-01 00:00:00'")
    # data.show(500)

    df2 = data \
        .filter("status = 'landed'") \
        .filter("duration >= 1000") \
        .filter("scheduled_departure IS NOT NULL") \
        .withColumn("date", f.to_date("scheduled_departure")) \
        .groupBy("date") \
        .count()
    # df2.show(365 * 3)
    # df2.write.mode("overwrite").csv("/tmp/delta_daily.csv")

    # log.info(f"count = {df2.count()}")

    schema = StructType([
        StructField("date", StringType(), True),
        StructField("price", DoubleType(), True),
        StructField("open", DoubleType(), True),
        StructField("high", DoubleType(), True),
        StructField("low", DoubleType(), True),
        StructField("volume", StringType(), True),
        StructField("change", StringType(), True),
        StructField("eps", DoubleType(), True),
        StructField("eps_forecast", DoubleType(), True),
        StructField("surprise", DoubleType(), True),  # percentage
    ])
    historical = spark.read.csv(f"{BASE_PATH}/delta_historical.csv", header=False, schema=schema) \
        .withColumn("date", f.to_date(f.col("date"), "MM/dd/yyyy"))
    # historical.show()

    df2.join(historical, df2.date == historical.date, "left_outer") \
        .drop(historical.date) \
        .withColumn("count", f.col("count").cast(IntegerType())) \
        .withColumn("count_scaled", f.col("count") / 1000) \
        .withColumn("price_scaled", f.col("price") / 10) \
        .orderBy(df2.date) \
        .write.option("header", True).mode("overwrite").csv(f"{BASE_PATH}/combined.csv")


if __name__ == "__main__":
    main()
