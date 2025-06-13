from flask import Flask, render_template_string, request, redirect, flash
import json, time, threading, os, requests

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Diperlukan untuk flash messages
CONFIG_PATH = "config.json"
posting_active = False
config = {
    "token": "",
    "use_webhook": False,
    "webhook_url": "",
    "channels": [],
    "dark_mode": False
}

def load_config():
    global config
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            try:
                config = json.load(f)
            except json.JSONDecodeError:
                print("[ERROR] config.json tidak valid, memuat default.")
    else:
        save_config()


def save_config():
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=4)


def send_log(message, channel_id=None, success=True):
    if config.get("use_webhook") and config.get("webhook_url"):
        try:
            now = time.strftime("%d %B %Y  %I:%M:%S %p")
            embed = {
                "title": "<a:ms_discord:1129069176917610619> Auto Post Discord <a:ms_discord:1129069176917610619>",
                "description": "> **Details Info**",
                "color": 65280 if success else 16711680,
                "fields": [
                    {"name": "<a:live:1247888274161143878> Status Log", "value": "> Success" if success else "> Failed"},
                    {"name": "<:BS_Time:1182386606661972099> Date Time", "value": f"> {now}"},
                    {"name": "<:discord:1263889532688797727> Channel Target", "value": f"> <#{channel_id}>" if channel_id else "> Unknown"},
                    {"name": "<a:ki_verify:1193420850511224913> Status Message", "value": f"> {message}"}
                ],
                "footer": {"text": "Auto Post By Lantas Continental. design By Void_String"}
            }
            payload = {"embeds": [embed]}
            requests.post(config["webhook_url"], json=payload)
        except Exception as e:
            print(f"[LOG ERROR] {e}")

@app.route("/", methods=["GET"])
@app.route("/index", methods=["GET"])
def index():
    load_config()
    return render_template_string(
        html_template, 
        config_json=json.dumps(config, indent=4), 
        config=config, 
        posting_active=posting_active,
        editing=False
    )

@app.route("/save-config", methods=["POST"])
def save():
    global config
    load_config()
    
    # Menangani pengaturan webhook secara terpisah
    if 'webhook_url' in request.form:
        webhook_url = request.form.get("webhook_url", "").strip()
        use_webhook = True if request.form.get("use_webhook") else False
        config["webhook_url"] = webhook_url
        config["use_webhook"] = use_webhook
        save_config()
        flash("Webhook settings saved successfully!", "success")
        return redirect("/#webhook")
    
    # Menangani token secara terpisah
    if 'token' in request.form:
        token = request.form.get("token", "").strip()
        if token:
            config["token"] = token
            save_config()
            flash("Token saved successfully!", "success")
        return redirect("/#settings")
    
    # Menangani operasi channel
    channel_id = request.form.get("channel_id")
    message = request.form.get("message")
    original_channel_id = request.form.get("original_channel_id")
    action = request.form.get("action")
    
    # Validasi input
    if action != "remove" and (not channel_id or not message):
        flash("All fields are required: Channel ID, Message", "danger")
        return redirect("/#channels")

    
    try:
        hours = int(request.form.get("hours", 0))
        minutes = int(request.form.get("minutes", 0))
        seconds = int(request.form.get("seconds", 0))
    except ValueError:
        hours = minutes = seconds = 0
    
    interval = hours * 3600 + minutes * 60 + seconds
    
    # Validasi interval minimal 1 detik
    if action != "remove" and interval <= 0:
        flash("Interval must be at least 1 second", "danger")
        return redirect("/#channels")
    
    # Cek duplikasi channel ID untuk operasi tambah
    if action == "add":
        if any(ch['id'] == channel_id for ch in config["channels"]):
            flash(f"Channel ID {channel_id} already exists!", "danger")
            return redirect("/#channels")
    
    # Eksekusi operasi
    if action == "add":
        config["channels"].append({"id": channel_id, "message": message, "interval": interval})
        flash("Channel added successfully!", "success")
    elif action == "edit":
        found = False
        for ch in config["channels"]:
            # Cek apakah mengedit channel dengan ID yang berbeda
            if ch["id"] == original_channel_id:
                # Jika ID berubah, cek apakah ID baru sudah ada
                if channel_id != original_channel_id and any(c['id'] == channel_id for c in config["channels"]):
                    flash(f"Channel ID {channel_id} already exists!", "danger")
                    return redirect("/#channels")
                
                ch["id"] = channel_id
                ch["message"] = message
                ch["interval"] = interval
                found = True
                break
        
        if found:
            flash("Channel updated successfully!", "success")
        else:
            flash("Channel not found!", "danger")
    elif action == "remove":
        before_count = len(config["channels"])
        config["channels"] = [ch for ch in config["channels"] if ch["id"] != channel_id]
        after_count = len(config["channels"])
        
        if after_count < before_count:
            flash("Channel removed successfully!", "success")
        else:
            flash("Channel not found!", "danger")
    
    save_config()
    return redirect("/#channels")

