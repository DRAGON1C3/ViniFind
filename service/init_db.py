import asyncio
import asyncpg
from pgvector.asyncpg import register_vector

DATABASE_URL = "postgresql://vinifind_user:vinifind_password@localhost:5432/vinifind"

async def init_db():
    # Подключаемся к базе данных
    conn = await asyncpg.connect(DATABASE_URL)
    
    # Включаем расширение pgvector (обязательно!)
    await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    await register_vector(conn)
    
    # Создаем таблицу для вин и их векторных эмбеддингов
    # Размерность эмбеддингов SigLIP 2 обычно составляет 768 или 1152 (зависит от версии модели)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS wines (
            id SERIAL PRIMARY KEY,
            name TEXT,
            vintage_year INTEGER,
            category TEXT,
            image_name TEXT,
            embedding VECTOR(768) 
        );
    """)
    
    print("✅ База данных успешно инициализирована, расширение pgvector и таблица созданы!")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(init_db())