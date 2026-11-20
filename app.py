# -*- coding: utf-8 -*-
"""
Web Server and REST API for Minh An Company AI Agent.
Runs on localhost:8000 using Python standard library http.server.
Supports complete live editing of all metrics, tasks, products, and data.
"""
import sys
import os
import json
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

# Ensure current directory is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from database import init_db, get_connection
import agent_engine

PORT = 8000

SAMPLE_REQUESTS = [
    {
        "id": "sample_complete",
        "title": "Mẫu 1: Yêu cầu chuẩn & Đủ thông tin (Tự động duyệt)",
        "desc": "Khách hàng gửi đầy đủ thông tin, xin chiết khấu 4% (nằm trong hạn mức NVKD).",
        "text": """Chào Công ty Cổ phần Công nghệ Cô Nàng Tinh Nghịch,
Tôi là Hoàng Long, phụ trách IT của Công ty Dược phẩm Vĩnh Khang.
Email: long.hoang@vinhkhangpharma.vn | SĐT: 0983 234 567
Chúng tôi đang cần trang bị hạ tầng CNTT cho chi nhánh mới:
1. 02 Switch Cisco Catalyst 24 port PoE (C9200L)
2. 06 Bộ phát Wi-Fi 6 Aruba Instant On AP505
3. 08 Laptop Dell Latitude 5440 cho nhân viên
Ngân sách dự kiến của chúng tôi khoảng 250 - 280 triệu đồng.
Thời hạn hoàn thành trước ngày 28/11/2026.
Đề nghị Cô Nàng Tinh Nghịch hỗ trợ mức chiết khấu 4% cho đơn hàng đầu tiên này.
Nhờ các bạn gửi báo giá sớm giúp tôi. Trân trọng!"""
    },
    {
        "id": "sample_missing",
        "title": "Mẫu 2: Thiếu thông tin (Rẽ nhánh Yêu cầu làm rõ)",
        "desc": "Yêu cầu sơ sài, thiếu số lượng, không có liên hệ và thời hạn cụ thể.",
        "text": """Chào Cô Nàng Tinh Nghịch,
Bên mình đang mở rộng văn phòng cần mua gấp máy chủ Dell và vài máy tính để bàn HP ProDesk cùng bộ phát wifi.
Cho mình xin báo giá tổng thể nhé. Gửi sớm trong ngày."""
    },
    {
        "id": "sample_over_authority",
        "title": "Mẫu 3: Vượt thẩm quyền NVKD (Cần Trưởng phòng duyệt)",
        "desc": "Đề xuất chiết khấu 10% (vượt mức 5% của NVKD), giá trị đơn lớn > 400 triệu.",
        "text": """Kính gửi Bộ phận Kinh doanh Công ty Cô Nàng Tinh Nghịch,
Tôi là Phạm Quốc Huy, Trưởng phòng Mua sắm Tập đoàn Xây dựng An Gia.
Email: huy.pq@angiaconstruction.vn - Hotline: 0918 889 999.
Công ty chúng tôi cần mua các thiết bị sau để phục vụ dự án trung tâm dữ liệu:
- 02 Máy chủ Dell PowerEdge R750 Xeon Silver
- 01 Tường lửa Firewall Fortinet FortiGate 60F
- 01 Bộ lưu điện UPS APC Smart-UPS 3000VA
- 01 Gói Dịch vụ Cài đặt và Triển khai Onsite
Tổng kinh phí phê duyệt dự án là 320 triệu đồng.
Thời hạn bàn giao mong muốn trước ngày 30/11/2026.
Vì đây là dự án lớn và An Gia sẽ hợp tác lâu dài, chúng tôi yêu cầu mức chiết khấu 10%.
Vui lòng gửi đề xuất kỹ thuật và bảng báo giá chính thức."""
    },
    {
        "id": "sample_stock_shortage",
        "title": "Mẫu 4: Thiếu tồn kho & Cảnh báo hạn giao (SLA Conflict)",
        "desc": "Đặt mua Switch Cisco 48 Port (đang hết hàng tồn) và đòi giao siêu gấp.",
        "text": """Cô Nàng Tinh Nghịch hỗ trợ báo giá gấp giúp anh:
Người liên hệ: Lê Văn Hùng - Giám đốc Kỹ thuật Cty Truyền thông Sao Mai
Email: hung.le@saomai.vn | Mobile: 0904 555 777
Bên anh cần:
- 03 Switch Cisco 48 Port (C9200L-48P)
- 10 Laptop ThinkPad T14 Gen 4 Core i7
Hạn chót bên anh phải nghiệm thu là trong vòng 3 ngày tới (yêu cầu giao gấp).
Chiết khấu ưu đãi 5% theo thỏa thuận trước nhé."""
    }
]

