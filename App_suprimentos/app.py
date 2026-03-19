
from io import BytesIO
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="Painel Andon de Suprimentos", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
.stApp {
    background: linear-gradient(180deg,#070B12 0%,#0F1724 100%);
    color:#E8EEF7;
}
h1,h2,h3,h4,h5,h6,p,label,span,div {
    color:#E8EEF7;
}
section[data-testid="stSidebar"] {
    background:#0B1220;
    border-right:1px solid rgba(255,255,255,0.08);
}

/* cards */
div[data-testid="stMetric"]{
    background:rgba(255,255,255,0.04);
    border:1px solid rgba(255,255,255,0.08);
    padding:14px;
    border-radius:14px;
}

/* tabelas: fundo claro + texto preto */
[data-testid="stDataFrame"] {
    background-color:#FFFFFF !important;
}
[data-testid="stDataFrame"] * {
    color:#000000 !important;
}
[data-testid="stDataFrame"] thead th {
    background:#F3F4F6 !important;
    color:#000000 !important;
    font-weight:600 !important;
}
[data-testid="stDataFrame"] tbody tr {
    color:#000000 !important;
}

/* selects tesla */
div[data-baseweb="select"] > div {
    background:#111827 !important;
    border:1px solid #334155 !important;
    border-radius:10px !important;
}
div[data-baseweb="select"] * {
    color:#FFFFFF !important;
    fill:#FFFFFF !important;
}
div[role="listbox"] {
    background:#111827 !important;
}
div[role="listbox"] * {
    color:#FFFFFF !important;
}
li[role="option"] {
    background:#111827 !important;
    color:#FFFFFF !important;
}
li[role="option"]:hover {
    background:#1F2937 !important;
}
li[aria-selected="true"] {
    background:#2563EB !important;
    color:#FFFFFF !important;
}

/* number input */
div[data-testid="stNumberInput"] input {
    color:#111827 !important;
    background:#FFFFFF !important;
    font-size:28px !important;
    font-weight:700 !important;
    opacity:1 !important;
    -webkit-text-fill-color:#111827 !important;
}
div[data-testid="stNumberInput"] button {
    color:#111827 !important;
    background:#E5E7EB !important;
    border-radius:8px !important;
}

/* ranking cards */
.rank-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    padding: 12px 14px;
    margin-bottom: 10px;
}
.rank-title {
    font-size: 14px;
    color: #CBD5E1;
    margin-bottom: 6px;
}
.rank-item {
    font-size: 15px;
    font-weight: 700;
    color: #FFFFFF;
}
.rank-value {
    font-size: 22px;
    font-weight: 800;
    color: #EF4444;
    margin-top: 4px;
}
</style>
""", unsafe_allow_html=True)

def to_float(v):
    if pd.isna(v):
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(".", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return 0.0

def normalizar(v):
    if pd.isna(v):
        return ""
    return str(v).strip()

def formatar_compacto(valor):
    if abs(valor) >= 1_000_000:
        return f"{valor/1_000_000:.1f}M"
    if abs(valor) >= 1_000:
        return f"{valor/1_000:.1f}K"
    return f"{valor:.0f}"

def multiselect_com_todos(label, options, key):
    options = list(options)
    opcoes = ["Todos"] + options
    selecionados = st.multiselect(label, opcoes, default=["Todos"], key=key)
    if not selecionados or "Todos" in selecionados:
        return options
    return [x for x in selecionados if x in options]

@st.cache_data(show_spinner=False)
def carregar_excel(uploaded_file):
    xls = pd.ExcelFile(uploaded_file)
    aba_estrut = [a for a in xls.sheet_names if "estrut" in a.lower()][0]
    aba_saldo = [a for a in xls.sheet_names if "saldo" in a.lower()][0]
    df_e = pd.read_excel(uploaded_file, sheet_name=aba_estrut)
    df_s = pd.read_excel(uploaded_file, sheet_name=aba_saldo)
    return df_e, df_s, aba_estrut, aba_saldo

def preparar_estruturas(df):
    base = pd.DataFrame({
        "MODELO": df.iloc[:,1].apply(normalizar),
        "TIPO": df.iloc[:,2].apply(normalizar),
        "FAMILIA": df.iloc[:,5].apply(normalizar),
        "ITEM": df.iloc[:,8].apply(normalizar),
        "QTD": df.iloc[:,9].apply(to_float)
    })
    base = base[(base["MODELO"] != "") & (base["TIPO"] != "") & (base["ITEM"] != "")].copy()
    base = base.groupby(["MODELO","TIPO","FAMILIA","ITEM"], as_index=False)["QTD"].sum()
    return base

def preparar_saldo(df):
    saldo = pd.DataFrame({
        "ITEM": df.iloc[:,2].apply(normalizar),
        "SALDO": df.iloc[:,3].apply(to_float)
    })
    saldo = saldo[saldo["ITEM"] != ""].copy()
    saldo = saldo.groupby("ITEM", as_index=False)["SALDO"].sum()
    return saldo

def simular(base, saldo, tipos, familias, mapa_modelos):
    registros = []
    for modelo, qtd_montar in mapa_modelos.items():
        filtro = base[
            (base["MODELO"] == modelo) &
            (base["TIPO"].isin(tipos)) &
            (base["FAMILIA"].isin(familias))
        ].copy()
        if filtro.empty:
            continue
        filtro["QTD_A_MONTAR"] = qtd_montar
        filtro["NECESSIDADE"] = filtro["QTD"] * qtd_montar
        registros.append(filtro)

    if not registros:
        return pd.DataFrame(), pd.DataFrame()

    detalhado = pd.concat(registros, ignore_index=True)
    consolidado = detalhado.groupby("ITEM", as_index=False)["NECESSIDADE"].sum()
    consolidado = consolidado.merge(saldo, on="ITEM", how="left")
    consolidado["SALDO"] = consolidado["SALDO"].fillna(0)
    consolidado["DELTA"] = consolidado["SALDO"] - consolidado["NECESSIDADE"]
    consolidado["FALTA"] = (-consolidado["DELTA"]).clip(lower=0)
    consolidado["SOBRA"] = consolidado["DELTA"].clip(lower=0)
    consolidado["STATUS"] = consolidado["DELTA"].apply(lambda x: "OK" if x >= 0 else "RUPTURA")
    consolidado = consolidado.sort_values(["FALTA","ITEM"], ascending=[False, True]).reset_index(drop=True)
    return detalhado, consolidado

def grafico_barras(df):
    plot_df = df.copy().sort_values("FALTA", ascending=False).reset_index(drop=True)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=plot_df["NECESSIDADE"], y=plot_df["ITEM"], orientation="h", name="Necessidade", marker=dict(color="#475569")))
    fig.add_trace(go.Bar(x=plot_df["SALDO"], y=plot_df["ITEM"], orientation="h", name="Saldo", marker=dict(color="#22C55E")))
    fig.add_trace(go.Scatter(
        x=plot_df["SALDO"],
        y=plot_df["ITEM"],
        mode="markers+text",
        name="Delta",
        text=[f"Δ {formatar_compacto(v)}" for v in plot_df["DELTA"]],
        textposition="middle right",
        marker=dict(size=12, color=["#EF4444" if v < 0 else "#10B981" for v in plot_df["DELTA"]], symbol="diamond")
    ))
    fig.update_layout(
        barmode="overlay",
        height=max(450, len(plot_df) * 34),
        title="Painel Andon - saldo e delta",
        xaxis_title="Quantidade",
        yaxis_title="Itens",
        paper_bgcolor="#0F1724",
        plot_bgcolor="#0F1724",
        font=dict(color="#E8EEF7"),
        legend_title="Indicadores",
        margin=dict(l=10, r=20, t=50, b=10),
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.08)")
    fig.update_yaxes(autorange="reversed", automargin=True)
    return fig

def termometro(valor, maximo, titulo, cor):
    maximo = max(maximo, 1)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=valor,
        number={"font": {"size": 24, "color": "#E8EEF7"}},
        title={"text": titulo, "font": {"size": 16, "color": "#E8EEF7"}},
        gauge={"shape": "bullet", "axis": {"range": [0, maximo]}, "bar": {"color": cor, "thickness": 0.8}, "bgcolor": "#1B2430", "borderwidth": 1, "bordercolor": "#2A3443"}
    ))
    fig.update_layout(height=170, margin=dict(l=20, r=20, t=40, b=10), paper_bgcolor="#0F1724")
    return fig

def mini_tabela(df):
    base = df.copy()
    base["DELTA_FMT"] = base["DELTA"].apply(formatar_compacto)
    base["SALDO_FMT"] = base["SALDO"].apply(formatar_compacto)
    base["NECESS_FMT"] = base["NECESSIDADE"].apply(formatar_compacto)
    base["FALTA_FMT"] = base["FALTA"].apply(formatar_compacto)
    mini = base[["ITEM", "NECESS_FMT", "SALDO_FMT", "DELTA_FMT", "FALTA_FMT", "STATUS"]].copy()
    mini.columns = ["ITEM", "NECESSIDADE", "SALDO", "DELTA", "FALTA", "STATUS"]
    return mini.head(10)

def colorir_linhas_por_status(row):
    if row["STATUS"] == "OK":
        return ["background-color: rgba(34,197,94,0.18); color: #000000;"] * len(row)
    return ["background-color: rgba(239,68,68,0.18); color: #000000;"] * len(row)

def converter_excel_download(df_consolidado, df_detalhado, df_resumo):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_consolidado.to_excel(writer, index=False, sheet_name="Simulacao_Consolidada")
        df_detalhado.to_excel(writer, index=False, sheet_name="Simulacao_Detalhada")
        df_resumo.to_excel(writer, index=False, sheet_name="Resumo")
    output.seek(0)
    return output

st.title("⚡ Painel Andon de Suprimentos")
st.caption("Com ranking das 10 maiores rupturas no topo do painel.")

uploaded = st.sidebar.file_uploader("Arquivo Excel", type=["xlsx", "xlsm", "xls"])
if not uploaded:
    st.info("Carregue o arquivo Excel para iniciar.")
    st.stop()

try:
    df_e, df_s, aba_e, aba_s = carregar_excel(uploaded)
    base = preparar_estruturas(df_e)
    saldo = preparar_saldo(df_s)

    st.success(f"Arquivo carregado com sucesso. Estruturas: {aba_e} | Saldo: {aba_s}")

    st.subheader("Filtros")
    c1, c2, c3, c4 = st.columns(4)

    tipos = sorted([x for x in base["TIPO"].unique().tolist() if x != ""])
    with c1:
        tipos_sel = multiselect_com_todos("Tipos", tipos, "tipos")

    familias = sorted([x for x in base[base["TIPO"].isin(tipos_sel)]["FAMILIA"].unique().tolist() if x != ""])
    with c2:
        familias_sel = multiselect_com_todos("Famílias", familias, "familias")

    modelos = sorted([x for x in base[(base["TIPO"].isin(tipos_sel)) & (base["FAMILIA"].isin(familias_sel))]["MODELO"].unique().tolist() if x != ""])
    with c3:
        modelos_sel = multiselect_com_todos("Modelos", modelos, "modelos")

    with c4:
        andon_ops = ["Todos", "RUPTURA", "OK"]
        andon_sel = st.multiselect("Filtro Andon", andon_ops, default=["Todos"])
        if not andon_sel or "Todos" in andon_sel:
            andon_sel = ["RUPTURA", "OK"]

    st.subheader("Quantidade a montar por modelo")
    mapa_modelos = {}
    cols = st.columns(3)
    for i, m in enumerate(modelos_sel):
        with cols[i % 3]:
            mapa_modelos[m] = st.number_input(f"Qtd. a montar - {m}", min_value=1, value=1, step=1, key=f"qtd_{m}")

    detalhado, consolidado = simular(base, saldo, tipos_sel, familias_sel, mapa_modelos)
    if consolidado.empty:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")
        st.stop()

    consolidado = consolidado[consolidado["STATUS"].isin(andon_sel)].copy()
    detalhado = detalhado[detalhado["ITEM"].isin(consolidado["ITEM"])].copy()

    if consolidado.empty:
        st.warning("Após aplicar os filtros, não restaram dados para exibir.")
        st.stop()

    total_nec = float(consolidado["NECESSIDADE"].sum())
    total_saldo = float(consolidado["SALDO"].sum())
    total_delta = float(consolidado["DELTA"].sum())
    total_falta = float(consolidado["FALTA"].sum())

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Necessidade", formatar_compacto(total_nec))
    m2.metric("Saldo", formatar_compacto(total_saldo))
    m3.metric("Delta", formatar_compacto(total_delta))
    m4.metric("Faltante", formatar_compacto(total_falta))

    st.subheader("Ranking das 10 maiores rupturas")
    ranking = consolidado[consolidado["FALTA"] > 0].copy().sort_values("FALTA", ascending=False).head(10)

    if ranking.empty:
        st.success("Não há rupturas para exibir no ranking.")
    else:
        rcols = st.columns(2)
        esquerda = ranking.iloc[:5]
        direita = ranking.iloc[5:10]

        with rcols[0]:
            for idx, (_, row) in enumerate(esquerda.iterrows(), start=1):
                st.markdown(f'''
                <div class="rank-card">
                    <div class="rank-title">#{idx} maior ruptura</div>
                    <div class="rank-item">{row["ITEM"]}</div>
                    <div class="rank-value">{formatar_compacto(row["FALTA"])}</div>
                </div>
                ''', unsafe_allow_html=True)

        with rcols[1]:
            for idx, (_, row) in enumerate(direita.iterrows(), start=6):
                st.markdown(f'''
                <div class="rank-card">
                    <div class="rank-title">#{idx} maior ruptura</div>
                    <div class="rank-item">{row["ITEM"]}</div>
                    <div class="rank-value">{formatar_compacto(row["FALTA"])}</div>
                </div>
                ''', unsafe_allow_html=True)

    st.subheader("Termômetros Andon")
    t1, t2, t3 = st.columns(3)
    with t1:
        st.plotly_chart(termometro(total_nec, max(total_nec, total_saldo), "Necessidade", "#64748B"), use_container_width=True)
        st.caption("Barra cinza: total necessário para atender os modelos selecionados.")
    with t2:
        st.plotly_chart(termometro(total_saldo, max(total_nec, total_saldo), "Saldo", "#22C55E"), use_container_width=True)
        st.caption("Barra verde: saldo disponível para faturamento na aba de estoque.")
    with t3:
        st.plotly_chart(termometro(abs(total_delta), max(abs(total_delta), total_nec), "Delta", "#38BDF8"), use_container_width=True)
        st.caption("Barra azul: diferença entre saldo e necessidade. Quando negativa, indica insuficiência.")

    st.subheader("Gráfico de barras Andon")
    st.plotly_chart(grafico_barras(consolidado), use_container_width=True)

    st.subheader("Mini tabela abaixo dos gráficos")
    mini = mini_tabela(consolidado)
    st.dataframe(mini.style.apply(colorir_linhas_por_status, axis=1), use_container_width=True, height=320)

    st.subheader("Tabela consolidada")
    tabela = consolidado.copy()
    for col in ["NECESSIDADE", "SALDO", "DELTA", "FALTA", "SOBRA"]:
        tabela[col] = tabela[col].round(3)
    st.dataframe(tabela, use_container_width=True, height=430)

    resumo = pd.DataFrame({
        "Indicador": ["Necessidade", "Saldo", "Delta", "Faltante"],
        "Valor": [round(total_nec, 3), round(total_saldo, 3), round(total_delta, 3), round(total_falta, 3)]
    })
    arquivo = converter_excel_download(tabela, detalhado, resumo)

    st.download_button("Baixar simulação em Excel", data=arquivo, file_name="simulacao_suprimentos_v15.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

except Exception as e:
    st.error(f"Erro ao processar o arquivo: {e}")
