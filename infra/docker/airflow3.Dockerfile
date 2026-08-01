FROM apache/airflow:3.2.2-python3.12

ARG AIRFLOW_VERSION=3.2.2
ARG PYTHON_VERSION=3.12

USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl gcc build-essential && \
    rm -rf /var/lib/apt/lists/*

USER airflow

COPY infra/docker/airflow3.requirements.txt /tmp/airflow3.requirements.txt
# Install the executor/database extras with Airflow's official tested constraints.
# Custom DAG dependencies are installed separately because Airflow's constraints
# file is intended for the Airflow installation step, not every later pip call.
RUN pip install --no-cache-dir \
    "apache-airflow[celery,postgres]==${AIRFLOW_VERSION}" \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt" && \
    pip install --no-cache-dir -r /tmp/airflow3.requirements.txt

COPY server/src /opt/hoteldata/src
COPY server/config /opt/hoteldata/config
COPY server/scripts /opt/hoteldata/scripts
COPY server/tests /opt/hoteldata/tests
