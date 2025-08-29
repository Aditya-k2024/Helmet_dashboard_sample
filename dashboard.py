import sys
import random
import json
import time
import csv
import os
from datetime import datetime
from collections import deque
from typing import Deque, Tuple, List, Optional
import requests
from urllib.request import urlopen

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QGridLayout, QGraphicsDropShadowEffect,
                             QPushButton, QFormLayout, QSizePolicy, QStackedWidget,
                             QListWidget, QListWidgetItem, QLineEdit, QMessageBox)
from PySide6.QtCore import (Qt, QPropertyAnimation, QPointF, QTimer, QRectF,
                          Property, QEasingCurve, QUrl, Slot, Signal, QThread)
from PySide6.QtGui import (QColor, QPainter, QBrush, QPen, QFont, QPainterPath, QIcon, QPolygonF, QPixmap)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage

# --- Configurations ---
CSV_FILE = "demo_data.csv"
MAX_POINTS = 100
API_KEY = "1d7f134a5c8ece4a227d6f300221907c" # <<< PASTE YOUR KEY HERE
CITY = "New"

# --- MODIFIED: Added 'battery' to the CSV generation ---
def generate_sample_csv(filename="demo_data.csv", num_rows=100, num_helmets=10):
    print(f"Generating {num_rows} rows of sample data for {num_helmets} helmets in {filename}...")
    helmet_ids = [f"SH-{i:03d}" for i in range(1, num_helmets + 1)]
    header = ["timestamp", "helmetId", "gas", "temperature", "humidity", "latitude", "longitude", "emergency", "battery"]
    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        for _ in range(num_rows):
            helmet_id = random.choice(helmet_ids); gas = random.uniform(901, 1200) if random.random() < 0.1 else random.uniform(300, 800); emergency = True if random.random() < 0.02 else False
            row = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "helmetId": helmet_id, "gas": f"{gas:.2f}", "temperature": f"{random.uniform(28.0, 35.0):.2f}", "humidity": f"{random.uniform(45.0, 65.0):.2f}", "latitude": f"{28.6139 + random.uniform(-0.05, 0.05):.6f}", "longitude": f"{77.2090 + random.uniform(-0.05, 0.05):.6f}", "emergency": emergency, "battery": random.randint(5, 100)}
            writer.writerow(row)
    print("Sample data generation complete.")

# (AnimatedLabel, HoverButton, and other widget classes are unchanged and can be collapsed)
class AnimatedLabel(QLabel):
    def __init__(self, is_float=False, parent=None):
        super().__init__("0", parent); self._is_float = is_float; self._value = 0.0
        self.animation = QPropertyAnimation(self, b"value", self); self.animation.setDuration(400); self.animation.setEasingCurve(QEasingCurve.OutCubic)
    @Property(float)
    def value(self): return self._value
    @value.setter
    def value(self, new_value):
        self._value = new_value; self.setText(f"{new_value:.1f}" if self._is_float else f"{int(new_value)}")
    def animate_to_value(self, end_value):
        self.animation.setEndValue(end_value); self.animation.start()
class HoverButton(QPushButton):
    def __init__(self, icon_path="", text="", parent=None):
        super().__init__(text, parent)
        if icon_path and os.path.exists(icon_path):
            self.setIcon(QIcon(icon_path)); self.setIconSize(self.sizeHint().boundedTo(self.size()*0.6))
        self.setStyleSheet(""" ... STYLESHEET UNCHANGED ... """)
class WebEnginePage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceId):
        print(f"JS Console ({sourceId}:{lineNumber}): {message}")
class ZoomableWebEngineView(QWebEngineView):
    def wheelEvent(self, event):
        event.ignore()
class MapWidget(QWidget):
    def __init__(self, is_fleet_map=False):
        super().__init__(); self.is_fleet_map = is_fleet_map; self.setObjectName("card"); layout = QVBoxLayout(self); layout.setContentsMargins(0,0,0,0); self.webview = ZoomableWebEngineView(); self.webview.setPage(WebEnginePage(self)); self.webview.setHtml(self.get_map_html(28.6139, 77.2090)); self.webview.page().setBackgroundColor(Qt.transparent); layout.addWidget(self.webview)
    def get_map_html(self, lat, lng):
        return f"""<!DOCTYPE html><html><head><title>Map</title><meta charset="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0"><link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css"/><script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script><style>body {{ margin:0; padding:0; background-color: transparent; }} #map {{ height: 100vh; width: 100%; border-radius: 16px; }}</style></head><body><div id="map"></div><script>var map = L.map('map', {{ zoomControl: true }}).setView([{lat}, {lng}], 13); L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}.png', {{ attribution: '&copy; OpenStreetMap &copy; CartoDB' }}).addTo(map); var markerLayer = L.layerGroup().addTo(map); var redIcon = new L.Icon({{ iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png', shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png', iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34], shadowSize: [41, 41] }});</script></body></html>"""
    def update_marker(self, lat, lng):
        js_code = f"""if (typeof map !== 'undefined' && typeof markerLayer !== 'undefined') {{ markerLayer.clearLayers(); var marker = L.marker([{lat}, {lng}], {{icon: redIcon}}); markerLayer.addLayer(marker); map.setView([{lat}, {lng}], 13); }}"""
        self.webview.page().runJavaScript(js_code)
    def update_all_markers(self, helmets_data):
        if not helmets_data: return
        helmets_json = json.dumps([{"id": hel_id, "lat": data[-1]['latitude'], "lng": data[-1]['longitude']} for hel_id, data in helmets_data.items() if data])
        js_code = f"""if (typeof map !== 'undefined' && typeof markerLayer !== 'undefined') {{ markerLayer.clearLayers(); var helmets = {helmets_json}; helmets.forEach(function(helmet) {{ var marker = L.marker([helmet.lat, helmet.lng], {{icon: redIcon}}); marker.bindTooltip(helmet.id, {{ permanent: true, direction: 'top', offset: [0, -10] }}); markerLayer.addLayer(marker); }}); }}"""
        self.webview.page().runJavaScript(js_code)
