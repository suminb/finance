from datetime import datetime
import json
import os
import sys

from logbook import Logger, StreamHandler
from pyspark import SparkContext, StorageLevel
from pyspark.sql import SparkSession, Row
import pyspark.sql.functions as f
from pyspark.sql.types import ArrayType, DoubleType, LongType, StructField, StructType, StringType, TimestampType
from pyspark.sql.window import Window


StreamHandler(sys.stdout).push_application()
log = Logger("ingest_flights")
#
# Data from flightradar24.com
#

BASE_PATH = "./flights"

spark = SparkSession.builder \
    .appName("m3bot") \
    .master("local[*]") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .config("spark.hadoop.fs.s3a.endpoint", "hyperion.shortbread.io:8000") \
    .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.access.key", os.environ["AWS_ACCESS_KEY_ID"]) \
    .config("spark.hadoop.fs.s3a.secret.key", os.environ["AWS_SECRET_ACCESS_KEY"]) \
    .getOrCreate()


def get_airport_code(airport: dict):
    if airport is not None:
        return airport["code"]["iata"]


def parse_timestamp(timestamp: int):
    if timestamp is not None:
        return datetime.fromtimestamp(timestamp)


def parse(args):
    value = args
    try:
        data = json.loads(value)
    except Exception as e:
        log.error(e)
        return

    try:
        flights = data["result"]["response"]["data"]
        first_row = flights[0]
    except Exception as e:
        log.error(e)
        return
    for flight in flights:
        yield Row(
            id=flight["identification"]["id"],
            number=flight["identification"]["number"]["default"],
            status=flight["status"]["generic"]["status"]["text"],
            origin=get_airport_code(flight["airport"]["origin"]),
            destination=get_airport_code(flight["airport"]["destination"]),
            scheduled_departure=parse_timestamp(flight["time"]["scheduled"]["departure"]),
        )


def parse_datetime(datetime_str, format_="%Y-%m-%d %H:%M:%S"):
    return datetime.strptime(datetime_str, format_)


def main():
    data = spark.sparkContext \
        .textFile(f"{BASE_PATH}/") \
        .flatMap(parse) \
        .toDF()
    data = data \
        .filter("id IS NOT NULL") \
        .dropDuplicates(["id"]) \
        .filter(f.col("number").startswith("DL")) \
        .filter("scheduled_departure >= '2022-01-01 00:00:00'") \
        .filter("scheduled_departure < '2023-01-01 00:00:00'") \
        .filter("origin = 'LHR' OR destination = 'LHR'")
    data.show(200)

    # df2 = data \
    #     .filter("status = 'landed'") \
    #     .filter("scheduled_departure IS NOT NULL") \
    #     .withColumn("date", f.to_date("scheduled_departure")) \
    #     .groupBy("date") \
    #     .count() \
    #     .orderBy("date")
    # df2.show(365)

    # log.info(f"count = {df2.count()}")


if __name__ == "__main__":
    main()
