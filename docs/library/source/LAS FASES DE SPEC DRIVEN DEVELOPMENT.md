# LAS FASES DE SPEC DRIVEN DEVELOPMENT

## 1. Definición del problema

Se identifica qué necesidad se quiere resolver, quiénes son los usuarios y cuál es el objetivo del sistema.

## 2. Recolección de requisitos

Se recopila información sobre lo que el software debe hacer. Incluye requisitos funcionales y no funcionales.

**Ejemplo:** "El sistema debe permitir registrar usuarios."

## 3. Especificación formal

Se redacta una especificación clara, detallada y verificable del sistema. Aquí se describen:

- Funciones del sistema
- Entradas y salidas
- Reglas de negocio
- Restricciones
- Casos de uso
- Criterios de aceptación

## 4. Validación de la especificación

Se revisa la especificación con usuarios, clientes o el equipo de desarrollo para confirmar que esté correcta y completa. El objetivo es evitar errores antes de programar.

## 5. Diseño del sistema

A partir de la especificación se define cómo se construirá el software. Incluye:

- Arquitectura
- Base de datos
- Interfaces
- Componentes
- Flujo de datos

## 6. Implementación

Se desarrolla el código siguiendo estrictamente la especificación aprobada. La especificación sirve como guía principal para programar.

## 7. Pruebas

Se verifica que el software cumpla con lo especificado. Las pruebas se basan en los requisitos y criterios de aceptación definidos antes.

## 8. Verificación y validación final - Entrega

Se comprueba que el sistema:

- Funciona correctamente
- Cumple con los requisitos
- Satisface la necesidad del usuario

## 9. Mantenimiento

Después de entregar el software, se corrigen errores, se hacen mejoras o se actualizan especificaciones si cambian las necesidades.

---

# Flujo de trabajo con OpenSpec

## 1. Instalar e iniciar OpenSpec

Primero se instala la herramienta y se inicializa dentro del proyecto:

```bash
npm install -g @fission-ai/openspec@latest
cd tu-proyecto
openspec init
```

## 2. Crear una propuesta

En lugar de empezar programando directamente, se crea una propuesta del cambio.

```
/opsx:propose crear sistema de login para usuarios
```

## 3. Generar la especificación del cambio

OpenSpec organiza cada cambio en su propia carpeta, con elementos como:

- propuesta
- especificación
- diseño
- tareas

**Funcionalidad:** Login de usuarios

**Requisitos:**

- El usuario debe ingresar correo y contraseña.
- El sistema debe validar las credenciales.
- Si las credenciales son correctas, se inicia sesión.
- Si son incorrectas, se muestra un mensaje de error.

## 4. Revisar y validar la especificación

Antes de programar, se revisa si la especificación está completa.

**Preguntas típicas:**

- ¿Está claro qué debe hacer el sistema?
- ¿Faltan reglas de negocio?
- ¿Hay casos de error?
- ¿Hay criterios de aceptación?

OpenSpec usa la idea de "agree before you build", es decir, acordar qué se va a construir antes de escribir código.

## 5. Diseñar la solución

Luego se define cómo se va a implementar.

**Ejemplo:**

- Crear tabla users.
- Crear endpoint POST /register.
- Crear endpoint POST /login.
- Usar JWT para sesión.
- Validar contraseña con hash.

## 6. Crear tareas de implementación

OpenSpec convierte la especificación en tareas concretas.

**Ejemplo:**

1. Crear modelo User.
2. Crear migración de base de datos.
3. Crear controlador AuthController.
4. Implementar registro.
5. Implementar login.
6. Crear pruebas.

## 7. Implementar con apoyo de IA

Después de aprobar la especificación, el asistente de IA o el desarrollador implementa el código siguiendo la spec. Regla principal: **No se programa lo que no está especificado.**

## 8. Verificar

OpenSpec incluye comandos de verificación como `/opsx:verify` para revisar que el cambio cumpla la especificación.

**Se revisa:**

- ¿El código cumple la spec?
- ¿Las pruebas pasan?
- ¿Se implementaron todas las tareas?
- ¿Hay errores o funcionalidades faltantes?

## 9. Archivar el cambio

Cuando el cambio ya está implementado y verificado, se archiva. OpenSpec maneja la idea de que los cambios se integran en una especificación principal o "source of truth", que representa el estado actual del sistema.

