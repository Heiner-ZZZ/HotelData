# Reglas de negocio

HotelData Hub Analytics se enfoca en analitica de reservas hoteleras: conversion, promociones, ocupacion, ingresos, calidad de datos y auditoria de cargas.

El sistema no debe describirse como pasarela de pagos, motor real de confirmacion de reservas, login productivo ni sistema transaccional hotelero completo. Trabaja con eventos de busqueda/reserva ya existentes y los convierte en informacion analitica.

## Usuarios

1. Admin
   - Puede consultar dashboard, registros, calidad, colecciones, empresa, problemas y auditoria.
   - Puede administrar `system_catalogs` mediante CRUD basico.
   - Puede revisar estado de ejecuciones ETL y actividad reciente.
   - Puede usar CRUD TA02 para `fact_hotel_reservations` y dimensiones.

2. Usuario normal
   - Puede consultar dashboard, registros, calidad, colecciones, empresa y problemas.
   - No debe modificar `system_catalogs`.
   - No debe ejecutar ni modificar el pipeline ETL.

## Reglas generales

- La gestion de usuarios pertenece a la capa web si se documenta, pero no altera el flujo ETL principal.
- Los roles no deben alterar Airflow ni el ETL.
- Airflow no debe depender de roles de usuario ni de `src.app`.
- El ETL debe seguir ejecutandose desde Python y cargando datos transformados en MongoDB.
- TA02 analiza eventos de busqueda, click, promocion, precio y reserva.
- Los indicadores de negocio se basan en `fact_hotel_reservations` y sus dimensiones.
