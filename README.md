# Multi-Helmet Fleet Dashboard (CSV Playback)

This project is a **desktop fleet dashboard** for monitoring multiple smart helmets using **Python + PySide6 (Qt for Python)**.  
It supports **CSV playback mode** (simulating real-time helmet data) and provides a fully interactive, modern dashboard interface.

## 🚀 Features
- Multi-helmet monitoring from CSV-simulated data.
- **Dashboard components:**
  - CO gas levels (with threshold alerting)
  - Temperature
  - Humidity
  - GPS-based map (Leaflet.js + Qt WebEngine)
  - Battery status indicator
  - Weather widget (via OpenWeatherMap API)
  - Sensor analysis graph (real-time plots)
  - Helmet list with last-seen timestamp and CO levels
  - System status (GPS, CO alert)
- **Fleet view:** Shows all helmet locations on a single map.
- **Data warehouse:** Historical helmet data view.
- **Settings page:** Allows dynamic threshold changes.
- Clean UI with shadows, animated labels, and hover effects.

## 🛠️ Tech Stack
- **Python 3**
- **PySide6 (Qt for Python)** → UI framework
- **Qt WebEngine** → for map embedding
- **Leaflet.js** → map rendering
- **OpenWeatherMap API** → live weather info
- **CSV** → demo data source (simulating helmet streams)

## 📂 Project Structure
```
multi-helmet-dashboard/
│── main.py              # Main dashboard application
│── demo_data.csv        # CSV file for simulated data
│── README.md            # Documentation (this file)
```
> The CSV file is auto-generated if not found.

## ⚡ How It Works
1. A CSV file (`demo_data.csv`) is loaded at startup.
2. Data rows are "played back" every 200ms to simulate real-time incoming helmet data.
3. Each row includes: timestamp, helmetId, gas, temperature, humidity, latitude, longitude, emergency, battery.
4. Dashboard updates in real-time with this simulated data.
5. Weather is fetched every 30 minutes from **OpenWeatherMap**.

### Example CSV Row
```csv
timestamp,helmetId,gas,temperature,humidity,latitude,longitude,emergency,battery
2025-08-29 12:00:01,SH-001,420.5,30.2,55.0,28.6139,77.2090,False,88
```

## 🔧 Setup Instructions
### 1. Install dependencies
```bash
pip install PySide6 requests
```

### 2. (Optional) Set your OpenWeatherMap API Key
Replace `API_KEY` in `main.py` with your key from:  
👉 https://openweathermap.org/api

### 3. Run the dashboard
```bash
python main.py
```

## 📊 Future Enhancements
- Replace CSV playback with **live ESP32/LoRa sensor data** over USB/Serial or MQTT.
- Add **MongoDB integration** for permanent data storage.
- Add **React + Node.js web dashboard** alternative.

## 👨‍💻 Author
Developed as part of a **Smart Helmet Fleet Monitoring Project**.
