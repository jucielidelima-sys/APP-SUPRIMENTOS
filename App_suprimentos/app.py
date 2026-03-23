from io import BytesIO
from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(
    page_title="Painel Andon de Suprimentos",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================
# LOCALIZAÇÃO DO ARQUIVO FIXO
# =============================

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_FILE = BASE_DIR / "dados.xlsx"

def carregar_excel_local_ou_upload():

    uploaded = st.sidebar.file_uploader(
        "Substituir arquivo Excel",
        type=["xlsx", "xlsm", "xls"]
    )

    if uploaded:
        return uploaded, "upload manual"

    if DEFAULT_FILE.exists():
        return DEFAULT_FILE, "arquivo padrão do repositório"

    st.error(f"Arquivo padrão não encontrado: {DEFAULT_FILE}")
    st.stop()

# =============================
# FUNÇÕES AUXILIARES
# =============================

def normalizar(v):
    if pd.isna(v):
        return ""
    return str(v).strip()

def to_float(v):
    if pd.isna(v):
        return 0
    if isinstance(v,(int,float)):
        return v
    return float(str(v).replace(".","").replace(",",".") or 0)

def formatar_compacto(v):

    if abs(v) >= 1_000_000:
        return f"{v/1_000_000:.1f}M"

    if abs(v) >= 1_000:
        return f"{v/1_000:.1f}K"

    return f"{v:.0f}"

# =============================
# LEITURA EXCEL
# =============================

@st.cache_data
def carregar_excel(file):

    xls = pd.ExcelFile(file)

    aba_estrut = [a for a in xls.sheet_names if "estrut" in a.lower()][0]
    aba_saldo = [a for a in xls.sheet_names if "saldo" in a.lower()][0]

    df_e = pd.read_excel(file, sheet_name=aba_estrut)
    df_s = pd.read_excel(file, sheet_name=aba_saldo)

    return df_e, df_s

# =============================
# PREPARAÇÃO
# =============================

def preparar_estruturas(df):

    base = pd.DataFrame({

        "COD_MODELO": df.iloc[:,0].apply(normalizar),
        "MODELO_DESC": df.iloc[:,1].apply(normalizar),
        "TIPO": df.iloc[:,2].apply(normalizar),
        "FAMILIA": df.iloc[:,5].apply(normalizar),
        "DERIVACAO": df.iloc[:,7].apply(normalizar),
        "ITEM": df.iloc[:,8].apply(normalizar),
        "QTD": df.iloc[:,9].apply(to_float)

    })

    base = base.groupby(
        ["COD_MODELO","MODELO_DESC","TIPO","FAMILIA","DERIVACAO","ITEM"],
        as_index=False
    )["QTD"].sum()

    return base

def preparar_saldo(df):

    saldo = pd.DataFrame({

        "ITEM": df.iloc[:,2].apply(normalizar),
        "SALDO": df.iloc[:,3].apply(to_float)

    })

    saldo = saldo.groupby("ITEM",as_index=False)["SALDO"].sum()

    return saldo

# =============================
# SIMULAÇÃO
# =============================

def simular(base, saldo, selecoes):

    registros = []

    for _,row in selecoes.iterrows():

        filtro = base[
            (base["COD_MODELO"] == row["COD_MODELO"]) &
            (base["DERIVACAO"] == row["DERIVACAO"])
        ].copy()

        filtro["NECESSIDADE"] = filtro["QTD"] * row["QTD_A_MONTAR"]

        registros.append(filtro)

    detalhado = pd.concat(registros)

    consolidado = detalhado.groupby(
        "ITEM",
        as_index=False
    )["NECESSIDADE"].sum()

    consolidado = consolidado.merge(
        saldo,
        on="ITEM",
        how="left"
    )

    consolidado["SALDO"] = consolidado["SALDO"].fillna(0)

    consolidado["DELTA"] = consolidado["SALDO"] - consolidado["NECESSIDADE"]

    consolidado["FALTA"] = (-consolidado["DELTA"]).clip(lower=0)

    consolidado["STATUS"] = consolidado["DELTA"].apply(
        lambda x: "OK" if x>=0 else "RUPTURA"
    )

    return detalhado, consolidado

# =============================
# GRÁFICO
# =============================

def grafico(df):

    df = df.sort_values("FALTA",ascending=False)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df["NECESSIDADE"],
        y=df["ITEM"],
        orientation="h",
        name="Necessidade"
    ))

    fig.add_trace(go.Bar(
        x=df["SALDO"],
        y=df["ITEM"],
        orientation="h",
        name="Saldo"
    ))

    fig.update_layout(
        barmode="overlay",
        height=600
    )

    return fig

# =============================
# APP
# =============================

st.title("⚡ Painel Andon de Suprimentos")

file_source, origem = carregar_excel_local_ou_upload()

st.sidebar.success(f"Fonte: {origem}")

df_e, df_s = carregar_excel(file_source)

base = preparar_estruturas(df_e)
saldo = preparar_saldo(df_s)

st.success("Arquivo carregado com sucesso")

# =============================
# SELEÇÃO
# =============================

cod_modelos = sorted(base["COD_MODELO"].unique())

cod_sel = st.multiselect(
    "COD Modelo",
    cod_modelos
)

linhas = []

for cod in cod_sel:

    subset = base[base["COD_MODELO"]==cod]

    derivacoes = subset["DERIVACAO"].unique()

    for der in derivacoes:

        c1,c2,c3 = st.columns(3)

        with c1:
            st.write(cod)

        with c2:
            st.write(der)

        with c3:

            qtd = st.number_input(
                f"{cod}-{der}",
                min_value=0,
                step=1
            )

        if qtd>0:

            linhas.append({

                "COD_MODELO":cod,
                "DERIVACAO":der,
                "QTD_A_MONTAR":qtd

            })

selecoes = pd.DataFrame(linhas)

if selecoes.empty:

    st.warning("Informe quantidade")

    st.stop()

detalhado, consolidado = simular(base,saldo,selecoes)

# =============================
# MÉTRICAS
# =============================

col1,col2,col3 = st.columns(3)

col1.metric("Necessidade",formatar_compacto(consolidado["NECESSIDADE"].sum()))
col2.metric("Saldo",formatar_compacto(consolidado["SALDO"].sum()))
col3.metric("Faltante",formatar_compacto(consolidado["FALTA"].sum()))

# =============================
# GRÁFICO
# =============================

st.plotly_chart(grafico(consolidado),use_container_width=True)

# =============================
# TABELA
# =============================

st.dataframe(consolidado)

# =============================
# EXPORTAÇÃO
# =============================

output = BytesIO()

with pd.ExcelWriter(output,engine="openpyxl") as writer:

    consolidado.to_excel(writer,index=False)

st.download_button(

    "Baixar simulação Excel",
    data=output.getvalue(),
    file_name="simulacao.xlsx"

)
