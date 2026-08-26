import json
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk
import urllib.parse
import webbrowser
import cv2
import numpy as np
from PIL import Image, ImageGrab
import pytesseract
import requests
import winsound

# Set Tesseract binary path
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

# Path resolution for executable vs script
if getattr(sys, "frozen", False):
  SCRIPT_DIR = os.path.dirname(sys.executable)
else:
  SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")


class PlaceholderEntry(ttk.Entry):
  """Custom Entry widget that supports faded placeholder text."""

  def __init__(
      self, container, placeholder="", placeholder_color="gray", *args, **kwargs
  ):
    super().__init__(container, *args, **kwargs)
    self.placeholder = placeholder
    self.placeholder_color = placeholder_color
    self.default_fg_color = "black"

    self.is_placeholder_active = False

    # Bind focus events
    self.bind("<FocusIn>", self._clear_placeholder)
    self.bind("<FocusOut>", self._add_placeholder)

    self._add_placeholder()

  def _add_placeholder(self, event=None):
    if not self.get().strip():
      self.is_placeholder_active = True
      self.delete(0, tk.END)
      self.insert(0, self.placeholder)
      self.config(foreground=self.placeholder_color)

  def _clear_placeholder(self, event=None):
    if self.is_placeholder_active:
      self.delete(0, tk.END)
      self.config(foreground=self.default_fg_color)
      self.is_placeholder_active = False

  def get_value(self):
    """Returns actual text, ignoring placeholder text."""
    if self.is_placeholder_active:
      return ""
    return self.get().strip()

  def set_value(self, text):
    """Sets a value programmatically (e.g. from saved config)."""
    if text:
      self.is_placeholder_active = False
      self.delete(0, tk.END)
      self.insert(0, text)
      self.config(foreground=self.default_fg_color)
    else:
      self._add_placeholder()


