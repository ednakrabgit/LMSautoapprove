"""
Script to generate the comprehensive Master Prompt specification document in Word format (.docx).
Contains complete specifications for Flow 1 and Flow 2, Portable architecture, and full blueprint.
"""

import os
import sys
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

def set_cell_background(cell, fill_hex):
    tc_pr = cell._element.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), fill_hex)
    tc_pr.append(shd)

def set_cell_margins(cell, top=120, bottom=120, left=160, right=160):
    tc_pr = cell._element.get_or_add_tcPr()
    tc_mar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tc_mar.append(node)
    tc_pr.append(tc_mar)

def create_prompt_document(output_path: str):
    doc = Document()

    # Page setup
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.85)
        section.right_margin = Inches(0.85)

    # Document Header Title
    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title_p.add_run("คู่มือและคำสั่ง Prompt ฉบับสมบูรณ์ (Master Prompt Specification)\nระบบอนุมัติการอบรมอัตโนมัติ (Viriyah Auto Approve Bot)")
    title_run.font.name = 'Sarabun'
    title_run.font.size = Pt(18)
    title_run.font.bold = True
    title_run.font.color.rgb = RGBColor(24, 76, 120)

    # Subtitle
    sub_p = doc.add_paragraph()
    sub_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub_run = sub_p.add_run("เอกสารพิมพ์เขียว (Blueprint) สำหรับสร้างระบบ Web Automation Routine & Desktop GUI ตั้งแต่เริ่มต้น (Start from 0)")
    sub_run.font.name = 'Sarabun'
    sub_run.font.size = Pt(11)
    sub_run.font.italic = True
    sub_run.font.color.rgb = RGBColor(100, 100, 100)

    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    # Box: Overview Summary
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.cell(0, 0)
    set_cell_background(cell, "EBF3FA")
    set_cell_margins(cell, top=140, bottom=140, left=200, right=200)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(4)
    r1 = p.add_run("📌 วัตถุประสงค์ของเอกสาร:\n")
    r1.font.bold = True
    r1.font.size = Pt(11)
    r1.font.color.rgb = RGBColor(24, 76, 120)
    
    r2 = p.add_run(
        "เอกสารนี้รวบรวมข้อกำหนด ความต้องการ (Requirements), ลำดับการทำงาน (Workflow), "
        "และโครงสร้างคำสั่ง Prompt ฉบับละเอียด เพื่อใช้สั่งงาน AI ในการสร้างระบบบอทอัตโนมัติขึ้นมาใหม่ทั้งหมดตั้งแต่ 0 "
        "โดยรองรับทั้ง Flow 1 (ผ่านการตรวจสอบ), Flow 2 (รออนุมัติ + ตรวจสอบบัตรประชาชน), สถาปัตยกรรม Portable (Zero-Install) และ GUI สำหรับผู้ใช้งานทั่วไป"
    )
    r2.font.size = Pt(10.5)

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # ----------------------------------------------------
    # SECTION 1: MASTER PROMPT (คัดลอกไปใช้ได้ทันที)
    # ----------------------------------------------------
    h1 = doc.add_heading(level=1)
    h1_run = h1.add_run("1. Master Prompt ฉบับละเอียด (คัดลอกสั่งงาน AI ได้ทันที)")
    h1_run.font.name = 'Sarabun'
    h1_run.font.color.rgb = RGBColor(24, 76, 120)

    prompt_table = doc.add_table(rows=1, cols=1)
    prompt_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    p_cell = prompt_table.cell(0, 0)
    set_cell_background(p_cell, "F9F9F9")
    set_cell_margins(p_cell, top=140, bottom=140, left=180, right=180)

    master_prompt = (
        "【คำสั่งสร้างระบบ Desktop Automation App สำหรับ Viriyah Online Learning】\n\n"
        "ช่วยพัฒนาโปรแกรม Desktop Application ด้วย Python + Playwright + CustomTkinter สำหรับทำ Routine งานอนุมัติการอบรมบนเว็บไซต์ของบริษัท วิริยะประกันภัย โดยมีรายละเอียดความต้องการทั้งหมดดังนี้:\n\n"
        "1. ข้อมูลเว็บไซต์และการ Login:\n"
        "   - URL เป้าหมาย: https://vonlinelearning.viriyah.co.th/admin/trainingEnrollments?activeTab=pendingApproval\n"
        "   - ใช้ Persistent Context (โฟลเดอร์ browser_profile) เพื่อบันทึก Session การล็อกอินไว้ในเครื่อง\n"
        "   - เมื่อเริ่มโปรแกรม หากยังไม่ได้ล็อกอิน ให้ระบบรอให้ผู้ใช้ล็อกอินในหน้าต่างเบราว์เซอร์ให้สำเร็จก่อนเริ่มทำงานอัตโนมัติ\n\n"
        "2. เมนูเลือก Flow การทำงาน (Multi-Flow Support):\n"
        "   ก่อนกดเริ่มทำงาน ให้มีเมนูเลือก Flow ได้ 2 รูปแบบ:\n\n"
        "   ▶ Flow 1: \"ผ่านการตรวจสอบ\"\n"
        "     1) ที่หน้าหลัก เลือกตัวกรองสถานะเป็น 'ผ่านการตรวจสอบ'\n"
        "     2) กดปุ่ม 'ดูรายละเอียด' ท้ายรายการ โดยเปิดเป็นแท็บใหม่ (New Tab)\n"
        "     3) ตรวจสอบแท็บใหม่: หากตรวจพบคำว่า 'ตรวจสอบใบประกาศนียบัตร' อยู่แล้ว -> ให้ปิดแท็บทันที (ข้ามรายการ)\n"
        "     4) หากยังไม่มี -> เลื่อนไปกดปุ่ม 'อนุมัติ' ด้านล่างขวา\n"
        "     5) เมื่อมี Pop-up หมายเหตุ -> กรอกคำว่า 'อนุมัติ' -> กดปุ่ม 'ยืนยัน' ที่มุมบนขวา\n"
        "     6) รอจนกว่าปุ่มมุมขวาล่างจะเปลี่ยนเป็นคำว่า 'ตรวจสอบใบประกาศนียบัตร'\n"
        "     7) ปิดแท็บรายละเอียด สลับกลับมาหน้าหลัก ทำการ Refresh หน้าเว็บ และดำเนินการรายการถัดไป\n\n"
        "   ▶ Flow 2: \"รออนุมัติ\"\n"
        "     1) ที่หน้าหลัก เลือกตัวกรองสถานะเป็น 'รออนุมัติ'\n"
        "     2) กดปุ่ม 'ดูรายละเอียด' ท้ายรายการ โดยเปิดเป็นแท็บใหม่ (New Tab)\n"
        "     3) ตรวจสอบเงื่อนไขในช่อง 'ผลการตรวจสอบ':\n"
        "        - ต้องพบข้อความครบถ้วนทั้ง 3 ข้อความนี้:\n"
        "          * \"ไม่ได้รับการตรวจสอบจากกรมการปกครอง\"\n"
        "          * \"ไม่ได้รับการตรวจสอบการปลอมแปลงภาพถ่ายบัตรประชาชน\"\n"
        "          * \"ผ่านการตรวจสอบความถูกต้องจากการอ่านข้อมูลบนบัตรประชาชน\"\n"
        "        - หากไม่พบข้อความใดข้อความหนึ่ง (ขาดไป หรือมีข้อความเตือนอื่น) -> ให้ปิดแท็บนี้ทันทีและข้ามรายการ\n"
        "     4) หากผ่านเกณฑ์ทั้ง 3 ข้อความ -> กดปุ่ม 'ผ่านการตรวจสอบ' ด้านขวาล่าง\n"
        "     5) Pop-up ขึ้นมา -> กรอกคำว่า 'ผ่านการตรวจสอบ' ในช่องหมายเหตุ -> กดยืนยันที่มุมบนขวา\n"
        "     6) รอจนกระทั่งปุ่มด้านขวาล่างเปลี่ยนเป็นคำว่า 'อนุมัติ' -> กดปุ่ม 'อนุมัติ'\n"
        "     7) Pop-up ขึ้นมา -> กรอกคำว่า 'อนุมัติ' ในช่องหมายเหตุ -> กดยืนยันที่มุมบนขวา\n"
        "     8) รอจนกระทั่งปุ่มด้านขวาล่างเปลี่ยนเป็นคำว่า 'ตรวจสอบใบประกาศนียบัตร' -> ปิดแท็บ\n"
        "     9) สลับกลับมาหน้าหลัก ทำการ Refresh และทำรายการถัดไปจนครบ\n\n"
        "3. หน้าต่างโปรแกรมและการควบคุม (GUI & Controls):\n"
        "   - ออกแบบหน้าตา Modern GUI สวยงามด้วย CustomTkinter\n"
        "   - มี Dropdown เลือก Flow 1 หรือ Flow 2 พร้อมคำอธิบายย่อที่เปลี่ยนตามตัวเลือก\n"
        "   - ช่องตั้งค่า: ข้อความหมายเหตุ, กำหนดจำนวนที่ต้องการทำ (0 = ทั้งหมด), หน่วงเวลา (วินาที)\n"
        "   - ปุ่มควบคุม: ▶️ เริ่มทำงาน (Start), ⏸️ หยุดชั่วคราว (Pause), ⏹️ ยกเลิก / หยุด (Stop)\n"
        "   - แถบสถานะ (Status Label) และ Live Log แบบเรียลไทม์ พร้อมตัวนับจำนวนที่ทำสำเร็จ\n"
        "   - ทำงานแบบ Multi-threading เพื่อไม่ให้หน้าต่างโปรแกรมค้างขณะบอทกำลังรัน\n\n"
        "4. โครงสร้างแบบ Portable (Zero-Install):\n"
        "   - รวมไฟล์ runtime และเบราว์เซอร์ Chromium ไว้ในโฟลเดอร์ ให้สามารถยกทั้งโฟลเดอร์ไปเปิดใช้งานบนคอมพิวเตอร์ Windows เครื่องอื่นได้ทันทีโดยไม่ต้องติดตั้ง Python หรือดาวน์โหลดอะไรเพิ่ม\n"
        "   - ไฟล์ run.bat ที่เปิดโปรแกรมได้แบบ One-Click"
    )

    pp = p_cell.paragraphs[0]
    p_run = pp.add_run(master_prompt)
    p_run.font.name = 'Consolas'
    p_run.font.size = Pt(9.5)
    p_run.font.color.rgb = RGBColor(40, 40, 40)

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # ----------------------------------------------------
    # SECTION 2: รายละเอียดแต่ละ Flow และตารางเปรียบเทียบ
    # ----------------------------------------------------
    h2 = doc.add_heading(level=1)
    h2_run = h2.add_run("2. สรุปเปรียบเทียบขั้นตอนการทำงาน (Flow Comparison)")
    h2_run.font.name = 'Sarabun'
    h2_run.font.color.rgb = RGBColor(24, 76, 120)

    table = doc.add_table(rows=7, cols=3)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = 'Table Grid'

    headers = ["ขั้นตอน / เงื่อนไข", "Flow 1: ผ่านการตรวจสอบ", "Flow 2: รออนุมัติ"]
    for i, title in enumerate(headers):
        c = table.cell(0, i)
        set_cell_background(c, "1F4E79")
        set_cell_margins(c, top=100, bottom=100, left=120, right=120)
        p = c.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(title)
        r.font.bold = True
        r.font.color.rgb = RGBColor(255, 255, 255)
        r.font.size = Pt(10)

    rows_data = [
        ("1. การกรองสถานะหน้าหลัก", "กรองตัวเลือก 'ผ่านการตรวจสอบ'", "กรองตัวเลือก 'รออนุมัติ'"),
        ("2. การเปิดรายการ", "คลิก 'ดูรายละเอียด' ในแท็บใหม่", "คลิก 'ดูรายละเอียด' ในแท็บใหม่"),
        ("3. การตรวจสอบเงื่อนไขก่อนทำ", "หากพบ 'ตรวจสอบใบประกาศนียบัตร' อยู่แล้ว -> ปิดแท็บทันที", "ต้องตรวจพบ 3 ข้อความบังคับใน 'ผลการตรวจสอบ' หากไม่ครบ ให้ปิดแท็บทันที"),
        ("4. การกดปุ่มขั้นที่ 1", "กดปุ่ม 'อนุมัติ' ด้านขวาล่าง", "กดปุ่ม 'ผ่านการตรวจสอบ' ด้านขวาล่าง"),
        ("5. การยืนยัน Pop-up ขั้นที่ 1", "กรอก 'อนุมัติ' -> กดยืนยัน", "กรอก 'ผ่านการตรวจสอบ' -> กดยืนยัน"),
        ("6. ขั้นตอนการอนุมัติขั้นที่ 2", "รอขึ้น 'ตรวจสอบใบประกาศนียบัตร' -> ปิดแท็บ", "รอกด 'อนุมัติ' -> Pop-up กรอก 'อนุมัติ' -> รอขึ้น 'ตรวจสอบใบประกาศนียบัตร' -> ปิดแท็บ")
    ]

    for row_idx, (c0, c1, c2) in enumerate(rows_data, start=1):
        bg = "FFFFFF" if row_idx % 2 != 0 else "F2F5F8"
        for col_idx, text in enumerate([c0, c1, c2]):
            c = table.cell(row_idx, col_idx)
            set_cell_background(c, bg)
            set_cell_margins(c, top=80, bottom=80, left=100, right=100)
            p = c.paragraphs[0]
            r = p.add_run(text)
            r.font.size = Pt(9.5)
            if col_idx == 0:
                r.font.bold = True

    doc.add_paragraph().paragraph_format.space_after = Pt(14)

    # ----------------------------------------------------
    # SECTION 3: สถาปัตยกรรมไฟล์และการทำงานแบบ Portable
    # ----------------------------------------------------
    h3 = doc.add_heading(level=1)
    h3_run = h3.add_run("3. สถาปัตยกรรมไฟล์และระบบพกพา (Portable Architecture)")
    h3_run.font.name = 'Sarabun'
    h3_run.font.color.rgb = RGBColor(24, 76, 120)

    p_arch = doc.add_paragraph()
    p_arch.add_run(
        "เพื่อให้โปรแกรมสามารถนำไปรันบนคอมพิวเตอร์เครื่องอื่นได้ทันทีโดยไม่ต้องติดตั้งซอฟต์แวร์เพิ่ม "
        "โครงสร้างโฟลเดอร์ถูกจัดวางให้เป็นแบบ Self-Contained ดังนี้:\n"
    ).font.size = Pt(10)

    arch_items = [
        ("auto_approve.py", "บอท Automation หลัก: ควบคุม Playwright, กรองสถานะ, จัดการแท็บ, ตรวจผลตรวจบัตร และจัดการ Pop-up"),
        ("gui.py", "หน้าต่างโปรแกรม (CustomTkinter GUI): จัดการเมนูเลือก Flow, รับค่าการตั้งค่า, แถบ Live Log, ตัวนับผลงาน และระบบ Threading"),
        ("python_runtime/", "โฟลเดอร์ Python Engine แบบ Portable พร้อมไลบรารีที่จำเป็นครบถ้วน (ขนาดกะทัดรัด ~184 MB)"),
        ("ms-playwright/", "โฟลเดอร์เก็บเบราว์เซอร์ Chromium สำหรับ Automation (ขนาด ~431 MB) ไม่ต้องดาวน์โหลดใหม่"),
        ("browser_profile/", "โฟลเดอร์เก็บคุกกี้และสถานะการเข้าสู่ระบบ (Session) ทำให้ไม่ต้องล็อกอินใหม่ทุกครั้ง"),
        ("run.bat", "สคริปต์เปิดโปรแกรมแบบ One-Click: เรียกใช้ Python Runtime ในโฟลเดอร์โดยตรง ป้องกันข้อผิดพลาดด้านสภาพแวดล้อม")
    ]

    for fname, fdesc in arch_items:
        p_item = doc.add_paragraph(style='List Bullet')
        p_item.paragraph_format.space_after = Pt(2)
        r_fn = p_item.add_run(f"{fname}: ")
        r_fn.font.bold = True
        r_fn.font.size = Pt(10)
        r_fn.font.color.rgb = RGBColor(31, 78, 121)
        r_fd = p_item.add_run(fdesc)
        r_fd.font.size = Pt(10)

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # ----------------------------------------------------
    # SECTION 4: ข้อพิจารณาเชิงเทคนิค (Technical Edge Cases)
    # ----------------------------------------------------
    h4 = doc.add_heading(level=1)
    h4_run = h4.add_run("4. จุดสำคัญและเทคนิคทางโปรแกรม (Key Implementation Techniques)")
    h4_run.font.name = 'Sarabun'
    h4_run.font.color.rgb = RGBColor(24, 76, 120)

    tech_points = [
        ("การจัดการแท็บใหม่ (New Tab Handling):", "ใช้ context.expect_page() หรือตรวจจับแท็ก <a> เพื่อเปิดแท็บใหม่อย่างแม่นยำ และใช้ main_page.bring_to_front() สลับกลับมาหน้าหลักเสมอ"),
        ("การตรวจสอบผลตรวจบัตรประชาชนแบบยืดหยุ่น (Whitespace-Agnostic):", "ทำการ Clean ช่องว่างและเครื่องหมายขึ้นบรรทัดใหม่ก่อนเปรียบเทียบ 3 ข้อความ เพื่อป้องกันปัญหาตัวอักษรไม่ตรงจากโค้ด HTML"),
        ("การหน่วงเวลาและรอการตอบสนองของเซิร์ฟเวอร์ (Wait Assertions):", "แทนที่จะใช้การ sleep แบบคงที่ ให้ใช้การวนลูปตรวจสอบการเปลี่ยนแปลงของปุ่ม 'ตรวจสอบใบประกาศนียบัตร' เพื่อให้บอททำงานได้เร็วที่สุดเท่าที่เซิร์ฟเวอร์จะประมวลผลเสร็จ"),
        ("การป้องกันการล็อกเบราว์เซอร์ (Singleton Lock):", "ใช้ launch_persistent_context ร่วมกับการปิด context.close() อย่างปลอดภัยในบล็อก finally เสมอ")
    ]

    for title, desc in tech_points:
        p_tp = doc.add_paragraph(style='List Bullet')
        p_tp.paragraph_format.space_after = Pt(3)
        r_t = p_tp.add_run(f"{title} ")
        r_t.font.bold = True
        r_t.font.size = Pt(10)
        r_d = p_tp.add_run(desc)
        r_d.font.size = Pt(10)

    # Save document
    doc.save(output_path)
    print(f"Document successfully created at: {output_path}")

if __name__ == "__main__":
    output_file = os.path.join(r"d:\from_c\desktop\app\autoapprove", "AutoApprove_Prompt_Specification.docx")
    create_prompt_document(output_file)
