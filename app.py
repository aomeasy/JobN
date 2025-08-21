"""
JobN Power by AI NT North
ระบบจัดการเอกสารและ AI Assistant สำหรับ บลนป.
"""

import streamlit as st
import os
from datetime import datetime
from config import config, ensure_directories, get_custom_css

# การตั้งค่าหน้าเว็บ
st.set_page_config(
    page_title=config.app.page_title,
    page_icon=config.app.page_icon,
    layout=config.app.layout,
    initial_sidebar_state="expanded"
)

# โหลด CSS
st.markdown(get_custom_css(), unsafe_allow_html=True)

# สร้างโฟลเดอร์ที่จำเป็น
ensure_directories()

def main():
    """ฟังก์ชันหลัก"""
    
    # Header
    st.markdown(f"""
    <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, {config.app.primary_color}20, {config.app.secondary_color}); border-radius: 10px; margin-bottom: 30px;">
        <h1 style="color: {config.app.text_color}; margin: 0;">
            📋 {config.app.app_name}
        </h1>
        <p style="color: {config.app.text_color}; opacity: 0.8; margin: 10px 0 0 0;">
            ระบบจัดการเอกสารและ AI Assistant สำหรับ บลนป. (บริการลูกค้านิคมอุตสาหกรรมภาคเหนือ)
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown(f"""
        <div style="text-align: center; padding: 15px; background-color: {config.app.primary_color}30; border-radius: 10px; margin-bottom: 20px;">
            <h3 style="color: {config.app.text_color}; margin: 0;">🎯 เมนูหลัก</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # แสดงสถานะการเชื่อมต่อ
        show_system_status()
    
    # เนื้อหาหน้าหลัก
    show_main_content()
    
    # Footer
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align: center; color: {config.app.text_color}; opacity: 0.7; padding: 10px;">
        <small>
            {config.app.app_name} v{config.app.app_version} | 
            พัฒนาโดยทีม AI NT North | 
            © 2025 บลนป.
        </small>
    </div>
    """, unsafe_allow_html=True)

def show_system_status():
    """แสดงสถานะระบบใน Sidebar"""
    st.markdown("### 🔧 สถานะระบบ")
    
    # สถานะฐานข้อมูล
    try:
        from database.database import test_connection
        db_status = "🟢 เชื่อมต่อแล้ว" if test_connection() else "🔴 ไม่สามารถเชื่อมต่อ"
    except:
        db_status = "🟡 ไม่ทราบสถานะ"
    
    st.write(f"**ฐานข้อมูล:** {db_status}")
    
    # สถานะ APIs
    st.write(f"**Chat API:** 🟡 {config.chat.model}")
    st.write(f"**Embedding API:** 🟡 {config.embedding.model}")
    st.write(f"**OCR API:** 🟡 Typhoon Models")
    
    # ข้อมูลการใช้งาน
    st.markdown("---")
    st.markdown("### 📊 สถิติการใช้งาน")
    
    # จำนวนเอกสาร (จาก session state หรือ database)
    doc_count = st.session_state.get('document_count', 0)
    chat_count = st.session_state.get('chat_count', 0)
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("เอกสาร", doc_count)
    with col2:
        st.metric("แชทประวัติ", chat_count)

def show_main_content():
    """แสดงเนื้อหาหน้าหลัก - คู่มือการใช้งาน"""
    
    # แท็บหลัก
    tab1, tab2, tab3, tab4 = st.tabs([
        "📖 คู่มือการใช้งาน", 
        "🚀 เริ่มต้นใช้งาน", 
        "💡 คุณสมบัติ", 
        "❓ คำถามที่พบบ่อย"
    ])
    
    with tab1:
        show_user_guide()
    
    with tab2:
        show_quick_start()
        
    with tab3:
        show_features()
        
    with tab4:
        show_faq()

def show_user_guide():
    """แสดงคู่มือการใช้งาน"""
    st.markdown("## 📖 คู่มือการใช้งานระบบ")
    
    st.markdown("""
    ### ระบบ JobN Power ประกอบด้วย 4 หน้าหลัก:
    
    #### 1. 📋 Document Manager (การจัดการเอกสาร)
    - **อัพโหลดเอกสาร**: รองรับไฟล์ PDF, Word, Excel, PowerPoint และรูปภาพ
    - **จัดหมวดหมู่**: แยกเอกสารตามประเภทและหน่วยงาน
    - **ค้นหาเอกสาร**: ค้นหาได้ทั้งชื่อไฟล์และเนื้อหาภายใน
    - **แชร์เอกสาร**: สร้างลิงก์สำหรับแชร์เอกสารกับเพื่อนร่วมงาน
    
    #### 2. 🤖 AI Chatbot (ผู้ช่วยอัจฉริยะ)
    - **RAG System**: ค้นหาและตอบคำถามจากเอกสารที่อัพโหลด
    - **ภาษาไทย**: รองรับการสนทนาภาษาไทยอย่างเต็มรูปแบบ
    - **บริบทเฉพาะ**: เข้าใจบริบทของงาน บลนป.
    - **ประวัติการสนทนา**: บันทึกและย้อนดูการสนทนาก่อนหน้า
    
    #### 3. 👁️ OCR Reader (อ่านข้อความจากรูป)
    - **อ่านภาษาไทย**: ใช้ Typhoon OCR รองรับภาษาไทยได้ดี
    - **หลายรูปแบบ**: รองรับ PDF, JPG, PNG และรูปแบบอื่นๆ
    - **แก้ไขข้อความ**: สามารถแก้ไขผลลัพธ์ที่อ่านได้
    - **บันทึกผลลัพธ์**: บันทึกข้อความที่อ่านได้ลงในระบบ
    
    #### 4. ⚙️ Settings (การตั้งค่า)
    - **LINE Token**: ตั้งค่าการแจ้งเตือนผ่าน LINE
    - **System Prompt**: กำหนดบุคลิกและวิธีตอบของ AI
    - **การจัดการผู้ใช้**: เพิ่ม/ลบผู้ใช้งาน (สำหรับ Admin)
    - **Backup & Restore**: สำรองและกู้คืนข้อมูล
    """)

def show_quick_start():
    """แสดงขั้นตอนเริ่มต้นใช้งาน"""
    st.markdown("## 🚀 เริ่มต้นใช้งานใน 5 ขั้นตอน")
    
    steps = [
        {
            "title": "1. ตั้งค่าระบบ",
            "content": "ไปที่หน้า Settings และตั้งค่า LINE Token (ถ้าต้องการ)",
            "icon": "⚙️"
        },
        {
            "title": "2. อัพโหลดเอกสาร",
            "content": "ไปที่หน้า Document Manager และอัพโหลดเอกสารที่ต้องการ",
            "icon": "📋"
        },
        {
            "title": "3. รอการประมวลผล",
            "content": "ระบบจะทำการ Embedding เอกสารเพื่อให้ AI สามารถค้นหาได้",
            "icon": "⏳"
        },
        {
            "title": "4. ทดสอบ AI Chatbot",
            "content": "ไปที่หน้า AI Chatbot และลองถามคำถามเกี่ยวกับเอกสาร",
            "icon": "🤖"
        },
        {
            "title": "5. ใช้งานจริง",
            "content": "เริ่มใช้งานระบบในการทำงานประจำวัน",
            "icon": "✅"
        }
    ]
    
    for i, step in enumerate(steps):
        with st.container():
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, {config.app.primary_color}20, {config.app.secondary_color}); 
                        padding: 15px; border-radius: 10px; margin: 10px 0; 
                        border-left: 4px solid {config.app.primary_color};">
                <h4 style="margin: 0; color: {config.app.text_color};">
                    {step['icon']} {step['title']}
                </h4>
                <p style="margin: 5px 0 0 0; color: {config.app.text_color};">
                    {step['content']}
                </p>
            </div>
            """, unsafe_allow_html=True)

