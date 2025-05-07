
"""
Main module for the Weather Data Consumer service
"""
import logging
import sys

from prometheus_client import start_http_server

from weather_consumer.messaging.rabbitmq_consumer import RabbitMQConsumer
from weather_consumer.processors.weather_data_processor import WeatherDataProcessor
from weather_consumer.repositories.postgres_repository import PostgresRepository
from weather_consumer.validators.validator_factory import ValidatorFactory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("weather-consumer")


def main():
    """Main function to run the weather data consumer"""
    # Start Prometheus metrics server
    start_http_server(8001)
    logger.info("Prometheus metrics server started on port 8001")
    
    # Create repository
    repository = PostgresRepository()
    
    # Create validator factory
    validator_factory = ValidatorFactory()
    
    # Create processor
    processor = WeatherDataProcessor(repository, validator_factory)
    
    # Create and run consumer
    consumer = RabbitMQConsumer(processor)
    try:
        consumer.run()
    finally:
        consumer.close()
        repository.close()


if __name__ == "__main__":
    main()
