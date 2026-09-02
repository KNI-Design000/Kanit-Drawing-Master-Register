import os
import pandas as pd
import streamlit as st
from datetime import datetime

# --- Set Page Config ---
st.set_page_config(
    page_title="Kanit Drawing Online",
    page_icon="📐",
    layout="wide"
)

# --- Streamlit GSheets Connection Setup ---
# สำหรับรันแบบ Online บน Streamlit Cloud จะใช้ streamlit-gsheets ในการเชื่อมต่อ
# ผู้ใช้งานต้องใส่ URL ของ Google Sheets ใน Secrets หรือ .streamlit/secrets.toml
# [connections.gsheets]
# spreadsheet = "https://docs.google.com/spreadsheets/d/xxxxxxx/edit"

try:
    from streamlit_gsheets import GSheetsConnection
    # ตรวจสอบว่ามีการเซ็ตอัป Connection หรือไม่
    conn = st.connection("gsheets", type=GSheetsConnection)
    USE_CLOUD = True
except Exception as e:
    USE_CLOUD = False
    st.sidebar.warning("⚠️ ยังไม่ได้ติดตั้งตัวเชื่อมต่อ Google Sheets ออนไลน์ (รันแบบ Local เท่านั้น)")

# --- Dictionary Definitions (ตามมาตรฐาน Kanit Group) ---
COMPANIES = {
    "KNI": "Kanit Industry Co., Ltd. (Trading/Parts)",
    "KNS": "Kanit Seat Co., Ltd. (Train Seat Manufacturing)",
    "KNA": "Kanit Aviation Co., Ltd. (Aviation Parts)",
    "KNM": "Kanit MRO Co., Ltd. (Maintenance, Repair, Overhaul)"
}

PROCESS_CODES = {
    "W": "W - Welding (Permanent Assembly)",
    "N": "N - Non-Permanent Assembly (Bolted/Mechanical)",
    "S": "S - Sheet Metal (Laser/Bent)",
    "M": "M - Machining (Turning/Milling)",
    "C": "C - Casting (Raw Cast parts)",
    "F": "F - Forging (Forged high-stress parts)",
    "E": "E - Extrusion (Profiles/Aluminium)",
    "I": "I - Direct Injection (Rubber/Plastic)",
    "P": "P - 3D Printing/Prototyping",
    "O": "O - Other (Schematics/Wiring Diagrams/Layouts)",
    "STD": "STD - Standard Part (Fasteners, catalog items)"
}

SYSTEMS = {
    "10": "10 - Main Structure/Underframe", "11": "11 - Side Wall / End Wall", "12": "12 - Roof Structure",
    "13": "13 - Skin / External Panels", "14": "14 - Coupler/Buffer/Draft Gear", "15": "15 - Painting/Anti-corrosion",
    "20": "20 - Engine / Prime Mover", "21": "21 - Cooling / Radiator", "22": "22 - Fuel / Exhaust",
    "23": "23 - Traction Motor", "24": "24 - Traction Converter/Inverter", "30": "30 - Power Supply / Wiring",
    "31": "31 - Control/Train Management", "32": "32 - Battery / Auxiliary Power", "33": "33 - Pantograph / Third Rail",
    "34": "34 - Lighting / Signal", "35": "35 - Communication / PIS", "40": "40 - Air Supply / Compressor",
    "41": "41 - Brake Cylinder / Valve", "42": "42 - Brake Disc / Caliper", "43": "43 - Parking / Emergency Brake",
    "50": "50 - Gearbox / Final Drive", "51": "51 - Coupling / Propeller Shaft", "52": "52 - Hydraulic Transmission",
    "60": "60 - HVAC Unit", "61": "61 - Air Duct / Grille", "62": "62 - AC Compressor", "63": "63 - Sanitary / Toilet System",
    "70": "70 - Bogie Frame", "71": "71 - Wheelset / Axle", "72": "72 - Primary Suspension", "73": "73 - Secondary Suspension",
    "74": "74 - Bearing / Axle Box", "80": "80 - Passenger Seat", "81": "81 - Interior Panel/Floor/Ceiling",
    "82": "82 - Passenger Door", "83": "83 - Window", "84": "84 - Handrail / Interior Fittings",
    "85": "85 - Cab / Driver Desk", "90": "90 - Jig / Fixture", "91": "91 - Gauge / Measuring",
    "92": "92 - Lifting / Handling", "99": "99 - Other"
}