class WeatherCard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent); self.setObjectName("card"); layout = QVBoxLayout(self); layout.setContentsMargins(15,15,15,15); self.city_label = QLabel("Loading..."); self.city_label.setObjectName("weatherCity"); self.icon_label = QLabel(); self.icon_label.setAlignment(Qt.AlignCenter); self.temp_label = QLabel("--°C"); self.temp_label.setObjectName("weatherTemp"); self.condition_label = QLabel("..."); self.condition_label.setObjectName("weatherCondition"); layout.addWidget(self.city_label); layout.addWidget(self.icon_label, 1); layout.addWidget(self.temp_label); layout.addWidget(self.condition_label)
    def update_content(self, data):
        self.city_label.setText(data.get('city', 'N/A')); self.temp_label.setText(f"{data.get('temp', '--')}°C"); self.condition_label.setText(data.get('condition', '...'))
        icon_url = data.get('icon_url')
        if icon_url:
            try:
                image_data = urlopen(icon_url).read(); pixmap = QPixmap(); pixmap.loadFromData(image_data); self.icon_label.setPixmap(pixmap)
            except Exception as e:
                print(f"Error loading weather icon: {e}")
class WeatherWorker(QThread):
    weather_updated = Signal(dict)
    def __init__(self, api_key, city):
        super().__init__(); self.api_key = api_key; self.city = city; self.is_running = True
    def run(self):
        while self.is_running:
            if not self.api_key or self.api_key == "YOUR_OPENWEATHERMAP_API_KEY":
                print("Weather API Key not set. Skipping weather fetch."); self._sleep_interruptible(1800); continue
            try:
                url = f"http://api.openweathermap.org/data/2.5/weather?q={self.city}&appid={self.api_key}&units=metric"; response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json(); weather_data = {"city": data['name'], "temp": f"{data['main']['temp']:.1f}", "condition": data['weather'][0]['description'].title(), "icon_url": f"http://openweathermap.org/img/wn/{data['weather'][0]['icon']}@2x.png"}; self.weather_updated.emit(weather_data)
                else: print(f"Error fetching weather: {response.status_code}")
            except Exception as e:
                print(f"An error occurred in WeatherWorker: {e}")
            self._sleep_interruptible(1800)
    def _sleep_interruptible(self, seconds):
        for _ in range(seconds):
            if not self.is_running: break
            time.sleep(1)
    def stop(self):
        print("Stopping Weather Worker..."); self.is_running = False; self.wait(); print("Weather Worker stopped.")
