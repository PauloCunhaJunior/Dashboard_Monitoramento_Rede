"""Dashboard de monitoramento de tráfego (snapshot): Streamlit + Plotly."""
from __future__ import annotations

import hashlib
from html import escape
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analise import (
    filtrar_dados, indicadores, ler_dados, obter_incidentes,
    por_categoria, por_departamento, top_destinos, top_usuarios,
)
from relatorio import gerar_relatorio_html

RAIZ = Path(__file__).resolve().parent
CSV_PADRAO = RAIZ / "dados" / "trafego_rede.csv"
COR_CIANO = "#30C8ED"
COR_VERDE = "#2FD7B5"
COR_AMARELA = "#F6BE67"
COR_VERMELHA = "#FA7086"
COR_ROXA = "#B4A2F2"
COR_TEXTO = "#EAF3FC"
COR_MUTED = "#93A9C1"

st.set_page_config(
    page_title="NOC | Monitoramento de tráfego",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
:root {color-scheme:dark;}
.stApp {background: #081626;}
[data-testid="stSidebar"] {background: #0C2032; border-right:1px solid #234258;}
[data-testid="stSidebar"] .stMarkdown p {color: #BACDE0;}
[data-testid="stMetric"] {background: linear-gradient(150deg,#122C41,#0D2236);border: 1px solid #27475F;
  border-radius: 14px; padding: 17px 20px; box-shadow: 0 6px 24px #04101b40;}
[data-testid="stMetricLabel"] {color: #AAC0D4; font-weight:600;}
[data-testid="stMetricValue"] {color: #F0F8FF; font-weight:750;}
[data-testid="stMetricDelta"] {color: #94ADC5;}
[data-testid="stVerticalBlockBorderWrapper"] > div {border-color:#25465d!important; border-radius:16px!important;}
.stTabs [data-baseweb="tab-list"] {gap:10px;border-bottom:1px solid #29475e;}
.stTabs [data-baseweb="tab"] {border-radius:9px 9px 0 0; padding:8px 14px;}
.stTabs [aria-selected="true"] {color:#54DAF6; border-bottom-color:#30C8ED;}
h1,h2,h3 {letter-spacing:-0.025em;}
.hero-box {padding:23px 28px; background:linear-gradient(104deg,#113858 0%,#113151 53%,#1A2A56 100%);
 border:1px solid #2F6079; border-radius:17px; margin-bottom:15px;box-shadow: 0 10px 25px #040c1944;}
.hero-eyebrow {font-size:12px;letter-spacing:.15em;color:#63D8EE;font-weight:800;margin-bottom:4px;}
.hero-title {font-size:31px;line-height:1.25;color:#FFFFFF;letter-spacing:-.03em;font-weight:800;margin-bottom:8px;}
.hero-copy {font-size:14px;color:#BDD9EE; margin:0;line-height:1.5;}
.pill {display:inline-block;background:#164F64;border:1px solid #288A9D;border-radius:30px;
 color:#A7F5FF;padding:4px 11px;font-size:11px;font-weight:800;white-space:nowrap;margin-top:11px;}
.section-title {font-size:17px;font-weight:750;color:#E9F4FF;letter-spacing:-.01em;margin-bottom:0;}
.helper-copy {font-size:12px;color:#A6BCD0;margin-bottom:8px;}
.small-banner {padding:10px 13px;color:#C5DEED;background:#0D2D41;border:1px solid #21536A;
 border-radius:10px;font-size:12px;line-height:1.6;margin:4px 0 15px 0;}
.badge-risk {font-size:12px;color:#FFBDC6;background:#502733;padding:3px 10px;border-radius:20px;}
[data-testid="stDataFrame"] {border-radius:10px;overflow:hidden;}
footer {visibility:hidden;}
</style>
""", unsafe_allow_html=True)


def br_int(valor: int | float) -> str:
    return f"{valor:,.0f}".replace(",", ".")


def br_num(valor: float, casas: int = 1) -> str:
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_volume_mb(mb: float) -> str:
    return f"{br_num(mb / 1024, 2)} GB" if mb >= 1024 else f"{br_num(mb, 1)} MB"


def estilizar_figura(fig: go.Figure, altura: int = 345, horizontal: bool = False) -> go.Figure:
    fig.update_layout(
        height=altura,
        margin=dict(l=5, r=12, t=8, b=25),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Arial,sans-serif", size=12, color=COR_TEXTO),
        hoverlabel=dict(bgcolor="#173650", font=dict(color=COR_TEXTO, size=12)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    fig.update_xaxes(showgrid=not horizontal, gridcolor="#254052", zeroline=False,
                     tickfont=dict(color=COR_MUTED, size=11), showline=False, automargin=True)
    fig.update_yaxes(showgrid=horizontal, gridcolor="#254052", zeroline=False,
                     tickfont=dict(color=COR_MUTED, size=11), showline=False, automargin=True)
    return fig


def barra_horizontal(rotulos, valores, *, cor: str = COR_CIANO,
                     sufixo: str = " MB", textos=None, altura: int = 355) -> go.Figure:
    fig = go.Figure(go.Bar(
        x=list(valores)[::-1], y=list(rotulos)[::-1], orientation="h",
        marker=dict(color=cor, line=dict(width=0), cornerradius=5),
        text=list(textos)[::-1] if textos is not None else None,
        textposition="auto", textfont=dict(color="#E9F8FF", size=11),
        customdata=list(valores)[::-1],
        hovertemplate="%{y}<br><b>%{x:,.1f}" + sufixo + "</b><extra></extra>",
    ))
    fig = estilizar_figura(fig, altura=altura)
    fig.update_layout(xaxis_title=None, yaxis_title=None, bargap=0.34)
    fig.update_yaxes(showgrid=False)
    return fig


def grafico_usuarios(tabela: pd.DataFrame) -> go.Figure:
    top = top_usuarios(tabela)
    fig = go.Figure(go.Bar(
        y=top["user_name"].tolist()[::-1], x=top["volume_mb"].tolist()[::-1], orientation="h",
        marker=dict(color=COR_CIANO, line=dict(width=0), cornerradius=5),
        customdata=top[["department", "conexoes"]].to_numpy()[::-1],
        hovertemplate="<b>%{y}</b><br>%{x:,.1f} MB<br>Setor: %{customdata[0]}<br>Conexões: %{customdata[1]}<extra></extra>",
    ))
    return estilizar_figura(fig, altura=400)


def grafico_departamentos(tabela: pd.DataFrame) -> go.Figure:
    dados = por_departamento(tabela)
    return barra_horizontal(dados["department"], dados["volume_mb"], cor=COR_ROXA,
                            altura=max(380, len(dados) * 28 + 45))


def grafico_upload_download(tabela: pd.DataFrame) -> go.Figure:
    soma = indicadores(tabela)
    fig = go.Figure(go.Pie(
        labels=["Download", "Upload"], values=[soma["download_mb"], soma["upload_mb"]],
        hole=0.68, sort=False,
        marker=dict(colors=[COR_CIANO, COR_VERDE], line=dict(color="#0c2032", width=3)),
        textinfo="percent", textfont=dict(size=13, color="#FFFFFF"),
        hovertemplate="<b>%{label}</b><br>%{value:,.1f} MB<br>%{percent}<extra></extra>",
    ))
    fig = estilizar_figura(fig, altura=340)
    fig.update_layout(showlegend=True, legend=dict(x=0.5, xanchor="center", y=-0.05,
                                                    orientation="h", font=dict(size=12)))
    fig.add_annotation(x=0.5, y=0.52, text="VOLUME", showarrow=False,
                       font=dict(size=12, color=COR_MUTED))
    fig.add_annotation(x=0.5, y=0.43, text=formatar_volume_mb(soma["volume_mb"]),
                       showarrow=False, font=dict(size=21, color=COR_TEXTO))
    return fig


def grafico_horas(tabela: pd.DataFrame) -> go.Figure:
    base = (tabela.assign(horario=tabela["timestamp"].dt.floor("h"))
            .groupby("horario", as_index=False)
            .agg(volume_mb=("volume_mb", "sum"),
                 bloqueios=("action", lambda s: int(s.eq("BLOCKED").sum()))))
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=base["horario"], y=base["volume_mb"], name="Volume (MB)",
        mode="lines+markers", fill="tozeroy",
        line=dict(color=COR_CIANO, width=3), marker=dict(size=6),
        fillcolor="rgba(48,200,237,0.13)",
        hovertemplate="%{x|%d/%m %Hh}<br>%{y:,.0f} MB<extra>Tráfego</extra>",
    ))
    fig.add_trace(go.Bar(
        x=base["horario"], y=base["bloqueios"], name="Bloqueios",
        marker_color=COR_VERMELHA, opacity=.73, yaxis="y2",
        hovertemplate="%{x|%d/%m %Hh}<br>%{y} bloqueios<extra></extra>",
    ))
    fig = estilizar_figura(fig, altura=340)
    fig.update_layout(
        yaxis=dict(title="MB", showgrid=True, gridcolor="#254052", zeroline=False,
                   tickfont=dict(color=COR_MUTED)),
        yaxis2=dict(title="Bloqueios", overlaying="y", side="right", showgrid=False,
                    tickfont=dict(color=COR_MUTED), rangemode="tozero"),
        barmode="overlay", hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    fig.update_xaxes(tickformat="%Hh", title=None)
    return fig


def grafico_destinos(tabela: pd.DataFrame) -> go.Figure:
    dest = top_destinos(tabela)
    fig = go.Figure(go.Bar(
        y=dest["dest_domain"].tolist()[::-1],
        x=dest["conexoes"].tolist()[::-1], orientation="h",
        customdata=dest[["category", "volume_mb"]].to_numpy()[::-1],
        marker=dict(color=COR_VERDE, cornerradius=5),
        hovertemplate="<b>%{y}</b><br>%{x} conexões<br>Categoria: %{customdata[0]}"
                      "<br>Volume: %{customdata[1]:,.1f} MB<extra></extra>",
    ))
    return estilizar_figura(fig, altura=400)


def grafico_categorias(tabela: pd.DataFrame) -> go.Figure:
    cat = por_categoria(tabela)
    return barra_horizontal(cat["category"], cat["volume_mb"], cor=COR_ROXA, altura=400)


def grafico_acoes(tabela: pd.DataFrame) -> go.Figure:
    ordem = ["ALLOWED", "ALERT", "BLOCKED"]
    contagens = tabela["action"].value_counts()
    fig = go.Figure(go.Pie(
        labels=ordem, values=[int(contagens.get(x, 0)) for x in ordem],
        hole=.66, sort=False, marker=dict(colors=[COR_VERDE, COR_AMARELA, COR_VERMELHA],
                                          line=dict(color="#0c2032", width=3)),
        textinfo="percent", textfont=dict(size=13),
        hovertemplate="<b>%{label}</b><br>%{value} conexões (%{percent})<extra></extra>",
    ))
    fig = estilizar_figura(fig, altura=320)
    fig.update_layout(legend=dict(orientation="h", xanchor="center", x=.5, y=-.07))
    fig.add_annotation(x=.5, y=.52, text="TOTAL", showarrow=False,
                       font=dict(color=COR_MUTED, size=12))
    fig.add_annotation(x=.5, y=.42, text=br_int(len(tabela)), showarrow=False,
                       font=dict(color=COR_TEXTO, size=22))
    return fig


@st.cache_data(show_spinner=False)
def carregar_csv(bytes_csv: bytes) -> pd.DataFrame:
    return ler_dados(bytes_csv)


with st.sidebar:
    st.markdown("## 🌐 Network Operations")
    st.caption("TRÁFEGO CORPORATIVO · ANÁLISE DE SNAPSHOT")
    st.divider()
    st.markdown("### Fonte de dados")
    arquivo = st.file_uploader("Substituir CSV (opcional)", type=["csv"],
                               help="Selecione um novo CSV com as 23 colunas do exercício.")

try:
    if arquivo is not None:
        conteudo = arquivo.getvalue()
        nome_fonte = arquivo.name
    else:
        conteudo = CSV_PADRAO.read_bytes()
        nome_fonte = CSV_PADRAO.name
    dados = carregar_csv(conteudo)
except (OSError, ValueError, pd.errors.ParserError, UnicodeError) as erro:
    st.error(f"Não foi possível carregar o CSV: {erro}")
    st.stop()

with st.sidebar:
    st.caption(f"Fonte ativa: **{nome_fonte}** · {br_int(len(dados))} linhas")
    st.divider()
    st.markdown("### Filtros globais")
    st.caption("Nenhuma opção marcada = exibir todas.")
    departamentos = st.multiselect("Departamento", sorted(dados["department"].unique().tolist()),
                                   placeholder="Todos os departamentos")
    usuarios = st.multiselect("Colaborador", sorted(dados["user_name"].unique().tolist()),
                              placeholder="Todos os colaboradores")
    categorias = st.multiselect("Categoria", sorted(dados["category"].unique().tolist()),
                                placeholder="Todas as categorias")
    acoes = st.multiselect("Ação", sorted(dados["action"].unique().tolist()),
                           placeholder="Todas as ações")
    riscos = st.multiselect("Risco", [r for r in ["Baixo", "Médio", "Alto"] if r in dados["threat_risk"].unique()],
                           placeholder="Todos os níveis")
    with st.expander("Filtros adicionais"):
        protocolos = st.multiselect("Protocolo", sorted(dados["protocol"].unique().tolist()),
                                    placeholder="Todos os protocolos")
        datas_possiveis = sorted(dados["data"].unique().tolist())
        datas = st.multiselect("Data", datas_possiveis, format_func=lambda d: d.strftime("%d/%m/%Y"),
                               placeholder="Todas as datas")
    menor_hora = int(dados["hora"].min())
    maior_hora = int(dados["hora"].max())
    if menor_hora < maior_hora:
        horas = st.slider("Faixa de horas", min_value=menor_hora, max_value=maior_hora,
                          value=(menor_hora, maior_hora), format="%d h")
    else:
        horas = (menor_hora, maior_hora)
        st.caption(f"Hora disponível: {menor_hora:02d}h")
    st.divider()
    st.info("**Fonte estática:** o arquivo representa registros já coletados; não é uma captura automática da rede.")
    st.caption("Para preservar dados de colaboradores, mantenha o painel local ou em ambiente autorizado.")

filtrados = filtrar_dados(
    dados, departamentos=departamentos, usuarios=usuarios, categorias=categorias,
    acoes=acoes, riscos=riscos, protocolos=protocolos, datas=datas, horas=horas,
)

primeira = dados["timestamp"].min().strftime("%d/%m/%Y %H:%M")
ultima = dados["timestamp"].max().strftime("%d/%m/%Y %H:%M")
st.markdown(
    f'<div class="hero-box"><div class="hero-eyebrow">NOC · ANÁLISE DE TRÁFEGO</div>'
    f'<div class="hero-title">Dashboard de Monitoramento de Rede</div>'
    f'<p class="hero-copy">Usuários, departamentos, tráfego, destinos e eventos de segurança '
    f'&nbsp;•&nbsp; Período da base: {escape(primeira)} a {escape(ultima)}</p>'
    f'<span class="pill">● SNAPSHOT HISTÓRICO · CSV</span></div>', unsafe_allow_html=True,
)

if filtrados.empty:
    st.warning("Nenhuma sessão corresponde aos filtros escolhidos. Ajuste os filtros na barra lateral.")
    st.stop()

k = indicadores(filtrados)
linhas_1 = st.columns(4)
linhas_1[0].metric("Conexões registradas", br_int(k["sessoes"]))
linhas_1[1].metric("Colaboradores", br_int(k["usuarios"]))
linhas_1[2].metric("Departamentos", br_int(k["departamentos"]))
linhas_1[3].metric("Volume registrado", formatar_volume_mb(k["volume_mb"]))
linhas_2 = st.columns(4)
linhas_2[0].metric("Conexões bloqueadas", br_int(k["bloqueados"]))
linhas_2[1].metric("Risco alto", br_int(k["alto"]))
linhas_2[2].metric("Alertas (ALERT)", br_int(k["alertas"]))
linhas_2[3].metric("Taxa de bloqueio", f"{br_num(k['taxa_bloqueio'], 1)}%")
st.caption(f"Indicadores calculados sobre {br_int(len(filtrados))} sessões filtradas, de {br_int(len(dados))} no arquivo original.")

aba_geral, aba_destinos, aba_seguranca, aba_dados = st.tabs([
    "📊 Visão geral", "🌍 Destinos e categorias", "🛡️ Segurança e incidentes", "🗂️ Dados e metodologia",
])

with aba_geral:
    st.write("")
    esq, dir_ = st.columns([1.1, 1], gap="large")
    with esq:
        with st.container(border=True):
            st.markdown('<div class="section-title">Top 10 usuários por consumo</div>', unsafe_allow_html=True)
            st.markdown('<div class="helper-copy">Ranking pelo volume total registrado, em MB</div>', unsafe_allow_html=True)
            st.plotly_chart(grafico_usuarios(filtrados), use_container_width=True,
                            config={"displayModeBar": False})
    with dir_:
        with st.container(border=True):
            st.markdown('<div class="section-title">Consumo por departamento</div>', unsafe_allow_html=True)
            st.markdown('<div class="helper-copy">Soma do tráfego de cada setor, em MB</div>', unsafe_allow_html=True)
            st.plotly_chart(grafico_departamentos(filtrados), use_container_width=True,
                            config={"displayModeBar": False})

    esq, dir_ = st.columns([1, 1.3], gap="large")
    with esq:
        with st.container(border=True):
            st.markdown('<div class="section-title">Upload × Download</div>', unsafe_allow_html=True)
            st.markdown('<div class="helper-copy">Proporção de bytes enviados e recebidos</div>', unsafe_allow_html=True)
            st.plotly_chart(grafico_upload_download(filtrados), use_container_width=True,
                            config={"displayModeBar": False})
    with dir_:
        with st.container(border=True):
            st.markdown('<div class="section-title">Tráfego por hora</div>', unsafe_allow_html=True)
            st.markdown('<div class="helper-copy">Volume e quantidade de bloqueios em cada hora</div>', unsafe_allow_html=True)
            st.plotly_chart(grafico_horas(filtrados), use_container_width=True,
                            config={"displayModeBar": False})
    st.markdown('<div class="small-banner">ℹ️ Os volumes representam bytes informados pelo log, '
                'inclusive em registros BLOCKED. Sem dados de capacidade do link e taxas instantâneas, '
                'a proporção upload/download não comprova saturação de banda.</div>', unsafe_allow_html=True)

with aba_destinos:
    st.write("")
    esq, dir_ = st.columns([1.15, 1], gap="large")
    with esq:
        with st.container(border=True):
            st.markdown('<div class="section-title">Top 10 domínios de destino</div>', unsafe_allow_html=True)
            st.markdown('<div class="helper-copy">Mais acessados por número de registros; passe o mouse para ver categoria e volume</div>',
                        unsafe_allow_html=True)
            st.plotly_chart(grafico_destinos(filtrados), use_container_width=True,
                            config={"displayModeBar": False})
    with dir_:
        with st.container(border=True):
            st.markdown('<div class="section-title">Top categorias por volume</div>', unsafe_allow_html=True)
            st.markdown('<div class="helper-copy">Agrupamento das aplicações pela categoria informada no CSV</div>',
                        unsafe_allow_html=True)
            st.plotly_chart(grafico_categorias(filtrados), use_container_width=True,
                            config={"displayModeBar": False})

    a, b = st.columns([1, 1.4], gap="large")
    with a:
        with st.container(border=True):
            st.markdown('<div class="section-title">Ações registradas</div>', unsafe_allow_html=True)
            st.markdown('<div class="helper-copy">Distribuição ALLOWED / ALERT / BLOCKED</div>', unsafe_allow_html=True)
            st.plotly_chart(grafico_acoes(filtrados), use_container_width=True,
                            config={"displayModeBar": False})
    with b:
        with st.container(border=True):
            st.markdown('<div class="section-title">Tabela de destinos</div>', unsafe_allow_html=True)
            tabela_destinos = (filtrados.groupby(["dest_domain", "category"], as_index=False)
                               .agg(Conexões=("session_id", "count"),
                                    **{"Volume (MB)": ("volume_mb", "sum")}))
            tabela_destinos = tabela_destinos.sort_values("Conexões", ascending=False).rename(
                columns={"dest_domain": "Domínio", "category": "Categoria"})
            st.dataframe(tabela_destinos, hide_index=True, use_container_width=True, height=315,
                         column_config={"Volume (MB)": st.column_config.NumberColumn(format="%.2f")})

with aba_seguranca:
    st.write("")
    st.markdown("### Painel de incidentes e bloqueios")
    st.caption("A visão padrão inclui sessões com **action = BLOCKED** OU **threat_risk = Alto** (união, sem duplicar eventos).")
    c1, c2 = st.columns([1, 1.5])
    with c1:
        foco = st.selectbox("Tipo de ocorrência", ["Bloqueados ou risco alto", "Somente bloqueados",
                                                      "Somente risco alto", "Somente alertas"])
    with c2:
        pesquisa = st.text_input("Buscar usuário, domínio, IP ou categoria", placeholder="Ex.: torrent, mariana, 10.10...")
    incidentes = obter_incidentes(filtrados, foco)
    if pesquisa.strip():
        termo = pesquisa.strip()
        colunas_pesquisa = ["user_name", "dest_domain", "dest_ip", "user_ip", "category", "session_id"]
        corresponde = pd.Series(False, index=incidentes.index)
        for c in colunas_pesquisa:
            corresponde |= incidentes[c].astype(str).str.contains(termo, case=False, regex=False, na=False)
        incidentes = incidentes.loc[corresponde].reset_index(drop=True)
    mini = st.columns(3)
    mini[0].metric("Eventos encontrados", br_int(len(incidentes)))
    mini[1].metric("Com bloqueio", br_int(int(incidentes["action"].eq("BLOCKED").sum())))
    mini[2].metric("Com risco alto", br_int(int(incidentes["threat_risk"].eq("Alto").sum())))
    if incidentes.empty:
        st.info("Nenhuma ocorrência encontrada com estes filtros.")
    else:
        colunas = ["timestamp", "session_id", "user_name", "department", "dest_domain", "category",
                   "dest_ip", "dest_port", "protocol", "threat_risk", "action", "volume_mb"]
        visivel = incidentes[colunas].rename(columns={
            "timestamp": "Data e hora", "session_id": "Sessão", "user_name": "Usuário",
            "department": "Departamento", "dest_domain": "Domínio", "category": "Categoria",
            "dest_ip": "IP destino", "dest_port": "Porta", "protocol": "Protocolo",
            "threat_risk": "Risco", "action": "Ação", "volume_mb": "Volume (MB)",
        })
        chave_selecao = hashlib.sha256(("|".join(incidentes["session_id"].astype(str)) + foco).encode()).hexdigest()[:14]
        selecao = st.dataframe(
            visivel, hide_index=True, use_container_width=True, height=385,
            selection_mode="single-row", on_select="rerun", key=f"selecionar_{chave_selecao}",
            column_config={
                "Data e hora": st.column_config.DatetimeColumn(format="DD/MM/YYYY HH:mm:ss"),
                "Volume (MB)": st.column_config.NumberColumn(format="%.2f"),
                "Porta": st.column_config.NumberColumn(format="%d"),
            },
        )
        st.caption("Clique em uma linha para abrir os detalhes do registro e baixar um relatório executivo em HTML.")
        arquivo_csv = incidentes[[c for c in dados.columns if c not in ["volume_mb", "hora", "data"]]].to_csv(
            index=False, sep=";", encoding="utf-8-sig", decimal=",").encode("utf-8-sig")
        st.download_button("📥 Exportar ocorrências filtradas (CSV)", data=arquivo_csv,
                           file_name="ocorrencias_trafego_rede.csv", mime="text/csv", use_container_width=False)
        if selecao.selection.rows:
            indice = selecao.selection.rows[0]
            reg = incidentes.iloc[indice].to_dict()
            st.divider()
            st.markdown(f"### 📄 Detalhes do evento `{reg['session_id']}`")
            st.write(f"**Usuário:** {reg['user_name']} · **Departamento:** {reg['department']}")
            st.write(f"**Destino:** `{reg['dest_domain']}` · **IP:** `{reg['dest_ip']}` · **Porta:** `{int(reg['dest_port'])}`")
            aa, bb, cc = st.columns(3)
            aa.metric("Ação", str(reg["action"]))
            bb.metric("Risco", str(reg["threat_risk"]))
            cc.metric("Volume registrado", f"{br_num(float(reg['volume_mb']), 2)} MB")
            st.caption("A ação e o risco são classificações presentes no arquivo. A linha, isoladamente, não comprova incidente de segurança.")
            html_relatorio = gerar_relatorio_html(reg)
            st.download_button("📥 Baixar relatório do evento (HTML / imprimir PDF)",
                               data=html_relatorio.encode("utf-8"), mime="text/html",
                               file_name=f"relatorio_{reg['session_id']}.html")

with aba_dados:
    st.write("")
    st.markdown("### Amostra dos registros")
    st.caption("Primeiras 50 linhas da seleção, ordenadas pelo horário. Para auditoria, todos os 2.000 registros estão no CSV incluído no projeto.")
    exibir = filtrados.head(50).drop(columns=["hora", "data", "volume_mb"])
    st.dataframe(exibir, use_container_width=True, hide_index=True, height=330)
    st.markdown("### Informações sobre o cálculo")
    st.markdown("""
- **Fonte:** arquivo CSV exportado integralmente da planilha Excel fornecida para a atividade.
- **Volume total:** soma de `total_bytes` convertida por 1.048.576 (equivale a MiB, indicado como MB para acompanhar o enunciado).
- **Total do gráfico:** os valores são somados em bytes antes da conversão, evitando erros de arredondamento da coluna original `total_megabytes`.
- **Ranking de usuários:** soma dos volumes registrados para cada usuário autenticado.
- **Domínios mais acessados:** classificação pela quantidade de sessões, não pelo volume consumido.
- **Ocorrências de segurança:** união lógica `action = BLOCKED` **ou** `threat_risk = Alto`, sem contagem duplicada.
- **Atualização:** este projeto **não lê o tráfego em tempo real**. Para atualizar a análise, substitua o CSV pelo novo snapshot.
- **Privacidade:** a base possui login, IPs e MACs. Mantenha esses arquivos em ambiente autorizado; antes de publicar, considere anonimizar os identificadores.
""")
    st.download_button("📥 Baixar os registros atualmente filtrados (CSV)",
                       data=filtrados[[c for c in dados.columns if c not in ["hora", "data", "volume_mb"]]]
                       .to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                       mime="text/csv", file_name="trafego_filtrado.csv")

st.divider()
st.caption("Dashboard didático · Python / Streamlit / Plotly · Análise de logs históricos, sem sondagem ativa da rede.")
