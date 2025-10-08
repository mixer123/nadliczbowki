import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder
import calendar
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

# 🔤 Ustawienia polskich znaków
pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))

# -------------------------
# Inicjalizacja session_state
# -------------------------
if "df" not in st.session_state:
    st.session_state["df"] = None
if "pensum_global" not in st.session_state:
    st.session_state["pensum_global"] = 3.6
if "wyplata" not in st.session_state:
    st.session_state["wyplata"] = 0.0
if "pn" not in st.session_state: st.session_state["pn"] = 0.0
if "wt" not in st.session_state: st.session_state["wt"] = 0.0
if "sr" not in st.session_state: st.session_state["sr"] = 0.0
if "czw" not in st.session_state: st.session_state["czw"] = 0
if "pt" not in st.session_state: st.session_state["pt"] = 0.0
if "pdf_ready" not in st.session_state: st.session_state["pdf_ready"] = None
if "form_version" not in st.session_state: st.session_state["form_version"] = 0  # 👈 licznik wersji formularza

# --- Style PDF ---
style_normal = ParagraphStyle(name='Normal', fontName='DejaVuSans', fontSize=11, leading=14)
style_title = ParagraphStyle(name='Title', fontName='DejaVuSans', fontSize=16, leading=20, alignment=1)

# -------------------------
# UI
# -------------------------
st.title("📘 Wykaz zrealizowanych godzin")

month_name = ["styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec",
              "lipiec", "sierpień", "wrzesień", "październik", "listopad", "grudzień"]
year = list(range(2025, 2036))

name = st.text_input(label="Imię i nazwisko", placeholder="Podaj imię i nazwisko")
month_ = st.selectbox("Wybierz miesiąc", options=list(range(1, 13)), format_func=lambda x: month_name[x - 1])
year_ = st.selectbox(label="Rok", options=year)
pens = [3.6, 3.8, 4.0, 4.2, 4.4, 4.6, 5.4, 6.0]
pens_ = st.selectbox(label="Pensum", options=pens, index=pens.index(st.session_state["pensum_global"]))
st.session_state["pensum_global"] = pens_

# Przydzial co tydzień
st.subheader("⚙️ Przydział tygodniowy")
col1, col2, col3, col4, col5 = st.columns(5)
with col1: st.session_state["pn"] = st.number_input("Poniedziałek", value=float(st.session_state["pn"]), step=0.5)
with col2: st.session_state["wt"] = st.number_input("Wtorek", value=float(st.session_state["wt"]), step=0.5)
with col3: st.session_state["sr"] = st.number_input("Środa", value=float(st.session_state["sr"]), step=0.5)
with col4: st.session_state["czw"] = st.number_input("Czwartek", value=float(st.session_state["czw"]), step=0.5)
with col5: st.session_state["pt"] = st.number_input("Piątek", value=float(st.session_state["pt"]), step=0.5)

# 📅 Generowanie dni roboczych
first_day = pd.Timestamp(year=int(year_), month=month_, day=1)
last_day = pd.Timestamp(year=int(year_), month=month_, day=calendar.monthrange(int(year_), month_)[1])
workdays = pd.bdate_range(start=first_day, end=last_day)
state_key = f"df_{year_}_{month_}"

# -------------------------
# Funkcja tworząca DataFrame
# -------------------------
def create_week_df(pensum_default):
    dates, weekdays, przydzial, pensum, wyplata_ = [], [], [], [], []
    dni_tygodnia = {
        "Monday": "Poniedziałek",
        "Tuesday": "Wtorek",
        "Wednesday": "Środa",
        "Thursday": "Czwartek",
        "Friday": "Piątek",
        "Saturday": "Sobota",
        "Sunday": "Niedziela"
    }
    for d in workdays:
        day_name = dni_tygodnia[d.strftime("%A")]
        dates.append(d.strftime("%Y-%m-%d"))
        weekdays.append(day_name)
        przydzial.append(0.0)
        pensum.append(pensum_default)
        wyplata_.append(0.0)
    return pd.DataFrame({
        "Data": dates,
        "Dzien": weekdays,
        "Przydzial": przydzial,
        "Pensum": pensum,
        "Wyplata": wyplata_
    })

# -------------------------
# Przycisk wstawienia tygodniowego przydziału
# -------------------------
if st.button("📅 Wstaw tygodniowy przydział"):
    st.session_state[state_key] = create_week_df(st.session_state["pensum_global"])
    st.session_state["form_version"] += 1  # 👈 nowa wersja formularza
    st.success(f"Wstawiono przydział dla {month_name[month_ - 1]} {year_}.")

