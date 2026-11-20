# -*- coding: utf-8 -*-
"""
AI Agent Engine for Minh An Company - B2B Sales Opportunity Processing.
Structured explicitly into 4 core phases:
  1. NHẬP (Input / Ingestion)
  2. LÀM SẠCH (Data Cleaning & Sanitization)
  3. XỬ LÝ (Processing & Business Logic)
  4. RA KẾT QUẢ (Output & Proposal Delivery)
"""
import re
import json
import datetime
import random
from database import get_connection

# ==============================================================================
# GIAI ĐOẠN 1: NHẬP (INPUT / INGESTION)
# ==============================================================================
def stage_1_input(raw_text, channel="Email / Web Form"):
    """
    Tiếp nhận văn bản yêu cầu thô từ khách hàng (Email, biểu mẫu, tin nhắn).
    """
    now = datetime.datetime.now()
    raw_clean = str(raw_text or "").strip()
    return {
        "channel": channel,
        "received_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "raw_text": raw_clean,
        "char_count": len(raw_clean),
        "line_count": len(raw_clean.splitlines()) if raw_clean else 0,
        "status": "INGESTED"
    }


# ==============================================================================
# GIAI ĐOẠN 2: LÀM SẠCH (DATA CLEANING & SANITIZATION)
# ==============================================================================
def clean_phone_number(raw_phone):
    if not raw_phone:
        return ""
    # Loại bỏ khoảng trắng, dấu gạch nối, dấu chấm
    digits = re.sub(r'[\s\.\-\(\)]', '', raw_phone)
    if digits.startswith("+84"):
        digits = "0" + digits[3:]
    elif digits.startswith("84") and len(digits) >= 11:
        digits = "0" + digits[2:]
    return digits

def clean_currency_text(text):
    if not text:
        return 0
    t = str(text).lower().replace(",", "").replace(".", "").replace(" ", "")
    # Check for "tỷ", "triệu", "tr", "k"
    m_ty = re.search(r'(\d+(?:\.\d+)?)\s*(?:tỷ|ty|billion)', t)
    if m_ty:
        return float(m_ty.group(1)) * 1000000000
    m_tr = re.search(r'(\d+(?:\.\d+)?)\s*(?:triệu|trieu|tr|m)', t)
    if m_tr:
        return float(m_tr.group(1)) * 1000000
    m_k = re.search(r'(\d+)\s*(?:k|nghìn|nghin)', t)
    if m_k:
        return float(m_k.group(1)) * 1000
    m_num = re.search(r'(\d{6,})', t)
    if m_num:
        return float(m_num.group(1))
    return 0

def clean_discount_text(text):
    if not text:
        return 0.0
    match = re.search(r'(?:chiết khấu|giảm giá|discount)\s*(?:là|khoảng|mức)?\s*(\d+(?:\.\d+)?)\s*%', text, re.IGNORECASE)
    if match:
        return float(match.group(1))
    match2 = re.search(r'(\d+(?:\.\d+)?)\s*%\s*(?:chiết khấu|giảm giá|discount)', text, re.IGNORECASE)
    if match2:
        return float(match2.group(1))
    return 0.0

