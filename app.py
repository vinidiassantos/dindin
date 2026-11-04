import streamlit as st
import yfinance as yf
import pandas as pd
import extra_streamlit_components as stx
import hashlib
from datetime import datetime, timedelta
import numpy as np 
import math
import altair as alt 
import requests 

# 1. Configuração da Página
st.set_page_config(page_title="DinDin", page_icon="💰", layout="wide")

# --- CSS RESPONSIVO E COM ESPAÇAMENTO REDUZIDO ---
st.markdown("""
    <style>
        .block-container { padding-top: 0.5rem !important; padding-bottom: 0.5rem !important; padding-left: 1rem !important; padding-right: 1rem !important; }
        header { visibility: hidden; }
        
        /* Reduz o gap global entre elementos */
        div[data-testid="stVerticalBlock"] { gap: 0.4rem !important; }
        div[data-testid="stMarkdownContainer"] p { margin-bottom: 0 !important; }
        hr { margin: 8px 0 !important; }

        /* ===== HEADER CUSTOM ===== */
        .header-container {
            display: flex; flex-wrap: wrap; gap: 10px; justify-content: space-between; align-items: flex-end;
            margin-top: -15px; margin-bottom: 10px;
        }
        .header-title { font-size: 2rem; font-weight: 700; margin: 0; line-height: 1; }
        .header-subtitle { font-size: 0.85rem; color: gray; margin-top: 3px; }
        .kpi-box { text-align: left; flex: 1; min-width: 90px; }
        .kpi-label { font-size: 0.75rem; color: gray; margin-bottom: 2px; }
        .kpi-value { font-size: 1.3rem; font-weight: 600; line-height: 1; overflow-wrap: anywhere; }
        .kpi-sub { font-size: 0.75rem; margin-top: 2px; font-weight: bold; }
        .kpi-meta { text-align: right; flex: 1.5; min-width: 140px; }

        .compact-list { margin-top: 0px; margin-bottom: 0px; padding-left: 20px; line-height: 1.3; font-size: 13px; }
        .compact-list li { margin-bottom: 3px; }
        .news-link { color: #4da6ff; text-decoration: none; font-size: 11px; margin-left: 5px; }
        .news-link:hover { text-decoration: underline; }

        a.ticker-link { text-decoration: none; color: inherit; }
        a.ticker-link:hover { text-decoration: underline; }

        /* ===== RESUMO (SUBSTITUI AS COLUNAS) ===== */
        .resumo-container {
            display: flex; flex-wrap: wrap; gap: 5px;
            background-color: rgba(128, 128, 128, 0.08);
            padding: 10px; border-radius: 8px; border: 1px solid rgba(128, 128, 128, 0.15);
            margin-bottom: 8px;
        }
        .resumo-box { flex: 1 1 calc(50% - 5px); min-width: 130px; text-align: center; }
        .resumo-label { font-size: 0.8rem; color: gray; margin-bottom: 2px; }
        .resumo-value { font-size: 1.3rem; font-weight: bold; overflow-wrap: anywhere; }

        /* =====================================================
           CELULAR / TABLET  (<= 768px) - FORÇA 2 CARDS POR LINHA
           ===================================================== */
        @media (max-width: 768px) {
            .block-container { padding-left: 0.5rem !important; padding-right: 0.5rem !important; padding-top: 0.5rem !important; }
            .header-container { margin-top: 0 !important; gap: 8px !important; }
            .header-title { font-size: 1.5rem !important; }
            .kpi-box { flex: 1 1 calc(50% - 4px) !important; min-width: 0 !important; }
            .kpi-meta { flex: 1 1 100% !important; text-align: left !important; }
            
            .resumo-box { flex: 1 1 calc(50% - 5px); margin-bottom: 5px; }
            .resumo-value { font-size: 1.1rem; }

            /* Força as colunas do Streamlit a ficarem 2 por linha no mobile */
            div[data-testid="stHorizontalBlock"] {
                flex-wrap: wrap !important;
                gap: 8px !important;
            }
            div[data-testid="column"] {
                flex: 1 1 calc(50% - 4px) !important;
                min-width: calc(50% - 4px) !important;
                max-width: calc(50% - 4px) !important;
            }
            div[data-testid="column"] div[data-testid="stVerticalBlockBorderWrapper"] {
                max-width: 100% !important;
                padding: 6px !important;
            }
            div[data-testid="column"] div[data-testid="stMetricValue"] {
                font-size: 1.1rem !important;
            }
            div[data-testid="column"] div[data-testid="stMarkdownContainer"] p {
                font-size: 11px !important;
            }
            div[data-baseweb="tab-list"] { overflow-x: auto !important; flex-wrap: nowrap !important; }
        }
    </style>
""", unsafe_allow_html=True)

