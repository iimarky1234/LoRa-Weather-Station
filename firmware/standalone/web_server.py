# ==============================================================================
# Asyncio Web Server & Self-Hosted Dashboard for Standalone Weather Station
# Displays telemetry from onboard sensors with full multi-node tab styling
# ==============================================================================
import asyncio
import json
import config

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Weather Station - Standalone Node & Local Server</title>
<style>
:root {
  --bg: #0f172a; --card: #1e293b; --text: #f8fafc; --subtext: #94a3b8;
  --accent: #38bdf8; --border: #334155; --green: #22c55e; --yellow: #eab308;
  --red: #ef4444; --orange: #f97316; --cyan: #06b6d4; --purple: #a855f7;
}
* { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
body { background: var(--bg); color: var(--text); padding: 16px; min-height: 100vh; }
.container { max-width: 960px; margin: 0 auto; }
header { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 12px; margin-bottom: 16px; gap: 8px; }
h1 { font-size: 1.4rem; color: var(--accent); display: flex; align-items: center; gap: 8px; }
.badge { background: #0369a1; color: #e0f2fe; padding: 3px 8px; border-radius: 6px; font-size: 0.75rem; }
.status-pill { display: inline-flex; align-items: center; gap: 6px; background: #064e3b; color: #a7f3d0; padding: 4px 10px; border-radius: 20px; font-size: 0.8rem; font-weight: 500; }
.dot { width: 8px; height: 8px; background: var(--green); border-radius: 50%; animation: pulse 2s infinite; }
@keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.3; } 100% { opacity: 1; } }

/* Node Tabs */
.node-tabs { display: flex; gap: 8px; margin-bottom: 16px; overflow-x: auto; padding-bottom: 4px; }
.node-tab { background: var(--card); border: 1px solid var(--border); color: var(--subtext); padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 0.88rem; font-weight: 600; display: inline-flex; align-items: center; gap: 6px; transition: all 0.2s; white-space: nowrap; }
.node-tab:hover { border-color: var(--accent); color: var(--text); }
.node-tab.active { background: #0369a1; border-color: var(--accent); color: #fff; }
.node-tab .tag { font-size: 0.7rem; background: rgba(0,0,0,0.3); padding: 2px 6px; border-radius: 4px; }

.actions { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
.btn { background: #2563eb; color: #fff; border: none; padding: 7px 12px; border-radius: 8px; cursor: pointer; font-size: 0.82rem; font-weight: 600; text-decoration: none; display: inline-flex; align-items: center; gap: 6px; }
.btn:hover { background: #1d4ed8; }
.btn-green { background: #059669; }
.btn-outline { background: transparent; border: 1px solid var(--border); color: var(--text); }
.btn-outline:hover { background: var(--card); }

.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin-bottom: 16px; }
.card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 14px; position: relative; }
.card-header { display: flex; justify-content: space-between; align-items: center; font-size: 0.78rem; color: var(--subtext); margin-bottom: 4px; }
.card-val { font-size: 1.7rem; font-weight: 700; color: #fff; margin-bottom: 2px; }
.card-unit { font-size: 0.9rem; color: var(--subtext); font-weight: 400; margin-left: 2px; }
.card-sub { font-size: 0.72rem; color: var(--subtext); }
.bar { width: 100%; height: 5px; background: #334155; border-radius: 3px; margin-top: 8px; overflow: hidden; }
.bar-fill { height: 100%; width: 0%; transition: width 0.4s; }

.status-box { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 12px 16px; margin-bottom: 16px; font-size: 0.82rem; display: flex; flex-wrap: wrap; gap: 16px; align-items: center; }
.status-item { display: flex; align-items: center; gap: 6px; }

.table-card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 14px; }
.table-responsive { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 0.78rem; text-align: left; }
th { color: var(--subtext); border-bottom: 1px solid var(--border); padding: 8px 10px; white-space: nowrap; }
td { border-bottom: 1px solid #1e293b; padding: 8px 10px; color: #cbd5e1; white-space: nowrap; }
tr:hover td { background: #334155; }
.badge-node { background: #312e81; color: #c7d2fe; padding: 2px 6px; border-radius: 4px; font-weight: 600; font-size: 0.72rem; }
</style>
</head>
<body>
<div class="container">
  <header>
    <div>
      <h1>📡 Weather Station <span class="badge">Standalone Node</span></h1>
      <p style="color:var(--subtext);font-size:0.8rem;margin-top:2px;">Integrated Multi-Sensor Station & Local Web Service</p>
    </div>
    <div class="status-pill">
      <div class="dot"></div>
      <span id="txtState">Local Offline Web Service</span>
    </div>
  </header>

  <!-- Node Navigation Tabs (Maintains Gateway Layout) -->
  <div class="node-tabs" id="nodeTabs">
    <button class="node-tab active" id="tabNode1" onclick="selectNode(1)">📍 Node #1 <span class="tag" id="tagNode1">Online</span></button>
  </div>

  <div class="actions">
    <button id="btnAuto" class="btn btn-outline" onclick="toggleRefresh()">⏸️ Pause Updates</button>
    <button class="btn btn-outline" onclick="fetchData()">🔄 Sync Now</button>
    <a href="/download" id="btnDownload" class="btn btn-green">💾 Download CSV Log</a>
  </div>

  <!-- Telemetry Sensor Cards for Active Station -->
  <div class="grid">
    <div class="card">
      <div class="card-header"><span>TEMPERATURE</span><span>🌡️</span></div>
      <div class="card-val"><span id="valTemp">--</span><span class="card-unit">°C</span></div>
      <div class="card-sub">AM2301B Precision Sensor</div>
      <div class="bar"><div id="barTemp" class="bar-fill" style="background:var(--orange);"></div></div>
    </div>

    <div class="card">
      <div class="card-header"><span>HUMIDITY</span><span>💧</span></div>
      <div class="card-val"><span id="valHum">--</span><span class="card-unit">%</span></div>
      <div class="card-sub">AM2301B Relative Humidity</div>
      <div class="bar"><div id="barHum" class="bar-fill" style="background:var(--cyan);"></div></div>
    </div>

    <div class="card">
      <div class="card-header"><span>AMBIENT LIGHT</span><span>☀️</span></div>
      <div class="card-val"><span id="valLux">--</span><span class="card-unit">Lux</span></div>
      <div class="card-sub">BH1750 Light Sensor</div>
      <div class="bar"><div id="barLux" class="bar-fill" style="background:var(--yellow);"></div></div>
    </div>

    <div class="card">
      <div class="card-header"><span>SOIL MOISTURE</span><span>🌱</span></div>
      <div class="card-val"><span id="valSoil">--</span><span class="card-unit">%</span></div>
      <div class="card-sub">Calibrated Analog Probe</div>
      <div class="bar"><div id="barSoil" class="bar-fill" style="background:var(--green);"></div></div>
    </div>

    <div class="card">
      <div class="card-header"><span>UV INDEX</span><span>🟣</span></div>
      <div class="card-val"><span id="valUvi">--</span><span class="card-unit">UVI</span></div>
      <div class="card-sub">LTR390 UV Sensor</div>
      <div class="bar"><div id="barUvi" class="bar-fill" style="background:var(--purple);"></div></div>
    </div>

    <div class="card">
      <div class="card-header"><span>PM2.5 DUST</span><span>💨</span></div>
      <div class="card-val"><span id="valPm25">--</span><span class="card-unit">µg/m³</span></div>
      <div class="card-sub">Laser Dust (APM10)</div>
      <div class="bar"><div id="barPm25" class="bar-fill" style="background:#ef4444;"></div></div>
    </div>

    <div class="card">
      <div class="card-header"><span>PM10 COARSE</span><span>🌫️</span></div>
      <div class="card-val"><span id="valPm10">--</span><span class="card-unit">µg/m³</span></div>
      <div class="card-sub">Coarse Dust (APM10)</div>
      <div class="bar"><div id="barPm10" class="bar-fill" style="background:#f43f5e;"></div></div>
    </div>
  </div>

  <div class="status-box">
    <div class="status-item">🏷️ <strong>Selected Node:</strong> <span id="valNode" style="color:#a78bfa;">Node #1</span></div>
    <div class="status-item">🕒 <strong>Last Reading:</strong> <span id="valTime" style="color:var(--accent);">--</span></div>
    <div class="status-item">🔌 <strong>Bus Link:</strong> <span id="valBus">Direct Onboard I2C / ADC</span></div>
    <div class="status-item">💾 <strong>Storage:</strong> <span id="valSd">Checking...</span></div>
    <div class="status-item">📊 <strong>Logged:</strong> <span id="valRows">0 records</span></div>
  </div>

  <div class="table-card">
    <div class="table-header" style="margin-bottom:12px;display:flex;justify-content:space-between;align-items:center;">
      <h3 style="font-size:0.95rem;color:#f1f5f9;">Recent Telemetry History</h3>
      <span style="font-size:0.75rem;color:var(--subtext);" id="histCount">Showing recent readings</span>
    </div>
    <div class="table-responsive">
      <table>
        <thead>
          <tr>
            <th>Time</th>
            <th>Station</th>
            <th>Temp (°C)</th>
            <th>Humidity (%)</th>
            <th>Light (Lux)</th>
            <th>Soil (%)</th>
            <th>UVI</th>
            <th>PM2.5</th>
            <th>PM10</th>
            <th>Medium</th>
          </tr>
        </thead>
        <tbody id="tableBody">
          <tr><td colspan="10" style="text-align:center;padding:20px;color:var(--subtext);">Waiting for sensor readings...</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</div>

<script>
let autoRefresh = true;
let selectedNodeId = 1;
let cachedData = { nodes: {}, latest: {} };

function selectNode(id) {
  selectedNodeId = id;
  document.querySelectorAll('.node-tab').forEach(t => t.classList.remove('active'));
  const activeTab = document.getElementById('tabNode' + id);
  if (activeTab) activeTab.classList.add('active');
  renderActiveNode();
}

function renderActiveNode() {
  const d = (cachedData.nodes && cachedData.nodes[selectedNodeId]) || cachedData.latest || {};
  
  document.getElementById('valNode').innerText = `Node #${selectedNodeId}`;
  document.getElementById('valTemp').innerText = d.temp !== null && d.temp !== undefined ? Number(d.temp).toFixed(1) : '--';
  document.getElementById('valHum').innerText = d.hum !== null && d.hum !== undefined ? Number(d.hum).toFixed(0) : '--';
  document.getElementById('valLux').innerText = d.lux !== null && d.lux !== undefined ? Number(d.lux).toFixed(0) : '--';
  document.getElementById('valSoil').innerText = d.soil_pct !== null && d.soil_pct !== undefined ? Number(d.soil_pct).toFixed(1) : '--';
  document.getElementById('valUvi').innerText = d.uvi !== null && d.uvi !== undefined ? Number(d.uvi).toFixed(2) : '--';
  document.getElementById('valPm25').innerText = d.pm25 !== null && d.pm25 !== undefined ? d.pm25 : '--';
  document.getElementById('valPm10').innerText = d.pm10 !== null && d.pm10 !== undefined ? d.pm10 : '--';
  document.getElementById('valTime').innerText = d.time || 'No reading acquired yet';

  // Dynamic Fill Bars
  document.getElementById('barTemp').style.width = Math.min(100, Math.max(0, ((d.temp || 0) / 50) * 100)) + '%';
  document.getElementById('barHum').style.width = Math.min(100, Math.max(0, d.hum || 0)) + '%';
  document.getElementById('barLux').style.width = Math.min(100, Math.max(0, ((d.lux || 0) / 2000) * 100)) + '%';
  document.getElementById('barSoil').style.width = Math.min(100, Math.max(0, d.soil_pct || 0)) + '%';
  document.getElementById('barUvi').style.width = Math.min(100, Math.max(0, ((d.uvi || 0) / 12) * 100)) + '%';
  document.getElementById('barPm25').style.width = Math.min(100, Math.max(0, ((d.pm25 || 0) / 150) * 100)) + '%';
  document.getElementById('barPm10').style.width = Math.min(100, Math.max(0, ((d.pm10 || 0) / 250) * 100)) + '%';
}

async function fetchData() {
  try {
    const res = await fetch('/api/data');
    if (!res.ok) return;
    const d = await res.json();
    cachedData = d;

    renderActiveNode();

    const sdSpan = document.getElementById('valSd');
    const btnDl = document.getElementById('btnDownload');
    if (d.storage_type === 'sd') {
      sdSpan.innerHTML = '<span style="color:#22c55e;">● MicroSD (/sd)</span>';
      if (btnDl) btnDl.innerText = '💾 Download CSV (SD)';
    } else if (d.storage_type === 'flash') {
      sdSpan.innerHTML = '<span style="color:#38bdf8;">● Internal Flash (16MB)</span>';
      if (btnDl) btnDl.innerText = '💾 Download CSV (Flash)';
    } else {
      sdSpan.innerHTML = '<span style="color:#ef4444;">✕ RAM Buffer Only</span>';
      if (btnDl) btnDl.innerText = '💾 Download CSV (None)';
    }
    document.getElementById('valRows').innerText = (d.log_count || 0) + ' records';

    fetchHistory();
  } catch (e) {}
}

async function fetchHistory() {
  try {
    const res = await fetch('/api/history');
    if (!res.ok) return;
    const history = await res.json();
    if (!history || history.length === 0) return;

    const tbody = document.getElementById('tableBody');
    let rowsHtml = '';
    for (let i = history.length - 1; i >= 0; i--) {
      const r = history[i];
      const dt = r.data || {};
      rowsHtml += `<tr>
        <td>${r.time}</td>
        <td><span class="badge-node">Node #${r.node_id || 1}</span></td>
        <td>${dt.temp !== undefined && dt.temp !== null ? dt.temp : '--'}</td>
        <td>${dt.hum !== undefined && dt.hum !== null ? dt.hum + '%' : '--'}</td>
        <td>${dt.lux !== undefined && dt.lux !== null ? dt.lux : '--'}</td>
        <td>${dt.soil_pct !== undefined && dt.soil_pct !== null ? dt.soil_pct + '%' : '--'}</td>
        <td>${dt.uvi !== undefined && dt.uvi !== null ? dt.uvi : '--'}</td>
        <td>${dt.pm25 !== undefined && dt.pm25 !== null ? dt.pm25 : '--'}</td>
        <td>${dt.pm10 !== undefined && dt.pm10 !== null ? dt.pm10 : '--'}</td>
        <td><span style="color:#38bdf8;">Logged</span></td>
      </tr>`;
    }
    tbody.innerHTML = rowsHtml;
  } catch (e) {}
}

function toggleRefresh() {
  autoRefresh = !autoRefresh;
  document.getElementById('btnAuto').innerText = autoRefresh ? '⏸️ Pause Updates' : '▶️ Resume Updates';
}

fetchData();
setInterval(() => { if (autoRefresh) fetchData(); }, 3000);
</script>
</body>
</html>"""

# Pre-encode HTML to avoid high-heap allocations during concurrent client requests
DASHBOARD_HTML_BYTES = DASHBOARD_HTML.encode('utf-8')

class StandaloneWebServer:
    def __init__(self, storage_mgr):
        self.storage_mgr = storage_mgr
        self.server = None
        self.nodes_data = {}
        self.latest_packet = {
            "node_id": 1,
            "time": "Never",
            "rssi": "Local",
            "snr": "Local",
            "temp": None,
            "hum": None,
            "lux": None,
            "soil_pct": None,
            "uvi": None,
            "pm25": None,
            "pm10": None,
            "sd_mounted": self.storage_mgr.sd_mounted,
            "storage_type": self.storage_mgr.storage_type,
            "storage_label": self.storage_mgr.get_storage_label(),
            "log_count": 0
        }

    def update_telemetry(self, packet):
        data = packet.get("data", {})
        node_id = packet.get("node_id", 1)
        telemetry = {
            "node_id": node_id,
            "time": packet.get("time", "Never"),
            "rssi": "Local",
            "snr": "Local",
            "temp": data.get("temp"),
            "hum": data.get("hum"),
            "lux": data.get("lux"),
            "soil_pct": data.get("soil_pct"),
            "uvi": data.get("uvi"),
            "pm25": data.get("pm25"),
            "pm10": data.get("pm10"),
            "sd_mounted": self.storage_mgr.sd_mounted,
            "storage_type": self.storage_mgr.storage_type,
            "storage_label": self.storage_mgr.get_storage_label(),
            "log_count": self.storage_mgr.log_count
        }

        self.nodes_data[node_id] = telemetry
        self.latest_packet.update(telemetry)

    async def handle_client(self, reader, writer):
        try:
            # 1. Read HTTP request line with timeout
            try:
                line = await asyncio.wait_for(reader.readline(), 3.0)
            except Exception:
                await writer.aclose()
                return

            if not line:
                await writer.aclose()
                return

            req_line = line.decode('utf-8', 'ignore').strip()
            parts = req_line.split()
            if len(parts) < 2:
                await writer.aclose()
                return

            method, raw_path = parts[0], parts[1]

            # 2. Drain headers with timeout to prevent hanging connections
            while True:
                try:
                    h_line = await asyncio.wait_for(reader.readline(), 2.0)
                except Exception:
                    break
                if not h_line or h_line == b"\r\n" or h_line == b"\n" or h_line.strip() == b"":
                    break

            # 3. Normalize path: strip query parameters and absolute URL proxy prefixes
            path = raw_path.split("?")[0]
            if "://" in path:
                scheme_removed = path.split("://", 1)[1]
                path = "/" + scheme_removed.split("/", 1)[1] if "/" in scheme_removed else "/"

            # 4. Captive Portal Detection Endpoints (Android, iOS, Windows, Chrome)
            if path in (
                "/generate_204", "/gen_204", "/connectivitycheck",
                "/hotspot-detect.html", "/library/test/success.html",
                "/ncsi.txt", "/connecttest.txt", "/canonical.html", "/success.txt"
            ):
                redirect_resp = (
                    b"HTTP/1.1 302 Found\r\n"
                    b"Location: http://192.168.4.1/\r\n"
                    b"Content-Length: 0\r\n"
                    b"Connection: close\r\n\r\n"
                )
                writer.write(redirect_resp)
                await writer.drain()
                return

            # 5. Main Dashboard Page (or catch-all on root)
            if path == "/" or path == "/index.html":
                body = DASHBOARD_HTML_BYTES
                hdr = (
                    b"HTTP/1.1 200 OK\r\n"
                    b"Content-Type: text/html; charset=utf-8\r\n"
                    b"Content-Length: " + str(len(body)).encode('utf-8') + b"\r\n"
                    b"Connection: close\r\n\r\n"
                )
                writer.write(hdr)
                await writer.drain()

                # Stream response in 1024-byte chunks with await writer.drain() to protect ESP32 TCP window
                chunk_size = 1024
                for offset in range(0, len(body), chunk_size):
                    writer.write(body[offset:offset + chunk_size])
                    await writer.drain()

            elif path == "/api/data":
                payload = {
                    "nodes": self.nodes_data,
                    "active_node_id": self.latest_packet.get("node_id", 1),
                    "latest": self.latest_packet,
                    "sd_mounted": self.storage_mgr.sd_mounted,
                    "storage_type": self.storage_mgr.storage_type,
                    "storage_label": self.storage_mgr.get_storage_label(),
                    "log_count": self.storage_mgr.log_count,
                    "log_size": self.storage_mgr.get_log_size()
                }
                body = json.dumps(payload).encode('utf-8')
                resp = (
                    b"HTTP/1.1 200 OK\r\n"
                    b"Content-Type: application/json\r\n"
                    b"Content-Length: " + str(len(body)).encode('utf-8') + b"\r\n"
                    b"Connection: close\r\n\r\n" + body
                )
                writer.write(resp)
                await writer.drain()

            elif path == "/api/history":
                history = self.storage_mgr.get_history(30)
                body = json.dumps(history).encode('utf-8')
                resp = (
                    b"HTTP/1.1 200 OK\r\n"
                    b"Content-Type: application/json\r\n"
                    b"Content-Length: " + str(len(body)).encode('utf-8') + b"\r\n"
                    b"Connection: close\r\n\r\n" + body
                )
                writer.write(resp)
                await writer.drain()

            elif path == "/download":
                if not self.storage_mgr.is_persistent() or not self.storage_mgr.active_log_path:
                    writer.write(b"HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\nNo persistent log available")
                    await writer.drain()
                else:
                    try:
                        size = self.storage_mgr.get_log_size()
                        resp_hdr = (
                            b"HTTP/1.1 200 OK\r\n"
                            b"Content-Type: text/csv\r\n"
                            b"Content-Disposition: attachment; filename=gateway_weather_log.csv\r\n"
                            b"Content-Length: " + str(size).encode('utf-8') + b"\r\n"
                            b"Connection: close\r\n\r\n"
                        )
                        writer.write(resp_hdr)
                        await writer.drain()

                        with open(self.storage_mgr.active_log_path, "rb") as f:
                            while True:
                                chunk = f.read(512)
                                if not chunk:
                                    break
                                writer.write(chunk)
                                await writer.drain()
                    except Exception:
                        pass

            elif path == "/favicon.ico":
                writer.write(b"HTTP/1.1 204 No Content\r\nConnection: close\r\n\r\n")
                await writer.drain()

            else:
                # Catch-all: For any other GET request (e.g., typing domain or subpath),
                # redirect directly to root dashboard
                if method.upper() == "GET":
                    redirect_resp = (
                        b"HTTP/1.1 302 Found\r\n"
                        b"Location: http://192.168.4.1/\r\n"
                        b"Content-Length: 0\r\n"
                        b"Connection: close\r\n\r\n"
                    )
                    writer.write(redirect_resp)
                    await writer.drain()
                else:
                    writer.write(b"HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\nNot Found")
                    await writer.drain()

        except Exception:
            pass
        finally:
            try:
                await writer.aclose()
            except Exception:
                pass

    async def start(self):
        if self.server:
            return self.server
        try:
            self.server = await asyncio.start_server(self.handle_client, "0.0.0.0", config.SERVER_PORT)
            print(f"[OK] Standalone Web Server listening on port {config.SERVER_PORT}")
            return self.server
        except Exception as e:
            print(f"[ERR] Failed to start web server on port {config.SERVER_PORT}: {e}")
            return None

    async def stop(self):
        if hasattr(self, "server") and self.server:
            try:
                self.server.close()
                await self.server.wait_closed()
            except Exception:
                pass
            self.server = None
