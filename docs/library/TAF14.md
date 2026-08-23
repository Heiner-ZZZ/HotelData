# TAF14 — Informes Estratégicos de HotelData

**Asignatura:** Construcción del Software — Sexto semestre  
**Sistema:** HotelData — Plataforma de gestión hotelera y analítica  
**Versión:** 2.0 | **Fecha:** 2026-08-09  
**Documento base:** TAF06, TA07, TA11, TA12 y EVF14 se utilizan únicamente como contexto de continuidad.

> **Alcance de la definición:** Se define el alcance estratégico nuevo de HotelData, sus dos vistas, sus informes, sus decisiones, sus indicadores y su evolución hacia IA predictiva. Los documentos anteriores no limitan este diseño ni deben utilizarse para convertir un informe estratégico en una repetición de un informe ya existente.

---

## 1. Propósito

Se define cómo HotelData ayudará a la dirección de la plataforma y a los propietarios de hoteles a tomar decisiones de largo plazo.

La pregunta central ya no es únicamente qué ocurrió en una reserva o en una jornada. La pregunta estratégica es:

> **¿Qué hoteles, planes, mercados y oportunidades deben recibir atención, inversión, reposicionamiento o crecimiento?**

Los informes deben:

- Comparar resultados en horizontes mensuales, trimestrales, semestrales y anuales.
- Mostrar tendencias y no únicamente valores aislados.
- Identificar oportunidades, riesgos y prioridades.
- Relacionar indicadores con decisiones de dirección.
- Diferenciar resultado actual, potencial futuro y nivel de confianza.
- Servir tanto a una propiedad individual como a toda la infraestructura hotelera.
- Incorporar progresivamente forecasting, IA predictiva y recomendaciones explicables.

No se crea una segunda versión de informes diarios ya existentes. Se define una capa de lectura estratégica: integrada, comparativa, prospectiva y orientada a decisiones.

---

## 2. Dos vistas estratégicas

HotelData tendrá dos niveles estratégicos claramente separados.

| Vista | Alcance | Usuario principal | Pregunta estratégica |
|---|---|---|---|
| **Vista A — Hotel individual** | Una propiedad específica | Dueño, gerente o responsable autorizado | ¿Cómo debe posicionarse, crecer y mejorar este hotel? |
| **Vista B — Control global** | Toda la cartera hotelera | `super_admin` y dirección corporativa | ¿Dónde debe invertir, intervenir, crecer o corregir la organización? |

### 2.1 Vista A — Hotel individual

La Vista A analiza una sola propiedad y no debe mostrar información confidencial de hoteles que estén fuera del alcance del usuario.

Su lectura estratégica comprende:

- Rentabilidad y contribución de los planes hoteleros.
- Evolución comercial de la propiedad.
- Posicionamiento frente al mercado cercano.
- Capacidad de sostener precios y diferenciación.
- Escenarios futuros de demanda, revenue y margen.
- Prioridades de crecimiento y reposicionamiento.

La Vista A tendrá **dos informes estratégicos**, cada uno con varias vistas internas:

| Código | Informe estratégico | Decisión que habilita |
|---|---|---|
| **IE-H01** | Análisis estratégico del desempeño económico-comercial y rentabilidad por plan hotelero | Mantener, rediseñar, promover o retirar planes hoteleros |
| **IE-H02** | Posicionamiento competitivo local y estrategia de mercado en un radio aproximado de 5 km | Definir diferenciación, banda de precio y estrategia competitiva |

### 2.2 Vista B — Control global

La Vista B observa la infraestructura hotelera como una cartera. No se limita a ordenar hoteles por un único número: debe explicar la relación entre rendimiento, potencial, riesgo, mercado y prioridades de inversión.

La Vista B tendrá **cinco informes estratégicos**:

| Código | Informe estratégico global | Decisión que habilita |
|---|---|---|
| **IE-G01** | Balanced Scorecard estratégico para el desempeño y crecimiento de la cartera hotelera | Equilibrar resultados financieros, mercado, cliente, innovación y crecimiento |
| **IE-G02** | Rankings estratégicos de rendimiento, oportunidad y riesgo de hoteles, mercados y planes | Priorizar inversión, acompañamiento, expansión y replicación de buenas prácticas |
| **IE-G03** | Análisis estratégico de rentabilidad, contribución y composición comercial de la cartera | Decidir qué hoteles y planes generan valor sostenible |
| **IE-G04** | Mapa estratégico de mercados, destinos, segmentos y posicionamiento de la cartera | Detectar territorios, segmentos y destinos con oportunidad |
| **IE-G05** | Forecasting e inteligencia predictiva para demanda, revenue y oportunidades de cartera | Anticipar demanda, revenue, riesgos y oportunidades futuras |

