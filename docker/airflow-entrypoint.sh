#!/bin/bash
set -e

echo "=== Inicializando Airflow ==="

airflow db migrate

if ! airflow users list 2>/dev/null | grep -q "^${_AIRFLOW_WWW_USER_USERNAME:-admin} "; then
    echo "Creando usuario admin..."
    airflow users create \
        --username "${_AIRFLOW_WWW_USER_USERNAME:-admin}" \
        --password "${_AIRFLOW_WWW_USER_PASSWORD:-Admin12345*}" \
        --firstname Admin \
        --lastname User \
        --role Admin \
        --email "${_AIRFLOW_WWW_USER_EMAIL:-admin@example.com}"
fi

echo "Aplicando tema oscuro a webserver_config.py..."
cat > /opt/airflow/webserver_config.py << 'PYEOF'
from __future__ import annotations
from flask_appbuilder.const import AUTH_DB

WTF_CSRF_ENABLED = True
WTF_CSRF_TIME_LIMIT = None
AUTH_TYPE = AUTH_DB
APP_THEME = "darkly.css"
PYEOF

echo "Iniciando servicios..."
airflow webserver &
airflow scheduler &
airflow triggerer &

wait
