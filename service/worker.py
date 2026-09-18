import asyncio
import json
import logging
import aio_pika

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RABBITMQ_URL = "amqp://guest:guest@localhost/"

async def process_wine_task(message: aio_pika.abc.AbstractIncomingMessage):
    """
    Функция обработки задачи, когда она поступает из очереди
    """
    async with message.process():
        data = json.loads(message.body.decode())
        label_id = data.get("label_id")
        image_url = data.get("image_url")
        
        logger.info(f"получена задача для обработки: label_id={label_id}, image_url={image_url}")
        
        # --- ЗДЕСЬ В БУДУЩЕМ БУДЕТ ML-КОМПОНЕНТ ---
        # 1. Скачиваем/загружаем картинку
        # 2. Прогоняем через SigLIP 2 для получения эмбеддинга
        # 3. Делаем поиск в pgvector
        # 4. Обрабатываем через VLM / RapidFuzz
        # ------------------------------------------
        
        # Имитируем бурную ML-деятельность (например, поиск по базе)
        await asyncio.sleep(2)
        
        logger.info(f"✅ Задача {label_id} успешно обработана!")

async def main():
    # Подключаемся к RabbitMQ
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    
    async with connection:
        # Открываем канал
        channel = await connection.channel()
        # Устанавливаем QoS (сколько задач воркер может брать одновременно)
        await channel.set_qos(prefetch_count=1)
        
        # Объявляем ту же очередь, куда шлет FastAPI
        queue = await channel.declare_queue("wine_tasks", durable=True)
        
        logger.info("⚙️ ML-воркер запущен и ждет задачи из RabbitMQ...")
        
        # Начинаем слушать очередь
        await queue.consume(process_wine_task)
        
        # Держим воркер запущенным
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Воркер остановлен пользователем.")