# Inicializa o gerenciador de cookies
cookie_manager = stx.CookieManager(key="cookie_dindin")

# ==========================================
# 2. TRAVA DE SEGURANÇA (COM COOKIES)
# ==========================================
token_seguranca = hashlib.sha256(st.secrets["app_password"].encode()).hexdigest()

if "password_correct" not in st.session_state:
    st.session_state.password_correct = False

auth_cookie = cookie_manager.get(cookie="dindin_auth")

if not st.session_state.password_correct and auth_cookie == token_seguranca:
    st.session_state.password_correct = True

if not st.session_state.password_correct:
    st.title("🔒 Acesso Restrito")
    st.write("Este aplicativo é privado. Insira a senha para visualizar os investimentos.")
    password = st.text_input("Senha:", type="password")
    if st.button("Entrar"):
        if password == st.secrets["app_password"]:
            st.session_state.password_correct = True
            cookie_manager.set("dindin_auth", token_seguranca, expires_at=datetime.now() + timedelta(days=7))
            st.rerun()
        else:
            st.error("Senha incorreta. Tente novamente.")
    st.stop() 

with st.sidebar:
    st.write("---")
    if st.button("Sair do App"):
        cookie_manager.delete("dindin_auth")
        st.session_state.password_correct = False
        st.rerun()

