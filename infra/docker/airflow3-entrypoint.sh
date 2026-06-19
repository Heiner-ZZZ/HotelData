#!/bin/bash
set -e

echo "=== Airflow 3.x - Inicializando ==="

airflow db migrate

# Pre-configure admin user password for SimpleAuthManager
PASSWORDS_FILE="${AIRFLOW_HOME:-/opt/airflow}/simple_auth_manager_passwords.json.generated"
if [ ! -f "$PASSWORDS_FILE" ]; then
    echo "Generando hash para contraseña admin..."
    mkdir -p "$(dirname "$PASSWORDS_FILE")"
    cat > "$PASSWORDS_FILE" << PYEOF
{"admin": "Admin12345*"}
PYEOF
    echo "Archivo de contraseñas creado con usuario admin / Admin12345*"
fi

echo "Iniciando scheduler + triggerer + dag-processor + api-server..."
airflow scheduler &
airflow triggerer &
airflow dag-processor &

echo "Iniciando API server..."
airflow api-server &

echo "Esperando que el API server esté listo..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:8080/auth/token -X POST -H "Content-Type: application/json" -d '{"username":"admin","password":"Admin12345*"}' -o /dev/null 2>/dev/null; then
        echo "API server listo!"
        break
    fi
    echo "  esperando... ($i/30)"
    sleep 3
done

echo "=== Airflow 3.x listo en http://localhost:8080 ==="
echo "=== Usuario: admin / Admin12345* ==="
echo "=== (contraseña configurada via SimpleAuthManager) ==="
wait