class FocusGraphCanvas(QWidget):
    def __init__(self):
        super().__init__();self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding);self.setMinimumHeight(200); self.threshold = 900; self.focus_vals = deque(maxlen=MAX_POINTS);self.distraction_vals = deque(maxlen=MAX_POINTS);self.humidity_vals = deque(maxlen=MAX_POINTS);self.background_color = QColor("#1F1F1F");self.co_normal_color = QColor("#2dd4bf");self.co_danger_color = QColor("#ef4444");self.temp_color = QColor("#3b82f6");self.humidity_color = QColor("#f97316");self.padding = {'left': 45, 'right': 15, 'top': 5, 'bottom': 25}
    def set_threshold(self, new_threshold):
        self.threshold = new_threshold; self.update()
    def update_plot(self, data_deque):
        if not data_deque: self.focus_vals.clear(); self.distraction_vals.clear(); self.humidity_vals.clear(); self.update(); return
        self.focus_vals = deque((d['gas'] for d in data_deque), maxlen=MAX_POINTS); self.distraction_vals = deque((d['temperature'] for d in data_deque), maxlen=MAX_POINTS); self.humidity_vals = deque((d['humidity'] for d in data_deque), maxlen=MAX_POINTS); self.update()
    def paintEvent(self, event):
        painter = QPainter(self);painter.setRenderHint(QPainter.RenderHint.Antialiasing);painter.fillRect(self.rect(), self.background_color)
        if not self.focus_vals: return
        graph_rect = self.rect().adjusted(self.padding['left'], self.padding['top'], -self.padding['right'], -self.padding['bottom'])
        max_val = max(max(self.focus_vals, default=0),max(self.distraction_vals, default=0),max(self.humidity_vals, default=0),self.threshold) * 1.1
        if max_val == 0: max_val = 1
        grid_pen = QPen(QColor("#444444"), 0.5, Qt.PenStyle.DashLine);axis_pen = QPen(QColor("#9E9E9E"));axis_font = QFont("Segoe UI", 8);painter.setFont(axis_font)
        for i in range(11):
            y = graph_rect.top() + graph_rect.height() * i / 10.0;value = max_val * (1 - i / 10.0)
            painter.setPen(grid_pen);painter.drawLine(graph_rect.left(), y, graph_rect.right(), y)
            if i % 2 == 0: painter.setPen(axis_pen);painter.drawText(QRectF(0, y - 10, self.padding['left'] - 5, 20), Qt.AlignRight | Qt.AlignVCenter, f"{value:.0f}")
        for i in range(11):
            x = graph_rect.left() + graph_rect.width() * i / 10.0;value = 100 - (i * 10)
            painter.setPen(grid_pen)
            if i > 0 and i < 10: painter.drawLine(x, graph_rect.top(), x, graph_rect.bottom())
            painter.setPen(axis_pen);painter.drawText(QRectF(x - 20, graph_rect.bottom(), 40, self.padding['bottom']), Qt.AlignCenter, f"{value}")
        if max_val > self.threshold:
            y_threshold = graph_rect.top() + graph_rect.height() * (1 - self.threshold / max_val)
            threshold_pen = QPen(self.co_danger_color, 1.5, Qt.PenStyle.DashLine); painter.setPen(threshold_pen);painter.drawLine(graph_rect.left(), y_threshold, graph_rect.right(), y_threshold)
            painter.setFont(QFont("Segoe UI", 8)); painter.setPen(self.co_danger_color);painter.drawText(QRectF(graph_rect.right() - 110, y_threshold - 5, 110, 20), Qt.AlignLeft, f"CO Limit: {self.threshold} ppm")
        line_thickness = 3.5
        self.draw_line_and_fill(painter, max_val, graph_rect, self.distraction_vals, self.temp_color, line_thickness)
        self.draw_line_and_fill(painter, max_val, graph_rect, self.humidity_vals, self.humidity_color, line_thickness)
        self.draw_segmented_line_and_fill(painter, max_val, graph_rect, self.focus_vals, line_thickness)
    def get_points(self, graph_rect, max_val, values):
        return [QPointF(graph_rect.left() + graph_rect.width()*(i/(MAX_POINTS-1 if MAX_POINTS>1 else 1)),graph_rect.top() + graph_rect.height()*(1-v/max_val)) for i, v in enumerate(values)]
    def draw_segmented_line_and_fill(self, painter, max_val, graph_rect, values, thickness):
        if len(values) < 2: return
        green_pen = QPen(self.co_normal_color, thickness); green_pen.setCapStyle(Qt.RoundCap);red_pen = QPen(self.co_danger_color, thickness); red_pen.setCapStyle(Qt.RoundCap);green_brush = QBrush(QColor(45, 212, 191, 51)); red_brush = QBrush(QColor(239, 68, 68, 51));points = self.get_points(graph_rect, max_val, values);path_segment = QPainterPath()
        for i in range(len(points) - 1):
            is_danger = values[i] > self.threshold or values[i+1] > self.threshold;pen = red_pen if is_danger else green_pen; brush = red_brush if is_danger else green_brush
            fill_poly = QPolygonF([points[i], points[i+1], QPointF(points[i+1].x(), graph_rect.bottom()), QPointF(points[i].x(), graph_rect.bottom())]);painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(brush); painter.drawPolygon(fill_poly);path_segment.moveTo(points[i])
            ctrl_pt1 = QPointF((points[i].x() + points[i+1].x()) / 2, points[i].y()); ctrl_pt2 = QPointF((points[i].x() + points[i+1].x()) / 2, points[i+1].y());path_segment.cubicTo(ctrl_pt1, ctrl_pt2, points[i+1]); painter.strokePath(path_segment, pen);path_segment.clear()
    def draw_line_and_fill(self, painter, max_val, graph_rect, values, color, thickness):
        if len(values) < 2: return
        points = self.get_points(graph_rect, max_val, values);line_path = QPainterPath(); line_path.moveTo(points[0])
        for i in range(len(points) - 1):
            ctrl_pt1 = QPointF((points[i].x() + points[i+1].x()) / 2, points[i].y()); ctrl_pt2 = QPointF((points[i].x() + points[i+1].x()) / 2, points[i+1].y());line_path.cubicTo(ctrl_pt1, ctrl_pt2, points[i+1])
        fill_path = QPainterPath(line_path); fill_path.lineTo(points[-1].x(), graph_rect.bottom()); fill_path.lineTo(points[0].x(), graph_rect.bottom()); fill_path.closeSubpath()
        fill_color = QColor(color); fill_color.setAlphaF(0.2); painter.setBrush(QBrush(fill_color)); painter.setPen(Qt.PenStyle.NoPen); painter.drawPath(fill_path);pen = QPen(color, thickness); pen.setCapStyle(Qt.RoundCap); painter.setPen(pen);painter.setBrush(Qt.BrushStyle.NoBrush); painter.drawPath(line_path)
