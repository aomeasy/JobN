"""
การจัดการการเชื่อมต่อฐานข้อมูล TiDB
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import streamlit as st
from contextlib import contextmanager
import logging
from typing import Generator, Optional
from config import config
from .models import Base

# ตั้งค่า logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """คลาสจัดการฐานข้อมูล"""
    
    def __init__(self):
        self._engine = None
        self._session_factory = None
        
    @property
    def engine(self):
        """สร้างและส่งคืน database engine"""
        if self._engine is None:
            self._engine = create_engine(
                config.db.url,
                pool_size=config.db.pool_size,
                max_overflow=config.db.max_overflow,
                pool_timeout=config.db.pool_timeout,
                pool_pre_ping=True,  # ตรวจสอบการเชื่อมต่อก่อนใช้งาน
                echo=False,  # เปลี่ยนเป็น True เพื่อดู SQL queries
                poolclass=StaticPool,
                connect_args={
                    "charset": "utf8mb4",
                    "connect_timeout": 60,
                    "read_timeout": 60,
                    "write_timeout": 60,
                }
            )
        return self._engine
    
    @property
    def session_factory(self):
        """สร้างและส่งคืน session factory"""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False
            )
        return self._session_factory
    
    def create_tables(self):
        """สร้างตารางทั้งหมด"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("✅ สร้างตารางฐานข้อมูลเรียบร้อย")
            return True
        except Exception as e:
            logger.error(f"❌ ไม่สามารถสร้างตารางได้: {e}")
            return False
    
    def test_connection(self) -> bool:
        """ทดสอบการเชื่อมต่อฐานข้อมูล"""
        try:
            with self.get_session() as session:
                result = session.execute(text("SELECT 1"))
                result.fetchone()
                logger.info("✅ เชื่อมต่อฐานข้อมูลสำเร็จ")
                return True
        except Exception as e:
            logger.error(f"❌ ไม่สามารถเชื่อมต่อฐานข้อมูลได้: {e}")
            return False
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Context manager สำหรับจัดการ database session"""
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()
    
    def get_session_sync(self) -> Session:
        """ได้ session แบบ synchronous (ใช้เมื่อไม่สามารถใช้ context manager ได้)"""
        return self.session_factory()
    
    def close_all_sessions(self):
        """ปิด session ทั้งหมด"""
        if self._engine:
            self._engine.dispose()
        self._engine = None
        self._session_factory = None

# สร้าง instance หลัก
db_manager = DatabaseManager()

# Utility functions สำหรับใช้งานใน Streamlit
def get_db_session():
    """ฟังก์ชันสำหรับใช้ใน Streamlit"""
    return db_manager.get_session()

def test_connection() -> bool:
    """ทดสอบการเชื่อมต่อ"""
    return db_manager.test_connection()

def init_database():
    """เริ่มต้นฐานข้อมูล (สร้างตารางถ้ายังไม่มี)"""
    return db_manager.create_tables()

@st.cache_resource
def get_database_info():
    """ดึงข้อมูลฐานข้อมูลสำหรับแสดงใน UI"""
    try:
        with db_manager.get_session() as session:
            # นับจำนวนเอกสาร
            doc_count = session.execute(
                text("SELECT COUNT(*) FROM documents")
            ).scalar() or 0
            
            # นับจำนวนผู้ใช้
            user_count = session.execute(
                text("SELECT COUNT(*) FROM users WHERE is_active = 1")
            ).scalar() or 0
            
            # นับจำนวนการสนทนา
            chat_count = session.execute(
                text("SELECT COUNT(*) FROM chat_sessions WHERE is_active = 1")
            ).scalar() or 0
            
            # นับจำนวนงาน OCR
            ocr_count = session.execute(
                text("SELECT COUNT(*) FROM ocr_tasks WHERE status = 'completed'")
            ).scalar() or 0
            
            return {
                "documents": doc_count,
                "users": user_count,
                "chats": chat_count,
                "ocr_tasks": ocr_count,
                "status": "connected"
            }
    except Exception as e:
        logger.error(f"ไม่สามารถดึงข้อมูลฐานข้อมูลได้: {e}")
        return {
            "documents": 0,
            "users": 0,
            "chats": 0,
            "ocr_tasks": 0,
            "status": "error"
        }

# การตั้งค่าการเชื่อมต่อสำหรับ Streamlit
def setup_database_connection():
    """ตั้งค่าการเชื่อมต่อฐานข้อมูลใน Streamlit"""
    if "db_initialized" not in st.session_state:
        try:
            # ทดสอบการเชื่อมต่อ
            if test_connection():
                # สร้างตารางถ้ายังไม่มี
                if init_database():
                    st.session_state.db_initialized = True
                    st.session_state.db_status = "✅ พร้อมใช้งาน"
                else:
                    st.session_state.db_status = "⚠️ ไม่สามารถสร้างตารางได้"
            else:
                st.session_state.db_status = "❌ ไม่สามารถเชื่อมต่อได้"
        except Exception as e:
            st.session_state.db_status = f"❌ เกิดข้อผิดพลาด: {str(e)}"
            logger.error(f"Database setup error: {e}")

# Migration functions (สำหรับการปรับปรุงฐานข้อมูลในอนาคต)
def run_migrations():
    """รันการปรับปรุงฐานข้อมูล"""
    try:
        with db_manager.get_session() as session:
            # ตรวจสอบว่ามีตาราง migrations หรือไม่
            result = session.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = DATABASE() AND table_name = 'migrations'
            """)).scalar()
            
            if result == 0:
                # สร้างตาราง migrations
                session.execute(text("""
                    CREATE TABLE migrations (
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        version VARCHAR(50) NOT NULL UNIQUE,
                        description TEXT,
                        executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_version (version)
                    )
                """))
                session.commit()
                logger.info("สร้างตาราง migrations เรียบร้อย")
            
            return True
    except Exception as e:
        logger.error(f"ไม่สามารถรัน migrations ได้: {e}")
        return False

# Health check function
def health_check():
    """ตรวจสอบสุขภาพของฐานข้อมูล"""
    try:
        with db_manager.get_session() as session:
            # ทดสอบ query พื้นฐาน
            session.execute(text("SELECT 1")).fetchone()
            
            # ตรวจสอบ connection pool
            pool = db_manager.engine.pool
            pool_status = {
                "size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "invalid": pool.invalid()
            }
            
            return {
                "status": "healthy",
                "pool": pool_status,
                "timestamp": "timestamp"
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": "timestamp"
        }

# Cleanup function
def cleanup_database():
    """ทำความสะอาดฐานข้อมูล"""
    try:
        db_manager.close_all_sessions()
        logger.info("ปิดการเชื่อมต่อฐานข้อมูลเรียบร้อย")
        return True
    except Exception as e:
        logger.error(f"ไม่สามารถปิดการเชื่อมต่อได้: {e}")
        return False

# เมื่อปิดแอปพลิเคชัน
import atexit
atexit.register(cleanup_database)
