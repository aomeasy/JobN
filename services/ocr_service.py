"""
บริการ OCR สำหรับอ่านข้อความจากรูปภาพและ PDF
ใช้ Typhoon OCR Models
"""

import requests
import json
import base64
import time
from typing import Dict, Any, Optional, List, Tuple
import logging
from datetime import datetime
import streamlit as st
from PIL import Image, ImageEnhance, ImageFilter
import io
import fitz  # PyMuPDF สำหรับ PDF
import os
from config import config
from database.database import get_db_session
from database.models import OCRTask, User

logger = logging.getLogger(__name__)

class OCRService:
    """คลาสจัดการ OCR"""
    
    def __init__(self):
        self.api_url = config.ocr.api_url
        self.typhoon_model = config.ocr.typhoon_model
        self.ocr_model = config.ocr.ocr_model
        self.supported_formats = config.ocr.supported_formats
        
    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """ปรับปรุงภาพก่อนส่ง OCR"""
        try:
            # แปลงเป็น RGB ถ้าจำเป็น
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # ปรับขนาดถ้าภาพใหญ่เกินไป
            max_size = (2048, 2048)
            if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
                image.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # เพิ่ม contrast และ sharpness
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.2)
            
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.1)
            
            # ลดสัญญาณรบกวน
            image = image.filter(ImageFilter.MedianFilter(size=1))
            
            return image
            
        except Exception as e:
            logger.error(f"เกิดข้อผิดพลาดในการปรับปรุงภาพ: {e}")
            return image
    
    def image_to_base64(self, image: Image.Image) -> str:
        """แปลงภาพเป็น base64"""
        try:
            buffer = io.BytesIO()
            image.save(buffer, format='PNG', quality=95)
            image_bytes = buffer.getvalue()
            return base64.b64encode(image_bytes).decode('utf-8')
        except Exception as e:
            logger.error(f"เกิดข้อผิดพลาดในการแปลง base64: {e}")
            return ""
    
    def pdf_to_images(self, pdf_path: str) -> List[Image.Image]:
        """แปลง PDF เป็นภาพ"""
        images = []
        try:
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                # เพิ่ม resolution สำหรับ OCR ที่ดีขึ้น
                mat = fitz.Matrix(2.0, 2.0)  # ขยายขนาด 2 เท่า
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_data))
                images.append(image)
            doc.close()
            return images
        except Exception as e:
            logger.error(f"เกิดข้อผิดพลาดในการแปลง PDF: {e}")
            return []
    
    def extract_text_from_image(self, image: Image.Image, 
                              use_typhoon: bool = True) -> Optional[Dict[str, Any]]:
        """สกัดข้อความจากภาพ"""
        try:
            start_time = time.time()
            
            # ปรับปรุงภาพ
            processed_image = self.preprocess_image(image)
            
            # แปลงเป็น base64
            base64_image = self.image_to_base64(processed_image)
            if not base64_image:
                return None
            
            # เลือกโมเดล
            model = self.typhoon_model if use_typhoon else self.ocr_model
            
            # สร้าง prompt สำหรับ OCR
            if use_typhoon:
                prompt = """กรุณาอ่านข้อความทั้งหมดในภาพนี้และส่งคืนเป็นข้อความธรรมดา:
                - อ่านข้อความทั้งภาษาไทยและภาษาอังกฤษ
                - รักษาการจัดรูปแบบเดิมไว้ (ขึ้นบรรทัดใหม่, ช่องว่าง)
                - ถ้ามีตารางให้จัดรูปแบบให้เข้าใจง่าย
                - ส่งคืนเฉพาะข้อความที่อ่านได้เท่านั้น ไม่ต้องอธิบาย
                
                ข้อความในภาพ:"""
            else:
                prompt = "Extract all text from this image, maintaining original formatting:"
            
            # เรียก API
            payload = {
                "model": model,
                "prompt": prompt,
                "images": [base64_image],
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 4000
                }
            }
            
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=120,
                headers={"Content-Type": "application/json"}
            )
            
            processing_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                extracted_text = result.get("response", "").strip()
                
                if extracted_text:
                    # ประเมินความมั่นใจโดยประมาณ
                    confidence = self._estimate_confidence(extracted_text)
                    
                    return {
                        "text": extracted_text,
                        "confidence": confidence,
                        "processing_time": processing_time,
                        "model_used": model,
                        "success": True
                    }
                else:
                    return {
                        "text": "",
                        "confidence": 0.0,
                        "processing_time": processing_time,
                        "model_used": model,
                        "success": False,
                        "error": "ไม่พบข้อความในภาพ"
                    }
            else:
                logger.error(f"OCR API error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("Timeout ในการทำ OCR")
            return None
        except Exception as e:
            logger.error(f"เกิดข้อผิดพลาดในการทำ OCR: {e}")
            return None
    
    def _estimate_confidence(self, text: str) -> float:
        """ประเมินความมั่นใจในผลลัพธ์ OCR"""
        try:
            if not text.strip():
                return 0.0
            
            # ตัวชี้วัดความมั่นใจ
            score = 0.5  # เริ่มต้น
            
            # ความยาวข้อความ
            if len(text) > 20:
                score += 0.1
            
            # อัตราส่วนตัวอักษรกับสัญลักษณ์พิเศษ
            alpha_chars = sum(c.isalnum() or c.isspace() for c in text)
            if len(text) > 0:
                alpha_ratio = alpha_chars / len(text)
                score += (alpha_ratio - 0.7) * 0.3
            
            # ตรวจสอบคำที่สมเหตุสมผล (ภาษาไทย/อังกฤษ)
            thai_chars = sum(ord(c) >= 0x0E00 and ord(c) <= 0x0E7F for c in text)
            english_chars = sum(c.isascii() and c.isalpha() for c in text)
            
            if thai_chars > 0 or english_chars > 0:
                score += 0.2
            
            # จำกัดค่าไม่ให้เกิน 1.0
            return min(1.0, max(0.0, score))
            
        except Exception:
            return 0.5
    
    def process_file(self, file_path: str, user_id: int = 1) -> Optional[int]:
        """ประมวลผลไฟล์ OCR"""
        try:
            # สร้าง OCR task
            with get_db_session() as session:
                task = OCRTask(
                    user_id=user_id,
                    input_filename=os.path.basename(file_path),
                    input_file_path=file_path,
                    input_file_type=os.path.splitext(file_path)[1].lower(),
                    status="processing"
                )
                session.add(task)
                session.commit()
                session.refresh(task)
                task_id = task.id
            
            # ประมวลผลตามประเภทไฟล์
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext == '.pdf':
                result = self._process_pdf(file_path)
            elif file_ext in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp']:
                result = self._process_image_file(file_path)
            else:
                result = {
                    "success": False,
                    "error": f"ไม่รองรับไฟล์ประเภท {file_ext}"
                }
            
            # อัพเดทผลลัพธ์
            with get_db_session() as session:
                task = session.query(OCRTask).filter(OCRTask.id == task_id).first()
                if task:
                    if result["success"]:
                        task.status = "completed"
                        task.extracted_text = result["text"]
                        task.confidence_score = result.get("confidence", 0.0)
                        task.processing_time = result.get("processing_time", 0.0)
                        task.model_used = result.get("model_used", "")
                        task.completed_at = datetime.utcnow()
                    else:
                        task.status = "failed"
                        task.error_message = result.get("error", "Unknown error")
                    
                    session.commit()
            
            return task_id if result["success"] else None
            
        except Exception as e:
            logger.error(f"เกิดข้อผิดพลาดในการประมวลผลไฟล์: {e}")
            return None
    
    def _process_image_file(self, file_path: str) -> Dict[str, Any]:
        """ประมวลผลไฟล์ภาพ"""
        try:
            image = Image.open(file_path)
            return self.extract_text_from_image(image) or {
                "success": False,
                "error": "ไม่สามารถสกัดข้อความได้"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"ไม่สามารถเปิดไฟล์ภาพได้: {str(e)}"
            }
    
    def _process_pdf(self, file_path: str) -> Dict[str, Any]:
        """ประมวลผลไฟล์ PDF"""
        try:
            start_time = time.time()
            images = self.pdf_to_images(file_path)
            
            if not images:
                return {
                    "success": False,
                    "error": "ไม่สามารถแปลง PDF เป็นภาพได้"
                }
            
            all_text = []
            total_confidence = 0.0
            successful_pages = 0
            
            for i, image in enumerate(images):
                page_result = self.extract_text_from_image(image)
                if page_result and page_result.get("success"):
                    all_text.append(f"--- หน้า {i+1} ---\n{page_result['text']}")
                    total_confidence += page_result.get("confidence", 0.0)
                    successful_pages += 1
                else:
                    all_text.append(f"--- หน้า {i+1} ---\n[ไม่สามารถอ่านข้อความได้]")
            
            processing_time = time.time() - start_time
            avg_confidence = total_confidence / max(successful_pages, 1)
            
            return {
                "success": successful_pages > 0,
                "text": "\n\n".join(all_text),
                "confidence": avg_confidence,
                "processing_time": processing_time,
                "model_used": self.typhoon_model,
                "pages_processed": len(images),
                "successful_pages": successful_pages
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"ไม่สามารถประมวลผล PDF ได้: {str(e)}"
            }
    
    def get_task_result(self, task_id: int) -> Optional[Dict[str, Any]]:
        """ดึงผลลัพธ์งาน OCR"""
        try:
            with get_db_session() as session:
                task = session.query(OCRTask).filter(OCRTask.id == task_id).first()
                
                if task:
                    return {
                        "id": task.id,
                        "uuid": task.uuid,
                        "filename": task.input_filename,
                        "status": task.status,
                        "extracted_text": task.extracted_text,
                        "confidence_score": task.confidence_score,
                        "processing_time": task.processing_time,
                        "model_used": task.model_used,
                        "error_message": task.error_message,
                        "created_at": task.created_at,
                        "completed_at": task.completed_at
                    }
                else:
                    return None
                    
        except Exception as e:
            logger.error(f"เกิดข้อผิดพลาดในการดึงผลลัพธ์: {e}")
            return None
    
    def get_user_tasks(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """ดึงรายการงาน OCR ของผู้ใช้"""
        try:
            with get_db_session() as session:
                tasks = session.query(OCRTask).filter(
                    OCRTask.user_id == user_id
                ).order_by(OCRTask.created_at.desc()).limit(limit).all()
                
                task_list = []
                for task in tasks:
                    task_list.append({
                        "id": task.id,
                        "uuid": task.uuid,
                        "filename": task.input_filename,
                        "status": task.status,
                        "confidence_score": task.confidence_score,
                        "processing_time": task.processing_time,
                        "created_at": task.created_at,
                        "completed_at": task.completed_at,
                        "has_text": bool(task.extracted_text)
                    })
                
                return task_list
                
        except Exception as e:
            logger.error(f"เกิดข้อผิดพลาดในการดึงรายการงาน: {e}")
            return []
    
    def get_ocr_statistics(self, user_id: int = None) -> Dict[str, Any]:
        """ดึงสถิติการใช้งาน OCR"""
        try:
            with get_db_session() as session:
                base_query = session.query(OCRTask)
                
                if user_id:
                    base_query = base_query.filter(OCRTask.user_id == user_id)
                
                total_tasks = base_query.count()
                completed_tasks = base_query.filter(OCRTask.status == "completed").count()
                failed_tasks = base_query.filter(OCRTask.status == "failed").count()
                
                # คำนวณเวลาประมวลผลเฉลี่ย
                avg_time = session.execute(
                    f"""SELECT AVG(processing_time) FROM ocr_tasks 
                       WHERE status = 'completed' AND processing_time IS NOT NULL
                       {f'AND user_id = {user_id}' if user_id else ''}"""
                ).scalar() or 0
                
                # คำนวณ confidence เฉลี่ย
                avg_confidence = session.execute(
                    f"""SELECT AVG(confidence_score) FROM ocr_tasks 
                       WHERE status = 'completed' AND confidence_score IS NOT NULL
                       {f'AND user_id = {user_id}' if user_id else ''}"""
                ).scalar() or 0
                
                return {
                    "total_tasks": total_tasks,
                    "completed_tasks": completed_tasks,
                    "failed_tasks": failed_tasks,
                    "pending_tasks": total_tasks - completed_tasks - failed_tasks,
                    "success_rate": (completed_tasks / max(total_tasks, 1)) * 100,
                    "avg_processing_time": round(float(avg_time), 2),
                    "avg_confidence": round(float(avg_confidence), 2),
                    "supported_formats": self.supported_formats
                }
                
        except Exception as e:
            logger.error(f"เกิดข้อผิดพลาดในการดึงสถิติ: {e}")
            return {}

# สร้าง instance หลัก
ocr_service = OCRService()

# Utility functions สำหรับใช้ใน Streamlit
def process_uploaded_file(uploaded_file, user_id: int = 1) -> Optional[int]:
    """ประมวลผลไฟล์ที่อัพโหลดใน Streamlit"""
    try:
        # บันทึกไฟล์ชั่วคราว
        temp_path = f"data/temp/{uploaded_file.name}"
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getvalue())
        
        # ประมวลผล OCR
        task_id = ocr_service.process_file(temp_path, user_id)
        
        # ลบไฟล์ชั่วคราว
        try:
            os.remove(temp_path)
        except:
            pass
        
        return task_id
        
    except Exception as e:
        logger.error(f"เกิดข้อผิดพลาดในการประมวลผลไฟล์ที่อัพโหลด: {e}")
        return None

def extract_text_from_uploaded_image(uploaded_file) -> Optional[Dict[str, Any]]:
    """สกัดข้อความจากภาพที่อัพโหลดทันที"""
    try:
        image = Image.open(uploaded_file)
        return ocr_service.extract_text_from_image(image)
    except Exception as e:
        logger.error(f"เกิดข้อผิดพลาดในการสกัดข้อความ: {e}")
        return None

@st.cache_data(ttl=300)  # cache เป็นเวลา 5 นาที
def get_ocr_statistics_cached(user_id: int = None):
    """ดึงสถิติ OCR สำหรับแสดงใน UI"""
    return ocr_service.get_ocr_statistics(user_id)
