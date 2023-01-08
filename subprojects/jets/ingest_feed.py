from datetime import datetime
import json
import os
import sys

from pyspark import SparkContext, StorageLevel
from pyspark.sql import SparkSession, Row
import pyspark.sql.functions as f
from pyspark.sql.types import ArrayType, DoubleType, LongType, StructField, StructType, StringType, TimestampType
from pyspark.sql.window import Window


#
# Data from flightradar24.com
# ['full_count', 'version', 'stats']
#
# Data itself is not too expensive: https://www.flightradar24.com/premium#featureInfo56
#

BASE_PATH = "s3a://standard/datasets/jets"

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


def parse(args):
    key, value = args
    try:
        data = json.loads(value)
    except Exception as e:
        print(e)
        return
    full_count = data.pop("full_count")
    version = data.pop("version")
    stats = data.pop("stats")

    for key, value in data.items():
        latitude = value[1] # ?
        longitude = value[2] # ?
        heading = value[3] # ?
        altitude = value[4]
        speed = value[5]

        unknown6 = value[6]
        unknown7 = value[7]

        aircraft = value[8]
        unknown9 = value[9]
        timestamp = value[10]
        timestamp = datetime.fromtimestamp(timestamp)

        # airport codes
        origin = value[11]
        destination = value[12]

        flight_number = value[13]

        unknown14 = value[14]
        unknown15 = value[15]
        unknown16 = value[16]
        unknown17 = value[17]

        operator = value[18] # carrier? operator?

        yield Row(
            key=key,
            latitude=latitude,
            longitude=longitude,
            heading=heading,
            altitude=altitude,
            speed=speed,
            unknown6=unknown6,
            unknown7=unknown7,
            aircraft=aircraft,
            unknown9=unknown9,
            timestamp=timestamp,
            origin=origin,
            destination=destination,
            flight_number=flight_number,
            operator=operator,
            unknown14=unknown14,
            unknown15=unknown15,
            unknown16=unknown16,
            unknown17=unknown17,
        )


def parse_datetime(datetime_str, format_="%Y-%m-%d %H:%M:%S"):
    return datetime.strptime(datetime_str, format_)


def main():
    columns = ["key", "latitude", "longitude", "timestamp", "departure", "arrival", "flight_number", "operator"]
    feed = spark.sparkContext \
        .wholeTextFiles(f"{BASE_PATH}/") \
        .flatMap(parse)
    feed = feed.toDF()
    feed.printSchema()

    delta_flights = feed \
        .filter(feed.flight_number.startswith("DL")) \
        .filter(feed.timestamp >= parse_datetime("2022-01-01 00:00:00")) \
        .filter(feed.timestamp < parse_datetime("2023-01-01 00:00:00"))
    delta_flights.select("flight_number").distinct().write.mode("overwrite").csv("/tmp/delta.csv")

    # df2 = feed.groupBy("key").count().sort(f.desc("count"))
    # df2.show()


if __name__ == "__main__":
    main()


# +--------+-----+
# |     key|count|
# +--------+-----+
# |2e146815|   32|
# |2e15a45d|   29|
# |2e15cf18|   28|
# |2e15a3dc|   28|
# |2e15df1e|   27|
# |2e15dc54|   27|
# |2e15bb98|   27|
# |2e15d235|   27|
# |2e15c1e2|   27|
# |2e15c68b|   27|
# |2e14d570|   27|
# |2e15d25b|   26|
# |2e15adc9|   26|
# |2e15a3bf|   26|
# |2e15e6d2|   26|
# |2e1479ae|   26|
# |2e15b36f|   26|
# |2e15918e|   26|
# |2e15c480|   25|
# |2e15e792|   25|