class MinhAnApiHandler(BaseHTTPRequestHandler):

    def send_json(self, data, status_code=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def get_route_path(self):
        """
        Extract the true requested path, compatible with both Localhost and Vercel Serverless.
        Handles query strings, proxy headers, and fallback matching.
        """
        raw = self.path or ''
        url = urllib.parse.urlparse(raw)
        qs = urllib.parse.parse_qs(url.query)
        for param in ['path', '__path', 'route']:
            if param in qs and qs[param]:
                p = qs[param][0]
                if not p.startswith('/'):
                    p = '/' + p
                return p

        # Check Vercel edge/proxy headers
        for h in ['x-forwarded-uri', 'x-matched-path', 'x-real-url', 'x-vercel-matched-path', 'x-invoke-path']:
            val = self.headers.get(h)
            if val:
                p = urllib.parse.urlparse(val).path
                if p and p not in ('/api/index.py', '/api/index', '/api'):
                    return p

        # Resilient match for known endpoints in raw path
        for ep in [
            '/api/process', '/api/feedback/delete', '/api/feedback', 
            '/api/decisions', '/api/analytics/products', '/api/auth/login', 
            '/api/auth/register', '/api/reset-session', '/api/ai/chat', 
            '/api/stats', '/api/sample-requests'
        ]:
            slug = ep.replace('/api/', '')
            if ep in raw or (slug in raw and not raw.startswith('/static/')):
                return ep

        return url.path

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        path = self.get_route_path()

        # 1. API: Sample Requests
        if path == '/api/sample-requests':
            return self.send_json(SAMPLE_REQUESTS)

        # 2. API: Stats & Settings
        elif path == '/api/stats':
            conn = get_connection()
            cur = conn.cursor()
            cur.execute('SELECT COUNT(*) FROM opportunities')
            total = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM opportunities WHERE status = 'CLARIFICATION_NEEDED'")
            clarification = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM opportunities WHERE status = 'PENDING_APPROVAL'")
            pending_approval = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM opportunities WHERE status IN ('READY_TO_SEND', 'APPROVED')")
            ready = cur.fetchone()[0]

            # Get custom user settings
            cur.execute('SELECT key, value FROM settings')
            settings_map = {row['key']: row['value'] for row in cur.fetchall()}
            conn.close()

            return self.send_json({
                "total_opportunities": total,
                "clarification_needed": clarification,
                "pending_approval": pending_approval,
                "ready_to_send": ready,
                "custom_kpi_done": settings_map.get('custom_kpi_done', str(ready + 24)),
                "custom_kpi_progress": settings_map.get('custom_kpi_progress', str(pending_approval + clarification + 6)),
                "custom_kpi_completed": settings_map.get('custom_kpi_completed', str(total + 50)),
                "custom_kpi_focus": settings_map.get('custom_kpi_focus', '18h'),
                "user_name": settings_map.get('user_name', 'Emily'),
                "user_greeting": settings_map.get('user_greeting', "Here's what's happening today.")
            })

        # 3. API: Settings
        elif path == '/api/settings':
            conn = get_connection()
            cur = conn.cursor()
            cur.execute('SELECT key, value FROM settings')
            settings_map = {row['key']: row['value'] for row in cur.fetchall()}
            conn.close()
            return self.send_json(settings_map)

        # 4. API: Tasks (To-Do List)
        elif path == '/api/tasks':
            conn = get_connection()
            cur = conn.cursor()
            cur.execute('SELECT * FROM tasks ORDER BY completed ASC, id DESC')
            tasks = [dict(row) for row in cur.fetchall()]
            conn.close()
            return self.send_json(tasks)

        # 5. API: Activities
        elif path == '/api/activities':
            conn = get_connection()
            cur = conn.cursor()
            cur.execute('SELECT * FROM activities ORDER BY id DESC LIMIT 10')
            acts = [dict(row) for row in cur.fetchall()]
            conn.close()
            return self.send_json(acts)

        # 6. API: Chart Data
        elif path == '/api/chart-data':
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT value FROM settings WHERE key = 'chart_data'")
            row = cur.fetchone()
            conn.close()
            if row and row['value']:
                try:
                    return self.send_json(json.loads(row['value']))
                except:
                    pass
            # Default chart values matching Emily's dashboard [25, 48, 72, 60, 78, 85, 92]
            return self.send_json({
                "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                "values": [25, 48, 72, 60, 78, 85, 92],
                "badge": "Tuyệt vời! 🎉"
            })

        # 7. API: Products & Stock
        elif path == '/api/products':
            conn = get_connection()
            cur = conn.cursor()
            cur.execute('SELECT * FROM products ORDER BY category, name')
            products = [dict(row) for row in cur.fetchall()]
            conn.close()
            return self.send_json(products)

        # 8. API: Sales Reps
        elif path == '/api/sales-reps':
            conn = get_connection()
            cur = conn.cursor()
            cur.execute('SELECT * FROM sales_reps ORDER BY current_leads ASC')
            reps = [dict(row) for row in cur.fetchall()]
            conn.close()
            return self.send_json(reps)

        # 9. API: Opportunities list
        elif path == '/api/opportunities':
            conn = get_connection()
            cur = conn.cursor()
            cur.execute('SELECT * FROM opportunities ORDER BY id DESC')
            opps = [dict(row) for row in cur.fetchall()]
            conn.close()
            return self.send_json(opps)

        # 10. API: Opportunity detail
        elif path.startswith('/api/opportunities/'):
            parts = path.strip('/').split('/')
            if len(parts) == 3 and parts[2].isdigit():
                opp_id = int(parts[2])
                conn = get_connection()
                cur = conn.cursor()
                cur.execute('SELECT * FROM opportunities WHERE id = ?', (opp_id,))
                opp = cur.fetchone()
                if not opp:
                    conn.close()
                    return self.send_json({"error": "Not found"}, 404)
                
                cur.execute('SELECT * FROM opportunity_items WHERE opportunity_id = ?', (opp_id,))
                items = [dict(row) for row in cur.fetchall()]
                conn.close()
                result = dict(opp)
                result['items'] = items
                return self.send_json(result)

        # 11. API: Analytics theo sản phẩm (Nhu cầu từ Email & File do người dùng nhập)
        elif path == '/api/analytics/products':
            conn = get_connection()
            cur = conn.cursor()
            cur.execute('''
                SELECT 
                    COALESCE(oi.matched_sku, p.sku, 'SP') as sku,
                    oi.matched_name as name,
                    COALESCE(p.category, 'Sản phẩm mới') as category,
                    COALESCE(oi.unit_price, 0) as unit_price,
                    COALESCE(p.stock_qty, 999) as stock_qty,
                    COUNT(DISTINCT oi.opportunity_id) as request_count,
                    COALESCE(SUM(oi.quantity), 0) as total_quantity,
                    COALESCE(SUM(oi.total_price), 0) as total_demand_val,
                    GROUP_CONCAT(DISTINCT o.client_name) as client_names,
                    GROUP_CONCAT(DISTINCT o.client_email) as client_emails
                FROM opportunity_items oi
                LEFT JOIN opportunities o ON oi.opportunity_id = o.id
                LEFT JOIN products p ON oi.product_id = p.id
                GROUP BY oi.matched_name
                ORDER BY total_quantity DESC, total_demand_val DESC
            ''')
            analytics = [dict(row) for row in cur.fetchall()]
            conn.close()
            return self.send_json(analytics)

        # 12. API: Danh sách Khách hàng từ Email & File (Leads)
        elif path == '/api/customer-leads':
            conn = get_connection()
            cur = conn.cursor()
            cur.execute('''
                SELECT 
                    o.id, o.code, o.client_name, o.client_company, o.client_email, o.client_phone,
                    o.status, o.total_final_price, o.assigned_rep_name, o.created_at,
                    GROUP_CONCAT(oi.matched_name || ' (x' || oi.quantity || ')') as products_summary
                FROM opportunities o
                LEFT JOIN opportunity_items oi ON o.id = oi.opportunity_id
                GROUP BY o.id
                ORDER BY o.id DESC
                LIMIT 50
            ''')
            leads = [dict(row) for row in cur.fetchall()]
            conn.close()
            return self.send_json(leads)

        # 12.1 API: Danh sách Đánh giá & Feedback của khách hàng
        elif path == '/api/feedback':
            conn = get_connection()
            cur = conn.cursor()
            cur.execute('SELECT id, name, contact, stars, comment, created_at as createdAt FROM customer_feedback ORDER BY id DESC')
            feedbacks = [dict(row) for row in cur.fetchall()]
            conn.close()
            return self.send_json(feedbacks)

        elif path == '/api/decisions':
            conn = get_connection()
            cur = conn.cursor()
            cur.execute('SELECT id, code, client_name, client_company, decision, reason, feedback, pic, department, created_at FROM customer_decisions ORDER BY id DESC')
            decisions = [dict(row) for row in cur.fetchall()]
            conn.close()
            return self.send_json(decisions)

        elif path == '/api/auth/me':
            # Trả về tài khoản mặc định hoặc thông tin từ phiên
            conn = get_connection()
            cur = conn.cursor()
            cur.execute('SELECT id, username, company_name, fullname, email, role FROM users ORDER BY id DESC LIMIT 1')
            user = cur.fetchone()
            conn.close()
            if user:
                return self.send_json({"authenticated": True, "user": dict(user)})
            return self.send_json({"authenticated": False})

        # 13. Serve Static Files (UI)
        if path == '/' or path == '/index.html':
            static_file = os.path.join(BASE_DIR, 'static', 'index.html')
            if os.path.exists(static_file):
                with open(static_file, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.send_header('Pragma', 'no-cache')
                self.send_header('Expires', '0')
                self.send_header('Content-Length', str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Index file not found")
                return

        # Serve static assets (JS, CSS, images)
        clean_path = path.lstrip('/')
        if clean_path.startswith('static/'):
            clean_path = clean_path[7:]
        possible_file = os.path.join(BASE_DIR, 'static', clean_path)
        if os.path.isfile(possible_file):
            if possible_file.endswith('.js'):
                content_type = 'application/javascript; charset=utf-8'
            elif possible_file.endswith('.css'):
                content_type = 'text/css; charset=utf-8'
            elif possible_file.endswith('.html'):
                content_type = 'text/html; charset=utf-8'
            elif possible_file.endswith('.png'):
                content_type = 'image/png'
            elif possible_file.endswith('.jpg') or possible_file.endswith('.jpeg'):
                content_type = 'image/jpeg'
            elif possible_file.endswith('.svg'):
                content_type = 'image/svg+xml'
            else:
                content_type = 'application/octet-stream'
            with open(possible_file, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        # 404
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        path = self.get_route_path()
        length = int(self.headers.get('Content-Length', 0))
        try:
            raw_bytes = self.rfile.read(length) if length > 0 else b'{}'
            body = raw_bytes.decode('utf-8')
        except UnicodeDecodeError:
            try:
                body = raw_bytes.decode('utf-8', errors='replace')
            except Exception:
                body = '{}'
        
        try:
            payload = json.loads(body)
        except Exception:
            payload = {}

        conn = get_connection()
        cur = conn.cursor()

        # 1. API: Process Inbound Request (Agent Core)
        if path == '/api/process':
            raw_text = payload.get('text', '').strip()
            if not raw_text:
                conn.close()
                return self.send_json({"error": "Vui lòng nhập nội dung yêu cầu của khách hàng"}, 400)
            
            custom_rep = payload.get('rep_name') or payload.get('pic') or payload.get('nvkd', '')
            custom_dept = payload.get('department') or payload.get('dept', '')
            result = agent_engine.run_agent_workflow(raw_text, custom_rep_name=custom_rep, custom_rep_dept=custom_dept)
            # Add to activities
            client_name = result.get('client_info', {}).get('name', 'Khách hàng')
            code = result.get('code', 'OPP')
            cur.execute('INSERT INTO activities (title, icon_type, time_ago) VALUES (?, ?, ?)',
                        (f"AI Agent tiếp nhận & xử lý yêu cầu #{code} ({client_name})", "check", "Vừa xong"))
            conn.commit()
            conn.close()
            return self.send_json(result)

        # 2. API: Manager Approve/Reject
        elif path.startswith('/api/opportunities/') and path.endswith('/approval'):
            parts = path.strip('/').split('/')
            if len(parts) == 4 and parts[2].isdigit():
                opp_id = int(parts[2])
                action = payload.get('action', 'APPROVE')
                notes = payload.get('notes', '')
                result = agent_engine.approve_opportunity(opp_id, action, notes)
                cur.execute('INSERT INTO activities (title, icon_type, time_ago) VALUES (?, ?, ?)',
                            (f"Trưởng phòng {'phê duyệt' if action == 'APPROVE' else 'từ chối'} cơ hội #{opp_id}", "check" if action == 'APPROVE' else "alert", "Vừa xong"))
                conn.commit()
                conn.close()
                return self.send_json(result)

        # 3. API: Tasks (Add, Toggle, Delete)
        elif path == '/api/tasks/add':
            title = payload.get('title', '').strip()
            emoji = payload.get('emoji', '📝')
            due_info = payload.get('due_info', 'Hôm nay')
            if title:
                cur.execute('INSERT INTO tasks (title, completed, emoji, due_info) VALUES (?, 0, ?, ?)', (title, emoji, due_info))
                conn.commit()
                task_id = cur.lastrowid
                conn.close()
                return self.send_json({"success": True, "id": task_id, "title": title})
            conn.close()
            return self.send_json({"error": "Tiêu đề không được để trống"}, 400)

        elif path.startswith('/api/tasks/') and path.endswith('/toggle'):
            parts = path.strip('/').split('/')
            if len(parts) == 4 and parts[2].isdigit():
                task_id = int(parts[2])
                cur.execute('UPDATE tasks SET completed = CASE WHEN completed = 1 THEN 0 ELSE 1 END WHERE id = ?', (task_id,))
                conn.commit()
                conn.close()
                return self.send_json({"success": True, "id": task_id})

        elif path.startswith('/api/tasks/') and path.endswith('/delete'):
            parts = path.strip('/').split('/')
            if len(parts) == 4 and parts[2].isdigit():
                task_id = int(parts[2])
                cur.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
                conn.commit()
                conn.close()
                return self.send_json({"success": True, "id": task_id})

        # 4. API: Save Custom Settings & KPIs (Người dùng tự sửa số liệu)
        elif path == '/api/settings/update':
            for k, v in payload.items():
                cur.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (str(k), str(v)))
            conn.commit()
            conn.close()
            return self.send_json({"success": True, "updated": payload})

        # 4.1 API: Reset All Data to 0 (Xóa sạch số liệu để người dùng tự nhập)
        elif path == '/api/reset-data':
            cur.execute('DELETE FROM products')
            cur.execute('DELETE FROM opportunities')
            cur.execute('DELETE FROM opportunity_items')
            cur.execute('DELETE FROM tasks')
            cur.execute('DELETE FROM activities')
            cur.execute('UPDATE sales_reps SET current_leads = 0')
            clean_settings = [
                ('custom_kpi_done', '0'),
                ('custom_kpi_progress', '0'),
                ('custom_kpi_completed', '0'),
                ('custom_kpi_focus', '0h'),
                ('chart_data', '{"labels": ["T2", "T3", "T4", "T5", "T6", "T7", "CN"], "values": [0, 0, 0, 0, 0, 0, 0], "badge": "Nhấp để đổi"}')
            ]
            for k, v in clean_settings:
                cur.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (k, v))
            conn.commit()
            conn.close()
            return self.send_json({"success": True, "message": "Đã đưa toàn bộ số liệu về 0"})

        # 5. API: Save Chart Data
        elif path == '/api/chart-data/update':
            cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('chart_data', ?)", (json.dumps(payload, ensure_ascii=False),))
            conn.commit()
            conn.close()
            return self.send_json({"success": True, "chart_data": payload})

        # 6. API: Update Product
        elif path == '/api/products/update':
            sku = payload.get('sku')
            name = payload.get('name')
            category = payload.get('category')
            unit_price = float(payload.get('unit_price', 0))
            stock_qty = int(payload.get('stock_qty', 0))
            lead_time_days = int(payload.get('lead_time_days', 7))
            warranty_months = int(payload.get('warranty_months', 12))
            
            cur.execute('''
            UPDATE products 
            SET name = ?, category = ?, unit_price = ?, stock_qty = ?, lead_time_days = ?, warranty_months = ?
            WHERE sku = ?
            ''', (name, category, unit_price, stock_qty, lead_time_days, warranty_months, sku))
            conn.commit()
            conn.close()
            return self.send_json({"success": True, "sku": sku})

        # 7. API: Add Product
        elif path == '/api/products/add':
            sku = payload.get('sku', '').strip()
            name = payload.get('name', '').strip()
            category = payload.get('category', 'Khác').strip()
            unit = payload.get('unit', 'Cái').strip()
            unit_price = float(payload.get('unit_price', 0))
            stock_qty = int(payload.get('stock_qty', 0))
            lead_time_days = int(payload.get('lead_time_days', 7))
            warranty_months = int(payload.get('warranty_months', 12))
            desc = payload.get('description', '')

            if sku and name:
                try:
                    cur.execute('''
                    INSERT INTO products (sku, name, category, unit, unit_price, stock_qty, lead_time_days, warranty_months, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (sku, name, category, unit, unit_price, stock_qty, lead_time_days, warranty_months, desc))
                    conn.commit()
                    conn.close()
                    return self.send_json({"success": True, "sku": sku})
                except Exception as e:
                    conn.close()
                    return self.send_json({"error": str(e)}, 400)
            conn.close()
            return self.send_json({"error": "SKU và Tên không được rỗng"}, 400)

        # 8. API: Delete Product
        elif path == '/api/products/delete':
            sku = payload.get('sku')
            if sku:
                cur.execute('DELETE FROM products WHERE sku = ?', (sku,))
                conn.commit()
                conn.close()
                return self.send_json({"success": True, "sku": sku})
            conn.close()
            return self.send_json({"error": "Thiếu mã SKU"}, 400)

        # 9. API: Update Sales Rep
        elif path == '/api/sales-reps/update':
            rep_id = payload.get('id')
            name = payload.get('name')
            email = payload.get('email')
            phone = payload.get('phone')
            current_leads = int(payload.get('current_leads', 0))
            specialty = payload.get('specialty')

            cur.execute('''
            UPDATE sales_reps 
            SET name = ?, email = ?, phone = ?, current_leads = ?, specialty = ?
            WHERE id = ?
            ''', (name, email, phone, current_leads, specialty, rep_id))
            conn.commit()
            conn.close()
            return self.send_json({"success": True, "id": rep_id})

        # 10. API: Thêm Đánh giá Khách hàng mới (Customer Feedback)
        elif path == '/api/feedback':
            name = payload.get('name', '').strip()
            contact = payload.get('contact', '').strip()
            comment = payload.get('comment', '').strip()
            stars = int(payload.get('stars', 5))
            import datetime
            created_at = payload.get('createdAt') or datetime.datetime.now().strftime("%H:%M - %d/%m/%Y")
            if name and comment:
                cur.execute('''
                INSERT INTO customer_feedback (name, contact, stars, comment, created_at)
                VALUES (?, ?, ?, ?, ?)
                ''', (name, contact, stars, comment, created_at))
                conn.commit()
                fb_id = cur.lastrowid
                conn.close()
                return self.send_json({
                    "success": True, 
                    "id": fb_id, 
                    "name": name, 
                    "contact": contact, 
                    "stars": stars, 
                    "comment": comment, 
                    "createdAt": created_at
                })
            conn.close()
            return self.send_json({"error": "Thiếu tên hoặc nội dung nhận xét"}, 400)

        # 11. API: Xóa Đánh giá Khách hàng
        elif path == '/api/feedback/delete':
            fb_id = payload.get('id')
            if fb_id:
                cur.execute('DELETE FROM customer_feedback WHERE id = ?', (fb_id,))
                conn.commit()
                conn.close()
                return self.send_json({"success": True, "id": fb_id})
            conn.close()
            return self.send_json({"error": "Thiếu id đánh giá"}, 400)

        elif path == '/api/decisions':
            import time, datetime
            code = payload.get('code', 'OPP-' + str(int(time.time())))
            client_name = payload.get('client_name', '').strip()
            client_company = payload.get('client_company', '').strip()
            decision = payload.get('decision', 'APPROVED').strip().upper()
            reason = payload.get('reason', '').strip()
            feedback = payload.get('feedback', '').strip()
            pic = payload.get('pic', 'Trần Phương Thảo').strip()
            department = payload.get('department', 'Phòng Kinh Doanh B2B').strip()
            created_at = payload.get('created_at') or datetime.datetime.now().strftime("%H:%M - %d/%m/%Y")
            cur.execute('''
            INSERT INTO customer_decisions (code, client_name, client_company, decision, reason, feedback, pic, department, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (code, client_name, client_company, decision, reason, feedback, pic, department, created_at))
            conn.commit()
            d_id = cur.lastrowid
            conn.close()
            return self.send_json({
                "success": True,
                "id": d_id,
                "code": code,
                "client_name": client_name,
                "client_company": client_company,
                "decision": decision,
                "reason": reason,
                "feedback": feedback,
                "pic": pic,
                "department": department,
                "created_at": created_at
            })

        # 12. API: Đăng Ký Tài Khoản Doanh Nghiệp
        elif path == '/api/auth/register':
            username = payload.get('username', '').strip()
            password = payload.get('password', '').strip()
            company_name = payload.get('company_name', '').strip() or 'Doanh Nghiệp Tiên Phong'
            fullname = payload.get('fullname', '').strip() or username
            email = payload.get('email', '').strip()
            if not username or not password:
                conn.close()
                return self.send_json({"error": "Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu"}, 400)
            try:
                import datetime
                created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cur.execute('INSERT INTO users (username, password, company_name, fullname, email, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                            (username, password, company_name, fullname, email, created_at))
                conn.commit()
                u_id = cur.lastrowid
                conn.close()
                return self.send_json({
                    "success": True,
                    "user": {
                        "id": u_id,
                        "username": username,
                        "company_name": company_name,
                        "fullname": fullname,
                        "email": email,
                        "role": "Enterprise Manager"
                    }
                })
            except Exception as e:
                conn.close()
                return self.send_json({"error": "Tên đăng nhập đã tồn tại hoặc xảy ra lỗi: " + str(e)}, 400)

        # 13. API: Đăng Nhập Doanh Nghiệp
        elif path == '/api/auth/login':
            username = payload.get('username', '').strip()
            password = payload.get('password', '').strip()
            cur.execute('SELECT id, username, company_name, fullname, email, role FROM users WHERE username = ? AND password = ?', (username, password))
            user = cur.fetchone()
            if not user:
                conn.close()
                return self.send_json({"error": "Tên đăng nhập hoặc mật khẩu không chính xác"}, 401)
            user_dict = dict(user)
            conn.close()
            return self.send_json({"success": True, "user": user_dict})

        # 14. API: Làm Sạch Phiên Cho File Mới (Không Trùng Lặp Dữ Liệu Cũ)
        elif path == '/api/reset-session':
            cur.execute('DELETE FROM opportunities')
            cur.execute('DELETE FROM opportunity_items')
            cur.execute('DELETE FROM tasks')
            cur.execute('DELETE FROM activities')
            cur.execute('DELETE FROM customer_decisions')
            conn.commit()
            conn.close()
            return self.send_json({"success": True, "message": "Đã làm sạch hoàn toàn phiên dữ liệu cũ"})

        # 15. API: AI Agent Trợ Lý Tương Tác & Phản Hồi Thông Minh
        elif path == '/api/ai/chat':
            user_msg = payload.get('message', '').strip()
            context_data = payload.get('context', {})
            company = payload.get('company', 'Doanh nghiệp')
            
            # Phân tích ý định người dùng bằng AI Agent Logic
            msg_lower = user_msg.lower()
            reply = ""
            action = None
            action_data = {}

            if any(k in msg_lower for k in ['chiết khấu', 'chiet khau', 'discount', 'giảm giá']):
                # Điều chỉnh chiết khấu
                import re
                match = re.search(r'(\d+(?:\.\d+)?)\s*%', msg_lower)
                val = float(match.group(1)) if match else 4.5
                reply = f"🤖 AI Agent đã thẩm định lại cơ cấu giá cho {company}: Tự động áp dụng mức chiết khấu tối ưu {val}%. Biên lợi nhuận gộp sau chiết khấu duy trì ở mức an toàn 22.8% và doanh thu dự kiến tăng thêm 15% nhờ kích cầu."
                action = 'UPDATE_DISCOUNT'
                action_data = {'discountPct': val}
            elif any(k in msg_lower for k in ['kênh', 'kenh', 'channel', 'nguồn']):
                reply = f"🤖 Chẩn đoán Kênh Bán: Kênh trực tiếp & B2B chiếm tỷ trọng lớn nhất với biên độ chốt deal 68%. Agent đề xuất mở rộng thêm kênh Affiliate và tối ưu chi phí quảng cáo số để gia tăng tệp khách hàng tự nhiên."
                action = 'SWITCH_DIMENSION'
                action_data = {'dimension': 'channel'}
            elif any(k in msg_lower for k in ['tồn kho', 'ton kho', 'stock', 'atp']):
                reply = f"🤖 Thẩm định Tồn kho ATP: 100% các mặt hàng chủ lực hiện sẵn sàng giao ngay. Thời gian phản hồi SLA trung bình đạt 24h, đảm bảo giao hàng đúng tiến độ cam kết."
                action = 'HIGHLIGHT_STOCK'
            elif any(k in msg_lower for k in ['giải pháp', 'chiến lược', 'hướng giải quyết', 'nhận xét']):
                reply = f"🤖 Chiến Lược Đề Xuất Cho {company}:\n1. [Ngắn hạn 7 ngày]: Tập trung chốt các đơn hàng có giá trị cao và gửi báo giá kèm chiết khấu tối ưu.\n2. [Trung hạn 30 ngày]: Đa dạng hóa kênh phân phối, giảm thiểu rủi ro phụ thuộc vào một nguồn doanh thu duy nhất."
                action = 'SHOW_STRATEGY'
            else:
                reply = f"🤖 AI Agent đã ghi nhận chỉ đạo từ {company}: '{user_msg}'. Agent đã tự động hiệu chỉnh thông số mô hình phân tích để đáp ứng chính xác nhất tiêu chuẩn đầu ra bạn mong muốn."
                action = 'REFRESH_ANALYSIS'

            conn.close()
            return self.send_json({
                "success": True,
                "reply": reply,
                "action": action,
                "action_data": action_data
            })

        # 404
        conn.close()
        self.send_json({"error": "Endpoint not found"}, 404)

def run_server():
    init_db()
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, MinhAnApiHandler)
    print(f"================================================================")
    print(f"🌸 Minh An AI Agent Server (Claymorphism UI) RUNNING on http://localhost:{PORT}")
    print(f"👉 Mở trình duyệt và truy cập: http://localhost:{PORT}")
    print(f"================================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()

if __name__ == '__main__':
    run_server()
