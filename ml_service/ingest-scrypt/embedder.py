import os
import json
import gc
import torch
import pandas as pd
from PIL import Image
from transformers import SiglipImageProcessor, AutoModel
from tqdm import tqdm

# Пути
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))

CSV_PATH = os.path.join(PROJECT_ROOT, "postgres_data", "strapi_output0709.csv")
IMAGES_DIR = os.path.join(PROJECT_ROOT, "postgres_data", "images")
OUTPUT_JSON = os.path.join(BASE_DIR, "embeddings_cache.json")

# Лимит для теста (оставь 50, чтобы проверить на железе)
MAX_IMAGES = 50 

if torch.backends.mps.is_available():
    DEVICE = "mps"
elif torch.cuda.is_available():
    DEVICE = "cuda"
else:
    DEVICE = "cpu"

print(f"🚀 Используем устройство для ML: {DEVICE}")

def generate_embeddings():
    if not os.path.exists(CSV_PATH) or not os.path.exists(IMAGES_DIR):
        print("❌ Ошибка путей!")
        return

    df = pd.read_csv(CSV_PATH)
    if MAX_IMAGES:
        df = df.head(MAX_IMAGES)
        print(f"🧪 Тестовый режим: обрабатываем первые {MAX_IMAGES} строк")
    
    photo_column = "Название фото"
    if photo_column not in df.columns:
        print(f"⚠️ Колонка '{photo_column}' не найдена!")
        return

    # Индекс файлов на диске
    disk_images = {}
    for filename in os.listdir(IMAGES_DIR):
        if filename.lower().endswith(('.webp', '.png', '.jpg', '.jpeg')):
            full_p = os.path.join(IMAGES_DIR, filename)
            disk_images[filename.lower()] = full_p
            disk_images[os.path.splitext(filename)[0].lower()] = full_p

    print(f"📁 Найдено картинок на диске: {len(disk_images)}")

    model_id = "google/siglip-so400m-patch14-384"
    print(f"🔄 Загружаю модель {model_id}...")
    processor = SiglipImageProcessor.from_pretrained(model_id)
    model = AutoModel.from_pretrained(model_id).to(DEVICE)
    model.eval()

    embeddings = []
    matched_count = 0
    
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Генерация эмбеддингов"):
        image_name = row.get(photo_column)
        if pd.isna(image_name):
            continue
            
        clean_name = str(image_name).strip()
        base_name = os.path.splitext(os.path.basename(clean_name))[0].lower()
        
        image_path = disk_images.get(clean_name.lower()) or disk_images.get(base_name)
        if not image_path:
            continue
            
        matched_count += 1
        try:
            image = Image.open(image_path).convert("RGB")
            inputs = processor(images=image, return_tensors="pt").to(DEVICE)
            
            with torch.no_grad():
                image_features = model.get_image_features(**inputs)
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                vector = image_features.cpu().numpy().tolist()[0]
                
            embeddings.append({
                "id": int(idx),
                "wine_name": str(row.get("Название вина", "Unknown")),
                "image_file": os.path.basename(image_path),
                "vector": vector
            })
            
        except Exception as e:
            print(f"⚠️ Ошибка: {e}")
        
        # Жёстко очищаем память после каждой итерации, чтобы ноут не зависал
        if DEVICE == "mps":
            torch.mps.empty_cache()
        gc.collect()
            
    print(f"\n🔗 Сопоставлено файлов с диском: {matched_count}")
    print(f"✅ Успешно сгенерировано эмбеддингов: {len(embeddings)}")
    
    if embeddings:
        with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
            json.dump(embeddings, f, ensure_ascii=False, indent=2)
        print(f"💾 Эмбеддинги сохранены в файл: {OUTPUT_JSON}")

if __name__ == "__main__":
    generate_embeddings()