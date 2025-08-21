"""
บริการ Chatbot สำหรับ RAG System
รวม AI Chat และการค้นหาเอกสาร
"""

import requests
import json
import time
from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime
import streamlit as st
from config import config
from database.database import get_db_session
from database.models import ChatSession, ChatMessage, ChatContext, User
from services.embedding_service import embedding_service

logger = logging.getLogger(__name__)

class ChatService:
    """คลาสจัดการ Chatbot และ RAG"""
    
    def __init__(self):
        self.api_url = config.chat.api_url
        self.model = config.chat.model
        self.timeout = config.chat.timeout
        self.max_tokens = config.chat.max_tokens
        self.temperature = config.chat.temperature
        
    def create_chat_session(self, user_id: int, title: str = None, 
                          system_prompt: str = None) -> Optional[int]:
        """สร้าง session การสนทนาใหม่"""
        try:
            with get_db_session() as session:
                chat_session = ChatSession(
                    user_id=user_id,
                    title=title or f"การสนทนา {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    system_prompt=system_prompt or config.get_system_prompt()
                )
                
                session.add(chat_session)
                session.commit()
                session.refresh(chat_session)
                
                logger.info(f"สร้าง chat session ใหม่: {chat_session.id}")
                return chat_session.id
                
        except Exception as e:
            logger.error(f"ไม่สามารถสร้าง chat session ได้: {e}")
            return None
    
    def send_message(self, session_id: int, message: str, 
                    use_rag: bool = True, rag_limit: int = 3) -> Optional[Dict[str, Any]]:
        """ส่งข้อความและรับคำตอบจาก AI"""
        start_time = time.time()
        
        try:
            with get_db_session() as session:
                # ดึง chat session
                chat_session = session.query(ChatSession).filter(
                    ChatSession.id == session_id
                ).first()
                
                if not chat_session:
                    logger.error(f"ไม่พบ chat session: {session_id}")
                    return None
                
                # บันทึกข้อความของผู้ใช้
                user_message = ChatMessage(
                    session_id=session_id,
                    role="user",
                    content=message
                )
                session.add(user_message)
                session.commit()
                session.refresh(user_message)
                
                # ค้นหาเอกสารที่เกี่ยวข้องถ้าใช้ RAG
                context_docs = []
                context_text = ""
                
                if use_rag:
                    context_docs = embedding_service.search_similar_chunks(
                        message, limit=rag_limit
                    )
                    
                    if context_docs:
                        context_text = "\n\nบริบทจากเอกสาร:\n"
                        for i, doc in enumerate(context_docs, 1):
                            context_text += f"\n{i}. จากเอกสาร '{doc['title']}':\n{doc['content'][:500]}...\n"
                
                # สร้าง prompt สำหรับ AI
                system_prompt = chat_session.system_prompt or config.get_system_prompt()
                full_prompt = f"{system_prompt}\n\nคำถาม: {message}{context_text}"
                
                # เรียก AI API
                ai_response = self._call_ai_api(full_prompt)
                
                if ai_response:
                    response_time = time.time() - start_time
                    
                    # บันทึกคำตอบของ AI
                    ai_message = ChatMessage(
                        session_id=session_id,
                        role="assistant",
                        content=ai_response["content"],
                        model_used=self.model,
                        tokens_used=ai_response.get("tokens", 0),
                        response_time=response_time,
                        context_documents=[doc["document_id"] for doc in context_docs] if context_docs else None,
                        similarity_scores=[doc["similarity"] for doc in context_docs] if context_docs else None
                    )
                    session.add(ai_message)
                    
                    # บันทึกบริบทที่ใช้
                    for rank, doc in enumerate(context_docs):
                        context = ChatContext(
                            message_id=ai_message.id,
                            document_id=doc["document_id"],
                            chunk_id=doc["chunk_id"],
                            similarity_score=doc["similarity"],
                            rank=rank
                        )
                        session.add(context)
                    
                    # อัพเดท session stats
                    chat_session.message_count += 2  # user + assistant
                    chat_session.total_tokens += ai_response.get("tokens", 0)
                    chat_session.last_activity = datetime.utcnow()
                    
                    session.commit()
                    
                    # ส่งคืนผลลัพธ์
                    return {
                        "response": ai_response["content"],
                        "context_documents": context_docs,
                        "response_time": response_time,
                        "tokens_used": ai_response.get("tokens", 0),
                        "message_id": ai_message.id
                    }
                else:
                    logger.error("ไม่ได้รับคำตอบจาก AI")
                    return None
                    
        except Exception as e:
            logger.error(f"เกิดข้อผิดพลาดในการส่งข้อความ: {e}")
            return None
    
    def _call_ai_api(self, prompt: str) -> Optional[Dict[str, Any]]:
        """เรียก AI API"""
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens
                }
            }
            
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "content": result.get("response", ""),
                    "tokens": result.get("eval_count", 0) + result.get("prompt_eval_count", 0)
                }
            else:
                logger.error(f"AI API error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("Timeout ในการเรียก AI API")
            return None
        except Exception as e:
            logger.error(f"เกิดข้อผิดพลาดในการเรียก AI API: {e}")
            return None
    
    def get_chat_history(self, session_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """ดึงประวัติการสนทนา"""
        try:
            with get_db_session() as session:
                messages = session.query(ChatMessage).filter(
                    ChatMessage.session_id == session_id
                ).order_by(ChatMessage.created_at.desc()).limit(limit).all()
                
                history = []
                for msg in reversed(messages):  # เรียงใหม่เพื่อให้เป็นลำดับเวลา
                    history.append({
                        "id": msg.id,
                        "role": msg.role,
                        "content": msg.content,
                        "created_at": msg.created_at,
                        "model_used": msg.model_used,
                        "tokens_used": msg.tokens_used,
                        "response_time": msg.response_time,
                        "context_documents": msg.context_documents,
                        "similarity_scores": msg.similarity_scores
                    })
                
                return history
                
        except Exception as e:
            logger.error(f"เกิดข้อผิดพลาดในการดึงประวัติ: {e}")
            return []
    
    def get_user_sessions(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """ดึงรายการ session ของผู้ใช้"""
        try:
            with get_db_session() as session:
                sessions = session.query(ChatSession).filter(
                    ChatSession.user_id == user_id,
                    ChatSession.is_active == True
                ).order_by(ChatSession.last_activity.desc()).limit(limit).all()
                
                session_list = []
                for chat_session in sessions:
                    session_list.append({
                        "id": chat_session.id,
                        "uuid": chat_session.uuid,
                        "title": chat_session.title,
                        "message_count": chat_session.message_count,
                        "created_at": chat_session.created_at,
                        "last_activity": chat_session.last_activity,
                        "total_tokens": chat_session.total_tokens
                    })
                
                return session_list
                
        except Exception as e:
            logger.error(f"เกิดข้อผิดพลาดในการดึงรายการ session: {e}")
            return []
    
    def delete_session(self, session_id: int, user_id: int) -> bool:
        """ลบ session (soft delete)"""
        try:
            with get_db_session() as session:
                chat_session = session.query(ChatSession).filter(
                    ChatSession.id == session_id,
                    ChatSession.user_id == user_id
                ).first()
                
                if chat_session:
                    chat_session.is_active = False
                    session.commit()
                    logger.info(f"ลบ chat session {session_id}")
                    return True
                else:
                    logger.warning(f"ไม่พบ chat session {session_id} สำหรับผู้ใช้ {user_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"เกิดข้อผิดพลาดในการลบ session: {e}")
            return False
    
    def update_session_title(self, session_id: int, user_id: int, title: str) -> bool:
        """อัพเดทชื่อ session"""
        try:
            with get_db_session() as session:
                chat_session = session.query(ChatSession).filter(
                    ChatSession.id == session_id,
                    ChatSession.user_id == user_id
                ).first()
                
                if chat_session:
                    chat_session.title = title
                    session.commit()
                    return True
                else:
                    return False
                    
        except Exception as e:
            logger.error(f"เกิดข้อผิดพลาดในการอัพเดทชื่อ session: {e}")
            return False
    
    def get_chat_statistics(self, user_id: int = None) -> Dict[str, Any]:
        """ดึงสถิติการใช้งาน chat"""
        try:
            with get_db_session() as session:
                base_query = session.query(ChatSession)
                message_query = session.query(ChatMessage)
                
                if user_id:
                    base_query = base_query.filter(ChatSession.user_id == user_id)
                    message_query = message_query.join(ChatSession).filter(
                        ChatSession.user_id == user_id
                    )
                
                stats = {
                    "total_sessions": base_query.count(),
                    "active_sessions": base_query.filter(ChatSession.is_active == True).count(),
                    "total_messages": message_query.count(),
                    "total_tokens": session.execute(
                        "SELECT COALESCE(SUM(total_tokens), 0) FROM chat_sessions" + 
                        (f" WHERE user_id = {user_id}" if user_id else "")
                    ).scalar() or 0
                }
                
                # สถิติเพิ่มเติม
                avg_messages = session.execute(
                    "SELECT AVG(message_count) FROM chat_sessions WHERE is_active = TRUE" +
                    (f" AND user_id = {user_id}" if user_id else "")
                ).scalar() or 0
                
                stats["avg_messages_per_session"] = round(float(avg_messages), 2)
                
                return stats
                
        except Exception as e:
            logger.error(f"เกิดข้อผิดพลาดในการดึงสถิติ: {e}")
            return {}

# สร้าง instance หลัก
chat_service = ChatService()

# Utility functions สำหรับใช้ใน Streamlit
def get_or_create_session(user_id: int = 1) -> int:
    """ดึงหรือสร้าง session สำหรับผู้ใช้"""
    if "chat_session_id" not in st.session_state:
        session_id = chat_service.create_chat_session(
            user_id=user_id,
            system_prompt=config.get_system_prompt()
        )
        st.session_state.chat_session_id = session_id
    
    return st.session_state.chat_session_id

def send_chat_message(message: str, use_rag: bool = True) -> Optional[Dict[str, Any]]:
    """ส่งข้อความใน Streamlit"""
    session_id = get_or_create_session()
    if session_id:
        return chat_service.send_message(session_id, message, use_rag)
    return None

@st.cache_data(ttl=60)  # cache เป็นเวลา 1 นาที
def get_chat_statistics_cached(user_id: int = None):
    """ดึงสถิติ chat สำหรับแสดงใน UI"""
    return chat_service.get_chat_statistics(user_id)
