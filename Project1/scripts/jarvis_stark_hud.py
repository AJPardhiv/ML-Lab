import cv2
import mediapipe as mp
import numpy as np
import pickle
import time
import math
from pathlib import Path
import threading
import queue
import psutil
import subprocess
from datetime import datetime

# Import pyttsx3 separately to handle errors
try:
    import pyttsx3
    VOICE_ENABLED = True
except Exception as e:
    print(f"Warning: Voice system unavailable - {e}")
    VOICE_ENABLED = False

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_face_mesh = mp.solutions.face_mesh

# Load gesture model
model_path = Path(__file__).parent.parent / 'models' / 'gesture_rf.pkl'
if not model_path.exists():
    print(f"ERROR: Model not found at {model_path}. Please train model first: python scripts/train_model.py")
    exit(1)
mod = pickle.load(open(model_path,'rb'))
clf = mod['model']
scaler = mod['scaler']

# Initialize audio engine in thread
voice_queue = queue.Queue()
voice_running = True

def speak_text(text):
    """Wrapper to safely add text to voice queue"""
    if VOICE_ENABLED:
        print(f'[VOICE] Queued: {text}')
        voice_queue.put(text)
    else:
        print(f'[VOICE] Disabled: {text}')

def voice_worker():
    """Background thread for speaking - completely isolated"""
    if not VOICE_ENABLED:
        print("Voice worker: pyttsx3 not available")
        return
    
    engine = None
    try:
        # Initialize engine in this thread
        engine = pyttsx3.init()
        engine.setProperty('rate', 160)
        engine.setProperty('volume', 1.0)
        print("[OK] Voice engine initialized in background thread")
        
        while voice_running:
            try:
                # Get text with short timeout
                text = voice_queue.get(timeout=0.3)
                
                if text is None or not voice_running:
                    break
                
                # Speak the text
                print(f'[SPEAK] {text}')
                engine.say(text)
                engine.runAndWait()
                
                # Small delay to prevent overlap
                time.sleep(0.2)
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Voice speak error: {e}")
                # Try to reinitialize engine
                try:
                    engine = pyttsx3.init()
                except:
                    pass
                continue
                
    except Exception as e:
        print(f"Voice thread error: {e}")
    finally:
        if engine:
            try:
                engine.stop()
            except:
                pass

# Start voice thread
voice_thread = threading.Thread(target=voice_worker, daemon=True)
voice_thread.start()
time.sleep(0.3)  # Give voice system time to initialize

GESTURE_LABELS = {
    'open_palm': 'Open Palm detected',
    'fist': 'Fist detected',
    'thumbs_up': 'Thumbs Up detected',
    'swipe_right': 'Swipe Right detected',
    'swipe_left': 'Swipe Left detected',
    'two_fingers': 'Two Fingers detected',
    'pointing': 'Pointing detected'
}

GESTURE_ACTIONS = {
    'open_palm': 'activate_chrome',
    'fist': 'close_window',
    'thumbs_up': 'confirm',
    'swipe_right': 'next_tab',
    'swipe_left': 'prev_tab',
    'two_fingers': 'volume_up',
    'pointing': 'cursor_mode'
}

# Toggle to prevent automation during testing (set to False to disable window/tab/volume actions)
ACTIONS_ENABLED = True

# System monitoring
class SystemMonitor:
    def __init__(self):
        self.cpu_percent = 0
        self.memory_percent = 0
        self.disk_percent = 0
        self.network_sent = 0
        self.network_recv = 0
        self.last_update = time.time()
        self.update_interval = 1.0
        
    def update(self):
        now = time.time()
        if now - self.last_update >= self.update_interval:
            self.cpu_percent = psutil.cpu_percent(interval=0.1)
            self.memory_percent = psutil.virtual_memory().percent
            self.disk_percent = psutil.disk_usage('/').percent
            net = psutil.net_io_counters()
            self.network_sent = net.bytes_sent / (1024 * 1024)  # MB
            self.network_recv = net.bytes_recv / (1024 * 1024)  # MB
            self.last_update = now
    
    def get_stats(self):
        return {
            'cpu': self.cpu_percent,
            'memory': self.memory_percent,
            'disk': self.disk_percent,
            'net_sent': self.network_sent,
            'net_recv': self.network_recv
        }

# Notification system
class NotificationSystem:
    def __init__(self):
        self.notifications = []
        self.max_notifications = 5
        
    def add(self, message, duration=3.0):
        self.notifications.append({
            'message': message,
            'time': time.time(),
            'duration': duration
        })
        if len(self.notifications) > self.max_notifications:
            self.notifications.pop(0)
    
    def get_active(self):
        now = time.time()
        active = []
        for notif in self.notifications:
            if now - notif['time'] < notif['duration']:
                active.append(notif)
        self.notifications = active
        return active

