import asyncio
import platform
import cv2
import numpy as np
import mediapipe as mp
import time
import math
import pygame
import random
import os

try:
    pygame.mixer.init()
    MIXER_READY = True
except pygame.error:
    MIXER_READY = False

class VirtualKeyboard:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_face_mesh = mp.solutions.face_mesh
        self.hands = self.mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7, max_num_hands=2)
        self.face_mesh = self.mp_face_mesh.FaceMesh(max_num_faces=1, min_detection_confidence=0.5, min_tracking_confidence=0.5)
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        self.layouts = {
            "QWERTY": [
                ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
                ["A", "S", "D", "F", "G", "H", "J", "K", "L"],
                ["Z", "X", "C", "V", "B", "N", "M", ",", ".", "/", "Backspace"],
                ["Space", "Enter", "Theme", "Layout", "Size+", "Size-", "Game", "Draw", "Meme"]
            ],
            "AZERTY": [
                ["A", "Z", "E", "R", "T", "Y", "U", "I", "O", "P"],
                ["Q", "S", "D", "F", "G", "H", "J", "K", "L", "M"],
                ["W", "X", "C", "V", "B", "N", ",", ".", "/", "Backspace"],
                ["Space", "Enter", "Theme", "Layout", "Size+", "Size-", "Game", "Draw", "Meme"]
            ],
            "INDONESIA": [
                ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
                ["A", "S", "D", "F", "G", "H", "J", "K", "L"],
                ["Z", "X", "C", "V", "B", "N", "M", ",", ".", "/", "Backspace"],
                ["Space", "Enter", "Theme", "Layout", "Size+", "Size-", "Game", "Draw", "Meme"]
            ]
        }
        self.current_layout = "QWERTY"
        self.current_theme = "default"
        self.themes = {
            "default": {
                "bg_color": (50, 50, 50),
                "key_color": (100, 100, 100),
                "key_pressed": (0, 255, 0),
                "key_hover": (150, 150, 150),
                "text_color": (255, 255, 255),
                "text_active": (0, 255, 0),
                "border_color": (255, 255, 255)
            },
            "dark": {
                "bg_color": (20, 20, 20),
                "key_color": (60, 60, 60),
                "key_pressed": (255, 0, 255),
                "key_hover": (80, 80, 80),
                "text_color": (200, 200, 200),
                "text_active": (255, 0, 255),
                "border_color": (100, 100, 100)
            },
            "neon": {
                "bg_color": (10, 10, 30),
                "key_color": (30, 30, 80),
                "key_pressed": (0, 255, 255),
                "key_hover": (50, 50, 100),
                "text_color": (0, 255, 255),
                "text_active": (255, 255, 0),
                "border_color": (0, 255, 255)
            },
            "nature": {
                "bg_color": (34, 139, 34),
                "key_color": (85, 107, 47),
                "key_pressed": (255, 215, 0),
                "key_hover": (107, 142, 35),
                "text_color": (255, 255, 255),
                "text_active": (255, 215, 0),
                "border_color": (255, 255, 255)
            }
        }
        self.key_width = 70
        self.key_height = 70
        self.key_start_x = 50
        self.key_start_y = 50
        self.spacing = 10
        self.scale_factor = 1.0
        self.key_animations = {}
        self.animation_duration = 0.3
        self.typed_text = ""
        self.pressed_time = {"left": 0, "right": 0}
        self.last_pressed = {"left": "", "right": ""}
        self.show_keyboard = False
        self.show_threshold = 120
        self.hide_threshold = 100
        self.keyboard_offset_x = 0
        self.keyboard_offset_y = 0
        self.follow_hand = False
        self.game_mode = False
        self.current_game = None
        self.games = {
            "pong": PongGame(),
            "brick": BrickBreakerGame(),
            "catch": CatchGame(),
            "snake": SnakeGame(),
            "mole": WhackAMoleGame(),
            "balloon": BalloonPopGame(),
            "flappy": FlappyBirdGame(),
            "dodge": DodgeGame(),
            "shooter": SpaceShooterGame()
        }
        self.draw_mode = False
        self.drawing_canvas = None
        self.current_color = (255, 255, 255)
        self.colors = [
            (255, 255, 255),
            (255, 0, 0),
            (0, 255, 0),
            (0, 0, 255),
            (255, 255, 0),
            (255, 0, 255),
            (0, 255, 255)
        ]
        self.brush_size = 5
        self.last_point = None
        self.hand_landmarks = None
        self.meme_mode = False
        self.meme_paths = {
            "THUMBS_UP": "thumbs_up.jpg",
            "POINTING": "pointing.jpg",
            "THINKING": "thinking.jpg",
            "NEUTRAL": "neutral.jpg"
        }
        self.meme_images = {}
        self.meme_current = "NEUTRAL"
        self.meme_pending = "NEUTRAL"
        self.meme_last_change = time.time()
        self.meme_hold_seconds = 0.25
        self.meme_image_height = None
        self.meme_image_max_width = None
        self.meme_width_fraction = 0.35
        self.create_sound_effects()

    def create_sound_effects(self):
        if not MIXER_READY:
            self.key_sound = None
            return
        try:
            sample_rate = 22050
            duration = 0.1
            frequency = 800
            frames = int(duration * sample_rate)
            arr = np.zeros(frames)
            for i in range(frames):
                arr[i] = np.sin(2 * np.pi * frequency * i / sample_rate)
            arr = (arr * 32767).astype(np.int16)
            stereo_arr = np.zeros((frames, 2), dtype=np.int16)
            stereo_arr[:, 0] = arr
            stereo_arr[:, 1] = arr
            self.key_sound = pygame.sndarray.make_sound(stereo_arr)
            self.key_sound.set_volume(0.3)
        except Exception:
            self.key_sound = None

    def play_key_sound(self):
        if self.key_sound:
            try:
                self.key_sound.play()
            except:
                pass

    def get_current_theme(self):
        return self.themes[self.current_theme]

    def switch_theme(self):
        theme_names = list(self.themes.keys())
        current_index = theme_names.index(self.current_theme)
        self.current_theme = theme_names[(current_index + 1) % len(theme_names)]

    def switch_layout(self):
        layout_names = list(self.layouts.keys())
        current_index = layout_names.index(self.current_layout)
        self.current_layout = layout_names[(current_index + 1) % len(layout_names)]

    def adjust_size(self, increase=True):
        self.scale_factor = min(2.0, self.scale_factor + 0.1) if increase else max(0.5, self.scale_factor - 0.1)
        self.key_width = int(70 * self.scale_factor)
        self.key_height = int(70 * self.scale_factor)
        self.spacing = int(10 * self.scale_factor)

    def toggle_game_mode(self):
        self.game_mode = not self.game_mode
        self.current_game = "menu" if self.game_mode else None
        self.draw_mode = False
        self.meme_mode = False

    def toggle_draw_mode(self):
        self.draw_mode = not self.draw_mode
        self.game_mode = False
        self.meme_mode = False
        if self.draw_mode:
            h, w = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)), int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.drawing_canvas = np.zeros((h, w, 3), dtype=np.uint8)
            self.last_point = None
        else:
            self.drawing_canvas = None

    def toggle_meme_mode(self):
        self.meme_mode = not self.meme_mode
        if self.meme_mode:
            self.draw_mode = False
            self.game_mode = False
            self.show_keyboard = False
            self.typed_text = ""
        else:
            self.meme_current = "NEUTRAL"
            self.meme_pending = "NEUTRAL"

    def get_curved_position(self, base_x, base_y, hand_center, curve_intensity=0.3):
        if hand_center is None:
            return base_x, base_y
        distance = np.sqrt((base_x - hand_center[0])**2 + (base_y - hand_center[1])**2)
        curve_offset_x = (base_x - hand_center[0]) * curve_intensity * (distance / 200)
        curve_offset_y = (base_y - hand_center[1]) * curve_intensity * (distance / 200)
        return int(base_x + curve_offset_x), int(base_y + curve_offset_y)

    def animate_key_press(self, key, start_time):
        animation = self.key_animations.get(key, {})
        start = animation.get("start_time", start_time)
        animation["start_time"] = start
        elapsed = time.time() - start
        if elapsed < self.animation_duration:
            animation["pulse"] = abs(math.sin(elapsed * 10))
            animation["active"] = True
            self.key_animations[key] = animation
        else:
            self.key_animations.pop(key, None)

    def is_finger_touching(self, x, y, button_x, button_y, button_width, button_height):
        return button_x < x < button_x + button_width and button_y < y < button_y + button_height

    def handle_special_keys(self, key):
        if key == "Backspace":
            self.typed_text = self.typed_text[:-1]
        elif key == "Enter":
            self.typed_text = ""
        elif key == "Space":
            self.typed_text += " "
        elif key == "Theme":
            self.switch_theme()
        elif key == "Layout":
            self.switch_layout()
        elif key == "Size+":
            self.adjust_size(True)
        elif key == "Size-":
            self.adjust_size(False)
        elif key == "Game":
            self.toggle_game_mode()
        elif key == "Draw":
            self.toggle_draw_mode()
        elif key == "Meme":
            self.toggle_meme_mode()

    def get_text_size(self, text, font=cv2.FONT_HERSHEY_SIMPLEX, font_scale=1, thickness=2):
        return cv2.getTextSize(text, font, font_scale, thickness)[0]

    def calculate_distance(self, point1, point2):
        return np.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)

    def load_meme_images(self, target_height, max_width):
        self.meme_images = {}
        self.meme_image_height = target_height
        self.meme_image_max_width = max_width
        for gesture, filename in self.meme_paths.items():
            path = os.path.join(os.getcwd(), filename)
            img = cv2.imread(path)
            if img is None:
                continue
            ratio_h = target_height / img.shape[0]
            ratio_w = max_width / img.shape[1] if max_width else ratio_h
            scale = min(ratio_h, ratio_w)
            width = max(1, int(img.shape[1] * scale))
            height = max(1, int(img.shape[0] * scale))
            resized = cv2.resize(img, (width, height))
            if height != target_height:
                pad_top = max(0, (target_height - height) // 2)
                pad_bottom = max(0, target_height - height - pad_top)
                resized = cv2.copyMakeBorder(resized, pad_top, pad_bottom, 0, 0, cv2.BORDER_CONSTANT, value=(0, 0, 0))
            self.meme_images[gesture] = resized

    def classify_meme_gesture(self, hand_landmarks):
        y_thumb_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.THUMB_TIP].y
        y_index_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP].y
        y_middle_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP].y
        y_ring_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.RING_FINGER_TIP].y
        y_pinky_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.PINKY_TIP].y
        y_middle_pip = hand_landmarks.landmark[self.mp_hands.HandLandmark.MIDDLE_FINGER_PIP].y
        is_thumb_up = y_thumb_tip < y_middle_pip
        fingers_down = (y_index_tip > y_middle_pip and y_middle_tip > y_middle_pip and y_ring_tip > y_middle_pip and y_pinky_tip > y_middle_pip)
        if is_thumb_up and fingers_down:
            return "THUMBS_UP"
        index_up = y_index_tip < y_middle_pip
        others_down = (y_middle_tip > y_middle_pip and y_ring_tip > y_middle_pip and y_pinky_tip > y_middle_pip)
        thumb_down = y_thumb_tip > y_middle_pip
        if index_up and others_down and thumb_down:
            return "POINTING"
        return "NEUTRAL"

    def is_thinking_gesture(self, hand_landmarks, face_landmarks, frame_width, frame_height):
        if not hand_landmarks or not face_landmarks:
            return False
        index_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
        nose_tip = face_landmarks.landmark[4]
        index_x = int(index_tip.x * frame_width)
        index_y = int(index_tip.y * frame_height)
        nose_x = int(nose_tip.x * frame_width)
        nose_y = int(nose_tip.y * frame_height)
        distance = math.hypot(index_x - nose_x, index_y - nose_y)
        max_distance = 50
        y_middle_pip = hand_landmarks.landmark[self.mp_hands.HandLandmark.MIDDLE_FINGER_PIP].y
        y_middle_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP].y
        is_middle_down = y_middle_tip > y_middle_pip
        return distance < max_distance and is_middle_down

    def update_meme_state(self, predicted):
        now = time.time()
        if predicted != self.meme_current:
            if predicted != self.meme_pending:
                self.meme_pending = predicted
                self.meme_last_change = now
            elif now - self.meme_last_change >= self.meme_hold_seconds:
                self.meme_current = predicted
        else:
            self.meme_pending = self.meme_current
            self.meme_last_change = now

    def get_meme_image(self, target_height, frame_width):
        max_width = int(frame_width * self.meme_width_fraction)
        if (not self.meme_images or
                self.meme_image_height != target_height or
                self.meme_image_max_width != max_width):
            self.load_meme_images(target_height, max_width)
        return self.meme_images.get(self.meme_current)

    def get_game_score(self):
        if not self.game_mode or self.current_game in (None, "menu"):
            return None
        game = self.games.get(self.current_game)
        if game and hasattr(game, "score"):
            return game.score
        return None

    def get_game_instructions(self):
        tips = {
            "pong": "Pong: Gerak paddle dengan jari, pantulkan bola, capai 10 poin untuk WIN.",
            "brick": "Brick Breaker: Gerak paddle, pantulkan bola, hancurkan semua brick sebelum nyawa habis.",
            "catch": "Catch: Gerak keranjang, tangkap bola jatuh, hindari miss, 10 poin untuk WIN.",
            "snake": "Snake: Arahkan kepala ular dengan jari, makan makanan, jangan tabrak dinding/tubuh, skor 10 menang.",
            "mole": "Whack A Mole: Ketuk mole yang muncul, 10 hit untuk menang.",
            "balloon": "Balloon Pop: Pecahkan balon yang naik; 10 balon pecah menang.",
            "flappy": "Flappy: Buka jari (lebih lebar) untuk flap, lewati pipa, skor 10 menang.",
            "dodge": "Dodge: Geser kiri-kanan hindari meteor, kumpulkan 20 lolos untuk menang.",
            "shooter": "Space Shooter: Geser pesawat kiri-kanan, laser auto menembak meteor, 12 poin menang."
        }
        return tips.get(self.current_game, "Pilih game, lalu ikuti instruksi di layar.")

    def draw_finish_button(self, overlay, finger_pos, game_area):
        theme = self.get_current_theme()
        button_x, button_y = game_area[2] - 100, game_area[1] + 10
        button_width, button_height = 80, 40
        is_touching = finger_pos and self.is_finger_touching(finger_pos[0], finger_pos[1], button_x, button_y, button_width, button_height)
        btn_color = theme["key_hover"] if is_touching else theme["key_color"]
        cv2.rectangle(overlay, (button_x, button_y), (button_x + button_width, button_y + button_height), btn_color, -1)
        cv2.rectangle(overlay, (button_x, button_y), (button_x + button_width, button_y + button_height), theme["border_color"], 2)
        text_size = self.get_text_size("Finish", font_scale=0.5)
        text_x = button_x + (button_width - text_size[0]) // 2
        text_y = button_y + (button_height + text_size[1]) // 2
        cv2.putText(overlay, "Finish", (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, theme["text_color"], 2)
        if is_touching and hasattr(self, 'finish_button_timer'):
            if time.time() - self.finish_button_timer > 1.0:
                self.current_game = "menu"
                self.finish_button_timer = 0
        elif is_touching:
            self.finish_button_timer = time.time()
        return overlay

    def draw_game_menu(self, overlay, finger_pos=None):
        theme = self.get_current_theme()
        menu_x, menu_y, menu_width, menu_height = 200, 100, 600, 400
        cv2.rectangle(overlay, (menu_x, menu_y), (menu_x + menu_width, menu_y + menu_height), theme["bg_color"], -1)
        cv2.rectangle(overlay, (menu_x, menu_y), (menu_x + menu_width, menu_y + menu_height), theme["border_color"], 3)
        title = "MINI GAMES"
        title_size = self.get_text_size(title, font_scale=1.2, thickness=3)
        title_x = menu_x + (menu_width - title_size[0]) // 2
        cv2.putText(overlay, title, (title_x, menu_y + 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, theme["text_active"], 3)
        games_list = [
            ("Pong", "pong"),
            ("Brick Breaker", "brick"),
            ("Catch Balls", "catch"),
            ("Snake", "snake"),
            ("Whack A Mole", "mole"),
            ("Balloon Pop", "balloon"),
            ("Flappy Bird", "flappy"),
            ("Dodge Meteors", "dodge"),
            ("Space Shooter", "shooter"),
            ("Back", "back")
        ]
        button_width, button_height = 120, 40
        cols = 3
        start_x = menu_x + 50
        start_y = menu_y + 100
        for i, (name, game_id) in enumerate(games_list):
            row = i // cols
            col = i % cols
            btn_x = start_x + col * (button_width + 20)
            btn_y = start_y + row * (button_height + 20)
            is_touching = finger_pos and self.is_finger_touching(finger_pos[0], finger_pos[1], btn_x, btn_y, button_width, button_height)
            btn_color = theme["key_hover"] if is_touching else theme["key_color"]
            cv2.rectangle(overlay, (btn_x, btn_y), (btn_x + button_width, btn_y + button_height), btn_color, -1)
            cv2.rectangle(overlay, (btn_x, btn_y), (btn_x + button_width, btn_y + button_height), theme["border_color"], 2)
            text_size = self.get_text_size(name, font_scale=0.5)
            text_x = btn_x + (button_width - text_size[0]) // 2
            text_y = btn_y + (button_height + text_size[1]) // 2
            cv2.putText(overlay, name, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, theme["text_color"], 2)
            if is_touching and hasattr(self, 'game_selection_timer'):
                if time.time() - self.game_selection_timer > 1.0:
                    if game_id == "back":
                        self.game_mode = False
                        self.current_game = None
                    else:
                        self.current_game = game_id
                        self.games[game_id].reset()
                    self.game_selection_timer = 0
            elif is_touching:
                self.game_selection_timer = time.time()
        return overlay

    def draw_color_picker(self, overlay, finger_pos):
        theme = self.get_current_theme()
        draw_area = (200, 100, 600, 400)
        button_width, button_height = 50, 50
        start_x = draw_area[0] + 50
        start_y = draw_area[1] + 100
        for i, color in enumerate(self.colors):
            col = i % 4
            row = i // 4
            btn_x = start_x + col * (button_width + 20)
            btn_y = start_y + row * (button_height + 20)
            is_touching = finger_pos and self.is_finger_touching(finger_pos[0], finger_pos[1], btn_x, btn_y, button_width, button_height)
            cv2.rectangle(overlay, (btn_x, btn_y), (btn_x + button_width, btn_y + button_height), color, -1)
            cv2.rectangle(overlay, (btn_x, btn_y), (btn_x + button_width, btn_y + button_height), theme["border_color"], 2)
            if is_touching and hasattr(self, 'color_selection_timer'):
                if time.time() - self.color_selection_timer > 0.5:
                    self.current_color = color
                    self.color_selection_timer = 0
            elif is_touching:
                self.color_selection_timer = time.time()
        exit_x, exit_y = draw_area[2] - 100, draw_area[1] + 10
        is_touching_exit = finger_pos and self.is_finger_touching(finger_pos[0], finger_pos[1], exit_x, exit_y, 80, 40)
        btn_color = theme["key_hover"] if is_touching_exit else theme["key_color"]
        cv2.rectangle(overlay, (exit_x, exit_y), (exit_x + 80, exit_y + 40), btn_color, -1)
        cv2.rectangle(overlay, (exit_x, exit_y), (exit_x + 80, exit_y + 40), theme["border_color"], 2)
        text_size = self.get_text_size("Exit", font_scale=0.5)
        text_x = exit_x + (80 - text_size[0]) // 2
        text_y = exit_y + (40 + text_size[1]) // 2
        cv2.putText(overlay, "Exit", (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, theme["text_color"], 2)
        if is_touching_exit and hasattr(self, 'exit_button_timer'):
            if time.time() - self.exit_button_timer > 1.0:
                self.toggle_draw_mode()
                self.exit_button_timer = 0
        elif is_touching_exit:
            self.exit_button_timer = time.time()
        cv2.rectangle(overlay, (draw_area[0] + 50, draw_area[1] + 50), (draw_area[0] + 100, draw_area[1] + 80), self.current_color, -1)
        cv2.rectangle(overlay, (draw_area[0] + 50, draw_area[1] + 50), (draw_area[0] + 100, draw_area[1] + 80), theme["border_color"], 2)
        return overlay

    def draw_keyboard(self, overlay, hand_center=None):
        theme = self.get_current_theme()
        keys = self.layouts[self.current_layout]
        for row_idx, row in enumerate(keys):
            for coll_idx, key in enumerate(row):
                base_x = self.key_start_x + self.keyboard_offset_x + coll_idx * (self.key_width + self.spacing)
                base_y = self.key_start_y + self.keyboard_offset_y + row_idx * (self.key_height + self.spacing)
                x, y = self.get_curved_position(base_x, base_y, hand_center) if self.follow_hand and hand_center else (base_x, base_y)
                key_color = theme["key_color"]
                if key in self.key_animations:
                    pulse = self.key_animations[key]['pulse']
                    key_color = tuple(int(c + (255 - c) * pulse * 0.5) for c in theme["key_pressed"])
                cv2.rectangle(overlay, (x, y), (x + self.key_width, y + self.key_height), key_color, -1)
                cv2.rectangle(overlay, (x, y), (x + self.key_width, y + self.key_height), theme["border_color"], 2)
                if self.current_theme == "neon":
                    glow_overlay = overlay.copy()
                    cv2.rectangle(glow_overlay, (x-2, y-2), (x + self.key_width+2, y + self.key_height+2), theme["border_color"], -1)
                    overlay = cv2.addWeighted(overlay, 0.9, glow_overlay, 0.1, 0)
                font_scale = 0.6 * self.scale_factor
                text_size = self.get_text_size(key, font_scale=font_scale)
                text_width, text_height = text_size
                text_x = x + (self.key_width - text_width) // 2
                text_y = y + (self.key_height + text_height) // 2
                if text_width > self.key_width - 10:
                    font_scale = 0.4 * self.scale_factor
                    text_size = self.get_text_size(key, font_scale=font_scale)
                    text_width, text_height = text_size
                    text_x = x + (self.key_width - text_width) // 2
                    text_y = y + (self.key_height + text_height) // 2
                text_color = theme["text_active"] if key in self.key_animations else theme["text_color"]
                cv2.putText(overlay, key, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_color, 2)
        return overlay

    def process_finger_input(self, overlay, x, y, hand_label, hand_center):
        theme = self.get_current_theme()
        keys = self.layouts[self.current_layout]
        for row_idx, row in enumerate(keys):
            for coll_idx, key in enumerate(row):
                base_x = self.key_start_x + self.keyboard_offset_x + coll_idx * (self.key_width + self.spacing)
                base_y = self.key_start_y + self.keyboard_offset_y + row_idx * (self.key_height + self.spacing)
                key_x, key_y = self.get_curved_position(base_x, base_y, hand_center) if self.follow_hand and hand_center else (base_x, base_y)
                if self.is_finger_touching(x, y, key_x, key_y, self.key_width, self.key_height):
                    cv2.rectangle(overlay, (key_x, key_y), (key_x + self.key_width, key_y + self.key_height), theme["key_hover"], -1)
                    font_scale = 0.6 * self.scale_factor
                    text_size = self.get_text_size(key, font_scale=font_scale)
                    text_width, text_height = text_size
                    text_x = key_x + (self.key_width - text_width) // 2
                    text_y = key_y + (self.key_height + text_height) // 2
                    if text_width > self.key_width - 10:
                        font_scale = 0.4 * self.scale_factor
                        text_size = self.get_text_size(key, font_scale=font_scale)
                        text_width, text_height = text_size
                        text_x = key_x + (self.key_width - text_width) // 2
                        text_y = key_y + (self.key_height + text_height) // 2
                    cv2.putText(overlay, key, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), 2)
                    if self.last_pressed[hand_label] != key:
                        self.pressed_time[hand_label] = time.time()
                        self.last_pressed[hand_label] = key
                    elif time.time() - self.pressed_time[hand_label] > 0.6:
                        self.key_animations[key] = {'pulse': 1.0, 'active': True, 'start_time': time.time()}
                        self.play_key_sound()
                        if key in ["Backspace", "Enter", "Space", "Theme", "Layout", "Size+", "Size-", "Game", "Draw"]:
                            self.handle_special_keys(key)
                        else:
                            self.typed_text += key
                        self.last_pressed[hand_label] = ""
                        self.animate_key_press(key, time.time())
        return overlay

    def process_drawing(self, overlay, finger_pos):
        if finger_pos and self.drawing_canvas is not None:
            current_point = finger_pos
            if self.last_point is not None:
                cv2.line(self.drawing_canvas, self.last_point, current_point, self.current_color, self.brush_size)
            self.last_point = current_point
            overlay = cv2.addWeighted(overlay, 0.8, self.drawing_canvas, 0.5, 0)
        return overlay

    def draw_text_display(self, overlay):
        if self.typed_text:
            theme = self.get_current_theme()
            text_x = 50 + self.keyboard_offset_x
            text_y = self.key_start_y + self.keyboard_offset_y + len(self.layouts[self.current_layout]) * (self.key_height + self.spacing) + 50
            font_scale = 1.5 * self.scale_factor
            text_size = self.get_text_size(self.typed_text, font_scale=font_scale, thickness=3)
            text_width, text_height = text_size
            cv2.rectangle(overlay, (text_x - 10, text_y - text_height - 10), (text_x + text_width + 10, text_y + 10), theme["bg_color"], -1)
            cv2.rectangle(overlay, (text_x - 10, text_y - text_height - 10), (text_x + text_width + 10, text_y + 10), theme["border_color"], 2)
            cv2.putText(overlay, self.typed_text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, theme["text_active"], 3)

    def draw_info_panel(self, overlay):
        theme = self.get_current_theme()
        if self.draw_mode:
            info_text = "DRAW MODE - Use finger to draw, select color, or exit"
        elif self.game_mode:
            score = self.get_game_score()
            score_text = f" | Score: {score}" if score is not None else ""
            info_text = f"GAME MODE - {self.current_game if self.current_game else 'Menu'}{score_text}"
        elif self.meme_mode:
            info_text = f"MEME MODE - Gesture: {self.meme_current.replace('_', ' ')}"
        else:
            info_text = f"Layout: {self.current_layout} | Theme: {self.current_theme} | Scale: {self.scale_factor:.1f}x"
        cv2.putText(overlay, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, theme["text_color"], 2)
        if self.game_mode and self.current_game and self.current_game != "menu":
            instructions = self.get_game_instructions()
        elif self.game_mode:
            instructions = "Menu game: pilih level & game dengan menunjuk."
        elif self.draw_mode:
            instructions = "Point to draw or select color | Exit to return"
        elif self.meme_mode:
            instructions = "Meme: thumbs up / pointing / thinking (jari ke hidung) / netral | tekan 'm' untuk toggle"
        else:
            instructions = "Spread fingers to show keyboard | Point to type | Game or Draw button"
        cv2.putText(overlay, instructions, (10, overlay.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, theme["text_color"], 1)
        credit_text = "Created by Riani Destanti, Fullstack Developer at Sobat Teknologi"
        credit_scale = 0.5
        credit_thickness = 1
        credit_size = self.get_text_size(credit_text, font_scale=credit_scale, thickness=credit_thickness)
        padding = 8
        extra_left = 10
        box_w = credit_size[0] + padding * 2 + extra_left
        box_h = credit_size[1] + padding * 2
        margin = 10
        credit_x = max(margin, overlay.shape[1] - box_w - margin)
        credit_y = overlay.shape[0] - box_h - margin
        shadow_offset = 3
        box_color = tuple(min(255, c + 40) for c in theme["bg_color"])
        shadow_color = (0, 0, 0)
        border_color = theme["border_color"]
        cv2.rectangle(overlay, (credit_x + shadow_offset, credit_y + shadow_offset), (credit_x + box_w + shadow_offset, credit_y + box_h + shadow_offset), shadow_color, -1)
        cv2.rectangle(overlay, (credit_x, credit_y), (credit_x + box_w, credit_y + box_h), box_color, -1)
        cv2.rectangle(overlay, (credit_x, credit_y), (credit_x + box_w, credit_y + box_h), border_color, 1)
        accent_x = credit_x + 6
        accent_width = 4
        accent_color = (0, 0, 255)
        cv2.rectangle(overlay, (accent_x, credit_y + 4), (accent_x + accent_width, credit_y + box_h - 4), accent_color, -1)
        text_x = credit_x + padding + extra_left
        text_y = credit_y + box_h - padding - 2
        cv2.putText(overlay, credit_text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, credit_scale, theme["text_color"], credit_thickness, cv2.LINE_AA)

    async def run(self):
        while self.cap.isOpened():
            success, frame = self.cap.read()
            if not success:
                break
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(rgb_frame)
            face_results = self.face_mesh.process(rgb_frame) if self.meme_mode else None
            overlay = frame.copy()
            hand_center = None
            finger_pos = None
            primary_hand = None
            if results.multi_hand_landmarks:
                for hand_idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                    if primary_hand is None:
                        primary_hand = hand_landmarks
                    hand_label = results.multi_handedness[hand_idx].classification[0].label.lower()
                    self.mp_drawing.draw_landmarks(overlay, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                    thumb_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.THUMB_TIP]
                    pinky_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.PINKY_TIP]
                    index_finger_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
                    thumb_x, thumb_y = int(thumb_tip.x * w), int(thumb_tip.y * h)
                    pinky_x, pinky_y = int(pinky_tip.x * w), int(pinky_tip.y * h)
                    hand_center = ((thumb_x + pinky_x) // 2, (thumb_y + pinky_y) // 2)
                    finger_pos = (int(index_finger_tip.x * w), int(index_finger_tip.y * h))
                    cv2.circle(overlay, finger_pos, 8, (0, 255, 0), -1)
                    if not self.game_mode and not self.draw_mode and not self.meme_mode:
                        distance = self.calculate_distance((thumb_x, thumb_y), (pinky_x, pinky_y))
                        self.show_keyboard = distance > self.show_threshold
                        if distance < self.hide_threshold:
                            self.show_keyboard = False
                        if self.show_keyboard:
                            overlay = self.process_finger_input(overlay, finger_pos[0], finger_pos[1], hand_label, hand_center)
                    elif self.draw_mode:
                        overlay = self.process_drawing(overlay, finger_pos)
                    if self.game_mode and self.current_game in self.games:
                        self.games[self.current_game].hand_landmarks = hand_landmarks
                        self.games[self.current_game].mp_hands = self.mp_hands
            face_landmarks = face_results.multi_face_landmarks[0] if face_results and face_results.multi_face_landmarks else None
            meme_image = None
            if self.meme_mode:
                predicted = "NEUTRAL"
                if primary_hand and face_landmarks and self.is_thinking_gesture(primary_hand, face_landmarks, w, h):
                    predicted = "THINKING"
                elif primary_hand:
                    predicted = self.classify_meme_gesture(primary_hand)
                self.update_meme_state(predicted)
                meme_image = self.get_meme_image(h, w)
            if self.draw_mode:
                overlay = self.draw_color_picker(overlay, finger_pos)
                if self.drawing_canvas is not None:
                    overlay = cv2.addWeighted(overlay, 0.8, self.drawing_canvas, 0.5, 0)
            elif self.game_mode:
                if self.current_game == "menu":
                    overlay = self.draw_game_menu(overlay, finger_pos)
                elif self.current_game in self.games:
                    overlay = self.games[self.current_game].update(overlay, finger_pos, self.typed_text)
                    overlay = self.draw_finish_button(overlay, finger_pos, self.games[self.current_game].game_area)
            else:
                if self.show_keyboard and not self.meme_mode:
                    overlay = self.draw_keyboard(overlay, hand_center)
                if not self.meme_mode:
                    self.draw_text_display(overlay)
            self.draw_info_panel(overlay)
            for key in list(self.key_animations.keys()):
                self.animate_key_press(key, time.time() - 0.1)
                if key not in self.key_animations:
                    self.key_animations.pop(key, None)
            display_frame = cv2.addWeighted(overlay, 0.8, frame, 0.2, 0)
            if self.meme_mode:
                if meme_image is not None:
                    target_w = max(80, int(display_frame.shape[1] * self.meme_width_fraction))
                    meme_scaled = cv2.resize(meme_image, (target_w, display_frame.shape[0]))
                    x1 = display_frame.shape[1] - target_w
                    x2 = display_frame.shape[1]
                    display_frame[:, x1:x2] = meme_scaled
                    cv2.rectangle(display_frame, (x1, 0), (x2 - 1, display_frame.shape[0] - 1), (255, 255, 255), 2)
                else:
                    cv2.putText(display_frame, "Meme image missing - check JPG files", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.imshow('Virtual Keyboard', display_frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('g'):
                self.toggle_game_mode()
            elif key == ord('d'):
                self.toggle_draw_mode()
            elif key == ord('m'):
                self.toggle_meme_mode()
            await asyncio.sleep(1.0 / 60)  
        self.cap.release()
        cv2.destroyAllWindows()
        self.face_mesh.close()
        pygame.mixer.quit()


class WinCelebration:
    """Shared 10s win effect with confetti, glow, and rays."""

    def __init__(self, duration=10.0):
        self.duration = duration
        self.active = False
        self.start_time = 0.0
        self.confetti = []
        self.center = (0, 0)

    def reset(self):
        self.active = False
        self.confetti = []

    def is_active(self):
        return self.active and (time.time() - self.start_time) < self.duration

    def _spawn_confetti(self, w, h):
        self.confetti = []
        for _ in range(140):
            self.confetti.append({
                "pos": [random.randint(0, w), random.randint(-h // 3, h // 4)],
                "vel": [random.uniform(-1.2, 1.2), random.uniform(3.5, 6.5)],
                "color": (
                    random.randint(140, 255),
                    random.randint(120, 255),
                    random.randint(140, 255)
                ),
                "size": random.randint(6, 12)
            })

    def start(self, overlay):
        h, w = overlay.shape[:2]
        self.center = (w // 2, h // 2)
        self._spawn_confetti(w, h)
        self.start_time = time.time()
        self.active = True

    def draw(self, overlay, label="YOU WIN!", subtitle="Nikmati konfeti 10 detik"):
        if not self.is_active():
            self.reset()
            return overlay
        progress = (time.time() - self.start_time) / self.duration
        h, w = overlay.shape[:2]
        fx_layer = overlay.copy()
        pulse = 0.5 + 0.5 * math.sin(progress * math.pi * 2)
        glow_radius = int(max(w, h) * (0.25 + 0.25 * pulse))
        cv2.circle(fx_layer, self.center, glow_radius, (255, 255, 255), -1)
        ring_radius = int(max(w, h) * (0.15 + progress * 0.35))
        cv2.circle(fx_layer, self.center, ring_radius, (255, 215, 0), 6)
        for c in self.confetti:
            c["pos"][0] += c["vel"][0] + math.sin(progress * 8 + c["pos"][1] * 0.02)
            c["pos"][1] += c["vel"][1]
            if c["pos"][1] > h + 20:
                c["pos"][0] = random.randint(0, w)
                c["pos"][1] = random.randint(-h // 5, 0)
            cv2.circle(fx_layer, (int(c["pos"][0]), int(c["pos"][1])), c["size"], c["color"], -1)
        beams = 24
        for i in range(beams):
            angle = (i / beams) * math.tau
            length = int((0.35 + 0.4 * pulse) * max(w, h))
            end_x = int(self.center[0] + math.cos(angle) * length)
            end_y = int(self.center[1] + math.sin(angle) * length)
            cv2.line(fx_layer, self.center, (end_x, end_y), (255, 255, 255), 2)
        overlay = cv2.addWeighted(overlay, 0.55, fx_layer, 0.45, 0)
        text_scale = 1.8
        text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, text_scale, 4)[0]
        text_x = self.center[0] - text_size[0] // 2
        text_y = self.center[1] - text_size[1] // 2
        cv2.putText(overlay, label, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, text_scale, (0, 0, 0), 10)
        cv2.putText(overlay, label, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, text_scale, (0, 255, 255), 4)
        sub_scale = 0.9
        sub_size = cv2.getTextSize(subtitle, cv2.FONT_HERSHEY_SIMPLEX, sub_scale, 2)[0]
        sub_x = self.center[0] - sub_size[0] // 2
        sub_y = text_y + 60
        cv2.putText(overlay, subtitle, (sub_x, sub_y), cv2.FONT_HERSHEY_SIMPLEX, sub_scale, (0, 0, 0), 6)
        cv2.putText(overlay, subtitle, (sub_x, sub_y), cv2.FONT_HERSHEY_SIMPLEX, sub_scale, (50, 220, 255), 2)
        timer_left = max(0, int(self.duration - (time.time() - self.start_time)))
        cv2.putText(overlay, f"Auto reset {timer_left}s", (self.center[0] - 120, sub_y + 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        return overlay


class PongGame:
    def __init__(self):
        self.game_area = (100, 100, 700, 500)
        self.win_fx = WinCelebration()
        self.win = False
        self.reset()
        self.hand_landmarks = None
        self.mp_hands = None

    def reset(self):
        self.win = False
        self.win_fx.reset()
        self.paddle_y = 300
        self.ball_x = 400
        self.ball_y = 300
        self.ball_dx = 5
        self.ball_dy = 3
        self.score = 0
        self.paddle_width = 20
        self.paddle_height = 100
        self.ball_size = 15

    def update(self, overlay, finger_pos, typed_text=""):
        if self.win:
            self.draw(overlay)
            overlay = self.win_fx.draw(overlay, label="PONG WIN!", subtitle="Konfeti 10 detik sebelum restart")
            if not self.win_fx.is_active():
                self.reset()
            return overlay
        if finger_pos:
            self.paddle_y = max(self.game_area[1], min(self.game_area[3] - self.paddle_height, finger_pos[1] - self.paddle_height // 2))
        self.ball_x += self.ball_dx
        self.ball_y += self.ball_dy
        if self.ball_y <= self.game_area[1] or self.ball_y >= self.game_area[3] - self.ball_size:
            self.ball_dy = -self.ball_dy
        if self.ball_x >= self.game_area[2] - self.ball_size:
            self.ball_dx = -self.ball_dx
        if self.ball_x <= self.game_area[0]:
            self.reset()
            return overlay
        paddle_x = self.game_area[0] + 30
        if (self.ball_x <= paddle_x + self.paddle_width and self.ball_x >= paddle_x and
                self.ball_y >= self.paddle_y and self.ball_y <= self.paddle_y + self.paddle_height):
            self.ball_dx = -self.ball_dx
            self.score += 1
            if self.score >= 10 and not self.win:
                self.win = True
                self.win_fx.start(overlay)
        self.draw(overlay)
        return overlay

    def draw(self, overlay):
        cv2.rectangle(overlay, (self.game_area[0], self.game_area[1]), (self.game_area[2], self.game_area[3]), (255, 255, 255), 2)
        paddle_x = self.game_area[0] + 30
        cv2.rectangle(overlay, (paddle_x, self.paddle_y), (paddle_x + self.paddle_width, self.paddle_y + self.paddle_height), (0, 255, 0), -1)
        cv2.circle(overlay, (int(self.ball_x), int(self.ball_y)), self.ball_size, (255, 255, 0), -1)
        cv2.putText(overlay, f"Score: {self.score}", (self.game_area[0], self.game_area[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

class BrickBreakerGame:
    def __init__(self):
        self.game_area = (120, 120, 680, 480)
        self.win_fx = WinCelebration()
        self.hand_landmarks = None
        self.mp_hands = None
        self.paddle_width = 120
        self.paddle_height = 18
        self.ball_radius = 10
        self.base_speed = 5.0
        self.rows = 4
        self.cols = 7
        self.brick_height = 22
        self.brick_padding = 8
        self.brick_top_padding = 16
        self.reset()

    def reset(self):
        self.win = False
        self.win_fx.reset()
        self.score = 0
        self.lives = 3
        self.paddle_x = (self.game_area[0] + self.game_area[2]) // 2 - self.paddle_width // 2
        self.paddle_y = self.game_area[3] - 40
        self.ball_x = float(self.paddle_x + self.paddle_width // 2)
        self.ball_y = float(self.paddle_y - 30)
        self.ball_dx = random.choice([-1, 1]) * self.base_speed
        self.ball_dy = -self.base_speed
        self.bricks = self._build_bricks()

    def _build_bricks(self):
        bricks = []
        left, top, right, _ = self.game_area
        area_width = right - left
        brick_width = int((area_width - (self.cols + 1) * self.brick_padding) / self.cols)
        for row in range(self.rows):
            for col in range(self.cols):
                x1 = left + self.brick_padding + col * (brick_width + self.brick_padding)
                y1 = top + self.brick_top_padding + row * (self.brick_height + self.brick_padding)
                bricks.append({
                    "rect": (x1, y1, x1 + brick_width, y1 + self.brick_height),
                    "color": (random.randint(120, 255), random.randint(150, 255), random.randint(150, 255))
                })
        return bricks

    def _bounce_from_brick(self, brick):
        x1, y1, x2, y2 = brick["rect"]
        overlap_left = self.ball_x + self.ball_radius - x1
        overlap_right = x2 - (self.ball_x - self.ball_radius)
        overlap_top = self.ball_y + self.ball_radius - y1
        overlap_bottom = y2 - (self.ball_y - self.ball_radius)
        min_overlap = min(overlap_left, overlap_right, overlap_top, overlap_bottom)
        if min_overlap in (overlap_left, overlap_right):
            self.ball_dx = -self.ball_dx
        else:
            self.ball_dy = -self.ball_dy

    def _reset_ball(self):
        self.ball_x = self.paddle_x + self.paddle_width // 2
        self.ball_y = self.paddle_y - 30
        self.ball_dx = random.choice([-1, 1]) * self.base_speed
        self.ball_dy = -self.base_speed

    def update(self, overlay, finger_pos, typed_text=""):
        if self.win:
            self.draw(overlay, win=True)
            overlay = self.win_fx.draw(overlay, label="BRICK WIN!", subtitle="Konfeti 10 detik sebelum restart")
            if not self.win_fx.is_active():
                self.reset()
            return overlay
        if finger_pos:
            self.paddle_x = max(self.game_area[0], min(self.game_area[2] - self.paddle_width, finger_pos[0] - self.paddle_width // 2))
        self.ball_x += self.ball_dx
        self.ball_y += self.ball_dy
        left, top, right, bottom = self.game_area
        if self.ball_x - self.ball_radius <= left or self.ball_x + self.ball_radius >= right:
            self.ball_dx = -self.ball_dx
        if self.ball_y - self.ball_radius <= top:
            self.ball_dy = -self.ball_dy
        paddle_x2 = self.paddle_x + self.paddle_width
        if (self.ball_y + self.ball_radius >= self.paddle_y and
                self.ball_y - self.ball_radius <= self.paddle_y + self.paddle_height and
                self.ball_x >= self.paddle_x and self.ball_x <= paddle_x2 and self.ball_dy > 0):
            self.ball_y = self.paddle_y - self.ball_radius
            self.ball_dy = -abs(self.ball_dy)
            offset = (self.ball_x - (self.paddle_x + self.paddle_width / 2)) / (self.paddle_width / 2)
            self.ball_dx = max(-self.base_speed * 1.5, min(self.base_speed * 1.5, self.base_speed * offset * 1.4))
        for brick in self.bricks[:]:
            x1, y1, x2, y2 = brick["rect"]
            if (self.ball_x + self.ball_radius > x1 and self.ball_x - self.ball_radius < x2 and
                    self.ball_y + self.ball_radius > y1 and self.ball_y - self.ball_radius < y2):
                self.bricks.remove(brick)
                self.score += 1
                self._bounce_from_brick(brick)
                break
        if not self.bricks and not self.win:
            self.win = True
            self.win_fx.start(overlay)
        if self.ball_y - self.ball_radius > bottom:
            self.lives -= 1
            if self.lives <= 0:
                self.reset()
                return overlay
            self._reset_ball()
        self.draw(overlay)
        return overlay

    def draw(self, overlay, win=False):
        cv2.rectangle(overlay, (self.game_area[0], self.game_area[1]), (self.game_area[2], self.game_area[3]), (255, 255, 255), 2)
        cv2.rectangle(overlay, (self.paddle_x, self.paddle_y), (self.paddle_x + self.paddle_width, self.paddle_y + self.paddle_height), (120, 200, 255), -1)
        cv2.circle(overlay, (int(self.ball_x), int(self.ball_y)), self.ball_radius, (255, 220, 120), -1)
        for brick in self.bricks:
            x1, y1, x2, y2 = brick["rect"]
            cv2.rectangle(overlay, (x1, y1), (x2, y2), brick["color"], -1)
            cv2.rectangle(overlay, (x1, y1), (x2, y2), (255, 255, 255), 1)
        cv2.putText(overlay, f"Score: {self.score}", (self.game_area[0], self.game_area[1] - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(overlay, f"Nyawa: {self.lives}", (self.game_area[0] + 200, self.game_area[1] - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 200, 200), 2)
        cv2.putText(overlay, "Pindah paddle dengan jari, hancurkan semua brick", (self.game_area[0], self.game_area[3] + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 220, 255), 2)
        if win:
            cv2.putText(overlay, "WIN! Konfeti 10 detik", (self.game_area[0] + 160, self.game_area[1] + 200), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 3)

class CatchGame:
    def __init__(self):
        self.game_area = (100, 100, 700, 500)
        self.win_fx = WinCelebration()
        self.win = False
        self.reset()
        self.hand_landmarks = None
        self.mp_hands = None

    def reset(self):
        self.win = False
        self.win_fx.reset()
        self.basket_x = 400
        self.basket_width = 80
        self.basket_height = 20
        self.balls = []
        self.score = 0
        self.last_spawn = time.time()

    def update(self, overlay, finger_pos, typed_text=""):
        if self.win:
            self.draw(overlay)
            overlay = self.win_fx.draw(overlay, label="CATCH WIN!", subtitle="Konfeti 10 detik sebelum restart")
            if not self.win_fx.is_active():
                self.reset()
            return overlay
        if finger_pos:
            self.basket_x = max(self.game_area[0], min(self.game_area[2] - self.basket_width, finger_pos[0] - self.basket_width // 2))
        if time.time() - self.last_spawn > 1.0:
            self.balls.append({
                'x': random.randint(self.game_area[0] + 20, self.game_area[2] - 20),
                'y': self.game_area[1],
                'speed': random.randint(3, 8),
                'color': (random.randint(100, 255), random.randint(100, 255), random.randint(100, 255))
            })
            self.last_spawn = time.time()
        for ball in self.balls[:]:
            ball['y'] += ball['speed']
            basket_y = self.game_area[3] - 50
            if ball['y'] >= basket_y and ball['x'] >= self.basket_x and ball['x'] <= self.basket_x + self.basket_width:
                self.balls.remove(ball)
                self.score += 1
                if self.score >= 10 and not self.win:
                    self.win = True
                    self.win_fx.start(overlay)
            elif ball['y'] > self.game_area[3]:
                self.balls.remove(ball)
        self.draw(overlay)
        return overlay

    def draw(self, overlay):
        cv2.rectangle(overlay, (self.game_area[0], self.game_area[1]), (self.game_area[2], self.game_area[3]), (255, 255, 255), 2)
        basket_y = self.game_area[3] - 50
        cv2.rectangle(overlay, (self.basket_x, basket_y), (self.basket_x + self.basket_width, basket_y + self.basket_height), (139, 69, 19), -1)
        for ball in self.balls:
            cv2.circle(overlay, (int(ball['x']), int(ball['y'])), 10, ball['color'], -1)
        cv2.putText(overlay, f"Score: {self.score}", (self.game_area[0], self.game_area[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

class SnakeGame:
    def __init__(self):
        self.game_area = (100, 100, 700, 500)
        self.grid_size = 20
        self.win_fx = WinCelebration()
        self.win = False
        self.reset()
        self.hand_landmarks = None
        self.mp_hands = None

    def reset(self):
        self.win = False
        self.win_fx.reset()
        self.snake = [(400, 300), (380, 300), (360, 300)]
        self.direction = (20, 0)
        self.food = self.spawn_food()
        self.score = 0
        self.last_move = time.time()

    def spawn_food(self):
        while True:
            x = random.randint(self.game_area[0] // self.grid_size, (self.game_area[2] - self.grid_size) // self.grid_size) * self.grid_size
            y = random.randint(self.game_area[1] // self.grid_size, (self.game_area[3] - self.grid_size) // self.grid_size) * self.grid_size
            new_food = (x, y)
            if new_food not in self.snake:
                return new_food

    def update(self, overlay, finger_pos, typed_text=""):
        if self.win:
            self.draw(overlay)
            overlay = self.win_fx.draw(overlay, label="SNAKE WIN!", subtitle="Konfeti 10 detik sebelum restart")
            if not self.win_fx.is_active():
                self.reset()
            return overlay
        if finger_pos and len(self.snake) > 0:
            head_x, head_y = self.snake[0]
            dx = finger_pos[0] - head_x
            dy = finger_pos[1] - head_y
            new_direction = (self.grid_size if dx > 0 else -self.grid_size, 0) if abs(dx) > abs(dy) else (0, self.grid_size if dy > 0 else -self.grid_size)
            if new_direction != (-self.direction[0], -self.direction[1]):
                self.direction = new_direction
        if time.time() - self.last_move > 0.2:
            head_x, head_y = self.snake[0]
            new_head = (head_x + self.direction[0], head_y + self.direction[1])
            if (new_head[0] < self.game_area[0] or new_head[0] >= self.game_area[2] or
                    new_head[1] < self.game_area[1] or new_head[1] >= self.game_area[3] or
                    new_head in self.snake):
                self.reset()
                return overlay
            self.snake.insert(0, new_head)
            if abs(new_head[0] - self.food[0]) < self.grid_size and abs(new_head[1] - self.food[1]) < self.grid_size:
                self.score += 1
                if self.score >= 10 and not self.win:
                    self.win = True
                    self.win_fx.start(overlay)
                self.food = self.spawn_food()
            else:
                self.snake.pop()
            self.last_move = time.time()
        self.draw(overlay)
        return overlay

    def draw(self, overlay):
        cv2.rectangle(overlay, (self.game_area[0], self.game_area[1]), (self.game_area[2], self.game_area[3]), (255, 255, 255), 2)
        for i, segment in enumerate(self.snake):
            color = (0, 255, 0) if i == 0 else (0, 200, 0)
            cv2.rectangle(overlay, segment, (segment[0] + self.grid_size, segment[1] + self.grid_size), color, -1)
        cv2.rectangle(overlay, self.food, (self.food[0] + self.grid_size, self.food[1] + self.grid_size), (255, 0, 0), -1)
        cv2.putText(overlay, f"Score: {self.score}", (self.game_area[0], self.game_area[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

class MemoryGame:
    """
    Diganti menjadi game Target Tap:
    - Target bulat muncul acak, sentuh untuk skor.
    - Hit target 10x untuk menang.
    """

    def __init__(self):
        self.game_area = (200, 150, 600, 450)
        self.target_radius = 28
        self.target_pos = None
        self.spawn_interval = 1.2
        self.last_spawn = 0
        self.score = 0
        self.win = False
        self.win_fx = WinCelebration()
        self.instructions = [
            "1) Sentuh target bulat yang muncul.",
            "2) Target pindah setiap muncul/hit.",
            "3) Lewatkan saja target lain.",
            "4) Capai skor 10 untuk menang."
        ]
        self.reset()
        self.hand_landmarks = None
        self.mp_hands = None

    def reset(self):
        self.score = 0
        self.win = False
        self.win_fx.reset()
        self.last_spawn = time.time()
        self.target_pos = self.random_target()

    def random_target(self):
        margin = 60
        x = random.randint(self.game_area[0] + margin, self.game_area[2] - margin)
        y = random.randint(self.game_area[1] + margin, self.game_area[3] - margin)
        color = (
            random.randint(100, 255),
            random.randint(100, 255),
            random.randint(100, 255)
        )
        return {"pos": (x, y), "color": color}

    def update(self, overlay, finger_pos, typed_text=""):
        now = time.time()
        if self.win:
            self.draw(overlay, win=True)
            overlay = self.win_fx.draw(overlay, label="TARGET TAP WIN!", subtitle="Konfeti 10 detik")
            if not self.win_fx.is_active():
                self.reset()
            return overlay
        if now - self.last_spawn > self.spawn_interval:
            self.target_pos = self.random_target()
            self.last_spawn = now
        if finger_pos and self.target_pos:
            tx, ty = self.target_pos["pos"]
            dist = math.hypot(finger_pos[0] - tx, finger_pos[1] - ty)
            if dist <= self.target_radius:
                self.score += 1
                if self.score >= 10:
                    self.win = True
                    self.win_fx.start(overlay)
                self.target_pos = self.random_target()
                self.last_spawn = now
        self.draw(overlay, win=False)
        return overlay

    def draw(self, overlay, win=False):
        cv2.rectangle(overlay, (self.game_area[0], self.game_area[1]), (self.game_area[2], self.game_area[3]), (25, 25, 35), -1)
        cv2.rectangle(overlay, (self.game_area[0], self.game_area[1]), (self.game_area[2], self.game_area[3]), (255, 255, 255), 2)
        cv2.putText(overlay, "TARGET TAP", (240, 190), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 2)
        cv2.putText(overlay, f"Score: {self.score}", (240, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 255, 200), 2)
        instr_x, instr_y = self.game_area[0] + 20, self.game_area[3] - 140
        cv2.rectangle(overlay, (instr_x - 10, instr_y - 60), (instr_x + 330, instr_y + 70), (45, 45, 60), -1)
        cv2.rectangle(overlay, (instr_x - 10, instr_y - 60), (instr_x + 330, instr_y + 70), (180, 180, 200), 1)
        cv2.putText(overlay, "Langkah:", (instr_x, instr_y - 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        for i, line in enumerate(self.instructions):
            cv2.putText(overlay, line, (instr_x, instr_y - 10 + i * 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (220, 220, 220), 1)
        if self.target_pos:
            tx, ty = self.target_pos["pos"]
            cv2.circle(overlay, (tx, ty), self.target_radius, self.target_pos["color"], -1)
            cv2.circle(overlay, (tx, ty), self.target_radius, (255, 255, 255), 2)
        if win:
            cv2.putText(overlay, "WIN! Konfeti 10 detik", (230, 420), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

class WhackAMoleGame:
    def __init__(self):
        self.game_area = (200, 150, 600, 450)
        self.win_fx = WinCelebration()
        self.radius = 30
        self.active_mole = None
        self.last_spawn = time.time()
        self.spawn_interval = 1.4
        self.mole_duration = 1.0
        self.score = 0
        self.win = False
        self.speed_mul = 1.0
        self.reset()

    def set_difficulty(self, multiplier):
        self.speed_mul = multiplier
        self.spawn_interval = max(0.6, 1.4 / multiplier)
        self.mole_duration = max(0.5, 1.0 / multiplier)
        self.reset()

    def reset(self):
        self.score = 0
        self.win = False
        self.win_fx.reset()
        self.active_mole = None
        self.last_spawn = time.time()
        left, top, right, bottom = self.game_area
        width = right - left
        height = bottom - top
        padding_x = 60
        padding_y = 100
        col_spacing = (width - 2 * padding_x) // 2
        row_spacing = (height - 2 * padding_y)
        cx0 = left + padding_x
        cy0 = top + padding_y
        self.holes = [
            (cx0 + col_spacing * c, cy0 + row_spacing * r)
            for r in range(2)
            for c in range(3)
        ]

    def spawn_mole(self):
        self.active_mole = random.choice(self.holes)
        self.last_spawn = time.time()

    def update(self, overlay, finger_pos, typed_text=""):
        now = time.time()
        if self.win:
            self.draw(overlay, win=True)
            overlay = self.win_fx.draw(overlay, label="MOLE WIN!", subtitle="Konfeti 10 detik sebelum ulang")
            if not self.win_fx.is_active():
                self.reset()
            return overlay
        if self.active_mole is None or now - self.last_spawn > self.mole_duration:
            self.spawn_mole()
        if finger_pos and self.active_mole:
            dist = math.hypot(finger_pos[0] - self.active_mole[0], finger_pos[1] - self.active_mole[1])
            if dist <= self.radius:
                self.score += 1
                if self.score >= 10:
                    self.win = True
                    self.win_fx.start(overlay)
                self.active_mole = None
                self.last_spawn = now
        self.draw(overlay, win=False)
        return overlay

    def draw(self, overlay, win=False):
        cv2.rectangle(overlay, (self.game_area[0], self.game_area[1]), (self.game_area[2], self.game_area[3]), (255, 255, 255), 2)
        title_x = self.game_area[0] + 20
        title_y = self.game_area[1] + 30
        cv2.putText(overlay, "WHACK A MOLE", (title_x, title_y), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        cv2.putText(overlay, f"Score: {self.score}", (title_x, title_y + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        for hole in self.holes:
            cv2.circle(overlay, hole, self.radius, (40, 40, 40), -1)
            cv2.circle(overlay, hole, self.radius, (255, 255, 255), 2)
        if self.active_mole:
            cv2.circle(overlay, self.active_mole, self.radius, (0, 200, 255), -1)
            cv2.circle(overlay, self.active_mole, self.radius, (255, 255, 255), 3)
        cv2.putText(overlay, "Sentuh mole untuk skor. 10 = WIN", (title_x, self.game_area[3] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        if win:
            cv2.putText(overlay, "WIN! Konfeti 10 detik", (260, 460), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

class BalloonPopGame:
    def __init__(self):
        self.game_area = (200, 150, 600, 450)
        self.win_fx = WinCelebration()
        self.balloons = []
        self.last_spawn = time.time()
        self.spawn_interval = 1.2
        self.radius = 30
        self.speed_range = (1.5, 2.5)
        self.score = 0
        self.win = False
        self.speed_mul = 1.0
        self.reset()

    def set_difficulty(self, multiplier):
        self.speed_mul = multiplier
        self.spawn_interval = max(0.5, 1.2 / multiplier)
        low, high = 1.5 * multiplier, 2.5 * multiplier
        self.speed_range = (low, high)
        self.reset()

    def reset(self):
        self.balloons = []
        self.last_spawn = time.time()
        self.score = 0
        self.win = False
        self.win_fx.reset()

    def spawn_balloon(self):
        x = random.randint(self.game_area[0] + self.radius, self.game_area[2] - self.radius)
        y = self.game_area[3] - self.radius
        speed = random.uniform(*self.speed_range)
        color = (
            random.randint(100, 255),
            random.randint(100, 255),
            random.randint(100, 255)
        )
        self.balloons.append({"pos": [x, y], "speed": speed, "color": color})

    def update(self, overlay, finger_pos, typed_text=""):
        now = time.time()
        if self.win:
            self.draw(overlay, win=True)
            overlay = self.win_fx.draw(overlay, label="BALLOON WIN!", subtitle="Konfeti 10 detik sebelum restart")
            if not self.win_fx.is_active():
                self.reset()
            return overlay
        if now - self.last_spawn > self.spawn_interval:
            self.spawn_balloon()
            self.last_spawn = now
        for balloon in self.balloons[:]:
            balloon["pos"][1] -= balloon["speed"]
            if balloon["pos"][1] < self.game_area[1]:
                self.balloons.remove(balloon)
        if finger_pos:
            for balloon in self.balloons[:]:
                bx, by = balloon["pos"]
                dist = math.hypot(finger_pos[0] - bx, finger_pos[1] - by)
                if dist <= self.radius:
                    self.score += 1
                    if self.score >= 10:
                        self.win = True
                        self.win_fx.start(overlay)
                    self.balloons.remove(balloon)
        self.draw(overlay, win=False)
        return overlay

    def draw(self, overlay, win=False):
        cv2.rectangle(overlay, (self.game_area[0], self.game_area[1]), (self.game_area[2], self.game_area[3]), (255, 255, 255), 2)
        title_x = self.game_area[0] + 20
        title_y = self.game_area[1] + 30
        cv2.putText(overlay, "BALLOON POP", (title_x, title_y), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        cv2.putText(overlay, f"Score: {self.score}", (title_x, title_y + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        for balloon in self.balloons:
            bx, by = int(balloon["pos"][0]), int(balloon["pos"][1])
            cv2.circle(overlay, (bx, by), self.radius, balloon["color"], -1)
            cv2.circle(overlay, (bx, by + self.radius), int(self.radius * 0.5), balloon["color"], 2)
        cv2.putText(overlay, "Sentuh balon untuk pecahkan. 10 = WIN", (title_x, self.game_area[3] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        if win:
            cv2.putText(overlay, "WIN! Konfeti 10 detik", (title_x + 30, self.game_area[3] - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

class DodgeGame:
    def __init__(self):
        self.game_area = (150, 130, 650, 480)
        self.win_fx = WinCelebration()
        self.player_width = 70
        self.player_height = 20
        self.spawn_interval = 0.9
        self.speed_range = (4.0, 7.0)
        self.target_clear = 20
        self.lives_max = 3
        self.hand_landmarks = None
        self.mp_hands = None
        self.reset()

    def reset(self):
        self.win = False
        self.win_fx.reset()
        self.player_x = (self.game_area[0] + self.game_area[2]) // 2 - self.player_width // 2
        self.player_y = self.game_area[3] - 40
        self.obstacles = []
        self.last_spawn = time.time()
        self.cleared = 0
        self.lives = self.lives_max

    def spawn_meteor(self):
        size = random.randint(18, 36)
        x = random.randint(self.game_area[0] + size, self.game_area[2] - size)
        speed = random.uniform(*self.speed_range)
        color = (
            random.randint(160, 210),
            random.randint(150, 200),
            random.randint(220, 255)
        )
        self.obstacles.append({"x": x, "y": self.game_area[1] - size, "size": size, "speed": speed, "color": color})

    def check_collision(self, meteor):
        px1 = self.player_x
        px2 = self.player_x + self.player_width
        py1 = self.player_y
        py2 = self.player_y + self.player_height
        mx = meteor["x"]
        my = meteor["y"]
        r = meteor["size"]
        return mx + r > px1 and mx - r < px2 and my + r > py1 and my - r < py2

    def update(self, overlay, finger_pos, typed_text=""):
        now = time.time()
        if self.win:
            self.draw(overlay, win=True)
            overlay = self.win_fx.draw(overlay, label="DODGE WIN!", subtitle="Konfeti 10 detik sebelum restart")
            if not self.win_fx.is_active():
                self.reset()
            return overlay
        if finger_pos:
            self.player_x = max(self.game_area[0], min(self.game_area[2] - self.player_width, finger_pos[0] - self.player_width // 2))
        if now - self.last_spawn > self.spawn_interval:
            self.spawn_meteor()
            self.last_spawn = now
        for meteor in self.obstacles[:]:
            meteor["y"] += meteor["speed"]
            if meteor["y"] - meteor["size"] > self.game_area[3]:
                self.obstacles.remove(meteor)
                self.cleared += 1
                if self.cleared >= self.target_clear and not self.win:
                    self.win = True
                    self.win_fx.start(overlay)
                continue
            if self.check_collision(meteor):
                self.obstacles.remove(meteor)
                self.lives -= 1
                if self.lives <= 0:
                    self.reset()
                    return overlay
        self.draw(overlay)
        return overlay

    def draw(self, overlay, win=False):
        y1, y2 = self.game_area[1], self.game_area[3]
        x1, x2 = self.game_area[0], self.game_area[2]
        region = overlay[y1:y2, x1:x2].copy()
        bg_color = np.array([225, 215, 230], dtype=np.uint8)
        patch = np.full(region.shape, bg_color, dtype=np.uint8)
        overlay[y1:y2, x1:x2] = cv2.addWeighted(region, 0.85, patch, 0.15, 0)
        frame_color = (255, 255, 255)
        player_color = (240, 170, 60) if not win else (80, 220, 120)
        text_color = (245, 240, 240)
        accent_text = (240, 170, 180)
        info_color = (210, 210, 240)
        cv2.rectangle(overlay, (self.game_area[0], self.game_area[1]), (self.game_area[2], self.game_area[3]), frame_color, 2)
        cv2.rectangle(overlay, (int(self.player_x), int(self.player_y)), (int(self.player_x + self.player_width), int(self.player_y + self.player_height)), player_color, -1)
        for meteor in self.obstacles:
            cv2.circle(overlay, (int(meteor["x"]), int(meteor["y"])), meteor["size"], meteor["color"], -1)
            cv2.circle(overlay, (int(meteor["x"]), int(meteor["y"])), meteor["size"], frame_color, 2)
        cv2.putText(overlay, f"Lolos: {self.cleared}/{self.target_clear}", (self.game_area[0], self.game_area[1] - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.7, text_color, 2)
        cv2.putText(overlay, f"Nyawa: {self.lives}", (self.game_area[0] + 220, self.game_area[1] - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.7, accent_text, 2)
        cv2.putText(overlay, "Geser jari kiri-kanan untuk menghindar", (self.game_area[0], self.game_area[3] + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, info_color, 2)

class SpaceShooterGame:
    def __init__(self):
        self.game_area = (140, 120, 660, 480)
        self.win_fx = WinCelebration()
        self.hand_landmarks = None
        self.mp_hands = None
        self.player_width = 70
        self.player_height = 24
        self.laser_speed = 11
        self.fire_cooldown = 0.28
        self.spawn_interval = 1.0
        self.speed_range = (2.8, 4.8)
        self.target_score = 12
        self.reset()

    def reset(self):
        self.win = False
        self.win_fx.reset()
        self.player_x = (self.game_area[0] + self.game_area[2]) // 2
        self.player_y = self.game_area[3] - 40
        self.lasers = []
        self.asteroids = []
        self.last_fire = time.time()
        self.last_spawn = time.time()
        self.score = 0
        self.lives = 3

    def spawn_asteroid(self):
        size = random.randint(18, 32)
        x = random.randint(self.game_area[0] + size, self.game_area[2] - size)
        speed = random.uniform(*self.speed_range)
        color = (
            random.randint(150, 220),
            random.randint(100, 170),
            random.randint(160, 255)
        )
        self.asteroids.append({"x": x, "y": self.game_area[1] - size, "size": size, "speed": speed, "color": color})

    def check_collision_player(self, meteor):
        px1 = self.player_x - self.player_width // 2
        px2 = self.player_x + self.player_width // 2
        py1 = self.player_y - self.player_height
        py2 = self.player_y + self.player_height // 2
        mx = meteor["x"]
        my = meteor["y"]
        r = meteor["size"]
        return mx + r > px1 and mx - r < px2 and my + r > py1 and my - r < py2

    def update(self, overlay, finger_pos, typed_text=""):
        now = time.time()
        if self.win:
            self.draw(overlay, win=True)
            overlay = self.win_fx.draw(overlay, label="SHOOTER WIN!", subtitle="Konfeti 10 detik sebelum restart")
            if not self.win_fx.is_active():
                self.reset()
            return overlay
        if finger_pos:
            min_x = self.game_area[0] + self.player_width // 2
            max_x = self.game_area[2] - self.player_width // 2
            self.player_x = max(min_x, min(max_x, finger_pos[0]))
        cooldown = max(0.18, self.fire_cooldown - (self.score * 0.01))
        if now - self.last_fire > cooldown:
            self.lasers.append({"x": self.player_x, "y": self.player_y - self.player_height, "speed": self.laser_speed})
            self.last_fire = now
        spawn_rate = max(0.55, self.spawn_interval - self.score * 0.03)
        if now - self.last_spawn > spawn_rate:
            self.spawn_asteroid()
            self.last_spawn = now
        for laser in self.lasers[:]:
            laser["y"] -= laser["speed"]
            if laser["y"] < self.game_area[1]:
                self.lasers.remove(laser)
        for meteor in self.asteroids[:]:
            meteor["y"] += meteor["speed"]
            if meteor["y"] - meteor["size"] > self.game_area[3]:
                self.asteroids.remove(meteor)
                self.lives -= 1
                if self.lives <= 0:
                    self.reset()
                    return overlay
                continue
            if self.check_collision_player(meteor):
                self.asteroids.remove(meteor)
                self.lives -= 1
                if self.lives <= 0:
                    self.reset()
                    return overlay
        for laser in self.lasers[:]:
            for meteor in self.asteroids[:]:
                dist = math.hypot(laser["x"] - meteor["x"], laser["y"] - meteor["y"])
                if dist <= meteor["size"]:
                    self.lasers.remove(laser)
                    self.asteroids.remove(meteor)
                    self.score += 1
                    if self.score >= self.target_score and not self.win:
                        self.win = True
                        self.win_fx.start(overlay)
                    break
        self.draw(overlay)
        return overlay

    def draw(self, overlay, win=False):
        x1, y1, x2, y2 = self.game_area
        region = overlay[y1:y2, x1:x2].copy()
        space_bg = np.full(region.shape, (25, 30, 60), dtype=np.uint8)
        overlay[y1:y2, x1:x2] = cv2.addWeighted(region, 0.65, space_bg, 0.35, 0)
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (255, 255, 255), 2)
        line_phase = int(time.time() * 80) % max(1, (y2 - y1))
        for offset in range(0, y2 - y1, 50):
            y_line = y1 + (line_phase + offset) % (y2 - y1)
            cv2.line(overlay, (x1, y_line), (x2, y_line), (60, 90, 140), 1)
        for laser in self.lasers:
            lx, ly = int(laser["x"]), int(laser["y"])
            cv2.line(overlay, (lx, ly), (lx, ly - 18), (0, 255, 200), 3)
            cv2.circle(overlay, (lx, ly - 20), 5, (180, 255, 255), -1)
        for meteor in self.asteroids:
            mx, my, size = int(meteor["x"]), int(meteor["y"]), meteor["size"]
            cv2.circle(overlay, (mx, my), size, meteor["color"], -1)
            cv2.circle(overlay, (mx, my), size, (255, 255, 255), 2)
        ship_points = np.array([
            [int(self.player_x), int(self.player_y - self.player_height)],
            [int(self.player_x - self.player_width // 2), int(self.player_y + self.player_height // 2)],
            [int(self.player_x + self.player_width // 2), int(self.player_y + self.player_height // 2)]
        ])
        cv2.fillPoly(overlay, [ship_points], (90, 220, 255))
        cv2.polylines(overlay, [ship_points], True, (255, 255, 255), 2)
        thruster_y = int(self.player_y + self.player_height // 2)
        cv2.line(overlay, (int(self.player_x - self.player_width // 4), thruster_y), (int(self.player_x - self.player_width // 4), thruster_y + 16), (0, 160, 255), 4)
        cv2.line(overlay, (int(self.player_x + self.player_width // 4), thruster_y), (int(self.player_x + self.player_width // 4), thruster_y + 16), (0, 160, 255), 4)
        cv2.putText(overlay, f"Score: {self.score}/{self.target_score}", (x1 + 10, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(overlay, f"Shield: {self.lives}", (x1 + 230, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 210, 180), 2)
        cv2.putText(overlay, "Gerak pesawat kiri-kanan | Laser otomatis", (x1 + 10, y2 + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (210, 235, 255), 2)
        if win:
            cv2.putText(overlay, "WIN! Konfeti 10 detik", (x1 + 120, y1 + 200), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

class FlappyBirdGame:
    def __init__(self):
        self.game_area = (100, 100, 700, 500)  
        self.bird_size = 20
        self.pipe_width = 50
        self.gap_size = 180
        self.pipe_speed = 3
        self.gravity = 0.5
        self.lift = -6
        self.hand_landmarks = None
        self.mp_hands = None
        self.max_velocity = 10
        self.win = False
        self.win_fx = WinCelebration()
        self.pipe_spacing = 220
        self.reset()

    def reset(self):
        self.win = False
        self.win_fx.reset()
        self.bird_x = self.game_area[0] + 100
        self.bird_y = (self.game_area[1] + self.game_area[3]) // 2
        self.bird_velocity = 0
        self.pipes = []
        self.score = 0
        self.last_pipe_spawn = time.time()
        self.game_over = False

    def update(self, overlay, finger_pos, typed_text=""):
        if self.win:
            self.draw(overlay)
            overlay = self.win_fx.draw(overlay, label="FLAPPY WIN!", subtitle="Konfeti 10 detik sebelum restart")
            if not self.win_fx.is_active():
                self.reset()
            return overlay
        if self.game_over:
            if finger_pos:
                self.reset()
            self.draw(overlay, win=False)
            return overlay
        velocity_change = self.gravity
        if self.hand_landmarks and self.mp_hands:
            thumb_tip = self.hand_landmarks.landmark[self.mp_hands.HandLandmark.THUMB_TIP]
            index_tip = self.hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
            w, h = overlay.shape[1], overlay.shape[0]
            thumb_x, thumb_y = thumb_tip.x * w, thumb_tip.y * h
            index_x, index_y = index_tip.x * w, index_tip.y * h
            distance = self.calculate_distance((thumb_x, thumb_y), (index_x, index_y))
            pinch_threshold = 50
            open_threshold = 120
            if distance > open_threshold:
                velocity_change += self.lift

        self.bird_velocity += velocity_change
        self.bird_velocity = max(-self.max_velocity, min(self.max_velocity, self.bird_velocity))
        self.bird_y += self.bird_velocity
        if self.bird_y < self.game_area[1]:
            self.bird_y = self.game_area[1]
            self.bird_velocity = 0
            self.game_over = True
        if self.bird_y > self.game_area[3] - self.bird_size:
            self.bird_y = self.game_area[3] - self.bird_size
            self.bird_velocity = 0
            self.game_over = True

        if time.time() - self.last_pipe_spawn > 1.6:
            if not self.pipes or self.pipes[-1]['x'] < self.game_area[2] - self.pipe_spacing:
                margin = 80
                min_gap_y = self.game_area[1] + margin + self.gap_size // 2
                max_gap_y = self.game_area[3] - margin - self.gap_size // 2
                min_gap_y = max(min_gap_y, self.game_area[1] + self.gap_size // 2 + 10)
                max_gap_y = min(max_gap_y, self.game_area[3] - self.gap_size // 2 - 10)
                if min_gap_y < max_gap_y:
                    gap_y = random.randint(min_gap_y, max_gap_y)
                else:
                    gap_y = (self.game_area[1] + self.game_area[3]) // 2
                self.pipes.append({
                    'x': self.game_area[2],
                    'gap_y': gap_y
                })
                self.last_pipe_spawn = time.time()

        for pipe in self.pipes[:]:
            pipe['x'] -= self.pipe_speed
            if pipe['x'] + self.pipe_width < self.game_area[0]:
                self.pipes.remove(pipe)
                self.score += 1
                if self.score >= 10:
                    self.win = True
                    self.win_fx.start(overlay)
            elif (pipe['x'] < self.bird_x + self.bird_size and
                  pipe['x'] + self.pipe_width > self.bird_x and
                  (self.bird_y < pipe['gap_y'] - self.gap_size // 2 or
                   self.bird_y + self.bird_size > pipe['gap_y'] + self.gap_size // 2)):
                self.game_over = True

        self.draw(overlay)
        return overlay

    def calculate_distance(self, point1, point2):
        return ((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)**0.5

    def draw(self, overlay, win=False):
        cv2.rectangle(overlay, (self.game_area[0], self.game_area[1]),
                      (self.game_area[2], self.game_area[3]), (255, 255, 255), 2)
        cv2.circle(overlay, (int(self.bird_x), int(self.bird_y)), self.bird_size // 2, (255, 255, 0), -1)
        for pipe in self.pipes:
            cv2.rectangle(overlay, (int(pipe['x']), self.game_area[1]),
                          (int(pipe['x']) + self.pipe_width, int(pipe['gap_y'] - self.gap_size // 2)),
                          (0, 255, 0), -1)
            cv2.rectangle(overlay, (int(pipe['x']), int(pipe['gap_y'] + self.gap_size // 2)),
                          (int(pipe['x']) + self.pipe_width, self.game_area[3]),
                          (0, 255, 0), -1)
        cv2.putText(overlay, f"Score: {self.score}", (self.game_area[0], self.game_area[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        if win:
            cv2.putText(overlay, "WIN!", (self.game_area[0] + 200, self.game_area[1] + 250),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 4)
        elif self.game_over:
            cv2.putText(overlay, "Game Over! Point to restart", (self.game_area[0] + 50, self.game_area[3] - 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)

async def main():
    keyboard = VirtualKeyboard()
    await keyboard.run()

if platform.system() == "Emscripten":
    asyncio.ensure_future(main())
else:
    if __name__ == "__main__":
        asyncio.run(main())
