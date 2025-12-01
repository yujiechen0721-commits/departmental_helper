import streamlit as st

# 隱藏右上角 GitHub + Fork 按鈕
hide_menu_style = """
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display:none;}
    </style>
    """
st.markdown(hide_menu_style, unsafe_allow_html=True)

import pandas as pd
import plotly.graph_objects as go
from collections import defaultdict
import os
from datetime import datetime

# 頁面設定
st.set_page_config(page_title="課程選課系統", layout="wide", initial_sidebar_state="expanded")
st.title("📚 課程選課系統")

# 設定課程資料檔案路徑
COURSE_FILE = "1141scu_courses.csv"  # 請修改為你的檔案路徑

# 時間節次對應表
TIME_SLOTS = {
    '1': '08:10-09:00',
    '2': '09:10-10:00',
    '3': '10:10-11:00',
    '4': '11:10-12:00',
    '5': '12:10-13:00',
    '6': '13:10-14:00',
    '7': '14:10-15:00',
    '8': '15:10-16:00',
    '9': '16:10-17:00',
    'A': '17:10-18:00',
    'B': '18:10-19:00',
    'C': '19:10-20:00',
    'D': '20:10-21:00',
}

# 星期對應
WEEKDAY_MAP = {
    '一': 'Monday',
    '二': 'Tuesday',
    '三': 'Wednesday',
    '四': 'Thursday',
    '五': 'Friday',
    '六': 'Saturday',
    '日': 'Sunday',
}

WEEKDAY_ORDER = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

# 中文星期對應
WEEKDAY_CHINESE = {
    'Monday': '星期一',
    'Tuesday': '星期二',
    'Wednesday': '星期三',
    'Thursday': '星期四',
    'Friday': '星期五',
    'Saturday': '星期六',
    'Sunday': '星期日',
}

@st.cache_data
def load_courses(file_path):
    """載入課程資料"""
    if not os.path.exists(file_path):
        st.error(f"找不到課程資料檔案: {file_path}")
        return None
    
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
    except:
        try:
            df = pd.read_csv(file_path, encoding='big5')
        except Exception as e:
            st.error(f"讀取檔案失敗: {e}")
            return None
    
    # 確保必要欄位存在
    required_cols = ['系所', '科目名稱', '星期', '節次', '授課教師', '教室']
    for col in required_cols:
        if col not in df.columns:
            st.error(f"CSV檔案缺少必要欄位: {col}")
            return None
    
    return df

def parse_time_slots(slots_str):
    """解析節次字串,例如 '34' -> ['3', '4']"""
    if pd.isna(slots_str):
        return []
    return list(str(slots_str))

def check_conflicts(selected_courses_data, code_column=None):
    """檢查課程衝突，返回詳細的衝突資訊"""
    conflicts = []
    schedule_map = defaultdict(list)  # {(星期, 節次): [課程資料]}
    
    for idx, course in selected_courses_data.iterrows():
        weekday = course['星期']
        slots = parse_time_slots(course['節次'])
        
        for slot in slots:
            key = (weekday, slot)
            if schedule_map[key]:
                # 與已存在的課程產生衝突
                for existing_course in schedule_map[key]:
                    conflict_info = {
                        '衝突時間': f"{weekday} 第{slot}節 ({TIME_SLOTS.get(slot, '')})",
                        '課程1': existing_course['科目名稱'],
                        '課程1教師': existing_course['授課教師'],
                        '課程1系所': existing_course['系所'],
                        '課程1教室': existing_course['教室'],
                        '課程2': course['科目名稱'],
                        '課程2教師': course['授課教師'],
                        '課程2系所': course['系所'],
                        '課程2教室': course['教室'],
                    }
                    
                    # 如果有科目代碼欄位，也加入（使用偵測到的欄位名稱）
                    if code_column and code_column in existing_course and code_column in course:
                        conflict_info[f'課程1{code_column}'] = existing_course[code_column]
                        conflict_info[f'課程2{code_column}'] = course[code_column]
                    
                    conflicts.append(conflict_info)
            
            # 將當前課程加入排程
            schedule_map[key].append(course)
    
    return conflicts

