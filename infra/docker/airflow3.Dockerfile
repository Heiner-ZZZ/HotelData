FROM apache/airflow:3.2.2-python3.12

USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl gcc build-essential && \
    rm -rf /var/lib/apt/lists/*

USER airflow

COPY infra/docker/airflow3.requirements.txt /tmp/airflow3.requirements.txt
RUN pip install --no-cache-dir -r /tmp/airflow3.requirements.txt

COPY server/src /opt/hoteldata/src
COPY server/config /opt/hoteldata/config
COPY server/scripts /opt/hoteldata/scripts
COPY server/tests /opt/hoteldata/tests