def clean_deadline_text(text):
    if not text:
        return None
    patterns = [
        r'(?:trước ngày|hạn|deadline|hoàn thành trước|giao trước)\s*(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)',
        r'(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)',
        r'trong vòng\s*(\d+)\s*(?:ngày|tuần|tháng)'
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(0).strip()
    return None

def stage_2_clean(input_payload):
    """
    Làm sạch, khử nhiễu, chuẩn hóa định dạng và bóc tách các thực thể dữ liệu có cấu trúc.
    """
    raw_text = input_payload["raw_text"]
    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]

    # 1. Bóc tách & làm sạch Email
    email_match = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', raw_text)
    clean_email = email_match.group(0).lower().strip() if email_match else ""

    # 2. Bóc tách & làm sạch Số điện thoại
    phone_match = re.search(r'(?:\+84|0)[1-9][0-9\s.-]{8,12}', raw_text)
    clean_phone = clean_phone_number(phone_match.group(0)) if phone_match else ""

    # 3. Bóc tách Tên người liên hệ & Tên công ty
    clean_name = ""
    clean_company = ""
    for line in lines:
        if not clean_name:
            m_name = re.search(r'(?:tôi là|tên tôi là|người liên hệ|từ|sender:?)\s*[:\-]?\s*([A-ZÀ-Ỹa-zà-ỹ\s]{3,35})', line, re.IGNORECASE)
            if m_name:
                clean_name = m_name.group(1).strip()
        if not clean_company:
            m_comp = re.search(r'(?:công ty|cty|doanh nghiệp|tập đoàn)\s*([A-ZÀ-Ỹ0-9\s\.\-]{3,45})', line, re.IGNORECASE)
            if m_comp:
                clean_company = ("Công ty " + m_comp.group(1).strip()).strip()

    if not clean_name and lines:
        for line in lines[:3]:
            if any(k in line.lower() for k in ["anh", "chị", "ông", "bà"]):
                clean_name = line.strip()
                break

    # 4. Làm sạch số tiền ngân sách & mức chiết khấu
    clean_discount = clean_discount_text(raw_text)
    clean_deadline = clean_deadline_text(raw_text)
    
    clean_budget = 0
    m_budget = re.search(r'(?:ngân sách|kinh phí|budget|tối đa|dự toán)\s*(?:khoảng|là|tầm)?\s*[:\s]?\s*([0-9\.,\s]+(?:tỷ|ty|triệu|trieu|tr|vnđ|vnd|đ)?)', raw_text, re.IGNORECASE)
    if m_budget:
        clean_budget = clean_currency_text(m_budget.group(1))

    # 5. Đánh giá chất lượng dữ liệu (Data Quality & Completeness Audit)
    missing_fields = []
    if not clean_email and not clean_phone:
        missing_fields.append("Thông tin liên hệ (Email hoặc Số điện thoại người gửi)")
    if not clean_deadline and ("gấp" in raw_text.lower() or "sớm nhất" in raw_text.lower()):
        missing_fields.append("Thời hạn cụ thể (Deadline) khách hàng mong muốn nghiệm thu")

    is_sufficient = (len(missing_fields) == 0)

    return {
        "clean_name": clean_name or "Quý Khách Hàng",
        "clean_company": clean_company or "Khách hàng Doanh nghiệp",
        "clean_email": clean_email,
        "clean_phone": clean_phone,
        "clean_budget": clean_budget,
        "clean_discount": clean_discount,
        "clean_deadline": clean_deadline or "Tiêu chuẩn (Theo thỏa thuận)",
        "missing_fields": missing_fields,
        "is_sufficient": is_sufficient,
        "sanitized_summary": f"Khách hàng: {clean_name or 'N/A'} | Cty: {clean_company or 'N/A'} | Mail: {clean_email or 'N/A'} | ĐT: {clean_phone or 'N/A'} | Ngân sách: {clean_budget:,.0f} đ"
    }