---

# Fases de SDD implementadas en OpenSpec

| Fase tradicional de SDD | Cómo se maneja en OpenSpec |
|---|---|
| Definir problema | Se escribe una intención o propuesta |
| Recolectar requisitos | Se detallan necesidades del cambio |
| Especificar | Se crea la spec del cambio |
| Validar | Se revisa antes de codificar |
| Diseñar | Se crea diseño técnico |
| Implementar | Se programa siguiendo la spec |
| Probar | Se ejecuta verificación |
| Mantener | Se archiva y se actualiza la spec principal |

**OpenSpec:** Propuesta → Especificación → Diseño → Tareas → Implementación → Verificación → Archivo

---

# Fase de SDD vs OpenSpec (detallado)

| Fase SDD | Cómo se maneja con OpenSpec | Documento usado | Objetivo principal | Ejemplo |
|---|---|---|---|---|
| 1. Definición del problema | Se plantea una intención o cambio | Propuesta inicial | Entender qué necesidad resolver | "Crear un sistema de login para usuarios" |
| 2. Recolección de requisitos | Se describen funcionalidades esperadas | Propuesta / requisitos | Definir qué debe hacer el sistema | "El usuario debe poder iniciar sesión con correo y contraseña" |
| 3. Especificación formal | Se crea una especificación clara | Spec del cambio | Convertir requisitos en reglas verificables | "Si las credenciales son incorrectas, mostrar mensaje de error" |
| 4. Validación de la especificación | Se revisa la spec antes de programar | Revisión de la spec | Confirmar que lo pedido está completo y correcto | Revisar si faltan casos de error |
| 5. Diseño del sistema | Se define cómo se implementará técnicamente | Documento de diseño | Planear arquitectura, datos, endpoints y componentes | Crear tabla users, endpoint /login, uso de JWT |
| 6. Planificación de tareas | Se divide el trabajo en pasos concretos | Lista de tareas | Organizar la implementación | Crear modelo, controlador, rutas, pruebas |
| 7. Implementación | Se programa siguiendo estrictamente la spec | Código fuente | Construir solo lo aprobado en la spec | Implementar registro, login y cierre de sesión |
| 8. Pruebas | Se verifica que el código cumpla criterios | Tests / verificación | Comprobar que funciona como fue especificado | Probar login correcto, login fallido y validaciones |
| 9. Verificación final | Se revisa que todas las tareas estén completas | Proceso de verificación | Asegurar que el cambio cumple la spec | Confirmar que todos los requisitos fueron implementados |
| 10. Archivo o cierre del cambio | Se archiva y la spec principal se actualiza | Archivo del cambio | Mantener la documentación viva del sistema | El login pasa a ser parte oficial del sistema |

---

# Relación SDD ↔ OpenSpec

| Spec Driven Development | OpenSpec |
|---|---|
| Problema | Propuesta |
| Requisitos | Detalle de la propuesta |
| Especificación | Spec del cambio |
| Validación | Revisión antes de programar |
| Diseño | Documento técnico |
| Implementación | Código basado en la spec |
| Pruebas | Verificación del cumplimiento |
| Mantenimiento | Archivo y actualización de la spec |

**SDD:** Problema → Requisitos → Especificación → Diseño → Código → Pruebas → Mantenimiento

**OpenSpec:** Propuesta → Spec → Diseño → Tareas → Implementación → Verificación → Archivo

---

# Skills Spec Kit integrados con SDD