MODELS = {
    "ALSD": "ALSD - ALSTOM Locomotive", "HIDD": "HIDD - HITACHI Locomotive", "GEAD": "GEAD - GEA Locomotive",
    "GEDD": "GEDD - GE Locomotive", "CSR2": "CSR2 - CSR SDA3", "CRVD": "CRVD - Changchun EMU",
    "PC24": "PC24 - PC24 Series", "PC25": "PC25 - PC25 Series", "PC26": "PC26 - PC26 Series",
    "KW20": "KW20 - KW20 Model", "KW75": "KW75 - KW75 Model", "DTD0": "DTD0 - DTD09 (Padded)",
    "KHM0": "KHM0 - KHM (Padded)", "KHML": "KHML - KHML Series", "THN0": "THN0 - THN (Padded)",
    "DAED": "DAED - DAEWOO Diesel", "SPRI": "SPRI - SPRING Locomotive", "ERQI": "ERQI - ERQI Series",
    "1120": "1120 - ETC 1120", "308D": "308D - 308D Model", "QSY5": "QSY5 - CRRC CDA5B1 (QSY)",
    "IBLC": "IBLC - Siemens Modular Metro (EMU-IBL) Blue Line 1", 
    "BLEC": "BLEC - Siemens Modular Metro (EMU-BLE) Blue Line Ext",
    "BLEX": "BLEX - Siemens Blue Line (Add-on)", "S24D": "S24D - J-TREC Sustina (Purple Line)",
    "ORLC": "ORLC - Siemens EMU 3 (Orange Line)", "PATS": "PATS - Alstom Innovia 300 (Pink Line)",
    "YMEM": "YMEM - Alstom Innovia 300 (Yellow Line)", "SIA1": "SIA1 - EMU-B1 Green Line (Siemens)",
    "SIA2": "SIA2 - EMU-B2 Green Line (CNR)", "CRB3": "CRB3 - EMU-B3 Green Line (CRRC)",
    "APM3": "APM3 - Bombardier APM 300 (Gold Line)", "ARLX": "ARLX - Siemens Desiro Class 360",
    "AT10": "AT10 - Hitachi AT100 (Red Line)"
}

# --- Load and Save Google Sheets Data ---
def load_data():
    if not USE_CLOUD:
        return pd.DataFrame()
    try:
        # โหลดข้อมูลจาก Sheet แรก (ตั้งชื่อเป็น 'Master Register' หรือใช้ Sheet1)
        df = conn.read(ttl="5s") # ดึงข้อมูลอัปเดตสุดภายใน 5 วินาที
        df = df.dropna(how='all')
        return df
    except Exception as e:
        st.error(f"❌ ดึงข้อมูลจาก Google Sheets ไม่สำเร็จ: {e}")
        return pd.DataFrame()

def save_data(df):
    if not USE_CLOUD:
        return False, "ระบบไม่ได้เชื่อมต่อแบบ Cloud"
    try:
        # บันทึกข้อมูลกลับไปยัง Google Sheets
        conn.update(data=df)
        return True, "บันทึกลง Google Sheets เรียบร้อยแล้ว!"
    except Exception as e:
        return False, f"เขียนข้อมูลลง Google Sheets ผิดพลาด: {e}"

# --- Validation Rules ---
def validate_drawing_number_parts(ccc, mmmm, ss, aa, bb, nnn, c):
    if ccc not in COMPANIES:
        return False, f"ไม่พบรหัสบริษัท '{ccc}' ในระบบ"
    if len(mmmm) != 4 or not mmmm.isalnum():
        return False, f"รหัสรุ่นรถไฟ '{mmmm}' ต้องมีความยาว 4 ตัวอักษร"
    if ss not in SYSTEMS:
        return False, f"ไม่พบรหัสระบบย่อย '{ss}' ในระบบ EN 15380-2"
    if len(aa) != 2 or not aa.isdigit():
        return False, "รหัส Master Assembly [AA] ต้องเป็นตัวเลข 2 หลัก (00-99)"
    if len(bb) != 2 or not bb.isdigit():
        return False, "รหัส Sub-Assembly [BB] ต้องเป็นตัวเลข 2 หลัก (00-99)"
    if aa == "00" and bb != "00":
        return False, "กฎ BOM: เมื่อระบุเป็นชิ้นส่วนเดี่ยว (AA = 00) รหัส Sub-Assembly (BB) ต้องเป็น 00 อัตโนมัติ"
    if len(nnn) != 3 or not nnn.isdigit():
        return False, "รหัสลำดับชิ้นส่วน [NNN] ต้องเป็นตัวเลข 3 หลัก (000-999)"
    if c not in PROCESS_CODES:
        return False, f"ไม่พบรหัสกรรมวิธีการผลิต '{c}' ในระบบ"
    return True, ""

