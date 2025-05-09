# Sistema de Gestión de Logs de Estaciones Meteorológicas

Este proyecto implementa un sistema completo para la gestión de logs de estaciones meteorológicas, utilizando una arquitectura de microservicios con principios SOLID/GRASP y patrones de diseño.

Realizado por los estudiantes:\
Isabella Sofía Arrieta Guardo \
José Fernando González Ortiz  
Eduardo Alejandro Negrín Perez

## Arquitectura del Sistema

El sistema está diseñado siguiendo una arquitectura de microservicios, donde cada componente tiene una responsabilidad única y bien definida:

1. **Productores**: Servicios Python que simulan estaciones meteorológicas y envían datos en formato JSON.
2. **RabbitMQ**: Broker de mensajería para la comunicación asíncrona entre productores y consumidores.
3. **Consumidores**: Microservicios Python que procesan los mensajes, validan los datos y los almacenan en PostgreSQL.
4. **Servicio de Alertas**: Microservicio que monitorea los datos y genera alertas basadas en umbrales configurables.
5. **API REST**: Servicio que proporciona acceso a los datos históricos y alertas.
6. **PostgreSQL**: Base de datos para almacenamiento persistente de los logs meteorológicos.
7. **Monitoreo y Alertas**: Sistema completo con Prometheus, Alertmanager y Grafana para monitoreo, generación de alertas y visualización.

## Principios de Diseño Aplicados

### Principios SOLID

1. **Principio de Responsabilidad Única (SRP)**
   - Cada clase tiene una única responsabilidad
   - Ejemplo: Separación de la validación de datos, procesamiento y persistencia en clases distintas

2. **Principio Abierto/Cerrado (OCP)**
   - Las clases están abiertas para extensión pero cerradas para modificación
   - Ejemplo: Sistema de validadores extensible sin modificar el código existente

3. **Principio de Sustitución de Liskov (LSP)**
   - Las clases derivadas pueden sustituir a sus clases base
   - Ejemplo: Diferentes tipos de estaciones meteorológicas implementan la misma interfaz

4. **Principio de Segregación de Interfaces (ISP)**
   - Interfaces específicas en lugar de una interfaz general
   - Ejemplo: Interfaces separadas para publicación, consumo y persistencia

5. **Principio de Inversión de Dependencias (DIP)**
   - Dependencia de abstracciones, no de implementaciones concretas
   - Ejemplo: Inyección de dependencias para servicios de mensajería y base de datos

### Principios GRASP

1. **Experto en Información**
   - Las responsabilidades se asignan a la clase que tiene la información necesaria
   - Ejemplo: La validación de datos meteorológicos se realiza en clases especializadas

2. **Creador**
   - Asignar la responsabilidad de crear objetos a clases específicas
   - Ejemplo: Factories para crear estaciones y validadores

3. **Alta Cohesión y Bajo Acoplamiento**
   - Componentes con responsabilidades relacionadas y mínimas dependencias
   - Ejemplo: Separación clara entre productores, consumidores y servicios de datos

## Patrones de Diseño Implementados

1. **Factory Method**
   - **Uso**: Creación de diferentes tipos de estaciones meteorológicas y validadores
   - **Justificación**: Permite añadir nuevos tipos de estaciones o validadores sin modificar el código existente

2. **Strategy**
   - **Uso**: Diferentes estrategias de validación para distintos tipos de datos
   - **Justificación**: Facilita la adición de nuevas reglas de validación y su intercambio en tiempo de ejecución

3. **Observer**
   - **Uso**: Sistema de alertas que reacciona a condiciones específicas
   - **Justificación**: Desacopla la detección de condiciones anómalas de las acciones a tomar

4. **Repository**
   - **Uso**: Abstracción del acceso a la base de datos
   - **Justificación**: Aísla la lógica de negocio de los detalles de persistencia

5. **Adapter**
   - **Uso**: Integración con RabbitMQ y otros sistemas externos
   - **Justificación**: Proporciona una interfaz consistente independientemente del sistema de mensajería utilizado

## Requisitos

- Docker y Docker Compose
- Git

## Instalación y Ejecución