| Fase SDD | Skill | ¿Para qué se usa? | Resultado esperado |
|---|---|---|---|
| 0. Definir reglas del proyecto | speckit-constitution | Define principios, estándares, restricciones y reglas generales del proyecto | Constitución del proyecto |
| 1. Definición del problema | speckit-specify | Describe qué se quiere construir y la necesidad del usuario | Especificación inicial de la funcionalidad |
| 2. Recolección de requisitos | speckit-specify + speckit-clarify | specify redacta requisitos; clarify detecta dudas o información faltante | Requisitos más completos y claros |
| 3. Especificación formal | speckit-specify | Convierte la idea en una especificación estructurada | Documento de especificación funcional |
| 4. Aclaración y validación | speckit-clarify | Elimina ambigüedades antes de diseñar o programar | Requisitos validados y sin dudas |
| 5. Diseño del sistema | speckit-plan | Define cómo se construirá técnicamente la solución | Plan técnico: arquitectura, componentes, APIs |
| 6. Análisis de consistencia | speckit-analyze | Revisa coherencia entre spec, plan y reglas | Detección de inconsistencias o vacíos |
| 7. Lista de verificación | speckit-checklist | Crea criterios para validar la funcionalidad completa | Checklist de calidad y cumplimiento |
| 8. División del trabajo | speckit-tasks | Convierte la spec y el plan en tareas concretas | Lista de tareas implementables |
| 9. Pasar tareas a issues | speckit-taskstoissues | Transforma tareas en issues para gestión | Issues listos para seguimiento |
| 10. Actualizar contexto del agente | speckit-agent-context-update | Actualiza el contexto del asistente de IA | Contexto actualizado con reglas y estado |
| 11. Implementación | speckit-implement | Implementa código siguiendo la spec y el plan | Código desarrollado según la spec |
| 12. Verificación final | speckit-checklist + speckit-analyze | Comprueba que lo implementado cumpla lo especificado | Validación final antes de cerrar el cambio |

---

# Flujo completo integrado

| Orden | Skill | Fase equivalente |
|---|---|---|
| 1 | speckit-constitution | Reglas base del proyecto |
| 2 | speckit-specify | Definir problema y requisitos |
| 3 | speckit-clarify | Aclarar dudas y validar requisitos |
| 4 | speckit-plan | Diseñar la solución técnica |
| 5 | speckit-analyze | Revisar coherencia del diseño |
| 6 | speckit-checklist | Crear criterios de validación |
| 7 | speckit-tasks | Dividir el trabajo en tareas |
| 8 | speckit-taskstoissues | Convertir tareas en issues |
| 9 | speckit-agent-context-update | Actualizar contexto del agente |
| 10 | speckit-implement | Implementar el software |
| 11 | speckit-analyze / speckit-checklist | Verificar cumplimiento final |

---

# De forma sencilla

| SDD tradicional | Spec Kit (.claude/skills) |
|---|---|
| Problema | speckit-specify |
| Requisitos | speckit-specify + speckit-clarify |
| Especificación | speckit-specify |
| Validación | speckit-clarify + speckit-checklist |
| Diseño | speckit-plan |
| Análisis | speckit-analyze |
| Tareas | speckit-tasks |
| Gestión del trabajo | speckit-taskstoissues |
| Contexto del agente | speckit-agent-context-update |
| Implementación | speckit-implement |
| Verificación | speckit-checklist + speckit-analyze |

---

# ESPECIFICACIÓN

Una buena especificación se realiza describiendo qué debe hacer el sistema, para quién, bajo qué reglas y cómo se verificará que está correcto, antes de empezar a programar.

En Spec Driven Development, una especificación no debe ser una idea vaga como: "Hacer un login." Debe convertirse en algo claro como: "El sistema debe permitir que un usuario registrado inicie sesión usando correo y contraseña. Si las credenciales son válidas, se crea una sesión. Si son inválidas, se muestra un mensaje de error sin revelar cuál campo falló."

## Estructura de una buena especificación

| Sección | Qué debe contener | Pregunta que responde | Ejemplo |
|---|---|---|---|
| 1. Nombre de la funcionalidad | Título claro y breve | ¿Qué se va a construir? | Inicio de sesión de usuarios |
| 2. Objetivo | Propósito de la funcionalidad | ¿Para qué sirve? | Permitir que usuarios registrados accedan al sistema |
| 3. Usuarios involucrados | Actores o roles que usan la función | ¿Quién la usa? | Usuario registrado, administrador |
| 4. Contexto del problema | Situación que se quiere resolver | ¿Qué necesidad existe? | Los usuarios necesitan acceder a su cuenta de forma segura |
| 5. Requisitos funcionales | Acciones que el sistema debe realizar | ¿Qué debe hacer el sistema? | Validar correo y contraseña |
| 6. Requisitos no funcionales | Calidad, seguridad, rendimiento, usabilidad | ¿Cómo debe comportarse? | La respuesta no debe tardar más de 2 segundos |
| 7. Reglas de negocio | Condiciones propias del sistema | ¿Qué reglas se deben cumplir? | Una cuenta bloqueada no puede iniciar sesión |
| 8. Entradas | Datos que recibe el sistema | ¿Qué información se ingresa? | Correo electrónico y contraseña |
| 9. Salidas | Respuestas del sistema | ¿Qué devuelve el sistema? | Sesión iniciada o mensaje de error |
| 10. Casos de uso o escenarios | Flujos normales y alternativos | ¿Qué puede pasar? | Login exitoso, contraseña incorrecta, cuenta bloqueada |
| 11. Criterios de aceptación | Condiciones para considerar terminado | ¿Cómo sé que está bien hecho? | Dado un usuario válido, cuando ingresa datos correctos, entonces accede |
| 12. Restricciones | Límites técnicos o de negocio | ¿Qué no se puede hacer? | No usar contraseñas en texto plano |
| 13. Fuera de alcance | Lo que no se implementará ahora | ¿Qué queda excluido? | Recuperación de contraseña no incluida en esta versión |