> La propuesta estratégica queda definida. IE-G05 tiene su alcance, informes y reglas establecidos; la incorporación progresiva de modelos predictivos es una evolución de implementación, no una ausencia de diseño.

---

## 3. Principios estratégicos

### 3.1 Cada informe debe producir una decisión

Todo informe estratégico debe responder explícitamente:

1. ¿Qué situación está mostrando?
2. ¿Por qué es importante para la dirección?
3. ¿Qué comparación o tendencia debe observarse?
4. ¿Qué oportunidad o riesgo revela?
5. ¿Qué decisión permite tomar?
6. ¿Qué horizonte de tiempo utiliza?
7. ¿Qué nivel de confianza y cobertura tienen sus datos?

### 3.2 Los antecedentes no son el alcance nuevo

TA06, TA07, TA11, TA12 y EVF14 se revisaron para mantener vocabulario, objetivos y continuidad institucional. Sin embargo:

- Los informes ya definidos anteriormente no se presentan como novedades del diseño.
- Las consultas de detalle no se convierten artificialmente en informes estratégicos.
- Un informe estratégico debe agregar contexto, comparación, proyección y decisión.
- Los indicadores existentes pueden servir como insumos, pero el producto debe ser una lectura nueva.
- La existencia de una métrica no significa que exista el informe estratégico que la interpreta.

### 3.3 La estrategia debe ser comparable

Las comparaciones deben respetar:

- Período equivalente.
- Moneda normalizada cuando corresponda.
- Segmento y categoría comparables.
- Tamaño y capacidad del hotel.
- Volumen mínimo de observaciones.
- Diferencia entre rendimiento observado y potencial estimado.
- Separación entre datos confirmados y predicciones.

### 3.4 La estrategia debe ser explicable

Un ranking, semáforo o recomendación no puede limitarse a mostrar una etiqueta. Debe indicar sus factores principales, el período analizado, la variación y la razón de la prioridad.

---

## 4. IE-G01 — Balanced Scorecard estratégico para el desempeño y crecimiento de la cartera hotelera

### 4.1 Propósito

El Balanced Scorecard será el informe ejecutivo principal de la Vista B. Permitirá que la dirección observe la cartera desde varias perspectivas y evite tomar decisiones basadas únicamente en ingresos.

El BSC tendrá cinco perspectivas estratégicas:

| Perspectiva | Pregunta | Resultado esperado |
|---|---|---|
| **Financiera y comercial** | ¿La cartera genera valor y crecimiento? | Prioridades de inversión, reposicionamiento y rentabilidad |
| **Cliente y reputación** | ¿La propuesta hotelera conserva preferencia y confianza? | Decisiones de diferenciación y experiencia de marca |
| **Mercado y posicionamiento** | ¿Dónde está ganando o perdiendo posición la cartera? | Selección de mercados y segmentos prioritarios |
| **Crecimiento e innovación** | ¿La organización está preparada para crecer y anticiparse? | Priorización de automatización, IA y nuevas capacidades |
| **Sostenibilidad y resiliencia** | ¿El crecimiento puede sostenerse ante cambios de demanda y costos? | Escenarios, prevención de concentración y continuidad estratégica |

### 4.2 Elementos del BSC

El informe debe presentar:

- Objetivo estratégico.
- Indicadores asociados.
- Meta y tendencia.
- Variación frente al período anterior.
- Nivel de cumplimiento.
- Hoteles o mercados que explican el resultado.
- Riesgo u oportunidad detectada.
- Acción recomendada.

El BSC no será una suma automática de tarjetas. Cada perspectiva debe relacionarse con los objetivos estratégicos de HotelData y con una agenda de decisión.

---

## 5. IE-G02 — Rankings estratégicos de rendimiento, oportunidad y riesgo

Los rankings sí son informes estratégicos cuando ayudan a decidir. No serán listas decorativas ni ordenamientos aislados.

### 5.1 Rankings globales completos

