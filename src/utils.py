import cv2
import numpy as np
import logging
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display
import math
import os
from src.constants import FONT_PATH_FA, FONT_PATH_EN

def check_hardware_acceleration():
    try:
        cuda_available = cv2.cuda.getCudaEnabledDeviceCount() > 0
        if cuda_available:
            device_count = cv2.cuda.getCudaEnabledDeviceCount()
            logging.info(f"CUDA enabled with {device_count} device(s).")
            for i in range(device_count):
                logging.info(f"CUDA Device {i}: {cv2.cuda.getDeviceInfo(i).name()}")
        else:
            logging.info("CUDA is not available.")

        opencl_available = cv2.ocl.haveOpenCL()
        if opencl_available:
            logging.info("OpenCL is available.")
            cv2.ocl.setUseOpenCL(True)
            logging.info(f"OpenCL enabled: {cv2.ocl.useOpenCL()}")
        else:
            logging.info("OpenCL is not available.")

        return cuda_available, opencl_available
    except Exception as e:
        logging.error(f"Error checking hardware acceleration: {e}")
        return False, False

def eye_aspect_ratio(eye):
    try:
        A = np.linalg.norm(eye[1] - eye[5])
        B = np.linalg.norm(eye[2] - eye[4])
        C = np.linalg.norm(eye[0] - eye[3])
        if C == 0:
            logging.warning("Zero horizontal eye distance detected. Returning default EAR of 0.0.")
            return 0.0
        ear = (A + B) / (2.0 * C)
        return ear
    except Exception as e:
        logging.error(f"Error calculating eye aspect ratio: {e}")
        return 0.0

