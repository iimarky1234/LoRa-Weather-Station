# ==============================================================================
# Asyncio Web Server & Self-Hosted Dashboard for ESP32-S3
# ==============================================================================
import asyncio
import json
import os
import config

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LoRa Weather Station Dashboard</title>
<style>
:root {
  --bg: #0f172a;
  --card: #1e293b;
  --text: #f8fafc;
  --subtext: #94a3b8;
  --accent: #38bdf8;
  --border: #334155;
  --green: #22c55e;
  --yellow: #eab308;
  --red: #ef4444;
  --purple: #a855f7;
}
* { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
body { background: var(--bg); color: var(--text); padding: 16px; min-height: 100vh; }
.container { max-width: 900px; margin: 0 auto; }
header { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 12px; margin-bottom: 20px; }
h1 { font-size: 1.5rem; color: var(--accent); display: flex; align-items: center; gap: 8px; }
.badge { background: #0369a1; color: #e0f2fe; padding: 4px 8px; border-radius: 6px; font-size: 0.75rem; }
.status-pill { display: inline-flex; align-items: center; gap: 6px; background: #064e3b; color: #a7f3d0; padding: 4px 10px; border-radius: 20px; font-size: 0.8rem; font-weight: 500; }
.dot { width: 8px; height: 8px; background: var(--green); border-radius: 50%; animation: pulse 2s infinite; }
@keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.3; } 100% { opacity: 1; } }

.actions { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px; }
.btn { background: #2563eb; color: #fff; border: none; padding: 8px 14px; border-radius: 8px; cursor: pointer; font-size: 0.85rem; font-weight: 600; text-decoration: none; display: inline-flex; align-items: center; gap: 6px; transition: background 0.2s; }
.btn:hover { background: #1d4ed8; }
.btn-green { background: #059669; }
.btn-green:hover { background: #047857; }
.btn-outline { background: transparent; border: 1px solid var(--border); color: var(--text); }
.btn-outline:hover { background: var(--card); }

.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; margin-bottom: 20px; }
.card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 16px; position: relative; overflow: hidden; }
.card-header { display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem; color: var(--subtext); margin-bottom: 8px; }
.card-val { font-size: 2rem; font-weight: 700; color: #fff; margin-bottom: 4px; }
.card-unit { font-size: 1rem; color: var(--subtext); font-weight: 400; margin-left: 2px; }
.card-sub { font-size: 0.75rem; color: var(--subtext); }

.bar { width: 100%; height: 6px; background: #334155; border-radius: 3px; margin-top: 8px; overflow: hidden; }
.bar-fill { height: 100%; background: var(--accent); width: 0%; transition: width 0.4s; }

.status-box { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 14px; margin-bottom: 20px; font-size: 0.85rem; display: flex; flex-wrap: wrap; gap: 20px; align-items: center; }
.status-item { display: flex; align-items: center; gap: 6px; }

.table-card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 16px; }
.table-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.table-responsive { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 0.82rem; text-align: left; }
th { color: var(--subtext); border-bottom: 1px solid var(--border); padding: 8px 10px; font-weight: 600; }
td { border-bottom: 1px solid #1e293b; padding: 8px 10px; color: #cbd5e1; }
tr:hover td { background: #334155; }
</style>
</head>
<body>
<div class="container">
  <header>
    <div>
      <h1>🌦️ Weather Station <span class="badge">ESP32-S3</span></h1>
      <p style="color:var(--subtext);font-size:0.8rem;margin-top:4px;">Autonomous Microclimate Logger & Self-Hosted Dashboard</p>
    </div>
    <div style="margin-top:8px;">
      <span class="status-pill"><span class="dot"></span> Live Telemetry</span>
    </div>
  </header>

  <div class="actions">
    <a href="/download" class="btn btn-green">📥 Download SD Log (.csv)</a>
    <button onclick="syncClock()" class="btn btn-outline" id="btnSync">⏱️ Sync RTC Time from Browser</button>
    <button onclick="toggleRefresh()" class="btn btn-outline" id="btnAuto">⏸️ Pause Updates</button>
  </div>

  <div class="grid">
    <div class="card">
      <div class="card-header"><span>TEMPERATURE</span><span>🌡️</span></div>
      <div class="card-val"><span id="valTemp">--</span><span class="card-unit">°C</span></div>
      <div class="card-sub">Air Temp (DHT11)</div>
      <div class="bar"><div id="barTemp" class="bar-fill" style="background:#f97316;"></div></div>
    </div>

    <div class="card">
      <div class="card-header"><span>HUMIDITY</span><span>💧</span></div>
      <div class="card-val"><span id="valHum">--</span><span class="card-unit">%</span></div>
      <div class="card-sub">Relative Humidity (DHT11)</div>
      <div class="bar"><div id="barHum" class="bar-fill" style="background:#06b6d4;"></div></div>
    </div>

    <div class="card">
      <div class="card-header"><span>AMBIENT LIGHT</span><span>☀️</span></div>
      <div class="card-val"><span id="valLux">--</span><span class="card-unit">Lux</span></div>
      <div class="card-sub">Calibrated Illuminance (BH1750)</div>
      <div class="bar"><div id="barLux" class="bar-fill" style="background:#eab308;"></div></div>
    </div>

    <div class="card">
      <div class="card-header"><span>SOIL MOISTURE</span><span>🌱</span></div>
      <div class="card-val"><span id="valSoil">--</span><span class="card-unit">%</span></div>
      <div class="card-sub" id="subSoil">Substrate Moisture</div>
      <div class="bar"><div id="barSoil" class="bar-fill" style="background:#22c55e;"></div></div>
    </div>
  </div>

  <div class="status-box">
    <div class="status-item">🕒 <strong>RTC Time:</strong> <span id="valTime" style="color:var(--accent);">--</span></div>
    <div class="status-item">💾 <strong>SD Card:</strong> <span id="valSd">Checking...</span></div>
    <div class="status-item">📊 <strong>Rows Logged:</strong> <span id="valRows">0</span></div>
    <div class="status-item">📁 <strong>CSV Size:</strong> <span id="valSize">0 KB</span></div>
  </div>

  <div class="table-card">
    <div class="table-header">
      <h3 style="font-size:1rem;color:#f1f5f9;">Recent Telemetry History</h3>
      <span style="font-size:0.75rem;color:var(--subtext);">Last 15 readings</span>
    </div>
    <div class="table-responsive">
      <table>
        <thead>
          <tr>
            <th>Timestamp</th>
            <th>Temp (°C)</th>
            <th>Humidity (%)</th>
            <th>Light (Lux)</th>
            <th>Soil (%)</th>
          </tr>
        </thead>
        <tbody id="tableBody">
          <tr><td colspan="5" style="text-align:center;color:var(--subtext);">Waiting for sensor telemetry...</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</div>

<script>
let autoRefresh = true;
let refreshTimer = null;

async function fetchData() {
  try {
    const res = await fetch('/api/data');
    if (!res.ok) return;
    const d = await res.json();
    
    document.getElementById('valTemp').innerText = d.temperature.toFixed(1);
    document.getElementById('valHum').innerText = d.humidity.toFixed(0);
    document.getElementById('valLux').innerText = d.lux.toFixed(0);
    document.getElementById('valSoil').innerText = d.soil_pct.toFixed(1);
    document.getElementById('valTime').innerText = d.timestamp;
    
    // Bars
    document.getElementById('barTemp').style.width = Math.min(100, Math.max(0, (d.temperature / 50) * 100)) + '%';
    document.getElementById('barHum').style.width = Math.min(100, Math.max(0, d.humidity)) + '%';
    document.getElementById('barLux').style.width = Math.min(100, Math.max(0, (d.lux / 2000) * 100)) + '%';
    document.getElementById('barSoil').style.width = Math.min(100, Math.max(0, d.soil_pct)) + '%';

    // Status
    const sdSpan = document.getElementById('valSd');
    if (d.sd_mounted) {
      sdSpan.innerHTML = '<span style="color:#22c55e;">● Mounted (/sd)</span>';
    } else {
      sdSpan.innerHTML = '<span style="color:#ef4444;">✕ Unmounted (RAM only)</span>';
    }
    document.getElementById('valRows').innerText = d.log_count;
    document.getElementById('valSize').innerText = (d.log_size / 1024).toFixed(1) + ' KB';

    fetchHistory();
  } catch (e) {
    console.error('Fetch error:', e);
  }
}

async function fetchHistory() {
  try {
    const res = await fetch('/api/history');
    if (!res.ok) return;
    const history = await res.json();
    if (!history || history.length === 0) return;
    
    const tbody = document.getElementById('tableBody');
    let rowsHtml = '';
    // Reverse so latest is on top
    for (let i = history.length - 1; i >= 0; i--) {
      const r = history[i];
      rowsHtml += `<tr>
        <td>${r.timestamp}</td>
        <td><strong>${r.temperature.toFixed(1)}</strong></td>
        <td>${r.humidity.toFixed(0)}%</td>
        <td>${r.lux.toFixed(0)}</td>
        <td>${r.soil_pct.toFixed(1)}%</td>
      </tr>`;
    }
    tbody.innerHTML = rowsHtml;
  } catch (e) {}
}

async function syncClock() {
  const btn = document.getElementById('btnSync');
  btn.innerText = 'Syncing...';
  try {
    const now = new Date();
    const payload = {
      year: now.getFullYear(),
      month: now.getMonth() + 1,
      day: now.getDate(),
      hour: now.getHours(),
      minute: now.getMinutes(),
      second: now.getSeconds()
    };
    const res = await fetch('/api/set_time', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      btn.innerText = '✅ Synced!';
      setTimeout(() => { btn.innerText = '⏱️ Sync RTC Time from Browser'; }, 2000);
      fetchData();
    } else {
      btn.innerText = '❌ Failed';
    }
  } catch (e) {
    btn.innerText = '❌ Error';
  }
}

function toggleRefresh() {
  autoRefresh = !autoRefresh;
  const btn = document.getElementById('btnAuto');
  if (autoRefresh) {
    btn.innerText = '⏸️ Pause Updates';
    refreshTimer = setInterval(fetchData, 3000);
  } else {
    btn.innerText = '▶️ Resume Updates';
    clearInterval(refreshTimer);
  }
}

fetchData();
refreshTimer = setInterval(fetchData, 3000);
</script>
</body>
</html>
"""

class WebServer:
    def __init__(self, sensor_mgr, storage_mgr):
        self.sensor_mgr = sensor_mgr
        self.storage_mgr = storage_mgr
        self.latest_data = {
            "timestamp": "2026-01-01 00:00:00",
            "temperature": 0.0,
            "humidity": 0.0,
            "lux": 0.0,
            "soil_pct": 0.0,
            "sd_mounted": False,
            "log_count": 0,
            "log_size": 0
        }

    def update_telemetry(self, data):
        """Updates the cached sensor reading served to clients."""
        self.latest_data.update(data)
        self.latest_data["sd_mounted"] = self.storage_mgr.sd_mounted
        self.latest_data["log_count"] = self.storage_mgr.log_count
        self.latest_data["log_size"] = self.storage_mgr.get_log_size()

    async def handle_client(self, reader, writer):
        """Processes incoming HTTP request and routes responses."""
        try:
            line = await reader.readline()
            if not line:
                await writer.aclose()
                return

            req_line = line.decode('utf-8', 'ignore').strip()
            parts = req_line.split()
            if len(parts) < 2:
                await writer.aclose()
                return

            method, path = parts[0], parts[1]
            print(f"[HTTP] {method} {path}")

            # Read remaining headers
            headers = {}
            content_length = 0
            while True:
                header_line = await reader.readline()
                if not header_line or header_line == b'\r\n' or header_line == b'\n':
                    break
                h_str = header_line.decode('utf-8', 'ignore').strip()
                if ':' in h_str:
                    k, v = h_str.split(':', 1)
                    k_lower = k.strip().lower()
                    headers[k_lower] = v.strip()
                    if k_lower == 'content-length':
                        try: content_length = int(v.strip())
                        except ValueError: pass

            # Read POST body if present
            body = b""
            if method == "POST" and content_length > 0:
                body = await reader.readexactly(content_length)

            # Route: GET /
            if method == "GET" and (path == "/" or path == "/index.html"):
                writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n")
                await writer.drain()
                html_bytes = DASHBOARD_HTML.encode('utf-8')
                for i in range(0, len(html_bytes), 1024):
                    writer.write(html_bytes[i:i+1024])
                    await writer.drain()

            # Route: GET /api/data
            elif method == "GET" and path == "/api/data":
                writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n")
                writer.write(json.dumps(self.latest_data).encode('utf-8'))
                await writer.drain()

            # Route: GET /api/history
            elif method == "GET" and path == "/api/history":
                writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n")
                history = self.storage_mgr.get_history(limit=20)
                writer.write(json.dumps(history).encode('utf-8'))
                await writer.drain()

            # Route: POST /api/set_time (Browser RTC calibration)
            elif method == "POST" and path == "/api/set_time":
                try:
                    payload = json.loads(body.decode('utf-8'))
                    ok = self.sensor_mgr.set_ds1307_datetime(
                        int(payload["year"]),
                        int(payload["month"]),
                        int(payload["day"]),
                        int(payload["hour"]),
                        int(payload["minute"]),
                        int(payload["second"])
                    )
                    resp = {"status": "ok" if ok else "fail"}
                except Exception as e:
                    resp = {"status": "error", "message": str(e)}

                writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n")
                writer.write(json.dumps(resp).encode('utf-8'))
                await writer.drain()

            # Route: GET /download (Streaming CSV download)
            elif method == "GET" and path == "/download":
                if not self.storage_mgr.sd_mounted:
                    # SD card is not mounted
                    writer.write(b"HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\n")
                    writer.write(b"MicroSD card is not mounted or unavailable.")
                    await writer.drain()
                else:
                    try:
                        # Stream CSV file chunk-by-chunk directly to client
                        writer.write(b"HTTP/1.1 200 OK\r\n")
                        writer.write(b"Content-Type: text/csv\r\n")
                        writer.write(b"Content-Disposition: attachment; filename=\"weather_data.csv\"\r\n")
                        writer.write(b"Connection: close\r\n\r\n")
                        await writer.drain()

                        with open(config.LOG_FILE_PATH, "r") as f:
                            while True:
                                chunk = f.read(512)
                                if not chunk:
                                    break
                                writer.write(chunk.encode('utf-8'))
                                await writer.drain()
                    except Exception as e:
                        print("[ERR] Error streaming CSV:", e)

            else:
                writer.write(b"HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\n404 Not Found")
                await writer.drain()

        except Exception as e:
            pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def start(self):
        """Starts the asynchronous HTTP server on port 80."""
        print(f"[INFO] Starting HTTP Web Server on port {config.SERVER_PORT}...")
        self.server = await asyncio.start_server(self.handle_client, "0.0.0.0", config.SERVER_PORT)
        print(f"[OK] Web Server listening on port {config.SERVER_PORT}")
        return self.server

    async def stop(self):
        """Stops the HTTP server cleanly."""
        if hasattr(self, "server") and self.server:
            print("[INFO] Stopping HTTP Web Server...")
            try:
                self.server.close()
                await self.server.wait_closed()
            except Exception:
                pass
            self.server = None
            print("[OK] Web Server stopped.")
