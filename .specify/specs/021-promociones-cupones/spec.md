# Especificacion: Promociones y Cupones

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O19 (Crear promociones con porcentaje descuento), CU-T01 (Gestionar campanas promocionales)

## 1. Objetivo

Crear campanas promocionales con porcentaje de descuento y codigos de cupon asociados, para ofrecer tarifas especiales en periodos especificos.

## 2. Contexto

Las promociones permiten al partner ofrecer descuentos porcentuales sobre las tarifas base. Cada campana puede tener multiples codigos de cupon que los huespedes pueden canjear.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Marketing hotelero | Define descuentos y segmentos objetivo |
| Revenue manager | Crea y gestiona campanas promocionales |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe permitir crear campana con nombre, descuento %, fechas vigencia | Alta |
| RF-002 | El sistema debe generar N codigos de cupon al crear la campana | Alta |
| RF-003 | El sistema debe permitir activar/desactivar campana | Alta |
| RF-004 | El sistema debe listar campanas por propiedad | Alta |
| RF-005 | El sistema debe validar descuento entre 1% y 100% | Alta |
| RF-006 | El sistema debe permitir editar campana | Media |

## 5. Requisitos no funcionales

| ID | Requisito |
|----|-----------|
| RNF-001 | Creacion de campana con 100 cupones menos de 1s |
| RNF-002 | Validacion de cupon en reserva menos de 300ms |

## 6. Reglas de negocio

- Una promocion tiene un % de descuento (1-100)
- Al crear campana, se generan N codigos de cupon asociados
- Los cupones tienen fecha de expiracion (la misma de la campana)
- Un cupon solo puede usarse una vez
- Las promociones pueden ser por propiedad (hotel_id) o globales (hotel_id = null)

## 7. Entradas

```json
{
  "name": "Descuento Verano",
  "description": "20% de descuento en estancias de verano",
  "discount_percentage": 20,
  "start_date": "2026-07-01",
  "end_date": "2026-08-31",
  "hotel_id": "HOTEL001",
  "coupon_count": 100,
  "min_nights": 2
}
```

## 8. Salidas

```json
{
  "success": true,
  "data": {
    "promotion_id": "promo_001",
    "name": "Descuento Verano",
    "discount_percentage": 20,
    "coupons_generated": 100,
    "coupons_used": 0,
    "status": "active",
    "valid_from": "2026-07-01",
    "valid_to": "2026-08-31"
  }
}
```

## 9. Escenarios

### Escenario 1: Crear campana con cupones
```gherkin
Dado que el revenue manager define una promocion de 20% para verano
Cuando crea la campana con 100 cupones
Entonces el sistema crea la campana en promotion_campaigns
Y genera 100 codigos unicos en coupon_codes
```

### Escenario 2: Usar cupon en reserva
```gherkin
Dado que existe un cupon valido
Cuando el cliente lo ingresa al reservar
Entonces el sistema aplica el descuento
Y marca el cupon como usado
```

## 10. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | Campana se crea con cupones generados |
| CA-002 | Cupon se valida y descuenta correctamente |
| CA-003 | Cupon usado no puede reutilizarse |
| CA-004 | Campana expirada no aplica descuento |

## 11. Restricciones

- discount_percentage entre 1 y 100
- coupon_count maximo 1000 por campana
- Codigos de cupon: 8-12 caracteres alfanumericos

## 12. Dependencias

- Coleccion promotion_campaigns
- Coleccion coupon_codes
- Modulo revenue/services/promotions.py

## 13. Fuera de alcance

- Envio automatico de cupones por email
- Segmentacion avanzada de clientes para promociones
