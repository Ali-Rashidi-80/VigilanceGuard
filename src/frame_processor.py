# frame_processor.py
import cv2
import mediapipe as mp
import numpy as np
import threading
import logging
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display
import math
from src.utils import eye_aspect_ratio, check_hardware_acceleration, render_animated_text
from src.constants import FRAME_WIDTH, FRAME_HEIGHT, LEFT_EYE_INDICES, RIGHT_EYE_INDICES, FONT_PATH_FA, FONT_PATH_EN, TEXTS, STD_DEV_THRESH, MIN_BRIGHTNESS_THRESH, DYNAMIC_EAR_ADJUST_RATE, SENSITIVITY_MODES

class FrameProcessor:
    def __init__(self, parent):
        self.parent = parent
        self.frame_width = FRAME_WIDTH
        self.frame_height = FRAME_HEIGHT
        self.latest_frame = None
        self.frame_lock = threading.Lock()
        self.lut_cache = {}
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        self.use_cuda, self.use_opencl = check_hardware_acceleration()
        self.is_running = True
        self.roll_history = deque(maxlen=15)
        self.pitch_history = deque(maxlen=15)
        self.long_term_ear_history = deque(maxlen=300)
        self.ear_smoothing_window = deque(maxlen=10)
        self.kalman_ear = 0.0
        self.kalman_noise = 0.01
        self.kalman_measurement_noise = 0.1

        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                logging.error("Failed to open webcam.")
                raise Exception("Cannot open webcam.")
        except Exception as e:
            logging.error(f"Error initializing webcam: {e}")
            raise

        try:
            self.mp_face_mesh = mp.solutions.face_mesh
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.6,
                min_tracking_confidence=0.6
            )
        except Exception as e:
            logging.error(f"Error initializing FaceMesh: {e}")
            raise

        self.frame_reader_thread = threading.Thread(target=self.read_frames, daemon=True)
        self.frame_reader_thread.start()

    def read_frames(self):
        try:
            while self.is_running:
                ret, frame = self.cap.read()
                if ret:
                    with self.frame_lock:
                        self.latest_frame = frame.copy()
                else:
                    logging.warning("Failed to read frame from webcam.")
                    time.sleep(0.005)
        except Exception as e:
            logging.error(f"Error reading frames: {e}")

    def enhance_frame(self, frame, brightness_threshold=50):
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            brightness = np.mean(gray)
            brightness_key = round(brightness, 2)

            if brightness < 10:
                gamma = 3.5
            elif brightness < 23:
                gamma = 2.8
            elif brightness < 30:
                gamma = 2.2
            elif brightness < 50:
                gamma = 1.7
            else:
                gamma = 1.2
            invGamma = 1.0 / gamma
            table = np.array([((i / 255.0) ** invGamma) * 255 for i in np.arange(256)]).astype("uint8")

            if brightness_key in self.lut_cache:
                table = self.lut_cache[brightness_key]
            else:
                self.lut_cache[brightness_key] = table
                if len(self.lut_cache) > 25600:
                    self.lut_cache.pop(list(self.lut_cache.keys())[0])

            if brightness < brightness_threshold:
                lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
                l = clahe.apply(l)
                lab = cv2.merge((l, a, b))
                frame = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
                frame = cv2.fastNlMeansDenoisingColored(frame, None, 10, 10, 7, 21)

            return cv2.LUT(frame, table), brightness
        except Exception as e:
            logging.error(f"Error enhancing frame: {e}")
            return frame, 0.0

    def process_quadrant_image(self, quadrant_img, quadrant_coords, left_eye_points, right_eye_points, alert_flag, alert_severity):
        try:
            x_start, y_start, x_end, y_end = quadrant_coords
            if alert_flag or self.parent.pending_alert_message:
                overlay = quadrant_img.copy()
                if alert_severity == "severe":
                    color = (0, 0, 255)
                elif alert_severity == "moderate":
                    color = (0, 165, 255)
                elif alert_severity == "mild":
                    color = (0, 255, 255)
                else:
                    color = (255, 255, 0)
                cv2.rectangle(overlay, (0, 0), (quadrant_img.shape[1], quadrant_img.shape[0]), color, -1)
                alpha = 0.2 if self.parent.pending_alert_message else 0.3
                cv2.addWeighted(overlay, alpha, quadrant_img, 1 - alpha, 0, quadrant_img)

            left_points = [(x - x_start, y - y_start) for x, y in left_eye_points if x_start <= x < x_end and y_start <= y < y_end]
            if left_points:
                cv2.polylines(quadrant_img, [np.array(left_points)], True, (0, 255, 0), 1)

            right_points = [(x - x_start, y - y_start) for x, y in right_eye_points if x_start <= x < x_end and y_start <= y < y_end]
            if right_points:
                cv2.polylines(quadrant_img, [np.array(right_points)], True, (0, 255, 0), 1)

            return quadrant_img
        except Exception as e:
            logging.error(f"Error processing quadrant image: {e}")
            return quadrant_img

    def process_frame(self):
        try:
            with self.frame_lock:
                frame = self.latest_frame.copy() if self.latest_frame is not None else None
            if frame is None:
                return None

            frame = cv2.resize(frame, (self.frame_width, self.frame_height))
            frame, brightness = self.enhance_frame(frame)

            smoothed_ear = 1.0
            current_roll = 0.0
            current_pitch = 0.0
            direction_text = "---"
            alert_flag = False
            alert_severity = "none"
            left_eye_points = []
            right_eye_points = []
            roll_dir = ""
            pitch_dir = ""

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.face_mesh.process(rgb_frame)

            if not results.multi_face_landmarks:
                return frame, smoothed_ear, current_roll, current_pitch, direction_text, True, left_eye_points, right_eye_points, roll_dir, pitch_dir, "no_face", brightness

            face_landmarks = results.multi_face_landmarks[0]
            for idx in LEFT_EYE_INDICES:
                lm = face_landmarks.landmark[idx]
                left_eye_points.append((int(lm.x * self.frame_width), int(lm.y * self.frame_height)))
            for idx in RIGHT_EYE_INDICES:
                lm = face_landmarks.landmark[idx]
                right_eye_points.append((int(lm.x * self.frame_width), int(lm.y * self.frame_height)))

            if len(left_eye_points) != len(LEFT_EYE_INDICES) or len(right_eye_points) != len(RIGHT_EYE_INDICES):
                logging.warning("Incomplete eye landmarks detected.")
                smoothed_ear = 0.0
            else:
                leftEAR = eye_aspect_ratio(np.array(left_eye_points))
                rightEAR = eye_aspect_ratio(np.array(right_eye_points))
                ear = (leftEAR + rightEAR) / 2.0
                self.ear_smoothing_window.append(ear)
                self.parent.alert_handler.ear_history.append(ear)
                self.long_term_ear_history.append(ear)

                prediction = self.kalman_ear
                measurement = ear
                self.kalman_ear = prediction + (measurement - prediction) / (1.0 + self.kalman_noise / self.kalman_measurement_noise)
                smoothed_ear = self.kalman_ear

                if len(self.long_term_ear_history) == self.long_term_ear_history.maxlen:
                    avg_ear = np.mean(self.long_term_ear_history)
                    ear_std = np.std(self.long_term_ear_history)
                    if avg_ear > 0.1 and ear_std < 0.04:
                        new_threshold = max(0.12, min(0.27, avg_ear * (1 - DYNAMIC_EAR_ADJUST_RATE)))
                        if abs(new_threshold - self.parent.EYE_AR_THRESH) > 0.001:
                            logging.info(f"Adjusted EYE_AR_THRESH to {new_threshold}")
                            self.parent.EYE_AR_THRESH = new_threshold

            left_center = np.mean(np.array(left_eye_points), axis=0)
            right_center = np.mean(np.array(right_eye_points), axis=0)
            eyes_center = (left_center + right_center) / 2
            current_roll = np.degrees(np.arctan2(right_center[1] - left_center[1], right_center[0] - left_center[0]))
            nose_lm = face_landmarks.landmark[1]
            nose = (int(nose_lm.x * self.frame_width), int(nose_lm.y * self.frame_height))
            diff_y = nose[1] - eyes_center[1]
            eye_distance = np.linalg.norm(right_center - left_center)
            current_pitch = np.degrees(np.arctan2(diff_y, eye_distance)) -30

            self.roll_history.append(current_roll)
            self.pitch_history.append(current_pitch)
            smoothed_roll = sum(self.roll_history) / len(self.roll_history) if self.roll_history else 0.0
            smoothed_pitch = sum(self.pitch_history) / len(self.pitch_history) if self.pitch_history else 0.0

            is_stable = True
            if len(self.roll_history) == self.roll_history.maxlen:
                roll_std = np.std(self.roll_history)
                if roll_std > STD_DEV_THRESH:
                    is_stable = False
                    logging.debug(f"Unstable roll: std={roll_std}")
            if len(self.pitch_history) == self.pitch_history.maxlen:
                pitch_std = np.std(self.pitch_history)
                if pitch_std > STD_DEV_THRESH:
                    is_stable = False
                    logging.debug(f"Unstable pitch: std={pitch_std}")

            sensitivity = SENSITIVITY_MODES[self.parent.alert_handler.sensitivity_mode]
            ear_threshold = self.parent.EYE_AR_THRESH * sensitivity["ear_scale"]
            roll_threshold = self.parent.HEAD_ROLL_THRESH * sensitivity["roll_scale"]
            pitch_threshold = self.parent.HEAD_PITCH_THRESH * sensitivity["pitch_scale"]

            if brightness < MIN_BRIGHTNESS_THRESH:
                ear_threshold *= 1.10
                roll_threshold *= 1.05
                pitch_threshold *= 1.05
                logging.debug(f"Low brightness ({brightness}), adjusted thresholds")

            if smoothed_roll > roll_threshold:
                roll_dir = self.parent.texts[self.parent.language]["right"]
            elif smoothed_roll < -roll_threshold:
                roll_dir = self.parent.texts[self.parent.language]["left"]
            if smoothed_pitch > pitch_threshold:
                pitch_dir = self.parent.texts[self.parent.language]["back"]
            elif smoothed_pitch < -pitch_threshold:
                pitch_dir = self.parent.texts[self.parent.language]["forward"]
            if roll_dir and pitch_dir:
                direction_text = f"{roll_dir} و {pitch_dir}" if self.parent.language == "fa" else f"{roll_dir} and {pitch_dir}"
            elif roll_dir:
                direction_text = roll_dir
            elif pitch_dir:
                direction_text = pitch_dir

            if is_stable and (smoothed_ear < ear_threshold or abs(smoothed_roll) > roll_threshold or abs(smoothed_pitch) > pitch_threshold):
                alert_flag = True
                if smoothed_ear < ear_threshold and (abs(smoothed_roll) > roll_threshold or abs(smoothed_pitch) > pitch_threshold):
                    alert_severity = "severe"
                elif smoothed_ear < ear_threshold:
                    alert_severity = "moderate"
                else:
                    alert_severity = "mild"

            return frame, smoothed_ear, smoothed_roll, smoothed_pitch, direction_text, alert_flag, left_eye_points, right_eye_points, roll_dir, pitch_dir, alert_severity, brightness
        except Exception as e:
            logging.error(f"Error processing frame: {e}")
            return None

    def finalize_frame(self, frame, alert_flag, alert_severity):
        try:
            mid_x = self.frame_width // 2
            mid_y = self.frame_height // 2
            top_left_img = frame[0:mid_y, 0:mid_x].copy()
            top_right_img = frame[0:mid_y, mid_x:self.frame_width].copy()
            bottom_left_img = frame[mid_y:self.frame_height, 0:mid_x].copy()
            bottom_right_img = frame[mid_y:self.frame_height, mid_x:self.frame_width].copy()

            args_list = [
                (top_left_img, (0, 0, mid_x, mid_y), self.parent.left_eye_points, self.parent.right_eye_points, alert_flag, alert_severity),
                (top_right_img, (mid_x, 0, self.frame_width, mid_y), self.parent.left_eye_points, self.parent.right_eye_points, alert_flag, alert_severity),
                (bottom_left_img, (0, mid_y, mid_x, self.frame_height), self.parent.left_eye_points, self.parent.right_eye_points, alert_flag, alert_severity),
                (bottom_right_img, (mid_x, mid_y, self.frame_width, self.frame_height), self.parent.left_eye_points, self.parent.right_eye_points, alert_flag, alert_severity)
            ]

            futures = [self.thread_pool.submit(self.process_quadrant_image, *args) for args in args_list]
            quad0 = futures[0].result()
            quad1 = futures[1].result()
            quad2 = futures[2].result()
            quad3 = futures[3].result()

            top_row = np.hstack((quad0, quad1))
            bottom_row = np.hstack((quad2, quad3))
            combined_frame = np.vstack((top_row, bottom_row))

            if alert_flag or self.parent.pending_alert_message:
                logging.info(f"Rendering alert: flag={alert_flag}, message={self.parent.pending_alert_message}")
                rgb_combined = cv2.cvtColor(combined_frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb_combined)
                alert_message = self.get_alert_message() if alert_flag else self.parent.pending_alert_message
                if alert_message:
                    pil_img = render_animated_text(pil_img, alert_message, self.parent.language, self.parent.animation_frame)
                    combined_frame = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGBA2BGR)
                    self.parent.animation_frame += 1
                else:
                    logging.warning("No alert message to render")
            else:
                self.parent.animation_frame = 0

            return cv2.cvtColor(combined_frame, cv2.COLOR_BGR2RGB)
        except Exception as e:
            logging.error(f"Error finalizing frame: {e}")
            return frame

    def get_alert_message(self):
        try:
            smoothed_ear = self.kalman_ear
            current_roll = self.parent.current_roll
            current_pitch = self.parent.current_pitch
            roll_dir = self.parent.roll_dir
            pitch_dir = self.parent.pitch_dir
            alert_severity = self.parent.alert_severity
            texts = TEXTS[self.parent.language]
            blink_rate = self.parent.alert_handler.calculate_blink_rate()

            if alert_severity == "no_face":
                return texts["alert_message_no_face"]

            sensitivity = SENSITIVITY_MODES[self.parent.alert_handler.sensitivity_mode]
            ear_threshold = self.parent.EYE_AR_THRESH * sensitivity["ear_scale"]
            roll_threshold = self.parent.HEAD_ROLL_THRESH * sensitivity["roll_scale"]
            pitch_threshold = self.parent.HEAD_PITCH_THRESH * sensitivity["pitch_scale"]

            if self.parent.brightness < MIN_BRIGHTNESS_THRESH:
                ear_threshold *= 1.10
                roll_threshold *= 1.05
                pitch_threshold *= 1.05

            is_eyes_closed = smoothed_ear < ear_threshold
            is_roll_exceeded = abs(current_roll) > roll_threshold
            is_pitch_exceeded = pitch_dir != ""

            if self.parent.alert_handler.current_alert_type == "long_blinked":
                return texts["alert_message_blink"].format(self.parent.alert_handler.blink_duration)
            elif self.parent.alert_handler.current_alert_type == "blink_anomaly":
                return texts["alert_message_blink_anomaly"].format(blink_rate)

            if is_eyes_closed and is_roll_exceeded and is_pitch_exceeded:
                direction_text = f"{roll_dir} و {pitch_dir}" if self.parent.language == "fa" else f"{roll_dir} and {pitch_dir}"
                return texts["alert_message_eyes_and_head_both"].format(direction_text)
            elif is_eyes_closed and is_roll_exceeded:
                opposite_roll = texts["left"] if roll_dir == "right" else texts["right"]
                return texts["alert_message_eyes_and_roll"].format(opposite_roll)
            elif is_eyes_closed and is_pitch_exceeded:
                opposite_pitch = texts["forward"] if pitch_dir == "back" else texts["back"]
                return texts["alert_message_eyes_and_pitch"].format(opposite_pitch)
            elif is_eyes_closed:
                return texts["alert_message_sleep"]
            elif is_roll_exceeded and is_pitch_exceeded:
                direction_text = f"{roll_dir} و {pitch_dir}" if self.parent.language == "fa" else f"{roll_dir} and {pitch_dir}"
                return texts["alert_message_head_both"].format(direction_text)
            elif is_roll_exceeded:
                opposite_roll = texts["left"] if roll_dir == "right" else texts["right"]
                return texts["alert_message_roll"].format(opposite_roll)
            elif is_pitch_exceeded:
                opposite_pitch = texts["forward"] if pitch_dir == "back" else texts["back"]
                return texts["alert_message_pitch"].format(opposite_pitch)
            return None
        except Exception as e:
            logging.error(f"Error generating alert message: {e}")
            return None

    def cleanup(self):
        try:
            self.is_running = False
            self.cap.release()
            self.thread_pool.shutdown(wait=True)
            self.face_mesh.close()
        except Exception as e:
            logging.error(f"Error cleaning up frame processor: {e}")