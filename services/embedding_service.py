"""
บริการ Embedding สำหรับ RAG System
ใช้สำหรับแปลงข้อความเป็น Vector เพื่อการค้นหา
"""

import requests
import json
import numpy as np
from typing import List, Optional, Tuple, Dict, Any
import logging
import time
from datetime import datetime
import streamlit as st
from config import config
from database.database import get_db_session
from database.models import Document, DocumentChunk
from sqlalchemy import text

logger = logging.getLogger(__name__)

class EmbeddingService:
    """คลาสจัดการ Embedding"""
    
    def __init__(self):
        self.api_url = config.embedding.api_url
        self.model = config.embedding.model
        self.timeout = config.embedding.timeout
        self.chunk_size = config.embedding.chunk_size
        self.chunk_overlap = config.embedding.chunk_overlap
        
    def create_embedding(self, text: str) -> Optional[List[float]]:
        """สร้าง embedding จากข้อความ"""
        try:
            payload = {
                "model": self.model,
                "prompt": text
            }
            
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                if "embedding" in result:
                    return result["embedding"]
                else:
                    logger.error(f"ไม่พบ embedding ในผลลัพธ์: {result}")
                    return None
            else:
                logger.error(f"API error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("Timeout ในการสร้าง embedding")
            return None
        except Exception as e:
            logger.error(f"เกิดข้อผิดพลาดในการสร้าง embedding: {e}")
            return None
    
    def create_batch_embeddings(self, texts: List[str], 
                              progress_callback=None) -> List[Optional[List[float]]]:
        """สร้าง embedding หลายรายการพร้อมกัน"""
        embeddings = []
        total = len(texts)
        
        for i, text in enumerate(texts):
            if progress_callback:
                progress_callback(i, total, f"Processing chunk {i+1}/{total}")
            
            embedding = self.create_embedding(text)
            embeddings.append(embedding)
            
            # หน่วงเวลาเล็กน้อยเพื่อไม่ให้ API ทำงานหนักเกินไป
            time.sleep(0.1)
        
        return embeddings
    
    def chunk_text(self, text: str, chunk_size: int = None, 
                   overlap: int = None) -> List[str]:
        """แบ่งข้อความเป็นชิ้นเล็กๆ สำหรับ embedding"""
        if chunk_size is None:
            chunk_size = self.chunk_size
        if overlap is None:
            overlap = self.chunk_overlap
            
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # หาจุดตัดที่เหมาะสม (หลัง sentence หรือ paragraph)
            if end < len(text):
                # หาจุดสิ้นสุดประโยค
                for i in range(end, start + overlap, -1):
                    if text[i] in '.!?।':
                        end = i + 1
                        break
                else:
                    # หาช่องว่าง
                    for i in range(end, start + overlap, -1):
                        if text[i].isspace():
                            end = i
                            break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap
            if start >= len(text):
                break
        
        return chunks
    
    def process_document(self, document_id: int) -> bool:
        """ประมวลผลเอกสารเพื่อสร้าง embeddings"""
        try:
            with get_db_session() as session:
                # ดึงเอกสาร
                document = session.query(Document).filter(
                    Document.id == document_id
                ).first()
                
                if not document:
                    logger.error(f"ไม่พบเอกสาร ID: {document_id}")
                    return False
                
                if not document.extracted_text:
                    logger.error(f"เอกสาร {document.filename} ยังไม่มีข้อความที่สกัดแล้ว")
                    return False
                
                # อัพเดทสถานะ
                document.processing_status = "processing"
                session.commit()
                
                # แบ่งข้อความเป็น chunks
                chunks = self.chunk_text(document.extracted_text)
                logger.info(f"แบ่งเอกสาร {document.filename} เป็น {len(chunks)} chunks")
                
                # สร้าง embeddings สำหรับแต่ละ chunk
                successful_chunks = 0
                
                for i, chunk_text in enumerate(chunks):
                    try:
                        # สร้าง embedding
                        embedding = self.create_embedding(chunk_text)
                        
                        if embedding:
                            # บันทึก chunk ลงฐานข้อมูล
                            chunk = DocumentChunk(
                                document_id=document_id,
                                chunk_index=i,
                                content=chunk_text,
                                embedding=embedding,
                                embedding_model=self.model
                            )
                            session.add(chunk)
                            successful_chunks += 1
                        else:
                            logger.warning(f"ไม่สามารถสร้าง embedding สำหรับ chunk {i}")
                            
                    except Exception as e:
                        logger.error(f"ข้อผิดพลาดใน chunk {i}: {e}")
                        continue
                
                # อัพเดทข้อมูลเอกสาร
                document.has_embeddings = successful_chunks > 0
                document.chunks_count = successful_chunks
                document.processing_status = "completed" if successful_chunks > 0 else "failed"
                document.processed_at = datetime.utcnow()
                
                session.commit()
                
                logger.info(f"ประมวลผลเอกสาร {document.filename} เสร็จสิ้น: {successful_chunks}/{len(chunks)} chunks")
                return successful_chunks > 0
                
        except Exception as e:
            logger.error(f"เกิดข้อผิดพลาดในการประมวลผลเอกสาร {document_id}: {e}")
            
            # อัพเดทสถานะเป็น failed
            try:
                with get_db_session() as session:
                    document = session.query(Document).filter(
                        Document.id == document_id
                    ).first()
                    if document:
                        document.processing_status = "failed"
                        session.commit()
            except:
                pass
                
            return False
    
    def search_similar_chunks(self, query: str, limit: int = 5,
                            document_ids: List[int] = None) -> List[Dict[str, Any]]:
        """ค้นหา chunks ที่คล้ายคลึงกับ query"""
        try:
            # สร้าง embedding สำหรับ query
            query_embedding = self.create_embedding(query)
            if not query_embedding:
                logger.error("ไม่สามารถสร้าง embedding สำหรับ query")
                return []
            
            with get_db_session() as session:
                # สร้าง base query
                sql_query = """
                SELECT 
                    dc.id,
                    dc.content,
                    dc.chunk_index,
                    dc.embedding,
                    d.id as document_id,
                    d.filename,
                    d.title,
                    d.category
                FROM document_chunks dc
                JOIN documents d ON dc.document_id = d.id
                WHERE dc.embedding IS NOT NULL
                AND d.is_processed = TRUE
                """
                
                params = {}
                
                # เพิ่มเงื่อนไขถ้ามีการระบุเอกสาร
                if document_ids:
                    placeholders = ','.join([f':doc_id_{i}' for i in range(len(document_ids))])
                    sql_query += f" AND d.id IN ({placeholders})"
                    for i, doc_id in enumerate(document_ids):
                        params[f'doc_id_{i}'] = doc_id
                
                # ดำเนินการ query
                result = session.execute(text(sql_query), params).fetchall()
                
                # คำนวณ cosine similarity
                similarities = []
                for row in result:
                    try:
                        chunk_embedding = json.loads(row.embedding) if isinstance(row.embedding, str) else row.embedding
                        similarity = self.cosine_similarity(query_embedding, chunk_embedding)
                        
                        similarities.append({
                            'chunk_id': row.id,
                            'content': row.content,
                            'chunk_index': row.chunk_index,
                            'document_id': row.document_id,
                            'filename': row.filename,
                            'title': row.title or row.filename,
                            'category': row.category,
                            'similarity': similarity
                        })
                    except Exception as e:
                        logger.warning(f"ไม่สามารถคำนวณ similarity สำหรับ chunk {row.id}: {e}")
                        continue
                
                # เรียงลำดับตาม similarity และคืนผลลัพธ์
                similarities.sort(key=lambda x: x['similarity'], reverse=True)
                return similarities[:limit]
                
        except Exception as e:
            logger.error(f"เกิดข้อผิดพลาดในการค้นหา: {e}")
            return []
    
    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """คำนวณ cosine similarity ระหว่างสอง vector"""
        try:
            v1 = np.array(vec1)
            v2 = np.array(vec2)
            
            dot_product = np.dot(v1, v2)
            norm_v1 = np.linalg.norm(v1)
            norm_v2 = np.linalg.norm(v2)
            
            if norm_v1 == 0 or norm_v2 == 0:
                return 0.0
            
            similarity = dot_product / (norm_v1 * norm_v2)
            return float(similarity)
            
        except Exception as e:
            logger.error(f"เกิดข้อผิดพลาดในการคำนวณ cosine similarity: {e}")
            return 0.0
    
    def get_embeddings_stats(self) -> Dict[str, Any]:
        """ดึงสถิติการใช้งาน embeddings"""
        try:
            with get_db_session() as session:
                stats = {
                    'total_documents': session.query(Document).count(),
                    'processed_documents': session.query(Document).filter(
                        Document.has_embeddings == True
                    ).count(),
                    'total_chunks': session.query(DocumentChunk).count(),
                    'embedding_model': self.model
                }
                
                # สถิติเพิ่มเติม
                pending_docs = session.query(Document).filter(
                    Document.processing_status == 'pending'
                ).count()
                
                failed_docs = session.query(Document).filter(
                    Document.processing_status == 'failed'  
                ).count()
                
                stats.update({
                    'pending_documents': pending_docs,
                    'failed_documents': failed_docs,
                    'success_rate': (stats['processed_documents'] / max(stats['total_documents'], 1)) * 100
                })
                
                return stats
                
        except Exception as e:
            logger.error(f"เกิดข้อผิดพลาดในการดึงสถิติ: {e}")
            return {}

# สร้าง instance หลัก
embedding_service = EmbeddingService()

# Utility functions สำหรับใช้ใน Streamlit
def process_document_embeddings(document_id: int, progress_bar=None):
    """ฟังก์ชันสำหรับประมวลผล embeddings ใน Streamlit"""
    
    def progress_callback(current, total, message):
        if progress_bar:
            progress = current / total
            progress_bar.progress(progress, text=message)
    
    return embedding_service.process_document(document_id)

def search_documents(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """ค้นหาเอกสารที่เกี่ยวข้องกับ query"""
    return embedding_service.search_similar_chunks(query, limit)

@st.cache_data(ttl=300)  # cache เป็นเวลา 5 นาที
def get_embedding_statistics():
    """ดึงสถิติ embeddings สำหรับแสดงใน UI"""
    return embedding_service.get_embeddings_stats()