def wrap_text(text, max_length=10):
    """文字自動換行，每 max_length 個字元插入換行"""
    if pd.isna(text) or text == '':
        return ''
    
    text = str(text)
    if len(text) <= max_length:
        return text
    
    # 每 max_length 個字元換行
    wrapped = '<br>'.join([text[i:i+max_length] for i in range(0, len(text), max_length)])
    return wrapped

def draw_schedule_table(selected_courses_data, show_weekend=False):
    """繪製課表 - 固定顯示週一到週五（或週日），優化版面配置"""
    # 建立課表資料結構
    schedule = defaultdict(lambda: defaultdict(list))
    
    for idx, course in selected_courses_data.iterrows():
        weekday = WEEKDAY_MAP.get(course['星期'], course['星期'])
        slots = parse_time_slots(course['節次'])
        
        # 課程資訊，使用自動換行
        course_name = wrap_text(course['科目名稱'], max_length=12)
        teacher = wrap_text(course['授課教師'], max_length=10)
        room = wrap_text(course['教室'], max_length=10)
        
        course_info = f"<b>{course_name}</b><br>{teacher}<br>{room}"
        
        for slot in slots:
            if slot in TIME_SLOTS:
                schedule[slot][weekday].append(course_info)
    
    # 固定顯示週一到週五（如果需要也可包含週末）
    if show_weekend:
        weekdays_to_show = WEEKDAY_ORDER
    else:
        weekdays_to_show = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    
    # 確定要顯示的節次 - 如果有任何課程就顯示該節次
    used_slots = set()
    for slot in schedule.keys():
        used_slots.add(slot)
    
    # 如果沒有選課，顯示常用節次
    if not used_slots:
        all_slots = ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D']
    else:
        all_slots = sorted(list(used_slots), key=lambda x: (x.isalpha(), x))
    
    # 準備表格資料 - 按欄位組織
    header_values = ['節次', '時間'] + [WEEKDAY_CHINESE[day] for day in weekdays_to_show]
    
    # 建立每一欄的資料
    slot_col = all_slots
    time_col = [TIME_SLOTS[slot] for slot in all_slots]
    
    # 建立每個星期的欄位資料
    weekday_cols = []
    for day in weekdays_to_show:
        day_data = []
        for slot in all_slots:
            if schedule[slot][day]:
                # 如果有多個課程,用分隔線隔開
                day_data.append('<br>━━━━━<br>'.join(schedule[slot][day]))
            else:
                day_data.append('')
        weekday_cols.append(day_data)
    
    # 組合所有欄位
    cell_values = [slot_col, time_col] + weekday_cols
    
    # 計算欄位寬度比例
    num_weekdays = len(weekdays_to_show)
    # 節次和時間欄較窄，其他欄位平均分配
    column_widths = [0.06, 0.10] + [0.84 / num_weekdays] * num_weekdays
    
    # 建立表格 - 改用白底，並優化版面配置
    fig = go.Figure()
    
    fig.add_trace(go.Table(
        columnwidth=column_widths,
        header=dict(
            values=header_values,
            fill_color='#4A90E2',
            align='center',
            font=dict(size=15, color='white', family='Microsoft JhengHei, Arial'),
            height=45
        ),
        cells=dict(
            values=cell_values,
            fill_color='white',
            align='center',
            font=dict(size=12, family='Microsoft JhengHei, Arial'),
            height=80,  # 增加高度以容納換行的文字
            line=dict(color='#ddd', width=1)
        )
    ))
    
    # 根據節次數量動態調整高度
    table_height = max(500, len(all_slots) * 80 + 100)
    
    fig.update_layout(
        title={
            'text': "📅 課程時間表",
            'font': {'size': 20, 'family': 'Microsoft JhengHei, Arial'},
            'x': 0.5,
            'xanchor': 'center'
        },
        height=table_height,
        width=1400,  # 固定寬度，確保完整顯示
        margin=dict(l=20, r=20, t=60, b=20),
        paper_bgcolor='white',
        plot_bgcolor='white'
    )
    
    return fig

def check_kaleido_available():
    """檢查 kaleido 是否可用"""
    try:
        import kaleido
        return True
    except ImportError:
        return False

def convert_to_csv_for_excel(df):
    """轉換 DataFrame 為適合 Excel 開啟的 CSV 格式"""
    # 使用 UTF-8 with BOM 編碼，Excel 可以正確識別
    return df.to_csv(index=False, encoding='utf-8-sig')

