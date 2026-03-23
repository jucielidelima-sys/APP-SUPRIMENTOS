
from io import BytesIO
from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="Painel Andon de Suprimentos", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
.stApp { background: linear-gradient(180deg,#070B12 0%,#0F1724 100%); color:#E8EEF7; }
h1,h2,h3,h4,h5,h6,p,label,span,div { color:#E8EEF7; }
section[data-testid="stSidebar"] { background:#0B1220; border-right:1px solid rgba(255,255,255,0.08); }
div[data-testid="stMetric"]{
    background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08); padding:14px; border-radius:14px;
}
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
    color:#111827 !important; background:#FFFFFF !important; font-size:22px !important;
    font-weight:700 !important; opacity:1 !important; -webkit-text-fill-color:#111827 !important;
}
div[data-testid="stNumberInput"] button { color:#111827 !important; background:#E5E7EB !important; border-radius:8px !important; }
.rank-card { background: rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08); border-radius:14px; padding:12px 14px; margin-bottom:10px; }
.rank-title { font-size:13px; color:#CBD5E1; margin-bottom:6px; }
.rank-item { font-size:15px; font-weight:700; color:#FFFFFF; line-height:1.25; }
.rank-value { font-size:24px; font-weight:800; color:#EF4444; margin-top:6px; }
</style>
""", unsafe_allow_html=True)

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_FILE = BASE_DIR / "dados.xlsx"

def carregar_excel_local_ou_upload():
    uploaded = st.sidebar.file_uploader("Substituir arquivo Excel", type=["xlsx", "xlsm", "xls"])
    if uploaded is not None:
        return uploaded, "upload manual"
    if DEFAULT_FILE.exists():
        return DEFAULT_FILE, "arquivo padrão do repositório"
    st.error(f"Arquivo padrão não encontrado: {DEFAULT_FILE}")
    st.stop()

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
def carregar_excel(file_source):
    xls = pd.ExcelFile(file_source)
    sheet_names = xls.sheet_names
    abas_estrut = [a for a in sheet_names if "estrut" in a.lower()]
    abas_saldo = [a for a in sheet_names if "saldo" in a.lower()]
    if not abas_estrut:
        raise ValueError(f"Não encontrei aba de estruturas. Abas disponíveis: {sheet_names}")
    if not abas_saldo:
        raise ValueError(f"Não encontrei aba de saldo. Abas disponíveis: {sheet_names}")
    aba_estrut = abas_estrut[0]
    aba_saldo = abas_saldo[0]
    df_e = pd.read_excel(file_source, sheet_name=aba_estrut)
    df_s = pd.read_excel(file_source, sheet_name=aba_saldo)
    return df_e, df_s, aba_estrut, aba_saldo

def preparar_estruturas(df):
    if df.shape[1] < 10:
        raise ValueError("A aba de estruturas precisa ter pelo menos 10 colunas.")
    base = pd.DataFrame({
        "COD_MODELO": df.iloc[:,0].apply(normalizar),
        "MODELO_DESC": df.iloc[:,1].apply(normalizar),
        "TIPO": df.iloc[:,2].apply(normalizar),
        "FAMILIA": df.iloc[:,5].apply(normalizar),
        "DERIVACAO": df.iloc[:,7].apply(normalizar),
        "ITEM": df.iloc[:,8].apply(normalizar),
        "QTD": df.iloc[:,9].apply(to_float),
    })
    base = base[(base["COD_MODELO"] != "") & (base["TIPO"] != "") & (base["ITEM"] != "")].copy()
    base = base.groupby(["COD_MODELO","MODELO_DESC","TIPO","FAMILIA","DERIVACAO","ITEM"], as_index=False)["QTD"].sum()
    return base

def preparar_saldo(df):
    if df.shape[1] < 4:
        raise ValueError("A aba de saldo precisa ter pelo menos 4 colunas.")
    saldo = pd.DataFrame({
        "ITEM": df.iloc[:,2].apply(normalizar),
        "SALDO": df.iloc[:,3].apply(to_float),
    })
    saldo = saldo[saldo["ITEM"] != ""].copy()
    saldo = saldo.groupby("ITEM", as_index=False)["SALDO"].sum()
    return saldo

def simular(base, saldo, tipos, familias, selecoes):
    registros = []
    for _, row in selecoes.iterrows():
        filtro = base[
            (base["COD_MODELO"] == row["COD_MODELO"]) &
            (base["TIPO"].isin(tipos)) &
            (base["FAMILIA"].isin(familias)) &
            (base["DERIVACAO"] == row["DERIVACAO"])
        ].copy()
        if filtro.empty or row["QTD_A_MONTAR"] <= 0:
            continue
        filtro["QTD_A_MONTAR"] = row["QTD_A_MONTAR"]
        filtro["DERIVACAO_SELECIONADA"] = row["DERIVACAO"]
        filtro["SEMANA"] = row["SEMANA"]
        filtro["NECESSIDADE"] = filtro["QTD"] * row["QTD_A_MONTAR"]
        registros.append(filtro)

    if not registros:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

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

    semanal = detalhado.groupby(["SEMANA","ITEM"], as_index=False)["NECESSIDADE"].sum()
    return detalhado, consolidado, semanal

def grafico_barras_tesla(df):
    plot_df = df.copy().sort_values("ORDEM_GRAFICO", ascending=False).reset_index(drop=True)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=plot_df["NECESSIDADE"], y=plot_df["ITEM"], orientation="h", name="Necessidade", marker=dict(color="#475569")))
    fig.add_trace(go.Bar(x=plot_df["SALDO"], y=plot_df["ITEM"], orientation="h", name="Saldo", marker=dict(color=["#22C55E" if d >= 0 else "#EF4444" for d in plot_df["DELTA"]])))
    fig.add_trace(go.Scatter(
        x=plot_df["SALDO"], y=plot_df["ITEM"], mode="markers+text", name="Delta",
        text=[f"Δ {formatar_compacto(v)}" for v in plot_df["DELTA"]],
        textposition="middle right",
        marker=dict(size=12, color=["#EF4444" if v < 0 else "#10B981" for v in plot_df["DELTA"]], symbol="diamond")
    ))
    fig.add_vline(x=0, line_width=1, line_color="rgba(255,255,255,0.25)")
    fig.update_layout(
        barmode="overlay", height=max(520, len(plot_df) * 34),
        title="Painel Andon Tesla - Ruptura e Estoque Positivo em Ordem Decrescente",
        xaxis_title="Quantidade", yaxis_title="Itens",
        paper_bgcolor="#0F1724", plot_bgcolor="#0F1724", font=dict(color="#E8EEF7"),
        legend_title="Indicadores", margin=dict(l=10, r=20, t=60, b=10),
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.08)")
    fig.update_yaxes(autorange="reversed", automargin=True)
    return fig

def grafico_semanal(semanal):
    semana_ordem = ["Semana 1", "Semana 2", "Semana 3", "Semana 4", "Semana 5", "Semana 6", "Semana 7", "Semana 8"]
    resumo = semanal.groupby("SEMANA", as_index=False)["NECESSIDADE"].sum()
    resumo["ord"] = resumo["SEMANA"].apply(lambda x: semana_ordem.index(x) if x in semana_ordem else 999)
    resumo = resumo.sort_values("ord")
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=resumo["SEMANA"], y=resumo["NECESSIDADE"], name="Produção por semana",
        marker=dict(color="#38BDF8"),
        text=[formatar_compacto(x) for x in resumo["NECESSIDADE"]],
        textposition="outside"
    ))
    fig.update_layout(
        title="Simulação de Produção por Semana",
        xaxis_title="Semana", yaxis_title="Necessidade Total",
        paper_bgcolor="#0F1724", plot_bgcolor="#0F1724", font=dict(color="#E8EEF7"),
        margin=dict(l=10, r=20, t=60, b=10), height=380
    )
    fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.08)")
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

def converter_excel_download(df_consolidado, df_detalhado, df_resumo, df_selecoes, df_semanal):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_consolidado.to_excel(writer, index=False, sheet_name="Simulacao_Consolidada")
        df_detalhado.to_excel(writer, index=False, sheet_name="Simulacao_Detalhada")
        df_selecoes.to_excel(writer, index=False, sheet_name="Selecoes_Modelo_Derivacao")
        df_semanal.to_excel(writer, index=False, sheet_name="Simulacao_Semanal")
        df_resumo.to_excel(writer, index=False, sheet_name="Resumo")
    output.seek(0)
    return output

st.title("⚡ Painel Andon de Suprimentos")

try:
    file_source, origem = carregar_excel_local_ou_upload()
    if origem == "arquivo padrão do repositório":
        st.sidebar.success("Usando arquivo padrão do repositório")
    else:
        st.sidebar.info("Usando arquivo enviado manualmente")

    df_e, df_s, aba_e, aba_s = carregar_excel(file_source)
    base = preparar_estruturas(df_e)
    saldo = preparar_saldo(df_s)

    st.success(f"Arquivo carregado com sucesso. Origem: {origem}. Estruturas: {aba_e} | Saldo: {aba_s}")

    st.subheader("Filtros")
    c1, c2, c3, c4 = st.columns(4)
    tipos = sorted(base["TIPO"].unique().tolist())
    with c1:
        tipos_sel = multiselect_com_todos("Tipos", tipos, "tipos")
    familias = sorted(base[base["TIPO"].isin(tipos_sel)]["FAMILIA"].unique().tolist())
    with c2:
        familias_sel = multiselect_com_todos("Famílias", familias, "familias")
    cod_modelos = sorted(base[(base["TIPO"].isin(tipos_sel)) & (base["FAMILIA"].isin(familias_sel))]["COD_MODELO"].unique().tolist(), key=lambda x: str(x))
    with c3:
        cod_modelos_sel = multiselect_com_todos("COD. Modelo", cod_modelos, "cod_modelos")
    with c4:
        andon_ops = ["Todos", "RUPTURA", "OK"]
        andon_sel = st.multiselect("Filtro Andon", andon_ops, default=["Todos"])
        if not andon_sel or "Todos" in andon_sel:
            andon_sel = ["RUPTURA", "OK"]

    st.subheader("Seleção por COD. Modelo, Derivação e Semanas")

    semana_opcoes = ["Semana 1", "Semana 2", "Semana 3", "Semana 4", "Semana 5", "Semana 6", "Semana 7", "Semana 8"]
    linhas_selecao = []

    for idx, cod_modelo in enumerate(cod_modelos_sel, start=1):
        subset_modelo = base[
            (base["TIPO"].isin(tipos_sel)) &
            (base["FAMILIA"].isin(familias_sel)) &
            (base["COD_MODELO"] == cod_modelo)
        ].copy()
        descs = [x for x in subset_modelo["MODELO_DESC"].dropna().unique().tolist() if str(x).strip() != ""]
        desc_modelo = descs[0] if descs else ""
        derivacoes_modelo = sorted([x for x in subset_modelo["DERIVACAO"].unique().tolist() if str(x).strip() != ""], key=lambda x: str(x))

        st.markdown(f"### COD. Modelo {cod_modelo}" + (f" — {desc_modelo}" if desc_modelo else ""))

        for j, deriv in enumerate(derivacoes_modelo, start=1):
            st.markdown(f"**Derivação {deriv}**")
            col_headers = st.columns([2,2,2])
            with col_headers[0]:
                st.markdown("**Semana**")
            with col_headers[1]:
                st.markdown("**Quantidade**")
            with col_headers[2]:
                st.markdown("**Usar**")

            for k, semana in enumerate(semana_opcoes, start=1):
                cols = st.columns([2,2,2])
                with cols[0]:
                    st.text_input(f"Semana {cod_modelo}-{j}-{k}", value=semana, disabled=True, key=f"sem_txt_{idx}_{j}_{k}")
                with cols[1]:
                    qtd = st.number_input(f"Qtd. {cod_modelo}-{j}-{k}", min_value=0, value=0, step=1, key=f"qtd_{idx}_{j}_{k}")
                with cols[2]:
                    usar = st.checkbox("Selecionar", value=(qtd > 0), key=f"usar_{idx}_{j}_{k}")

                if usar and qtd > 0:
                    linhas_selecao.append({
                        "COD_MODELO": cod_modelo,
                        "MODELO_DESC": desc_modelo,
                        "DERIVACAO": deriv,
                        "SEMANA": semana,
                        "QTD_A_MONTAR": qtd
                    })

    df_selecoes = pd.DataFrame(linhas_selecao)

    if df_selecoes.empty:
        st.warning("Selecione pelo menos uma derivação com quantidade maior que zero.")
        st.stop()

    detalhado, consolidado, semanal = simular(base, saldo, tipos_sel, familias_sel, df_selecoes)

    if consolidado.empty:
        st.warning("Nenhum dado encontrado para os filtros e derivações selecionados.")
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

    cobertura_percentual = 0 if total_nec == 0 else min((total_saldo / total_nec) * 100, 999.9)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Necessidade", formatar_compacto(total_nec))
    m2.metric("Saldo", formatar_compacto(total_saldo))
    m3.metric("Delta", formatar_compacto(total_delta))
    m4.metric("Faltante", formatar_compacto(total_falta))
    m5.metric("Cobertura", f"{cobertura_percentual:.1f}%")

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
                st.markdown(f'''<div class="rank-card"><div class="rank-title">#{idx} maior ruptura</div><div class="rank-item">{row["ITEM"]}</div><div class="rank-value">{formatar_compacto(row["FALTA"])}</div></div>''', unsafe_allow_html=True)
        with rcols[1]:
            for idx, (_, row) in enumerate(direita.iterrows(), start=6):
                st.markdown(f'''<div class="rank-card"><div class="rank-title">#{idx} maior ruptura</div><div class="rank-item">{row["ITEM"]}</div><div class="rank-value">{formatar_compacto(row["FALTA"])}</div></div>''', unsafe_allow_html=True)

    st.subheader("Indicadores e Cobertura de Estoque")
    t1, t2, t3, t4 = st.columns(4)
    with t1:
        st.plotly_chart(termometro(total_nec, max(total_nec, total_saldo), "Necessidade", "#64748B"), use_container_width=True)
    with t2:
        st.plotly_chart(termometro(total_saldo, max(total_nec, total_saldo), "Saldo", "#22C55E"), use_container_width=True)
    with t3:
        st.plotly_chart(termometro(abs(total_delta), max(abs(total_delta), total_nec), "Delta", "#38BDF8"), use_container_width=True)
    with t4:
        st.plotly_chart(termometro(cobertura_percentual, max(cobertura_percentual, 100), "Cobertura %", "#F59E0B"), use_container_width=True)

    g1, g2 = st.columns([1.4, 1])
    with g1:
        st.subheader("Gráfico Tesla / BI Industrial")
        st.plotly_chart(grafico_barras_tesla(consolidado), use_container_width=True)
    with g2:
        st.subheader("Simulação de Produção por Semana")
        st.plotly_chart(grafico_semanal(semanal), use_container_width=True)

    st.subheader("Mini tabela abaixo dos gráficos")
    mini = mini_tabela(consolidado)
    st.dataframe(mini.style.apply(colorir_linhas_por_status, axis=1), use_container_width=True, height=320)

    st.subheader("Tabela de seleções por modelo, derivação e semana")
    st.dataframe(df_selecoes, use_container_width=True, height=260)

    st.subheader("Tabela consolidada")
    tabela = consolidado.copy()
    for col in ["NECESSIDADE", "SALDO", "DELTA", "FALTA", "SOBRA", "ORDEM_GRAFICO"]:
        if col in tabela.columns:
            tabela[col] = tabela[col].round(3)
    st.dataframe(tabela, use_container_width=True, height=430)

    resumo = pd.DataFrame({
        "Indicador": ["Necessidade", "Saldo", "Delta", "Faltante", "Cobertura %"],
        "Valor": [round(total_nec, 3), round(total_saldo, 3), round(total_delta, 3), round(total_falta, 3), round(cobertura_percentual, 2)]
    })

    arquivo = converter_excel_download(tabela, detalhado, resumo, df_selecoes, semanal)
    st.download_button("Baixar simulação em Excel", data=arquivo, file_name="simulacao_suprimentos_tesla_v23.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

except Exception as e:
    st.error(f"Erro ao processar o arquivo: {e}")
