# Sistema de Gestión de Logs de Estaciones Meteorológicas

Este proyecto implementa un sistema completo para la gestión de logs de estaciones meteorológicas, utilizando una arquitectura de microservicios con principios SOLID/GRASP y patrones de diseño.

## Arquitectura del Sistema

El sistema está diseñado siguiendo una arquitectura de microservicios, donde cada componente tiene una responsabilidad única y bien definida:

1. **Productores**: Servicios Python que simulan estaciones meteorológicas y envían datos en formato JSON.
2. **RabbitMQ**: Broker de mensajería para la comunicación asíncrona entre productores y consumidores.
3. **Consumidores**: Microservicios Python que procesan los mensajes, validan los datos y los almacenan en PostgreSQL.
4. **Servicio de Alertas**: Microservicio que monitorea los datos y genera alertas basadas en umbrales configurables.
5. **API REST**: Servicio que proporciona acceso a los datos históricos y alertas.
6. **PostgreSQL**: Base de datos para almacenamiento persistente de los logs meteorológicos.
7. **Monitoreo**: Sistema de logs y métricas con Prometheus y Grafana.

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
   \`\`\`bash
   git clone https://github.com/usuario/weather-station-logs.git
   cd weather-station-logs
   \`\`\`

2. Iniciar los servicios con Docker Compose:
   \`\`\`bash
   docker-compose up -d
   \`\`\`

3. Verificar que todos los servicios estén funcionando:
   \`\`\`bash
   docker-compose ps
   \`\`\`

## Acceso a los Servicios

- **RabbitMQ Management**: http://localhost:15672 (usuario: weather_user, contraseña: weather_password)
- **API REST**: http://localhost:8000
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (usuario: admin, contraseña: admin)

## Estructura del Proyecto

\`\`\`
weather-station-logs/
├── docker-compose.yml          # Configuración de Docker Compose
├── README.md                   # Documentación del proyecto
├── producers/                  # Servicio productor de datos
│   ├── Dockerfile
│   ├── requirements.txt
│   └── weather_producer/       # Módulos del productor
│       ├── __init__.py
│       ├── main.py
│       ├── models.py
│       ├── factories.py
│       ├── messaging/
│       └── stations/
├── consumers/                  # Servicio consumidor de datos
│   ├── Dockerfile
│   ├── requirements.txt
│   └── weather_consumer/       # Módulos del consumidor
│       ├── __init__.py
│       ├── main.py
│       ├── models.py
│       ├── messaging/
│       ├── processors/
│       ├── repositories/
│       └── validators/
├── alert-service/              # Servicio de alertas
│   ├── Dockerfile
│   ├── requirements.txt
│   └── weather_alerts/         # Módulos de alertas
│       ├── __init__.py
│       ├── main.py
│       ├── models.py
│       ├── alert_manager.py
│       ├── repositories/
│       └── notifiers/
├── api-service/                # Servicio de API REST
│   ├── Dockerfile
│   ├── requirements.txt
│   └── weather_api/            # Módulos de la API
│       ├── __init__.py
│       ├── main.py
│       ├── models.py
│       ├── dependencies.py
│       └── repositories/
├── database/                   # Scripts de inicialización de la base de datos
│   └── init.sql
└── monitoring/                 # Configuración de monitoreo
    ├── prometheus.yml
    ├── grafana-datasources/
    └── grafana-dashboards/
\`\`\`

## API REST

La API REST proporciona los siguientes endpoints:

- `GET /stations`: Lista todas las estaciones meteorológicas
- `GET /stations/{station_id}`: Obtiene información de una estación específica
- `GET /readings`: Obtiene lecturas meteorológicas con filtros opcionales
- `GET /readings/latest`: Obtiene la última lectura de cada estación
- `GET /alerts`: Obtiene alertas con filtros opcionales
- `GET /alert-configurations`: Obtiene las configuraciones de alertas

## Extensiones Posibles

1. **Autenticación y Autorización**: Implementar JWT o OAuth2 para la API REST
2. **Escalabilidad Horizontal**: Desplegar múltiples instancias de consumidores para manejar mayor carga
3. **Procesamiento Avanzado**: Implementar análisis de datos y predicciones meteorológicas
4. **Notificaciones Multicanal**: Extender el sistema de alertas para enviar notificaciones por email, SMS, etc.

## Licencia

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo LICENSE para más detalles.