@app.route("/start", methods=["POST"])
def start():
    global posting_active
    if not posting_active:
        posting_active = True
        threading.Thread(target=auto_post, daemon=True).start()
        flash("Auto posting started!", "success")
    return redirect("/")

@app.route("/stop", methods=["POST"])
def stop():
    global posting_active
    posting_active = False
    flash("Auto posting stopped!", "info")
    return redirect("/")

@app.route("/test-webhook", methods=["POST"])
def test_webhook():
    load_config()
    send_log("Test webhook log berhasil dikirim.")
    flash("Webhook test sent successfully!", "success")
    return redirect("/#webhook")

@app.route("/save-dark-mode", methods=["POST"])
def save_dark_mode():
    config['dark_mode'] = request.json.get('dark_mode', False)
    save_config()
    return jsonify(success=True)

def post_to_channel(ch):
    while posting_active:
        try:
            url = f"https://discord.com/api/v10/channels/{ch['id']}/messages"
            headers = {"Authorization": config["token"], "Content-Type": "application/json"}
            data = {"content": ch["message"]}
            res = requests.post(url, headers=headers, json=data)
            success = res.status_code in (200, 204)
            send_log(f"Pesan ke <#{ch['id']}> {'berhasil' if success else 'gagal'} [{res.status_code}].", ch['id'], success)
        except Exception as e:
            send_log(f"Error kirim ke <#{ch['id']}>: {e}", ch['id'], False)
        time.sleep(ch["interval"])

def auto_post():
    load_config()
    for ch in config["channels"]:
        threading.Thread(target=post_to_channel, args=(ch,), daemon=True).start()