# -------------------------
# Edycja pól number_input z przyciskiem aktualizacji
# -------------------------
if state_key in st.session_state and st.session_state[state_key] is not None:
    df = st.session_state[state_key]
    st.subheader("⚙️ Edycja przydziałów i pensum (edytuj oraz kliknij 'Zastosuj zmiany')")

    tmp_data = {"Data": [], "Dzien": [], "Przydzial": [], "Pensum": [], "Wyplata": []}
    dni_przydzial = {
        "Poniedziałek": st.session_state["pn"],
        "Wtorek": st.session_state["wt"],
        "Środa": st.session_state["sr"],
        "Czwartek": st.session_state["czw"],
        "Piątek": st.session_state["pt"],
    }

    for idx, row in df.iterrows():
        col1, col2 = st.columns(2)
        with col1:
            value = dni_przydzial.get(row["Dzien"], 0.0)
            przydz = st.number_input(
                label=f"Przydział {row['Dzien']}",
                value=float(value),
                step=0.5,
                key=f"tmp_przydz_{row['Data']}_{st.session_state['form_version']}"  # 👈 klucz uwzględnia wersję
            )
        with col2:
            pen = st.number_input(
                label=f"Pensum {row['Data']}",
                value=float(row["Pensum"]),
                step=0.1,
                key=f"tmp_pens_{row['Data']}_{st.session_state['form_version']}"  # 👈 klucz uwzględnia wersję
            )
        tmp_data["Data"].append(row["Data"])
        tmp_data["Dzien"].append(row["Dzien"])
        tmp_data["Przydzial"].append(przydz)
        tmp_data["Pensum"].append(pen)
        tmp_data["Wyplata"].append(round(przydz - pen, 2))

    if st.button("💾 Zastosuj zmiany"):
        new_df = pd.DataFrame(tmp_data)
        st.session_state[state_key] = new_df
        st.session_state["wyplata"] = (new_df["Przydzial"] - new_df["Pensum"]).sum()
        st.write(new_df)
        st.success(f"✅ Pola zapisane. Do wypłaty: {round(st.session_state['wyplata'],2)} godzin")

# -------------------------
# Funkcja tworząca PDF
# -------------------------
def create_pdf_bytes():
    df_for_pdf = st.session_state.get(state_key)
    if df_for_pdf is None:
        df_for_pdf = create_week_df(st.session_state["pensum_global"])

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []

    elements.append(Paragraph("Podsumowanie zrealizowanych godzin", style_title))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Miesiąc: {month_name[month_-1]} {year_}", style_normal))
    elements.append(Paragraph(f"Nauczyciel: {name}", style_normal))
    elements.append(Paragraph(f"Do wypłaty: {round(st.session_state.get('wyplata',0),2)} godzin", style_normal))
    elements.append(Spacer(1, 12))

    pdf_table_data = df_for_pdf.copy()
    pdf_table_data["Data"] = pd.to_datetime(pdf_table_data["Data"]).dt.strftime("%Y-%m-%d")
    if "auto_unique_id" in pdf_table_data.columns:
        pdf_table_data = pdf_table_data.drop(columns=["auto_unique_id"])
    data = [pdf_table_data.columns.to_list()] + pdf_table_data.values.tolist()

    table = Table(data, colWidths=[70,70,70,70,70])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("FONTNAME", (0, 0), (-1, -1), "DejaVuSans"),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Podpis nauczyciela: ....................", style_normal))
    elements.append(Paragraph("Zatwierdził: ................................", style_normal))
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

# -------------------------
# Generowanie PDF
# -------------------------
if st.button("📄 Generuj PDF"):
    st.session_state["pdf_ready"] = create_pdf_bytes()
    st.success("PDF wygenerowany — kliknij przycisk pobrania poniżej.")

if st.session_state.get("pdf_ready") is not None:
    st.download_button(
        label="⬇️ Pobierz raport PDF",
        data=st.session_state["pdf_ready"],
        file_name=f"raport_{name.replace(' ','_')}_{month_name[month_-1]}_{year_}.pdf",
        mime="application/pdf"
    )

# Wyświetlenie sumy
st.caption(f"Do wypłaty: {round(st.session_state.get('wyplata',0),2)} godzin")