## Plantilla de trabajo

```markdown
# Especificación: [Nombre de la funcionalidad]

## 1. Objetivo
Describir brevemente qué se quiere lograr.

## 2. Contexto
Explicar el problema o necesidad que se quiere resolver.

## 3. Usuarios o actores
- Actor 1:
- Actor 2:

## 4. Requisitos funcionales
- RF-001:
- RF-002:
- RF-003:

## 5. Requisitos no funcionales
- RNF-001:
- RNF-002:

## 6. Reglas de negocio
- RN-001:
- RN-002:

## 7. Entradas
- Dato 1:
- Dato 2:

## 8. Salidas
- Resultado esperado:
- Mensajes de error:

## 9. Escenarios principales
### Escenario 1: Caso exitoso
Dado que...
Cuando...
Entonces...

### Escenario 2: Caso de error
Dado que...
Cuando...
Entonces...

## 10. Criterios de aceptación
- CA-001:
- CA-002:
- CA-003:

## 11. Restricciones
- Restricción 1:
- Restricción 2:

## 12. Fuera de alcance
- Elemento no incluido:
```

### Escenario: Inicio de sesión exitoso

```gherkin
Dado que existe un usuario registrado con correo "ana@email.com"
Y su contraseña es correcta
Cuando el usuario ingresa su correo y contraseña
Entonces el sistema debe iniciar sesión
Y debe redirigirlo al panel principal
```

### Escenario: Inicio de sesión fallido

```gherkin
Dado que el usuario ingresa un correo o contraseña incorrectos
Cuando intenta iniciar sesión
Entonces el sistema debe mostrar el mensaje "Credenciales inválidas"
Y no debe iniciar sesión
```

## Ejemplo Login

| Elemento | Ejemplo |
|---|---|
| Funcionalidad | Inicio de sesión de usuarios |
| Objetivo | Permitir que un usuario registrado acceda al sistema de forma segura |
| Actor principal | Usuario registrado |
| Entrada | Correo electrónico y contraseña |
| Salida exitosa | Sesión iniciada y redirección al panel principal |
| Salida fallida | Mensaje: "Credenciales inválidas" |
| Regla de negocio | El sistema no debe indicar si falló el correo o la contraseña |
| Restricción | La contraseña nunca debe almacenarse en texto plano |
| Criterio de aceptación | Si el usuario ingresa credenciales correctas, el sistema debe iniciar sesión |

## Características de una buena especificación

| Característica | Significado |
|---|---|
| Clara | Se entiende sin necesidad de adivinar |
| Completa | Incluye casos normales, errores y restricciones |
| Verificable | Se puede comprobar con pruebas |
| Sin ambigüedad | No usa frases vagas sin definirlas |
| Ordenada | Separa requisitos, reglas, escenarios y criterios |
| Implementable | El equipo puede convertirla en diseño, tareas y código |
| Mantenible | Puede actualizarse cuando cambian las necesidades |

## Relación con Spec Kit

| Parte de la especificación | Skill de Spec Kit |
|---|---|
| Definir la funcionalidad | speckit-specify |
| Resolver dudas | speckit-clarify |
| Convertirla en diseño técnico | speckit-plan |
| Revisar inconsistencias | speckit-analyze |
| Crear criterios de validación | speckit-checklist |
| Dividir en tareas | speckit-tasks |
| Implementar según la spec | speckit-implement |

## Preguntas que debe responder una buena especificación