| Código | Ranking | Criterio estratégico | Decisión |
|---|---|---|---|
| **R-G01** | Hoteles líderes de la cartera | Resultado, crecimiento, consistencia y potencial de referencia | Replicar prácticas y proteger fortalezas |
| **R-G02** | Hoteles con mayor oportunidad | Potencial futuro frente al rendimiento observado | Priorizar acompañamiento e inversión |
| **R-G03** | Hoteles con riesgo estratégico | Deterioro persistente, concentración, pérdida de mercado o baja resiliencia | Activar un plan de corrección |
| **R-G04** | Mercados y destinos con mayor oportunidad | Demanda, crecimiento, atractivo y capacidad de la cartera | Decidir expansión y posicionamiento |
| **R-G05** | Planes hoteleros con mayor contribución | Revenue neto, margen, recurrencia y sostenibilidad comercial | Mantener, rediseñar o retirar planes |
| **R-G06** | Hoteles referentes en reputación | Nivel, evolución y consistencia de la percepción del huésped | Replicar prácticas de marca y servicio |

### 5.2 Reglas de los rankings

Cada ranking debe mostrar:

- Criterio de ordenamiento.
- Período analizado.
- Variación frente al período anterior.
- Cobertura y cantidad de observaciones.
- Segmento o grupo de comparación.
- Nivel de confianza.
- Motivo de la posición.
- Decisión sugerida.

Debe existir más de una lectura: rendimiento actual, oportunidad futura y riesgo. Un hotel con alto resultado no necesariamente es el hotel con mayor potencial de crecimiento.

---

## 6. IE-G03 — Análisis estratégico de rentabilidad, contribución y composición comercial de la cartera

### 6.1 Rentabilidad por plan hotelero

Sí habrá un informe estratégico de ganancias y contribución por plan para cada hotel. Este informe también alimentará el análisis global de la cartera.

La pregunta estratégica no es solamente qué plan vende más, sino:

> **¿Qué plan crea valor sostenible después de descuentos, devoluciones, comisiones y costos asociados?**

El informe debe distinguir claramente:

| Concepto | Interpretación estratégica |
|---|---|
| **Revenue bruto** | Volumen comercial antes de ajustes |
| **Revenue neto** | Resultado después de descuentos, devoluciones y comisiones |
| **Contribución** | Valor después de costos variables y costos directos disponibles |
| **Ganancia neta** | Resultado posterior a todos los costos que el modelo pueda atribuir correctamente |
| **Margen** | Capacidad del plan para producir valor relativo |
| **Valor futuro** | Contribución esperada según demanda y escenarios |

Cuando todavía no exista información suficiente para calcular ganancia neta, el informe debe llamarse contribución o rentabilidad parcial. Nunca debe presentar revenue como ganancia.

### 6.2 Decisiones que habilita

- Identificar planes que venden mucho pero producen poco margen.
- Detectar planes que atraen huéspedes de alto valor o recurrencia.
- Comparar descuentos frente a contribución real.
- Simular cambios de precio y restricciones.
- Definir qué planes deben crecer, mantenerse, rediseñarse o retirarse.
- Comparar la composición de ingresos de cada hotel.
- Identificar dependencia excesiva de un solo plan o segmento.

### 6.3 Lectura global de cartera

IE-G03 permitirá comparar hoteles por:

- Crecimiento rentable.
- Diversificación de planes.
- Margen y contribución.
- Dependencia de segmentos.
- Capacidad de sostener el resultado en diferentes temporadas.
- Potencial de replicar un modelo comercial exitoso.

---

## 7. IE-G04 — Mapa estratégico de mercados, destinos, segmentos y posicionamiento

IE-G04 analizará la posición de la cartera en mercados, destinos y segmentos. Su objetivo no es describir una venta puntual, sino definir dónde competir y dónde crecer.

Debe responder:

- ¿Qué mercados están creciendo?
- ¿Qué destinos tienen demanda compatible con la oferta de HotelData?
- ¿Qué segmentos muestran mayor valor futuro?
- ¿Qué hoteles están bien posicionados y cuáles están desaprovechando su mercado?
- ¿Dónde existe concentración o dependencia excesiva?
- ¿Qué mercado requiere inversión, diferenciación o una nueva propuesta?

Las visualizaciones estratégicas incluirán:

- Mapa de oportunidades por mercado y destino.
- Matriz crecimiento × posición actual.
- Evolución de participación y atractivo.
- Comparación entre hoteles de una misma zona.
- Priorización de segmentos y temporadas.

---

## 8. IE-H02 — Posicionamiento competitivo local y estrategia de mercado en un radio aproximado de 5 km

El análisis de mercado cercano sí es estratégico cuando se utiliza para decidir el posicionamiento de un hotel, no únicamente para cambiar un precio en un día concreto.

### 8.1 Qué debe analizar

| Dimensión | Pregunta estratégica |
|---|---|
| **Conjunto competitivo** | ¿Qué hoteles son realmente comparables con esta propiedad? |
| **Precio relativo** | ¿El hotel está por encima, debajo o dentro de una banda defendible? |
| **Producto** | ¿Qué características justifican la diferencia de precio? |
| **Reputación** | ¿La experiencia permite sostener el posicionamiento? |
| **Demanda** | ¿Qué segmentos y temporadas ofrecen oportunidad? |
| **Diferenciación** | ¿Qué debe mejorar o comunicar el hotel para ganar posición? |
| **Escenarios** | ¿Qué ocurriría con diferentes precios, productos o planes? |

### 8.2 Decisiones

IE-H02 debe ayudar a:

- Definir el conjunto competitivo del hotel.
- Establecer una banda de precio sostenible.
- Detectar una posición de precio sin respaldo de producto o reputación.
- Encontrar oportunidades de diferenciación.
- Proponer inversiones comerciales y de producto.
- Preparar escenarios de temporada alta, baja y eventos.

El ajuste diario de precio es una acción posterior. La decisión estratégica es definir el posicionamiento que orientará esos ajustes.

---

## 9. IE-G05 — Forecasting e inteligencia predictiva para demanda, revenue y oportunidades de cartera

La integración de IA predictiva y forecasting está definida como la siguiente evolución estratégica de HotelData. Su propósito es anticipar y recomendar, no solamente resumir el pasado.

### 9.1 Informes predictivos planificados

| Código | Informe futuro | Predicción o análisis | Decisión estratégica |
|---|---|---|---|
| **IA-01** | Forecasting de demanda | Demanda futura por hotel, mercado y temporada | Preparar crecimiento, capacidad y campañas |
| **IA-02** | Forecasting de revenue y margen | Escenarios de revenue, RevPAR y contribución | Elegir estrategia comercial futura |
| **IA-03** | Recomendador de posicionamiento de precio | Banda competitiva según demanda, producto y reputación | Ajustar estrategia de precio del hotel |
| **IA-04** | Riesgo de cancelación y volatilidad | Probabilidad de cancelación, no-show o variación de demanda | Proteger escenarios y capacidad |
| **IA-05** | Detección de anomalías estratégicas | Cambios inusuales de mercado, reputación o rentabilidad | Investigar riesgos antes de que escalen |
| **IA-06** | Simulador de planes hoteleros | Resultado esperado de precio, descuento y condiciones | Diseñar el portafolio más rentable |
| **IA-07** | Score de oportunidad de cartera | Potencial de cada hotel frente a su situación actual | Priorizar inversión y acompañamiento |
| **IA-08** | Predicción de valor y recurrencia | Probabilidad de retorno y valor futuro de segmentos | Diseñar fidelización y crecimiento |

### 9.2 Reglas de confianza

Todo informe con IA debe mostrar:

- Horizonte de predicción.
- Datos utilizados.
- Nivel o intervalo de confianza.
- Fecha de cálculo.
- Versión del modelo.
- Diferencia entre observado y predicho.
- Razones principales de la recomendación.
- Resultado posterior para evaluar si la predicción fue correcta.

La IA recomendará antes de automatizar. Ninguna primera versión debe cambiar precios, capacidad o planes sin revisión de un usuario autorizado.

---

## 10. ETL MongoDB hacia ClickHouse como soporte de consolidación estratégica

El proceso ETL que alimenta la capa analítica estratégica está definido como infraestructura de consolidación. Su función es preparar agregados confiables para que los informes puedan comparar hoteles, períodos, planes y mercados.

El flujo ya definido es:

```text
MongoDB
  │ extracción agregada
  │ transformación y normalización
  │ validación de calidad
  │ carga en ClickHouse
  │ informes estratégicos
```

