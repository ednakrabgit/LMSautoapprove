"""
Auto Approve Script for Viriyah Online Learning Admin Portal
Automates the approval process for training enrollments with multi-flow support:
- Flow 1: "ผ่านการตรวจสอบ" (Approved passed verification items)
- Flow 2: "รออนุมัติ" (Verify ID checks -> Pass verification -> Approve)
"""

import os
import sys
import time
import logging
from urllib.parse import urljoin
from pathlib import Path

# Configure Playwright to use portable local ms-playwright directory if present
LOCAL_BROWSERS_DIR = Path(__file__).resolve().parent / "ms-playwright"
if LOCAL_BROWSERS_DIR.exists():
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(LOCAL_BROWSERS_DIR)

from typing import Callable, Optional, List
from playwright.sync_api import sync_playwright, Page, BrowserContext

# Target URL
TARGET_URL = "https://vonlinelearning.viriyah.co.th/admin/trainingEnrollments?activeTab=pendingApproval"
USER_DATA_DIR = Path(__file__).resolve().parent / "browser_profile"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("AutoApprove")

# Allowed phrases for Flow 2 ("รออนุมัติ") in "ผลการตรวจสอบ"
ALLOWED_VERIFICATION_PHRASES = [
    "ไม่ได้รับการตรวจสอบจากกรมการปกครอง",
    "ไม่ได้รับการตรวจสอบการปลอมแปลงภาพถ่ายบัตรประชาชน",
    "ผ่านการตรวจสอบความถูกต้องจากการอ่านข้อมูลบนบัตรประชาชน"
]


