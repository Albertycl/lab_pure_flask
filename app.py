from flask import Flask, jsonify, request
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import time

app = Flask(__name__)

# ── 1. Metric objects (in-memory accumulators) ──

REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

IN_PROGRESS = Gauge(
    'http_requests_in_progress',
    'Number of HTTP requests currently being processed',
)

TASKS_CREATED = Counter('tasks_created_total', 'Total number of tasks created')
TASKS_DELETED = Counter('tasks_deleted_total', 'Total number of tasks deleted')

# ── 2. Middleware (auto-tracks every request) ──

@app.before_request
def before_request_func():
    request._start_time = time.time()
    IN_PROGRESS.inc()

@app.after_request
def after_request_func(response):
    latency = time.time() - request._start_time
    if request.path != '/metrics':
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.path,
            status=response.status_code
        ).inc()
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=request.path
        ).observe(latency)
    IN_PROGRESS.dec()
    return response

# ── 3. /metrics endpoint (Prometheus scrapes this) ──

@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

# ── Your existing routes (unchanged) ──

tasks = [
    {"id": 1, "title": "Buy groceries", "done": False},
    {"id": 2, "title": "Walk the dog", "done": False},
]
next_id = 3


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/tasks", methods=["GET"])
def get_tasks():
    return jsonify(tasks)


@app.route("/api/tasks", methods=["POST"])
def create_task():
    global next_id
    data = request.get_json()
    if not data or "title" not in data:
        return jsonify({"error": "title is required"}), 400
    task = {"id": next_id, "title": data["title"], "done": False}
    next_id += 1
    tasks.append(task)
    TASKS_CREATED.inc()
    return jsonify(task), 201


@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    for i, task in enumerate(tasks):
        if task["id"] == task_id:
            tasks.pop(i)
            TASKS_DELETED.inc()
            return jsonify({"message": "deleted"})
    return jsonify({"error": "not found"}), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