- ¿Qué se va a construir?
- ¿Quién lo va a usar?
- ¿Qué debe hacer?
- ¿Qué reglas debe cumplir?
- ¿Qué errores pueden ocurrir?
- ¿Cómo se comprobará que funciona?
- ¿Qué queda fuera del alcance?

---

# Especificaciones para sistemas con varios módulos

Cuando debes poner especificaciones de varias partes del sistema, no conviene escribir todo en un solo documento gigante. Lo correcto es organizar las especificaciones por módulos, funcionalidades o cambios.

```
Sistema completo → Módulos → Funcionalidades → Requisitos → Criterios de aceptación → Tareas
```

## 1. Especificación general del sistema

| Elemento | Ejemplo |
|---|---|
| Nombre del sistema | Sistema de gestión académica |
| Objetivo general | Administrar estudiantes, cursos, matrículas y calificaciones |
| Actores principales | Administrador, docente, estudiante |
| Módulos del sistema | Usuarios, cursos, matrículas, calificaciones, reportes |
| Reglas generales | Solo usuarios autenticados pueden acceder |
| Restricciones generales | El sistema debe usar roles y permisos |

```markdown
# Especificación general: Sistema de gestión académica
El sistema permitirá administrar estudiantes, docentes, cursos,
matrículas y calificaciones.

Módulos:
1. Gestión de usuarios
2. Gestión de cursos
3. Matrículas
4. Calificaciones
5. Reportes
```

## 2. Especificación por módulo

| Módulo | Archivo | Contenido |
|---|---|---|
| Usuarios | usuarios-spec.md | Registro, login, roles, permisos |
| Cursos | cursos-spec.md | Crear curso, editar curso, asignar docente |
| Matrículas | matriculas-spec.md | Inscribir estudiante, cancelar matrícula |
| Calificaciones | calificaciones-spec.md | Registrar nota, editar nota, calcular promedio |
| Reportes | reportes-spec.md | Generar reportes académicos |

## 3. Dentro de cada módulo, separar por funcionalidades

| Módulo | Funcionalidad | Requisitos |
|---|---|---|
| Usuarios | Registro de usuario | Crear cuenta con nombre, correo y contraseña |
| Usuarios | Inicio de sesión | Validar credenciales |
| Usuarios | Roles | Asignar permisos según tipo de usuario |
| Usuarios | Recuperar contraseña | Enviar enlace de recuperación |

```markdown
# Módulo: Usuarios

## Funcionalidad 1: Registro de usuario
El sistema debe permitir crear usuarios con nombre, correo y contraseña.

## Funcionalidad 2: Inicio de sesión
El sistema debe permitir que usuarios registrados ingresen al sistema.

## Funcionalidad 3: Roles y permisos
El sistema debe restringir acciones según el rol del usuario.
```

## 4. Identificadores para ordenar requisitos

| Código | Significado |
|---|---|
| RF-USU-001 | Requisito funcional del módulo Usuarios |
| RF-CUR-001 | Requisito funcional del módulo Cursos |
| RF-MAT-001 | Requisito funcional del módulo Matrículas |
| RF-CAL-001 | Requisito funcional del módulo Calificaciones |
| RNF-001 | Requisito no funcional general |

| ID | Módulo | Requisito |
|---|---|---|
| RF-USU-001 | Usuarios | El sistema debe permitir registrar usuarios |
| RF-USU-002 | Usuarios | El sistema debe permitir iniciar sesión |
| RF-CUR-001 | Cursos | El sistema debe permitir crear cursos |
| RF-MAT-001 | Matrículas | El sistema debe permitir matricular estudiantes |
| RF-CAL-001 | Calificaciones | El sistema debe permitir registrar notas |

## 5. Relación Spec Kit con múltiples módulos

| Paso | Skill | Uso |
|---|---|---|
| 1 | speckit-constitution | Reglas generales del proyecto |
| 2 | speckit-specify | Especificación de cada módulo o funcionalidad |
| 3 | speckit-clarify | Aclarar dudas de cada módulo |
| 4 | speckit-plan | Diseño técnico de cada parte |
| 5 | speckit-analyze | Revisar conflictos entre módulos |
| 6 | speckit-checklist | Criterios de validación por módulo |
| 7 | speckit-tasks | Tareas por funcionalidad |
| 8 | speckit-implement | Implementar siguiendo specs aprobadas |

