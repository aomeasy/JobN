# JobN Power by AI NT North

ระบบจัดการเอกสารและ AI Assistant สำหรับ บลนป. (บริการลูกค้านิคมอุตสาหกรรมภาคเหนือ)

## 🎯 วัตถุประสงค์

- จัดการเอกสารภายในส่วนงาน บลนป.
- ระบบ AI Chatbot แบบ RAG สำหรับตอบคำถามจากเอกสาร
- รองรับการอ่านข้อความจากรูปภาพ (OCR)
- แจ้งเตือนผ่าน LINE Notify

## ✨ คุณสมบัติหลัก

### 📋 Document Manager
- อัพโหลดเอกสาร PDF, Word, Excel, PowerPoint และรูปภาพ
- สกัดข้อความอัตโนมัติ
- จัดหมวดหมู่และแท็กเอกสาร
- ค้นหาเอกสารด้วย AI

### 🤖 AI Chatbot
- ระบบ RAG (Retrieval-Augmented Generation)
- รองรับภาษาไทยและอังกฤษ
- ค้นหาและตอบคำถามจากเอกสาร
- กำหนด System Prompt ได้

### 👁️ OCR Reader
- อ่านข้อความจากรูปภาพ
- ใช้ Typhoon OCR สำหรับภาษาไทย
- รองรับ PDF, JPG, PNG และรูปแบบอื่นๆ
- แก้ไขผลลัพธ์ได้

### ⚙️ Settings
- ตั้งค่า LINE Token
- กำหนด System Prompt สำหรับ AI
- จัดการการตั้งค่าระบบ

## 🏗️ สถาปัตยกรรมระบบ

### ฐานข้อมูล
- **TiDB Cloud**: ฐานข้อมูลหลัก
- URL: `mysql+pymysql://2wGpw4Qa2maXMEz.root:FMDCS56nmOL9KSWg@gateway01.ap-southeast-1.prod.aws.tidbcloud.com:4000/ntdatabase`

### AI Models และ APIs
- **Chat Model**: Qwen3:14b สำหรับ Chatbot
- **Embedding Model**: nomic-embed-text:latest สำหรับ RAG
- **OCR Models**: 
  - scb10x/llama3.1-typhoon2-8b-instruct:latest
  - scb10x/typhoon-ocr-7b:latest
- **API URL**: http://209.15.123.47:11434

## 🚀 การติดตั้งและใช้งาน

### ข้อกำหนดระบบ
- Python 3.8+
- Git
- ความจุพื้นที่ว่าง 2GB+

### ขั้นตอนการติดตั้ง

1. **Clone Repository**
   ```bash
   git clone https://github.com/yourusername/jobn-power.git
   cd jobn-power
   ```

2. **สร้าง Virtual Environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

3. **ติดตั้ง Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **สร้างไฟล์การตั้งค่า**
   
   สร้างไฟล์ `.streamlit/secrets.toml`:
   ```toml
   # LINE Notify (ถ้าต้องการ)
   line_token = "your_line_notify_token"
   
   # การตั้งค่าเพิ่มเติม
   admin_password = "your_admin_password"
   ```

5. **รันแอปพลิเคชัน**
   ```bash
   streamlit run app.py
   ```

6. **เข้าถึงระบบ**
   - เปิดเบราว์เซอร์ไปที่: http://localhost:8501

### การ Deploy บน Streamlit Cloud

1. **Push โค้ดไปยัง GitHub**
   ```bash
   git add .
   git commit -m "Initial commit"
   git push origin main
   ```

2. **ไปที่ Streamlit Cloud**
   - เข้าสู่ระบบที่ https://share.streamlit.io/
   - เชื่อมต่อ GitHub Repository
   - เลือกไฟล์ `app.py` เป็นจุดเริ่มต้น

3. **ตั้งค่า Secrets**
   - ไปที่ Settings → Secrets
   - เพิ่มการตั้งค่าตาม `secrets.toml`

## 📁 โครงสร้างโปรเจค

