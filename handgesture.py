import asyncio
import platform
import cv2
import numpy as np
import mediapipe as mp
import time
import math
import pygame
import random

pygame.mixer.init()

class VirtualKeyboard:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7, max_num_hands=2)
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        self.layouts = {
            "QWERTY": [
                ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
                ["A", "S", "D", "F", "G", "H", "J", "K", "L"],
                ["Z", "X", "C", "V", "B", "N", "M", ",", ".", "/", "Backspace"],
                ["Space", "Enter", "Theme", "Layout", "Size+", "Size-", "Game", "Draw"]
            ],
            "AZERTY": [
                ["A", "Z", "E", "R", "T", "Y", "U", "I", "O", "P"],
                ["Q", "S", "D", "F", "G", "H", "J", "K", "L", "M"],
                ["W", "X", "C", "V", "B", "N", ",", ".", "/", "Backspace"],
                ["Space", "Enter", "Theme", "Layout", "Size+", "Size-", "Game", "Draw"]
            ],
            "INDONESIA": [
                ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
                ["A", "S", "D", "F", "G", "H", "J", "K", "L"],
                ["Z", "X", "C", "V", "B", "N", "M", ",", ".", "/", "Backspace"],
                ["Space", "Enter", "Theme", "Layout", "Size+", "Size-", "Game", "Draw"]
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
            "catch": CatchGame(),
            "snake": SnakeGame(),
            "typing": TypingGame(self),  
            "memory": MemoryGame(),
            "flappy": FlappyBirdGame()
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
        self.create_sound_effects()

    def create_sound_effects(self):
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
        except:
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

    def toggle_draw_mode(self):
        self.draw_mode = not self.draw_mode
        self.game_mode = False
        if self.draw_mode:
            h, w = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)), int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.drawing_canvas = np.zeros((h, w, 3), dtype=np.uint8)
            self.last_point = None
        else:
            self.drawing_canvas = None

    def get_curved_position(self, base_x, base_y, hand_center, curve_intensity=0.3):
        if hand_center is None:
            return base_x, base_y
        distance = np.sqrt((base_x - hand_center[0])**2 + (base_y - hand_center[1])**2)
        curve_offset_x = (base_x - hand_center[0]) * curve_intensity * (distance / 200)
        curve_offset_y = (base_y - hand_center[1]) * curve_intensity * (distance / 200)
        return int(base_x + curve_offset_x), int(base_y + curve_offset_y)

    def animate_key_press(self, key, start_time):
        elapsed = time.time() - start_time
        if elapsed < self.animation_duration:
            pulse = abs(math.sin(elapsed * 10))
            self.key_animations[key] = {'pulse': pulse, 'active': True}
        elif key in self.key_animations:
            del self.key_animations[key]

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

    def get_text_size(self, text, font=cv2.FONT_HERSHEY_SIMPLEX, font_scale=1, thickness=2):
        return cv2.getTextSize(text, font, font_scale, thickness)[0]

    def calculate_distance(self, point1, point2):
        return np.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)

    def get_game_score(self):
        if not self.game_mode or self.current_game in (None, "menu"):
            return None
        game = self.games.get(self.current_game)
        if game and hasattr(game, "score"):
            return game.score
        return None

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
            ("Catch Balls", "catch"),
            ("Snake", "snake"),
            ("Typing Race", "typing"),
            ("Memory", "memory"),
            ("Flappy Bird", "flappy"),
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
                        self.key_animations[key] = {'pulse': 1.0, 'active': True}
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
        else:
            info_text = f"Layout: {self.current_layout} | Theme: {self.current_theme} | Scale: {self.scale_factor:.1f}x"
        cv2.putText(overlay, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, theme["text_color"], 2)
        instructions = "Point to select game | Game button to exit" if self.game_mode else \
                      "Point to draw or select color | Exit to return" if self.draw_mode else \
                      "Spread fingers to show keyboard | Point to type | Game or Draw button"
        cv2.putText(overlay, instructions, (10, overlay.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, theme["text_color"], 1)

    async def run(self):
        while self.cap.isOpened():
            success, frame = self.cap.read()
            if not success:
                break
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(rgb_frame)
            overlay = frame.copy()
            hand_center = None
            finger_pos = None
            if results.multi_hand_landmarks:
                for hand_idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
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
                    if not self.game_mode and not self.draw_mode:
                        distance = self.calculate_distance((thumb_x, thumb_y), (pinky_x, pinky_y))
                        self.show_keyboard = distance > self.show_threshold
                        if distance < self.hide_threshold:
                            self.show_keyboard = False
                        if self.show_keyboard:
                            overlay = self.process_finger_input(overlay, finger_pos[0], finger_pos[1], hand_label, hand_center)
                    elif self.draw_mode:
                        overlay = self.process_drawing(overlay, finger_pos)
                    # Store hand landmarks for games
                    if self.game_mode and self.current_game in self.games:
                        self.games[self.current_game].hand_landmarks = hand_landmarks
                        self.games[self.current_game].mp_hands = self.mp_hands
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
                if self.show_keyboard:
                    overlay = self.draw_keyboard(overlay, hand_center)
                self.draw_text_display(overlay)
            self.draw_info_panel(overlay)
            for key in list(self.key_animations.keys()):
                self.animate_key_press(key, time.time() - 0.1)
                if key not in self.key_animations:
                    self.key_animations.pop(key, None)
            frame = cv2.addWeighted(overlay, 0.8, frame, 0.2, 0)
            cv2.imshow('Virtual Keyboard', frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('g'):
                self.toggle_game_mode()
            elif key == ord('d'):
                self.toggle_draw_mode()
            await asyncio.sleep(1.0 / 60)  
        self.cap.release()
        cv2.destroyAllWindows()
        pygame.mixer.quit()

class PongGame:
    def __init__(self):
        self.game_area = (100, 100, 700, 500)
        self.reset()
        self.hand_landmarks = None
        self.mp_hands = None

    def reset(self):
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
        self.draw(overlay)
        return overlay

    def draw(self, overlay):
        cv2.rectangle(overlay, (self.game_area[0], self.game_area[1]), (self.game_area[2], self.game_area[3]), (255, 255, 255), 2)
        paddle_x = self.game_area[0] + 30
        cv2.rectangle(overlay, (paddle_x, self.paddle_y), (paddle_x + self.paddle_width, self.paddle_y + self.paddle_height), (0, 255, 0), -1)
        cv2.circle(overlay, (int(self.ball_x), int(self.ball_y)), self.ball_size, (255, 255, 0), -1)
        cv2.putText(overlay, f"Score: {self.score}", (self.game_area[0], self.game_area[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

class CatchGame:
    def __init__(self):
        self.game_area = (100, 100, 700, 500)
        self.reset()
        self.hand_landmarks = None
        self.mp_hands = None

    def reset(self):
        self.basket_x = 400
        self.basket_width = 80
        self.basket_height = 20
        self.balls = []
        self.score = 0
        self.last_spawn = time.time()

    def update(self, overlay, finger_pos, typed_text=""):
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
        self.reset()
        self.hand_landmarks = None
        self.mp_hands = None

    def reset(self):
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

class TypingGame:
    def __init__(self, parent):
        self.words = ["PYTHON", "OPENCV", "MEDIAPIPE", "KEYBOARD", "VIRTUAL", "GAME", "CODE", "TECH"]
        self.game_area = (200, 200, 600, 400)
        self.parent = parent  # Reference to VirtualKeyboard
        self.reset()
        self.hand_landmarks = None
        self.mp_hands = None

    def reset(self):
        self.current_word = random.choice(self.words)
        self.typed_chars = ""
        self.score = 0
        self.start_time = time.time()
        self.words_completed = 0

    def update(self, overlay, finger_pos, typed_text=""):
        if typed_text:
            self.typed_chars = typed_text
            if self.typed_chars == self.current_word:
                self.score += 1
                self.words_completed += 1
                self.current_word = random.choice(self.words)
                self.typed_chars = ""
                self.parent.typed_text = ""  
        self.draw(overlay)
        return overlay

    def draw(self, overlay):
        cv2.rectangle(overlay, (self.game_area[0], self.game_area[1]), (self.game_area[2], self.game_area[3]), (50, 50, 50), -1)
        cv2.rectangle(overlay, (self.game_area[0], self.game_area[1]), (self.game_area[2], self.game_area[3]), (255, 255, 255), 2)
        cv2.putText(overlay, "TYPING RACE", (self.game_area[0] + 50, self.game_area[1] + 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(overlay, f"Type: {self.current_word}", (self.game_area[0] + 50, self.game_area[1] + 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        cv2.putText(overlay, f"Typed: {self.typed_chars}", (self.game_area[0] + 50, self.game_area[1] + 130), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
        cv2.putText(overlay, f"Score: {self.score}", (self.game_area[0] + 50, self.game_area[1] + 160), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(overlay, "Use keyboard to type the word", (self.game_area[0] + 50, self.game_area[1] + 190), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 2)

class MemoryGame:
    def __init__(self):
        self.game_area = (200, 150, 600, 450)
        self.last_input_time = 0
        self.input_cooldown = 0.5
        self.reset()
        self.hand_landmarks = None
        self.mp_hands = None

    def reset(self):
        self.sequence = []
        self.player_input = []
        self.showing_sequence = False
        self.current_step = 0
        self.game_state = "waiting"
        self.last_update = time.time()
        self.score = 0
        self.buttons = [
            {"pos": (300, 250), "color": (255, 0, 0), "id": 0},
            {"pos": (400, 250), "color": (0, 255, 0), "id": 1},
            {"pos": (300, 350), "color": (0, 0, 255), "id": 2},
            {"pos": (400, 350), "color": (255, 255, 0), "id": 3}
        ]
        self.button_size = 60
        self.generate_sequence()

    def generate_sequence(self):
        self.sequence.append(random.randint(0, 3))
        self.current_step = 0
        self.game_state = "showing"
        self.last_update = time.time()

    def update(self, overlay, finger_pos, typed_text=""):
        current_time = time.time()
        if self.game_state == "showing":
            if current_time - self.last_update > 0.8:
                self.current_step += 1
                if self.current_step >= len(self.sequence):
                    self.game_state = "input"
                    self.player_input = []
                    self.positive_step = 0
                self.last_update = current_time
        elif self.game_state == "input" and finger_pos and current_time - self.last_input_time > self.input_cooldown:
            for button in self.buttons:
                btn_x, btn_y = button["pos"]
                if abs(finger_pos[0] - btn_x) < self.button_size // 2 and abs(finger_pos[1] - btn_y) < self.button_size // 2:
                    self.player_input.append(button["id"])
                    self.last_input_time = current_time
                    if self.player_input[-1] != self.sequence[len(self.player_input) - 1]:
                        self.reset()
                        return overlay
                    if len(self.player_input) == len(self.sequence):
                        self.score += 1
                        self.generate_sequence()
                    break
        self.draw(overlay)
        return overlay

    def draw(self, overlay):
        cv2.rectangle(overlay, (self.game_area[0], self.game_area[1]), (self.game_area[2], self.game_area[3]), (30, 30, 30), -1)
        cv2.rectangle(overlay, (self.game_area[0], self.game_area[1]), (self.game_area[2], self.game_area[3]), (255, 255, 255), 2)
        cv2.putText(overlay, "MEMORY GAME", (250, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(overlay, f"Level: {self.score + 1}", (250, 230), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(overlay, f"Score: {self.score}", (250, 255), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        for i, button in enumerate(self.buttons):
            btn_x, btn_y = button["pos"]
            color = button["color"]
            if self.game_state == "showing" and self.current_step < len(self.sequence) and self.sequence[self.current_step] == button["id"]:
                color = tuple(min(255, c + 100) for c in color)
            cv2.circle(overlay, (btn_x, btn_y), self.button_size // 2, color, -1)
            cv2.circle(overlay, (btn_x, btn_y), self.button_size // 2, (255, 255, 255), 2)
        if self.game_state == "showing":
            cv2.putText(overlay, "Watch the sequence...", (250, 420), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        elif self.game_state == "input":
            cv2.putText(overlay, "Repeat the sequence!", (250, 420), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

class FlappyBirdGame:
    def __init__(self):
        self.game_area = (100, 100, 700, 500)  
        self.bird_size = 20
        self.pipe_width = 50
        self.gap_size = 150
        self.pipe_speed = 3
        self.gravity = 0.5
        self.lift = -2
        self.hand_landmarks = None
        self.mp_hands = None
        self.reset()

    def reset(self):
        self.bird_x = self.game_area[0] + 100
        self.bird_y = (self.game_area[1] + self.game_area[3]) // 2
        self.bird_velocity = 0
        self.pipes = []
        self.score = 0
        self.last_pipe_spawn = time.time()
        self.game_over = False

    def update(self, overlay, finger_pos, typed_text=""):
        if self.game_over:
            if finger_pos: 
                self.reset()
            return overlay

        velocity_change = 0
        if self.hand_landmarks and self.mp_hands:
            thumb_tip = self.hand_landmarks.landmark[self.mp_hands.HandLandmark.THUMB_TIP]
            index_tip = self.hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
            w, h = overlay.shape[1], overlay.shape[0]
            thumb_x, thumb_y = thumb_tip.x * w, thumb_tip.y * h
            index_x, index_y = index_tip.x * w, index_tip.y * h
            distance = self.calculate_distance((thumb_x, thumb_y), (index_x, index_y))
            pinch_threshold = 50
            open_threshold = 100
            if distance < pinch_threshold:
                velocity_change = self.gravity  
            elif distance > open_threshold:
                velocity_change = self.lift  

        self.bird_velocity += velocity_change
        self.bird_y += self.bird_velocity
        if self.bird_y < self.game_area[1] or self.bird_y > self.game_area[3] - self.bird_size:
            self.game_over = True

        if time.time() - self.last_pipe_spawn > 2.0:
            gap_y = random.randint(self.game_area[1] + 100, self.game_area[3] - 100 - self.gap_size)
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
            elif (pipe['x'] < self.bird_x + self.bird_size and
                  pipe['x'] + self.pipe_width > self.bird_x and
                  (self.bird_y < pipe['gap_y'] - self.gap_size // 2 or
                   self.bird_y + self.bird_size > pipe['gap_y'] + self.gap_size // 2)):
                self.game_over = True

        self.draw(overlay)
        return overlay

    def calculate_distance(self, point1, point2):
        return ((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)**0.5

    def draw(self, overlay):
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
        if self.game_over:
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
