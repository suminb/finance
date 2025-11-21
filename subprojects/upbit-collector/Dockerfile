FROM python:3.9-alpine

COPY . /opt/app
WORKDIR /opt/app
RUN pip install -r requirements.txt

# TODO: Pass the log path by parameter
ENTRYPOINT [ "python", "collector.py" ]