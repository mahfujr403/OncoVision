import os
import re
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete
from app.rag.embeddings import EmbeddingService
from app.models.knowledge_embedding import KnowledgeEmbedding

class DocumentIngestionPipeline:
    """Pipeline for ingesting and chunking knowledge documents."""
    
    def __init__(self, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service
        self.chunk_size_tokens = 500  # Approximated by word count in this simplified version
        self.overlap_tokens = 50

    def _approximate_tokens(self, text: str) -> int:
        return len(text.split())

    def _chunk_text(self, text: str) -> list[str]:
        """Split text into chunks, trying by paragraph first, then sentences if needed."""
        paragraphs = re.split(r'\n\s*\n', text)
        chunks = []
        current_chunk = []
        current_length = 0
        
        for p in paragraphs:
            p_len = self._approximate_tokens(p)
            if current_length + p_len > self.chunk_size_tokens and current_chunk:
                chunks.append(" ".join(current_chunk))
                # Add overlap
                overlap = []
                overlap_len = 0
                for item in reversed(current_chunk):
                    item_len = self._approximate_tokens(item)
                    if overlap_len + item_len <= self.overlap_tokens:
                        overlap.insert(0, item)
                        overlap_len += item_len
                    else:
                        break
                current_chunk = overlap
                current_length = overlap_len
                
            if p_len > self.chunk_size_tokens:
                # If a single paragraph is too large, split by sentences
                sentences = re.split(r'(?<=[.!?]) +', p)
                for s in sentences:
                    s_len = self._approximate_tokens(s)
                    if current_length + s_len > self.chunk_size_tokens and current_chunk:
                        chunks.append(" ".join(current_chunk))
                        current_chunk = []
                        current_length = 0
                    current_chunk.append(s)
                    current_length += s_len
            else:
                current_chunk.append(p)
                current_length += p_len
                
        if current_chunk:
            chunks.append(" ".join(current_chunk))
            
        return [c.strip() for c in chunks if c.strip()]

    async def ingest_document(self, file_path: Path, session: AsyncSession):
        """Read a single file, chunk it, embed, and store."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Failed to read {file_path}: {e}")
            return

        topic = file_path.parent.name
        source_str = str(file_path.relative_to(file_path.parents[2])) # Rel to knowledge_base
        
        chunks = self._chunk_text(content)
        if not chunks:
            return
            
        embeddings = await self.embedding_service.get_embeddings(chunks)
        
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            record = KnowledgeEmbedding(
                content=chunk,
                source=source_str,
                topic=topic,
                chunk_index=i,
                embedding=embedding
            )
            session.add(record)
            
        await session.commit()

    async def ingest_directory(self, directory: Path, session: AsyncSession):
        """Read all .md and .txt files recursively."""
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith('.md') or file.endswith('.txt'):
                    file_path = Path(root) / file
                    await self.ingest_document(file_path, session)

    async def clear_and_reingest(self, directory: Path, session: AsyncSession):
        """Drop existing embeddings and reingest the directory."""
        await session.execute(delete(KnowledgeEmbedding))
        await session.commit()
        await self.ingest_directory(directory, session)
