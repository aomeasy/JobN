"""
หน้าจัดการเอกสาร - Document Manager
อัพโหลด, จัดเก็บ, ค้นหา และจัดการเอกสาร
"""

import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
import mimetypes
from config import config, get_custom_css
from database.database import get_db_session
from database.models import Document, User
from services.embedding_service import process_document_embeddings, get_embedding_statistics
from utils.file_handler import FileHandler
import plotly.express as px
import plotly.graph_objects as go

# ตั้งค่าหน้า
st.set_page_config(
    page_title="Document Manager - JobN Power",
    page_icon="📋",
    layout="wide"
)

# โหลด CSS
st.markdown(get_custom_css(), unsafe_allow_html=True)

def main():
    """ฟังก์ชันหลัก"""
    
    # Header
    st.markdown(f"""
    <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, {config.app.primary_color}20, {config.app.secondary_color}); border-radius: 10px; margin-bottom: 30px;">
        <h1 style="color: {config.app.text_color}; margin: 0;">
            📋 จัดการเอกสาร
        </h1>
        <p style="color: {config.app.text_color}; opacity: 0.8; margin: 10px 0 0 0;">
            อัพโหลด จัดเก็บ และค้นหาเอกสารสำหรับระบบ AI
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # แท็บหลัก
    tab1, tab2, tab3, tab4 = st.tabs([
        "📤 อัพโหลดเอกสาร",
        "📚 คลังเอกสาร", 
        "🔍 ค้นหาเอกสาร",
        "📊 สถิติและรายงาน"
    ])
    
    with tab1:
        upload_documents()
    
    with tab2:
        document_library()
    
    with tab3:
        search_documents()
    
    with tab4:
        show_statistics()

def upload_documents():
    """หน้าอัพโหลดเอกสาร"""
    st.markdown("### 📤 อัพโหลดเอกสาร")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # ไฟล์อัพโหลด
        uploaded_files = st.file_uploader(
            "เลือกไฟล์เอกสาร",
            type=['pdf', 'docx', 'xlsx', 'pptx', 'txt', 'jpg', 'jpeg', 'png'],
            accept_multiple_files=True,
            help=f"รองรับไฟล์ขนาดสูงสุด {config.app.max_file_size}MB"
        )
        
        if uploaded_files:
            st.markdown("### 📝 ข้อมูลเอกสาร")
            
            # ข้อมูลสำหรับทุกไฟล์
            category = st.selectbox(
                "หมวดหมู่",
                ["เอกสารทั่วไป", "คู่มือการทำงาน", "นโยบายและระเบียบ", 
                 "รายงานประจำปี", "แผนงานโครงการ", "เอกสารลูกค้า", "อื่นๆ"],
                key="batch_category"
            )
            
            tags_input = st.text_input(
                "แท็ก (คั่นด้วยเครื่องหมายจุลภาค)",
                help="เช่น: บลนป, คู่มือ, 2025",
                key="batch_tags"
            )
            
            is_public = st.checkbox(
                "เปิดให้เข้าถึงสาธารณะ",
                value=False,
                help="อนุญาตให้ผู้ใช้อื่นเห็นเอกสารนี้"
            )
            
            # ปุ่มอัพโหลด
            if st.button("🚀 อัพโหลดทั้งหมด", type="primary"):
                upload_multiple_files(uploaded_files, category, tags_input, is_public)
    
    with col2:
        show_upload_info()

def upload_multiple_files(uploaded_files, category: str, tags_input: str, is_public: bool):
    """อัพโหลดไฟล์หลายไฟล์"""
    
    progress_bar = st.progress(0, text="เริ่มต้นการอัพโหลด...")
    status_container = st.container()
    
    file_handler = FileHandler()
    total_files = len(uploaded_files)
    successful_uploads = 0
    
    # แปลง tags
    tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()] if tags_input else []
    
    for i, uploaded_file in enumerate(uploaded_files):
        progress = (i + 1) / total_files
        progress_bar.progress(progress, text=f"กำลังอัพโหลด {uploaded_file.name}...")
        
        try:
            # ตรวจสอบขนาดไฟล์
            if uploaded_file.size > config.app.max_file_size * 1024 * 1024:
                status_container.error(f"❌ {uploaded_file.name}: ไฟล์ใหญ่เกิน {config.app.max_file_size}MB")
                continue
            
            # บันทึกไฟล์
            file_info = file_handler.save_uploaded_file(
                uploaded_file, 
                category=category,
                tags=tags,
                is_public=is_public,
                user_id=1  # TODO: ใช้ user_id จริงจากการล็อกอิน
            )
            
            if file_info:
                status_container.success(f"✅ {uploaded_file.name}: อัพโหลดสำเร็จ")
                successful_uploads += 1
                
                # ประมวลผล embedding ในพื้นหลัง
                if file_info.get('document_id'):
                    st.session_state[f"processing_{file_info['document_id']}"] = True
            else:
                status_container.error(f"❌ {uploaded_file.name}: การอัพโหลดล้มเหลว")
        
        except Exception as e:
            status_container.error(f"❌ {uploaded_file.name}: {str(e)}")
    
    progress_bar.progress(1.0, text="เสร็จสิ้น!")
    
    # สรุปผลการอัพโหลด
    if successful_uploads > 0:
        st.success(f"🎉 อัพโหลดสำเร็จ {successful_uploads}/{total_files} ไฟล์")
        
        # แสดงการประมวลผล embedding
        if st.button("🔄 เริ่มประมวลผล AI Embeddings"):
            process_all_pending_embeddings()
    else:
        st.error("
