import os
import jinja2
import json
import calendar
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import OperationalError

# ==========================================
# CONFIGURATION & SETUP
# ==========================================
app = Flask(__name__)

# Use SQLite for a simple, local file-based database
# IMPORTANT: use current working directory so DB lives next to EXE when packaged
basedir = os.path.abspath(os.getcwd())
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'agency.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'agency-secret-key-123'

db = SQLAlchemy(app)

# ==========================================
# DATABASE MODELS
# ==========================================
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    due_date = db.Column(db.String(20), nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Financial(db.Model):
    """Model to store monthly revenue (Legacy seeded data, now optional)"""
    id = db.Column(db.Integer, primary_key=True)
    month = db.Column(db.String(20), nullable=False)
    revenue = db.Column(db.Float, nullable=False)
    order_index = db.Column(db.Integer, default=0)

class Client(db.Model):
    """Model to store client details"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    company = db.Column(db.String(100))
    email = db.Column(db.String(100))
    status = db.Column(db.String(20), default='Lead') # Lead, Active, Churned
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Sale(db.Model):
    """Model to store sales records"""
    id = db.Column(db.Integer, primary_key=True)
    client_name = db.Column(db.String(100), nullable=False)
    service = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='In Progress') # In Progress, Closed Won, Closed Lost
    date = db.Column(db.String(20), nullable=False)

# ==========================================
# HTML TEMPLATES
# ==========================================

BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AgencyOS | Owner Tracker</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
    <style>
        body { background-color: #f4f6f9; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        .sidebar { min-height: 100vh; background: #1e293b; color: white; }
        .nav-link { color: #cbd5e1; margin-bottom: 5px; }
        .nav-link:hover, .nav-link.active { color: white; background: #334155; border-radius: 5px; }
        .card { border: none; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        .stat-card { border-left: 4px solid; }
        .status-done { text-decoration: line-through; color: gray; }
        .btn-primary { background-color: #3b82f6; border: none; }
        .btn-primary:hover { background-color: #2563eb; }
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="row">
            <!-- Sidebar -->
            <div class="col-md-2 sidebar p-3">
                <h3 class="text-center mb-4 fw-bold"><i class="bi bi-rocket-takeoff"></i> AgencyOS</h3>
                <ul class="nav flex-column">
                    <li class="nav-item">
                        <a class="nav-link {% if page == 'home' %}active{% endif %}" href="/">
                            <i class="bi bi-house-door me-2"></i> Home
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {% if page == 'dashboard' %}active{% endif %}" href="/dashboard">
                            <i class="bi bi-graph-up me-2"></i> Dashboard
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {% if page == 'workbench' %}active{% endif %}" href="/workbench">
                            <i class="bi bi-tools me-2"></i> Workbench
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {% if page == 'clients' %}active{% endif %}" href="/clients">
                            <i class="bi bi-people me-2"></i> Clients
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {% if page == 'sales' %}active{% endif %}" href="/sales">
                            <i class="bi bi-currency-dollar me-2"></i> Sales
                        </a>
                    </li>
                </ul>
                <hr>
                <div class="mt-auto text-center text-muted small">
                    &copy; 2025 Agency Owner
                </div>
            </div>

            <!-- Main Content -->
            <div class="col-md-10 p-4">
                {% block content %}{% endblock %}
            </div>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

HOME_TEMPLATE = """
{% extends "base" %}
{% block content %}
<div class="container">
    <div class="row align-items-center justify-content-center text-center" style="height: 80vh;">
        <div class="col-md-8">
            <h1 class="display-4 fw-bold text-primary mb-3">Welcome back, Boss.</h1>
            <p class="lead text-muted mb-5">Track your agency's growth, manage tasks, and deliver excellence.</p>
            <div class="d-flex gap-3 justify-content-center">
                <a href="/dashboard" class="btn btn-outline-dark btn-lg px-4"><i class="bi bi-graph-up"></i> Check Stats</a>
                <a href="/workbench" class="btn btn-primary btn-lg px-4"><i class="bi bi-plus-circle"></i> Add New Task</a>
            </div>
        </div>
    </div>
</div>
{% endblock %}
"""

DASHBOARD_TEMPLATE = """
{% extends "base" %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <h2 class="fw-bold">Agency Analytics</h2>
    
    <!-- Timeframe Selector Form -->
    <form action="/dashboard" method="GET" class="d-flex align-items-center">
        <label class="me-2 text-muted small fw-bold">View Data:</label>
        <select name="timeframe" class="form-select form-select-sm border-0 shadow-sm bg-white fw-bold text-primary" style="width: auto; cursor: pointer;" onchange="this.form.submit()">
            <option value="1m" {% if selected_timeframe == '1m' %}selected{% endif %}>Last 30 Days</option>
            <option value="3m" {% if selected_timeframe == '3m' %}selected{% endif %}>Last 3 Months</option>
            <option value="6m" {% if selected_timeframe == '6m' %}selected{% endif %}>Last 6 Months</option>
            <option value="1y" {% if selected_timeframe == '1y' %}selected{% endif %}>Last Year</option>
            <option value="all" {% if selected_timeframe == 'all' %}selected{% endif %}>All Time</option>
        </select>
    </form>
</div>

<!-- Key Metrics Row -->
<div class="row mb-4">
    <div class="col-md-3">
        <div class="card stat-card p-3 h-100" style="border-color: #3b82f6;">
            <h6 class="text-muted">Revenue ({{ selected_label }})</h6>
            <h3>${{ current_revenue }}</h3>
            <small class="text-success"><i class="bi bi-check-circle"></i> Closed won deals</small>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card stat-card p-3 h-100" style="border-color: #10b981;">
            <h6 class="text-muted">Active Clients</h6>
            <h3>{{ active_clients }}</h3>
            <small class="text-muted">Generating recurring rev</small>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card stat-card p-3 h-100" style="border-color: #f59e0b;">
            <h6 class="text-muted">Pending Tasks</h6>
            <h3>{{ pending_count }}</h3>
            <small class="text-warning">Focus required</small>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card stat-card p-3 h-100" style="border-color: #ef4444;">
            <h6 class="text-muted">Pipeline ({{ selected_label }})</h6>
            <h3>${{ pipeline_value }}</h3>
            <small class="text-primary">Potential deal value</small>
        </div>
    </div>
</div>

<!-- Charts Row -->
<div class="row">
    <div class="col-md-8 mb-4">
        <div class="card p-4 h-100">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h5 class="m-0">Revenue Trend</h5>
                <span class="badge bg-light text-muted">{{ selected_label }}</span>
            </div>
            <div style="height: 300px;">
                <canvas id="revenueChart"></canvas>
            </div>
        </div>
    </div>
    <div class="col-md-4 mb-4">
        <div class="card p-4 h-100">
            <h5>Task Distribution</h5>
            <div style="height: 300px;">
                <canvas id="taskChart"></canvas>
            </div>
        </div>
    </div>
</div>

<script>
    // Revenue Chart
    const ctxRev = document.getElementById('revenueChart').getContext('2d');
    const revenueLabels = {{ revenue_labels | safe }};
    const revenueData = {{ revenue_data | safe }};

    new Chart(ctxRev, {
        type: 'line',
        data: {
            labels: revenueLabels,
            datasets: [{
                label: 'Revenue ($)',
                data: revenueData,
                borderColor: '#3b82f6',
                tension: 0.3,
                fill: true,
                backgroundColor: 'rgba(59, 130, 246, 0.1)'
            }]
        },
        options: { 
            responsive: true, 
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { borderDash: [2, 4] }
                },
                x: {
                    grid: { display: false }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return '$' + context.parsed.y.toLocaleString();
                        }
                    }
                }
            }
        }
    });

    // Task Distribution Chart
    const ctxTask = document.getElementById('taskChart').getContext('2d');
    const taskLabels = {{ category_labels | safe }};
    const taskData = {{ category_data | safe }};

    new Chart(ctxTask, {
        type: 'doughnut',
        data: {
            labels: taskLabels,
            datasets: [{
                data: taskData,
                backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#6366f1', '#ef4444'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '70%',
            plugins: {
                legend: { position: 'bottom' }
            }
        }
    });
</script>
{% endblock %}
"""

WORKBENCH_TEMPLATE = """
{% extends "base" %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <h2 class="fw-bold">Workbench</h2>
    <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#addTaskModal">
        <i class="bi bi-plus-lg"></i> New Task
    </button>
</div>

<div class="row">
    <div class="col-md-12">
        <div class="card p-0 overflow-hidden">
            <div class="card-header bg-white py-3">
                <h5 class="m-0">Current Agenda</h5>
            </div>
            <div class="table-responsive">
                <table class="table table-hover mb-0 align-middle">
                    <thead class="table-light">
                        <tr>
                            <th>Status</th>
                            <th>Task</th>
                            <th>Category</th>
                            <th>Due Date</th>
                            <th class="text-end">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for task in tasks %}
                        <tr class="{% if task.is_completed %}table-light{% endif %}">
                            <td>
                                {% if task.is_completed %}
                                <span class="badge bg-success rounded-pill">Done</span>
                                {% else %}
                                <span class="badge bg-warning text-dark rounded-pill">Pending</span>
                                {% endif %}
                            </td>
                            <td class="{% if task.is_completed %}status-done{% endif %} fw-bold">
                                {{ task.title }}
                            </td>
                            <td>
                                <span class="badge border text-dark bg-light">{{ task.category }}</span>
                            </td>
                            <td class="{% if task.is_completed %}status-done{% endif %}">
                                {{ task.due_date }}
                            </td>
                            <td class="text-end">
                                {% if not task.is_completed %}
                                <a href="/complete/{{ task.id }}" class="btn btn-sm btn-outline-success me-1" title="Mark Done">
                                    <i class="bi bi-check-lg"></i>
                                </a>
                                {% endif %}
                                <a href="/delete/{{ task.id }}" class="btn btn-sm btn-outline-danger" title="Delete" onclick="return confirm('Remove this task?')">
                                    <i class="bi bi-trash"></i>
                                </a>
                            </td>
                        </tr>
                        {% else %}
                        <tr>
                            <td colspan="5" class="text-center py-4 text-muted">
                                <i class="bi bi-inbox display-6 d-block mb-2"></i>
                                No tasks scheduled. Time to scale?
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<div class="modal fade" id="addTaskModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Schedule Item</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <form action="/add_task" method="POST">
                <div class="modal-body">
                    <div class="mb-3">
                        <label class="form-label">Task Title</label>
                        <input type="text" name="title" class="form-control" placeholder="e.g. Client Review Meeting" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Category</label>
                        <select name="category" class="form-select">
                            <option value="Meeting">Meeting</option>
                            <option value="Delivery">Project Delivery</option>
                            <option value="Outreach">Sales/Outreach</option>
                            <option value="Admin">Admin/Finance</option>
                            <option value="Strategy">Strategy</option>
                        </select>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Due Date</label>
                        <input type="date" name="due_date" class="form-control" required>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    <button type="submit" class="btn btn-primary">Add to Workbench</button>
                </div>
            </form>
        </div>
    </div>
</div>
{% endblock %}
"""

CLIENTS_TEMPLATE = """
{% extends "base" %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <h2 class="fw-bold">Client Directory</h2>
    <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#addClientModal">
        <i class="bi bi-person-plus-fill"></i> Add Client
    </button>
</div>

<div class="card border-0 shadow-sm">
    <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
            <thead class="table-light">
                <tr>
                    <th>Client / Company</th>
                    <th>Contact</th>
                    <th>Status</th>
                    <th class="text-end">Actions</th>
                </tr>
            </thead>
            <tbody>
                {% for client in clients %}
                <tr>
                    <td>
                        <div class="fw-bold">{{ client.name }}</div>
                        <div class="small text-muted">{{ client.company }}</div>
                    </td>
                    <td>
                        <a href="mailto:{% if client.email %}{{ client.email }}{% endif %}" class="text-decoration-none">{{ client.email }}</a>
                    </td>
                    <td>
                        {% if client.status == 'Active' %}
                            <span class="badge bg-success bg-opacity-10 text-success px-3">Active</span>
                        {% elif client.status == 'Lead' %}
                            <span class="badge bg-primary bg-opacity-10 text-primary px-3">Lead</span>
                        {% else %}
                            <span class="badge bg-secondary bg-opacity-10 text-secondary px-3">{{ client.status }}</span>
                        {% endif %}
                    </td>
                    <td class="text-end">
                        <a href="/delete_client/{{ client.id }}" class="btn btn-sm btn-outline-danger" onclick="return confirm('Delete this client?')"><i class="bi bi-trash"></i></a>
                    </td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="4" class="text-center py-5 text-muted">
                        <i class="bi bi-people display-4 d-block mb-3"></i>
                        No clients found. Add your first client!
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>

<!-- Add Client Modal -->
<div class="modal fade" id="addClientModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">New Client</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <form action="/add_client" method="POST">
                <div class="modal-body">
                    <div class="mb-3">
                        <label class="form-label">Full Name</label>
                        <input type="text" name="name" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Company Name</label>
                        <input type="text" name="company" class="form-control">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Email Address</label>
                        <input type="email" name="email" class="form-control">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Status</label>
                        <select name="status" class="form-select">
                            <option value="Lead">Lead</option>
                            <option value="Active">Active</option>
                            <option value="Churned">Churned</option>
                        </select>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    <button type="submit" class="btn btn-primary">Save Client</button>
                </div>
            </form>
        </div>
    </div>
</div>
{% endblock %}
"""

SALES_TEMPLATE = """
{% extends "base" %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <h2 class="fw-bold">Sales Tracker</h2>
    <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#addSaleModal">
        <i class="bi bi-currency-dollar"></i> Record Sale
    </button>
</div>

<div class="row mb-4">
    <div class="col-md-12">
        <div class="card border-0 shadow-sm">
            <div class="table-responsive">
                <table class="table table-hover align-middle mb-0">
                    <thead class="table-light">
                        <tr>
                            <th>Client</th>
                            <th>Service / Deal</th>
                            <th>Date</th>
                            <th>Amount</th>
                            <th>Status</th>
                            <th class="text-end">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for sale in sales %}
                        <tr>
                            <td class="fw-bold">{{ sale.client_name }}</td>
                            <td>{{ sale.service }}</td>
                            <td>{{ sale.date }}</td>
                            <td>${{ sale.amount }}</td>
                            <td>
                                {% if sale.status == 'Closed Won' %}
                                    <span class="badge bg-success">Won</span>
                                {% elif sale.status == 'Closed Lost' %}
                                    <span class="badge bg-danger">Lost</span>
                                {% else %}
                                    <span class="badge bg-warning text-dark">In Progress</span>
                                {% endif %}
                            </td>
                            <td class="text-end">
                                <a href="/delete_sale/{{ sale.id }}" class="btn btn-sm btn-outline-danger" onclick="return confirm('Remove this record?')"><i class="bi bi-trash"></i></a>
                            </td>
                        </tr>
                        {% else %}
                        <tr>
                            <td colspan="6" class="text-center py-5 text-muted">
                                <i class="bi bi-wallet2 display-4 d-block mb-3"></i>
                                No sales records found.
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<!-- Add Sale Modal -->
<div class="modal fade" id="addSaleModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Record New Deal</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <form action="/add_sale" method="POST">
                <div class="modal-body">
                    <div class="mb-3">
                        <label class="form-label">Client</label>
                        <select name="client_name" class="form-select" required>
                            <option value="" disabled selected>Select a client...</option>
                            {% for client in clients %}
                                <option value="{{ client.name }}">{{ client.name }} ({{ client.company }})</option>
                            {% endfor %}
                        </select>
                        {% if not clients %}
                            <div class="form-text text-danger">No clients found. Please add a client first.</div>
                        {% endif %}
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Service / Project Name</label>
                        <input type="text" name="service" class="form-control" placeholder="e.g. SEO Package" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Deal Value ($)</label>
                        <input type="number" step="0.01" name="amount" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Closing Date</label>
                        <input type="date" name="date" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Status</label>
                        <select name="status" class="form-select">
                            <option value="In Progress">In Progress / Negotiating</option>
                            <option value="Closed Won">Closed Won</option>
                            <option value="Closed Lost">Closed Lost</option>
                        </select>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    <button type="submit" class="btn btn-primary">Save Deal</button>
                </div>
            </form>
        </div>
    </div>
</div>
{% endblock %}
"""

# Register templates in memory
app.jinja_loader = jinja2.DictLoader({
    'base': BASE_TEMPLATE,
    'home': HOME_TEMPLATE,
    'dashboard': DASHBOARD_TEMPLATE,
    'workbench': WORKBENCH_TEMPLATE,
    'clients': CLIENTS_TEMPLATE,
    'sales': SALES_TEMPLATE
})

# ==========================================
# ROUTES & LOGIC
# ==========================================

@app.route('/')
def home():
    return render_template('home', page='home')

@app.route('/dashboard')
def dashboard():
    # --- 1. Get Timeframe & Configure Date Logic ---
    timeframe = request.args.get('timeframe', '6m')
    today = datetime.today()
    start_date_obj = None
    
    label_map = {
        '1m': 'Last 30 Days',
        '3m': 'Last 3 Months',
        '6m': 'Last 6 Months',
        '1y': 'Last Year',
        'all': 'All Time'
    }
    selected_label = label_map.get(timeframe, 'Last 6 Months')

    # Determine Start Date for Filtering
    if timeframe == '1m':
        start_date_obj = today - timedelta(days=30)
    elif timeframe == '3m':
        start_date_obj = today - timedelta(days=90)
    elif timeframe == '6m':
        start_date_obj = today - timedelta(days=180)
    elif timeframe == '1y':
        start_date_obj = today - timedelta(days=365)
    else:
        # For 'all', we pick an old date
        start_date_obj = datetime(1900, 1, 1)

    cutoff_date_str = start_date_obj.strftime('%Y-%m-%d')

    # --- 2. KPI Queries (Filtered by Date) ---
    pending_count = Task.query.filter_by(is_completed=False).count()
    active_clients = Client.query.filter_by(status='Active').count()
    
    # Filter Pipeline (In Progress)
    pipeline_query = Sale.query.filter(Sale.status == 'In Progress')
    if timeframe != 'all':
        pipeline_query = pipeline_query.filter(Sale.date >= cutoff_date_str)
    pipeline_value = sum(deal.amount for deal in pipeline_query.all())

    # Filter Revenue (Closed Won)
    revenue_query = Sale.query.filter(Sale.status == 'Closed Won')
    if timeframe != 'all':
        revenue_query = revenue_query.filter(Sale.date >= cutoff_date_str)
    total_revenue = sum(deal.amount for deal in revenue_query.all())
    
    # --- 3. Graph Data Generation (REAL Sales Data) ---
    revenue_labels = []
    revenue_data = []
    
    # Fetch filtered sales for graphing
    graph_query = Sale.query.filter(Sale.status == 'Closed Won')
    if timeframe != 'all':
        graph_query = graph_query.filter(Sale.date >= cutoff_date_str)
    sales_data = graph_query.order_by(Sale.date).all()

    if timeframe == '1m':
        # === Daily Breakdown for Last 30 Days ===
        sales_map = {}
        for s in sales_data:
            sales_map[s.date] = sales_map.get(s.date, 0) + s.amount
            
        current = start_date_obj
        while current <= today:
            d_str = current.strftime('%Y-%m-%d')
            label = current.strftime('%d %b')
            
            revenue_labels.append(label)
            revenue_data.append(sales_map.get(d_str, 0))
            
            current += timedelta(days=1)
    else:
        # === Monthly Breakdown ===
        sales_map = {}
        for s in sales_data:
            m_key = s.date[:7]  # YYYY-MM
            sales_map[m_key] = sales_map.get(m_key, 0) + s.amount
            
        if timeframe == 'all':
            if sales_data:
                try:
                    first_sale_date = datetime.strptime(sales_data[0].date, '%Y-%m-%d')
                    loop_date = first_sale_date.replace(day=1)
                except:
                    loop_date = today.replace(day=1)
            else:
                loop_date = today.replace(day=1)
        else:
            loop_date = start_date_obj.replace(day=1)
            
        while loop_date <= today:
            m_key = loop_date.strftime('%Y-%m')
            label = loop_date.strftime('%b %Y')
            
            revenue_labels.append(label)
            revenue_data.append(sales_map.get(m_key, 0))
            
            next_m = loop_date + timedelta(days=32)
            loop_date = next_m.replace(day=1)

    # --- 4. Task Chart Data ---
    categories = ["Meeting", "Delivery", "Outreach", "Admin", "Strategy"]
    cat_data = [Task.query.filter_by(category=cat).count() for cat in categories]

    return render_template(
        'dashboard', 
        page='dashboard',
        selected_timeframe=timeframe,
        selected_label=selected_label,
        pending_count=pending_count,
        active_clients=active_clients,
        pipeline_value=f"{pipeline_value:,}",
        current_revenue=f"{int(total_revenue):,}", 
        category_labels=json.dumps(categories),
        category_data=json.dumps(cat_data),
        revenue_labels=json.dumps(revenue_labels),
        revenue_data=json.dumps(revenue_data)
    )

@app.route('/workbench')
def workbench():
    tasks = Task.query.order_by(Task.is_completed, Task.due_date).all()
    return render_template('workbench', page='workbench', tasks=tasks)

@app.route('/add_task', methods=['POST'])
def add_task():
    title = request.form.get('title')
    category = request.form.get('category')
    due_date = request.form.get('due_date')
    new_task = Task(title=title, category=category, due_date=due_date)
    db.session.add(new_task)
    db.session.commit()
    return redirect(url_for('workbench'))

@app.route('/complete/<int:id>')
def complete_task(id):
    task = Task.query.get_or_404(id)
    task.is_completed = True
    db.session.commit()
    return redirect(url_for('workbench'))

@app.route('/delete/<int:id>')
def delete_task(id):
    task = Task.query.get_or_404(id)
    db.session.delete(task)
    db.session.commit()
    return redirect(url_for('workbench'))

# --- CLIENT ROUTES ---
@app.route('/clients')
def clients():
    all_clients = Client.query.order_by(Client.created_at.desc()).all()
    return render_template('clients', page='clients', clients=all_clients)

@app.route('/add_client', methods=['POST'])
def add_client():
    name = request.form.get('name')
    company = request.form.get('company')
    email = request.form.get('email')
    status = request.form.get('status')
    
    new_client = Client(name=name, company=company, email=email, status=status)
    db.session.add(new_client)
    db.session.commit()
    return redirect(url_for('clients'))

@app.route('/delete_client/<int:id>')
def delete_client(id):
    client = Client.query.get_or_404(id)
    db.session.delete(client)
    db.session.commit()
    return redirect(url_for('clients'))

# --- SALES ROUTES ---
@app.route('/sales')
def sales():
    all_sales = Sale.query.order_by(Sale.id.desc()).all()
    all_clients = Client.query.all()
    return render_template('sales', page='sales', sales=all_sales, clients=all_clients)

@app.route('/add_sale', methods=['POST'])
def add_sale():
    client_name = request.form.get('client_name')
    service = request.form.get('service')
    amount = float(request.form.get('amount'))
    date = request.form.get('date')
    status = request.form.get('status')
    
    new_sale = Sale(client_name=client_name, service=service, amount=amount, date=date, status=status)
    db.session.add(new_sale)
    db.session.commit()
    return redirect(url_for('sales'))

@app.route('/delete_sale/<int:id>')
def delete_sale(id):
    sale = Sale.query.get_or_404(id)
    db.session.delete(sale)
    db.session.commit()
    return redirect(url_for('sales'))

# ==========================================
# INITIALIZATION HELPERS (for desktop + dev)
# ==========================================
def seed_financials_dynamically():
    """Generates data for the LAST 6 MONTHS relative to today."""
    print("Generating fresh financial data...")
    today = datetime.today()
    base_revenue = 25000
    Financial.query.delete()
    seeds = []
    for i in range(5, -1, -1):
        date = today - timedelta(days=30 * i)
        month_name = date.strftime("%b")
        rev = base_revenue + (5000 * (6 - i))
        if i == 2:
            rev -= 3000
        seeds.append(Financial(month=month_name, revenue=rev, order_index=6-i))
    db.session.add_all(seeds)
    db.session.commit()

def init_db():
    """Create/repair schema and seed initial data."""
    with app.app_context():
        try:
            db.create_all()
            Financial.query.first()
            Client.query.first()
        except OperationalError:
            print("Schema mismatch (adding new tables). Rebuilding...")
            db.drop_all()
            db.create_all()

        if Financial.query.count() != 6:
            seed_financials_dynamically()

        if Task.query.count() == 0:
            task_seeds = [
                Task(title="Q3 Strategy Call", category="Meeting", due_date="2023-11-01"),
                Task(title="Deliver Mockups", category="Delivery", due_date="2023-11-05"),
            ]
            db.session.add_all(task_seeds)
            db.session.commit()

def run_flask():
    """Initialize DB and run the Flask server (for desktop wrapper or dev)."""
    init_db()
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )

if __name__ == '__main__':
    # Development mode: run with Python directly
    run_flask()