class DataWarehousePage(QWidget):
    helmet_selected = Signal(str)
    def __init__(self, parent=None):
        super().__init__(parent);self.helmet_list = QListWidget();self.helmet_list.setStyleSheet("""QListWidget { background-color: #1F1F1F; border-radius: 16px; font-size: 12pt; padding: 5px; } QListWidget::item { padding: 10px; border-bottom: 1px solid #333333; } QListWidget::item:hover { background-color: #333333; } QListWidget::item:selected { background-color: #1d4ed8; color: white; }""");self.helmet_list.itemClicked.connect(self._on_item_clicked);layout = QVBoxLayout(self); title = QLabel("Connected Helmets"); title.setObjectName("headerLabel"); layout.addWidget(title); layout.addWidget(self.helmet_list)
    def update_helmet_list(self, helmet_data, active_helmet_id):
        self.helmet_list.blockSignals(True)
        self.helmet_list.clear()
        for helmet_id, data_packets in sorted(helmet_data.items()):
            if not data_packets: continue
            last_packet = data_packets[-1]; last_seen = last_packet['timestamp']; last_co = last_packet['gas']
            item_text = f"<b>ID: {helmet_id}</b><br><span style='font-size: 10pt; color: #9E9E9E;'>Last Seen: {last_seen} | Last CO: {last_co:.0f} ppm</span>"
            list_item = QListWidgetItem(); list_item.setData(Qt.UserRole, helmet_id); self.helmet_list.addItem(list_item)
            label = QLabel(item_text); label.setWordWrap(True); list_item.setSizeHint(label.sizeHint()); self.helmet_list.setItemWidget(list_item, label)
            if helmet_id == active_helmet_id: self.helmet_list.setCurrentItem(list_item)
        self.helmet_list.blockSignals(False)
    @Slot(QListWidgetItem)
    def _on_item_clicked(self, item):
        if item: helmet_id = item.data(Qt.UserRole); self.helmet_selected.emit(helmet_id)

