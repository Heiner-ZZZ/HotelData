FROM apache/airflow:2.9.3-python3.12

USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl gcc build-essential && \
    rm -rf /var/lib/apt/lists/*

USER airflow
COPY docker/airflow.requirements.txt /tmp/airflow.requirements.txt
RUN pip install --no-cache-dir -r /tmp/airflow.requirements.txt

COPY src /opt/hoteldata/src
COPY config /opt/hoteldata/config
COPY scripts /opt/hoteldata/scripts