## 6. Estructura de carpetas recomendada

```
specs/
├── 000-sistema-general/
│   ├── spec.md
│   ├── reglas.md
│   └── glosario.md
├── 001-usuarios/
│   ├── spec.md
│   ├── plan.md
│   ├── tasks.md
│   └── checklist.md
├── 002-cursos/
│   ├── spec.md
│   ├── plan.md
│   ├── tasks.md
│   └── checklist.md
├── 003-matriculas/
│   ├── spec.md
│   ├── plan.md
│   ├── tasks.md
│   └── checklist.md
└── 004-calificaciones/
    ├── spec.md
    ├── plan.md
    ├── tasks.md
    └── checklist.md
```

## 7. Tabla modelo para varias partes del sistema

| Parte | Objetivo | Requisitos principales | Dependencias | Criterio de aceptación |
|---|---|---|---|---|
| Usuarios | Gestionar acceso al sistema | Registrar, iniciar sesión, asignar roles | Base de datos | Un usuario válido puede iniciar sesión |
| Cursos | Administrar cursos | Crear, editar, eliminar cursos | Usuarios/docentes | Un administrador puede crear un curso |
| Matrículas | Inscribir estudiantes | Registrar, cancelar matrícula | Usuarios y cursos | Un estudiante queda inscrito en un curso |
| Calificaciones | Gestionar notas | Registrar, editar y consultar notas | Matrículas | Un docente puede registrar la nota de un estudiante |
| Reportes | Mostrar información resumida | Generar reportes por curso o estudiante | Cursos, matrículas y notas | El sistema genera un reporte correcto |

## 8. Ejemplo completo: Especificación del módulo de Matrículas

```markdown
# Especificación: Módulo de Matrículas

## Objetivo
Permitir que un estudiante sea inscrito en un curso disponible.

## Actores
- Administrador
- Estudiante

## Requisitos funcionales

RF-MAT-001: El sistema debe permitir registrar la matrícula de un estudiante en un curso.
RF-MAT-002: El sistema debe validar que el estudiante exista.
RF-MAT-003: El sistema debe validar que el curso exista.
RF-MAT-004: El sistema no debe permitir matricular dos veces al mismo estudiante en el mismo curso.

## Reglas de negocio

RN-MAT-001: Un estudiante solo puede matricularse en cursos activos.
RN-MAT-002: Una matrícula debe tener estado: activa, cancelada o finalizada.

## Entradas
- ID del estudiante
- ID del curso
- Fecha de matrícula

## Salidas
- Matrícula creada correctamente
- Mensaje de error si el estudiante ya está matriculado

## Criterios de aceptación

CA-MAT-001: Dado que existe un estudiante y existe un curso activo,
            cuando el administrador registra la matrícula,
            entonces el sistema debe guardar la matrícula con estado activa.

CA-MAT-002: Dado que el estudiante ya está matriculado en el curso,
            cuando se intenta registrar otra matrícula,
            entonces el sistema debe mostrar un error.
```

## 9. Regla práctica

| Situación | Qué hacer |
|---|---|
| Es una regla que afecta a todo el sistema | Va en la especificación general o constitución |
| Es una funcionalidad independiente | Va en su propia especificación |
| Es parte de un módulo grande | Va dentro de la spec del módulo |
| Depende de otro módulo | Se declara en "dependencias" |
| Se puede probar por separado | Debe tener sus propios criterios de aceptación |
| Es muy grande | Se divide en varias specs más pequeñas |

## En resumen

```
Especificación general del sistema
        ↓
Especificación del módulo Usuarios
        ↓
Especificación del módulo Cursos
        ↓
Especificación del módulo Matrículas
        ↓
Especificación del módulo Calificaciones
        ↓
Planes, tareas, checklist e implementación por cada módulo
```

Cada parte debe tener: Objetivo, Requisitos, Reglas de negocio, Entradas, Salidas, Escenarios, Criterios de aceptación, Dependencias, Fuera de alcance.

---

# NIVELES EMPRESARIALES

## Especificación del módulo Estratégico-Administrativo

```
specs/
└── 001-estrategico-adm/
    ├── estrategico-adm-spec.md
    ├── plan.md
    ├── tasks.md
    └── checklist.md
```

### Contenido del archivo

