#!/bin/bash
set -e

echo "=== Airflow 3.x - Inicializando ==="

export AIRFLOW_HOME="${AIRFLOW_HOME:-/opt/airflow}"

airflow db migrate

echo "=== Configurando contraseña admin ==="
# Pre-crear archivo de passwords para evitar autogeneración aleatoria
PASSWORD_FILE="${AIRFLOW_HOME:-/opt/airflow}/simple_auth_manager_passwords.json.generated"
if [ ! -f "$PASSWORD_FILE" ]; then
    echo '{"admin": "Admin12345*"}' > "$PASSWORD_FILE"
    echo "Contraseña fijada: admin / Admin12345*"
fi

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