# --- App UI Layout ---
st.title("📐 Kanit Group Online Drawing Registry (Google Sheets Cloud)")
st.markdown("ระบบลงทะเบียนและตรวจสอบรหัสแบบเขียนรถไฟของ Kanit Group ผ่านระบบออนไลน์ที่เชื่อมต่อกับ **Google Sheets** แบบเรียลไทม์")

if not USE_CLOUD:
    st.error("🔌 **ต้องการการตั้งค่าเบื้องต้น:** เพื่อรันระบบ Cloud ร่วมกับ Google Sheets กรุณาอ่านคำแนะนำในคู่มือวิธีเชื่อมต่อเบื้องหลัง")
    st.stop()

# Load Database
df_db = load_data()

# --- Tab Layout ---
tab_register, tab_database = st.tabs([
    "✍️ ลงทะเบียนแบบเขียนใหม่ (Quick Register)",
    "📊 ทะเบียนออนไลน์ (Live Database & Dashboard)"
])

with tab_register:
    st.header("✍️ ลงทะเบียนแบบง่าย (ระบบรันเลขให้อัตโนมัติ)")
    st.write("ระบุข้อมูลเพื่อเลือกและคำนวณรหัส Drawing อัตโนมัติ")

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("ส่วนที่ 1-3: ข้อมูลรถไฟ")
        comp_sel = st.selectbox("บริษัทเจ้าของแบบ (CCC):", list(COMPANIES.keys()), format_func=lambda x: f"{x} - {COMPANIES[x]}")
        model_sel = st.selectbox("รุ่นรถไฟ (MMMM):", list(MODELS.keys()), format_func=lambda x: MODELS[x])
        system_sel = st.selectbox("ระบบเทคนิค EN 15380-2 (SS):", list(SYSTEMS.keys()), format_func=lambda x: SYSTEMS[x])
        
        st.subheader("ส่วนที่ 4-6: โครงสร้างประกอบ (BOM)")
        part_type = st.radio(
            "ประเภทชิ้นงานที่ต้องการลงทะเบียน:",
            ["ชิ้นส่วนเดี่ยวแยกอิสระ (Single Part) -> [AA=00, BB=00]", 
             "ชุดประกอบหลักใหม่ (New Master Assembly) -> [BB=00, NNN=000]",
             "ชิ้นส่วนย่อยในชุดประกอบ (Component)"]
        )
        
        # ค้นหาเลขรันอัตโนมัติจาก Google Sheets
        aa_val, bb_val, nnn_val = "00", "00", "001"
        is_override = st.checkbox("🔓 ต้องการแก้ไขตัวเลขชุดรหัสด้วยตนเอง (Manual Override)")
        
        if not is_override and not df_db.empty:
            # วิเคราะห์ข้อมูลในตารางเพื่อหาเลขล่าสุด
            # กรองเฉพาะโครงการและระบบปัจจุบัน
            try:
                # แปลงหัวตารางให้เป็นสตริงเผื่อกรณีกระทบหัวข้อ
                df_filtered = df_db[
                    (df_db['Company (CCC)'].astype(str) == comp_sel) & 
                    (df_db['Model (MMMM)'].astype(str) == model_sel) & 
                    (df_db['System (SS)'].astype(str) == system_sel)
                ]
                
                if "Single Part" in part_type:
                    aa_val, bb_val = "00", "00"
                    single_parts = df_filtered[(df_filtered['Master (AA)'].astype(str) == "00")]
                    if not single_parts.empty:
                        last_nnn = pd.to_numeric(single_parts['Part No. (NNN)'], errors='coerce').max()
                        nnn_val = str(int(last_nnn) + 1).zfill(3) if not pd.isna(last_nnn) else "001"
                    else:
                        nnn_val = "001"
                        
                elif "Master Assembly" in part_type:
                    master_parts = df_db[(df_db['Model (MMMM)'].astype(str) == model_sel) & (df_db['System (SS)'].astype(str) == system_sel) & (df_db['Master (AA)'].astype(str) != "00")]
                    if not master_parts.empty:
                        last_aa = pd.to_numeric(master_parts['Master (AA)'], errors='coerce').max()
                        aa_val = str(int(last_aa) + 1).zfill(2) if not pd.isna(last_aa) else "01"
                    else:
                        aa_val = "01"
                    bb_val, nnn_val = "00", "000"
                    
                else: # Component
                    # ดึงชุดประกอบหลักที่มีอยู่
                    masters = df_db[(df_db['Model (MMMM)'].astype(str) == model_sel) & (df_db['System (SS)'].astype(str) == system_sel) & (df_db['Master (AA)'].astype(str) != "00")]['Master (AA)'].unique()
                    if len(masters) > 0:
                        aa_sel = st.selectbox("เลือกชุดประกอบหลักอ้างอิง [AA]:", sorted(list(masters)))
                        aa_val = aa_sel
                        
                        # ค้นหารหัสย่อย BB
                        sub_parts = df_db[(df_db['Model (MMMM)'].astype(str) == model_sel) & (df_db['System (SS)'].astype(str) == system_sel) & (df_db['Master (AA)'].astype(str) == aa_sel)]
                        if not sub_parts.empty:
                            last_bb = pd.to_numeric(sub_parts['Sub (BB)'], errors='coerce').max()
                            bb_val = str(int(last_bb) + 1).zfill(2) if not pd.isna(last_bb) else "01"
                        else:
                            bb_val = "01"
                        nnn_val = "001" # เริ่มชิ้นส่วนแรกในชุดย่อย
                    else:
                        st.warning("⚠️ ไม่พบชุดประกอบหลัก กรุณาสร้าง Master Assembly ก่อน หรือ ติ๊ก Override ด้านบนเพื่อคีย์มือ")
            except Exception as e:
                st.caption(f"ระบบรันเลขว่าง: {e}")
        
        # แสดงผลและรับค่ากรณีกดแมนนวลคีย์
        if is_override:
            aa_val = st.text_input("รหัสชุดประกอบหลัก [AA] (2 หลัก):", value=aa_val, max_chars=2)
            bb_val = st.text_input("รหัสชุดประกอบย่อย [BB] (2 หลัก):", value=bb_val, max_chars=2)
            nnn_val = st.text_input("ลำดับชิ้นส่วน [NNN] (3 หลัก):", value=nnn_val, max_chars=3)
        else:
            st.info(f"🤖 ระบบคำนวณรหัสปัจจุบันให้อัตโนมัติ: **[AA={aa_val}, BB={bb_val}, NNN={nnn_val}]**")

    with col2:
        st.subheader("ส่วนที่ 7: กรรมวิธีผลิตและรายละเอียดเอกสาร")
        process_sel = st.selectbox("กรรมวิธีการผลิต / ชิ้นส่วนมาตรฐาน (C):", list(PROCESS_CODES.keys()), format_func=lambda x: PROCESS_CODES[x])
        drawing_title = st.text_input("ชื่อภาษาไทย/อังกฤษของชิ้นงาน (Drawing Title) *จำเป็น*:", placeholder="เช่น Cushion Frame Base")
        engineer_name = st.text_input("ชื่อวิศวกรผู้รับผิดชอบ (Responsible Engineer):", placeholder="เช่น K. Viput")
        rev_val = st.text_input("รุ่นแก้ไข (Revision):", value="A", max_chars=3)
        status_sel = st.selectbox("สถานะแบบ:", ["Draft", "Under Review", "Approved", "Obsolete"])
        remarks_val = st.text_area("หมายเหตุการสั่งผลิต (Remarks):", placeholder="เช่น หนา 1.5 มม.")

    st.markdown("---")
    
    # Live preview
    aa_clean = aa_val.strip().zfill(2) if aa_val.strip().isdigit() else "00"
    bb_clean = bb_val.strip().zfill(2) if bb_val.strip().isdigit() else "00"
    nnn_clean = nnn_val.strip().zfill(3) if nnn_val.strip().isdigit() else "001"
    
    full_code = f"{comp_sel}-{model_sel}-{system_sel}-{aa_clean}-{bb_clean}-{nnn_clean}-{process_sel}"
    st.subheader("🔍 พรีวิวรหัส Drawing อัตโนมัติ")
    st.info(f"### รหัสที่จะถูกส่งบันทึก: `{full_code}`")
    
    is_valid, err_msg = validate_drawing_number_parts(comp_sel, model_sel, system_sel, aa_clean, bb_clean, nnn_clean, process_sel)
    if not is_valid:
        st.error(f"⚠️ โครงสร้างรหัสขัดข้อง: {err_msg}")
    else:
        st.success("✅ รหัสถูกต้องตรงตามข้อกำหนดทางวิศวกรรมของ Kanit Group (Draft 1)")

    if st.button("💾 ยืนยันบันทึกข้อมูลลง Google Sheets ออนไลน์", disabled=not is_valid):
        if not drawing_title.strip():
            st.warning("⚠️ กรุณากรอก 'ชื่อชิ้นงาน' ก่อนกดยืนยัน")
        else:
            with st.spinner("กำลังเขียนข้อมูลลง Google Sheets บนระบบคลาวด์..."):
                # สร้างแถวใหม่
                new_row = {
                    "No.": len(df_db) + 1,
                    "Company (CCC)": comp_sel,
                    "Model (MMMM)": model_sel,
                    "System (SS)": system_sel,
                    "Master (AA)": aa_clean,
                    "Sub (BB)": bb_clean,
                    "Part No. (NNN)": nnn_clean,
                    "Process (C)": process_sel,
                    "Full Drawing Number": full_code,
                    "Drawing Title (Part Name)": drawing_title.strip(),
                    "Rev": rev_val.strip().upper(),
                    "Status": status_sel,
                    "Engineer": engineer_name.strip(),
                    "Date Created": datetime.now().strftime("%Y-%m-%d"),
                    "Remarks": remarks_val.strip()
                }
                
                # อัปเดต Dataframe
                df_updated = pd.concat([df_db, pd.DataFrame([new_row])], ignore_index=True)
                success, msg = save_data(df_updated)
                
                if success:
                    st.balloons()
                    st.success("🎉 บันทึกแบบเขียนออนไลน์เรียบร้อยแล้ว!")
                    st.experimental_rerun()
                else:
                    st.error(msg)

