# Plan de Implementación: Promociones y Cupones

**Branch**: `021-promociones-cupones` | **Spec**: [spec.md](spec.md)

## Arquitectura

```
Frontend                            Backend                          MongoDB
─────────────────                   ─────────────────                ──────
                                                     ┌──────────────────────────┐
  /management/promotions ──────────►               │ modules/revenue/          │
  (CRUD: list, create, edit, delete)  CRUD          │ services/promotions.py   │──► promotion_campaigns
                                      /api/revenue/ │ (create_campaign,        │──► coupon_codes
                                      promotions/   │  update_campaign,        │
                                                     │  list_campaigns,         │
                                                     │  activate/deactivate)    │
                                                     └──────────────────────────┘
```

## Endpoints

| Método | Ruta | Propósito |
|--------|------|-----------|
| GET | /api/revenue/properties/{id}/promotions | Listar campañas promocionales |
| POST | /api/revenue/properties/{id}/promotions | Crear campaña con códigos de cupón |
| PUT | /api/revenue/promotions/{promo_id} | Actualizar campaña |
| POST | /api/revenue/promotions/{promo_id}/toggle | Activar/desactivar |

## Reglas de negocio

- Una promoción tiene un % de descuento (1-100)
- Al crear promoción, se generan N códigos de cupón asociados
- Los cupones tienen fecha de expiración
- Un cupón solo puede usarse una vez
- Las promociones pueden ser por propiedad o globales
