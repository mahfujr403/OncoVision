import asyncio
import os
import sys

# Add the backend directory to Python path so 'app' can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.settings import get_settings
from app.database.session import get_db
from app.llm.client import get_gemini_client
from app.rag.embeddings import EmbeddingService
from app.rag.ingestion import DocumentIngestionPipeline

async def main():
    settings = get_settings()
    
    if not settings.GOOGLE_API_KEY:
        print("❌ Error: GOOGLE_API_KEY is not set in .env")
        sys.exit(1)
        
    print("🚀 Initializing Gemini LLM Client...")
    llm_client = get_gemini_client(settings.GOOGLE_API_KEY, settings.LLM_MODEL)
    
    print("🧠 Initializing Embedding Service...")
    embedding_service = EmbeddingService(llm_client)
    
    knowledge_base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "rag", "knowledge_base")
    
    if not os.path.exists(knowledge_base_dir):
        print(f"❌ Error: Knowledge base directory not found at {knowledge_base_dir}")
        sys.exit(1)

    print("📚 Starting Document Ingestion Pipeline...")
    # Using the existing get_db generator
    async for db_session in get_db():
        pipeline = DocumentIngestionPipeline(embedding_service)
        try:
            from pathlib import Path
            from sqlalchemy import delete
            from app.models.knowledge_embedding import KnowledgeEmbedding

            print("🧹 Clearing previous embeddings from database...")
            await db_session.execute(delete(KnowledgeEmbedding))
            await db_session.commit()

            print(f"📂 Reading Markdown files from: {knowledge_base_dir}")
            dir_path = Path(knowledge_base_dir)
            await pipeline.ingest_directory(dir_path, db_session)
            
            print("\n✅ Ingestion Completed Successfully with 768-dim normalized embeddings!")
        except Exception as e:
            print(f"\n❌ Error during ingestion: {str(e)}")
        finally:
            break # Only need one session

if __name__ == "__main__":
    asyncio.run(main())