# --- NEW: Battery Card Widget ---
class BatteryCard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setFixedSize(200, 100)
        self._level = 0

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        self.value_label = QLabel("-- %")
        self.value_label.setObjectName("batteryValue")
        layout.addWidget(self.value_label)
        layout.addStretch()

    def set_level(self, level):
        self._level = level
        self.value_label.setText(f"{level} %")
        self.update() # Trigger a repaint to redraw the battery icon

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Battery body
        body_rect = QRectF(self.width() - 60, 20, 50, 25)
        painter.setPen(QPen(QColor("#9E9E9E"), 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(body_rect, 5, 5)

        # Battery tip
        tip_rect = QRectF(body_rect.right(), 25, 5, 15)
        painter.setBrush(QColor("#9E9E9E"))
        painter.drawRoundedRect(tip_rect, 2, 2)
        
        # Battery level fill
        if self._level > 50:
            fill_color = QColor("#2dd4bf") # Green
        elif self._level > 20:
            fill_color = QColor("#facc15") # Yellow
        else:
            fill_color = QColor("#ef4444") # Red

        fill_width = (body_rect.width() - 6) * (self._level / 100.0)
        fill_rect = QRectF(body_rect.left() + 3, body_rect.top() + 3, fill_width, body_rect.height() - 6)
        painter.setPen(Qt.NoPen)
        painter.setBrush(fill_color)
        painter.drawRoundedRect(fill_rect, 3, 3)

class DashboardPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_layout = QGridLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(15)
        
        # --- MODIFIED: Location card and weather card are now in the same method ---
        self.location_and_weather_container = self._create_location_weather_card()
        
        cards_container = self._create_sensor_cards()
        self.map_card = MapWidget()
        self.graph_container = self._create_graph_container()
        
        self.main_layout.addWidget(self.location_and_weather_container, 0, 0)
        self.main_layout.addWidget(cards_container, 0, 1)
        self.main_layout.addWidget(self.map_card, 0, 2)
        self.main_layout.addWidget(self.graph_container, 1, 0, 1, 3)
        
        self.main_layout.setColumnStretch(0, 3); self.main_layout.setColumnStretch(1, 5); self.main_layout.setColumnStretch(2, 4)
        self.main_layout.setRowStretch(0, 1); self.main_layout.setRowStretch(1, 2)
        self._apply_shadows()

    # --- MODIFIED: This method now creates the left panel with location AND weather ---
    def _create_location_weather_card(self):
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0,0,0,0)
        container_layout.setSpacing(15)
        
        # Location Part
        loc_card = QWidget(); loc_card.setObjectName("card")
        loc_layout = QVBoxLayout(loc_card)
        title_label = QLabel("📍 ACTIVE HELMET LOCATION"); title_label.setObjectName("cardTitle")
        loc_layout.addWidget(title_label)
        grid = QGridLayout(); grid.setSpacing(15)
        lat_card = QWidget(); lat_card.setObjectName("locationInfoCard"); lat_layout = QVBoxLayout(lat_card); lat_layout.setContentsMargins(20, 15, 20, 15); lat_title = QLabel("LATITUDE"); lat_title.setObjectName("locationCardSubTitle"); self.main_latitude_label = QLabel("---"); self.main_latitude_label.setObjectName("locationCardValue"); lat_layout.addWidget(lat_title); lat_layout.addWidget(self.main_latitude_label); lat_layout.addStretch()
        grid.addWidget(lat_card, 0, 0)
        lon_card = QWidget(); lon_card.setObjectName("locationInfoCard"); lon_layout = QVBoxLayout(lon_card); lon_layout.setContentsMargins(20, 15, 20, 15); lon_title = QLabel("LONGITUDE"); lon_title.setObjectName("locationCardSubTitle"); self.main_longitude_label = QLabel("---"); self.main_longitude_label.setObjectName("locationCardValue"); lon_layout.addWidget(lon_title); lon_layout.addWidget(self.main_longitude_label); lon_layout.addStretch()
        grid.addWidget(lon_card, 0, 1)
        loc_layout.addLayout(grid)
        
        # Weather Part
        self.weather_card = WeatherCard()
        
        container_layout.addWidget(loc_card)
        container_layout.addWidget(self.weather_card)
        
        return container
        
    def _create_sensor_cards(self):
        container = QWidget(); layout = QGridLayout(container); layout.setSpacing(15)
        self.co_card = self._create_card("CO Level", "ppm", "pTasksCard", is_float=False)
        self.temp_card = self._create_card("Temperature", "°C", "aTasksCard", is_float=True)
        self.humidity_card = self._create_card("Humidity", "%", "humidityCard", is_float=True)
        self.status_card = self._create_status_card()
        # --- NEW: Create and add the BatteryCard ---
        self.battery_card = BatteryCard()

        layout.addWidget(self.co_card, 0, 0, 1, 2)
        layout.addWidget(self.temp_card, 1, 0)
        layout.addWidget(self.humidity_card, 1, 1)
        layout.addWidget(self.status_card, 0, 2)
        layout.addWidget(self.battery_card, 1, 2) # Add to the empty spot
        return container
        
    def _create_card(self, title, unit, name, is_float):
        card = QWidget();card.setObjectName(name);layout = QVBoxLayout(card);layout.setContentsMargins(25, 20, 25, 20);title_label = QLabel(title);title_label.setObjectName("dataCardTitle");value_layout = QHBoxLayout();val_label = AnimatedLabel(is_float=is_float);val_label.setObjectName("dataCardValue");unit_label = QLabel(unit);unit_label.setObjectName("dataCardUnit");value_layout.addStretch(1);value_layout.addWidget(val_label);value_layout.addWidget(unit_label, 0, Qt.AlignTop);value_layout.addStretch(1);layout.addWidget(title_label, 0, Qt.AlignTop);layout.addStretch(1);layout.addLayout(value_layout);layout.addStretch(1);card.value_label = val_label
        return card
    def _create_status_card(self):
        card = QWidget();card.setObjectName("statusCard");layout = QVBoxLayout(card);layout.setContentsMargins(20, 20, 20, 20);layout.setSpacing(15);title = QLabel("SYSTEM STATUS");title.setObjectName("cardTitle");layout.addWidget(title);form_layout = QFormLayout();self.gps_status_label = QLabel("Unknown");self.gps_status_label.setObjectName("statusLabel");self.co_status_label = QLabel("Unknown");self.co_status_label.setObjectName("statusLabel");form_layout.addRow(QLabel("GPS Signal:"), self.gps_status_label);form_layout.addRow(QLabel("CO Alert:"), self.co_status_label);layout.addLayout(form_layout)
        return card
    def _create_graph_container(self):
        container = QWidget();container.setObjectName("card");layout = QVBoxLayout(container);layout.setContentsMargins(45, 10, 15, 25);layout.setSpacing(0);header_layout = QHBoxLayout();title = QLabel("SENSOR ANALYSIS");title.setObjectName("cardTitle");legend_container = QWidget();legend_layout = QHBoxLayout(legend_container);legend_layout.setContentsMargins(0,0,0,0);legend_layout.setSpacing(15);legend_layout.addWidget(self._create_legend_item("#2dd4bf", "CO (Normal)"));legend_layout.addWidget(self._create_legend_item("#ef4444", "CO (Danger)"));legend_layout.addWidget(self._create_legend_item("#3b82f6", "Temperature"));legend_layout.addWidget(self._create_legend_item("#f97316", "Humidity (%)"));header_layout.addWidget(title);header_layout.addStretch();header_layout.addWidget(legend_container);self.graph_canvas = FocusGraphCanvas();layout.addLayout(header_layout);layout.addWidget(self.graph_canvas)
        return container
    def _apply_shadows(self):
        widgets = [self.location_and_weather_container, self.co_card, self.temp_card, self.humidity_card, self.status_card, self.graph_container, self.map_card, self.battery_card];
        for w in widgets:
            if w: shadow = QGraphicsDropShadowEffect(self);shadow.setBlurRadius(50);shadow.setOffset(0, 8);shadow.setColor(QColor(0, 0, 0, 80));w.setGraphicsEffect(shadow)
    def _create_legend_item(self, color, text):
        item = QWidget();layout = QHBoxLayout(item);layout.setSpacing(8);box = QLabel();box.setFixedSize(12,12);box.setStyleSheet(f"background-color: {color}; border-radius: 3px;");layout.addWidget(box);layout.addWidget(QLabel(text))
        return item
class SettingsPage(QWidget):
    threshold_changed = Signal(int)
    def __init__(self, initial_threshold, parent=None):
        super().__init__(parent); self.setObjectName("card"); layout = QFormLayout(self); layout.setContentsMargins(25, 25, 25, 25); layout.setSpacing(15); title = QLabel("Application Settings"); title.setObjectName("headerLabel"); layout.addRow(title); self.threshold_input = QLineEdit(str(initial_threshold)); self.threshold_input.setStyleSheet("font-size: 12pt; padding: 5px;"); layout.addRow("CO Threshold Limit (ppm):", self.threshold_input); self.apply_button = HoverButton(text="Apply"); self.apply_button.setFixedWidth(120); self.apply_button.clicked.connect(self._apply_changes); layout.addRow(self.apply_button)
    def _apply_changes(self):
        new_value_str = self.threshold_input.text()
        try:
            new_value_int = int(new_value_str); self.threshold_changed.emit(new_value_int); print(f"Threshold changed to: {new_value_int}")
        except ValueError:
            print(f"Invalid input for threshold: {new_value_str}")
class FleetMapPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent); layout = QVBoxLayout(self); layout.setContentsMargins(0,0,0,0); self.map_widget = MapWidget(is_fleet_map=True); layout.addWidget(self.map_widget)
    def update_map(self, helmet_data):
        self.map_widget.update_all_markers(helmet_data)