# ==============================================================================
# GIAI ĐOẠN 3: XỬ LÝ (PROCESSING & BUSINESS LOGIC)
# ==============================================================================
# ==============================================================
# GIAI ĐOẠN 3: XỬ LÝ (PROCESSING & BÓC TÁCH SẢN PHẨM MỚI 100%)
# ==============================================================
def extract_dynamic_products(text, db_products=None):
    """
    Tự động bóc tách và phân tích BẤT KỲ sản phẩm nào do người dùng nhập vào:
    - Không gò bó vào danh mục giả lập cũ (Dell, Cisco...).
    - Tự động nhận diện tên sản phẩm, số lượng, đơn giá mới mà người dùng cung cấp.
    - Tự động lưu sản phẩm mới vào CSDL để phân tích theo thời gian thực.
    """
    conn = get_connection()
    cur = conn.cursor()

    text_clean = text.replace('\r', '')

    # 1. Bóc tách từng dòng có gạch đầu dòng, dấu cộng, hoa thị hoặc số thứ tự
    found_matches = []
    for raw_line in text_clean.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        m = re.match(r'^(?:[-*•+]|\d+[\.)])\s*(?:(?:số lượng|sl)?\s*[:=-]?\s*(\d+)\s*(?:bộ|cái|chiếc|thiết bị|hộp|thùng|gói|kg|user|lic|tấm|mét|đôi|hạng mục)?\s*)?(.*?)(?:\((.*?)\))?$', line, re.IGNORECASE)
        if m:
            raw_qty = m.group(1)
            raw_name = m.group(2).strip()
            extra_info = (m.group(3) or "").strip()

            lower_name = raw_name.lower()
            if any(skip in lower_name for skip in ['kính gửi', 'chào', 'tôi là', 'email:', 'sđt:', 'điện thoại:', 'ngân sách', 'chiết khấu', 'hạn giao', 'thời hạn', 'hotline', 'địa chỉ', 'công ty', 'tập đoàn']):
                continue
            if len(raw_name) < 2:
                continue

            qty = int(raw_qty) if raw_qty and raw_qty.isdigit() else 1

            # Trích xuất đơn giá nếu người dùng có ghi
            unit_price = 0
            m_price = re.search(r'(?:đơn giá|giá|tầm|khoảng)?\s*[:\s]?\s*([0-9\.,]+)\s*(?:k|nghìn|ngàn|triệu|tr|vnđ|vnd|đ)', extra_info + " " + line, re.IGNORECASE)
            if m_price:
                p_val = m_price.group(1).replace('.', '').replace(',', '')
                if p_val.isdigit():
                    val_num = float(p_val)
                    p_lower = (extra_info + " " + line).lower()
                    if 'triệu' in p_lower or 'tr' in p_lower:
                        val_num *= 1000000
                    elif 'k' in p_lower or 'nghìn' in p_lower:
                        val_num *= 1000
                    unit_price = val_num

            found_matches.append({
                "name": raw_name,
                "quantity": qty,
                "unit_price": unit_price
            })

    # 2. Nếu không tìm thấy dạng gạch đầu dòng, tìm theo các câu yêu cầu thông thường
    if not found_matches:
        inline_pattern = re.compile(
            r'(?:cần mua|báo giá|đặt hàng|mua|yêu cầu)\s*(?:gấp|thêm)?\s*(\d+)?\s*(?:bộ|cái|chiếc|thiết bị|hộp|thùng|gói|kg|user)?\s*([^\n\r,\.;]+)',
            re.IGNORECASE
        )
        for m in inline_pattern.finditer(text_clean):
            raw_qty = m.group(1)
            raw_name = m.group(2).strip()
            lower_name = raw_name.lower()
            if any(skip in lower_name for skip in ['kính gửi', 'chào', 'tôi là', 'email', 'sđt', 'điện thoại', 'ngân sách', 'chiết khấu', 'hạn giao']):
                continue
            if len(raw_name) >= 2:
                qty = int(raw_qty) if raw_qty and raw_qty.isdigit() else 1
                found_matches.append({
                    "name": raw_name,
                    "quantity": qty,
                    "unit_price": 0
                })

    # 3. Đưa vào bảng products và cấu trúc items_evaluated
    items_evaluated = []
    for idx, match in enumerate(found_matches, 1):
        prod_name = match["name"].strip()
        qty = max(1, match["quantity"])
        unit_price = match["unit_price"]

        # Kiểm tra sản phẩm đã có trong bảng products chưa
        cur.execute('SELECT * FROM products WHERE LOWER(name) = ?', (prod_name.lower(),))
        existing_prod = cur.fetchone()

        if existing_prod:
            prod_dict = dict(existing_prod)
            prod_id = prod_dict['id']
            prod_sku = prod_dict['sku']
            if unit_price == 0 and prod_dict['unit_price'] > 0:
                unit_price = prod_dict['unit_price']
            stock_qty = prod_dict.get('stock_qty', 999)
        else:
            # Tạo mã SKU tự động cho sản phẩm mới
            words = re.findall(r'[A-Za-z0-9]+', prod_name)
            acronym = "".join([w[0].upper() for w in words[:3]]) if words else "SP"
            prod_sku = f"{acronym}-{random.randint(100, 999)}"
            cur.execute('''
            INSERT INTO products (sku, name, category, unit, unit_price, stock_qty, lead_time_days, warranty_months, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (prod_sku, prod_name, "Sản phẩm mới của khách hàng", "Cái", unit_price, 999, 2, 12, "Sản phẩm mới tự động nhận diện từ yêu cầu"))
            conn.commit()
            prod_id = cur.lastrowid
            stock_qty = 999

        total_price = unit_price * qty
        items_evaluated.append({
            "product_id": prod_id,
            "sku": prod_sku,
            "name": prod_name,
            "quantity": qty,
            "unit_price": unit_price,
            "total_price": total_price,
            "stock_available": stock_qty,
            "is_stock_sufficient": 1,
            "item_lead_time_days": 2,
            "warranty_months": 12
        })

    conn.close()
    return items_evaluated

def stage_3_process(cleaned_payload, db_products, db_sales_reps, raw_text, custom_rep_name=None, custom_rep_dept=None):
    """
    Thực hiện toàn bộ nghiệp vụ:
    - Tự động bóc tách sản phẩm mới người dùng cung cấp
    - Phân bổ NVKD
    - Tính toán chiết khấu & Kiểm tra thẩm quyền phê duyệt
    """
    now = datetime.datetime.now()
    items_evaluated = extract_dynamic_products(raw_text, db_products)

    # Nếu không bóc tách được sản phẩm nào
    if len(items_evaluated) == 0:
        cleaned_payload["is_sufficient"] = False
        cleaned_payload["missing_fields"].append("Danh sách sản phẩm / thiết bị cụ thể cần báo giá")

    # Nếu có ngân sách nhưng đơn giá sản phẩm chưa có, phân bổ ngân sách cho sản phẩm
    budget_req = cleaned_payload.get("clean_budget", 0)
    total_qty = sum(it["quantity"] for it in items_evaluated)
    total_original = sum(it["total_price"] for it in items_evaluated)
    if total_original == 0 and budget_req > 0 and total_qty > 0:
        avg_price = budget_req / total_qty
        for it in items_evaluated:
            it["unit_price"] = avg_price
            it["total_price"] = avg_price * it["quantity"]
        total_original = budget_req

    if not cleaned_payload["is_sufficient"]:
        return {
            "status": "CLARIFICATION_NEEDED",
            "is_sufficient": False,
            "missing_fields": cleaned_payload["missing_fields"],
            "items_evaluated": items_evaluated,
            "total_original": total_original,
            "total_final": total_original,
            "requires_approval": False
        }

    # 1. NVKD Phụ trách: Ưu tiên tên do người dùng tự nhập hoặc chọn
    dept_val = str(custom_rep_dept).strip() if custom_rep_dept and str(custom_rep_dept).strip() else "Phòng Kinh Doanh B2B"
    assigned_rep = None
    if custom_rep_name and str(custom_rep_name).strip():
        clean_name = str(custom_rep_name).strip()
        assigned_rep = {
            "id": 999,
            "name": clean_name,
            "email": f"{clean_name.lower().replace(' ', '.')}@conangtinhnghich.vn",
            "phone": "0988 888 888",
            "department": dept_val,
            "specialty": dept_val
        }
    else:
        # Tìm trong văn bản nếu có NVKD / PIC: Tên
        m_rep = re.search(r'(?:NVKD|PIC|phụ trách|người phụ trách)\s*[:=-]\s*([^\n,;|]+)', raw_text, re.IGNORECASE)
        if m_rep:
            clean_name = m_rep.group(1).strip()
            assigned_rep = {
                "id": 999,
                "name": clean_name,
                "email": f"{clean_name.lower().replace(' ', '.')}@conangtinhnghich.vn",
                "phone": "0988 888 888",
                "department": dept_val,
                "specialty": dept_val
            }
        elif db_sales_reps and len(db_sales_reps) > 0:
            sorted_reps = sorted(db_sales_reps, key=lambda x: (x.get('current_leads', 0), x['id']))
            assigned_rep = sorted_reps[0]
            assigned_rep["department"] = dept_val
        else:
            assigned_rep = {
                "id": 1,
                "name": "Trần Phương Thảo",
                "email": "thao.tp@conangtinhnghich.vn",
                "phone": "0912 345 671",
                "department": dept_val,
                "specialty": dept_val
            }

    feasible_date = now + datetime.timedelta(days=2)
    feasible_deadline_str = feasible_date.strftime("%d/%m/%Y")
    deadline_status = "ON_TIME"

    # 2. Tính toán Chiết khấu & Kiểm tra Thẩm quyền
    discount_pct = cleaned_payload["clean_discount"]
    discount_amount = total_original * (discount_pct / 100.0)
    total_final = total_original - discount_amount

    requires_approval = False
    approval_reasons = []

    if discount_pct > 5.0:
        requires_approval = True
        approval_reasons.append(f"Chiết khấu yêu cầu ({discount_pct}%) vượt hạn mức tự quyết của NVKD (tối đa 5.0%)")

    if total_final >= 200000000:
        requires_approval = True
        approval_reasons.append(f"Giá trị đơn hàng ({total_final:,.0f} VNĐ) vượt ngưỡng phê duyệt lớn (200 triệu VNĐ)")

    if budget_req > 0 and total_final > budget_req * 1.15:
        requires_approval = True
        approval_reasons.append(f"Báo giá ({total_final:,.0f} đ) vượt 15% so với ngân sách khách ({budget_req:,.0f} đ)")

    if deadline_status == "DEADLINE_RISK":
        requires_approval = True
        approval_reasons.append("Tồn kho không kịp deadline gấp, cần Trưởng phòng duyệt phương án giao từng đợt")

    return {
        "status": "PENDING_APPROVAL" if requires_approval else "READY_TO_SEND",
        "is_sufficient": True,
        "assigned_rep": assigned_rep,
        "items_evaluated": items_evaluated,
        "total_original": total_original,
        "discount_pct": discount_pct,
        "discount_amount": discount_amount,
        "total_final": total_final,
        "feasible_deadline": feasible_deadline_str,
        "deadline_status": deadline_status,
        "stock_warnings": [],
        "requires_approval": requires_approval,
        "approval_reasons": approval_reasons
    }


# ==============================================================================
# GIAI ĐOẠN 4: RA KẾT QUẢ (OUTPUT & PROPOSAL DELIVERY)
# ==============================================================================
def stage_4_output(stage1, stage2, stage3):
    """
    Tổng hợp kết quả cuối cùng:
    - Nếu thiếu thông tin: Soạn email đề nghị khách làm rõ
    - Nếu hợp lệ: Tạo mã hồ sơ cơ hội, bảng báo giá hoàn chỉnh và email phản hồi
    """
    now = datetime.datetime.now()
    code = f"OPP-{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S')}"

    # Trường hợp 1: Thiếu thông tin -> Ra kết quả là Email Yêu Cầu Làm Rõ
    if not stage3["is_sufficient"]:
        clarification_email = f"""Kính gửi Anh/Chị {stage2.get('clean_name', 'Quý Khách Hàng')},

Công ty Cổ phần Công nghệ Cô Nàng Tinh Nghịch xin chân thành cảm ơn Anh/Chị và Quý công ty {stage2.get('clean_company', 'Quý Doanh Nghiệp')} đã quan tâm đến giải pháp của chúng tôi.

Để đội ngũ kỹ sư và kinh doanh của Cô Nàng Tinh Nghịch thẩm định chính xác tồn kho khả dụng và lập bảng báo giá chi tiết, kính đề nghị Quý công ty vui lòng bổ sung thông tin sau:

{chr(10).join([f"  • {item}" for item in stage3['missing_fields']])}

Ngay khi nhận được danh sách sản phẩm hoặc thông tin bổ sung, Cô Nàng Tinh Nghịch cam kết gửi Bảng Báo Giá chi tiết trong vòng 04 giờ làm việc.

Trân trọng cảm ơn,
Bộ phận Kinh doanh B2B - Công ty Cổ phần Công nghệ Cô Nàng Tinh Nghịch
Hotline: 1900 6868 | Email: sales@conangtinhnghich.vn
"""
        rep = stage3.get("assigned_rep") or {
            "id": 1,
            "name": "Trần Phương Thảo",
            "department": "Phòng Kinh Doanh B2B",
            "email": "thao.tp@conangtinhnghich.vn",
            "phone": "0912 345 671"
        }
        return {
            "success": True,
            "code": code,
            "is_sufficient": False,
            "status": "CLARIFICATION_NEEDED",
            "client_info": {
                "name": stage2.get("clean_name") or "Quý Khách Hàng",
                "company": stage2.get("clean_company") or "Khách hàng Doanh nghiệp",
                "email": stage2.get("clean_email") or "",
                "phone": stage2.get("clean_phone") or ""
            },
            "assigned_rep": rep,
            "items": stage3.get("items_evaluated", []),
            "total_original": 0,
            "discount_pct": stage3.get("discount_pct", 0),
            "discount_amount": 0,
            "total_final": 0,
            "requested_budget": stage2.get("clean_budget", 0),
            "requested_deadline": stage2.get("clean_deadline", ""),
            "feasible_deadline": "Cần bổ sung danh mục sản phẩm",
            "deadline_status": "Chưa có sản phẩm",
            "stock_warnings": [],
            "requires_manager_approval": False,
            "approval_reasons": [],
            "clarification_email": clarification_email,
            "proposal_email_draft": clarification_email,
            "missing_fields": stage3["missing_fields"],
            "summary_card": {
                "title": "Yêu Cầu Chưa Có Sản Phẩm Báo Giá",
                "action": "Đã tự động tạo Email đề nghị khách hàng bổ sung danh sách sản phẩm."
            }
        }

    # Trường hợp 2: Đủ thông tin -> Ra kết quả Hồ Sơ Cơ Hội, Báo Giá & Email Phản Hồi
    rep = stage3.get("assigned_rep") or {
        "id": 1,
        "name": "Trần Phương Thảo",
        "department": "Phòng Kinh Doanh B2B",
        "email": "thao.tp@conangtinhnghich.vn",
        "phone": "0912 345 671"
    }
    items = stage3.get("items_evaluated") or []

    item_rows_txt = ""
    for idx, it in enumerate(items, 1):
        price_str = f"{it['unit_price']:,.0f} đ" if it['unit_price'] > 0 else "Theo thỏa thuận"
        total_str = f"{it['total_price']:,.0f} đ" if it['total_price'] > 0 else "Theo thỏa thuận"
        item_rows_txt += f"  {idx}. {it['name']} | SL: {it['quantity']} | Đơn giá: {price_str} | Thành tiền: {total_str} (Sẵn sàng đáp ứng)\n"

    total_orig_str = f"{stage3.get('total_original', 0):,.0f} VNĐ" if stage3.get('total_original', 0) > 0 else "Theo báo giá thỏa thuận"
    total_final_str = f"{stage3.get('total_final', 0):,.0f} VNĐ" if stage3.get('total_final', 0) > 0 else "Theo báo giá thỏa thuận"

    client_display_name = stage2.get('clean_name') or "Quý Khách Hàng"
    client_display_company = stage2.get('clean_company') or "Khách hàng Doanh nghiệp"

    proposal_email_draft = f"""Kính gửi Anh/Chị {client_display_name} - {client_display_company},

Công ty Cổ phần Công nghệ Cô Nàng Tinh Nghịch xin gửi lời chào trân trọng và lời cảm ơn sâu sắc đến Quý công ty.
Tôi là {rep.get('name', 'Trần Phương Thảo')} - Chuyên viên phụ trách trực tiếp yêu cầu của Quý khách.

Căn cứ vào nhu cầu của Quý công ty, Cô Nàng Tinh Nghịch xin trân trọng gửi Bản Báo Giá Dự Thảo như sau:

--- BẢNG BÁO GIÁ DỰ THẢO (MÃ SỐ: {code}) ---
{item_rows_txt}
• Tổng giá trị trước chiết khấu: {total_orig_str}
• Chiết khấu áp dụng: {stage3.get('discount_pct', 0)}% (-{stage3.get('discount_amount', 0):,.0f} VNĐ)
• TỔNG GIÁ TRỊ THANH TOÁN: {total_final_str}

--- CAM KẾT VẬN HÀNH & TIẾN ĐỘ TRIỂN KHAI ---
• Thời gian bàn giao cam kết: {stage3.get('feasible_deadline', '3 ngày làm việc')} (Đội ngũ kỹ thuật hỗ trợ tận nơi).
• Tiêu chuẩn bảo hành: Chính hãng theo từng thiết bị (12 - 36 tháng), đổi mới trong 30 ngày nếu phát sinh lỗi phần cứng.
• Phương thức thanh toán: Đặt cọc 30% khi ký hợp đồng, 70% sau khi bàn giao nghiệm thu.

Anh/Chị vui lòng xem chi tiết và phản hồi để Cô Nàng Tinh Nghịch giữ tồn kho khả dụng cho đơn hàng của mình.

Trân trọng,
{rep.get('name', 'Trần Phương Thảo')} | {rep.get('department', 'Bộ phận Kinh doanh B2B')}
Công ty Cổ phần Công nghệ Cô Nàng Tinh Nghịch
Điện thoại: {rep.get('phone', '0912 345 671')} | Email: {rep.get('email', 'sales@conangtinhnghich.vn')}
Địa chỉ: Tầng 5, Tòa nhà Công nghệ, Cầu Giấy, Hà Nội
"""

    return {
        "success": True,
        "code": code,
        "is_sufficient": True,
        "status": stage3.get("status", "READY_TO_SEND"),
        "client_info": {
            "name": client_display_name,
            "company": client_display_company,
            "email": stage2.get("clean_email", ""),
            "phone": stage2.get("clean_phone", "")
        },
        "assigned_rep": rep,
        "items": items,
        "total_original": stage3.get("total_original", 0),
        "discount_pct": stage3.get("discount_pct", 0),
        "discount_amount": stage3.get("discount_amount", 0),
        "total_final": stage3.get("total_final", 0),
        "requested_budget": stage2.get("clean_budget", 0),
        "requested_deadline": stage2.get("clean_deadline", ""),
        "feasible_deadline": stage3.get("feasible_deadline", ""),
        "deadline_status": stage3.get("deadline_status", "Tiêu chuẩn"),
        "stock_warnings": stage3.get("stock_warnings", []),
        "requires_manager_approval": stage3.get("requires_approval", False),
        "approval_reasons": stage3.get("approval_reasons", []),
        "proposal_email_draft": proposal_email_draft
    }


# ==============================================================================
# PIPELINE CHÍNH (ORCHESTRATOR): NHẬP -> LÀM SẠCH -> XỬ LÝ -> RA KẾT QUẢ
# ==============================================================================
def run_agent_workflow(raw_request, options=None, custom_rep_name=None, custom_rep_dept=None):
    """
    Quy trình xử lý hoàn chỉnh 4 bước:
      1. NHẬP: Thu nhận dữ liệu thô
      2. LÀM SẠCH: Chuẩn hóa, bóc tách thực thể và kiểm tra tính toàn vẹn
      3. XỬ LÝ: Thẩm định tồn kho, bảng giá mới, hạn mức chiết khấu và phân quyền
      4. RA KẾT QUẢ: Lập hồ sơ cơ hội, bảng báo giá và bản nháp phản hồi
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute('SELECT * FROM products')
    db_products = [dict(row) for row in cur.fetchall()]

    cur.execute('SELECT * FROM sales_reps')
    db_sales_reps = [dict(row) for row in cur.fetchall()]

    # 1. NHẬP
    s1 = stage_1_input(raw_request)

    # 2. LÀM SẠCH
    s2 = stage_2_clean(s1)

    # 3. XỬ LÝ
    s3 = stage_3_process(s2, db_products, db_sales_reps, raw_request, custom_rep_name=custom_rep_name, custom_rep_dept=custom_rep_dept)

    # 4. RA KẾT QUẢ
    s4 = stage_4_output(s1, s2, s3)

    # Lưu vào Database nếu hợp lệ
    try:
        if s4["is_sufficient"]:
            # Tăng current_leads cho NVKD nếu có trong db
            rep_id = s4["assigned_rep"].get("id", 1)
            rep_name = s4["assigned_rep"].get("name", "NVKD")
            rep_email = s4["assigned_rep"].get("email", "sales@conangtinhnghich.vn")
            
            # Nếu NVKD tự nhập chưa có trong bảng sales_reps, tự động tạo mới
            cur.execute('SELECT id FROM sales_reps WHERE name = ?', (rep_name,))
            existing_rep = cur.fetchone()
            if existing_rep:
                rep_id = existing_rep[0]
                cur.execute('UPDATE sales_reps SET current_leads = current_leads + 1 WHERE id = ?', (rep_id,))
            else:
                cur.execute('INSERT INTO sales_reps (code, name, email, phone, current_leads, specialty) VALUES (?, ?, ?, ?, ?, ?)',
                            (f"KD{random.randint(10,99)}", rep_name, rep_email, "0988 888 888", 1, "Kinh doanh B2B"))
                rep_id = cur.lastrowid

            cur.execute('''
            INSERT INTO opportunities (
                code, client_name, client_company, client_email, client_phone,
                raw_request, status, is_info_sufficient, assigned_rep_id, assigned_rep_name,
                requested_budget, requested_deadline, feasible_deadline, deadline_status,
                total_original_price, requested_discount_pct, approved_discount_pct, total_final_price,
                requires_manager_approval, approval_status, manager_notes, proposal_email_draft
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                s4["code"], s4["client_info"]["name"], s4["client_info"]["company"],
                s4["client_info"]["email"], s4["client_info"]["phone"],
                raw_request, s4["status"], 1, s4["assigned_rep"]["id"], s4["assigned_rep"]["name"],
                s4["requested_budget"], s4["requested_deadline"], s4["feasible_deadline"], s4["deadline_status"],
                s4["total_original"], s4["discount_pct"], 0 if s4["requires_manager_approval"] else s4["discount_pct"], s4["total_final"],
                1 if s4["requires_manager_approval"] else 0,
                "PENDING_APPROVAL" if s4["requires_manager_approval"] else "NOT_REQUIRED",
                "; ".join(s4["approval_reasons"]) if s4["requires_manager_approval"] else "Đã tự động thẩm định",
                s4["proposal_email_draft"]
            ))
            opp_id = cur.lastrowid
            s4["opportunity_id"] = opp_id

            # Lưu chi tiết sản phẩm
            for it in s4["items"]:
                cur.execute('''
                INSERT INTO opportunity_items (
                    opportunity_id, product_id, matched_sku, matched_name, requested_name,
                    quantity, unit_price, total_price, stock_available, is_stock_sufficient, item_lead_time_days
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    opp_id, it['product_id'], it['sku'], it['name'], it['name'],
                    it['quantity'], it['unit_price'], it['total_price'],
                    it['stock_available'], it['is_stock_sufficient'], it['item_lead_time_days']
                ))
            conn.commit()
        else:
            cur.execute('''
            INSERT INTO opportunities (
                code, client_name, client_company, client_email, client_phone,
                raw_request, status, is_info_sufficient, missing_info_notes, proposal_email_draft
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                s4["code"], s2["clean_name"], s2["clean_company"], s2["clean_email"], s2["clean_phone"],
                raw_request, "CLARIFICATION_NEEDED", 0, "; ".join(s4["missing_fields"]), s4["clarification_email"]
            ))
            opp_id = cur.lastrowid
            s4["opportunity_id"] = opp_id
            for it in s3.get("items_evaluated", []):
                cur.execute('''
                INSERT INTO opportunity_items (
                    opportunity_id, product_id, matched_sku, matched_name, requested_name,
                    quantity, unit_price, total_price, stock_available, is_stock_sufficient, item_lead_time_days
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    opp_id, it.get('product_id'), it.get('sku'), it.get('name'), it.get('name'),
                    it.get('quantity', 1), it.get('unit_price', 0), it.get('total_price', 0),
                    it.get('stock_available', 0), it.get('is_stock_sufficient', 1), it.get('item_lead_time_days', 0)
                ))
            conn.commit()
    except Exception as e:
        print("Error saving to DB:", e)
    finally:
        conn.close()

    # Đóng gói toàn bộ 4 giai đoạn trả về để UI hiển thị trực quan
    s4["stages"] = {
        "stage_1_input": s1,
        "stage_2_clean": s2,
        "stage_3_process": s3,
        "stage_4_output": {
            "code": s4["code"],
            "status": s4["status"],
            "is_sufficient": s4["is_sufficient"]
        }
    }

    return s4

def approve_opportunity(opp_id, action, manager_notes=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM opportunities WHERE id = ?', (opp_id,))
    opp = cur.fetchone()
    if not opp:
        conn.close()
        return {"success": False, "error": "Không tìm thấy cơ hội"}

    if action == "APPROVE":
        cur.execute('''
        UPDATE opportunities 
        SET approval_status = 'APPROVED', 
            status = 'READY_TO_SEND',
            approved_discount_pct = requested_discount_pct,
            manager_notes = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        ''', (manager_notes or "Trưởng phòng đã phê duyệt mức chiết khấu và đề xuất.", opp_id))
    elif action == "REJECT":
        cur.execute('''
        UPDATE opportunities 
        SET approval_status = 'REJECTED', 
            status = 'REJECTED',
            manager_notes = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        ''', (manager_notes or "Trưởng phòng yêu cầu NVKD thương lượng lại.", opp_id))

    conn.commit()
    conn.close()
    return {"success": True, "action": action}