# HTML template yang telah diperbaiki
html_template = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Auto Poster Controller</title>
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Bootstrap Icons -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        :root {
            --primary: #4361ee;
            --secondary: #3f37c9;
            --success: #4cc9f0;
            --dark: #1e1e2d;
            --light: #f8f9fa;
            --card-bg: #ffffff;
            --text: #343a40;
            --border: #e0e0e0;
            --dark-text: #f0f0f0;
            --dark-card-bg: #252525;
            --dark-border: #444;
        }
        .dark-mode {
            --primary: #4cc9f0;
            --secondary: #4361ee;
            --dark: #121212;
            --light: #1e1e2d;
            --card-bg: var(--dark-card-bg);
            --text: var(--dark-text);
            --border: var(--dark-border);
        }
        body {
            background-color: var(--light);
            color: var(--text);
            transition: background-color 0.3s, color 0.3s;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            min-height: 100vh;
        }
        .navbar-brand {
            font-weight: 700;
            letter-spacing: 1px;
        }
        .card {
            background-color: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            margin-bottom: 20px;
            transition: transform 0.3s;
        }
        .card:hover {
            transform: translateY(-5px);
        }
        .card-header {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white;
            border-radius: 10px 10px 0 0 !important;
            font-weight: 600;
            padding: 12px 20px;
        }
        .card-body {
            padding: 25px;
        }
        .form-label {
            font-weight: 500;
            margin-bottom: 8px;
            color: var(--text);
        }
        .btn-primary {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border: none;
            transition: all 0.3s;
        }
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(67, 97, 238, 0.3);
        }
        .btn-danger {
            background: linear-gradient(135deg, #e63946, #d90429);
            border: none;
        }
        .status-indicator {
            width: 15px;
            height: 15px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 8px;
        }
        .status-active {
            background-color: #4ade80;
            box-shadow: 0 0 10px #4ade80;
        }
        .status-inactive {
            background-color: #e11d48;
        }
        .config-box {
            background-color: rgba(0,0,0,0.05);
            border-radius: 8px;
            padding: 15px;
            max-height: 200px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 14px;
            color: var(--text);
        }
        .dark-mode .config-box {
            background-color: rgba(255,255,255,0.05);
        }
        .nav-tabs .nav-link {
            color: var(--text);
            font-weight: 500;
            border: none;
        }
        .nav-tabs .nav-link.active {
            color: var(--primary);
            border-bottom: 3px solid var(--primary);
            background: transparent;
        }
        .mode-toggle {
            cursor: pointer;
            font-size: 1.5rem;
            color: var(--text);
        }
        .token-input-group {
            position: relative;
        }
        .token-toggle {
            position: absolute;
            right: 10px;
            top: 50%;
            transform: translateY(-50%);
            cursor: pointer;
            color: #6c757d;
        }
        .section-icon {
            font-size: 1.2rem;
            margin-right: 10px;
            color: var(--primary);
        }
        .floating-buttons {
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 1000;
        }
        .floating-buttons .btn {
            border-radius: 50%;
            width: 60px;
            height: 60px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            margin-bottom: 15px;
        }
        .interval-controls {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .interval-control {
            flex: 1;
            min-width: 100px;
        }
        .channel-item {
            background: rgba(0,0,0,0.03);
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 10px;
        }
        .dark-mode .channel-item {
            background: rgba(255,255,255,0.05);
        }
        .channel-message {
            background: var(--light);
            padding: 10px;
            border-radius: 6px;
            margin: 10px 0;
            white-space: pre-wrap;
            font-family: monospace;
        }
        .dark-mode .channel-message {
            background: var(--dark);
        }
        .editing-indicator {
            display: inline-block;
            padding: 3px 8px;
            background: var(--primary);
            color: white;
            border-radius: 4px;
            font-size: 0.8rem;
            margin-left: 10px;
        }
        .auto-post-indicator {
            display: inline-block;
            margin-left: 10px;
        }
        .alert-flash {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 2000;
            min-width: 300px;
        }
        @media (max-width: 768px) {
            .card-body {
                padding: 15px;
            }
            .floating-buttons {
                bottom: 10px;
                right: 10px;
            }
            .floating-buttons .btn {
                width: 50px;
                height: 50px;
                font-size: 0.9rem;
            }
            .interval-controls {
                flex-direction: column;
            }
            .alert-flash {
                left: 20px;
                right: 20px;
            }
        }
    </style>
</head>
<body class="{{ 'dark-mode' if config.get('dark_mode', False) else '' }}">
    <!-- Flash Messages -->
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            <div class="alert-flash">
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>
                {% endfor %}
            </div>
        {% endif %}
    {% endwith %}
    
    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg navbar-dark" style="background: linear-gradient(135deg, var(--primary), var(--secondary));">
        <div class="container">
            <a class="navbar-brand" href="#"><i class="bi bi-send"></i> Auto Poster Controller</a>
            <div class="d-flex align-items-center">
                <div class="me-3">
                    <span class="status-indicator {% if posting_active %}status-active{% else %}status-inactive{% endif %}"></span>
                    <span class="text-white">
                        {% if posting_active %}Running{% else %}Stopped{% endif %}
                    </span>
                </div>
                <div class="mode-toggle" id="modeToggle">
                    <i class="bi {{ 'bi-sun' if config.get('dark_mode', False) else 'bi-moon' }}"></i>
                </div>
            </div>
        </div>
    </nav>
    <div class="container py-4">
        <!-- Tabs Navigation -->
        <ul class="nav nav-tabs mb-4" id="myTab" role="tablist">
            <li class="nav-item"><button class="nav-link active" id="settings-tab" data-bs-toggle="tab" data-bs-target="#settings" type="button"><i class="bi bi-gear section-icon"></i>Settings</button></li>
            <li class="nav-item"><button class="nav-link" id="channels-tab" data-bs-toggle="tab" data-bs-target="#channels" type="button"><i class="bi bi-hash section-icon"></i>Channels</button></li>
            <li class="nav-item"><button class="nav-link" id="webhook-tab" data-bs-toggle="tab" data-bs-target="#webhook" type="button"><i class="bi bi-link-45deg section-icon"></i>Webhooks</button></li>
            <li class="nav-item"><button class="nav-link" id="config-tab" data-bs-toggle="tab" data-bs-target="#config" type="button"><i class="bi bi-code-slash section-icon"></i>Configuration</button></li>
        </ul>
        <div class="tab-content" id="myTabContent">
            <!-- Settings Tab -->
            <div class="tab-pane fade show active" id="settings">
                <div class="card">
                    <div class="card-header"><i class="bi bi-key"></i> Discord Token</div>
                    <div class="card-body">
                        <form method="post" action="/save-config">
                            <div class="token-input-group mb-3">
    <label class="form-label">Discord Bot Token</label>
    <div class="position-relative">
      <input type="password" name="token" class="form-control" value="{{ config.token }}" placeholder="Enter Discord token" required>
      <span class="token-toggle position-absolute" style="top:50%; right:10px; transform:translateY(-50%); cursor:pointer;">
        <i class="bi bi-eye"></i>
      </span>
    </div>
    <div class="form-text">Keep your token secure. Never share it publicly.</div>
</div>

                            <button type="submit" class="btn btn-primary"><i class="bi bi-save"></i> Save Token</button>
                        </form>
                        <form method="post" action="/test-webhook" class="mt-3">
                            <button type="submit" class="btn btn-outline-primary"><i class="bi bi-send-check"></i> Test Webhook</button>
                        </form>
                    </div>
                </div>
            </div>
            <!-- Channels Tab -->
            <div class="tab-pane fade" id="channels">
                <div class="card">
                    <div class="card-header">
                        <i class="bi {{ 'bi-pencil' if editing else 'bi-plus-circle' }}"></i> 
                        {{ 'Edit Channel' if editing else 'Add New Channel' }}
                        {% if editing %}<span class="editing-indicator">EDITING MODE</span>{% endif %}
                    </div>
                    <div class="card-body">
                        <form id="channelForm" method="post" action="/save-config">
                            <input type="hidden" name="action" value="{{ 'edit' if editing else 'add' }}">
                            <input type="hidden" name="original_channel_id" value="{{ original_channel_id }}">
                            
                            <div class="mb-3">
                                <label class="form-label">Channel ID <span class="text-danger">*</span></label>
                                <input type="text" id="channelId" name="channel_id" class="form-control" 
                                       value="{{ channel_id or '' }}" placeholder="Channel ID" 
                                       {{ 'readonly' if editing else '' }} required>
                            </div>
                            
                            <div class="mb-3">
                                <label class="form-label">Message Content <span class="text-danger">*</span></label>
                                <textarea id="channelMessage" name="message" class="form-control" 
                                          rows="4" placeholder="Message to post..." required>{{ channel_message or '' }}</textarea>
                            </div>
                            
                            <div class="mb-3">
                                <label class="form-label">Posting Interval <span class="text-danger">*</span></label>
                                <div class="interval-controls">
                                    <div class="interval-control">
                                        <label class="form-label">Hours</label>
                                        <input type="number" name="hours" class="form-control" 
                                               value="{{ hours or 0 }}" min="0" placeholder="0" required>
                                    </div>
                                    <div class="interval-control">
                                        <label class="form-label">Minutes</label>
                                        <input type="number" name="minutes" class="form-control" 
                                               value="{{ minutes or 0 }}" min="0" max="59" placeholder="0" required>
                                    </div>
                                    <div class="interval-control">
                                        <label class="form-label">Seconds</label>
                                        <input type="number" name="seconds" class="form-control" 
                                               value="{{ seconds or 0 }}" min="0" max="59" placeholder="0" required>
                                    </div>
                                </div>
                                <div class="form-text">Total interval must be at least 1 second</div>
                            </div>
                            
                            <button type="submit" class="btn btn-success">
                                <i class="bi {{ 'bi-arrow-repeat' if editing else 'bi-save' }}"></i> 
                                {{ 'Update Channel' if editing else 'Add Channel' }}
                            </button>
                            
                            {% if editing %}
                            <button type="button" class="btn btn-secondary" onclick="cancelEdit()">
                                <i class="bi bi-x-circle"></i> Cancel Edit
                            </button>
                            {% endif %}
                        </form>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-header"><i class="bi bi-list-check"></i> Active Channels</div>
                    <div class="card-body">
                        {% for ch in config.channels %}
                        <div class="channel-item">
                            <div class="d-flex justify-content-between align-items-center">
                                <div>
                                    <strong>Channel ID:</strong> {{ ch.id }}
                                    {% if posting_active %}
                                    <span class="auto-post-indicator">
                                        <span class="status-indicator status-active"></span>
                                        <small>Active</small>
                                    </span>
                                    {% endif %}
                                </div>
                                <div>
                                    <button class="btn btn-sm btn-outline-primary me-1" 
                                            onclick="editChannel('{{ ch.id }}', `{{ ch.message | replace('\n', '\\n') | replace('\r', '') }}`, {{ ch.interval }})">
                                        <i class="bi bi-pencil"></i>
                                    </button>
                                    <form method="post" action="/save-config" class="d-inline" 
                                          onsubmit="return confirm('Are you sure you want to delete this channel?');">
                                        <input type="hidden" name="action" value="remove">
                                        <input type="hidden" name="channel_id" value="{{ ch.id }}">
                                        <button type="submit" class="btn btn-sm btn-outline-danger">
                                            <i class="bi bi-trash"></i>
                                        </button>
                                    </form>
                                </div>
                            </div>
                            
                            <div class="mt-2">
                                <strong>Interval:</strong> 
                                {{ ch.interval // 3600 }}h {{ (ch.interval % 3600) // 60 }}m {{ ch.interval % 60 }}s
                            </div>
                            
                            <div class="channel-message mt-2">
                                {{ ch.message }}
                            </div>
                        </div>
                        {% else %}
                        <div class="text-center py-3">
                            <i class="bi bi-info-circle"></i> No channels configured
                        </div>
                        {% endfor %}
                    </div>
                </div>
            </div>
            <!-- Webhooks Tab -->
            <div class="tab-pane fade" id="webhook">
                <div class="card">
                    <div class="card-header"><i class="bi bi-send-check"></i> Webhook Integration</div>
                    <div class="card-body">
                        <form method="post" action="/save-config">
                            <div class="form-check form-switch mb-3">
                                <input class="form-check-input" type="checkbox" id="useWebhookSwitch" name="use_webhook" {% if config.use_webhook %}checked{% endif %}>
                                <label class="form-check-label" for="useWebhookSwitch">Enable Webhook</label>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Webhook URL</label>
                                <input type="url" name="webhook_url" class="form-control" value="{{ config.webhook_url }}" placeholder="https://discord.com/api/webhooks/..." />
                            </div>
                            <button type="submit" class="btn btn-primary"><i class="bi bi-save"></i> Save Webhook</button>
                        </form>
                    </div>
                </div>
            </div>
            <!-- Configuration Tab -->
            <div class="tab-pane fade" id="config">
                <div class="card">
                    <div class="card-header"><i class="bi bi-file-earmark-code"></i> Current Configuration</div>
                    <div class="card-body">
                        <div class="config-box">{{ config_json }}</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <!-- Floating Action Buttons -->
    <div class="floating-buttons">
        {% if posting_active %}
        <form action="/stop" method="post" class="d-inline">
            <button class="btn btn-danger" title="Stop Auto Post">
                <i class="bi bi-stop-fill"></i>
            </button>
        </form>
        {% else %}
        <form action="/start" method="post" class="d-inline">
            <button class="btn btn-success" title="Start Auto Post">
                <i class="bi bi-play-fill"></i>
            </button>
        </form>
        {% endif %}
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Dark mode toggle
        document.getElementById('modeToggle').addEventListener('click', function() {
            document.body.classList.toggle('dark-mode');
            const icon = this.querySelector('i');
            icon.classList.toggle('bi-sun');
            icon.classList.toggle('bi-moon');
            
            // Save preference to server
            fetch('/save-dark-mode', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    dark_mode: document.body.classList.contains('dark-mode')
                })
            });
        });
        
        // Edit channel function
        function editChannel(id, msg, interval) {
            // Calculate hours, minutes, seconds
            const hours = Math.floor(interval / 3600);
            const minutes = Math.floor((interval % 3600) / 60);
            const seconds = interval % 60;
            
            // Redirect to edit mode
            window.location.href = `/edit-channel?channel_id=${id}&message=${encodeURIComponent(msg)}&hours=${hours}&minutes=${minutes}&seconds=${seconds}`;
        }
        
        // Cancel edit function
        function cancelEdit() {
            window.location.href = '/#channels';
        }
        
        // Auto-dismiss alerts after 5 seconds
        setTimeout(() => {
            document.querySelectorAll('.alert').forEach(alert => {
                new bootstrap.Alert(alert).close();
            });
        }, 5000);

        // Toggle visibility token
document.querySelector('.token-toggle').addEventListener('click', function() {
    const inp = document.querySelector('input[name="token"]');
    const icon = this.querySelector('i');
    if (inp.type === 'password') {
        inp.type = 'text';
        icon.classList.replace('bi-eye', 'bi-eye-slash');
    } else {
        inp.type = 'password';
        icon.classList.replace('bi-eye-slash', 'bi-eye');
    }
});

    </script>
</body>
</html>
'''

# Route untuk edit channel
@app.route("/edit-channel", methods=["GET"])
def edit_channel():
    channel_id = request.args.get("channel_id")
    message = request.args.get("message", "")
    hours = request.args.get("hours", 0)
    minutes = request.args.get("minutes", 0)
    seconds = request.args.get("seconds", 0)
    
    return render_template_string(
        html_template,
        config_json=json.dumps(config, indent=4),
        config=config,
        posting_active=posting_active,
        editing=True,
        original_channel_id=channel_id,
        channel_id=channel_id,
        channel_message=message,
        hours=hours,
        minutes=minutes,
        seconds=seconds
    )

if __name__ == "__main__":
    load_config()
    app.run(debug=True, host="0.0.0.0", port=5000)
