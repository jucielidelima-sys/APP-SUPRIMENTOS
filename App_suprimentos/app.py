
from io import BytesIO
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from pathlib import Path

st.set_page_config(page_title="Painel Andon de Suprimentos", layout="wide")

# =============================
# CARREGAMENTO AUTOMÁTICO
# =============================

DEFAULT_FILE = Path("dados.xlsx")

uploaded = st.sidebar.file_uploader("Substituir arquivo Excel", type=["xlsx"])

if uploaded:
    excel_file = uploaded
else:
    if DEFAULT_FILE.exists():
        excel_file = DEFAULT_FILE
        st.sidebar.success("Usando arquivo padrão do repositório")
    else:
        st.warning("Arquivo padrão não encontrado.")
        st.stop()

# =============================
# LEITURA EXCEL
# =============================

xls = pd.ExcelFile(excel_file)

aba_estrut = [a for a in xls.sheet_names if "estrut" in a.lower()][0]
aba_saldo = [a for a in xls.sheet_names if "saldo" in a.lower()][0]

df_e = pd.read_excel(excel_file, sheet_name=aba_estrut)
df_s = pd.read_excel(excel_file, sheet_name=aba_saldo)

st.title("Painel Andon de Suprimentos")

st.success(f"Arquivo carregado automaticamente: {excel_file}")

st.write("Estruturas", df_e.head())
st.write("Saldo", df_s.head())

# =============================
# EXPORTAÇÃO
# =============================

output = BytesIO()

with pd.ExcelWriter(output, engine="openpyxl") as writer:
    df_e.to_excel(writer, sheet_name="Estruturas", index=False)
    df_s.to_excel(writer, sheet_name="Saldo", index=False)

st.download_button(
    "Exportar dados carregados",
    data=output.getvalue(),
    file_name="exportacao_suprimentos.xlsx"
)