# --- Tab 2: Live Database & Dashboard ---
with tab_database:
    st.header("📊 ตารางทะเบียนหลักคลาวด์ออนไลน์ (Live Google Sheets)")
    
    if df_db.empty:
        st.warning("📭 ยังไม่มีข้อมูลบันทึกในตารางขณะนี้")
    else:
        # KPI Cards
        total_drawings = len(df_db)
        approved_count = len(df_db[df_db['Status'].astype(str).str.contains("Approved", case=False, na=False)])
        draft_count = len(df_db[df_db['Status'].astype(str).str.contains("Draft", case=False, na=False)])
        
        col_k1, col_k2, col_k3 = st.columns(3)
        col_k1.metric("📐 แบบเขียนออนไลน์รวม", f"{total_drawings} รายการ")
        col_k2.metric("🟢 อนุมัติแล้ว (Approved)", approved_count)
        col_k3.metric("🔵 แบบร่างค้างอยู่ (Draft)", draft_count)
        
        st.markdown("---")
        
        # Search block
        search_q = st.text_input("🔍 พิมพ์ค้นหาด่วน (เช่น ชื่อแบบเขียน, รหัส, ชื่อวิศวกร):", placeholder="เช่น Seat, KNS, Viput...")
        
        display_df = df_db.copy()
        if search_q:
            mask = display_df.astype(str).apply(lambda x: x.str.contains(search_q, case=False, na=False)).any(axis=1)
            display_df = display_df[mask]
            st.caption(f"🎯 ค้นพบ {len(display_df)} รายการจากคำค้นหา '{search_q}'")
            
        st.dataframe(display_df, use_container_width=True)
        st.caption("ข้อมูลด้านบนนี้ถูกดึงและ Sync ตรงกับ Google Sheets ออนไลน์เบื้องหลัง")
