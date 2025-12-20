"""
Flask приложение для мониторинга хоста
День 15: Environment - Агент + Docker

Собирает метрики хоста и отдает их через HTTP endpoint /health
"""

from flask import Flask, render_template_string
import psutil
import platform
import datetime
import socket

app = Flask(__name__)

# HTML шаблон для отображения метрик
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="5">
    <title>Server Health Monitor</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }

        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }

        .header .subtitle {
            font-size: 1.2em;
            opacity: 0.9;
        }

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }

        .metric-card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            transition: transform 0.3s ease;
        }

        .metric-card:hover {
            transform: translateY(-5px);
        }

        .metric-card h2 {
            color: #667eea;
            font-size: 1.3em;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .metric-card .icon {
            font-size: 1.5em;
        }

        .metric-value {
            font-size: 2.5em;
            font-weight: bold;
            color: #333;
            margin: 10px 0;
        }

        .metric-label {
            color: #666;
            font-size: 0.9em;
            margin-top: 5px;
        }

        .progress-bar {
            width: 100%;
            height: 12px;
            background: #e0e0e0;
            border-radius: 6px;
            overflow: hidden;
            margin-top: 10px;
        }

        .progress-fill {
            height: 100%;
            transition: width 0.3s ease;
            border-radius: 6px;
        }

        .progress-fill.good {
            background: linear-gradient(90deg, #4CAF50, #8BC34A);
        }

        .progress-fill.warning {
            background: linear-gradient(90deg, #FF9800, #FFC107);
        }

        .progress-fill.danger {
            background: linear-gradient(90deg, #f44336, #E91E63);
        }

        .info-section {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }

        .info-section h2 {
            color: #667eea;
            margin-bottom: 15px;
        }

        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }

        .info-item {
            padding: 10px;
            background: #f5f5f5;
            border-radius: 8px;
        }

        .info-item strong {
            color: #667eea;
            display: block;
            margin-bottom: 5px;
        }

        .footer {
            text-align: center;
            color: white;
            margin-top: 30px;
            opacity: 0.8;
        }

        .status-badge {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: bold;
            margin-top: 10px;
        }

        .status-badge.online {
            background: #4CAF50;
            color: white;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🖥️ Server Health Monitor</h1>
            <div class="subtitle">Real-time system metrics</div>
            <div class="status-badge online">● ONLINE</div>
        </div>

        <div class="metrics-grid">
            <!-- CPU Metric -->
            <div class="metric-card">
                <h2><span class="icon">⚙️</span> CPU Usage</h2>
                <div class="metric-value">{{ cpu_percent }}%</div>
                <div class="progress-bar">
                    <div class="progress-fill {{ cpu_status }}" style="width: {{ cpu_percent }}%"></div>
                </div>
                <div class="metric-label">{{ cpu_count }} cores @ {{ cpu_freq }} MHz</div>
            </div>

            <!-- Memory Metric -->
            <div class="metric-card">
                <h2><span class="icon">💾</span> Memory</h2>
                <div class="metric-value">{{ mem_percent }}%</div>
                <div class="progress-bar">
                    <div class="progress-fill {{ mem_status }}" style="width: {{ mem_percent }}%"></div>
                </div>
                <div class="metric-label">{{ mem_used }} / {{ mem_total }} GB</div>
            </div>

            <!-- Disk Metric -->
            <div class="metric-card">
                <h2><span class="icon">💿</span> Disk Usage</h2>
                <div class="metric-value">{{ disk_percent }}%</div>
                <div class="progress-bar">
                    <div class="progress-fill {{ disk_status }}" style="width: {{ disk_percent }}%"></div>
                </div>
                <div class="metric-label">{{ disk_used }} / {{ disk_total }} GB</div>
            </div>

            <!-- Uptime Metric -->
            <div class="metric-card">
                <h2><span class="icon">⏱️</span> Uptime</h2>
                <div class="metric-value" style="font-size: 1.8em;">{{ uptime }}</div>
                <div class="metric-label">Since {{ boot_time }}</div>
            </div>
        </div>

        <div class="info-section">
            <h2>📋 System Information</h2>
            <div class="info-grid">
                <div class="info-item">
                    <strong>Hostname</strong>
                    {{ hostname }}
                </div>
                <div class="info-item">
                    <strong>Platform</strong>
                    {{ platform }}
                </div>
                <div class="info-item">
                    <strong>Architecture</strong>
                    {{ architecture }}
                </div>
                <div class="info-item">
                    <strong>Python Version</strong>
                    {{ python_version }}
                </div>
                <div class="info-item">
                    <strong>IP Address</strong>
                    {{ ip_address }}
                </div>
                <div class="info-item">
                    <strong>Temperature</strong>
                    {{ temperature }}
                </div>
            </div>
        </div>

        <div class="footer">
            <p>🤖 AIBot Monitoring System | Auto-refresh every 5 seconds</p>
            <p>День 15: Environment - Агент + Docker</p>
        </div>
    </div>
</body>
</html>
"""


def get_status_class(percent):
    """Определить класс статуса на основе процента использования."""
    if percent < 70:
        return "good"
    elif percent < 85:
        return "warning"
    else:
        return "danger"


def get_temperature():
    """Получить температуру процессора (если доступно)."""
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            # Попробовать найти температуру CPU
            for name, entries in temps.items():
                if 'coretemp' in name.lower() or 'cpu' in name.lower():
                    if entries:
                        return f"{entries[0].current:.1f}°C"
        return "N/A"
    except:
        return "N/A"


def get_ip_address():
    """Получить IP адрес хоста."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "N/A"


@app.route('/health')
def health():
    """Endpoint для отображения метрик хоста."""

    # CPU метрики
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_count = psutil.cpu_count()
    cpu_freq = psutil.cpu_freq().current if psutil.cpu_freq() else 0

    # Memory метрики
    mem = psutil.virtual_memory()
    mem_total = round(mem.total / (1024**3), 2)
    mem_used = round(mem.used / (1024**3), 2)
    mem_percent = mem.percent

    # Disk метрики
    disk = psutil.disk_usage('/')
    disk_total = round(disk.total / (1024**3), 2)
    disk_used = round(disk.used / (1024**3), 2)
    disk_percent = disk.percent

    # Uptime
    boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
    uptime_seconds = (datetime.datetime.now() - boot_time).total_seconds()

    days = int(uptime_seconds // 86400)
    hours = int((uptime_seconds % 86400) // 3600)
    minutes = int((uptime_seconds % 3600) // 60)

    if days > 0:
        uptime = f"{days}d {hours}h"
    else:
        uptime = f"{hours}h {minutes}m"

    # System info
    hostname = socket.gethostname()
    platform_info = f"{platform.system()} {platform.release()}"
    architecture = platform.machine()
    python_version = platform.python_version()
    ip_address = get_ip_address()
    temperature = get_temperature()

    return render_template_string(
        HTML_TEMPLATE,
        cpu_percent=cpu_percent,
        cpu_count=cpu_count,
        cpu_freq=int(cpu_freq),
        cpu_status=get_status_class(cpu_percent),
        mem_percent=mem_percent,
        mem_used=mem_used,
        mem_total=mem_total,
        mem_status=get_status_class(mem_percent),
        disk_percent=disk_percent,
        disk_used=disk_used,
        disk_total=disk_total,
        disk_status=get_status_class(disk_percent),
        uptime=uptime,
        boot_time=boot_time.strftime("%Y-%m-%d %H:%M:%S"),
        hostname=hostname,
        platform=platform_info,
        architecture=architecture,
        python_version=python_version,
        ip_address=ip_address,
        temperature=temperature
    )


@app.route('/')
def index():
    """Перенаправление на /health."""
    return health()


if __name__ == '__main__':
    # Запуск Flask на всех интерфейсах, порт 8001
    app.run(host='0.0.0.0', port=8001, debug=False)