# ==========================================
# FUNÇÕES E DICIONÁRIOS DE APOIO
# ==========================================
def fmt_brl(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def fmt_pct(valor):
    return f"{valor:.2f}%".replace(".", ",")

def fmt_grande(valor):
    if valor is None: return ""
    try:
        if abs(valor) >= 1e9: return f"R$ {valor/1e9:.1f} Bi".replace(".", ",")
        if abs(valor) >= 1e6: return f"R$ {valor/1e6:.1f} Mi".replace(".", ",")
        return fmt_brl(valor)
    except:
        return str(valor)

def gerar_link_investidor10(ticker):
    ticker_lower = ticker.lower()
    if ticker_lower in ['xpml11', 'mcci11', 'hglg11', 'knri11', 'mxrf11']:
        return f"https://investidor10.com.br/fiis/{ticker_lower}/"
    elif ticker_lower in ['bova11']:
        return f"https://investidor10.com.br/etfs/{ticker_lower}/"
    else:
        return f"https://investidor10.com.br/acoes/{ticker_lower}/"

def formatar_data_min(data_timestamp):
    if pd.isna(data_timestamp): return ""
    meses_pt = {'Jan': 'jan', 'Feb': 'fev', 'Mar': 'mar', 'Apr': 'abr', 'May': 'mai', 'Jun': 'jun', 'Jul': 'jul', 'Aug': 'ago', 'Sep': 'set', 'Oct': 'out', 'Nov': 'nov', 'Dec': 'dez'}
    return f" ({meses_pt.get(data_timestamp.strftime('%b'), '')}/{data_timestamp.strftime('%y')})"

def style_taxa(val):
    return f'color: {"#FF4B4B" if val < 0 else "inherit"}; font-weight: bold;'

@st.cache_data(ttl=86400) 
def buscar_metricas_fundamentalistas(ticker):
    try:
        api_key = st.secrets["api_keys"]["dadosb3"]
    except KeyError:
        return {}
        
    headers = {"X-API-Key": api_key}
    metricas = {"score": 0, "roe": None, "receita": None, "divida": None}

    try:
        res_bal = requests.get(f"https://dadosb3.com/api/empresas/{ticker}/balancos", headers=headers, timeout=5)
        if res_bal.status_code == 200:
            periodos = res_bal.json().get("periodos", [])
            if periodos:
                ultimo = periodos[-1]
                metricas["receita"] = ultimo.get("receita_liquida") or ultimo.get("receita")
                metricas["divida"] = ultimo.get("divida_liquida")
    except: pass

    try:
        res_ind = requests.get(f"https://dadosb3.com/api/empresas/{ticker}/indicadores", headers=headers, timeout=5)
        if res_ind.status_code == 200:
            anos = res_ind.json().get("anos", [])
            if anos:
                ultimo_ano = anos[-1]
                roe = ultimo_ano.get("roe")
                div_ebitda = ultimo_ano.get("divida_liquida_ebitda", 10)
                metricas["roe"] = roe
                if roe and roe > 15: metricas["score"] += 2
                if div_ebitda and div_ebitda < 2.5: metricas["score"] += 1
    except: pass

    try:
        res_mult = requests.get(f"https://dadosb3.com/api/empresas/{ticker}/multiplos", headers=headers, timeout=5)
        if res_mult.status_code == 200:
            pl = res_mult.json().get("pl")
            if pl and 0 < pl < 15: metricas["score"] += 1
    except: pass

    return metricas

dicionario_empresas = {
    'VALE3': 'Vale S.A. (Mineração)', 'WEGE3': 'WEG S.A. (Motores)', 
    'ITSA4': 'Itaúsa (Holding)', 'BOVA11': 'iShares (ETF Ibov)', 
    'CEAB3': 'C&A Modas (Varejo)', 'XPML11': 'XP Malls (FII Shoppings)', 
    'MCCI11': 'Mauá Capital (FII Papel)', 'PETR4': 'Petrobras (Petróleo)', 
    'BBAS3': 'Banco do Brasil (Banco)', 'ITUB4': 'Itaú Unibanco (Banco)', 
    'BBDC4': 'Bradesco (Banco)', 'MGLU3': 'Magazine Luiza (Varejo)', 
    'LREN3': 'Lojas Renner (Varejo)', 'VIVT3': 'Telefônica Vivo (Telecom)', 
    'TAEE11': 'Taesa (Energia)', 'KLBN11': 'Klabin (Papel/Celulose)', 
    'SANB11': 'Santander (Banco)', 'BPAC11': 'BTG Pactual (Banco)', 
    'HGLG11': 'CSHG Logística (FII)', 'KNRI11': 'Kinea Renda (FII Híbrido)', 
    'MXRF11': 'Maxi Renda (FII Papel)'
}

@st.cache_data(ttl=900)
def buscar_dados(ativo):
    ticker = yf.Ticker(f"{ativo}.SA")
    return ticker.history(period="max")

def calcular_rsi(dados, periodo=14):
    delta = dados.diff(1)
    ganho = (delta.where(delta > 0, 0)).rolling(window=periodo).mean()
    perda = (-delta.where(delta < 0, 0)).rolling(window=periodo).mean()
    rs = ganho / perda
    return 100 - (100 / (1 + rs.iloc[-1]))

def gerar_tabela_renda_fixa(ativos, investidos, posicoes, ganhos, taxas_atuais):
    df = pd.DataFrame({
        "Ativo": ativos, "Investido (R$)": investidos, "Posição Atual (R$)": posicoes,
        "Ganho (R$)": ganhos, "Taxa (%)": taxas_atuais
    })
    meses_2026 = ["Jan/26", "Fev/26", "Mar/26", "Abr/26", "Mai/26", "Jun/26", "Jul/26", "Ago/26", "Set/26", "Out/26", "Nov/26", "Dez/26"]
    dados_grafico = {}
    for mes in meses_2026: df[mes] = [0.0] * len(ativos); df[f"Tx {mes}"] = [0.0] * len(ativos)
    meses_grafico = meses_2026[:10]
    for i, ativo in enumerate(ativos):
        base_rate = taxas_atuais[i] if taxas_atuais[i] > 0 else 10.0
        taxas_ativo = []
        for j, mes in enumerate(meses_2026):
            taxa_ano = base_rate + np.random.uniform(-0.2, 0.2)
            taxa_mensal = (1 + (taxa_ano / 100)) ** (1/12) - 1
            df.loc[df.index[i], mes] = posicoes[i] * ((1 + taxa_mensal) ** (j + 1))
            df.loc[df.index[i], f"Tx {mes}"] = taxa_ano
            if j < 10: taxas_ativo.append(taxa_ano)
        dados_grafico[ativo] = taxas_ativo
    df_grafico = pd.DataFrame(dados_grafico, index=[m.split('/')[0] for m in meses_grafico])
    return df, df_grafico

# ==========================================
# NOTÍCIAS E OPORTUNIDADES
# ==========================================
def get_noticias_renda_variavel():
    return """
    <ul class="compact-list">
        <li><b>VALE3:</b> Ação sobe forte após 'call' positiva sobre câmbio e metais. <a class="news-link" href="https://valor.globo.com" target="_blank">[Ler mais]</a></li>
        <li><b>WEGE3:</b> Dispara 4,4% hoje e acumula alta de 15,3% na semana. <a class="news-link" href="https://br.investing.com" target="_blank">[Ler mais]</a></li>
    </ul>
    """

def get_oportunidades_renda_variavel():
    return """
    <ul class="compact-list">
        <li><b>Small Caps:</b> BB-BI inclui <b>Pine (PINE4)</b> e <b>Dexco (DXCO3)</b> na carteira. <a class="news-link" href="https://investalk.bb.com.br" target="_blank">[Ler mais]</a></li>
        <li><b>Exportadoras:</b> Dólar alto coloca <b>Suzano (SUZB3)</b> no radar. <a class="news-link" href="https://www.infomoney.com.br" target="_blank">[Ler mais]</a></li>
    </ul>
    """

def get_noticias_renda_fixa(titulos):
    noticias = []
    for titulo in titulos:
        noticias.append(f'<li><b>{titulo}:</b> Acompanhe as taxas do Tesouro Direto hoje. <a class="news-link" href="https://www.infomoney.com.br" target="_blank">[Ler mais]</a></li>')
    return "<ul class='compact-list'>" + "".join(noticias) + "</ul>"

def get_oportunidades_renda_fixa():
    return """
    <ul class="compact-list">
        <li><b>IPCA+:</b> Juro real volta a 8% ao ano; oportunidade em títulos longos. <a class="news-link" href="https://www.seudinheiro.com" target="_blank">[Ler mais]</a></li>
    </ul>
    """

# ==========================================
# VALORES CONSOLIDADOS ATUALIZADOS (NOVEMBRO)
# ==========================================
inv_geral = 145521.18
pos_geral = 155268.30
rent_geral = 6.70

inv_rv = 1147.50
pos_rv = 1147.65
rent_rv = 0.01
ganho_rv_real = 0.15

inv_rf = 144373.68
ganho_rf = 9746.82
rent_rf = 6.75

cor_rv = "#00FF00" if rent_rv >= 0 else "#FF4B4B"

# ==========================================
# CABEÇALHO COMPACTO
# ==========================================
header_html = f"""
<div class="header-container" id="topo">
<div style="flex: 2; min-width: 180px;">
<div class="header-title"><a href="#topo" target="_self" style="text-decoration: none; color: inherit;">💰 DinDin</a></div>
</div>
<div class="kpi-box">
<div class="kpi-label">Total Investido</div>
<div class="kpi-value">{fmt_brl(inv_geral)}</div>
</div>
<div class="kpi-box">
<div class="kpi-label">Posição Atual</div>
<div class="kpi-value">{fmt_brl(pos_geral)}</div>
</div>
<div class="kpi-box" style="flex: 0.8;">
<div class="kpi-label">Rentab.</div>
<div class="kpi-value" style="color: #00FF00;">{fmt_pct(rent_geral)}</div>
</div>
<div class="kpi-box" style="flex: 1.2;">
<div class="kpi-label">Total Variável</div>
<div class="kpi-value">{fmt_brl(inv_rv)}</div>
<div class="kpi-sub" style="color: {cor_rv};">{fmt_pct(rent_rv)}</div>
</div>
<div class="kpi-box" style="flex: 1.2;">
<div class="kpi-label">Total Fixo</div>
<div class="kpi-value">{fmt_brl(inv_rf)}</div>
<div class="kpi-sub" style="color: #00FF00;">{fmt_pct(rent_rf)}</div>
</div>
<div class="kpi-meta">
<div class="kpi-label">Meta 500k (21.35%)</div>
<div class="kpi-value" style="font-size: 1.1rem;">Atual: R$ 106.779,65</div>
</div>
</div>
<hr style="margin: 0px 0 10px 0; border: 0; border-top: 1px solid #333;">
"""
st.markdown(header_html, unsafe_allow_html=True)

# ==========================================
# CRIANDO AS 3 ABAS
# ==========================================
aba_renda_variavel, aba_renda_fixa, aba_maria = st.tabs([
    "📈 Renda Variável (Ações e FIIs)", "🏦 Renda Fixa", "👩 Invest Maria"
])

# ==========================================
# ABA 1: RENDA VARIÁVEL
# ==========================================
with aba_renda_variavel:
    st.subheader("Sua Carteira de Cotações")
    
    carteira_acoes = ['XPML11', 'MCCI11', 'ITSA4', 'BOVA11', 'CEAB3', 'VALE3', 'WEGE3']
    inv_ativos = [99.73, 89.89, 130.10, 173.23, 107.40, 322.70, 224.45]
    total_investido_rv = 1147.50
    
    resumo_html = f"""
    <div class="resumo-container">
        <div class="resumo-box">
            <div class="resumo-label">Total Investido</div>
            <div class="resumo-value">{fmt_brl(total_investido_rv)}</div>
        </div>
        <div class="resumo-box">
            <div class="resumo-label">Posição Atual</div>
            <div class="resumo-value">{fmt_brl(pos_rv)}</div>
        </div>
        <div class="resumo-box">
            <div class="resumo-label">Ganho Total</div>
            <div class="resumo-value" style="color: {cor_rv};">{fmt_brl(ganho_rv_real)}</div>
        </div>
        <div class="resumo-box">
            <div class="resumo-label">Rentabilidade Média</div>
            <div class="resumo-value" style="color: {cor_rv};">{fmt_pct(rent_rv)}</div>
        </div>
    </div>
    """
    st.markdown(resumo_html, unsafe_allow_html=True)
    
    num_cols = 4
    num_rows = math.ceil(len(carteira_acoes) / num_cols)

    for row in range(num_rows):
        cols = st.columns(num_cols)
        for i in range(num_cols):
            idx = row * num_cols + i
            if idx < len(carteira_acoes):
                ativo = carteira_acoes[idx]
                hist = buscar_dados(ativo)
                
                if not hist.empty:
                    preco_atual = hist['Close'].iloc[-1]
                    preco_anterior = hist['Close'].iloc[-2]
                    variacao_pct = ((preco_atual - preco_anterior) / preco_anterior) * 100
                    rsi = calcular_rsi(hist['Close'])
                    min_6m = hist['Low'].tail(126).min()
                    hist_5a = hist['Low'].tail(1260); min_5a = hist_5a.min()
                    texto_data_5a = formatar_data_min(hist_5a.idxmin())
                    share = (inv_ativos[idx] / total_investido_rv) * 100
                    sinal = "COMPRAR" if rsi < 35 else ("VENDER" if rsi > 70 else "MANTER")
                    cor_sinal = "#00FF00" if rsi < 35 else ("#FF4B4B" if rsi > 70 else "#808080")
                    nome_empresa = dicionario_empresas.get(ativo, "")
                    link = gerar_link_investidor10(ativo)
                    metricas = buscar_metricas_fundamentalistas(ativo)
                        
                    with cols[i]:
                        with st.container(border=True):
                            st.markdown(f"<div style='text-align: center; margin-top: -5px; margin-bottom: 2px; line-height: 1.1;'><a class='ticker-link' href='{link}' target='_blank' style='font-size: 16px; font-weight: bold;'>{ativo}</a><br><span style='font-size: 10px; color: gray;'>{nome_empresa}</span></div>", unsafe_allow_html=True)
                            st.metric(label="Cotação Atual", value=fmt_brl(preco_atual), delta=f"{variacao_pct:.2f}%".replace(".", ","), label_visibility="collapsed")
                            
                            html_tecnico = f"<div style='font-size: 12px; line-height: 1.3; margin-top: -5px; margin-bottom: 5px;'>📉 <b>Mín 6m:</b> {fmt_brl(min_6m)}<br>⏳ <b>Mín 5a:</b> {fmt_brl(min_5a)}{texto_data_5a}<br>📊 <b>RSI:</b> {rsi:.1f}".replace(".", ",") + f"<br>🤖 <b>Sinal:</b> <span style='color:{cor_sinal}; font-weight: bold;'>{sinal}</span><br>💼 <b>Share:</b> {share:.1f}%".replace(".", ",") + "</div>"
                            st.markdown(html_tecnico, unsafe_allow_html=True)
                            
                            if metricas.get("receita") or metricas.get("divida") or metricas.get("roe"):
                                html_indicadores = "<hr style='margin: 4px 0; border-top: 1px solid rgba(128, 128, 128, 0.3);'>"
                                if metricas.get("receita"): html_indicadores += f"<div style='font-size: 11px;'>💰 <b>Receita:</b> {fmt_grande(metricas['receita'])}</div>"
                                if metricas.get("divida"): html_indicadores += f"<div style='font-size: 11px;'>🏦 <b>Dív. Líq:</b> {fmt_grande(metricas['divida'])}</div>"
                                if metricas.get("roe"): html_indicadores += f"<div style='font-size: 11px;'>🏆 <b>ROE:</b> {fmt_pct(metricas['roe'])}</div>"
                                st.markdown(html_indicadores, unsafe_allow_html=True)
                            
                            st.progress(share / 100.0) 

    radar_tickers = ['PETR4', 'BBAS3', 'ITUB4', 'BBDC4', 'MGLU3', 'LREN3', 'VIVT3', 'TAEE11', 'KLBN11', 'SANB11', 'BPAC11', 'HGLG11', 'KNRI11', 'MXRF11']
    oportunidades = []

    with st.spinner("Analisando fundamentos e RSI..."):
        for ticker in radar_tickers:
            hist_radar = buscar_dados(ticker)
            if not hist_radar.empty:
                rsi_radar = calcular_rsi(hist_radar['Close'])
                if rsi_radar < 35:
                    metricas_radar = buscar_metricas_fundamentalistas(ticker)
                    score = metricas_radar.get("score", 0)
                    if score >= 2:
                        preco_radar = hist_radar['Close'].iloc[-1]
                        preco_ant_radar = hist_radar['Close'].iloc[-2]
                        var_pct_radar = ((preco_radar - preco_ant_radar) / preco_ant_radar) * 100
                        min_6m_radar = hist_radar['Low'].tail(126).min()
                        hist_radar_5a = hist_radar['Low'].tail(1260)
                        min_5a_radar = hist_radar_5a.min()
                        texto_data_5a_radar = formatar_data_min(hist_radar_5a.idxmin())
                        oportunidades.append({
                            "ativo": ticker, "preco": preco_radar, "variacao": var_pct_radar,
                            "rsi": rsi_radar, "min_6m": min_6m_radar, "min_5a": min_5a_radar,
                            "data_min_5a": texto_data_5a_radar, "score": score
                        })

    if oportunidades:
        st.divider()
        st.subheader("🔥 Radar")
        
        num_rows_op = math.ceil(len(oportunidades) / num_cols)
        for row in range(num_rows_op):
            cols_op = st.columns(num_cols)
            for i in range(num_cols):
                idx_op = row * num_cols + i
                if idx_op < len(oportunidades):
                    op = oportunidades[idx_op]
                    nome_empresa_radar = dicionario_empresas.get(op['ativo'], "")
                    link_op = gerar_link_investidor10(op['ativo'])
                    estrelas = "⭐" * op['score']
                    
                    with cols_op[i]:
                        with st.container(border=True):
                            st.markdown(f"<div style='text-align: center; margin-top: -5px; margin-bottom: 2px; line-height: 1.1;'><a class='ticker-link' href='{link_op}' target='_blank' style='font-size: 16px; font-weight: bold; color: #00FF00;'>{op['ativo']}</a><br><span style='font-size: 10px; color: gray;'>{nome_empresa_radar}</span></div>", unsafe_allow_html=True)
                            st.metric(label="Preço", value=fmt_brl(op['preco']), delta=f"{op['variacao']:.2f}%".replace(".", ","), label_visibility="collapsed")
                            st.markdown(f"<div style='font-size: 12px; line-height: 1.3; margin-top: -5px; margin-bottom: 5px;'>🎯 <b>RSI:</b> {op['rsi']:.1f}".replace(".", ",") + f"<br>🏆 <b>Score:</b> {estrelas} ({op['score']}/4)<br>📉 <b>Mín 6m:</b> {fmt_brl(op['min_6m'])}<br>⏳ <b>Mín 5a:</b> {fmt_brl(op['min_5a'])}{op['data_min_5a']}</div>", unsafe_allow_html=True)

    st.divider()
    st.markdown("#### 💡 Notícias dos Seus Ativos - Renda Variável (Últimas 24h)")
    st.markdown(get_noticias_renda_variavel(), unsafe_allow_html=True)
    st.divider()
    st.markdown("#### 🚀 Oportunidades do Mercado - Fora da Carteira")
    st.markdown(get_oportunidades_renda_variavel(), unsafe_allow_html=True)

# ==========================================
# ABA 2: RENDA FIXA (FAMÍLIA)
# ==========================================
with aba_renda_fixa:
    st.subheader("Painel de Renda Fixa")
    
    ativos_fam = ["IPCA+ 2032", "PRÉ 2032", "Selic 2031"]
    inv_fam = [2987.73, 1476.27, 96038.86]
    pos_fam = [3092.00, 1457.00, 101083.00]
    gan_fam = [104.27, -19.27, 5044.14]
    rent_fam = [3.49, -1.31, 5.25]
    
    total_investido = 101650.36
    total_posicao = 106779.65
    total_ganho = 5129.14
    rent_media = 5.05

    resumo_rf_html = f"""
    <div class="resumo-container">
        <div class="resumo-box"><div class="resumo-label">Total Investido</div><div class="resumo-value">{fmt_brl(total_investido)}</div></div>
        <div class="resumo-box"><div class="resumo-label">Posição Atual</div><div class="resumo-value">{fmt_brl(total_posicao)}</div></div>
        <div class="resumo-box"><div class="resumo-label">Ganho Total</div><div class="resumo-value">{fmt_brl(total_ganho)}</div></div>
        <div class="resumo-box"><div class="resumo-label">Rentabilidade Média</div><div class="resumo-value">{fmt_pct(rent_media)}</div></div>
    </div>
    """
    st.markdown(resumo_rf_html, unsafe_allow_html=True)

    st.markdown("#### Detalhamento e Evolução Mês a Mês (2026)")
    
    df_fam, df_grafico_fam = gerar_tabela_renda_fixa(ativos_fam, inv_fam, pos_fam, gan_fam, rent_fam)
    df_fam.insert(5, "Share (%)", (df_fam["Investido (R$)"] / total_investido) * 100)

    cols_to_center_fam = [c for c in df_fam.columns if c != 'Ativo']

    styled_fam = (df_fam.style
                  .map(style_taxa, subset=['Taxa (%)'])
                  .format({
                      "Investido (R$)": lambda x: fmt_brl(x),
                      "Posição Atual (R$)": lambda x: fmt_brl(x),
                      "Ganho (R$)": lambda x: fmt_brl(x),
                      "Taxa (%)": lambda x: fmt_pct(x),
                      **{mes: lambda x: fmt_brl(x) for mes in ["Jan/26", "Fev/26", "Mar/26", "Abr/26", "Mai/26", "Jun/26", "Jul/26", "Ago/26", "Set/26", "Out/26", "Nov/26", "Dez/26"]},
                      **{f"Tx {mes}": lambda x: fmt_pct(x) for mes in ["Jan/26", "Fev/26", "Mar/26", "Abr/26", "Mai/26", "Jun/26", "Jul/26", "Ago/26", "Set/26", "Out/26", "Nov/26", "Dez/26"]}
                  })
                  .set_properties(subset=cols_to_center_fam, **{'text-align': 'center'})
                  .set_properties(subset=['Share (%)'], **{'border-right': '2px solid #555'}))

    config_colunas = {
        "Share (%)": st.column_config.ProgressColumn("Share (%)", format="%.1f%%", min_value=0, max_value=100)
    }

    st.dataframe(styled_fam, hide_index=True, use_container_width=True, column_config=config_colunas)

    st.markdown("#### Histórico de Taxas")
    
    df_melt = df_grafico_fam.reset_index().melt('index', var_name='Ativo', value_name='Taxa')
    df_melt = df_melt.rename(columns={'index': 'Mês'})
    df_ultimo_mes = df_melt[df_melt['Mês'] == 'Out']

    line = alt.Chart(df_melt).mark_line(point=True).encode(
        x=alt.X('Mês:N', sort=None, title='Mês', axis=alt.Axis(labelAngle=0)),
        y=alt.Y('Taxa:Q', title='Taxa Anualizada (%)', scale=alt.Scale(zero=False)),
        color=alt.Color('Ativo:N', legend=alt.Legend(orient='bottom', columns=3)),
        tooltip=[alt.Tooltip('Mês:N', title='Mês'), alt.Tooltip('Ativo:N', title='Ativo'), alt.Tooltip('Taxa:Q', title='Taxa (%)', format='.2f')]
    )

    text = alt.Chart(df_ultimo_mes).mark_text(align='left', dx=5, fontSize=12, fontWeight='bold').encode(
        x=alt.X('Mês:N'), y=alt.Y('Taxa:Q'), text=alt.Text('Taxa:Q', format='.1f'), color=alt.Color('Ativo:N', legend=None)
    )

    chart_fam = (line + text).properties(height=300).interactive()
    st.altair_chart(chart_fam, use_container_width=True)

    st.divider()
    st.markdown("#### 💡 Notícias dos Seus Títulos - Renda Fixa (Últimas 24h)")
    st.markdown(get_noticias_renda_fixa(ativos_fam), unsafe_allow_html=True)
    st.divider()
    st.markdown("#### 🚀 Oportunidades do Mercado - Fora da Carteira")
    st.markdown(get_oportunidades_renda_fixa(), unsafe_allow_html=True)

# ==========================================
# ABA 3: INVEST MARIA
# ==========================================
with aba_maria:
    st.subheader("Painel de Renda Fixa - Maria")
    
    ativos_maria = ["IPCA+ 2029", "IPCA+ 2032", "IPCA+ 2035 c/juros sem", "PRÉ 2032", "PRÉ 2035 c/juros sem", "SELIC 2031"]
    inv_maria = [5779.67, 1580.87, 5444.10, 1452.61, 2370.30, 26095.77]
    pos_maria = [6528.00, 1636.00, 5658.00, 1475.00, 2254.00, 29790.00]
    gan_maria = [748.33, 55.13, 213.90, 22.39, -116.30, 3694.23]
    rent_maria = [12.95, 3.49, 3.93, 1.54, -4.91, 14.16]
    
    total_investido_maria = 42723.32
    total_posicao_maria = 47341.00
    total_ganho_maria = 4617.68
    rent_media_maria = 10.81

    resumo_maria_html = f"""
    <div class="resumo-container">
        <div class="resumo-box"><div class="resumo-label">Total Investido</div><div class="resumo-value">{fmt_brl(total_investido_maria)}</div></div>
        <div class="resumo-box"><div class="resumo-label">Posição Atual</div><div class="resumo-value">{fmt_brl(total_posicao_maria)}</div></div>
        <div class="resumo-box"><div class="resumo-label">Ganho Total</div><div class="resumo-value">{fmt_brl(total_ganho_maria)}</div></div>
        <div class="resumo-box"><div class="resumo-label">Rentabilidade Média</div><div class="resumo-value">{fmt_pct(rent_media_maria)}</div></div>
    </div>
    """
    st.markdown(resumo_maria_html, unsafe_allow_html=True)

    st.markdown("#### Detalhamento e Evolução Mês a Mês (2026)")
    
    df_maria, df_grafico_maria = gerar_tabela_renda_fixa(ativos_maria, inv_maria, pos_maria, gan_maria, rent_maria)
    df_maria.insert(5, "Share (%)", (df_maria["Investido (R$)"] / total_investido_maria) * 100)

    cols_to_center_maria = [c for c in df_maria.columns if c != 'Ativo']

    styled_maria = (df_maria.style
                    .map(style_taxa, subset=['Taxa (%)'])
                    .format({
                        "Investido (R$)": lambda x: fmt_brl(x),
                        "Posição Atual (R$)": lambda x: fmt_brl(x),
                        "Ganho (R$)": lambda x: fmt_brl(x),
                        "Taxa (%)": lambda x: fmt_pct(x),
                        **{mes: lambda x: fmt_brl(x) for mes in ["Jan/26", "Fev/26", "Mar/26", "Abr/26", "Mai/26", "Jun/26", "Jul/26", "Ago/26", "Set/26", "Out/26", "Nov/26", "Dez/26"]},
                        **{f"Tx {mes}": lambda x: fmt_pct(x) for mes in ["Jan/26", "Fev/26", "Mar/26", "Abr/26", "Mai/26", "Jun/26", "Jul/26", "Ago/26", "Set/26", "Out/26", "Nov/26", "Dez/26"]}
                    })
                    .set_properties(subset=cols_to_center_maria, **{'text-align': 'center'})
                    .set_properties(subset=['Share (%)'], **{'border-right': '2px solid #555'}))

    st.dataframe(styled_maria, hide_index=True, use_container_width=True, column_config=config_colunas)

    st.markdown("#### Histórico de Taxas")
    
    df_melt_maria = df_grafico_maria.reset_index().melt('index', var_name='Ativo', value_name='Taxa')
    df_melt_maria = df_melt_maria.rename(columns={'index': 'Mês'})
    df_ultimo_mes_maria = df_melt_maria[df_melt_maria['Mês'] == 'Out']

    line_maria = alt.Chart(df_melt_maria).mark_line(point=True).encode(
        x=alt.X('Mês:N', sort=None, title='Mês', axis=alt.Axis(labelAngle=0)),
        y=alt.Y('Taxa:Q', title='Taxa Anualizada (%)', scale=alt.Scale(zero=False)),
        color=alt.Color('Ativo:N', legend=alt.Legend(orient='bottom', columns=3)),
        tooltip=[alt.Tooltip('Mês:N', title='Mês'), alt.Tooltip('Ativo:N', title='Ativo'), alt.Tooltip('Taxa:Q', title='Taxa (%)', format='.2f')]
    )

    text_maria = alt.Chart(df_ultimo_mes_maria).mark_text(align='left', dx=5, fontSize=12, fontWeight='bold').encode(
        x=alt.X('Mês:N'), y=alt.Y('Taxa:Q'), text=alt.Text('Taxa:Q', format='.1f'), color=alt.Color('Ativo:N', legend=None)
    )

    chart_maria = (line_maria + text_maria).properties(height=300).interactive()
    st.altair_chart(chart_maria, use_container_width=True)

    st.divider()
    st.markdown("#### 💡 Notícias dos Seus Títulos - Renda Fixa (Últimas 24h)")
    st.markdown(get_noticias_renda_fixa(ativos_maria), unsafe_allow_html=True)
    st.divider()
    st.markdown("#### 🚀 Oportunidades do Mercado - Fora da Carteira")
    st.markdown(get_oportunidades_renda_fixa(), unsafe_allow_html=True)