class MIR4MonitorGUI:

  def __init__(self, root):
    self.root = root
    self.root.title("MIR4 Screen Monitor & Alert System")
    self.root.geometry("540x580")
    self.root.resizable(False, False)

    self.bbox = None
    self.monitoring = False
    self.in_combat_state = False
    self.last_beep_time = 0

    self._build_ui()
    self.load_config()
    self.log(f"System initialized. Config path: {CONFIG_FILE}")

  def _build_ui(self):
    self.notebook = ttk.Notebook(self.root)
    self.notebook.pack(fill="both", expand=True)

    self.main_tab = ttk.Frame(self.notebook)
    self.about_tab = ttk.Frame(self.notebook)

    self.notebook.add(self.main_tab, text=" Monitor Controls ")
    self.notebook.add(self.about_tab, text=" About ")

    self._build_main_tab()
    self._build_about_tab()

  def _build_main_tab(self):
    padding = {"padx": 10, "pady": 4}

    # Target Text Configuration with Placeholder
    ttk.Label(
        self.main_tab,
        text="Target Text to Detect:",
        font=("Segoe UI", 9, "bold"),
    ).pack(anchor="w", **padding)
    self.target_text_entry = PlaceholderEntry(
        self.main_tab, placeholder="e.g. In combat", width=60
    )
    self.target_text_entry.pack(fill="x", **padding)

    # NTFY Topic Configuration with Placeholder
    ttk.Label(
        self.main_tab, text="ntfy.sh Topic Name:", font=("Segoe UI", 9, "bold")
    ).pack(anchor="w", **padding)
    self.ntfy_entry = PlaceholderEntry(
        self.main_tab, placeholder="e.g. my_mir4_topic_123", width=60
    )
    self.ntfy_entry.pack(fill="x", **padding)

    # Region Selection Button
    self.select_btn = ttk.Button(
        self.main_tab,
        text="1. Select Screen Area (Auto-Minimizes)",
        command=self.trigger_region_selection,
    )
    self.select_btn.pack(fill="x", **padding)

    self.region_label = ttk.Label(
        self.main_tab,
        text="Selected Region: None",
        foreground="gray",
        font=("Segoe UI", 9, "italic"),
    )
    self.region_label.pack(anchor="w", **padding)

    ttk.Separator(self.main_tab, orient="horizontal").pack(
        fill="x", pady=6, padx=10
    )

    # Control Buttons
    self.start_btn = ttk.Button(
        self.main_tab,
        text="2. Start Monitoring",
        command=self.start_monitoring,
        state="disabled",
    )
    self.start_btn.pack(fill="x", **padding)

    self.stop_btn = ttk.Button(
        self.main_tab,
        text="Stop Monitoring",
        command=self.stop_monitoring,
        state="disabled",
    )
    self.stop_btn.pack(fill="x", **padding)

    # Status Display
    self.status_label = ttk.Label(
        self.main_tab,
        text="Status: Idle",
        font=("Segoe UI", 9, "bold"),
        foreground="blue",
    )
    self.status_label.pack(anchor="w", **padding)

    # Debug Log Display
    ttk.Label(
        self.main_tab, text="Debug Log:", font=("Segoe UI", 9, "bold")
    ).pack(anchor="w", **padding)
    self.log_text = tk.Text(
        self.main_tab,
        height=7,
        width=60,
        font=("Consolas", 8),
        state="disabled",
    )
    self.log_text.pack(fill="both", expand=True, **padding)

  def _build_about_tab(self):
    padding = {"padx": 15, "pady": 6}

    ttk.Label(
        self.about_tab,
        text="MIR4 Screen Monitor & Alert System",
        font=("Segoe UI", 12, "bold"),
    ).pack(anchor="w", **padding)
    ttk.Label(
        self.about_tab,
        text="Created by: demigeek",
        font=("Segoe UI", 10, "bold"),
        foreground="#2c3e50",
    ).pack(anchor="w", padx=15, pady=2)

    report_btn = ttk.Button(
        self.about_tab,
        text="✉ Report Bug / Send Feedback",
        command=self.open_email_client,
    )
    report_btn.pack(anchor="w", padx=15, pady=6)

    ttk.Separator(self.about_tab, orient="horizontal").pack(
        fill="x", pady=10, padx=15
    )

    ttk.Label(
        self.about_tab,
        text="BETA SOFTWARE DISCLAIMER",
        font=("Segoe UI", 9, "bold"),
        foreground="#c0392b",
    ).pack(anchor="w", padx=15, pady=(4, 2))

    disclaimer_text = (
        "This application is currently in active Beta development. "
        "While functional, it may contain unhandled edge cases, OCR inaccuracies, "
        "or unexpected errors depending on system scaling and screen setups.\n\n"
        "USE AT YOUR OWN RISK:\n"
        "This software is provided 'as-is' without warranties of any kind. "
        "The developer assumes no responsibility or liability for missed alerts, "
        "game character deaths, or unintended software behavior during automated execution."
    )

    disc_box = tk.Text(
        self.about_tab,
        height=9,
        width=55,
        font=("Segoe UI", 9),
        wrap="word",
        bg="#f8f9fa",
        relief="solid",
        bd=1,
    )
    disc_box.insert(tk.END, disclaimer_text)
    disc_box.config(state="disabled")
    disc_box.pack(fill="x", padx=15, pady=5)

  def open_email_client(self):
    recipient = "furny777@gmail.com"
    subject = "MIR4 Monitor Bug Report / Feedback"
    body = (
        "Hi demigeek,\n\n"
        "I found a bug / have feedback regarding the MIR4 Screen Monitor app:\n\n"
        "[Describe your issue or suggestion here]\n\n"
        "System Specs / Windows Version (Optional): "
    )

    query_params = urllib.parse.urlencode({"subject": subject, "body": body})
    mailto_url = f"mailto:{recipient}?{query_params}"

    try:
      webbrowser.open(mailto_url)
      self.log("Opened default email client for bug reporting.")
    except Exception as e:
      self.log(f"[ERROR] Could not open email client: {e}")
      messagebox.showerror(
          "Error",
          f"Failed to open mail client automatically.\nPlease email manually to: {recipient}",
      )

  def save_config(self):
    config_data = {
        "target_text": self.target_text_entry.get_value(),
        "ntfy_topic": self.ntfy_entry.get_value(),
        "bbox": list(self.bbox) if self.bbox else None,
    }
    try:
      with open(CONFIG_FILE, "w") as f:
        json.dump(config_data, f, indent=4)
      self.log(f"Configuration saved successfully to: {CONFIG_FILE}")
    except Exception as e:
      self.log(f"[ERROR] Failed to save config: {e}")

  def load_config(self):
    if not os.path.exists(CONFIG_FILE):
      self.log("No config.json found on startup. Using defaults.")
      return

    try:
      with open(CONFIG_FILE, "r") as f:
        config_data = json.load(f)

      if config_data.get("target_text"):
        self.target_text_entry.set_value(config_data["target_text"])

      if config_data.get("ntfy_topic"):
        self.ntfy_entry.set_value(config_data["ntfy_topic"])

      if config_data.get("bbox"):
        self.bbox = tuple(config_data["bbox"])
        self.region_label.config(
            text=f"Selected Region: {self.bbox}", foreground="green"
        )
        self.start_btn.config(state="normal")
        self.log(f"Restored saved screen region: {self.bbox}")

    except Exception as e:
      self.log(f"[ERROR] Failed to load config: {e}")

  def log(self, message):
    def _update():
      timestamp = time.strftime("%H:%M:%S")
      formatted_msg = f"[{timestamp}] {message}\n"
      self.log_text.config(state="normal")
      self.log_text.insert(tk.END, formatted_msg)
      self.log_text.see(tk.END)
      self.log_text.config(state="disabled")

    self.root.after(0, _update)

  def send_phone_notification(self, message, title="MIR4 Alert"):
    ntfy_topic = self.ntfy_entry.get_value()
    if not ntfy_topic:
      return

    def _send():
      try:
        self.log(f"Sending push notification: '{message}'")
        requests.post(
            f"https://ntfy.sh/{ntfy_topic}",
            data=message.encode("utf-8"),
            headers={
                "Title": title,
                "Priority": "high",
                "Tags": "warning,swords",
            },
            timeout=5,
        )
      except Exception as e:
        self.log(f"[ERROR] Failed to send push notification: {e}")

    threading.Thread(target=_send, daemon=True).start()

  def trigger_region_selection(self):
    self.log("Triggering screen capture mode...")
    self.root.iconify()
    time.sleep(0.5)

    try:
      img_pil = ImageGrab.grab()
      img_bgr = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
      clone = img_bgr.copy()

      start_point, end_point = None, None
      selecting = False

      def mouse_handler(event, x, y, flags, param):
        nonlocal start_point, end_point, selecting
        if event == cv2.EVENT_LBUTTONDOWN:
          selecting = True
          start_point, end_point = (x, y), (x, y)
        elif event == cv2.EVENT_MOUSEMOVE and selecting:
          end_point = (x, y)
        elif event == cv2.EVENT_LBUTTONUP:
          selecting = False
          end_point = (x, y)

      window_name = "Drag Box Over Target Area - Press ENTER/SPACE when done"
      cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
      cv2.setWindowProperty(
          window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN
      )
      cv2.setMouseCallback(window_name, mouse_handler)

      while True:
        temp_img = clone.copy()
        if start_point and end_point:
          cv2.rectangle(temp_img, start_point, end_point, (0, 255, 0), 2)

        cv2.imshow(window_name, temp_img)
        key = cv2.waitKey(1) & 0xFF
        if key in (13, 32) and start_point and end_point:
          break

      cv2.destroyAllWindows()

      x1, y1 = min(start_point[0], end_point[0]), min(
          start_point[1], end_point[1]
      )
      x2, y2 = max(start_point[0], end_point[0]), max(
          start_point[1], end_point[1]
      )

      self.bbox = (x1, y1, x2, y2)
      self.region_label.config(
          text=f"Selected Region: {self.bbox}", foreground="green"
      )
      self.start_btn.config(state="normal")
      self.log(f"Region selected successfully: {self.bbox}")
      self.save_config()

    except Exception as e:
      cv2.destroyAllWindows()
      self.log(f"[ERROR] Selection failed: {e}")
      messagebox.showerror(
          "Selection Error", f"Failed to capture screen: {e}"
      )
    finally:
      self.root.deiconify()

  def start_monitoring(self):
    if not self.bbox:
      messagebox.showwarning(
          "Missing Selection", "Please select a screen area first."
      )
      return

    target_val = self.target_text_entry.get_value()
    if not target_val:
      messagebox.showwarning(
          "Missing Input", "Please specify target text to watch for."
      )
      return

    self.save_config()

    self.monitoring = True
    self.start_btn.config(state="disabled")
    self.select_btn.config(state="disabled")
    self.stop_btn.config(state="normal")
    self.status_label.config(text="Status: Active", foreground="green")
    self.log("Started monitoring thread...")

    threading.Thread(target=self._monitor_loop, daemon=True).start()

  def stop_monitoring(self):
    self.log("Stopping monitoring loop...")
    self.monitoring = False
    self.start_btn.config(state="normal")
    self.select_btn.config(state="normal")
    self.stop_btn.config(state="disabled")
    self.status_label.config(text="Status: Idle", foreground="blue")

  def _play_beep(self):
    winsound.Beep(1500, 200)

  def _monitor_loop(self):
    target_text = self.target_text_entry.get_value().lower()
    self.log(f"OCR actively searching for text string: '{target_text}'")

    try:
      while self.monitoring:
        img_pil = ImageGrab.grab(bbox=self.bbox)

        gray = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2GRAY)
        _, processed = cv2.threshold(
            gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )

        detected_text = pytesseract.image_to_string(
            processed, config="--psm 6"
        ).strip()

        preview = cv2.resize(
            processed, None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST
        )
        cv2.imshow("OCR Region Feed (Press Q to exit)", preview)

        if cv2.waitKey(10) & 0xFF == ord("q"):
          self.log("Manual quit requested via OpenCV window ('Q' pressed).")
          self.root.after(0, self.stop_monitoring)
          break

        if target_text in detected_text.lower():
          if not self.in_combat_state:
            self.in_combat_state = True
            self.log(f"[ALERT TRIGGERED] Recognized text: '{detected_text}'")
            self.send_phone_notification(
                f"Target text '{target_text}' detected on screen!",
                title="MIR4 Alert Triggered",
            )

          current_time = time.time()
          if current_time - self.last_beep_time > 0.3:
            threading.Thread(target=self._play_beep, daemon=True).start()
            self.last_beep_time = current_time

        else:
          if self.in_combat_state:
            self.in_combat_state = False
            self.log("[ALERT CLEARED] Target text is no longer visible.")
            self.send_phone_notification(
                "Target text cleared.", title="MIR4 Alert Cleared"
            )

        time.sleep(0.05)

    except Exception as e:
      self.log(f"[CRITICAL ERROR] Monitor thread crashed: {e}")
      self.root.after(
          0,
          lambda: messagebox.showerror(
              "Runtime Error", f"Error during screen monitoring: {e}"
          ),
      )
    finally:
      cv2.destroyAllWindows()
      cv2.waitKey(1)
      self.log("Monitoring stopped cleanly. Windows destroyed.")
      self.root.after(0, self.stop_monitoring)


if __name__ == "__main__":
  root = tk.Tk()
  app = MIR4MonitorGUI(root)
  root.mainloop()