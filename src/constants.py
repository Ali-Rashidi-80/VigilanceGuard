# constants.py
import os, cv2

# Frame dimensions
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

# Eye indices for MediaPipe FaceMesh
LEFT_EYE_INDICES = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_INDICES = [263, 387, 385, 362, 380, 373]

# Alert thresholds
EYE_AR_THRESH = 0.14
EYE_AR_CONSEC_FRAMES = 80
HEAD_ROLL_THRESH = 15
HEAD_PITCH_THRESH = 22
ALERT_MIN_DURATION = 1.0
ALERT_COOLDOWN = {
    "no_face": 5.0,
    "eyes_closed": 3.0,
    "eyes_closed_and_head": 3.0,
    "head_tilt": 2.0,
    "blink_anomaly": 5.0
}
GRACE_PERIOD = 1.5
STD_DEV_THRESH = 4.0
MIN_BRIGHTNESS_THRESH = 10
DYNAMIC_EAR_ADJUST_RATE = 0.002
SENSITIVITY_MODES = {
    "high": {"ear_scale": 0.80, "consec_frames": 50, "roll_scale": 0.85, "pitch_scale": 0.80},
    "normal": {"ear_scale": 1.0, "consec_frames": 80, "roll_scale": 1.0, "pitch_scale": 1.0},
    "low": {"ear_scale": 1.20, "consec_frames": 100, "roll_scale": 1.15, "pitch_scale": 1.15}
}

# Scoring system thresholds
SCORE_THRESHOLD = {
    "eyes_closed": 100.0,
    "head_tilt_roll": 80.0,
    "head_tilt_pitch": 80.0,
    "no_face": 120.0,
    "long_blink": 60.0,
    "blink_anomaly": 60.0
}
SCORE_DECAY = 0.9  # Decay factor for scores per frame
SCORE_WEIGHTS = {
    "eyes_closed": 2.0,
    "head_tilt_roll": 1.5,
    "head_tilt_pitch": 1.5,
    "no_face": 3.0
}

# Smoothing filter weights
SMOOTHING_WEIGHTS = [0.5, 0.3, 0.15, 0.05]  # Weights for weighted moving average

# File paths
FONT_PATH_FA = "assets/BNazanin.ttf"
FONT_PATH_EN = "assets/arial.ttf"
ALARM_SOUND = "assets/Enrique Iglesias & Pitbull - Move To Miami.mp3"
ALERT_FOLDER = "alerts"
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".drowsiness_config.json")

# Video recording settings
FOURCC = cv2.VideoWriter_fourcc(*'mp4v')
FPS = 20.0
YOLO_MODEL_PATH = "src/yolo11n.pt"

# Blink detection thresholds
BLINK_RATE_MIN = 15
BLINK_RATE_MAX = 20
BLINK_DURATION_THRESH = 0.5
BLINK_CONSEC_FRAMES = 10

# Text messages (unchanged)
TEXTS = {
    "fa": {
        "blink_rate": "نرخ پلک زدن: {} در دقیقه 👁️",
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
        "save_settings": "ذخیره تنظیمات",
        "settings_saved": "تنظیمات با موفقیت ذخیره شد.",
        "alert_message_blink_anomaly": "نرخ پلک زدن غیرنرمال است! ({}/دقیقه)",
        "alert_message_long_blink": "پلک زدن طولانی تشخیص داده شد! ({:.2f} ثانیه)",
        "alert_warning_blink": "احتیاط: نرخ پلک زدن غیرنرمال یا پلک زدن طولانی.",
    },
    "en": {
        "blink_rate": "Blink Rate: {} per minute 👁️",
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
        "save_settings": "Save Settings",
        "settings_saved": "Settings saved successfully.",
        "alert_message_blink_anomaly": "Abnormal blink rate detected! ({}/minute)",
        "alert_message_long_blink": "Long blink detected! ({:.2f} seconds)",
        "alert_warning_blink": "Caution: Abnormal blink rate or long blink detected.",
    }
}