def render_animated_text(pil_img, text, language, frame_count):
    try:
        draw = ImageDraw.Draw(pil_img, 'RGBA')
        font_size = 40  # اندازه فونت مناسب
        try:
            if language == "fa":
                font = ImageFont.truetype(FONT_PATH_FA, font_size)
            else:
                font = ImageFont.truetype(FONT_PATH_EN, font_size)
        except IOError:
            logging.warning("Falling back to default font with size 24.")
            font = ImageFont.truetype("arial.ttf", 24) if language == "en" else ImageFont.truetype("tahoma.ttf", 24)

        # رندر صحیح متن فارسی
        reshaped_text = arabic_reshaper.reshape(text) if language == "fa" else text
        bidi_text = get_display(reshaped_text) if language == "fa" else text

        opacity = int(255 * (1.0 - (math.sin(frame_count / 20.0) * 0.3)))
        offset_y = int(20 * math.sin(frame_count / 15.0))

        bbox = font.getbbox(bidi_text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        img_width, img_height = pil_img.size
        text_x = (img_width - text_width) / 2
        text_y = (img_height - text_height) / 2 + offset_y

        draw.rectangle(
            [(text_x - 10, text_y - 10), (text_x + text_width + 10, text_y + text_height + 10)],
            fill=(0, 0, 0, 128)
        )

        # سایه برای خوانایی بهتر
        draw.text((text_x + 3, text_y + 3), bidi_text, font=font, fill=(0, 0, 0, opacity))
        draw.text((text_x, text_y), bidi_text, font=font, fill=(255, 255, 255, opacity))
        return pil_img
    except Exception as e:
        logging.error(f"Error rendering animated text: {e}")
        return pil_img

def get_texts():
    return {
        "fa": {
            "window_title": "سیستم تشخیص خواب‌آلودگی",
            "window_title_settings": "تنظیمات",
            "main_tab": "اصلی",
            "settings_btn": "تنظیمات ⚙️",
            "eye_threshold": "آستانه نسبت چشم (ضریب ۱۰۰)",
            "consec_frames": "تعداد فریم‌های متوالی",
            "roll_tilt": "آستانه کجی سر افقی (درجه)",
            "pitch_tilt": "آستانه کجی سر عمودی (درجه)",
            "sensitivity_label": "حالت حساسیت",
            "alert_count": "تعداد هشدارها: {} 🚨",
            "ear_ratio": "نسبت چشم: {:.2f} 👁️",
            "tilt_info": "کجی افقی: {:.2f}° | کجی عمودی: {:.2f}° 🛠️",
            "direction": "جهت هشدار: {} 📍",
            "theme_label": "تم رابط کاربری",
            "language_label": "زبان",
            "volume_label": "میزان صدای هشدار",
            "sound_alert_label": "فعال کردن هشدار صوتی",
            "day_theme": "روشن",
            "night_theme": "تیره",
            "persian": "فارسی",
            "english": "انگلیسی",
            "sensitivity_high": "حساس",
            "sensitivity_normal": "معمولی",
            "sensitivity_low": "کم‌حساس",
            "alert_message_sleep": "چشمان خود را باز نگه دارید!",
            "alert_message_roll": "سر خود را به سمت {} تنظیم کنید!",
            "alert_message_pitch": "سر خود را به سمت {} تنظیم کنید!",
            "alert_message_head_both": "سر خود را به سمت {} تنظیم کنید!",
            "alert_message_eyes_and_roll": "چشمان خود را باز کنید و سر را به سمت {} تنظیم کنید!",
            "alert_message_eyes_and_pitch": "چشمان خود را باز کنید و سر را به سمت {} تنظیم کنید!",
            "alert_message_eyes_and_head_both": "چشمان خود را باز کنید و سر را به سمت {} تنظیم کنید!",
            "alert_message_no_face": "چهره‌ای شناسایی نشد! لطفاً در مقابل دوربین قرار بگیرید.",
            "alert_warning_sleep": "احتیاط: چشمان شما در حال بسته شدن است.",
            "alert_warning_head": "احتیاط: سر خود را صاف نگه دارید.",
            "horizon": "افقی",
            "straight": "مستقیم",
            "right": "راست",
            "left": "چپ",
            "forward": "جلو",
            "back": "عقب",
            "blink_rate": "نرخ پلک زدن: {} در دقیقه 👁️",
            "save_settings": "ذخیره تنظیمات",
            "settings_saved": "تنظیمات با موفقیت ذخیره شد."
            
        },
        "en": {
            "window_title": "Drowsiness Detection System",
            "window_title_settings": "Settings",
            "main_tab": "Main",
            "settings_btn": "Settings ⚙️",
            "eye_threshold": "Eye Aspect Ratio Threshold (x100)",
            "consec_frames": "Consecutive Frames",
            "roll_tilt": "Head Roll Threshold (degrees)",
            "pitch_tilt": "Head Pitch Threshold (degrees)",
            "sensitivity_label": "Sensitivity Mode",
            "alert_count": "Alert Count: {} 🚨",
            "ear_ratio": "Eye Aspect Ratio: {:.2f} 👁️",
            "tilt_info": "Roll: {:.2f}° | Pitch: {:.2f}° 🛠️",
            "direction": "Alert Direction: {} 📍",
            "theme_label": "Interface Theme",
            "language_label": "Language",
            "volume_label": "Alert Volume",
            "sound_alert_label": "Enable Sound Alert",
            "day_theme": "Light",
            "night_theme": "Dark",
            "persian": "Persian",
            "english": "English",
            "sensitivity_high": "High",
            "sensitivity_normal": "Normal",
            "sensitivity_low": "Low",
            "alert_message_sleep": "Keep your eyes open!",
            "alert_message_roll": "Tilt your head to the {}!",
            "alert_message_pitch": "Tilt your head {}!",
            "alert_message_head_both": "Adjust your head to {}!",
            "alert_message_eyes_and_roll": "Open your eyes and tilt your head to the {}!",
            "alert_message_eyes_and_pitch": "Open your eyes and tilt your head {}!",
            "alert_message_eyes_and_head_both": "Open your eyes and adjust your head to {}!",
            "alert_message_no_face": "No face detected! Please position yourself in front of the camera.",
            "alert_warning_sleep": "Caution: Your eyes are closing.",
            "alert_warning_head": "Caution: Keep your head straight.",
            "horizon": "horizon",
            "straight": "straight",
            "right": "right",
            "left": "left",
            "forward": "forward",
            "back": "back",
            "blink_rate": "Blink Rate: {} per minute 👁️",
            "save_settings": "Save Settings",
            "settings_saved": "Settings saved successfully."
        }
    }