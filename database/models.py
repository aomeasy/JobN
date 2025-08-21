"""
โมเดลฐานข้อมูลสำหรับระบบ JobN Power
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

class User(Base):
    """โมเดลผู้ใช้งาน"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    department = Column(String(100), nullable=True)
    role = Column(String(50), default="user")  # user, admin, super_admin
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # ความสัมพันธ์
    documents = relationship("Document", back_populates="uploaded_by_user")
    chat_sessions = relationship("ChatSession", back_populates="user")
    ocr_tasks = relationship("OCRTask", back_populates="user")

class Document(Base):
    """โมเดลเอกสาร"""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String(36), unique=True, default=lambda: str(uuid.uuid4()), index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)  # ขนาดไฟล์ในไบต์
    file_type = Column(String(50), nullable=False)  # pdf, docx, xlsx, etc.
    mime_type = Column(String(100), nullable=False)
    
    # เมตาดาต้า
    title = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    tags = Column(JSON, nullable=True)  # เก็บเป็น array ของ tags
    
    # การประมวลผล
    is_processed = Column(Boolean, default=False)
    processing_status = Column(String(50), default="pending")  # pending, processing, completed, failed
    extracted_text = Column(Text, nullable=True)
    
    # Embedding
    has_embeddings = Column(Boolean, default=False)
    embedding_model = Column(String(100), nullable=True)
    chunks_count = Column(Integer, default=0)
    
    # ข้อมูลผู้ใช้
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_public = Column(Boolean, default=False)
    access_count = Column(Integer, default=0)
    
    # เวลา
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    
    # ความสัมพันธ์
    uploaded_by_user = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    chat_contexts = relationship("ChatContext", back_populates="document")

class DocumentChunk(Base):
    """โมเดลชิ้นส่วนเอกสาร (สำหรับ RAG)"""
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)  # ลำดับของ chunk ในเอกสาร
    
    # เนื้อหา
    content = Column(Text, nullable=False)
    content_type = Column(String(50), default="text")  # text, table, image
    
    # Embedding
    embedding = Column(JSON, nullable=True)  # เก็บ vector embedding
    embedding_model = Column(String(100), nullable=True)
    
    # ตำแหน่งในเอกสาร
    page_number = Column(Integer, nullable=True)
    start_char = Column(Integer, nullable=True)
    end_char = Column(Integer, nullable=True)
    
    # เมตาดาต้า
    metadata = Column(JSON, nullable=True)  # เก็บข้อมูลเพิ่มเติม
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # ความสัมพันธ์
    document = relationship("Document", back_populates="chunks")

class ChatSession(Base):
    """โมเดลเซสชันการสนทนา"""
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String(36), unique=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # ข้อมูลเซสชัน
    title = Column(String(200), nullable=True)  # หัวข้อการสนทนา
    system_prompt = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # สถิติ
    message_count = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    
    # ความสัมพันธ์
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    """โมเดลข้อความในการสนทนา"""
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    
    # ข้อความ
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    
    # เมตาดาต้า
    model_used = Column(String(100), nullable=True)
    tokens_used = Column(Integer, nullable=True)
    response_time = Column(Float, nullable=True)  # เวลาในการตอบ (วินาที)
    
    # RAG Context
    context_documents = Column(JSON, nullable=True)  # เอกสารที่ใช้อ้างอิง
    similarity_scores = Column(JSON, nullable=True)  # คะแนนความเหมือน
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # ความสัมพันธ์
    session = relationship("ChatSession", back_populates="messages")

class ChatContext(Base):
    """โมเดลบริบทที่ใช้ในการตอบ (สำหรับ RAG)"""
    __tablename__ = "chat_contexts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, ForeignKey("chat_messages.id"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    chunk_id = Column(Integer, ForeignKey("document_chunks.id"), nullable=True)
    
    # ข้อมูลการใช้งาน
    similarity_score = Column(Float, nullable=False)  # คะแนนความเหมือน 0-1
    rank = Column(Integer, nullable=False)  # ลำดับความสำคัญ
    used_in_response = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # ความสัมพันธ์
    document = relationship("Document", back_populates="chat_contexts")

class OCRTask(Base):
    """โมเดลงาน OCR"""
    __tablename__ = "ocr_tasks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String(36), unique=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # ไฟล์อินพุต
    input_filename = Column(String(255), nullable=False)
    input_file_path = Column(String(500), nullable=False)
    input_file_type = Column(String(50), nullable=False)
    
    # การประมวลผล
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    model_used = Column(String(100), nullable=True)
    processing_time = Column(Float, nullable=True)  # เวลาในการประมวลผล (วินาที)
    
    # ผลลัพธ์
    extracted_text = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=True)  # ความมั่นใจในผลลัพธ์ 0-1
    
    # เมตาดาต้า
    metadata = Column(JSON, nullable=True)  # เก็บข้อมูลเพิ่มเติม
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # ความสัมพันธ์
    user = relationship("User", back_populates="ocr_tasks")

class SystemConfig(Base):
    """โมเดลการตั้งค่าระบบ"""
    __tablename__ = "system_configs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    value_type = Column(String(20), default="string")  # string, int, float, bool, json
    description = Column(Text, nullable=True)
    is_encrypted = Column(Boolean, default=False)
    is_public = Column(Boolean, default=False)  # สามารถแสดงให้ผู้ใช้ทั่วไปเห็นได้
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(String(100), nullable=True)

class AuditLog(Base):
    """โมเดลบันทึกการใช้งาน"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # การกระทำ
    action = Column(String(100), nullable=False)  # upload, chat, ocr, download, etc.
    resource_type = Column(String(50), nullable=True)  # document, message, task
    resource_id = Column(String(100), nullable=True)
    
    # รายละเอียด
    description = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)  # รองรับ IPv6
    user_agent = Column(String(500), nullable=True)
    
    # เมตาดาต้า
    metadata = Column(JSON, nullable=True)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