# --- MAIN DASHBOARD WINDOW ---
class DashboardWindow(QMainWindow):
    def __init__(self):
        super().__init__();self.setWindowTitle("Multi-Helmet Fleet Dashboard (CSV Playback)"); self.setGeometry(100, 100, 1400, 900)
        self.helmet_data = {}; self.current_helmet_id = None; self.is_paused = False; self.emergency_alert_shown = False; self.last_data_time = time.time(); self.co_threshold = 900
        self.playback_data = []; self.playback_index = 0
        self._load_csv_data(); self._setup_ui(); self._apply_stylesheet()
        self.playback_timer = QTimer(self); self.playback_timer.timeout.connect(self.run_playback_step); self.playback_timer.start(200)
        self.ui_update_timer = QTimer(self); self.ui_update_timer.timeout.connect(self.update_all_ui); self.ui_update_timer.start(1000)
        self.header_timer = QTimer(self); self.header_timer.timeout.connect(self.update_header_time); self.header_timer.start(1000)
        self.weather_worker = WeatherWorker(API_KEY, CITY); self.weather_worker.weather_updated.connect(self.update_weather_card); self.weather_worker.start()
    def _load_csv_data(self):
        try:
            with open(CSV_FILE, "r") as f:
                reader = csv.DictReader(f); self.playback_data = list(reader)
            print(f"Successfully loaded {len(self.playback_data)} rows from {CSV_FILE}")
            if self.playback_data: self.current_helmet_id = self.playback_data[0].get('helmetId')
        except FileNotFoundError:
            print(f"Error: {CSV_FILE} not found. Running generate_sample_csv()..."); generate_sample_csv(CSV_FILE); self._load_csv_data()
    @Slot()
    def run_playback_step(self):
        if not self.playback_data or self.is_paused: return
        data_row = self.playback_data[self.playback_index]
        typed_data = {"helmetId": data_row.get('helmetId'),"gas": float(data_row.get("gas", 0)),"temperature": float(data_row.get("temperature", 0)),"humidity": float(data_row.get("humidity", 0)),"latitude": float(data_row.get("latitude", 0.0)),"longitude": float(data_row.get("longitude", 0.0)),"emergency": data_row.get("emergency", 'False').lower() == 'true', "battery": int(data_row.get("battery", 0))}
        helmet_id = typed_data.get('helmetId')
        if not helmet_id: return
        typed_data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if helmet_id not in self.helmet_data:
            self.helmet_data[helmet_id] = deque(maxlen=MAX_POINTS)
        self.helmet_data[helmet_id].append(typed_data)
        self.playback_index = (self.playback_index + 1) % len(self.playback_data)
    @Slot()
    def update_all_ui(self):
        if self.is_paused: return
        self.data_warehouse_page.update_helmet_list(self.helmet_data, self.current_helmet_id)
        self.fleet_map_page.update_map(self.helmet_data)
        if self.current_helmet_id and self.helmet_data.get(self.current_helmet_id):
            latest_data = self.helmet_data[self.current_helmet_id][-1]
            self.update_dashboard_display(latest_data)
    def update_dashboard_display(self, data):
        self.helmet_id_label.setText(f"ID: {data.get('helmetId', 'N/A')}")
        page = self.dashboard_page
        co = data.get('gas', 0); temp = data.get('temperature', 0); hum = data.get('humidity', 0); lat = data.get('latitude', 0.0); lng = data.get('longitude', 0.0); is_emergency = data.get('emergency', False); battery = data.get('battery', 0)
        page.co_card.value_label.animate_to_value(co); page.temp_card.value_label.animate_to_value(temp); page.humidity_card.value_label.animate_to_value(hum)
        page.main_latitude_label.setText(f"{lat:.6f}" if lat != 0.0 else "No GPS Fix"); page.main_longitude_label.setText(f"{lng:.6f}" if lng != 0.0 else "No GPS Fix")
        # --- NEW: Update battery card ---
        page.battery_card.set_level(battery)
        if lat != 0.0: page.map_card.update_marker(lat, lng)
        page.graph_canvas.update_plot(self.helmet_data[self.current_helmet_id])
        if co > self.co_threshold and not self.emergency_alert_shown:
            self._show_emergency_alert(lat, lng); self.emergency_alert_shown = True
        elif co <= self.co_threshold:
            self.emergency_alert_shown = False
        if lat != 0.0: page.gps_status_label.setStyleSheet("color: #2dd4bf;"); page.gps_status_label.setText("ACTIVE")
        else: page.gps_status_label.setStyleSheet("color: #9E9E9E;"); page.gps_status_label.setText("NO FIX")
        if co > self.co_threshold:
            page.co_status_label.setStyleSheet("color: #ef4444;"); page.co_status_label.setText("DANGER")
        else:
            page.co_status_label.setStyleSheet("color: #2dd4bf;"); page.co_status_label.setText("Normal")
    @Slot(dict)
    def update_weather_card(self, weather_data):
        # Update the weather card on the dashboard page
        self.dashboard_page.weather_card.update_content(weather_data)
    def _show_emergency_alert(self, lat, lng):
        alert = QMessageBox(self); alert.setWindowTitle("EMERGENCY ALERT"); alert.setText(f"CO Level Critical (>{self.co_threshold} ppm)!"); alert.setInformativeText(f"High CO levels detected for the active helmet.\nLast known location: \nLatitude: {lat:.6f}\nLongitude: {lng:.6f}"); alert.setIcon(QMessageBox.Icon.Critical); alert.setStandardButtons(QMessageBox.StandardButton.Ok); alert.setStyleSheet("QMessageBox { background-color: #1F1F1F; color: #E0E0E0; } QMessageBox QLabel { color: #E0E0E0; }"); alert.exec()
    def _setup_ui(self):
        main_widget = QWidget(); self.main_layout = QVBoxLayout(main_widget); self.main_layout.setContentsMargins(25, 25, 25, 25); self.main_layout.setSpacing(15); header_widget = self._create_header(); self.stacked_widget = QStackedWidget(); self.dashboard_page = DashboardPage(); self.data_warehouse_page = DataWarehousePage(); self.settings_page = SettingsPage(initial_threshold=self.co_threshold); self.fleet_map_page = FleetMapPage(); self.stacked_widget.addWidget(self.dashboard_page); self.stacked_widget.addWidget(self.data_warehouse_page); self.stacked_widget.addWidget(self.fleet_map_page); self.stacked_widget.addWidget(self.settings_page); self.main_layout.addWidget(header_widget); self.main_layout.addWidget(self.stacked_widget, 1); self.setCentralWidget(main_widget); self.data_warehouse_page.helmet_selected.connect(self.change_active_helmet); self.settings_page.threshold_changed.connect(self.on_threshold_changed)
    def _create_header(self):
        widget = QWidget();layout = QHBoxLayout(widget);layout.setContentsMargins(0,0,0,0);self.nav_button_dashboard = HoverButton(text="Dashboard"); self.nav_button_dashboard.setCheckable(True); self.nav_button_dashboard.setChecked(True); self.nav_button_dashboard.clicked.connect(self._show_dashboard_page);self.nav_button_warehouse = HoverButton(text="Data Warehouse"); self.nav_button_warehouse.setCheckable(True); self.nav_button_warehouse.clicked.connect(self._show_warehouse_page);self.nav_button_map = HoverButton(text="Fleet Map"); self.nav_button_map.setCheckable(True); self.nav_button_map.clicked.connect(self._show_fleet_map_page);self.nav_button_settings = HoverButton(text="Settings"); self.nav_button_settings.setCheckable(True); self.nav_button_settings.clicked.connect(self._show_settings_page);layout.addWidget(self.nav_button_dashboard); layout.addWidget(self.nav_button_warehouse); layout.addWidget(self.nav_button_map); layout.addWidget(self.nav_button_settings); layout.addStretch(1);title_container = QWidget(); title_layout = QVBoxLayout(title_container); title_layout.setContentsMargins(0,0,0,0); title_layout.setSpacing(0); title_layout.setAlignment(Qt.AlignCenter);self.title_label = QLabel("Multi-Helmet Fleet Dashboard"); self.title_label.setObjectName("headerLabel");self.time_label = QLabel(""); self.time_label.setObjectName("timeLabel"); self.update_header_time();title_layout.addWidget(self.title_label); title_layout.addWidget(self.time_label); layout.addWidget(title_container); layout.addStretch(1);status_container = QWidget();status_layout = QHBoxLayout(status_container);status_layout.setSpacing(20);self.helmet_id_label = QLabel("ID: ---");self.helmet_id_label.setObjectName("statusHeaderLabel");self.connection_status_label = QLabel("CONNECTED");self.connection_status_label.setObjectName("statusHeaderLabel");self.connection_status_label.setStyleSheet("color: #2dd4bf;");status_layout.addWidget(self.helmet_id_label);status_layout.addWidget(self.connection_status_label);self.pause_button = HoverButton("pause-icon.png", "Pause");self.pause_button.setCheckable(True);self.pause_button.clicked.connect(self.toggle_pause);save_button = HoverButton("camera-icon.png", "Save PNG");save_button.clicked.connect(self.save_snapshot);layout.addWidget(status_container); layout.addWidget(self.pause_button); layout.addWidget(save_button)
        return widget
    def _update_nav_buttons(self, active_button):
        for button in [self.nav_button_dashboard, self.nav_button_warehouse, self.nav_button_map, self.nav_button_settings]:
            button.setChecked(button is active_button)
    @Slot()
    def _show_dashboard_page(self): self.stacked_widget.setCurrentIndex(0); self._update_nav_buttons(self.nav_button_dashboard)
    @Slot()
    def _show_warehouse_page(self): self.stacked_widget.setCurrentIndex(1); self._update_nav_buttons(self.nav_button_warehouse)
    @Slot()
    def _show_fleet_map_page(self): self.stacked_widget.setCurrentIndex(2); self._update_nav_buttons(self.nav_button_map)
    @Slot()
    def _show_settings_page(self): self.stacked_widget.setCurrentIndex(3); self._update_nav_buttons(self.nav_button_settings)
    @Slot(str)
    def change_active_helmet(self, helmet_id):
        print(f"Changing active helmet to: {helmet_id}"); self.current_helmet_id = helmet_id; self._show_dashboard_page()
        if self.helmet_data.get(helmet_id): self.update_dashboard_display(self.helmet_data[helmet_id][-1])
    @Slot(int)
    def on_threshold_changed(self, new_threshold):
        self.co_threshold = new_threshold; self.dashboard_page.graph_canvas.set_threshold(new_threshold)
    def update_header_time(self):
        if hasattr(self, 'time_label'): self.time_label.setText(datetime.now(tz=None).strftime('%A, %B %d, %Y  |  %I:%M:%S %p'))
    def toggle_pause(self):
        self.is_paused = not self.is_paused
        if self.is_paused: self.ui_update_timer.stop(); self.playback_timer.stop(); self.pause_button.setText("Resume")
        else: self.ui_update_timer.start(); self.playback_timer.start(); self.pause_button.setText("Pause")
    def save_snapshot(self):
        filename = f"snapshot_dark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"; self.grab().save(filename); print(f"✅ Screenshot saved to {filename}")
    def closeEvent(self, event):
        self.weather_worker.stop(); event.accept()
    def _apply_stylesheet(self):
        self.setStyleSheet("""QWidget { font-family: 'Segoe UI', sans-serif; color: #E0E0E0; }QMainWindow { background-color: #141414; }#headerLabel { font-size: 16pt; font-weight: 600; color: #FFFFFF; }#timeLabel { font-size: 10pt; color: #9E9E9E; }#statusHeaderLabel { font-size: 11pt; font-weight: 700; color: #FFFFFF; }#statusCard, #card { background-color: #1F1F1F; border-radius: 16px; }#pTasksCard, #aTasksCard, #humidityCard { border-radius: 16px; color: #FFFFFF; }#pTasksCard { background-color: qlineargradient(x1:0, y1:1, x2:1, y2:0, stop:0 #a855f7, stop:1 #ef4444); }#aTasksCard { background-color: qlineargradient(x1:0, y1:1, x2:1, y2:0, stop:0 #f97316, stop:1 #facc15); }#humidityCard { background-color: qlineargradient(x1:0, y1:1, x2:1, y2:0, stop:0 #3b82f6, stop:1 #2dd4bf); }#dataCardTitle { font-size: 12pt; font-weight: 800; color: #FFFFFF; text-transform: uppercase; letter-spacing: 1px; }#dataCardValue { font-size: 34pt; font-weight: 700; color: #FFFFFF; }#dataCardUnit { font-size: 14pt; font-weight: 600; color: rgba(255, 255, 255, 0.7); }
        #locationInfoCard { background-color: #27272a; border-radius: 12px; } #locationCardSubTitle { font-size: 9pt; font-weight: 600; color: #A1A1AA; text-transform: uppercase; } #locationCardValue { font-size: 20pt; font-weight: 700; color: #FFFFFF; }
        #cardTitle { font-size: 10pt; font-weight: 700; color: #FFFFFF; letter-spacing: 1px; text-transform: uppercase;}QFormLayout QLabel { font-size: 10pt; color: #9E9E9E; }#statusLabel { font-size: 11pt; font-weight: 900; }
        #weatherCity {{ font-size: 12pt; font-weight: 600; color: #FFFFFF; }} #weatherTemp {{ font-size: 28pt; font-weight: 700; color: #FFFFFF; }} #weatherCondition {{ font-size: 10pt; color: #9E9E9E; }}
        #batteryValue {{ font-size: 28pt; font-weight: 700; color: #FFFFFF; }}
        """)

if __name__ == "__main__":
    generate_sample_csv(CSV_FILE, num_rows=100, num_helmets=10)
    app = QApplication(sys.argv)
    window = DashboardWindow()
    window.show()
    sys.exit(app.exec())