1. Clonar el repositorio:
   ```python
   git clone https://github.com/Joverit5/Sistemas-de-Mensajes.git
   cd Sistemas-de-Mensajes
   ```

2. Iniciar los servicios con Docker Compose:
   ```python
   docker-compose up -d
   ```

3. Verificar que todos los servicios estén funcionando:
   ```python
   docker-compose ps
   ```

## Acceso a los Servicios

- **RabbitMQ Management**: http://localhost:15672 (usuario: weather_user, contraseña: weather_password)
- **API REST**: http://localhost:8000
- **Prometheus**: http://localhost:9090
- **Alertmanager**: http://localhost:9093
- **Grafana**: http://localhost:3000 (usuario: admin, contraseña: admin)

## Sistema de Monitoreo y Alertas

El sistema incluye una configuración completa de monitoreo y alertas basada en Prometheus, Alertmanager y Grafana.

### Alertas en Prometheus

El sistema utiliza un archivo `alerts.yml` que define reglas de alertas para diferentes aspectos:

- **Condiciones meteorológicas**: Alertas para temperaturas extremas, alta humedad, vientos fuertes, etc.
- **Estado de las estaciones**: Alertas para batería baja, estaciones sin reportar, etc.
- **Rendimiento del sistema**: Alertas para fallos en el procesamiento de mensajes, colas grandes, etc.
- **Estado de los servicios**: Alertas para servicios caídos, alto uso de CPU/memoria, etc.
- **Base de datos**: Alertas para problemas con PostgreSQL.

### Gestión de Alertas con Alertmanager

Alertmanager está configurado para gestionar las alertas generadas por Prometheus. La configuración actual:

- Agrupa alertas relacionadas para evitar notificaciones duplicadas
- Clasifica las alertas por categoría y severidad
- No envía notificaciones por correo (configuración silenciosa)

### Visualización en Grafana

Se han implementado dos dashboards principales en Grafana:

1. **Weather Station Dashboard**: Muestra métricas de las estaciones meteorológicas, como temperatura, humedad, presión, etc.

2. **Panel de Alertas**: Dashboard especializado que muestra:
   - Gráfico de alertas enviadas por severidad (`weather_alerts_notifications_sent_total`)
   - Tabla de alertas activas
   - Distribución de alertas por severidad
   - Contador de alertas activas
   - Evolución temporal de alertas por severidad

## Configuración del Sistema de Alertas

### Personalización de Alertas

Para personalizar las alertas según sus necesidades:

1. Edite el archivo `monitoring/alerts.yml` para modificar umbrales o añadir nuevas reglas
2. Reinicie Prometheus para aplicar los cambios:
   ```python
   docker-compose restart prometheus
   ```

3. Verifique las alertas en la interfaz de Prometheus: http://localhost:9090/alerts

## API REST

La API REST proporciona los siguientes endpoints:

- `GET /stations`: Lista todas las estaciones meteorológicas
- `GET /stations/{station_id}`: Obtiene información de una estación específica
- `GET /readings`: Obtiene lecturas meteorológicas con filtros opcionales
- `GET /readings/latest`: Obtiene la última lectura de cada estación
- `GET /alerts`: Obtiene alertas con filtros opcionales
- `GET /alert-configurations`: Obtiene las configuraciones de alertas

## Solución de Problemas

### Visualización en Grafana

Si los dashboards no muestran datos:

1. Verifique que la fuente de datos de Prometheus está configurada correctamente en Grafana
2. Asegúrese de que Prometheus está recopilando datos de todos los servicios
3. Compruebe que las métricas utilizadas en los paneles existen en Prometheus

## Extensiones Posibles

1. **Notificaciones de Alertas**: Configurar Alertmanager para enviar notificaciones por email, Slack, etc.
2. **Autenticación y Autorización**: Implementar JWT o OAuth2 para la API REST
3. **Escalabilidad Horizontal**: Desplegar múltiples instancias de consumidores para manejar mayor carga
4. **Procesamiento Avanzado**: Implementar análisis de datos y predicciones meteorológicas
5. **Dashboards Personalizados**: Crear paneles adicionales en Grafana para visualizaciones específicas

## Licencia

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo LICENSE para más detalles.