class AutoApproveBot:
    def __init__(
        self,
        log_callback: Optional[Callable[[str], None]] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        status_callback: Optional[Callable[[str], None]] = None,
        flow_type: str = "ผ่านการตรวจสอบ",  # "ผ่านการตรวจสอบ" or "รออนุมัติ"
        remark_text: str = "อนุมัติ",
        delay_seconds: float = 1.5,
        max_items: int = 0,  # 0 means unlimited / all
        headless: bool = False
    ):
        self.log_callback = log_callback
        self.progress_callback = progress_callback
        self.status_callback = status_callback
        self.flow_type = flow_type
        self.remark_text = remark_text
        self.delay_seconds = delay_seconds
        self.max_items = max_items
        self.headless = headless
        
        self.is_running = False
        self.is_paused = False
        self.processed_count = 0
        self.skipped_rows = set()

    def log(self, message: str, level: str = "INFO"):
        if level == "ERROR":
            logger.error(message)
        elif level == "WARNING":
            logger.warning(message)
        else:
            logger.info(message)
            
        if self.log_callback:
            self.log_callback(f"[{time.strftime('%H:%M:%S')}] {message}")

    def update_status(self, status: str):
        if self.status_callback:
            self.status_callback(status)

    def stop(self):
        self.log("🛑 ได้รับคำสั่งให้หยุดการทำงาน")
        self.is_running = False
        self.is_paused = False

    def pause(self):
        self.is_paused = True
        self.log("⏸️ หยุดการทำงานชั่วคราว")
        self.update_status("หยุดชั่วคราว")

    def resume(self):
        self.is_paused = False
        self.log("▶️ ดำเนินการต่อ")
        self.update_status("กำลังทำงาน")

    def _check_pause_and_stop(self) -> bool:
        """Returns True if should continue, False if stopped."""
        while self.is_paused and self.is_running:
            time.sleep(0.5)
        return self.is_running

    def _wait_for_login(self, page: Page):
        """Checks if login is needed and waits for the user to login."""
        self.log("กำลังตรวจสอบสถานะการเข้าสู่ระบบ...")
        self.update_status("กำลังตรวจสอบการเข้าสู่ระบบ...")
        
        page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
        time.sleep(2)

        while self.is_running:
            current_url = page.url
            is_login_page = (
                "login" in current_url.lower() or 
                page.locator("input[type='password']").count() > 0 or 
                page.locator("text=เข้าสู่ระบบ").count() > 0
            )
            
            is_admin_loaded = (
                "admin" in current_url and 
                (page.locator("text=หลักสูตรเก็บชั่วโมงอบรม").count() > 0 or 
                 page.locator("text=ตรวจสอบการอนุมัติ").count() > 0 or
                 page.locator("text=ขออนุมัติ").count() > 0)
            )

            if is_admin_loaded:
                self.log("✅ ตรวจพบการเข้าสู่ระบบเรียบร้อยแล้ว!")
                break

            if is_login_page:
                self.log("⚠️ กรุณาเข้าสู่ระบบ (Login) ในหน้าต่างเบราว์เซอร์ให้เรียบร้อย...", "WARNING")
                self.update_status("รอผู้ใช้เข้าสู่ระบบ...")
                time.sleep(3)
            else:
                time.sleep(2)

    def _select_status_filter(self, page: Page, status_name: str) -> bool:
        """Ensures that the status dropdown filter is set to the target status (supports 'รออนุมัติ' and 'รออนุมัติ (ครั้งที่ 2)')."""
        try:
            self.log(f"กำลังตรวจสอบตัวกรองสถานะ: '{status_name}'...")

            # Wait briefly for filter bar or table to render
            for _ in range(15):
                try:
                    body_txt = page.locator("body").inner_text()
                    if "สถานะ" in body_txt or "ดูรายละเอียด" in body_txt or "รายการทั้งหมด" in body_txt:
                        break
                except Exception:
                    pass
                time.sleep(0.5)

            # Click tab 'ตรวจสอบการอนุมัติ' only if not already on pendingApproval tab
            if "activeTab=pendingApproval" not in page.url:
                tab = page.locator("button:has-text('ตรวจสอบการอนุมัติ'), a:has-text('ตรวจสอบการอนุมัติ')").first
                try:
                    if tab.count() > 0 and tab.is_visible():
                        tab.click()
                        time.sleep(1.5)
                except Exception:
                    pass

            # Find the specific filter dropdown trigger that contains 'สถานะ:' (e.g. 'สถานะ: รออนุมัติ' or 'สถานะ: ทั้งหมด')
            status_dropdown = None
            best_area = float("inf")
            dropdown_triggers = page.locator("button, div, span").filter(has_text="สถานะ").all()
            for trigger in dropdown_triggers:
                try:
                    if not trigger.is_visible():
                        continue
                    txt = trigger.inner_text().strip()
                    # Must be the filter pill containing 'สถานะ:' (not the table header 'สถานะ' or the full page container)
                    if "สถานะ:" not in txt and "สถานะ :" not in txt:
                        continue
                    box = trigger.bounding_box()
                    if box and 18 <= box["height"] <= 65 and 50 <= box["width"] <= 420:
                        area = box["width"] * box["height"]
                        tag = trigger.evaluate("el => el.tagName.toLowerCase()")
                        # Prefer <button> or smallest bounding box wrapping 'สถานะ:'
                        if tag == "button":
                            status_dropdown = trigger
                            break
                        if area < best_area:
                            best_area = area
                            status_dropdown = trigger
                except Exception:
                    continue

            if status_dropdown:
                text_content = status_dropdown.inner_text().strip()
                # Accepts both 'รออนุมัติ' and 'รออนุมัติ (ครั้งที่ 2)' when status_name is 'รออนุมัติ'
                if status_name in text_content:
                    self.log(f"ตัวกรองสถานะตั้งค่าเป็น '{text_content}' เรียบร้อยแล้ว")
                    return True

                self.log(f"กำลังเปลี่ยนตัวกรองจาก '{text_content}' เป็น '{status_name}'...")
                status_dropdown.click()
                time.sleep(1.0)

                # Find option inside dropdown menu (strictly excluding table rows/cells and summary cards)
                clicked_option = page.evaluate(
                    """(targetStatus) => {
                        const candidates = Array.from(document.querySelectorAll('li, [role="option"], [role="menuitem"], button, div, span'));
                        let bestEl = null;
                        let bestArea = Infinity;
                        for (const el of candidates) {
                            if (el.closest('table, tbody, thead, tr, td, th')) continue;
                            const rect = el.getBoundingClientRect();
                            if (rect.width < 20 || rect.width > 380 || rect.height < 14 || rect.height > 60) continue;
                            if (rect.top <= 0 || rect.left <= 0) continue;
                            const txt = (el.innerText || '').trim();
                            if (!txt || txt.includes('สถานะ:')) continue;
                            // Match exact status name (e.g. 'รออนุมัติ' or 'ผ่านการตรวจสอบ')
                            if (txt === targetStatus || txt === targetStatus + ' (ครั้งที่ 2)') {
                                const area = rect.width * rect.height;
                                if (area < bestArea) {
                                    bestArea = area;
                                    bestEl = el;
                                }
                            }
                        }
                        if (bestEl) {
                            bestEl.click();
                            return true;
                        }
                        return false;
                    }""",
                    status_name
                )

                if clicked_option:
                    self.log(f"✅ เลือกสถานะ '{status_name}' สำเร็จ")
                    time.sleep(2.5)
                    return True

            # Fallback for <select> element
            selects = page.locator("select").all()
            for sel in selects:
                if sel.is_visible():
                    options = sel.locator("option").all_inner_texts()
                    for opt in options:
                        if status_name in opt:
                            sel.select_option(label=opt)
                            self.log(f"✅ เลือกตัวกรองสถานะ '{status_name}' ผ่าน select box สำเร็จ")
                            time.sleep(2)
                            return True

            self.log(f"ตัวกรองสถานะ '{status_name}' พร้อมใช้งาน", "INFO")
            return True
        except Exception as e:
            self.log(f"⚠️ เกิดข้อผิดพลาดในการตั้งค่าตัวกรอง: {e}", "WARNING")
            return False

    def _find_next_detail_button(self, page: Page):
        """
        Finds the next visible 'ดูรายละเอียด' button in the table that hasn't been skipped yet.
        Supports rows with status 'รออนุมัติ', 'รออนุมัติ (ครั้งที่ 2)', etc., as well as 'ผ่านการตรวจสอบ'.
        Returns (button_locator, row_key, row_status_text) or (None, None, None).
        """
        # Wait up to 8 seconds for table buttons to render
        for _ in range(16):
            if not self.is_running:
                return None, None, None
            btns = page.locator("button:has-text('ดูรายละเอียด'), a:has-text('ดูรายละเอียด')").all()
            if any(b.is_visible() for b in btns):
                break
            time.sleep(0.5)

        detail_buttons = page.locator("button:has-text('ดูรายละเอียด')").all()
        visible_buttons = [btn for btn in detail_buttons if btn.is_visible()]
        if not visible_buttons:
            detail_links = page.locator("a:has-text('ดูรายละเอียด')").all()
            visible_buttons = [lnk for lnk in detail_links if lnk.is_visible()]

        if not visible_buttons:
            return None, None, None

        self.log(f"พบรายการในหน้านี้ทั้งหมด {len(visible_buttons)} รายการ")

        for idx, btn in enumerate(visible_buttons):
            try:
                # Extract row text & status from ancestor <tr> or row container
                row_info = btn.evaluate(
                    """(el) => {
                        const tr = el.closest('tr') || el.parentElement?.parentElement || el.parentElement;
                        if (!tr) return { key: '', status: '', summary: '' };
                        const cells = Array.from(tr.querySelectorAll('td')).map(td => (td.innerText || '').trim());
                        if (cells.length >= 6) {
                            const name = cells[0] || '';
                            const email = cells[1] || '';
                            const idCard = cells[2] || '';
                            const course = cells[3] || '';
                            const dateStr = cells[4] || '';
                            const status = cells[5] || '';
                            return {
                                key: `${name}|${idCard}|${course}|${dateStr}`,
                                status: status,
                                summary: `${name} (${idCard}) - สถานะ: ${status}`
                            };
                        }
                        const fullText = (tr.innerText || '').replace(/\\s+/g, ' ').trim();
                        return { key: fullText.slice(0, 120), status: fullText, summary: fullText.slice(0, 100) };
                    }"""
                )
                row_key = row_info.get("key") or f"row_{idx}"
                row_status = row_info.get("status") or ""
                row_summary = row_info.get("summary") or f"รายการที่ {idx + 1}"

                if row_key in self.skipped_rows:
                    continue

                # Check if row status matches current flow:
                # Flow 2 ('รออนุมัติ') accepts 'รออนุมัติ', 'รออนุมัติ (ครั้งที่ 2)', 'รออนุมัติ (ครั้งที่ 3)', etc.
                # Flow 1 ('ผ่านการตรวจสอบ') accepts 'ผ่านการตรวจสอบ'
                if self.flow_type == "รออนุมัติ":
                    if row_status and ("ไม่อนุมัติ" in row_status or ("รออนุมัติ" not in row_status and "ผ่านการตรวจสอบ" not in row_status)):
                        self.log(f"⏭️ ข้าม {row_summary} (สถานะไม่ใช่ รออนุมัติ / รออนุมัติ (ครั้งที่ 2))")
                        self.skipped_rows.add(row_key)
                        continue
                else:
                    if row_status and "ผ่านการตรวจสอบ" not in row_status:
                        self.log(f"⏭️ ข้าม {row_summary} (สถานะไม่ใช่ ผ่านการตรวจสอบ)")
                        self.skipped_rows.add(row_key)
                        continue

                self.log(f"📌 เลือกดำเนินการ: {row_summary}")
                return btn, row_key, row_status
            except Exception:
                return btn, f"row_{idx}", ""

        return None, None, None

    def _open_detail_in_new_tab(self, page: Page, detail_btn) -> Optional[Page]:
        """Opens the detail link in a new browser tab."""
        context = page.context
        original_url = page.url

        # Method 1: If <a> tag with href (ancestor, self, or child)
        try:
            href = detail_btn.evaluate(
                """(el) => {
                    if (el.tagName.toLowerCase() === 'a' && el.getAttribute('href')) return el.getAttribute('href');
                    const anc = el.closest('a');
                    if (anc && anc.getAttribute('href')) return anc.getAttribute('href');
                    const child = el.querySelector('a');
                    if (child && child.getAttribute('href')) return child.getAttribute('href');
                    return null;
                }"""
            )
            if href and not href.startswith("javascript"):
                full_url = urljoin(page.url, href)
                self.log(f"🌐 กำลังเปิดแท็บใหม่ไปยัง: {full_url}")
                new_tab = context.new_page()
                new_tab.goto(full_url, wait_until="domcontentloaded", timeout=45000)
                return new_tab
        except Exception as e:
            logger.debug(f"Href lookup: {e}")

        # Method 2: Ctrl+Click (Win/Linux) or Meta+Click (Mac) or Middle Click inside expect_page
        modifier_key = "Meta" if sys.platform == "darwin" else "Control"
        try:
            self.log("🌐 กำลังกดเปิด 'ดูรายละเอียด' ในแท็บใหม่...")
            detail_btn.scroll_into_view_if_needed()
            with context.expect_page(timeout=6000) as new_page_info:
                try:
                    detail_btn.click(modifiers=[modifier_key])
                except Exception:
                    detail_btn.click(button="middle")
            new_tab = new_page_info.value
            new_tab.wait_for_load_state("domcontentloaded", timeout=45000)
            return new_tab
        except Exception as e:
            logger.debug(f"{modifier_key}+Click: {e}")

        # Check if Method 2 navigated the main page itself in the same tab
        if page.url != original_url and "activeTab=pendingApproval" not in page.url:
            detail_url = page.url
            self.log(f"🌐 เปิดหน้ารายละเอียดในแท็บใหม่: {detail_url}")
            new_tab = context.new_page()
            new_tab.goto(detail_url, wait_until="domcontentloaded", timeout=45000)
            try:
                page.goto(original_url, wait_until="domcontentloaded", timeout=45000)
            except Exception:
                pass
            return new_tab

        # Method 3: Standard click (either opens a new tab OR navigates same tab)
        try:
            with context.expect_page(timeout=4000) as new_page_info:
                detail_btn.click()
            new_tab = new_page_info.value
            new_tab.wait_for_load_state("domcontentloaded", timeout=45000)
            return new_tab
        except Exception as e:
            if page.url != original_url and "activeTab=pendingApproval" not in page.url:
                detail_url = page.url
                self.log(f"🌐 เปิดหน้ารายละเอียดในแท็บใหม่: {detail_url}")
                new_tab = context.new_page()
                new_tab.goto(detail_url, wait_until="domcontentloaded", timeout=45000)
                try:
                    page.goto(original_url, wait_until="domcontentloaded", timeout=45000)
                except Exception:
                    pass
                return new_tab
            self.log(f"❌ ไม่สามารถเปิดแท็บใหม่ได้: {e}", "ERROR")
            return None

    def _wait_for_detail_page_ready(self, detail_page: Page, timeout_seconds: int = 20):
        """Waits until the detail page finishes rendering its content."""
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            if not self.is_running:
                return
            try:
                body_text = detail_page.locator("body").inner_text()
                if (
                    "ผลการตรวจสอบ" in body_text
                    or "ข้อมูลการยืนยันตัวตน" in body_text
                    or "รายละเอียดการเรียน" in body_text
                    or self._is_already_approved(detail_page)
                ):
                    time.sleep(1.0)
                    return
            except Exception:
                pass
            time.sleep(0.5)

    def _is_already_approved(self, detail_page: Page) -> bool:
        """Checks if certificate button/text is already shown."""
        return (
            detail_page.locator("button:has-text('ตรวจสอบใบประกาศนียบัตร')").count() > 0 or
            detail_page.locator("button:has-text('ตรวจสอบประกาศนียบัตร')").count() > 0 or
            detail_page.locator("button:has-text('ตรวจสอบใบประกาศ')").count() > 0 or
            detail_page.locator("text=ตรวจสอบใบประกาศนียบัตร").count() > 0 or
            detail_page.locator("text=ตรวจสอบประกาศนียบัตร").count() > 0
        )

    def _fill_and_confirm_modal(self, detail_page: Page, remark_text: str, modal_title_hint: str = "") -> bool:
        """Waits for popup modal, fills remark, clicks confirm, and waits for modal to close."""
        self.log(f"กำลังรอ Pop-up {modal_title_hint}...")
        try:
            detail_page.wait_for_selector("textarea, input[placeholder*='หมายเหตุ'], .ant-modal, .modal, div[role='dialog']", timeout=10000)
        except Exception:
            pass

        time.sleep(0.6)

        # 1. Fill Remark
        remark_input = None
        input_candidates = [
            detail_page.locator(".ant-modal textarea, .modal textarea, div[role='dialog'] textarea"),
            detail_page.locator("textarea[placeholder*='หมายเหตุ']"),
            detail_page.locator("textarea"),
            detail_page.locator(".ant-modal input, .modal input, div[role='dialog'] input"),
            detail_page.locator("input[placeholder*='หมายเหตุ']")
        ]

        for candidate in input_candidates:
            try:
                if candidate.count() > 0 and candidate.first.is_visible():
                    remark_input = candidate.first
                    break
            except Exception:
                continue

        if remark_input:
            self.log(f"✍️ กรอกข้อความในช่องหมายเหตุ: '{remark_text}'")
            remark_input.fill(remark_text)
            time.sleep(0.5)
        else:
            self.log(f"⚠️ ไม่พบช่องกรอกหมายเหตุ กำลังกดปุ่มยืนยันต่อ...", "WARNING")

        # 2. Click Confirm Button ('ยืนยัน')
        self.log("🔘 กำลังกดปุ่ม 'ยืนยัน'...")
        confirm_btn = None
        confirm_candidates = [
            detail_page.locator(".ant-modal, .modal, div[role='dialog']").locator("button:has-text('ยืนยัน')"),
            detail_page.get_by_role("button", name="ยืนยัน", exact=True),
            detail_page.locator("button:text-is('ยืนยัน')"),
            detail_page.locator("button.btn-primary:has-text('ยืนยัน'), button.ant-btn-primary:has-text('ยืนยัน')"),
            detail_page.locator("//button[normalize-space()='ยืนยัน']"),
            detail_page.locator("button:has-text('ยืนยัน')").last
        ]

        for candidate in confirm_candidates:
            try:
                if candidate.count() > 0 and candidate.first.is_visible():
                    confirm_btn = candidate.first
                    break
            except Exception:
                continue

        if not confirm_btn:
            self.log("❌ ไม่พบปุ่ม 'ยืนยัน'", "ERROR")
            return False

        confirm_btn.click()
        self.log(f"✅ กดปุ่มยืนยัน ({modal_title_hint}) สำเร็จแล้ว!")

        # Wait until the modal (textarea / 'ละทิ้ง' button) closes so the underlying page updates
        start_wait = time.time()
        while time.time() - start_wait < 12:
            try:
                if detail_page.locator("textarea").count() == 0 or not detail_page.locator("textarea").first.is_visible():
                    break
            except Exception:
                break
            time.sleep(0.5)

        time.sleep(1.0)
        return True

    def _wait_for_cert_button(self, detail_page: Page, timeout_seconds: int = 45) -> bool:
        """Waits until bottom-right shows 'ตรวจสอบใบประกาศนียบัตร' / 'ตรวจสอบประกาศนียบัตร'."""
        self.log("⏳ กำลังรอจนกว่าจะขึ้นคำว่า 'ตรวจสอบใบประกาศนียบัตร' ที่มุมขวาล่าง...")
        self.update_status("รอคำว่า 'ตรวจสอบใบประกาศนียบัตร'...")

        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            if not self.is_running:
                return False
            try:
                if self._is_already_approved(detail_page):
                    self.log("✨ ตรวจพบปุ่ม 'ตรวจสอบใบประกาศนียบัตร' เรียบร้อยแล้ว!")
                    return True
            except Exception:
                pass
            time.sleep(1)

        self.log("⚠️ รอนานเกินกำหนด ระบบอาจบันทึกสำเร็จแล้ว ดำเนินการต่อ...", "WARNING")
        return True

    def _find_action_button(self, detail_page: Page, button_name: str):
        """
        Finds specific action button like 'อนุมัติ' or 'ผ่านการตรวจสอบ' at bottom-right.
        Strictly avoids matching tabs/sidebar items like 'ประวัติการอนุมัติ', 'ตรวจสอบการอนุมัติ', 'ไม่อนุมัติ'.
        """
        exact_candidates = [
            detail_page.get_by_role("button", name=button_name, exact=True),
            detail_page.locator(f"button:text-is('{button_name}')"),
            detail_page.locator(f"//button[normalize-space()='{button_name}']"),
        ]
        for candidate in exact_candidates:
            try:
                count = candidate.count()
                for i in range(count):
                    btn = candidate.nth(i)
                    if btn.is_visible():
                        return btn
            except Exception:
                continue

        forbidden_substrings = [
            "ไม่",
            "ประวัติ",
            "ตรวจสอบการอนุมัติ",
            "ใบประกาศ",
            "ประกาศนียบัตร",
            "กลับไป",
            "ละทิ้ง",
            "ยืนยัน",
        ]
        try:
            all_buttons = detail_page.locator("button, a[role='button']").all()
            for btn in reversed(all_buttons):
                try:
                    if not btn.is_visible():
                        continue
                    txt = btn.inner_text().strip()
                    if not txt:
                        continue
                    if any(bad in txt for bad in forbidden_substrings):
                        continue
                    if txt == button_name or txt.startswith(button_name):
                        return btn
                except Exception:
                    continue
        except Exception:
            pass
        return None

    def _verify_id_card_check(self, detail_page: Page) -> bool:
        """
        Flow 2 - Step 2: ตรวจสอบเครื่องหมายในช่อง "ผลการตรวจสอบ"
        - ต้องพบข้อความครบถ้วน:
          1. "ไม่ได้รับการตรวจสอบจากกรมการปกครอง"
          2. "ไม่ได้รับการตรวจสอบการปลอมแปลงภาพถ่ายบัตรประชาชน"
          3. "ผ่านการตรวจสอบความถูกต้องจากการอ่านข้อมูลบนบัตรประชาชน"
        - ถ้าไม่พบข้อความใดข้อความหนึ่ง ให้ปิดหน้านี้ได้เลย (return False)
        """
        self.log("🔍 กำลังตรวจสอบข้อความในช่อง 'ผลการตรวจสอบ'...")
        
        try:
            # Wait up to 12 seconds for 'ผลการตรวจสอบ' to appear on the page
            for _ in range(24):
                try:
                    if detail_page.locator("text=ผลการตรวจสอบ").count() > 0:
                        break
                except Exception:
                    pass
                time.sleep(0.5)

            full_check_text = detail_page.locator("body").inner_text()

            # Helper for whitespace-agnostic comparison
            def clean_str(s: str) -> str:
                return "".join(s.split())

            clean_full_text = clean_str(full_check_text)

            # Check for the required 3 phrases
            missing_phrases = []
            found_phrases = []

            for phrase in ALLOWED_VERIFICATION_PHRASES:
                if clean_str(phrase) in clean_full_text or phrase in full_check_text:
                    found_phrases.append(phrase)
                else:
                    missing_phrases.append(phrase)

            if missing_phrases:
                self.log(f"⛔ ตรวจไม่พบข้อความที่กำหนดใน 'ผลการตรวจสอบ' (ไม่พบ: {', '.join(missing_phrases)}) -> ปิดแท็บและข้ามรายการนี้", "WARNING")
                return False

            self.log(f"✅ ตรวจพบข้อความใน 'ผลการตรวจสอบ' ครบถ้วนทั้ง 3 รายการ:")
            for p in found_phrases:
                self.log(f"   • {p}")
            return True

        except Exception as e:
            self.log(f"⚠️ เกิดข้อผิดพลาดในการอ่านผลการตรวจสอบ: {e}", "WARNING")
            return False

    def _process_flow1_transaction(self, main_page: Page, detail_btn) -> bool:
        """
        FLOW 1: 'ผ่านการตรวจสอบ'
        1. Open in new tab
        2. Early check: if 'ตรวจสอบใบประกาศนียบัตร' exists -> close tab immediately
        3. Click 'อนุมัติ' at bottom-right
        4. Popup 'อนุมัติ' -> Fill 'อนุมัติ' -> Click 'ยืนยัน'
        5. Wait until bottom-right shows 'ตรวจสอบใบประกาศนียบัตร'
        6. Close tab
        """
        detail_page = None
        try:
            detail_page = self._open_detail_in_new_tab(main_page, detail_btn)
            if not detail_page:
                return False

            self.log("⏳ กำลังโหลดหน้ารายละเอียดการเรียน...")
            self._wait_for_detail_page_ready(detail_page, timeout_seconds=20)

            # Early Check
            if self._is_already_approved(detail_page):
                self.log("ℹ️ ตรวจพบคำว่า 'ตรวจสอบใบประกาศนียบัตร' อยู่แล้ว (อนุมัติแล้ว) ปิดแท็บได้ทันที")
                detail_page.close()
                detail_page = None
                main_page.bring_to_front()
                return True

            # Locate and click 'อนุมัติ'
            self.log("🔍 กำลังค้นหาปุ่ม 'อนุมัติ' ด้านล่างขวา...")
            approve_btn = None
            for _ in range(10):
                approve_btn = self._find_action_button(detail_page, "อนุมัติ")
                if approve_btn:
                    break
                time.sleep(0.5)

            if not approve_btn:
                self.log("❌ ไม่พบปุ่ม 'อนุมัติ' ในหน้ารายละเอียด", "ERROR")
                detail_page.close()
                return False

            self.log("🔘 กำลังกดปุ่ม 'อนุมัติ'...")
            approve_btn.scroll_into_view_if_needed()
            approve_btn.click()
            time.sleep(1)

            # Modal Fill & Confirm
            success = self._fill_and_confirm_modal(detail_page, self.remark_text if self.remark_text else "อนุมัติ", "อนุมัติ")
            if not success:
                detail_page.close()
                return False

            # Wait for certificate button
            self._wait_for_cert_button(detail_page, timeout_seconds=45)

            # Close tab
            self.log("🔒 กำลังปิดแท็บรายละเอียด...")
            detail_page.close()
            detail_page = None
            main_page.bring_to_front()
            time.sleep(self.delay_seconds)
            return True

        except Exception as e:
            self.log(f"❌ เกิดข้อผิดพลาดในรายการนี้ (Flow 1): {e}", "ERROR")
            if detail_page and not detail_page.is_closed():
                try:
                    detail_page.close()
                except Exception:
                    pass
            main_page.bring_to_front()
            return False

    def _process_flow2_transaction(self, main_page: Page, detail_btn) -> bool:
        """
        FLOW 2: 'รออนุมัติ' และ 'รออนุมัติ (ครั้งที่ 2)'
        1. Open in new tab
        2. Check 'ผลการตรวจสอบ' (if warnings outside allowed 3 phrases -> close tab)
        3. Click 'ผ่านการตรวจสอบ' at bottom-right
        4. Popup 'ผ่านการตรวจสอบ' -> Fill 'ผ่านการตรวจสอบ' -> Click 'ยืนยัน'
        5. Wait until bottom-right shows 'อนุมัติ' -> Click 'อนุมัติ'
        6. Popup 'อนุมัติ' -> Fill 'อนุมัติ' -> Click 'ยืนยัน'
        7. Wait until bottom-right shows 'ตรวจสอบใบประกาศนียบัตร' -> Close tab
        """
        detail_page = None
        try:
            detail_page = self._open_detail_in_new_tab(main_page, detail_btn)
            if not detail_page:
                return False

            self.log("⏳ กำลังโหลดหน้ารายละเอียดการเรียน (รองรับทั้ง 'รออนุมัติ' และ 'รออนุมัติ (ครั้งที่ 2)')...")
            self._wait_for_detail_page_ready(detail_page, timeout_seconds=20)

            # Early Check if already finished
            if self._is_already_approved(detail_page):
                self.log("ℹ️ ตรวจพบคำว่า 'ตรวจสอบใบประกาศนียบัตร' อยู่แล้ว ปิดแท็บได้ทันที")
                detail_page.close()
                detail_page = None
                main_page.bring_to_front()
                return True

            # Step 2: Check 'ผลการตรวจสอบ'
            is_valid = self._verify_id_card_check(detail_page)
            if not is_valid:
                self.log("🔒 ปิดแท็บหน้านี้ทันทีเนื่องจากผลการตรวจสอบไม่ตรงตามเงื่อนไข")
                detail_page.close()
                detail_page = None
                main_page.bring_to_front()
                return False

            # Step 3: Wait up to 10s to locate 'ผ่านการตรวจสอบ' (or 'อนุมัติ' if already passed verification)
            self.log("🔍 กำลังค้นหาปุ่ม 'ผ่านการตรวจสอบ' ด้านขวาล่าง...")
            verify_pass_btn = None
            approve_btn = None
            for _ in range(20):
                verify_pass_btn = self._find_action_button(detail_page, "ผ่านการตรวจสอบ")
                if verify_pass_btn:
                    break
                approve_btn = self._find_action_button(detail_page, "อนุมัติ")
                if approve_btn:
                    break
                time.sleep(0.5)

            if not verify_pass_btn:
                if approve_btn:
                    self.log("ℹ️ รายการนี้อยู่ในขั้นตอนพร้อมกด 'อนุมัติ' กำลังดำเนินการขั้นตอน 'อนุมัติ' ต่อไป...")
                else:
                    self.log("❌ ไม่พบปุ่ม 'ผ่านการตรวจสอบ' หรือ 'อนุมัติ'", "ERROR")
                    detail_page.close()
                    return False
            else:
                self.log("🔘 กำลังกดปุ่ม 'ผ่านการตรวจสอบ' ด้านขวาล่าง...")
                verify_pass_btn.scroll_into_view_if_needed()
                verify_pass_btn.click()
                time.sleep(1)

                # Step 4: Popup 'ผ่านการตรวจสอบ' -> Fill 'ผ่านการตรวจสอบ' -> Confirm
                success = self._fill_and_confirm_modal(detail_page, "ผ่านการตรวจสอบ", "ผ่านการตรวจสอบ")
                if not success:
                    detail_page.close()
                    return False

            # Step 5: Wait until bottom-right shows 'อนุมัติ'
            self.log("⏳ กำลังรอจนกว่าจะมีปุ่ม 'อนุมัติ' ขึ้นที่มุมขวาล่าง...")
            self.update_status("รอปุ่ม 'อนุมัติ'...")
            
            approve_btn = None
            start_time = time.time()
            while time.time() - start_time < 30:
                if not self.is_running:
                    break
                if self._is_already_approved(detail_page):
                    self.log("✨ ตรวจพบปุ่ม 'ตรวจสอบใบประกาศนียบัตร' เรียบร้อยแล้ว!")
                    detail_page.close()
                    detail_page = None
                    main_page.bring_to_front()
                    time.sleep(self.delay_seconds)
                    return True
                approve_btn = self._find_action_button(detail_page, "อนุมัติ")
                if approve_btn:
                    break
                time.sleep(1)

            if not approve_btn:
                self.log("❌ ไม่พบปุ่ม 'อนุมัติ' หลังยืนยันผ่านการตรวจสอบ", "ERROR")
                detail_page.close()
                return False

            self.log("🔘 กำลังกดปุ่ม 'อนุมัติ' ด้านขวาล่าง...")
            approve_btn.scroll_into_view_if_needed()
            approve_btn.click()
            time.sleep(1)

            # Step 6: Popup 'อนุมัติ' -> Fill 'อนุมัติ' -> Confirm
            remark_to_use = self.remark_text if self.remark_text else "อนุมัติ"
            success = self._fill_and_confirm_modal(detail_page, remark_to_use, "อนุมัติ")
            if not success:
                detail_page.close()
                return False

            # Step 7: Wait until bottom-right shows 'ตรวจสอบใบประกาศนียบัตร'
            self._wait_for_cert_button(detail_page, timeout_seconds=45)

            # Close tab
            self.log("🔒 กำลังปิดแท็บรายละเอียด...")
            detail_page.close()
            detail_page = None
            main_page.bring_to_front()
            time.sleep(self.delay_seconds)
            return True

        except Exception as e:
            self.log(f"❌ เกิดข้อผิดพลาดในรายการนี้ (Flow 2): {e}", "ERROR")
            if detail_page and not detail_page.is_closed():
                try:
                    detail_page.close()
                except Exception:
                    pass
            main_page.bring_to_front()
            return False

    def run(self):
        """Main loop of the bot."""
        self.is_running = True
        self.is_paused = False
        self.processed_count = 0
        self.skipped_rows = set()
        
        self.log(f"🚀 กำลังเริ่มต้นระบบ Auto Approve [Flow: {self.flow_type}]...")
        self.update_status("กำลังเปิดเบราว์เซอร์...")

        USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

        try:
            with sync_playwright() as p:
                browser_context: Optional[BrowserContext] = None
                try:
                    browser_context = p.chromium.launch_persistent_context(
                        user_data_dir=str(USER_DATA_DIR),
                        headless=self.headless,
                        viewport={"width": 1440, "height": 900},
                        args=[
                            "--start-maximized",
                            "--disable-blink-features=AutomationControlled"
                        ]
                    )
                except Exception as e:
                    self.log(f"💥 ไม่สามารถเปิดเบราว์เซอร์ Chromium ได้: {e}", "ERROR")
                    self.log("💡 คำแนะนำ: หากติดปัญหาเรื่องเบราว์เซอร์ ให้รันคำสั่ง 'playwright install chromium' ใน Terminal หรือตรวจสอบว่าไม่มี Chrome หน้าต่างเดิมค้างอยู่", "WARNING")
                    return

                try:
                    main_page = browser_context.pages[0] if browser_context.pages else browser_context.new_page()
                    
                    # Step 1: Login & Navigation
                    self._wait_for_login(main_page)
                    if not self.is_running:
                        return

                    # Step 2: Set status filter according to flow
                    self._select_status_filter(main_page, self.flow_type)

                    self.update_status(f"กำลังดำเนินการ [{self.flow_type}]...")

                    consecutive_empty_count = 0

                    while self._check_pause_and_stop():
                        # Check if max items limit reached
                        if self.max_items > 0 and self.processed_count >= self.max_items:
                            self.log(f"🎉 ดำเนินการครบตามจำนวนที่กำหนด ({self.max_items} รายการ) เรียบร้อยแล้ว!")
                            break

                        # Ensure we are on the pending approvals list page in main tab
                        if "trainingEnrollments" not in main_page.url or "activeTab=pendingApproval" not in main_page.url:
                            self.log("กลับไปยังหน้ารายการขออนุมัติ...")
                            main_page.goto(TARGET_URL, wait_until="domcontentloaded")
                            time.sleep(2)
                            self._select_status_filter(main_page, self.flow_type)

                        # Find next available "ดูรายละเอียด" button (supports both 'รออนุมัติ' and 'รออนุมัติ (ครั้งที่ 2)')
                        target_btn, row_key, _ = self._find_next_detail_button(main_page)
                        
                        if not target_btn:
                            consecutive_empty_count += 1
                            self.log(f"ไม่พบรายการที่รอทำเพิ่มเติมในหน้านี้ (ตรวจสอบครั้งที่ {consecutive_empty_count}/3)...")
                            
                            if consecutive_empty_count >= 3:
                                self.log(f"✨ ไม่มีรายการ '{self.flow_type}' คงเหลือที่ต้องดำเนินการแล้ว!")
                                break
                            
                            main_page.reload(wait_until="domcontentloaded")
                            time.sleep(3)
                            self._select_status_filter(main_page, self.flow_type)
                            continue

                        consecutive_empty_count = 0
                        
                        if self.flow_type == "รออนุมัติ":
                            success = self._process_flow2_transaction(main_page, target_btn)
                        else:
                            success = self._process_flow1_transaction(main_page, target_btn)
                        
                        if success:
                            self.processed_count += 1
                            self.log(f"🎉 ดำเนินการสำเร็จแล้วรวม {self.processed_count} รายการ")
                            if self.progress_callback:
                                self.progress_callback(self.processed_count, self.max_items)
                            
                            # Refresh main page to update table list after action
                            time.sleep(1)
                            self.log("🔄 กำลังรีเฟรชหน้าหลัก (Refresh)...")
                            main_page.reload(wait_until="domcontentloaded")
                            time.sleep(2)
                            self._select_status_filter(main_page, self.flow_type)
                        else:
                            if row_key:
                                self.skipped_rows.add(row_key)
                            self.log("⚠️ ข้ามไปยังรายการถัดไป / ตรวจสอบรายการถัดไป", "WARNING")
                            time.sleep(self.delay_seconds)

                except Exception as e:
                    self.log(f"💥 เกิดข้อผิดพลาดขณะทำงาน: {e}", "ERROR")
                finally:
                    if browser_context:
                        try:
                            browser_context.close()
                        except Exception:
                            pass
        except Exception as e:
            self.log(f"💥 เกิดข้อผิดพลาดของระบบ: {e}", "ERROR")
        finally:
            self.is_running = False
            self.is_paused = False
            self.update_status("เสร็จสิ้น / หยุดทำงาน")
            self.log("🏁 สิ้นสุดการทำงาน")


if __name__ == "__main__":
    bot = AutoApproveBot(
        flow_type="ผ่านการตรวจสอบ",
        remark_text="อนุมัติ",
        delay_seconds=1.5,
        max_items=0,
        headless=False
    )
    bot.run()