| Sección | Contenido | Propósito |
|---|---|---|
| Nombre del módulo | Módulo Estratégico-Administrativo | Identificar la parte del sistema |
| Objetivo | Qué problema resuelve | Definir el propósito |
| Actores | Usuarios que usan el módulo | Saber quién interactúa |
| Requisitos funcionales | Qué debe hacer el sistema | Definir funciones |
| Requisitos no funcionales | Seguridad, rendimiento, usabilidad | Definir calidad |
| Reglas de negocio | Condiciones propias del proceso | Evitar ambigüedades |
| Entradas | Datos que recibe | Saber qué información se registra |
| Salidas | Resultados esperados | Saber qué devuelve el sistema |
| Escenarios | Casos normales y alternativos | Validar comportamiento |
| Criterios de aceptación | Cómo saber que está correcto | Base para pruebas |
| Dependencias | Otros módulos relacionados | Evitar conflictos |
| Fuera de alcance | Qué no se hará en esta parte | Delimitar el trabajo |

### Ejemplo base

```markdown
# Especificación: Módulo Estratégico-Administrativo

## 1. Objetivo
El módulo estratégico-administrativo tiene como objetivo permitir la gestión,
seguimiento y control de información relacionada con la planificación estratégica,
toma de decisiones administrativas y organización interna del sistema.

## 2. Contexto
La organización necesita contar con una sección que permita registrar, consultar
y administrar información clave para la gestión estratégica, como objetivos
institucionales, planes de acción, indicadores, responsables y avances.

## 3. Actores
- Administrador del sistema
- Directivo
- Coordinador administrativo
- Usuario consultor

## 4. Requisitos funcionales

### RF-EADM-001: Gestión de objetivos estratégicos
El sistema debe permitir registrar objetivos estratégicos con nombre, descripción,
responsable, fecha de inicio, fecha de finalización y estado.

### RF-EADM-002: Consulta de objetivos estratégicos
El sistema debe permitir consultar la lista de objetivos estratégicos registrados.

### RF-EADM-003: Actualización de objetivos estratégicos
El sistema debe permitir modificar la información de un objetivo estratégico existente.

### RF-EADM-004: Eliminación o desactivación de objetivos
El sistema debe permitir desactivar objetivos estratégicos que ya no estén vigentes.

### RF-EADM-005: Gestión de planes de acción
El sistema debe permitir crear planes de acción asociados a un objetivo estratégico.

### RF-EADM-006: Seguimiento de avances
El sistema debe permitir registrar el porcentaje de avance de cada plan de acción.

### RF-EADM-007: Gestión de responsables
El sistema debe permitir asignar responsables a objetivos, actividades o planes de acción.

### RF-EADM-008: Reportes administrativos
El sistema debe generar reportes sobre objetivos, planes de acción, responsables y avances.

## 5. Requisitos no funcionales

### RNF-EADM-001: Seguridad
Solo los usuarios autorizados deben poder crear, modificar o eliminar información estratégica.

### RNF-EADM-002: Rendimiento
Las consultas principales del módulo no deben tardar más de 3 segundos en condiciones normales.

### RNF-EADM-003: Usabilidad
Las pantallas del módulo deben ser claras y permitir identificar fácilmente
objetivos, responsables, fechas y estados.

### RNF-EADM-004: Trazabilidad
El sistema debe registrar qué usuario creó o modificó cada objetivo estratégico.

## 6. Reglas de negocio

### RN-EADM-001
Un objetivo estratégico debe tener al menos un responsable asignado.

### RN-EADM-002
Un plan de acción debe estar asociado a un objetivo estratégico existente.

### RN-EADM-003
El porcentaje de avance de un plan de acción no puede ser menor que 0 ni mayor que 100.

### RN-EADM-004
Un objetivo finalizado no debe permitir nuevos planes de acción,
salvo que sea reactivado por un administrador.

## 7. Entradas
- Nombre del objetivo estratégico
- Descripción
- Responsable
- Fecha de inicio
- Fecha de finalización
- Estado
- Plan de acción
- Porcentaje de avance
- Observaciones

## 8. Salidas
- Objetivo estratégico registrado
- Lista de objetivos estratégicos
- Reporte de avances
- Mensajes de confirmación
- Mensajes de error o validación

## 9. Estados posibles
Los objetivos estratégicos pueden tener los siguientes estados:
- Pendiente
- En proceso
- Finalizado
- Cancelado
- Inactivo

## 10. Escenarios

### Escenario 1: Registro exitoso de objetivo estratégico
Dado que el usuario tiene permisos administrativos
Y completa los datos obligatorios del objetivo estratégico
Cuando guarda la información
Entonces el sistema debe registrar el objetivo
Y debe mostrar un mensaje de confirmación.

### Escenario 2: Registro con datos incompletos
Dado que el usuario intenta registrar un objetivo estratégico
Y no completa los campos obligatorios
Cuando intenta guardar la información
Entonces el sistema debe mostrar los campos faltantes
Y no debe registrar el objetivo.

### Escenario 3: Actualización de avance
Dado que existe un plan de acción asociado a un objetivo estratégico
Cuando el usuario registra un porcentaje de avance válido
Entonces el sistema debe actualizar el avance del plan de acción.

### Escenario 4: Avance inválido
Dado que el usuario intenta registrar un avance menor que 0 o mayor que 100
Cuando intenta guardar el avance
Entonces el sistema debe mostrar un mensaje de error
Y no debe actualizar el plan de acción.

## 11. Criterios de aceptación

### CA-EADM-001
El sistema permite crear un objetivo estratégico con todos los datos obligatorios.

### CA-EADM-002
El sistema impide guardar objetivos estratégicos incompletos.

### CA-EADM-003
El sistema permite consultar objetivos estratégicos registrados.

### CA-EADM-004
El sistema permite actualizar el estado de un objetivo estratégico.

### CA-EADM-005
El sistema permite asociar planes de acción a objetivos existentes.

### CA-EADM-006
El sistema valida que el porcentaje de avance esté entre 0 y 100.

### CA-EADM-007
El sistema genera reportes administrativos con información de objetivos,
responsables y avances.

## 12. Dependencias
Este módulo puede depender de:
- Módulo de usuarios
- Módulo de roles y permisos
- Módulo de reportes
- Base de datos institucional

## 13. Fuera de alcance
En esta versión no se incluye:
- Inteligencia artificial para análisis estratégico
- Predicción automática de cumplimiento de objetivos
- Integración con sistemas externos
- Firma digital de documentos administrativos
```

