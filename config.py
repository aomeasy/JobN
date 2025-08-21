"""
การตั้งค่าระบบ JobN Power by AI NT North
"""
import os
from dataclasses import dataclass
from typing import Optional
import streamlit as st

@dataclass
class DatabaseConfig:
    """การตั้งค่าฐานข้อมูล"""
    url: str = "mysql+pymysql://2wGpw4Qa2maXMEz.root:FMDCS56nmOL9KSWg@gateway01.ap-southeast-1.prod.aws.tidbcloud.com:4000/ntdatabase?ssl_verify_cert=false"
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30

@dataclass
class EmbeddingConfig:
    """การตั้งค่า Embedding API"""
    api_url: str = "http://209.15.123.47:11434/api/embeddings"
    model: str = "nomic-embed-text:latest"
    timeout: int = 60
    chunk_size: int = 512
    chunk_overlap: int = 50

@dataclass
class ChatConfig:
    """การตั้งค่า Chat API"""
    api_url: str = "http://209.15.123.47:11434/api/generate"
    model: str = "Qwen3:14b"
    timeout: int = 120
    max_tokens: int = 4000
    temperature: float = 0.3

@dataclass
class OCRConfig:
    """การตั้งค่า OCR"""
    typhoon_model: str = "scb10x/llama3.1-typhoon2-8b-instruct:latest"
    ocr_model: str = "scb10x/typhoon-ocr-7b:latest"
    api_url: str = "http://209.15.123.47:11434/api/generate"
    supported_formats: list = None
    
    def __post_init__(self):
        if self.supported_formats is None:
            self.supported_formats = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp']

@dataclass
class AppConfig:
    """การตั้งค่าหลักของแอปพลิเคชัน"""
    app_name: str = "JobN Power by AI NT North"
    app_version: str = "1.0.0"
    page_title: str = "JobN Power - Document Management & AI Assistant"
    page_icon: str = "📋"
    layout: str = "wide"
    upload_folder: str = "data/uploads"
    embeddings_folder: str = "data/embeddings"
    max_file_size: int = 200  # MB
    
    # สีธีม
    primary_color: str = "#FFD700"
    secondary_color: str = "#FFF8DC" 
    accent_color: str = "#FF8C00"
    background_color: str = "#FFFAF0"
    text_color: str = "#2F2F2F"

class Config:
    """คลาสหลักสำหรับจัดการการตั้งค่าทั้งหมด"""
    
    def __init__(self):
        self.db = DatabaseConfig()
        self.embedding = EmbeddingConfig()
        self.chat = ChatConfig()
        self.ocr = OCRConfig()
        self.app = AppConfig()
        
    def get_line_token(self) -> Optional[str]:
        """ดึง LINE Token จาก Streamlit secrets หรือ session state"""
        try:
            # ลองดึงจาก secrets ก่อน
            if 'line_token' in st.secrets:
                return st.secrets['line_token']
            
            # ถ้าไม่มีใน secrets ให้ดึงจาก session state
            if 'line_token' in st.session_state:
                return st.session_state.line_token
                
            return None
        except Exception:
            return None
    
    def get_system_prompt(self) -> str:
        """ดึง System Prompt จาก session state"""
        default_prompt = """คุณเป็น AI Assistant สำหรับองค์กร บลนป. (บริการลูกค้านิคมอุตสาหกรรมภาคเหนือ)
        
        หน้าที่ของคุณ:
        1. ตอบคำถามเกี่ยวกับเอกสารและข้อมูลขององค์กร
        2. ช่วยเหลือในการค้นหาข้อมูลที่เกี่ยวข้อง
        3. ให้คำแนะนำและข้อมูลที่เป็นประโยชน์
        
        คำแนะนำ:
        - ตอบเป็นภาษาไทยที่เป็นกันเอง
        - ใช้ข้อมูลจากเอกสารที่ให้มาเป็นหลัก
        - หากไม่ทราบคำตอบ ให้บอกว่าไม่ทราบและแนะนำให้ติดต่อเจ้าหน้าที่
        - รักษาความเป็นมืออาชีพและให้ข้อมูลที่ถูกต้อง
        """
        
        return st.session_state.get('system_prompt', default_prompt)
    
    def update_system_prompt(self, prompt: str):
        """อัพเดท System Prompt"""
        st.session_state.system_prompt = prompt
    
    def update_line_token(self, token: str):
        """อัพเดท LINE Token"""
        st.session_state.line_token = token

# สร้าง instance หลักสำหรับใช้งาน
config = Config()

# ฟังก์ชันช่วยเหลือ
def ensure_directories():
    """สร้างโฟลเดอร์ที่จำเป็นหากยังไม่มี"""
    import os
    os.makedirs(config.app.upload_folder, exist_ok=True)
    os.makedirs(config.app.embeddings_folder, exist_ok=True)
    os.makedirs("data/temp", exist_ok=True)

def get_custom_css() -> str:
    """ส่งคืน Custom CSS สำหรับ Streamlit"""
    return f"""
    <style>
    /* หลัก */
    .main .block-container {{
        padding-top: 1rem;
        padding-bottom: 1rem;
    }}
    
    /* Sidebar */
    .css-1d391kg {{
        background-color: {config.app.secondary_color};
    }}
    
    /* Header */
    .css-10trblm {{
        color: {config.app.text_color};
        font-weight: bold;
    }}
    
    /* Buttons */
    .stButton > button {{
        background-color: {config.app.primary_color};
        color: {config.app.text_color};
        border: none;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s;
    }}
    
    .stButton > button:hover {{
        background-color: {config.app.accent_color};
        box-shadow: 0 4px 12px rgba(255, 140, 0, 0.3);
    }}
    
    /* File uploader */
    .stFileUploader {{
        background-color: {config.app.secondary_color};
        border: 2px dashed {config.app.primary_color};
        border-radius: 10px;
        padding: 20px;
    }}
    
    /* Chat messages */
    .stChatMessage {{
        background-color: {config.app.secondary_color};
        border-radius: 10px;
        margin: 5px 0;
    }}
    
    /* Success/Error messages */
    .stAlert {{
        border-radius: 8px;
    }}
    
    /* Metrics */
    .metric-container {{
        background: linear-gradient(135deg, {config.app.primary_color}20, {config.app.secondary_color});
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }}
    </style>
    """