def show_features():
    """แสดงคุณสมบัติของระบบ"""
    st.markdown("## 💡 คุณสมบัติเด่นของระบบ")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div style="background: {config.app.secondary_color}; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
            <h4 style="color: {config.app.text_color}; margin-top: 0;">🔍 RAG System</h4>
            <p style="color: {config.app.text_color};">
                • ค้นหาข้อมูลจากเอกสารด้วย AI<br>
                • รองรับภาษาไทยและอังกฤษ<br>
                • ความแม่นยำสูงด้วย Vector Search<br>
                • ตอบคำถามตามบริบทขององค์กร
            </p>
        </div>
        
        <div style="background: {config.app.secondary_color}; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
            <h4 style="color: {config.app.text_color}; margin-top: 0;">📱 LINE Integration</h4>
            <p style="color: {config.app.text_color};">
                • แจ้งเตือนผ่าน LINE Notify<br>
                • อัพเดทสถานะการทำงาน<br>
                • รายงานการใช้งานระบบ<br>
                • การแจ้งเตือนเมื่อมีเอกสารใหม่
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style="background: {config.app.secondary_color}; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
            <h4 style="color: {config.app.text_color}; margin-top: 0;">🔒 ความปลอดภัย</h4>
            <p style="color: {config.app.text_color};">
                • ข้อมูลเก็บใน TiDB Cloud<br>
                • การยืนยันตัวตนแบบหลายชั้น<br>
                • เข้ารหัสการสื่อสาร<br>
                • การจัดการสิทธิ์ผู้ใช้
            </p>
        </div>
        
        <div style="background: {config.app.secondary_color}; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
            <h4 style="color: {config.app.text_color}; margin-top: 0;">⚡ ประสิทธิภาพ</h4>
            <p style="color: {config.app.text_color};">
                • รองรับไฟล์ขนาดใหญ่ถึง 200MB<br>
                • ประมวลผลเร็วด้วย GPU<br>
                • Caching เพื่อลดเวลาตอบสนอง<br>
                • อัพเดทแบบ Real-time
            </p>
        </div>
        """, unsafe_allow_html=True)

def show_faq():
    """แสดงคำถามที่พบบ่อย"""
    st.markdown("## ❓ คำถามที่พบบ่อย")
    
    faqs = [
        {
            "question": "ระบบรองรับไฟล์ประเภทไหนบ้าง?",
            "answer": "รองรับไฟล์ PDF, Word (.docx), Excel (.xlsx), PowerPoint (.pptx), รูปภาพ (JPG, PNG, TIFF) และไฟล์ข้อความ (.txt)"
        },
        {
            "question": "AI สามารถตอบคำถามภาษาไทยได้หรือไม่?",
            "answer": "ได้ครับ ระบบใช้โมเดล Qwen3 และ Typhoon ที่รองรับภาษาไทยได้ดี และสามารถเข้าใจบริบทเฉพาะของงาน บลนป."
        },
        {
            "question": "ข้อมูลจะปลอดภัยหรือไม่?",
            "answer": "ปลอดภัยครับ เก็บข้อมูลใน TiDB Cloud ที่มีมาตรฐานความปลอดภัยสูง และมีการเข้ารหัสข้อมูลทุกระดับ"
        },
        {
            "question": "สามารถใช้งานผ่านมือถือได้หรือไม่?",
            "answer": "ได้ครับ ระบบทำงานผ่าน Web Browser จึงสามารถใช้งานได้ทั้งคอมพิวเตอร์และมือถือ"
        },
        {
            "question": "หากมีปัญหาการใช้งานติดต่อที่ไหน?",
            "answer": "สามารถติดต่อทีม IT ของ บลนป. หรือใช้ระบบ AI Chatbot เพื่อขอความช่วยเหลือเบื้องต้น"
        }
    ]
    
    for i, faq in enumerate(faqs):
        with st.expander(f"📌 {faq['question']}"):
            st.write(faq['answer'])

if __name__ == "__main__":
    main()
