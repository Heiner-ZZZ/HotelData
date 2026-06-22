# Checklist: Gestión de Sesiones

- [ ] Logout elimina documento de user_sessions
- [ ] Logout elimina cookie hoteldata_session
- [ ] Logout registrado en user_activity_logs
- [ ] GET /api/auth/me retorna datos correctos con sesión válida
- [ ] GET /api/auth/me retorna 401 sin sesión
- [ ] Sesión expira automáticamente por TTL index
