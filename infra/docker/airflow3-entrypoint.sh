#!/bin/bash
set -e

echo "=== Airflow 3.x - Inicializando ==="

export AIRFLOW_HOME="${AIRFLOW_HOME:-/opt/airflow}"

airflow db migrate

echo "Iniciando scheduler..."
airflow scheduler &
SCHEDULER_PID=$!

echo "Iniciando API server..."
airflow api-server --port 8080 &
API_PID=$!

echo "=== Airflow 3.x listo en http://localhost:8080 ==="
echo "=== Usuario: admin / Admin12345* ==="

trap "kill $SCHEDULER_PID $API_PID 2>/dev/null" SIGINT SIGTERM
wait
