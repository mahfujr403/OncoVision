import asyncio
import os
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Ensure .env is read from backend/.env if not in environment
from dotenv import load_dotenv
env_path = os.path.join(backend_dir, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)

from app.core.settings import get_settings
from app.database.session import get_db
from app.llm.client import get_gemini_client
from app.rag.embeddings import EmbeddingService
from app.rag.ingestion import DocumentIngestionPipeline
from app.models.knowledge_embedding import KnowledgeEmbedding
from sqlalchemy import select, func, delete

async def main():
    settings = get_settings()
    
    if not settings.GOOGLE_API_KEY:
        print("[ERROR] GOOGLE_API_KEY is not set in environment or .env")
        sys.exit(1)
        
    print("[INFO] Initializing Gemini LLM Client...")
    llm_client = get_gemini_client(settings.GOOGLE_API_KEY, settings.LLM_MODEL)
    
    print("[INFO] Initializing Embedding Service (768-dim)...")
    embedding_service = EmbeddingService(llm_client)
    
    knowledge_base_dir = os.path.join(backend_dir, "app", "rag", "knowledge_base")
    
    if not os.path.exists(knowledge_base_dir):
        print(f"[ERROR] Knowledge base directory not found at {knowledge_base_dir}")
        sys.exit(1)

    print(f"[INFO] Reading Knowledge Base from: {knowledge_base_dir}")
    async for db_session in get_db():
        pipeline = DocumentIngestionPipeline(embedding_service)
        try:
            print("[INFO] Clearing previous embeddings from database...")
            await db_session.execute(delete(KnowledgeEmbedding))
            await db_session.commit()

            print("[INFO] Ingesting documents...")
            dir_path = Path(knowledge_base_dir)
            await pipeline.ingest_directory(dir_path, db_session)
            
            total_records = await db_session.scalar(select(func.count(KnowledgeEmbedding.id)))
            print(f"\n[SUCCESS] Ingestion Completed! Total embeddings in database: {total_records}")
            
            topics = (await db_session.execute(select(KnowledgeEmbedding.topic).distinct())).scalars().all()
            print(f"[INFO] Ingested topics ({len(topics)}): {', '.join(topics)}")
        except Exception as e:
            print(f"\n[ERROR] Ingestion failed: {e}")
            await db_session.rollback()
        finally:
            break

if __name__ == "__main__":
    asyncio.run(main())
