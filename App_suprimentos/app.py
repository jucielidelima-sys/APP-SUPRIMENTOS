
from io import BytesIO
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="Painel Andon de Suprimentos", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
.stApp { background: linear-gradient(180deg,#070B12 0%,#0F1724 100%); color:#E8EEF7; }
h1,h2,h3,h4,h5,h6,p,label,span,div { color:#E8EEF7; }
section[data-testid="stSidebar"] { background:#0B1220; border-right:1px solid rgba(255,255,255,0.08); }
div[data-testid="stMetric"]{ background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08); padding:14px; border-radius:14px; }
[data-testid="stDataFrame"] { background-color:#FFFFFF !important; }
[data-testid="stDataFrame"] * { color:#000000 !important; }
[data-testid="stDataFrame"] thead th { background:#F3F4F6 !important; color:#000000 !important; font-weight:600 !important; }
div[data-baseweb="select"] > div { background:#111827 !important; border:1px solid #334155 !important; border-radius:10px !important; }
div[data-baseweb="select"] * { color:#FFFFFF !important; fill:#FFFFFF !important; }
div[role="listbox"] { background:#111827 !important; }
div[role="listbox"] * { color:#FFFFFF !important; }
li[role="option"] { background:#111827 !important; color:#FFFFFF !important; }
li[role="option"]:hover { background:#1F2937 !important; }
li[aria-selected="true"] { background:#2563EB !important; color:#FFFFFF !important; }
div[data-testid="stNumberInput"] input {
    color:#111827 !important; background:#FFFFFF !important; font-size:24px !important;
    font-weight:700 !important; opacity:1 !important; -webkit-text-fill-color:#111827 !important;
}
div[data-testid="stNumberInput"] button { color:#111827 !important; background:#E5E7EB !important; border-radius:8px !important; }
.rank-card { background: rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08); border-radius:14px; padding:12px 14px; margin-bottom:10px; }
.rank-title { font-size:14px; color:#CBD5E1; margin-bottom:6px; }
.rank-item { font-size:15px; font-weight:700; color:#FFFFFF; }
.rank-value { font-size:22px; font-weight:800; color:#EF4444; margin-top:4px; }
</style>
""", unsafe_allow_html=True)

def to_float(v):
    if pd.isna(v): return 0.0
    if isinstance(v, (int, float)): return float(v)
    s = str(v).strip().replace(".", "").replace(",", ".")
    try: return float(s)
    except Exception: return 0.0

def normalizar(v):
    if pd.isna(v): return ""
    return str(v).strip()

def formatar_compacto(valor):
    if abs(valor) >= 1_000_000: return f"{valor/1_000_000:.1f}M"
    if abs(valor) >= 1_000: return f"{valor/1_000:.1f}K"
    return f"{valor:.0f}"

def multiselect_com_todos(label, options, key):
    options = [x for x in list(options) if str(x).strip() != ""]
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
        "COD_MODELO": df.iloc[:,0].apply(normalizar),
        "MODELO_DESC": df.iloc[:,1].apply(normalizar),
        "TIPO": df.iloc[:,2].apply(normalizar),
        "FAMILIA": df.iloc[:,5].apply(normalizar),
        "DERIVACAO": df.iloc[:,7].apply(normalizar),
        "ITEM": df.iloc[:,8].apply(normalizar),
        "QTD": df.iloc[:,9].apply(to_float)
    })
    base = base[(base["COD_MODELO"] != "") & (base["TIPO"] != "") & (base["ITEM"] != "")].copy()
    base = base.groupby(["COD_MODELO","MODELO_DESC","TIPO","FAMILIA","DERIVACAO","ITEM"], as_index=False)["QTD"].sum()
    return base

def preparar_saldo(df):
    saldo = pd.DataFrame({
        "ITEM": df.iloc[:,2].apply(normalizar),
        "SALDO": df.iloc[:,3].apply(to_float)
    })
    saldo = saldo[saldo["ITEM"] != ""].copy()
    saldo = saldo.groupby("ITEM", as_index=False)["SALDO"].sum()
    return saldo

def simular(base, saldo, tipos, familias, selecoes_modelo):
    registros = []
    for cod_modelo, dados in selecoes_modelo.items():
        qtd_montar = dados["qtd"]
        derivacao = dados["derivacao"]
        filtro = base[
            (base["COD_MODELO"] == cod_modelo) &
            (base["TIPO"].isin(tipos)) &
            (base["FAMILIA"].isin(familias)) &
            (base["DERIVACAO"] == derivacao)
        ].copy()
        if filtro.empty:
            continue
        filtro["QTD_A_MONTAR"] = qtd_montar
        filtro["DERIVACAO_SELECIONADA"] = derivacao
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
    consolidado["ORDEM_GRAFICO"] = consolidado.apply(lambda x: x["FALTA"] if x["FALTA"] > 0 else x["SOBRA"], axis=1)
    consolidado = consolidado.sort_values(["ORDEM_GRAFICO","ITEM"], ascending=[False, True]).reset_index(drop=True)
    return detalhado, consolidado

def grafico_barras_tesla(df):
    plot_df = df.copy().sort_values("ORDEM_GRAFICO", ascending=False).reset_index(drop=True)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=plot_df["NECESSIDADE"], y=plot_df["ITEM"], orientation="h", name="Necessidade",
        marker=dict(color="#475569"),
        hovertemplate="<b>%{y}</b><br>Necessidade: %{x:,.2f}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=plot_df["SALDO"], y=plot_df["ITEM"], orientation="h", name="Saldo",
        marker=dict(color=["#22C55E" if s > 0 else "#64748B" for s in plot_df["SALDO"]]),
        hovertemplate="<b>%{y}</b><br>Saldo: %{x:,.2f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=plot_df["SALDO"], y=plot_df["ITEM"], mode="markers+text", name="Delta",
        text=[f"Δ {formatar_compacto(v)}" for v in plot_df["DELTA"]],
        textposition="middle right",
        marker=dict(size=12, color=["#EF4444" if v < 0 else "#10B981" for v in plot_df["DELTA"]], symbol="diamond"),
        hovertemplate="<b>%{y}</b><br>%{text}<extra></extra>",
    ))
    fig.add_vline(x=0, line_width=1, line_color="rgba(255,255,255,0.25)")
    fig.update_layout(
        barmode="overlay",
        height=max(500, len(plot_df) * 34),
        title="Painel Andon Tesla - Ruptura e Estoque Positivo em Ordem Decrescente",
        xaxis_title="Quantidade",
        yaxis_title="Itens",
        paper_bgcolor="#0F1724",
        plot_bgcolor="#0F1724",
        font=dict(color="#E8EEF7"),
        legend_title="Indicadores",
        margin=dict(l=10, r=20, t=60, b=10),
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.08)")
    fig.update_yaxes(autorange="reversed", automargin=True)
    return fig

def termometro(valor, maximo, titulo, cor):
    maximo = max(maximo, 1)
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=valor,
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
st.caption("Versão completa com exportação Excel, gráfico Tesla/BI e ranking das rupturas.")

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
    tipos = sorted(base["TIPO"].unique().tolist())
    with c1:
        tipos_sel = multiselect_com_todos("Tipos", tipos, "tipos")

    familias = sorted(base[base["TIPO"].isin(tipos_sel)]["FAMILIA"].unique().tolist())
    with c2:
        familias_sel = multiselect_com_todos("Famílias", familias, "familias")

    cod_modelos = sorted(
        base[(base["TIPO"].isin(tipos_sel)) & (base["FAMILIA"].isin(familias_sel))]["COD_MODELO"].unique().tolist(),
        key=lambda x: str(x)
    )
    with c3:
        cod_modelos_sel = multiselect_com_todos("COD. Modelo", cod_modelos, "cod_modelos")

    with c4:
        andon_ops = ["Todos", "RUPTURA", "OK"]
        andon_sel = st.multiselect("Filtro Andon", andon_ops, default=["Todos"])
        if not andon_sel or "Todos" in andon_sel:
            andon_sel = ["RUPTURA", "OK"]

    st.subheader("Seleção por COD. Modelo")
    st.caption("Somente os códigos selecionados aparecem abaixo. Para cada código, escolha uma derivação e informe a quantidade.")

    selecoes_modelo = {}
    for idx, cod_modelo in enumerate(cod_modelos_sel, start=1):
        subset_modelo = base[
            (base["TIPO"].isin(tipos_sel)) &
            (base["FAMILIA"].isin(familias_sel)) &
            (base["COD_MODELO"] == cod_modelo)
        ].copy()

        derivacoes_modelo = sorted([x for x in subset_modelo["DERIVACAO"].unique().tolist() if str(x).strip() != ""], key=lambda x: str(x))
        descs = [x for x in subset_modelo["MODELO_DESC"].dropna().unique().tolist() if str(x).strip() != ""]
        desc_modelo = descs[0] if descs else ""

        box1, box2, box3 = st.columns([3, 4, 2])
        with box1:
            st.selectbox("COD. Modelo", [cod_modelo], index=0, key=f"cod_fixo_{idx}")
        with box2:
            label_der = f"Derivação - {cod_modelo}"
            if desc_modelo:
                label_der = f"Derivação - {cod_modelo} | {desc_modelo}"
            derivacao_sel = st.selectbox(label_der, derivacoes_modelo, index=0 if derivacoes_modelo else None, key=f"derivacao_{idx}")
        with box3:
            qtd_sel = st.number_input(f"Qtd. - {cod_modelo}", min_value=1, value=1, step=1, key=f"qtd_{idx}")

        if derivacoes_modelo:
            selecoes_modelo[cod_modelo] = {"derivacao": derivacao_sel, "qtd": qtd_sel}

    detalhado, consolidado = simular(base, saldo, tipos_sel, familias_sel, selecoes_modelo)
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
                </div>''', unsafe_allow_html=True)
        with rcols[1]:
            for idx, (_, row) in enumerate(direita.iterrows(), start=6):
                st.markdown(f'''
                <div class="rank-card">
                    <div class="rank-title">#{idx} maior ruptura</div>
                    <div class="rank-item">{row["ITEM"]}</div>
                    <div class="rank-value">{formatar_compacto(row["FALTA"])}</div>
                </div>''', unsafe_allow_html=True)

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
        st.caption("Barra azul: diferença entre saldo e necessidade.")

    st.subheader("Gráfico Tesla / BI Industrial")
    st.plotly_chart(grafico_barras_tesla(consolidado), use_container_width=True)

    st.subheader("Mini tabela abaixo dos gráficos")
    mini = mini_tabela(consolidado)
    st.dataframe(mini.style.apply(colorir_linhas_por_status, axis=1), use_container_width=True, height=320)

    st.subheader("Tabela consolidada")
    tabela = consolidado.copy()
    for col in ["NECESSIDADE", "SALDO", "DELTA", "FALTA", "SOBRA", "ORDEM_GRAFICO"]:
        if col in tabela.columns:
            tabela[col] = tabela[col].round(3)
    st.dataframe(tabela, use_container_width=True, height=430)

    resumo = pd.DataFrame({
        "Indicador": ["Necessidade", "Saldo", "Delta", "Faltante"],
        "Valor": [round(total_nec, 3), round(total_saldo, 3), round(total_delta, 3), round(total_falta, 3)]
    })

    arquivo = converter_excel_download(tabela, detalhado, resumo)
    st.download_button(
        "Baixar simulação em Excel",
        data=arquivo,
        file_name="simulacao_suprimentos_tesla_v19.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

except Exception as e:
    st.error(f"Erro ao processar o arquivo: {e}")