# 自訂 CSS 讓側邊欄更寬
st.markdown("""
    <style>
    [data-testid="stSidebar"][aria-expanded="true"]{
        min-width: 450px;
        max-width: 450px;
    }
    </style>
    """, unsafe_allow_html=True)

# 主程式
# 讀取本地端課程資料
df = load_courses(COURSE_FILE)

if df is not None:
    # 檢測科目代碼欄位
    code_column_names = ['科目代碼', '課程代碼', '課號', 'course_code', 'code']
    detected_code_column = None
    
    for col_name in code_column_names:
        if col_name in df.columns:
            detected_code_column = col_name
            break
    
    # 顯示載入資訊
    if detected_code_column:
        st.success(f"✅ 成功載入 {len(df)} 筆課程資料 (檔案: {COURSE_FILE})  |  偵測到科目代碼欄位: **{detected_code_column}**")
    else:
        st.success(f"✅ 成功載入 {len(df)} 筆課程資料 (檔案: {COURSE_FILE})")
        st.info("ℹ️ 未偵測到科目代碼欄位，搜尋功能將僅搜尋課程名稱")
    
    # 側邊欄:搜尋和選擇課程
    st.sidebar.header("🔍 快速搜尋課程")
    
    # 搜尋框
    search_query = st.sidebar.text_input(
        "輸入課程名稱或科目代碼",
        placeholder="例如：微積分、CS101",
        help="支援模糊搜尋，會搜尋課程名稱和科目代碼"
    )
    
    # 儲存選中的課程
    if 'selected_courses' not in st.session_state:
        st.session_state.selected_courses = []
    
    # 如果有搜尋內容，顯示搜尋結果
    if search_query:
        st.sidebar.subheader("📋 搜尋結果")
        
        # 搜尋邏輯：在課程名稱和科目代碼中查找
        search_mask = df['科目名稱'].str.contains(search_query, case=False, na=False)
        
        # 如果找到科目代碼欄位，也加入搜尋
        if detected_code_column:
            search_mask = search_mask | df[detected_code_column].astype(str).str.contains(search_query, case=False, na=False)
        
        search_results = df[search_mask]
        
        if len(search_results) > 0:
            st.sidebar.success(f"找到 {len(search_results)} 門課程")
            
            # 初始化搜尋選擇的 session state
            if 'search_selection' not in st.session_state:
                st.session_state.search_selection = []
            
            # 建立搜尋結果的選項
            search_options = {}
            for idx, row in search_results.iterrows():
                # 組合顯示資訊 - 使用檢測到的科目代碼欄位
                code_info = ""
                if detected_code_column and detected_code_column in row and pd.notna(row[detected_code_column]):
                    code_info = f"[{row[detected_code_column]}] "
                
                class_info = f"[{row['班級']}] " if pd.notna(row['班級']) else ""
                dept_info = f"({row['系所']})"
                time_info = f"{row['星期']}{row['節次']}"
                
                option_text = f"{code_info}{class_info}{row['科目名稱']} {dept_info}\n👨‍🏫 {row['授課教師']} | ⏰ {time_info}"
                search_options[option_text] = idx
            
            # 顯示搜尋結果並允許選擇
            selected_from_search = st.sidebar.multiselect(
                "從搜尋結果中選擇課程",
                options=list(search_options.keys()),
                default=st.session_state.search_selection,
                key="search_results_selector"
            )
            
            # 更新 session state
            st.session_state.search_selection = selected_from_search
            
            # 加入選課按鈕
            col1, col2 = st.sidebar.columns([1, 1])
            with col1:
                if st.button("➕ 加入選課", use_container_width=True, disabled=len(selected_from_search)==0):
                    added_count = 0
                    for option in selected_from_search:
                        idx = search_options[option]
                        if idx not in st.session_state.selected_courses:
                            st.session_state.selected_courses.append(idx)
                            added_count += 1
                    
                    if added_count > 0:
                        st.sidebar.success(f"✅ 已加入 {added_count} 門課程")
                    else:
                        st.sidebar.info("ℹ️ 所選課程已在選課清單中")
                    
                    # 清空選擇
                    st.session_state.search_selection = []
                    st.rerun()
            
            with col2:
                if st.button("🔄 清除選擇", use_container_width=True, disabled=len(selected_from_search)==0):
                    st.session_state.search_selection = []
                    st.rerun()
        else:
            st.sidebar.warning(f"找不到符合「{search_query}」的課程")
    
    st.sidebar.markdown("---")
    st.sidebar.header("📚 按系所選擇課程")
    
    # 取得所有系所
    departments = sorted(df['系所'].unique())
    selected_depts = st.sidebar.multiselect("選擇學系", departments)
    
    if selected_depts:
        # 根據選擇的系所篩選課程
        filtered_df = df[df['系所'].isin(selected_depts)]
        
        for dept in selected_depts:
            st.sidebar.subheader(f"📖 {dept}")
            
            # 取得該系所的所有班級
            dept_data = df[df['系所'] == dept]
            classes = sorted(dept_data['班級'].dropna().unique())
            
            if len(classes) > 0:
                selected_classes = st.sidebar.multiselect(
                    f"選擇{dept}的班級",
                    options=classes,
                    key=f"class_{dept}"
                )
                
                if selected_classes:
                    # 根據選擇的班級篩選課程
                    dept_courses = dept_data[dept_data['班級'].isin(selected_classes)]
                else:
                    # 如果沒有選擇班級,顯示該系所所有課程
                    dept_courses = dept_data
            else:
                # 如果該系所沒有班級資料,顯示所有課程
                dept_courses = dept_data
            
            # 建立課程選項 (包含更多資訊)
            course_options = {}
            for idx, row in dept_courses.iterrows():
                class_info = f"[{row['班級']}]" if pd.notna(row['班級']) else ""
                course_key = f"{class_info}{row['科目名稱']} ({row['授課教師']}) - {row['星期']}{row['節次']}"
                course_options[course_key] = idx
            
            if course_options:
                selected = st.sidebar.multiselect(
                    f"選擇課程",
                    options=list(course_options.keys()),
                    key=f"course_{dept}"
                )
                
                # 更新選中的課程
                for course_key in selected:
                    idx = course_options[course_key]
                    if idx not in st.session_state.selected_courses:
                        st.session_state.selected_courses.append(idx)
            else:
                st.sidebar.info(f"{dept} 沒有符合條件的課程")
    
    # 清除選課按鈕
    if st.sidebar.button("🗑️ 清除所有選課"):
        st.session_state.selected_courses = []
        st.rerun()
    
    # 顯示已選課程
    if st.session_state.selected_courses:
        st.header("已選課程")
        selected_data = df.loc[st.session_state.selected_courses]
        
        # 顯示課程列表
        display_cols = ['科目名稱', '系所', '班級', '授課教師', '星期', '節次', '學分數', '教室']
        
        # 如果有科目代碼欄位也顯示（使用偵測到的欄位名稱）
        if detected_code_column and detected_code_column in selected_data.columns:
            display_cols = [detected_code_column] + display_cols
        
        # 只顯示存在的欄位
        display_cols = [col for col in display_cols if col in selected_data.columns]
        st.dataframe(selected_data[display_cols], use_container_width=True)
        
        # 檢查衝突
        st.header("⚠️ 衝突檢測")
        conflicts = check_conflicts(selected_data, code_column=detected_code_column)
        
        if conflicts:
            st.error(f"發現 {len(conflicts)} 個課程時間衝突!")
            conflict_df = pd.DataFrame(conflicts)
            st.dataframe(conflict_df, use_container_width=True)
        else:
            st.success("✅ 沒有課程時間衝突!")
        
        # 繪製課表
        st.header("📅 課程表")
        
        # 選擇是否顯示週末
        show_weekend = st.checkbox("顯示週末", value=False)
        
        fig = draw_schedule_table(selected_data, show_weekend=show_weekend)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        
        # 統計資訊
        st.header("📊 統計資訊")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("已選課程數", len(selected_data))
        with col2:
            total_credits = selected_data['學分數'].sum() if '學分數' in selected_data.columns else 0
            st.metric("總學分數", total_credits)
        with col3:
            st.metric("涉及系所", selected_data['系所'].nunique())
        
        # 匯出功能
        st.header("💾 匯出課表")
        
        col_export1, col_export2, col_export3 = st.columns(3)
        
        with col_export1:
            # CSV 匯出 - 修正編碼問題
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_data = convert_to_csv_for_excel(selected_data)
            st.download_button(
                label="📥 下載課表 CSV (Excel)",
                data=csv_data,
                file_name=f"我的課表_{timestamp}.csv",
                mime="text/csv",
                help="UTF-8 with BOM 編碼，Excel 可直接開啟",
                use_container_width=True
            )
        
        with col_export2:
            # HTML 互動式課表匯出（不需要 kaleido）
            if fig:
                html_string = fig.to_html(include_plotlyjs='cdn')
                st.download_button(
                    label="🌐 下載互動式課表 (HTML)",
                    data=html_string,
                    file_name=f"我的課表_{timestamp}.html",
                    mime="text/html",
                    help="可在瀏覽器中開啟的互動式課表",
                    use_container_width=True
                )
        
        with col_export3:
            # 課表圖片匯出（需要 kaleido）
            if fig:
                if check_kaleido_available():
                    try:
                        img_bytes = fig.to_image(
                            format="png", 
                            width=1600, 
                            height=max(700, len(fig.data[0].cells.values[0]) * 80 + 150)
                        )
                        st.download_button(
                            label="🖼️ 下載課表圖片 (PNG)",
                            data=img_bytes,
                            file_name=f"我的課表_{timestamp}.png",
                            mime="image/png",
                            help="高解析度課表圖片，適合列印",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"圖片匯出失敗: {e}")
                        st.info("提示：可改用 HTML 格式後，在瀏覽器中截圖")
                else:
                    st.info("💡 安裝 kaleido 以啟用 PNG 匯出")
                    with st.expander("查看安裝說明"):
                        st.code("pip install kaleido", language="bash")
                        st.markdown("或使用 conda：")
                        st.code("conda install -c conda-forge python-kaleido", language="bash")
        
        # 完成排課確認
        st.markdown("---")
        if st.button("✅ 確認完成排課", type="primary", use_container_width=True):
            st.success("🎉 排課完成！你的課表已經準備好了。")
            st.balloons()
            
            # 顯示課表摘要
            with st.expander("📋 查看課表摘要", expanded=True):
                st.write(f"**總共選擇:** {len(selected_data)} 門課程")
                st.write(f"**總學分數:** {total_credits} 學分")
                st.write(f"**涉及系所:** {', '.join(selected_data['系所'].unique())}")
                if conflicts:
                    st.warning(f"⚠️ 注意：仍有 {len(conflicts)} 個時間衝突需要解決")
                else:
                    st.success("✅ 無時間衝突")
    
    else:
        st.info("👈 請從左側選單選擇課程")
        st.markdown("""
        ### 使用說明
        
        #### 🔍 快速搜尋
        - 在搜尋框中輸入**課程名稱**或**科目代碼**
        - 支援**模糊搜尋**，輸入關鍵字即可
        - 從搜尋結果中選擇課程後，點擊「➕ 加入選課」按鈕
        
        #### 📚 按系所瀏覽
        1. 在左側邊欄選擇「學系」
        2. 選擇「班級」（可選）
        3. 選擇想要的「課程」
        
        #### ✅ 其他功能
        - 系統會自動檢測課程衝突
        - 查看課表並可匯出 CSV、HTML 或圖片
        
        ### 匯出格式說明
        - **CSV (Excel)**: 使用 UTF-8 BOM 編碼，Excel 可直接開啟無亂碼
        - **HTML**: 互動式課表，可在瀏覽器中開啟、放大檢視
        - **PNG**: 高解析度圖片格式，適合列印或分享（需安裝 kaleido）
        
        ### 💡 搜尋小技巧
        - 搜尋「微積分」會找到所有包含微積分的課程
        - 搜尋「CS」會找到所有課程代碼包含 CS 的課程
        - 搜尋結果會顯示課程代碼、名稱、教師、時間等完整資訊
        - **記得選擇後要點擊「➕ 加入選課」按鈕才會加入課表！**
        """)

else:
    st.error("❌ 無法載入課程資料")
    st.markdown(f"""
    請確認:
    1. 課程資料檔案 `{COURSE_FILE}` 存在於程式執行目錄
    2. 檔案格式正確,包含必要欄位:系所、科目名稱、星期、節次、授課教師、教室
    
    你可以在程式碼中修改 `COURSE_FILE` 變數來指定正確的檔案路徑。
    """)
