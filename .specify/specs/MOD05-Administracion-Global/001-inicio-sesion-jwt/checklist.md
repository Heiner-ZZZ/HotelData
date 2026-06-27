# Checklist: Inicio de Sesión JWT

## Funcional
- [ ] Login con credenciales válidas funciona
- [ ] Login con contraseña incorrecta rechaza con mensaje genérico
- [ ] Login con cuenta inactiva rechaza con mensaje específico
- [ ] Sesión creada en user_sessions con hash SHA-256
- [ ] Cookie httponly establecida correctamente

## Seguridad
- [ ] Contraseñas con bcrypt, nunca texto plano
- [ ] Mensaje de error no revela si falló email o password
- [ ] Cookie httponly + samesite=lax

## Auditoría
- [ ] Login exitoso registrado en user_activity_logs
- [ ] Login fallido registrado en user_activity_logs

## Tests
- [ ] test_login_success
- [ ] test_login_invalid_credentials
- [ ] test_login_inactive_account
- [ ] test_session_ttl