```
jobn_power/
├── 📄 app.py                      # ไฟล์หลัก Streamlit
├── 📄 config.py                   # การตั้งค่าระบบ
├── 📄 requirements.txt            # Dependencies
│
├── 📁 database/                   # การจัดการฐานข้อมูล
│   ├── models.py                  # โมเดล SQLAlchemy
│   ├── database.py                # การเชื่อมต่อ
│   └── operations.py              # CRUD operations
│
├── 📁 services/                   # บริการต่างๆ
│   ├── embedding_service.py       # บริการ Embedding
│   ├── chat_service.py            # บริการ Chatbot
│   ├── ocr_service.py             # บริการ OCR
│   └── line_service.py            # บริการ LINE Notify
│
├── 📁 pages/                      # หน้าเว็บ
│   ├── 01_📋_Document_Manager.py  # จัดการเอกสาร
│   ├── 02_🤖_AI_Chatbot.py        # AI Chatbot
│   ├── 03_👁️_OCR_Reader.py        # OCR Reader
│   └── 04_⚙️_Settings.py          # การตั้งค่า
│
├── 📁 utils/                      # ยูทิลิตี้
│   ├── file_handler.py            # จัดการไฟล์
│   ├── auth.py                    # การยืนยันตัวตน
│   └── helpers.py                 # ฟังก์ชันช่วยเหลือ
│
├── 📁 components/                 # UI Components
│   ├── sidebar.py                 # Sidebar
│   ├── chat_interface.py          # Interface สำหรับ chat
│   └── document_viewer.py         # แสดงเอกสาร
│
├── 📁 data/                       # ข้อมูล
│   ├── uploads/                   # ไฟล์ที่อัพโหลด
│   ├── embeddings/                # Vector embeddings
│   └── temp/                      # ไฟล์ชั่วคราว
│
└── 📁 .streamlit/                 # การตั้งค่า Streamlit
    ├── config.toml                # การตั้งค่าทั่วไป
    └── secrets.toml               # ข้อมูลลับ (ไม่อัพโหลด Git)
```

## 💡 การใช้งาน

### 1. อัพโหลดเอกสาร
1. ไปที่หน้า "📋 Document Manager"
2. เลือกไฟล์ที่ต้องการอัพโหลด
3. กำหนดหมวดหมู่และแท็ก
4. กดปุ่ม "อัพโหลด"
5. รอระบบประมวลผล Embeddings

### 2. ใช้งาน AI Chatbot
1. ไปที่หน้า "🤖 AI Chatbot"
2. พิมพ์คำถามที่ต้องการทราบ
3. ระบบจะค้นหาเอกสารที่เกี่ยวข้อง
4. ได้รับคำตอบพร้อมอ้างอิงเอกสาร

### 3. อ่านข้อความจากรูป
1. ไปที่หน้า "👁️ OCR Reader"
2. อัพโหลดรูปภาพหรือ PDF
3. เลือกโมเดล OCR (แนะนำ Typhoon สำหรับภาษาไทย)
4. กดปุ่ม "เริ่มการอ่าน"
5. แก้ไขผลลัพธ์ถ้าจำเป็น

### 4. การตั้งค่าระบบ
1. ไปที่หน้า "⚙️ Settings"
2. ตั้งค่า LINE Token สำหรับแจ้งเตือน
3. ปรับ System Prompt สำหรับ AI
4. จัดการผู้ใช้งาน (สำหรับ Admin)

## 🔧 การกำหนดค่า

### Environment Variables
สร้างไฟล์ `.env` หรือใช้ Streamlit Secrets:

```toml
# Database
TIDB_URL = "mysql+pymysql://..."

# AI APIs
EMBEDDING_API_URL = "http://209.15.123.47:11434/api/embeddings"
EMBEDDING_MODEL = "nomic-embed-text:latest"
CHAT_API_URL = "http://209.15.123.47:11434/api/generate"
CHAT_MODEL = "Qwen3:14b"

# LINE Notify (Optional)
LINE_TOKEN = "your_line_notify_token"

# App Settings
MAX_FILE_SIZE_MB = 200
UPLOAD_FOLDER = "data/uploads"
```

### การปรับแต่ง

1. **สีธีม**: แก้ไขใน `config.py`
   ```python
   primary_color = "#FFD700"     # สีหลัก
   secondary_color = "#FFF8DC"   # สีรอง
   accent_color = "#FF8C00"      # สีเน้น
   ```

2. **ขีดจำกัดไฟล์**: แก้ไขใน `config.py`
   ```python
   max_file_size = 200  # MB
   chunk_size = 512     # สำหรับ embedding
   ```

3. **โมเดล AI**: แก้ไขใน `config.py`
   ```python
   chat_model = "Qwen3:14b"
   embedding_model = "nomic-embed-text:latest"
   ```

## 🧪 การทดสอบ

รันการทดสอบ:
```bash
# ทดสอบฐานข้อมูล
python -m pytest tests/test_database.py

# ทดสอบบริการต่างๆ
