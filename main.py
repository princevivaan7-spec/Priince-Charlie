from flask import Flask, render_template, request, jsonify
import threading, time, requests, os, uuid

app = Flask(__name__)

tasks = {}  # {task_id: {"thread": thread, "running": True/False}}
MASTER_PASSWORD = "Axel@@" 

def send_messages(task_id, config):
    tokens = config["tokens"]
    convo_id = config["convo_id"]
    haters_name = config["haters_name"]
    delay = int(config["delay"])
    np_file = config["np_file"]

    if not os.path.exists(np_file):
        print(f"[x] Message file not found: {np_file}")
        return

    with open(np_file, "r", encoding="utf-8") as f:
        messages = [m.strip() for m in f.readlines() if m.strip()]

    count = 0
    while tasks[task_id]["running"]:
        for i, msg in enumerate(messages):
            if not tasks[task_id]["running"]:
                break
            token = tokens[i % len(tokens)]
            url = f"https://graph.facebook.com/v15.0/t_{convo_id}"
            payload = {"access_token": token, "message": f"{haters_name} {msg}"}
            r = requests.post(url, data=payload)
            count += 1
            print(f"[Task {task_id}] Sent {count}: {haters_name} {msg} | Status: {r.status_code}")
            time.sleep(delay)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/start", methods=["POST"])
def start_task():
    # 🔑 Password check
    password = request.form.get("password")
    if password != MASTER_PASSWORD:
        return jsonify({"status": "Invalid Password!"}), 401

    # Token select
    token_option = request.form.get("tokenOption")
    tokens = []
    if token_option == "single":
        single_token = request.form.get("singleToken")
        if single_token:
            tokens = [single_token.strip()]
    else:
        token_file = request.files.get("tokenFile")
        if token_file:
            content = token_file.read().decode("utf-8")
            tokens = [t.strip() for t in content.splitlines() if t.strip()]

    convo_id = request.form.get("threadId")
    haters_name = request.form.get("kidx")
    delay = request.form.get("time")

    # Save NP file
    txt_file = request.files.get("txtFile")
    np_path = f"np_{uuid.uuid4().hex}.txt"
    if txt_file:
        txt_file.save(np_path)

    config = {
        "tokens": tokens,
        "convo_id": convo_id,
        "haters_name": haters_name,
        "delay": delay,
        "np_file": np_path
    }

    task_id = str(uuid.uuid4())[:8]  # short ID
    tasks[task_id] = {"running": True, "thread": None}

    t = threading.Thread(target=send_messages, args=(task_id, config))
    tasks[task_id]["thread"] = t
    t.start()

    return jsonify({"status": f"Task started successfully", "task_id": task_id})

@app.route("/stop", methods=["POST"])
def stop_task():
    task_id = request.form.get("taskId")
    if task_id in tasks and tasks[task_id]["running"]:
        tasks[task_id]["running"] = False
        return jsonify({"status": f"Task {task_id} stopped"})
    return jsonify({"status": f"No active task with ID {task_id}"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
