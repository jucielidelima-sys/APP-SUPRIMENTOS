
from io import BytesIO
from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="Painel Andon de Suprimentos", layout="wide")

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_FILE = BASE_DIR / "dados.xlsx"

def load_file():
    up = st.sidebar.file_uploader("Substituir Excel", type=["xlsx"])
    if up:
        return up
    if DEFAULT_FILE.exists():
        return DEFAULT_FILE
    st.error("dados.xlsx não encontrado")
    st.stop()

def to_float(v):
    if pd.isna(v): return 0
    if isinstance(v,(int,float)): return v
    return float(str(v).replace(".","").replace(",",".") or 0)

file = load_file()

xls = pd.ExcelFile(file)
aba_e = [s for s in xls.sheet_names if "estrut" in s.lower()][0]
aba_s = [s for s in xls.sheet_names if "saldo" in s.lower()][0]

df_e = pd.read_excel(file, sheet_name=aba_e)
df_s = pd.read_excel(file, sheet_name=aba_s)

base = pd.DataFrame({
    "COD_MODELO": df_e.iloc[:,0].astype(str),
    "DERIVACAO": df_e.iloc[:,7].astype(str),
    "ITEM": df_e.iloc[:,8].astype(str),
    "QTD": df_e.iloc[:,9].apply(to_float)
})

saldo = pd.DataFrame({
    "ITEM": df_s.iloc[:,2].astype(str),
    "SALDO": df_s.iloc[:,3].apply(to_float)
})

saldo = saldo.groupby("ITEM",as_index=False).sum()

st.title("⚡ Painel Andon de Suprimentos")

modelos = sorted(base["COD_MODELO"].unique())
modelo_sel = st.multiselect("Modelo", modelos)

semanas = ["Semana 1","Semana 2","Semana 3","Semana 4"]

selecoes = []

for m in modelo_sel:
    st.subheader(f"Modelo {m}")
    derivs = base[base["COD_MODELO"]==m]["DERIVACAO"].unique()

    for d in derivs:
        c1,c2,c3 = st.columns(3)
        with c1:
            st.write("Derivação",d)
        with c2:
            sem_sel = st.multiselect(f"Semanas {m}-{d}",semanas)
        with c3:
            qtd = st.number_input(f"Qtd {m}-{d}",0,step=1)

        for s in sem_sel:
            if qtd>0:
                selecoes.append((m,d,s,qtd))

if not selecoes:
    st.stop()

df_sel = pd.DataFrame(selecoes,columns=["MODELO","DERIV","SEMANA","QTD"])

reg=[]
for _,r in df_sel.iterrows():
    f=base[(base["COD_MODELO"]==r.MODELO)&(base["DERIVACAO"]==r.DERIV)].copy()
    f["NECESSIDADE"]=f["QTD"]*r.QTD
    f["SEMANA"]=r.SEMANA
    reg.append(f)

det=pd.concat(reg)

cons=det.groupby("ITEM",as_index=False)["NECESSIDADE"].sum()
cons=cons.merge(saldo,on="ITEM",how="left").fillna(0)
cons["DELTA"]=cons["SALDO"]-cons["NECESSIDADE"]
cons["FALTA"]=(-cons["DELTA"]).clip(lower=0)

st.subheader("Resumo")
st.metric("Necessidade",int(cons["NECESSIDADE"].sum()))
st.metric("Saldo",int(cons["SALDO"].sum()))
st.metric("Faltante",int(cons["FALTA"].sum()))

fig=go.Figure()
fig.add_bar(y=cons["ITEM"],x=cons["NECESSIDADE"],orientation="h",name="Necessidade")
fig.add_bar(y=cons["ITEM"],x=cons["SALDO"],orientation="h",name="Saldo")
st.plotly_chart(fig,use_container_width=True)

out=BytesIO()
with pd.ExcelWriter(out,engine="openpyxl") as w:
    cons.to_excel(w,index=False)

st.download_button("Exportar Excel",out.getvalue(),"simulacao.xlsx")
