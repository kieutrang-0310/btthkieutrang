# -*- coding: utf-8 -*-
"""
Database configuration for Minh An AI Agent.
Compatible with both Localhost and Vercel Serverless environment.
"""
import sqlite3
import os
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# On Vercel, the filesystem is read-only except /tmp
if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    DB_PATH = "/tmp/minhan_sales.db"
    source_db = os.path.join(BASE_DIR, "minhan_sales.db")
    if not os.path.exists(DB_PATH) and os.path.exists(source_db):
        try:
            shutil.copyfile(source_db, DB_PATH)
        except Exception:
            pass
else:
    DB_PATH = os.path.join(BASE_DIR, "minhan_sales.db")

def get_connection():
    # If DB does not exist, initialize it
    if not os.path.exists(DB_PATH):
        init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(reset_all=False):
    # Ensure directory exists if needed
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        try:
            os.makedirs(db_dir, exist_ok=True)
        except Exception:
            pass

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Bảng sản phẩm & giá niêm yết
    cur.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        unit TEXT NOT NULL,
        unit_price REAL NOT NULL,
        stock_qty INTEGER NOT NULL DEFAULT 0,
        lead_time_days INTEGER NOT NULL DEFAULT 7,
        warranty_months INTEGER NOT NULL DEFAULT 12,
        description TEXT
    )
    ''')

    # 2. Bảng Nhân viên Kinh doanh (6 NVKD Minh An)
    cur.execute('''
    CREATE TABLE IF NOT EXISTS sales_reps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        phone TEXT,
        current_leads INTEGER DEFAULT 0,
        specialty TEXT
    )
    ''')

    # 3. Bảng Hồ sơ Cơ hội
    cur.execute('''
    CREATE TABLE IF NOT EXISTS opportunities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        client_name TEXT,
        client_company TEXT,
        client_email TEXT,
        client_phone TEXT,
        raw_request TEXT NOT NULL,
        status TEXT NOT NULL, 
        is_info_sufficient INTEGER DEFAULT 1,
        missing_info_notes TEXT,
        assigned_rep_id INTEGER,
        assigned_rep_name TEXT,
        requested_budget REAL DEFAULT 0,
        requested_deadline TEXT,
        feasible_deadline TEXT,
        deadline_status TEXT, 
        total_original_price REAL DEFAULT 0,
        requested_discount_pct REAL DEFAULT 0,
        approved_discount_pct REAL DEFAULT 0,
        total_final_price REAL DEFAULT 0,
        requires_manager_approval INTEGER DEFAULT 0,
        approval_status TEXT DEFAULT 'NOT_REQUIRED', 
        manager_notes TEXT,
        proposal_email_draft TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (assigned_rep_id) REFERENCES sales_reps (id)
    )
    ''')

    # 4. Bảng Chi tiết Hạng mục
    cur.execute('''
    CREATE TABLE IF NOT EXISTS opportunity_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        opportunity_id INTEGER NOT NULL,
        product_id INTEGER,
        matched_sku TEXT,
        matched_name TEXT,
        requested_name TEXT,
        quantity INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        total_price REAL NOT NULL,
        stock_available INTEGER NOT NULL,
        is_stock_sufficient INTEGER NOT NULL,
        item_lead_time_days INTEGER DEFAULT 0,
        FOREIGN KEY (opportunity_id) REFERENCES opportunities (id),
        FOREIGN KEY (product_id) REFERENCES products (id)
    )
    ''')

    # 5. Bảng To-Do Tasks
    cur.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        completed INTEGER DEFAULT 0,
        emoji TEXT DEFAULT '📋',
        due_info TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 6. Bảng Hoạt động
    cur.execute('''
    CREATE TABLE IF NOT EXISTS activities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        icon_type TEXT DEFAULT 'check',
        time_ago TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 7. Cài đặt hệ thống
    cur.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    ''')

    # 8. Bảng Đánh giá & Feedback của khách hàng (Để trống ban đầu, chỉ hiển thị khi khách hàng thực tế gửi đánh giá)
    cur.executescript('''
    CREATE TABLE IF NOT EXISTS customer_feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        contact TEXT,
        stars INTEGER DEFAULT 5,
        comment TEXT NOT NULL,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS customer_decisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT NOT NULL,
        client_name TEXT,
        client_company TEXT,
        decision TEXT NOT NULL, -- 'APPROVED' hoặc 'REJECTED'
        reason TEXT,
        feedback TEXT,
        pic TEXT,
        department TEXT,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        company_name TEXT NOT NULL,
        fullname TEXT,
        email TEXT,
        role TEXT DEFAULT 'Enterprise Manager',
        created_at TEXT
    );
    ''')

    conn.commit()

    # Seed products if empty
    cur.execute('SELECT COUNT(*) FROM products')
    if cur.fetchone()[0] == 0:
        seed_sample_data(conn)

    # Clean settings by default
    default_settings = [
        ('custom_kpi_done', '0'),
        ('custom_kpi_progress', '0'),
        ('custom_kpi_completed', '0'),
        ('custom_kpi_focus', '0h'),
        ('user_name', 'Quản trị viên'),
        ('user_greeting', 'Chào mừng bạn đến với Công nghệ Cô Nàng Tinh Nghịch! ✨'),
        ('company_name', 'Công ty Cổ phần Công nghệ Cô Nàng Tinh Nghịch'),
        ('chart_data', '{"labels": ["T2", "T3", "T4", "T5", "T6", "T7", "CN"], "values": [0, 0, 0, 0, 0, 0, 0], "badge": "Nhấp để đổi ghi chú"}')
    ]
    for k, v in default_settings:
        cur.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (k, v))

    if reset_all:
        cur.execute('DELETE FROM opportunities')
        cur.execute('DELETE FROM opportunity_items')
        cur.execute('DELETE FROM tasks')
        cur.execute('DELETE FROM activities')
        cur.execute('UPDATE sales_reps SET current_leads = 0')
        for k, v in default_settings:
            cur.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (k, v))

    conn.commit()
    conn.close()

def seed_sample_data(conn):
    cur = conn.cursor()
    # 6 NVKD của Công ty Cổ phần Công nghệ Cô Nàng Tinh Nghịch
    sales_reps = [
        ('KD01', 'Trần Phương Thảo', 'thao.tp@conangtinhnghich.vn', '0912 345 671', 0, 'Phòng Kinh Doanh B2B'),
        ('KD02', 'Lê Hải Đăng', 'dang.lh@conangtinhnghich.vn', '0912 345 672', 0, 'Phòng Kỹ Thuật & Giải Pháp'),
        ('KD03', 'Phạm Quốc Tuấn', 'tuan.pq@conangtinhnghich.vn', '0912 345 673', 0, 'Phòng Vận Hành & Kho Vận'),
        ('KD04', 'Vũ Thu Trang', 'trang.vt@conangtinhnghich.vn', '0912 345 674', 0, 'Phòng Chăm Sóc Khách Hàng'),
        ('KD05', 'Nguyễn Hoàng Nam', 'nam.nh@conangtinhnghich.vn', '0912 345 675', 0, 'Phòng Kinh Doanh B2B'),
        ('KD06', 'Đỗ Mai Anh', 'anh.dm@conangtinhnghich.vn', '0912 345 676', 0, 'Phòng Kỹ Thuật & Giải Pháp'),
    ]
    cur.executemany('''
    INSERT OR IGNORE INTO sales_reps (code, name, email, phone, current_leads, specialty)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', sales_reps)

    # KHÔNG gán sẵn sản phẩm và giá giả lập (để người dùng tự nhập sản phẩm mới và hệ thống tự động phân tích)
    conn.commit()

if __name__ == "__main__":
    init_db(reset_all=True)
    print("Database ready for Localhost & Vercel.")