# Action executor
def execute_action(action_name, notifications):
    """Execute gesture-triggered actions"""
    if not ACTIONS_ENABLED:
        notifications.add('[INFO] Actions disabled')
        return False
    try:
        if action_name == 'activate_chrome':
            subprocess.Popen(['chrome', '--new-window'])
            notifications.add('[OK] Opening Chrome Browser')
            speak_text('Opening Chrome')
            return True
        elif action_name == 'close_window':
            # Send Alt+F4 on Windows
            import pyautogui
            pyautogui.hotkey('alt', 'F4')
            notifications.add('[OK] Closing Window')
            speak_text('Closing window')
            return True
        elif action_name == 'next_tab':
            import pyautogui
            pyautogui.hotkey('ctrl', 'tab')
            notifications.add('[>>] Next Tab')
            return True
        elif action_name == 'prev_tab':
            import pyautogui
            pyautogui.hotkey('ctrl', 'shift', 'tab')
            notifications.add('[<<] Previous Tab')
            return True
        elif action_name == 'volume_up':
            import pyautogui
            pyautogui.press('volumeup')
            notifications.add('[VOL+] Volume Up')
            return True
    except Exception as e:
        notifications.add(f'[ERROR] Action failed: {action_name}')
        print(f"Action error: {e}")
        return False
    return False


