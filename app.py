
from io import BytesIO
from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="Painel Andon de Suprimentos", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
:root{
    --bg1:#0f1115;
    --bg2:#1a1d23;
    --line1:rgba(255,255,255,0.05);
    --line2:rgba(255,255,255,0.02);
    --glass:rgba(18,22,30,0.68);
    --glass2:rgba(24,28,38,0.62);
    --text:#E8EEF7;
    --muted:#A7B4C8;
    --green:#22C55E;
    --blue:#38BDF8;
    --orange:#F97316;
    --red:#EF4444;
}
.stApp{
    background:
      linear-gradient(180deg, rgba(10,12,16,0.96) 0%, rgba(15,18,24,0.98) 100%),
      repeating-linear-gradient(45deg, var(--line1) 0px, var(--line1) 10px, transparent 10px, transparent 20px),
      repeating-linear-gradient(-45deg, var(--line2) 0px, var(--line2) 10px, transparent 10px, transparent 20px),
      linear-gradient(180deg, var(--bg1) 0%, var(--bg2) 100%);
    color:var(--text);
}
.block-container{padding-top:1rem;padding-bottom:2rem;}
h1,h2,h3,h4,h5,h6,p,label,span,div{color:var(--text);}
section[data-testid="stSidebar"]{
    background:
      linear-gradient(180deg, rgba(12,15,21,0.95) 0%, rgba(16,20,28,0.95) 100%),
      repeating-linear-gradient(45deg, rgba(255,255,255,0.03) 0px, rgba(255,255,255,0.03) 8px, transparent 8px, transparent 16px);
    border-right:1px solid rgba(255,255,255,0.08);
    backdrop-filter: blur(10px);
}
section[data-testid="stSidebar"]::before{
    content:"";
    display:block;
    height:5px;
    border-radius:999px;
    margin:0 0 14px 0;
    background:linear-gradient(90deg,var(--blue),var(--green),var(--orange));
    box-shadow:0 0 12px rgba(56,189,248,0.55);
}
.glass-hero{
    background:
      linear-gradient(135deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.03) 100%),
      repeating-linear-gradient(45deg, rgba(255,255,255,0.018) 0px, rgba(255,255,255,0.018) 10px, transparent 10px, transparent 20px);
    border:1px solid rgba(255,255,255,0.10);
    box-shadow:0 18px 40px rgba(0,0,0,0.30), inset 0 0 40px rgba(56,189,248,0.03);
    border-radius:22px;
    padding:18px 22px;
    margin-bottom:16px;
    backdrop-filter: blur(10px);
}
.glass-hero h1{
    margin:0;
    font-size:2.35rem;
    letter-spacing:-0.03em;
    color:#F8FAFC;
    text-shadow:0 0 18px rgba(56,189,248,0.10);
}
.glass-hero p{
    margin:8px 0 0 0;
    color:var(--muted);
    font-size:1.05rem;
}
div[data-testid="stMetric"]{
    background:
      linear-gradient(135deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.03) 100%),
      repeating-linear-gradient(45deg, rgba(255,255,255,0.018) 0px, rgba(255,255,255,0.018) 10px, transparent 10px, transparent 20px);
    border:1px solid rgba(255,255,255,0.10);
    border-radius:18px;
    box-shadow:0 12px 28px rgba(0,0,0,0.24);
    padding:14px;
    backdrop-filter: blur(8px);
}
div[data-testid="stMetricLabel"] > div{color:var(--muted)!important;}
div[data-testid="stMetricValue"]{color:#FFFFFF!important;text-shadow:0 0 10px rgba(56,189,248,0.10);}
[data-testid="stDataFrame"]{
    background:#FFFFFF!important;
    border-radius:16px;
    overflow:hidden;
    border:1px solid rgba(255,255,255,0.06);
}
[data-testid="stDataFrame"] *{color:#000!important;}
[data-testid="stDataFrame"] thead th{
    background:#E5E7EB!important;
    color:#000!important;
    font-weight:700!important;
}
div[data-baseweb="select"] > div{
    background:#0E1624!important;
    border:1px solid #334155!important;
    border-radius:12px!important;
    box-shadow:0 0 0 1px rgba(56,189,248,0.05), 0 0 14px rgba(56,189,248,0.06);
}
div[data-baseweb="select"] *{color:#FFFFFF!important;fill:#FFFFFF!important;}
div[role="listbox"]{background:#111827!important;}
div[role="listbox"] *{color:#FFFFFF!important;}
li[role="option"]{background:#111827!important;color:#FFFFFF!important;}
li[role="option"]:hover{background:#1F2937!important;}
li[aria-selected="true"]{background:#2563EB!important;color:#FFFFFF!important;}
div[data-testid="stNumberInput"] input{
    color:#0F172A!important;
    background:#FFFFFF!important;
    font-size:20px!important;
    font-weight:700!important;
    border-radius:12px!important;
    -webkit-text-fill-color:#0F172A!important;
}
div[data-testid="stNumberInput"] button{
    color:#0F172A!important;
    background:#E5E7EB!important;
    border-radius:8px!important;
}
.rank-card{
    background:
      linear-gradient(135deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.03) 100%),
      repeating-linear-gradient(45deg, rgba(255,255,255,0.018) 0px, rgba(255,255,255,0.018) 10px, transparent 10px, transparent 20px);
    border:1px solid rgba(255,255,255,0.10);
    border-radius:18px;
    padding:12px 14px;
    margin-bottom:12px;
    box-shadow:0 12px 28px rgba(0,0,0,0.24);
    backdrop-filter: blur(8px);
}
.rank-title{font-size:12px;color:var(--muted);margin-bottom:6px;}
.rank-item{font-size:15px;font-weight:700;color:#fff;line-height:1.25;}
.rank-value{font-size:24px;font-weight:800;color:var(--orange);margin-top:6px;}
.rank-track{
    margin-top:8px;
    height:8px;
    border-radius:999px;
    background:rgba(255,255,255,0.08);
    overflow:hidden;
}
.rank-bar{
    height:100%;
    border-radius:999px;
    background:linear-gradient(90deg, var(--orange), var(--red));
    box-shadow:0 0 16px rgba(249,115,22,0.55);
    animation:growbar 1.2s ease-out;
}
@keyframes growbar{
    from{width:0%;}
}
.panel-title{
    display:flex;
    align-items:center;
    gap:10px;
    margin:8px 0 10px 0;
    color:#F8FAFC;
    font-weight:700;
}
.panel-title .icon{
    width:28px;height:28px;border-radius:10px;
    display:inline-flex;align-items:center;justify-content:center;
    background:rgba(56,189,248,0.10);
    box-shadow:0 0 14px rgba(56,189,248,0.18);
}
hr{border-color:rgba(255,255,255,0.08);}
</style>
""", unsafe_allow_html=True)

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_FILE = BASE_DIR / "dados.xlsx"
SEMANA_ORDEM = ["Semana 1","Semana 2","Semana 3","Semana 4"]

def carregar_excel_local_ou_upload():
    uploaded = st.sidebar.file_uploader("Substituir arquivo Excel", type=["xlsx","xlsm","xls"])
    if uploaded is not None:
        return uploaded, "upload manual"
    if DEFAULT_FILE.exists():
        return DEFAULT_FILE, "arquivo padrão do repositório"
    st.error(f"Arquivo padrão não encontrado: {DEFAULT_FILE}")
    st.stop()

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
    options = [x for x in list(options) if str(x).strip() != ""]
    opcoes = ["Todos"] + options
    selecionados = st.multiselect(label, opcoes, default=["Todos"], key=key)
    if not selecionados or "Todos" in selecionados:
        return options
    return [x for x in selecionados if x in options]

@st.cache_data(show_spinner=False)
def carregar_excel(file_source):
    xls = pd.ExcelFile(file_source)
    abas_estrut = [a for a in xls.sheet_names if "estrut" in a.lower()]
    abas_saldo = [a for a in xls.sheet_names if "saldo" in a.lower()]
    if not abas_estrut or not abas_saldo:
        raise ValueError(f"Abas disponíveis: {xls.sheet_names}")
    return (
        pd.read_excel(file_source, sheet_name=abas_estrut[0]),
        pd.read_excel(file_source, sheet_name=abas_saldo[0]),
        abas_estrut[0],
        abas_saldo[0],
    )

def preparar_estruturas(df):
    base = pd.DataFrame({
        "COD_MODELO": df.iloc[:,0].apply(normalizar),
        "MODELO_DESC": df.iloc[:,1].apply(normalizar),
        "TIPO": df.iloc[:,2].apply(normalizar),
        "FAMILIA": df.iloc[:,5].apply(normalizar),
        "COMPONENTE": df.iloc[:,6].apply(normalizar),
        "DERIVACAO": df.iloc[:,7].apply(normalizar),
        "DESCRICAO_ESTRUTURA": df.iloc[:,8].apply(normalizar),
        "QTD": df.iloc[:,9].apply(to_float),
    })
    base = base[(base["COD_MODELO"] != "") & (base["TIPO"] != "") & (base["COMPONENTE"] != "")].copy()
    return base.groupby(
        ["COD_MODELO","MODELO_DESC","TIPO","FAMILIA","COMPONENTE","DERIVACAO","DESCRICAO_ESTRUTURA"],
        as_index=False
    )["QTD"].sum()

def preparar_saldo(df):
    saldo = pd.DataFrame({
        "COMPONENTE": df.iloc[:,0].apply(normalizar),
        "DESCRICAO_COMPONENTE": df.iloc[:,1].apply(normalizar),
        "SALDO": df.iloc[:,2].apply(to_float),
        "UM": df.iloc[:,3].apply(normalizar),
    })
    saldo = saldo[saldo["COMPONENTE"] != ""].copy()
    saldo = saldo.groupby("COMPONENTE", as_index=False).agg(
        DESCRICAO_COMPONENTE=("DESCRICAO_COMPONENTE", lambda s: next((x for x in s if str(x).strip() != ""), "")),
        SALDO=("SALDO", "sum"),
        UM=("UM", lambda s: next((x for x in s if str(x).strip() != ""), "")),
    )
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
        filtro["SEMANA"] = row["SEMANA"]
        filtro["NECESSIDADE"] = filtro["QTD"] * row["QTD_A_MONTAR"]
        registros.append(filtro)

    if not registros:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    detalhado = pd.concat(registros, ignore_index=True)

    consolidado = detalhado.groupby(["COMPONENTE","DESCRICAO_ESTRUTURA"], as_index=False)["NECESSIDADE"].sum().merge(saldo, on="COMPONENTE", how="left")
    consolidado["SALDO"] = consolidado["SALDO"].fillna(0)
    consolidado["DESCRICAO_COMPONENTE"] = consolidado["DESCRICAO_COMPONENTE"].fillna("")
    consolidado["UM"] = consolidado["UM"].fillna("")
    consolidado["DELTA"] = consolidado["SALDO"] - consolidado["NECESSIDADE"]
    consolidado["FALTA"] = (-consolidado["DELTA"]).clip(lower=0)
    consolidado["SOBRA"] = consolidado["DELTA"].clip(lower=0)
    consolidado["STATUS"] = consolidado["DELTA"].apply(lambda x: "OK" if x >= 0 else "RUPTURA")
    consolidado["ORDEM_GRAFICO"] = consolidado.apply(lambda x: x["FALTA"] if x["FALTA"] > 0 else x["SOBRA"], axis=1)
    consolidado = consolidado.sort_values(["ORDEM_GRAFICO","COMPONENTE"], ascending=[False, True]).reset_index(drop=True)

    semanal_item = detalhado.groupby(["SEMANA","COMPONENTE","DESCRICAO_ESTRUTURA"], as_index=False)["NECESSIDADE"].sum().merge(saldo, on="COMPONENTE", how="left")
    semanal_item["SALDO"] = semanal_item["SALDO"].fillna(0)
    semanal_item["ord"] = semanal_item["SEMANA"].apply(lambda x: SEMANA_ORDEM.index(x) if x in SEMANA_ORDEM else 999)
    semanal_item = semanal_item.sort_values(["COMPONENTE","ord"]).reset_index(drop=True)
    semanal_item["CONSUMO_ACUM_ITEM"] = semanal_item.groupby("COMPONENTE")["NECESSIDADE"].cumsum()
    semanal_item["SALDO_ANTES_ITEM"] = (semanal_item["SALDO"] - (semanal_item["CONSUMO_ACUM_ITEM"] - semanal_item["NECESSIDADE"])).clip(lower=0)
    semanal_item["SALDO_APOS_ITEM"] = (semanal_item["SALDO"] - semanal_item["CONSUMO_ACUM_ITEM"]).clip(lower=0)
    semanal_item["RUPTURA_ITEM"] = (semanal_item["NECESSIDADE"] - semanal_item["SALDO_ANTES_ITEM"]).clip(lower=0)

    resumo = semanal_item.groupby("SEMANA", as_index=False).agg(
        NECESSIDADE=("NECESSIDADE","sum"),
        SALDO_ANTES_SEMANA=("SALDO_ANTES_ITEM","sum"),
        SALDO_APOS_SEMANA=("SALDO_APOS_ITEM","sum"),
        RUPTURA_SEMANA=("RUPTURA_ITEM","sum"),
    )
    resumo["ord"] = resumo["SEMANA"].apply(lambda x: SEMANA_ORDEM.index(x) if x in SEMANA_ORDEM else 999)
    resumo = resumo.sort_values("ord").reset_index(drop=True)
    resumo["COBERTURA_PCT"] = resumo.apply(lambda r: 0 if r["NECESSIDADE"] <= 0 else min((r["SALDO_ANTES_SEMANA"] / r["NECESSIDADE"]) * 100, 100.0), axis=1)
    resumo["STATUS_SEMANA"] = resumo["RUPTURA_SEMANA"].apply(lambda x: "RUPTURA" if x > 0 else "OK")
    return detalhado, consolidado, resumo

def grafico_barras_tesla(df):
    plot_df = df.copy().sort_values("ORDEM_GRAFICO", ascending=False).reset_index(drop=True)
    eixo_y = [f"{c} - {d if d else e}" for c, d, e in zip(plot_df["COMPONENTE"], plot_df["DESCRICAO_COMPONENTE"], plot_df["DESCRICAO_ESTRUTURA"])]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=plot_df["NECESSIDADE"], y=eixo_y, orientation="h", name="Necessidade", marker=dict(color="#54657C")))
    fig.add_trace(go.Bar(x=plot_df["SALDO"], y=eixo_y, orientation="h", name="Saldo", marker=dict(color=["#22C55E" if d >= 0 else "#EF4444" for d in plot_df["DELTA"]])))
    fig.add_trace(go.Scatter(
        x=plot_df["SALDO"], y=eixo_y, mode="markers+text", name="Delta",
        text=[f"Δ {formatar_compacto(v)}" for v in plot_df["DELTA"]],
        textposition="middle right",
        marker=dict(size=12, color=["#F97316" if v < 0 else "#38BDF8" for v in plot_df["DELTA"]], symbol="diamond")
    ))
    fig.add_vline(x=0, line_width=1, line_color="rgba(255,255,255,0.25)")
    fig.update_layout(
        barmode="overlay", height=max(580, len(plot_df) * 38),
        title="📡 Painel Andon Fábrica 4.0 - Ruptura e Estoque",
        xaxis_title="Quantidade", yaxis_title="Componente",
        paper_bgcolor="rgba(12,16,22,0.72)", plot_bgcolor="rgba(12,16,22,0.52)",
        font=dict(color="#E8EEF7"), legend_title="Indicadores", margin=dict(l=10, r=20, t=60, b=10)
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.08)", zeroline=False)
    fig.update_yaxes(autorange="reversed", automargin=True)
    return fig

def grafico_semanal_status(df):
    cores = ["#EF4444" if s == "RUPTURA" else "#22C55E" for s in df["STATUS_SEMANA"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["SEMANA"], y=df["NECESSIDADE"], width=[0.50]*len(df), offsetgroup="n",
        name="Necessidade", marker=dict(color=cores, line=dict(color="rgba(255,255,255,0.15)", width=1)),
        text=[formatar_compacto(v) for v in df["NECESSIDADE"]], textposition="outside"
    ))
    fig.add_trace(go.Bar(
        x=df["SEMANA"], y=df["RUPTURA_SEMANA"], width=[0.32]*len(df), offsetgroup="r",
        name="Ruptura", marker=dict(color="#F97316", line=dict(color="rgba(255,255,255,0.10)", width=1)),
        text=[formatar_compacto(v) if v > 0 else "" for v in df["RUPTURA_SEMANA"]], textposition="outside"
    ))
    fig.add_trace(go.Scatter(
        x=df["SEMANA"], y=df["SALDO_APOS_SEMANA"], name="Saldo restante",
        mode="lines+markers+text",
        text=[f"Saldo {formatar_compacto(v)}" for v in df["SALDO_APOS_SEMANA"]],
        textposition="top center",
        line=dict(color="#38BDF8", width=3),
        marker=dict(size=9, color="#38BDF8")
    ))
    fig.update_layout(
        title="🏭 Simulação de Produção por Semana - Sala de Controle",
        xaxis_title="Semana", yaxis_title="Quantidade",
        bargap=0.14,
        paper_bgcolor="rgba(12,16,22,0.72)", plot_bgcolor="rgba(12,16,22,0.52)",
        font=dict(color="#E8EEF7"), margin=dict(l=10, r=20, t=60, b=10),
        height=600, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0)
    )
    ymax = max(float(df["NECESSIDADE"].max()) if len(df) else 0, float(df["SALDO_APOS_SEMANA"].max()) if len(df) else 0, 1)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.08)", range=[0, ymax*1.22])
    return fig


def termometro(valor, maximo, titulo, cor):
    maximo = max(maximo, 1)
    zona_verde = maximo * 0.33
    zona_amarela = maximo * 0.66

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=valor,
        number={"font": {"size": 38, "color": "#FFFFFF"}},
        title={"text": titulo, "font": {"size": 18, "color": "#E5E7EB"}},
        gauge={
            "shape": "angular",
            "axis": {"range": [0, maximo], "tickwidth": 1, "tickcolor": "#64748B"},
            "bar": {"color": cor, "thickness": 0.35},
            "bgcolor": "#0B1220",
            "steps": [
                {"range": [0, zona_verde], "color": "#10241A"},
                {"range": [zona_verde, zona_amarela], "color": "#2B2410"},
                {"range": [zona_amarela, maximo], "color": "#2B1515"}
            ],
            "threshold": {"line": {"color": "#F8FAFC", "width": 5},
                          "thickness": 0.85,
                          "value": valor}
        }
    ))

    fig.update_layout(
        height=285,
        margin=dict(l=10, r=10, t=60, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E8EEF7")
    )
    return fig

def mini_tabela(df):
    base = df.copy()
    base["DELTA_FMT"] = base["DELTA"].apply(formatar_compacto)
    base["SALDO_FMT"] = base["SALDO"].apply(formatar_compacto)
    base["NECESS_FMT"] = base["NECESSIDADE"].apply(formatar_compacto)
    base["FALTA_FMT"] = base["FALTA"].apply(formatar_compacto)
    mini = base[["COMPONENTE","DESCRICAO_COMPONENTE","NECESS_FMT","SALDO_FMT","DELTA_FMT","FALTA_FMT","STATUS"]].copy()
    mini.columns = ["COMPONENTE","DESCRIÇÃO","NECESSIDADE","SALDO","DELTA","FALTA","STATUS"]
    return mini.head(10)

def colorir_linhas_por_status(row):
    if row["STATUS"] == "OK":
        return ["background-color: rgba(34,197,94,0.18); color: #000000;"] * len(row)
    return ["background-color: rgba(239,68,68,0.18); color: #000000;"] * len(row)

def converter_excel_download(df_consolidado, df_detalhado, df_resumo, df_selecoes, df_resumo_semanal):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_consolidado.to_excel(writer, index=False, sheet_name="Simulacao_Consolidada")
        df_detalhado.to_excel(writer, index=False, sheet_name="Simulacao_Detalhada")
        df_selecoes.to_excel(writer, index=False, sheet_name="Selecoes_Modelo_Derivacao")
        df_resumo_semanal.to_excel(writer, index=False, sheet_name="Resumo_Semanal")
        df_resumo.to_excel(writer, index=False, sheet_name="Resumo")
    output.seek(0)
    return output

st.markdown('<div class="glass-hero"><h1>🏭 Painel Andon de Suprimentos 4.0</h1><p>Fundo xadrez metálico, glow nos gráficos, cards estilo Tesla/PowerBI, efeito glassmorphism e layout de sala de controle.</p></div>', unsafe_allow_html=True)

file_source, origem = carregar_excel_local_ou_upload()
df_e, df_s, aba_e, aba_s = carregar_excel(file_source)
base = preparar_estruturas(df_e)
saldo = preparar_saldo(df_s)

st.success(f"Arquivo carregado com sucesso. Origem: {origem}. Estruturas: {aba_e} | Saldo: {aba_s}")

st.markdown('<div class="panel-title"><span class="icon">⚙️</span><span>Filtros</span></div>', unsafe_allow_html=True)
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

st.markdown('<div class="panel-title"><span class="icon">🧩</span><span>Seleção por COD. Modelo, Derivação e Semana</span></div>', unsafe_allow_html=True)
linhas_selecao = []
for idx, cod_modelo in enumerate(cod_modelos_sel, start=1):
    subset = base[(base["TIPO"].isin(tipos_sel)) & (base["FAMILIA"].isin(familias_sel)) & (base["COD_MODELO"] == cod_modelo)].copy()
    descs = [x for x in subset["MODELO_DESC"].dropna().unique().tolist() if str(x).strip() != ""]
    desc = descs[0] if descs else ""
    derivs = sorted([x for x in subset["DERIVACAO"].unique().tolist() if str(x).strip() != ""], key=lambda x: str(x))
    st.markdown(f"### COD. Modelo {cod_modelo}" + (f" — {desc}" if desc else ""))
    for j, deriv in enumerate(derivs, start=1):
        qtd_linhas = st.selectbox(f"Quantidade de lançamentos para derivação {deriv} - {cod_modelo}", [0,1,2,3,4], index=0, key=f"nlin_{idx}_{j}")
        for linha in range(1, qtd_linhas + 1):
            cols = st.columns([2,2,2,2])
            with cols[0]:
                st.text_input(f"Derivação {cod_modelo}-{j}-{linha}", value=str(deriv), disabled=True, key=f"der_{idx}_{j}_{linha}")
            with cols[1]:
                semana = st.selectbox(f"Semana {cod_modelo}-{j}-{linha}", SEMANA_ORDEM, key=f"sem_{idx}_{j}_{linha}")
            with cols[2]:
                qtd = st.number_input(f"Qtd. {cod_modelo}-{j}-{linha}", min_value=0, value=0, step=1, key=f"qtd_{idx}_{j}_{linha}")
            with cols[3]:
                usar = st.checkbox("Selecionar", value=(qtd > 0), key=f"usar_{idx}_{j}_{linha}")
            if usar and qtd > 0:
                linhas_selecao.append({"COD_MODELO": cod_modelo, "MODELO_DESC": desc, "DERIVACAO": deriv, "SEMANA": semana, "QTD_A_MONTAR": qtd})

df_selecoes = pd.DataFrame(linhas_selecao)
if df_selecoes.empty:
    st.warning("Selecione pelo menos um lançamento com quantidade maior que zero.")
    st.stop()

detalhado, consolidado, resumo_semanal = simular(base, saldo, tipos_sel, familias_sel, df_selecoes)
consolidado = consolidado[consolidado["STATUS"].isin(andon_sel)].copy()

total_nec = float(consolidado["NECESSIDADE"].sum())
total_saldo = float(consolidado["SALDO"].sum())
total_delta = float(consolidado["DELTA"].sum())
total_falta = float(consolidado["FALTA"].sum())
cobertura_percentual = 0 if total_nec == 0 else min((total_saldo / total_nec) * 100, 100.0)

st.markdown('<div class="panel-title"><span class="icon">📊</span><span>Indicadores</span></div>', unsafe_allow_html=True)
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Necessidade", formatar_compacto(total_nec))
m2.metric("Saldo", formatar_compacto(total_saldo))
m3.metric("Delta", formatar_compacto(total_delta))
m4.metric("Faltante", formatar_compacto(total_falta))
m5.metric("Cobertura", f"{cobertura_percentual:.1f}%")

st.markdown('<div class="panel-title"><span class="icon">🚨</span><span>Ranking das 10 maiores rupturas</span></div>', unsafe_allow_html=True)
ranking = consolidado[consolidado["FALTA"] > 0].copy().sort_values("FALTA", ascending=False).head(10)
if ranking.empty:
    st.success("Não há rupturas para exibir no ranking.")
else:
    max_falta = max(float(ranking["FALTA"].max()), 1.0)
    r1, r2 = st.columns(2)
    with r1:
        for idx, (_, row) in enumerate(ranking.iloc[:5].iterrows(), start=1):
            largura = (float(row["FALTA"]) / max_falta) * 100
            st.markdown(
                f'<div class="rank-card"><div class="rank-title">#{idx} maior ruptura</div>'
                f'<div class="rank-item">{row["COMPONENTE"]} - {row["DESCRICAO_COMPONENTE"] or row["DESCRICAO_ESTRUTURA"]}</div>'
                f'<div class="rank-value">{formatar_compacto(row["FALTA"])}</div>'
                f'<div class="rank-track"><div class="rank-bar" style="width:{largura:.1f}%"></div></div></div>',
                unsafe_allow_html=True
            )
    with r2:
        for idx, (_, row) in enumerate(ranking.iloc[5:10].iterrows(), start=6):
            largura = (float(row["FALTA"]) / max_falta) * 100
            st.markdown(
                f'<div class="rank-card"><div class="rank-title">#{idx} maior ruptura</div>'
                f'<div class="rank-item">{row["COMPONENTE"]} - {row["DESCRICAO_COMPONENTE"] or row["DESCRICAO_ESTRUTURA"]}</div>'
                f'<div class="rank-value">{formatar_compacto(row["FALTA"])}</div>'
                f'<div class="rank-track"><div class="rank-bar" style="width:{largura:.1f}%"></div></div></div>',
                unsafe_allow_html=True
            )

st.markdown('<div class="panel-title"><span class="icon">📈</span><span>Indicadores e Cobertura de Estoque</span></div>', unsafe_allow_html=True)
t1, t2, t3, t4 = st.columns(4)
with t1:
    st.plotly_chart(termometro(total_nec, max(total_nec, total_saldo), "Necessidade", "#64748B"), use_container_width=True)
with t2:
    st.plotly_chart(termometro(total_saldo, max(total_nec, total_saldo), "Saldo", "#22C55E"), use_container_width=True)
with t3:
    st.plotly_chart(termometro(abs(total_delta), max(abs(total_delta), total_nec), "Delta", "#38BDF8"), use_container_width=True)
with t4:
    st.plotly_chart(termometro(cobertura_percentual, max(cobertura_percentual, 100), "Cobertura %", "#F59E0B"), use_container_width=True)

st.markdown('<div class="panel-title"><span class="icon">🖥️</span><span>Dashboard Sala de Controle</span></div>', unsafe_allow_html=True)
g1, g2 = st.columns([1.0, 1.7])
with g1:
    st.plotly_chart(grafico_barras_tesla(consolidado), use_container_width=True)
with g2:
    st.plotly_chart(grafico_semanal_status(resumo_semanal), use_container_width=True)

st.markdown('<div class="panel-title"><span class="icon">📅</span><span>Resumo semanal</span></div>', unsafe_allow_html=True)
st.dataframe(resumo_semanal[["SEMANA","NECESSIDADE","SALDO_ANTES_SEMANA","SALDO_APOS_SEMANA","RUPTURA_SEMANA","COBERTURA_PCT","STATUS_SEMANA"]], use_container_width=True, height=240)

st.markdown('<div class="panel-title"><span class="icon">📦</span><span>Mini tabela abaixo dos gráficos</span></div>', unsafe_allow_html=True)
st.dataframe(mini_tabela(consolidado).style.apply(colorir_linhas_por_status, axis=1), use_container_width=True, height=320)

st.markdown('<div class="panel-title"><span class="icon">🗂️</span><span>Tabela de seleções por modelo, derivação e semana</span></div>', unsafe_allow_html=True)
st.dataframe(df_selecoes, use_container_width=True, height=260)

st.markdown('<div class="panel-title"><span class="icon">🧾</span><span>Tabela consolidada</span></div>', unsafe_allow_html=True)
tabela = consolidado[["COMPONENTE","DESCRICAO_COMPONENTE","DESCRICAO_ESTRUTURA","NECESSIDADE","SALDO","UM","DELTA","FALTA","SOBRA","STATUS"]].copy()
for col in ["NECESSIDADE","SALDO","DELTA","FALTA","SOBRA"]:
    tabela[col] = tabela[col].round(3)
st.dataframe(tabela, use_container_width=True, height=430)

resumo = pd.DataFrame({"Indicador":["Necessidade","Saldo","Delta","Faltante","Cobertura %"],"Valor":[round(total_nec,3),round(total_saldo,3),round(total_delta,3),round(total_falta,3),round(cobertura_percentual,2)]})
arquivo = converter_excel_download(tabela, detalhado, resumo, df_selecoes, resumo_semanal)
st.download_button("Baixar simulação em Excel", data=arquivo, file_name="simulacao_suprimentos_tesla_v36.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