La ejecución cuenta con horario configurable, corrida manual, control de progreso, reporte de calidad y evidencia de la última actualización. El ETL no constituye un informe estratégico por sí mismo: es la base de información que permite construirlos.

El diseño estratégico no queda limitado a las métricas actualmente disponibles. Cuando se incorporen nuevas métricas para rentabilidad, mercado, forecasting o IA, el proceso podrá ampliarse sin modificar la separación entre Vista A y Vista B.

---

## 11. Trazabilidad estratégica

| Objetivo estratégico | Informe TAF14 | Vista | Resultado |
|---|---|---|---|
| Dirigir el crecimiento de la cartera | IE-G01, IE-G02, IE-G03 | B global | Prioridades de inversión y crecimiento |
| Equilibrar resultados financieros y no financieros | IE-G01 | B global | Agenda estratégica equilibrada |
| Mejorar la posición competitiva | IE-G04, IE-H02 | B global y A individual | Mercados, segmentos y precios defendibles |
| Aumentar la rentabilidad de los planes | IE-G03, IE-H01 | B global y A individual | Portafolio de planes más rentable |
| Anticipar demanda y riesgos | IE-G05 | B global | Escenarios y recomendaciones futuras |
| Desarrollar el potencial de cada propiedad | IE-G02, IE-G03, IE-H01, IE-H02 | Ambas vistas | Acompañamiento y decisiones por hotel |

---

## 12. Criterios de aceptación estratégica

Se considera cumplido cuando:

- Existen las dos vistas estratégicas claramente separadas.
- La Vista A contiene como máximo dos informes estratégicos por hotel.
- La Vista B contiene informes de cartera y no una simple suma de pantallas individuales.
- El BSC está definido como informe ejecutivo.
- Los rankings incluyen rendimiento, oportunidad, riesgo, mercados y planes.
- La rentabilidad por plan diferencia revenue, contribución y ganancia.
- El mercado de aproximadamente 5 km está definido como herramienta de posicionamiento estratégico.
- Forecasting e IA tienen informes futuros, objetivos y reglas de confianza definidos.
- El ETL MongoDB hacia ClickHouse está documentado como infraestructura de consolidación, sin convertirlo en una repetición de informes anteriores.
- Ningún informe estratégico se presenta como novedad si únicamente repite un informe ya existente.
- Cada informe termina en una decisión de dirección.

**Resultado:** queda establecida la especificación estratégica nueva de HotelData.

---

## 13. Conclusión

HotelData contará con una lectura estratégica integral para sus dos niveles de decisión:

- La **Vista A** decidirá cómo crecer, posicionar y rentabilizar cada hotel.
- La **Vista B** decidirá dónde invertir, intervenir, expandir y replicar capacidades en toda la cartera.
- El **BSC** equilibrará la visión financiera, comercial, de mercado, innovación y resiliencia.
- Los **rankings** priorizarán hoteles, mercados, destinos, planes, oportunidades y riesgos.
- La **rentabilidad por plan** mostrará qué propuestas generan valor sostenible.
- El **mercado de 5 km** permitirá diseñar una posición competitiva defendible.
- El **forecasting y la IA** convertirán los informes en instrumentos de anticipación y recomendación.
- El **ETL MongoDB hacia ClickHouse** funcionará como soporte de consolidación para esta nueva capa estratégica.

No se repite el pasado: los documentos anteriores se utilizan para conservar consistencia y definir lo nuevo que HotelData necesita para dirigir su futuro.

---

## 14. Referencias

- `docs/library/source/TAF06_extracted.md` — objetivos estratégicos y visión inicial.
- `docs/library/source/TA07_ESPECIFICACIONES.md` — trazabilidad de objetivos y requisitos.
- `docs/library/TA11.md` — contexto de arquitectura y niveles de decisión.
- `docs/library/TA12.md` y `docs/library/EVF14.md` — contexto de continuidad documental.
- `docs/PLAN_ETL_MONGO_TO_CLICKHOUSE.md` — contexto del proceso de consolidación analítica.
- Fatima, T. & Elbanna, S. (2020), *Balanced scorecard in the hospitality and tourism industry: Past, present and future*, International Journal of Hospitality Management, 91, 102656: <https://pmc.ncbi.nlm.nih.gov/articles/PMC7456592/>.
- Mews, *Hotel Industry KPIs: What to Track and Why*: <https://www.mews.com/en/blog/hotel-industry-kpis>.