class StarkHUDElement:
    """Individual HUD element that can rotate and animate"""
    def __init__(self, element_type, position, size):
        self.type = element_type
        self.position = position  # (x_offset, y_offset) from face center
        self.size = size
        self.rotation = 0
        self.animation_time = 0
        self.pulse_phase = np.random.random() * 2 * np.pi
        self.segments_rotation = 0
        self.inner_rotation = 0
        
    def update(self, dt):
        """Update animation state"""
        self.animation_time += dt
        # Rotate elements at different speeds
        if self.type == 'arc_reactor':
            self.rotation += 20 * dt
            self.segments_rotation += 45 * dt
            self.inner_rotation -= 60 * dt
        elif self.type == 'targeting':
            self.rotation += 30 * dt
        elif self.type == 'radar':
            self.rotation += 60 * dt
        elif self.type in ['side_panel_left', 'side_panel_right']:
            self.rotation += 10 * dt
        elif self.type == 'circular_menu':
            self.rotation += 25 * dt
        elif self.type == 'tech_rings':
            self.rotation += 15 * dt
        
        if self.rotation >= 360:
            self.rotation -= 360
        if self.segments_rotation >= 360:
            self.segments_rotation -= 360
        if self.inner_rotation <= -360:
            self.inner_rotation += 360
    
    def draw(self, frame, face_x, face_y):
        """Draw this HUD element"""
        x = int(face_x + self.position[0])
        y = int(face_y + self.position[1])
        
        if self.type == 'arc_reactor':
            self.draw_arc_reactor(frame, x, y)
        elif self.type == 'targeting':
            self.draw_targeting_reticle(frame, x, y)
        elif self.type == 'radar':
            self.draw_radar(frame, x, y)
        elif self.type == 'side_panel_left':
            self.draw_side_panel(frame, x, y, 'left')
        elif self.type == 'side_panel_right':
            self.draw_side_panel(frame, x, y, 'right')
        elif self.type == 'status_bars':
            self.draw_status_bars(frame, x, y)
        elif self.type == 'corner_brackets':
            self.draw_corner_brackets(frame, x, y)
        elif self.type == 'circular_menu':
            self.draw_circular_menu(frame, x, y)
        elif self.type == 'tech_rings':
            self.draw_tech_rings(frame, x, y)
        elif self.type == 'data_stream':
            self.draw_data_stream(frame, x, y)
    
    def draw_arc_reactor(self, frame, x, y):
        """Draw rotating arc reactor style circle - highly detailed"""
        cyan = (255, 255, 0)
        blue = (255, 200, 0)
        white = (255, 255, 255)
        
        # Multiple concentric circles
        for r_offset in [0, -5, -10, -15, -20]:
            cv2.circle(frame, (x, y), self.size + r_offset, cyan, 1)
        
        # Main outer circle
        cv2.circle(frame, (x, y), self.size, cyan, 3)
        
        # Rotating outer segments (24 segments)
        num_segments = 24
        for i in range(num_segments):
            angle = (self.segments_rotation + i * (360 / num_segments)) * np.pi / 180
            start_r = self.size - 12
            end_r = self.size - 2
            
            x1 = int(x + np.cos(angle) * start_r)
            y1 = int(y + np.sin(angle) * start_r)
            x2 = int(x + np.cos(angle) * end_r)
            y2 = int(y + np.sin(angle) * end_r)
            
            thickness = 3 if i % 3 == 0 else 1
            cv2.line(frame, (x1, y1), (x2, y2), cyan, thickness)
        
        # Middle ring with notches
        middle_r = self.size - 30
        cv2.circle(frame, (x, y), middle_r, blue, 2)
        for i in range(12):
            angle = (self.rotation + i * 30) * np.pi / 180
            x1 = int(x + np.cos(angle) * (middle_r - 5))
            y1 = int(y + np.sin(angle) * (middle_r - 5))
            x2 = int(x + np.cos(angle) * (middle_r + 5))
            y2 = int(y + np.sin(angle) * (middle_r + 5))
            cv2.line(frame, (x1, y1), (x2, y2), cyan, 2)
        
        # Inner rotating core with triangular segments
        inner_r = 25
        for i in range(6):
            angle = (self.inner_rotation + i * 60) * np.pi / 180
            x1 = int(x + np.cos(angle) * inner_r)
            y1 = int(y + np.sin(angle) * inner_r)
            x2 = int(x + np.cos(angle + 0.5) * (inner_r - 10))
            y2 = int(y + np.sin(angle + 0.5) * (inner_r - 10))
            cv2.line(frame, (x1, y1), (x2, y2), white, 2)
        
        # Center core
        cv2.circle(frame, (x, y), 10, cyan, 2)
        cv2.circle(frame, (x, y), 5, (0, 255, 255), -1)
        
        # Pulsing energy lines
        pulse = abs(np.sin(self.animation_time * 3))
        for i in range(4):
            angle = (self.rotation * 3 + i * 90) * np.pi / 180
            x1 = int(x + np.cos(angle) * 15)
            y1 = int(y + np.sin(angle) * 15)
            x2 = int(x + np.cos(angle) * (self.size - 25))
            y2 = int(y + np.sin(angle) * (self.size - 25))
            color = (int(255 * pulse), 255, int(255 * (1 - pulse)))
            cv2.line(frame, (x1, y1), (x2, y2), color, 1)
    
    def draw_targeting_reticle(self, frame, x, y):
        """Draw rotating targeting reticle"""
        red = (0, 0, 255)
        orange = (0, 165, 255)
        
        # Outer circle
        cv2.circle(frame, (x, y), self.size, red, 2)
        
        # Rotating crosshairs
        for i in range(4):
            angle = (self.rotation + i * 90) * np.pi / 180
            start_r = self.size - 20
            end_r = self.size + 10
            
            x1 = int(x + np.cos(angle) * start_r)
            y1 = int(y + np.sin(angle) * start_r)
            x2 = int(x + np.cos(angle) * end_r)
            y2 = int(y + np.sin(angle) * end_r)
            
            cv2.line(frame, (x1, y1), (x2, y2), orange, 2)
        
        # Inner crosshair
        line_len = 20
        cv2.line(frame, (x - line_len, y), (x + line_len, y), red, 2)
        cv2.line(frame, (x, y - line_len), (x, y + line_len), red, 2)
        
        # Corner brackets
        bracket_size = 15
        for i in range(4):
            angle = (45 + i * 90) * np.pi / 180
            bx = int(x + np.cos(angle) * self.size)
            by = int(y + np.sin(angle) * self.size)
            
            # Draw L-shaped bracket
            dx = int(np.cos(angle) * bracket_size)
            dy = int(np.sin(angle) * bracket_size)
            cv2.line(frame, (bx, by), (bx + dx, by), red, 2)
            cv2.line(frame, (bx, by), (bx, by + dy), red, 2)
    
    def draw_radar(self, frame, x, y):
        """Draw rotating radar sweep"""
        green = (0, 255, 0)
        dark_green = (0, 150, 0)
        
        # Radar circles
        for r in range(20, self.size, 20):
            cv2.circle(frame, (x, y), r, dark_green, 1)
        
        # Rotating sweep line
        angle = self.rotation * np.pi / 180
        x_end = int(x + np.cos(angle) * self.size)
        y_end = int(y + np.sin(angle) * self.size)
        cv2.line(frame, (x, y), (x_end, y_end), green, 2)
        
        # Sweep fade effect (draw multiple lines)
        for i in range(1, 6):
            fade_angle = (self.rotation - i * 10) * np.pi / 180
            x_fade = int(x + np.cos(fade_angle) * self.size)
            y_fade = int(y + np.sin(fade_angle) * self.size)
            alpha = 1 - (i / 6)
            color = (0, int(255 * alpha), 0)
            cv2.line(frame, (x, y), (x_fade, y_fade), color, 1)
        
        # Random blips
        np.random.seed(int(self.animation_time * 10) % 1000)
        for _ in range(3):
            blip_r = np.random.randint(10, self.size)
            blip_angle = np.random.random() * 2 * np.pi
            bx = int(x + np.cos(blip_angle) * blip_r)
            by = int(y + np.sin(blip_angle) * blip_r)
            cv2.circle(frame, (bx, by), 3, green, -1)
    
    def draw_side_panel(self, frame, x, y, side):
        """Draw detailed side information panel"""
        cyan = (255, 255, 0)
        blue = (255, 150, 0)
        green = (0, 255, 0)
        
        width = 150
        height = 250
        
        if side == 'left':
            x1, y1 = x - width, y - height // 2
            x2, y2 = x, y + height // 2
        else:
            x1, y1 = x, y - height // 2
            x2, y2 = x + width, y + height // 2
        
        # Panel border with animation
        pulse = abs(np.sin(self.animation_time * 2 + self.pulse_phase))
        color = (int(255 * pulse), 255, 0)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
        cv2.rectangle(frame, (x1 + 5, y1 + 5), (x2 - 5, y2 - 5), blue, 1)
        
        # Animated corner markers
        corner_size = 15
        corners = [(x1, y1), (x2, y1), (x1, y2), (x2, y2)]
        for idx, (cx, cy) in enumerate(corners):
            cv2.line(frame, (cx - corner_size, cy), (cx + corner_size, cy), cyan, 3)
            cv2.line(frame, (cx, cy - corner_size), (cx, cy + corner_size), cyan, 3)
            cv2.circle(frame, (cx, cy), 4, green, -1)
        
        # Horizontal scan lines
        for i in range(0, height, 12):
            scan_y = y1 + i
            scan_progress = ((self.animation_time * 50) % height) / height
            if abs((i / height) - scan_progress) < 0.1:
                cv2.line(frame, (x1 + 5, scan_y), (x2 - 5, scan_y), cyan, 2)
            else:
                cv2.line(frame, (x1 + 5, scan_y), (x2 - 5, scan_y), blue, 1)
        
        # Text labels with more detail
        font = cv2.FONT_HERSHEY_SIMPLEX
        if side == 'left':
            cv2.putText(frame, 'SYSTEM', (x1 + 15, y1 + 30), font, 0.6, cyan, 2)
            cv2.putText(frame, 'STATUS', (x1 + 15, y1 + 55), font, 0.5, blue, 1)
            cv2.putText(frame, 'ONLINE', (x1 + 15, y1 + 80), font, 0.6, green, 2)
            
            # Progress bars
            cv2.rectangle(frame, (x1 + 15, y1 + 100), (x2 - 15, y1 + 110), cyan, 1)
            bar_fill = int((x2 - x1 - 30) * 0.95)
            cv2.rectangle(frame, (x1 + 15, y1 + 100), (x1 + 15 + bar_fill, y1 + 110), green, -1)
            
            cv2.putText(frame, 'NEURAL', (x1 + 15, y1 + 135), font, 0.5, blue, 1)
            cv2.putText(frame, 'LINK', (x1 + 15, y1 + 155), font, 0.5, blue, 1)
            cv2.putText(frame, 'ACTIVE', (x1 + 15, y1 + 175), font, 0.5, green, 1)
        else:
            cv2.putText(frame, 'POWER', (x1 + 15, y1 + 30), font, 0.6, cyan, 2)
            cv2.putText(frame, 'CORE', (x1 + 15, y1 + 55), font, 0.5, blue, 1)
            cv2.putText(frame, '98%', (x1 + 15, y1 + 85), font, 0.7, green, 2)
            
            # Power bars
            for bar_idx in range(3):
                bar_y = y1 + 110 + bar_idx * 25
                cv2.rectangle(frame, (x1 + 15, bar_y), (x2 - 15, bar_y + 10), cyan, 1)
                bar_percent = 0.98 - bar_idx * 0.05
                bar_fill = int((x2 - x1 - 30) * bar_percent)
                cv2.rectangle(frame, (x1 + 15, bar_y), (x1 + 15 + bar_fill, bar_y + 10), green, -1)
            
            cv2.putText(frame, 'STABLE', (x1 + 15, y1 + 210), font, 0.5, green, 1)
    
    def draw_status_bars(self, frame, x, y):
        """Draw detailed status bars at top"""
        cyan = (255, 255, 0)
        green = (0, 255, 0)
        white = (255, 255, 255)
        
        width = 400
        height = 80
        
        x1, y1 = x - width // 2, y
        x2, y2 = x + width // 2, y + height
        
        # Main frame with double border
        cv2.rectangle(frame, (x1, y1), (x2, y2), cyan, 3)
        cv2.rectangle(frame, (x1 + 5, y1 + 5), (x2 - 5, y2 - 5), cyan, 1)
        
        # Corner decorations
        corner_size = 12
        for cx in [x1, x2]:
            for cy in [y1, y2]:
                cv2.line(frame, (cx - corner_size, cy), (cx + corner_size, cy), white, 2)
                cv2.line(frame, (cx, cy - corner_size), (cx, cy + corner_size), white, 2)
        
        # Title with glow effect
        cv2.putText(frame, 'J.A.R.V.I.S. ACTIVE', (x1 + 40, y1 + 35), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, cyan, 3)
        cv2.putText(frame, 'J.A.R.V.I.S. ACTIVE', (x1 + 40, y1 + 35), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, white, 1)
        
        # Animated progress bar
        progress = (np.sin(self.animation_time * 2) + 1) / 2
        bar_width = int((x2 - x1 - 80) * progress)
        cv2.rectangle(frame, (x1 + 40, y1 + 50), (x2 - 40, y1 + 62), cyan, 2)
        cv2.rectangle(frame, (x1 + 40, y1 + 50), 
                     (x1 + 40 + bar_width, y1 + 62), green, -1)
        
        # Status indicators
        cv2.putText(frame, 'SYS', (x1 + 10, y1 + 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, green, 1)
        cv2.circle(frame, (x1 + 18, y1 + 70), 3, green, -1)
    
    def draw_corner_brackets(self, frame, x, y):
        """Draw detailed corner brackets around face"""
        cyan = (255, 255, 0)
        red = (0, 0, 255)
        size = self.size
        bracket_len = 40
        
        # Animated pulse
        pulse = abs(np.sin(self.animation_time * 3 + self.pulse_phase))
        thickness = int(2 + pulse * 2)
        
        corners = [
            (x - size, y - size),
            (x + size, y - size),
            (x - size, y + size),
            (x + size, y + size)
        ]
        
        for i, (cx, cy) in enumerate(corners):
            # Determine direction for L-bracket
            h_dir = 1 if i % 2 == 1 else -1
            v_dir = 1 if i >= 2 else -1
            
            # Multiple layer brackets
            for offset in [0, 5, 10]:
                cv2.line(frame, (cx, cy), (cx + h_dir * (bracket_len - offset), cy), cyan, thickness)
                cv2.line(frame, (cx, cy), (cx, cy + v_dir * (bracket_len - offset)), cyan, thickness)
            
            # Corner decorations
            cv2.circle(frame, (cx, cy), 5, (0, 255, 255), -1)
            cv2.circle(frame, (cx, cy), 8, cyan, 2)
            
            # Notches on brackets
            for notch in range(3):
                notch_pos = 15 + notch * 10
                nx1 = cx + h_dir * notch_pos
                ny1 = cy + v_dir * notch_pos
                cv2.line(frame, (nx1, cy), (nx1, cy + v_dir * 5), red, 1)
                cv2.line(frame, (cx, ny1), (cx + h_dir * 5, ny1), red, 1)
    
    def draw_circular_menu(self, frame, x, y):
        """Draw circular menu with segments"""
        cyan = (255, 255, 0)
        white = (255, 255, 255)
        
        num_segments = 8
        inner_r = self.size - 20
        outer_r = self.size
        
        # Draw segments
        for i in range(num_segments):
            angle1 = (self.rotation + i * (360 / num_segments) - 10) * np.pi / 180
            angle2 = (self.rotation + (i + 1) * (360 / num_segments) - 10) * np.pi / 180
            
            # Draw arc segment
            pts_outer = []
            pts_inner = []
            for angle in np.linspace(angle1, angle2, 20):
                pts_outer.append([int(x + np.cos(angle) * outer_r), int(y + np.sin(angle) * outer_r)])
                pts_inner.append([int(x + np.cos(angle) * inner_r), int(y + np.sin(angle) * inner_r)])
            
            if i % 2 == 0:
                for j in range(len(pts_outer) - 1):
                    cv2.line(frame, tuple(pts_outer[j]), tuple(pts_outer[j + 1]), cyan, 2)
                    cv2.line(frame, tuple(pts_inner[j]), tuple(pts_inner[j + 1]), cyan, 2)
        
        # Connecting lines
        for i in range(num_segments):
            angle = (self.rotation + i * (360 / num_segments)) * np.pi / 180
            x1 = int(x + np.cos(angle) * inner_r)
            y1 = int(y + np.sin(angle) * inner_r)
            x2 = int(x + np.cos(angle) * outer_r)
            y2 = int(y + np.sin(angle) * outer_r)
            cv2.line(frame, (x1, y1), (x2, y2), cyan, 1)
    
    def draw_tech_rings(self, frame, x, y):
        """Draw technical detail rings"""
        cyan = (255, 255, 0)
        blue = (255, 200, 0)
        
        # Multiple rotating rings with details
        for ring_idx, r in enumerate([self.size, self.size - 15, self.size - 30]):
            cv2.circle(frame, (x, y), r, cyan, 1)
            
            # Add tick marks
            num_ticks = 32 - ring_idx * 8
            for i in range(num_ticks):
                angle = (self.rotation * (1 + ring_idx * 0.5) + i * (360 / num_ticks)) * np.pi / 180
                x1 = int(x + np.cos(angle) * (r - 3))
                y1 = int(y + np.sin(angle) * (r - 3))
                x2 = int(x + np.cos(angle) * (r + 3))
                y2 = int(y + np.sin(angle) * (r + 3))
                thickness = 2 if i % 4 == 0 else 1
                cv2.line(frame, (x1, y1), (x2, y2), blue, thickness)
    
    def draw_data_stream(self, frame, x, y):
        """Draw streaming data effect"""
        green = (0, 255, 0)
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        # Scrolling data text
        data_items = ['SYS:OK', 'PWR:98%', 'NET:ON', 'CAM:HD', 'AI:ACT']
        offset = int((self.animation_time * 30) % 100)
        
        for i, item in enumerate(data_items):
            y_pos = y + i * 20 - offset
            if 0 < y_pos < frame.shape[0]:
                alpha = 1.0 - abs(y_pos - y) / 100
                color = (0, int(255 * alpha), 0)
                cv2.putText(frame, item, (x, y_pos), font, 0.4, color, 1)


class StarkHUDSystem:
    """Manages all HUD elements"""
    def __init__(self):
        self.elements = []
        self.last_time = time.time()
        self.system_monitor = SystemMonitor()
        self.notifications = NotificationSystem()
        self.init_elements()
    
    def init_elements(self):
        """No face-anchored elements (clean view)"""
        self.elements = []
    
    def update(self):
        """Update all elements and system stats"""
        current_time = time.time()
        dt = current_time - self.last_time
        self.last_time = current_time
        
        for element in self.elements:
            element.update(dt)
        
        self.system_monitor.update()
    
    def draw(self, frame, face_x, face_y, gesture_label='STANDBY', fps=0):
        """Draw clean, organized HUD"""
        h, w = frame.shape[:2]
        cyan = (255, 255, 0)
        green = (0, 255, 0)
        red = (0, 0, 255)
        white = (255, 255, 255)
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        # Draw minimal face tracking elements
        for element in self.elements:
            element.draw(frame, face_x, face_y)
        
        # Top left - System stats panel
        self.draw_system_panel(frame, 20, 20)
        
        # Top right - Gesture info panel
        self.draw_gesture_panel(frame, w - 320, 20, gesture_label)
        
        # Bottom left - Notifications
        self.draw_notifications(frame, 20, h - 200)
        
        # Bottom right - Action hints
        self.draw_action_hints(frame, w - 320, h - 250)
        
        # Center bottom - Gesture display (minimal)
        text = gesture_label
        text_size = cv2.getTextSize(text, font, 0.8, 2)[0]
        text_x = (w - text_size[0]) // 2
        text_y = h - 40
        
        cv2.rectangle(frame, (text_x - 15, text_y - 30), 
                     (text_x + text_size[0] + 15, text_y + 10), (0, 0, 0), -1)
        cv2.rectangle(frame, (text_x - 15, text_y - 30), 
                     (text_x + text_size[0] + 15, text_y + 10), cyan, 2)
        cv2.putText(frame, text, (text_x, text_y), font, 0.8, cyan, 2)
    
    def draw_system_panel(self, frame, x, y):
        """Draw system monitoring panel"""
        cyan = (255, 255, 0)
        green = (0, 255, 0)
        red = (0, 0, 255)
        yellow = (0, 255, 255)
        white = (255, 255, 255)
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        stats = self.system_monitor.get_stats()
        
        # Panel background
        cv2.rectangle(frame, (x, y), (x + 280, y + 160), (0, 0, 0), -1)
        cv2.rectangle(frame, (x, y), (x + 280, y + 160), cyan, 2)
        
        # Title
        cv2.putText(frame, 'SYSTEM STATUS', (x + 10, y + 25), font, 0.6, cyan, 2)
        cv2.line(frame, (x + 10, y + 30), (x + 270, y + 30), cyan, 1)
        
        # Time
        now = datetime.now().strftime("%H:%M:%S")
        cv2.putText(frame, f'TIME: {now}', (x + 10, y + 50), font, 0.5, white, 1)
        
        # CPU
        cpu_color = red if stats['cpu'] > 80 else (yellow if stats['cpu'] > 60 else green)
        cv2.putText(frame, f"CPU:  {stats['cpu']:.1f}%", (x + 10, y + 75), font, 0.5, white, 1)
        bar_width = int(240 * stats['cpu'] / 100)
        cv2.rectangle(frame, (x + 10, y + 80), (x + 250, y + 90), cyan, 1)
        cv2.rectangle(frame, (x + 10, y + 80), (x + 10 + bar_width, y + 90), cpu_color, -1)
        
        # Memory
        mem_color = red if stats['memory'] > 80 else (yellow if stats['memory'] > 60 else green)
        cv2.putText(frame, f"MEM:  {stats['memory']:.1f}%", (x + 10, y + 105), font, 0.5, white, 1)
        bar_width = int(240 * stats['memory'] / 100)
        cv2.rectangle(frame, (x + 10, y + 110), (x + 250, y + 120), cyan, 1)
        cv2.rectangle(frame, (x + 10, y + 110), (x + 10 + bar_width, y + 120), mem_color, -1)
        
        # Disk
        disk_color = red if stats['disk'] > 90 else green
        cv2.putText(frame, f"DISK: {stats['disk']:.1f}%", (x + 10, y + 135), font, 0.5, white, 1)
        bar_width = int(240 * stats['disk'] / 100)
        cv2.rectangle(frame, (x + 10, y + 140), (x + 250, y + 150), cyan, 1)
        cv2.rectangle(frame, (x + 10, y + 140), (x + 10 + bar_width, y + 150), disk_color, -1)
    
    def draw_gesture_panel(self, frame, x, y, gesture):
        """Draw gesture information panel"""
        cyan = (255, 255, 0)
        white = (255, 255, 255)
        green = (0, 255, 0)
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        # Panel background
        cv2.rectangle(frame, (x, y), (x + 300, y + 140), (0, 0, 0), -1)
        cv2.rectangle(frame, (x, y), (x + 300, y + 140), cyan, 2)
        
        # Title
        cv2.putText(frame, 'GESTURE CONTROL', (x + 10, y + 25), font, 0.6, cyan, 2)
        cv2.line(frame, (x + 10, y + 30), (x + 290, y + 30), cyan, 1)
        
        # Current gesture
        cv2.putText(frame, 'ACTIVE:', (x + 10, y + 55), font, 0.5, white, 1)
        cv2.putText(frame, gesture, (x + 90, y + 55), font, 0.6, green, 2)
        
        # Action mapping
        gesture_key = gesture.lower().replace(' ', '_')
        action = GESTURE_ACTIONS.get(gesture_key, 'none')
        cv2.putText(frame, 'ACTION:', (x + 10, y + 80), font, 0.5, white, 1)
        cv2.putText(frame, action.replace('_', ' ').title(), (x + 10, y + 100), font, 0.5, green, 1)
        
        # Status indicator
        cv2.circle(frame, (x + 280, y + 20), 8, green, -1)
        cv2.putText(frame, 'READY', (x + 220, y + 125), font, 0.5, green, 1)
    
    def draw_notifications(self, frame, x, y):
        """Draw notification panel"""
        cyan = (255, 255, 0)
        white = (255, 255, 255)
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        active_notifs = self.notifications.get_active()
        
        if not active_notifs:
            return
        
        # Panel background
        height = 40 + len(active_notifs) * 30
        cv2.rectangle(frame, (x, y), (x + 350, y + height), (0, 0, 0), -1)
        cv2.rectangle(frame, (x, y), (x + 350, y + height), cyan, 2)
        
        # Title
        cv2.putText(frame, 'NOTIFICATIONS', (x + 10, y + 25), font, 0.6, cyan, 2)
        
        # Notifications
        for i, notif in enumerate(active_notifs):
            cv2.putText(frame, notif['message'], (x + 10, y + 50 + i * 30), 
                       font, 0.5, white, 1)
    
    def draw_action_hints(self, frame, x, y):
        """Draw available actions panel"""
        cyan = (255, 255, 0)
        white = (255, 255, 255)
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        # Panel background
        cv2.rectangle(frame, (x, y), (x + 300, y + 230), (0, 0, 0), -1)
        cv2.rectangle(frame, (x, y), (x + 300, y + 230), cyan, 2)
        
        # Title
        cv2.putText(frame, 'AVAILABLE ACTIONS', (x + 10, y + 25), font, 0.6, cyan, 2)
        cv2.line(frame, (x + 10, y + 30), (x + 290, y + 30), cyan, 1)
        
        # Actions list
        actions = [
            'Open Palm: Open Chrome',
            'Fist: Close Window',
            'Thumbs Up: Confirm',
            'Swipe Right: Next Tab',
            'Swipe Left: Prev Tab',
            'Two Fingers: Volume Up',
            'Pointing: Cursor Mode'
        ]
        
        for i, action in enumerate(actions):
            cv2.putText(frame, action, (x + 10, y + 55 + i * 25), 
                       font, 0.4, white, 1)


def main():
    # Set camera to highest resolution
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    
    # Get actual resolution
    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    hud_system = StarkHUDSystem()
    
    # Welcome message
    print("=" * 60)
    print("STARK INDUSTRIES AR HUD SYSTEM")
    print("=" * 60)
    print(f"Resolution: {actual_width}x{actual_height}")
    print("Initializing voice system...")
    
    if VOICE_ENABLED:
        speak_text("Welcome to Stark Industries A R HUD system. All systems online.")
        time.sleep(0.5)
        speak_text("Gesture recognition system active.")
        print("[OK] Voice system active")
    else:
        print("[WARNING] Voice system disabled")
    
    print("[OK] Face tracking enabled")
    print("[OK] Gesture recognition loaded")
    print("\nControls:")
    print("  - ESC: Exit")
    print("  - F: Toggle fullscreen")
    print("=" * 60)
    
    # Create fullscreen window
    cv2.namedWindow('Stark Industries AR HUD', cv2.WINDOW_NORMAL)
    cv2.setWindowProperty('Stark Industries AR HUD', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    
    with mp_face_mesh.FaceMesh(
        static_image_mode=False,
        max_num_faces=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5) as face_mesh, \
         mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.6) as hands:
        
        last_gesture = ('', 0)
        last_action_time = 0
        action_cooldown = 2.0  # seconds between actions
        fps_time = time.time()
        fps_counter = 0
        fps_display = 0
        fullscreen = True
        first_gesture = True
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            h, w = frame.shape[:2]
            img = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Process face landmarks
            face_results = face_mesh.process(rgb)
            face_center_x, face_center_y = w // 2, h // 2
            
            if face_results.multi_face_landmarks:
                face_landmarks = face_results.multi_face_landmarks[0]
                # Use nose landmark as face center
                nose = face_landmarks.landmark[1]
                face_center_x = int(nose.x * w)
                face_center_y = int(nose.y * h)
            
            # Process hand gestures
            res = hands.process(rgb)
            gesture_label = 'STANDBY'
            
            if res.multi_hand_landmarks:
                lm = res.multi_hand_landmarks[0]
                mp_drawing.draw_landmarks(img, lm, mp_hands.HAND_CONNECTIONS,
                    mp_drawing.DrawingSpec(color=(0, 255, 255), thickness=3, circle_radius=4),
                    mp_drawing.DrawingSpec(color=(255, 255, 0), thickness=3))
                
                data = []
                for p in lm.landmark:
                    data.extend([p.x, p.y])
                x = scaler.transform([data])
                pred = clf.predict(x)[0]
                gesture_label = pred.upper().replace('_', ' ')
                now = time.time()
                
                # Announce gesture change with voice
                if pred != last_gesture[0]:
                    gesture_text = GESTURE_LABELS.get(pred, pred)
                    print(f"[GESTURE] Changed: {pred} -> {gesture_text}")
                    
                    # Speak the gesture
                    speak_text(gesture_text)
                    
                    # Execute action if cooldown passed
                    if now - last_action_time >= action_cooldown:
                        action = GESTURE_ACTIONS.get(pred, None)
                        if action and execute_action(action, hud_system.notifications):
                            last_action_time = now
                    
                    last_gesture = (pred, now)
                    first_gesture = False
                    
                elif now - last_gesture[1] > 5.0 and not first_gesture:
                    # Re-announce if holding same gesture
                    gesture_text = GESTURE_LABELS.get(pred, pred)
                    print(f"[GESTURE] Maintained: {gesture_text}")
                    speak_text(f"{gesture_text} maintained")
                    last_gesture = (pred, now)
            
            # Update and draw HUD system
            hud_system.update()
            
            # Calculate FPS
            fps_counter += 1
            if time.time() - fps_time > 1.0:
                fps_display = fps_counter
                fps_counter = 0
                fps_time = time.time()
            
            hud_system.draw(img, face_center_x, face_center_y, gesture_label, fps_display)
            
            # Draw FPS indicator
            cv2.putText(img, f'FPS: {fps_display}', (w // 2 - 50, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            cv2.imshow('Stark Industries AR HUD', img)
            
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC
                print('Shutting down Stark Industries HUD...')
                speak_text("Shutting down HUD system. Goodbye.")
                time.sleep(1.5)  # Give time for goodbye message
                break
            elif key == ord('f') or key == ord('F'):  # Toggle fullscreen
                fullscreen = not fullscreen
                if fullscreen:
                    cv2.setWindowProperty('Stark Industries AR HUD', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
                    print("[OK] Fullscreen mode enabled")
                else:
                    cv2.setWindowProperty('Stark Industries AR HUD', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
                    print("[OK] Windowed mode enabled")
        
        cap.release()
        cv2.destroyAllWindows()
        
        # Proper cleanup
        global voice_running
        voice_running = False
        voice_queue.put(None)
        
        # Wait for voice thread to finish
        if voice_thread.is_alive():
            voice_thread.join(timeout=2)
        
        print('[OK] Stark Industries HUD closed')


if __name__ == '__main__':
    main()