### Relación con Spec Kit

| Archivo | Skill relacionado | Función |
|---|---|---|
| estrategico-adm-spec.md | speckit-specify | Define qué debe hacer el módulo |
| plan.md | speckit-plan | Define cómo se construirá |
| tasks.md | speckit-tasks | Divide el módulo en tareas |
| checklist.md | speckit-checklist | Define cómo se validará |
| Análisis del módulo | speckit-analyze | Revisa inconsistencias |
| Implementación | speckit-implement | Construye según la especificación |

---

# Estructura de carpetas recomendada (niveles empresariales)

```
specs/
├── 000-sistema-general/
│   ├── spec.md
│   ├── glossary.md
│   └── rules.md
├── 001-estrategico-adm/
│   ├── estrategico-adm-spec.md
│   ├── plan.md
│   ├── tasks.md
│   └── checklist.md
├── 002-Tactico/
│   ├── usuarios-spec.md
│   ├── plan.md
│   ├── tasks.md
│   └── checklist.md
├── 003-operativo/
    ├── reportes-spec.md
    ├── plan.md
    ├── tasks.md
    └── checklist.md
```

## Ventajas de separar por carpetas

| Ventaja | Explicación |
|---|---|
| Orden | Cada módulo tiene su propia especificación |
| Mantenimiento | Puedes modificar una parte sin afectar todo |
| Claridad | Es más fácil saber qué pertenece a cada módulo |
| Mejor planificación | Cada módulo puede tener su propio plan.md |
| Mejor implementación | speckit-implement puede trabajar sobre una parte específica |
| Mejor validación | Cada módulo puede tener su propio checklist.md |
| Escalabilidad | Si el sistema crece, la estructura sigue ordenada |

## Ejemplo más completo

```
specs/
├── estrategico/
│   └── administrativo/
│       └── estrategico-adm-spec.md
├── tactico/
│   └── financiero/
│       ├── financiero-spec.md
│       ├── plan.md
│       ├── tasks.md
│       └── checklist.md
└── operativo/
    └── inventario/
        ├── inventario-spec.md
        ├── plan.md
        ├── tasks.md
        └── checklist.md
```
