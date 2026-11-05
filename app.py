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
from streamlit_gsheets import GSheetsConnection

# 1. Configuração da Página
st.set_page_config(page_title="DinDin", page_icon="💰", layout="wide")

# --- CSS RESPONSIVO E OTIMIZADO ---
st.markdown("""
    <style>
        .block-container { padding-top: 0.5rem !important; padding-bottom: 0.5rem !important; padding-left: 0.5rem !important; padding-right: 0.5rem !important; }
        header { visibility: hidden; }
        
        div[data-testid="stVerticalBlock"] { gap: 0.4rem !important; }
        div[data-testid="stMarkdownContainer"] p { margin-bottom: 0 !important; }
        hr { margin: 8px 0 !important; }

        /* ===== HEADER CUSTOM (2 por linha no mobile) ===== */
        .header-grid {
            display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px;
            margin-top: -10px; margin-bottom: 10px; align-items: end;
        }
        .header-logo { grid-column: span 1; }
        .header-title { font-size: 2rem; font-weight: 700; margin: 0; line-height: 1; }
        
        .kpi-box { text-align: left; }
        .kpi-label { font-size: 0.75rem; color: gray; margin-bottom: 2px; }
        .kpi-value { font-size: 1.2rem; font-weight: 600; line-height: 1; overflow-wrap: anywhere; }
        .kpi-sub { font-size: 0.75rem; margin-top: 2px; font-weight: bold; }
        .kpi-meta { text-align: right; grid-column: span 4; margin-top: 5px; }

        @media (max-width: 768px) {
            .header-grid { grid-template-columns: repeat(2, 1fr); gap: 8px; }
            .header-logo { grid-column: span 2; margin-bottom: 5px; }
            .header-title { font-size: 1.6rem; }
            .kpi-meta { grid-column: span 2; text-align: left; }
            .kpi-value { font-size: 1.1rem; }
        }

        /* ===== RESUMO (2 por linha no mobile) ===== */
        .resumo-grid {
            display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px;
            background-color: rgba(128, 128, 128, 0.08);
            padding: 12px; border-radius: 8px; border: 1px solid rgba(128, 128, 128, 0.15);
            margin-bottom: 10px;
        }
        .resumo-box { text-align: center; }
        .resumo-label { font-size: 0.8rem; color: gray; margin-bottom: 2px; }
        .resumo-value { font-size: 1.2rem; font-weight: bold; overflow-wrap: anywhere; }

        @media (max-width: 768px) {
            .resumo-grid { grid-template-columns: repeat(2, 1fr); }
        }

        /* ===== TABS ===== */
        div[data-baseweb="tab-list"] { overflow-x: auto !important; flex-wrap: nowrap !important; }
        
        /* Ajustes finos nos cards */
        div[data-testid="column"] div[data-testid="stVerticalBlockBorderWrapper"] { padding: 8px !important; }
        div[data-testid="column"] div[data-testid="stMetricValue"] { font-size: 1.15rem !important; }
        div[data-testid="column"] div[data-testid="stMarkdownContainer"] p { font-size: 11px !important; }
        
        .compact-list { margin-top: 0px; margin-bottom: 0px; padding-left: 20px; line-height: 1.3; font-size: 13px; }
        .news-link { color: #4da6ff; text-decoration: none; font-size: 11px; margin-left: 5px; }
        a.ticker-link { text-decoration: none; color: inherit; }
        a.ticker-link:hover { text-decoration: underline; }
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
    except: return str(valor)

def limpar_moeda(val):
    if pd.isna(val) or val == "": return 0.0
    s = str(val).replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".")
    try: return float(s)
    except: return 0.0

def limpar_pct(val):
    if pd.isna(val) or val == "": return 0.0
    s = str(val).replace("%", "").replace(",", ".").replace(" ", "")
    try: return float(s)
    except: return 0.0

def gerar_link_investidor10(ticker):
    ticker_lower = str(ticker).lower()
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
    try: api_key = st.secrets["api_keys"]["dadosb3"]
    except KeyError: return {}
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
    'VALE3': 'Vale S.A.', 'WEGE3': 'WEG S.A.', 'ITSA4': 'Itaúsa', 'BOVA11': 'iShares Ibov', 
    'CEAB3': 'C&A Modas', 'XPML11': 'XP Malls', 'MCCI11': 'Mauá Capital', 'PETR4': 'Petrobras', 
    'BBAS3': 'Banco do Brasil', 'ITUB4': 'Itaú Unibanco', 'BBDC4': 'Bradesco', 'MGLU3': 'Magazine Luiza', 
    'LREN3': 'Lojas Renner', 'VIVT3': 'Telefônica Vivo', 'TAEE11': 'Taesa', 'KLBN11': 'Klabin', 
    'SANB11': 'Santander', 'BPAC11': 'BTG Pactual', 'HGLG11': 'CSHG Logística', 'KNRI11': 'Kinea Renda', 
    'MXRF11': 'Maxi Renda'
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

# ==========================================
# INTEGRAÇÃO COM GOOGLE SHEETS (LEITURA DINÂMICA)
# ==========================================
# Valores de Fallback (Caso a planilha falhe)
inv_geral = 145521.18; pos_geral = 155268.30; rent_geral = 6.70; lucro_geral = 9747.12
inv_rv = 1147.50; pos_rv = 1147.65; rent_rv = 0.01; ganho_rv_real = 0.15
inv_rf = 101650.36; pos_rf = 106779.65; rent_rf = 5.05; ganho_rf_real = 5129.14
inv_maria = 42723.32; pos_maria = 47341.00; ganho_maria = 4617.68; rent_maria = 10.81

# Inicializa DataFrames vazios para evitar erro de "not defined"
df_total = pd.DataFrame()
df_rv = pd.DataFrame()
df_rf = pd.DataFrame()
df_maria = pd.DataFrame()
df_macro = pd.DataFrame()

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Lê cada aba de forma independente
    try: df_total = conn.read(worksheet="Total", ttl=30)
    except: pass
        
    try: df_rv = conn.read(worksheet="Renda Variável", ttl=30)
    except: pass
        
    try: df_rf = conn.read(worksheet="Renda Fixa", ttl=30)
    except: pass
        
    try: df_maria = conn.read(worksheet="Investimentos Maria", ttl=30)
    except: pass
        
    try: df_macro = conn.read(worksheet="Indicadores Macro", ttl=30)
    except: st.sidebar.warning("⚠️ Aba 'Indicadores Macro' não encontrada na planilha.")
    
    # Extração da aba TOTAL (Só executa se o df_total não estiver vazio)
    if not df_total.empty:
        pos_geral = limpar_moeda(df_total.iloc[4, 0])
        inv_geral = limpar_moeda(df_total.iloc[4, 2])
        lucro_geral = limpar_moeda(df_total.iloc[4, 4])
        rent_geral = limpar_pct(df_total.iloc[4, 6]) * 100

    # Extração Renda Variável
    if not df_rv.empty:
        inv_rv = limpar_moeda(df_rv.iloc[1, 5])
        pos_rv = limpar_moeda(df_rv.iloc[1, 6])
        ganho_rv_real = limpar_moeda(df_rv.iloc[1, 7])
        rent_rv = limpar_pct(df_rv.iloc[1, 8]) * 100

    # Extração Renda Fixa
    if not df_rf.empty:
        inv_rf = limpar_moeda(df_rf.iloc[1, 4])
        pos_rf = limpar_moeda(df_rf.iloc[1, 5])
        ganho_rf_real = limpar_moeda(df_rf.iloc[1, 6])
        rent_rf = limpar_pct(df_rf.iloc[1, 7]) * 100

    # Extração Maria
    if not df_maria.empty:
        inv_maria = limpar_moeda(df_maria.iloc[1, 4])
        pos_maria = limpar_moeda(df_maria.iloc[1, 5])
        ganho_maria = limpar_moeda(df_maria.iloc[1, 6])
        rent_maria = limpar_pct(df_maria.iloc[1, 7]) * 100
    
    st.sidebar.success("📈 Dados do Google Sheets carregados!")
    
except Exception as e:
    st.sidebar.warning(f"⚠️ Usando dados locais (Erro na conexão: {e})")

cor_rv = "#00FF00" if rent_rv >= 0 else "#FF4B4B"

# ==========================================
# CABEÇALHO COMPACTO
# ==========================================
header_html = f"""
<div class="header-grid" id="topo">
<div class="header-logo">
    <a href="#topo" target="_self" style="text-decoration: none; color: inherit; font-size: 2rem; font-weight: 700; line-height: 1;">💰 DinDin</a>
</div>
<div class="kpi-box"><div class="kpi-label">Patrimônio Total</div><div class="kpi-value">{fmt_brl(pos_geral)}</div></div>
<div class="kpi-box"><div class="kpi-label">Capital Aplicado</div><div class="kpi-value">{fmt_brl(inv_geral)}</div></div>
<div class="kpi-box"><div class="kpi-label">Lucro Total</div><div class="kpi-value" style="color: #00FF00;">{fmt_brl(lucro_geral)}</div></div>
<div class="kpi-box"><div class="kpi-label">Rentab. Global</div><div class="kpi-value" style="color: #00FF00;">{fmt_pct(rent_geral)}</div></div>
<div class="kpi-meta">
    <div class="kpi-label">Meta Familiar: R$ 500.000 (Progresso: {fmt_pct((pos_geral/500000)*100)})</div>
    <div class="kpi-value" style="font-size: 1rem;">Falta: {fmt_brl(max(0, 500000 - pos_geral))}</div>
</div>
</div>
<hr style="margin: 0px 0 10px 0; border: 0; border-top: 1px solid #333;">
"""
st.markdown(header_html, unsafe_allow_html=True)

# ==========================================
# CRIANDO AS 4 ABAS
# ==========================================
aba_renda_variavel, aba_renda_fixa, aba_maria, aba_mercado = st.tabs([
    "📈 Renda Variável", "🏦 Renda Fixa", "👩 Maria", "🌍 Mercado"
])

# ==========================================
# ABA 1: RENDA VARIÁVEL
# ==========================================
with aba_renda_variavel:
    st.subheader("Sua Carteira de Cotações")
    
    try:
        # Tenta extrair da planilha
        carteira_acoes = df_rv.iloc[4:10, 0].dropna().tolist() + df_rv.iloc[11:14, 0].dropna().tolist()
        inv_ativos = df_rv.iloc[4:10, 5].apply(limpar_moeda).tolist() + df_rv.iloc[11:14, 5].apply(limpar_moeda).tolist()
        # Limpa strings vazias ou cabeçalhos indesejados
        carteira_acoes = [str(a).strip() for a in carteira_acoes if isinstance(a, str) and len(str(a).strip()) > 0 and len(str(a).strip()) <= 6]
        inv_ativos = [i for i in inv_ativos if i > 0]
    except:
        # Fallback
        carteira_acoes = ['ITSA4', 'BOVA11', 'CEAB3', 'VALE3', 'WEGE3', 'XPML11', 'MCCI11']
        inv_ativos = [130.10, 173.23, 107.40, 322.70, 224.45, 99.73, 89.89]
    
    resumo_html = f"""
    <div class="resumo-grid">
        <div class="resumo-box"><div class="resumo-label">Total Investido</div><div class="resumo-value">{fmt_brl(inv_rv)}</div></div>
        <div class="resumo-box"><div class="resumo-label">Posição Atual</div><div class="resumo-value">{fmt_brl(pos_rv)}</div></div>
        <div class="resumo-box"><div class="resumo-label">Ganho Total</div><div class="resumo-value" style="color: {cor_rv};">{fmt_brl(ganho_rv_real)}</div></div>
        <div class="resumo-box"><div class="resumo-label">Rentabilidade Média</div><div class="resumo-value" style="color: {cor_rv};">{fmt_pct(rent_rv)}</div></div>
    </div>
    """
    st.markdown(resumo_html, unsafe_allow_html=True)
    
    # 2 CARDS POR LINHA
    for i in range(0, len(carteira_acoes), 2):
        cols = st.columns(2)
        
        for j in range(2):
            if i + j < len(carteira_acoes):
                ativo = carteira_acoes[i+j]
                hist = buscar_dados(ativo)
                if not hist.empty:
                    preco_atual = hist['Close'].iloc[-1]
                    preco_anterior = hist['Close'].iloc[-2]
                    variacao_pct = ((preco_atual - preco_anterior) / preco_anterior) * 100
                    rsi = calcular_rsi(hist['Close'])
                    min_6m = hist['Low'].tail(126).min()
                    hist_5a = hist['Low'].tail(1260); min_5a = hist_5a.min()
                    texto_data_5a = formatar_data_min(hist_5a.idxmin())
                    share = (inv_ativos[i+j] / inv_rv) * 100 if inv_rv > 0 else 0
                    sinal = "COMPRAR" if rsi < 35 else ("VENDER" if rsi > 70 else "MANTER")
                    cor_sinal = "#00FF00" if rsi < 35 else ("#FF4B4B" if rsi > 70 else "#808080")
                    nome_empresa = dicionario_empresas.get(ativo, "")
                    link = gerar_link_investidor10(ativo)
                    metricas = buscar_metricas_fundamentalistas(ativo)
                        
                    with cols[j]:
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

# ==========================================
# ABA 2: RENDA FIXA (FAMÍLIA)
# ==========================================
with aba_renda_fixa:
    st.subheader("Painel de Renda Fixa")
    
    try:
        ativos_fam = df_rf.iloc[2:5, 0].dropna().tolist()
        inv_fam = df_rf.iloc[2:5, 4].apply(limpar_moeda).tolist()
        pos_fam = df_rf.iloc[2:5, 5].apply(limpar_moeda).tolist()
        gan_fam = df_rf.iloc[2:5, 6].apply(limpar_moeda).tolist()
        rent_fam = df_rf.iloc[2:5, 7].apply(limpar_pct).tolist()
    except:
        ativos_fam = ["IPCA+ 2032", "PRÉ 2032", "Selic 2031"]
        inv_fam = [2987.73, 1476.27, 96038.86]
        pos_fam = [3096.00, 1466.00, 101083.00]
        gan_fam = [108.27, -10.27, 5044.14]
        rent_fam = [3.62, -0.70, 5.25]

    resumo_rf_html = f"""
    <div class="resumo-grid">
        <div class="resumo-box"><div class="resumo-label">Total Investido</div><div class="resumo-value">{fmt_brl(inv_rf)}</div></div>
        <div class="resumo-box"><div class="resumo-label">Posição Atual</div><div class="resumo-value">{fmt_brl(pos_rf)}</div></div>
        <div class="resumo-box"><div class="resumo-label">Ganho Total</div><div class="resumo-value">{fmt_brl(ganho_rf_real)}</div></div>
        <div class="resumo-box"><div class="resumo-label">Rentabilidade Média</div><div class="resumo-value">{fmt_pct(rent_rf)}</div></div>
    </div>
    """
    st.markdown(resumo_rf_html, unsafe_allow_html=True)

    st.markdown("#### Detalhamento da Carteira")
    
    df_exibir = pd.DataFrame({
        "Ativo": ativos_fam, "Investido (R$)": inv_fam, "Posição Atual (R$)": pos_fam,
        "Ganho (R$)": gan_fam, "Rentabilidade": rent_fam
    })
    
    styled_df = (df_exibir.style.format({
        "Investido (R$)": lambda x: fmt_brl(x), "Posição Atual (R$)": lambda x: fmt_brl(x),
        "Ganho (R$)": lambda x: fmt_brl(x), "Rentabilidade": lambda x: fmt_pct(x)
    }).map(style_taxa, subset=['Rentabilidade']))
    
    st.dataframe(styled_df, hide_index=True, use_container_width=True)

# ==========================================
# ABA 3: INVEST MARIA
# ==========================================
with aba_maria:
    st.subheader("Painel de Renda Fixa - Maria")
    
    try:
        ativos_maria = df_maria.iloc[2:7, 0].dropna().tolist()
        inv_maria_arr = df_maria.iloc[2:7, 4].apply(limpar_moeda).tolist()
        pos_maria_arr = df_maria.iloc[2:7, 5].apply(limpar_moeda).tolist()
        gan_maria_arr = df_maria.iloc[2:7, 6].apply(limpar_moeda).tolist()
        rent_maria_arr = df_maria.iloc[2:7, 7].apply(limpar_pct).tolist()
    except:
        ativos_maria = ["IPCA+ 2029", "IPCA+ 2032", "PRÉ 2032", "PRÉ 2035 c/juros sem", "SELIC 2031"]
        inv_maria_arr = [5779.67, 4988.63, 2001.26, 2370.30, 28000.00]
        pos_maria_arr = [6533.00, 5000.00, 2020.00, 2269.00, 31600.00]
        gan_maria_arr = [753.33, 11.37, 18.74, -101.30, 3600.00]
        rent_maria_arr = [13.03, 0.22, 0.93, -4.27, 12.85]

    resumo_maria_html = f"""
    <div class="resumo-grid">
        <div class="resumo-box"><div class="resumo-label">Total Investido</div><div class="resumo-value">{fmt_brl(inv_maria)}</div></div>
        <div class="resumo-box"><div class="resumo-label">Posição Atual</div><div class="resumo-value">{fmt_brl(pos_maria)}</div></div>
        <div class="resumo-box"><div class="resumo-label">Ganho Total</div><div class="resumo-value">{fmt_brl(ganho_maria)}</div></div>
        <div class="resumo-box"><div class="resumo-label">Rentabilidade Média</div><div class="resumo-value">{fmt_pct(rent_maria)}</div></div>
    </div>
    """
    st.markdown(resumo_maria_html, unsafe_allow_html=True)

    st.markdown("#### Detalhamento da Carteira")
    
    df_maria_exibir = pd.DataFrame({
        "Ativo": ativos_maria, "Investido (R$)": inv_maria_arr, "Posição Atual (R$)": pos_maria_arr,
        "Ganho (R$)": gan_maria_arr, "Rentabilidade": rent_maria_arr
    })
    
    styled_maria = (df_maria_exibir.style.format({
        "Investido (R$)": lambda x: fmt_brl(x), "Posição Atual (R$)": lambda x: fmt_brl(x),
        "Ganho (R$)": lambda x: fmt_brl(x), "Rentabilidade": lambda x: fmt_pct(x)
    }).map(style_taxa, subset=['Rentabilidade']))
    
    st.dataframe(styled_maria, hide_index=True, use_container_width=True)

# ==========================================
# ABA 4: MERCADO (INDICADORES MACRO)
# ==========================================
with aba_mercado:
    st.subheader("🌍 Indicadores de Mercado")
    st.markdown("Dados em tempo real via Google Sheets (aba Indicadores Macro).")
    
    if df_macro.empty:
        st.warning("Não foi possível carregar a aba 'Indicadores Macro'. Verifique se o nome da aba está escrito exatamente assim na sua planilha do Google (com espaços e acentos corretos) e se ela está compartilhada com o e-mail da Service Account.")
    else:
        try:
            # Filtra as linhas 9 (cabeçalho) até a linha 21, ignorando linhas vazias
            macro_df = df_macro.iloc[9:22, [0, 1, 2, 4, 5]].dropna(subset=[0])
            macro_df.columns = ["Ticker", "Indicador", "Classe", "Valor Atual", "Variação Dia"]
            
            # Divide em blocos de 2 colunas para renderizar no mobile (2x2)
            num_cols = 2
            for i in range(0, len(macro_df), num_cols):
                cols = st.columns(num_cols)
                for j in range(num_cols):
                    if i + j < len(macro_df):
                        row = macro_df.iloc[i+j]
                        ticker = row["Ticker"]
                        nome = row["Indicador"]
                        classe = row["Classe"]
                        val = row["Valor Atual"]
                        var = row["Variação Dia"]
                        
                        # Formatação do valor (Se for moeda, % ou pontos)
                        if "BRL" in str(row["Ticker"]) or "R$" in str(val):
                            val_str = fmt_brl(limpar_moeda(val))
                        elif "%" in str(val) or "Taxas" in str(classe):
                            val_str = fmt_pct(limpar_pct(val) * 100 if limpar_pct(val) < 1 else limpar_pct(val))
                        else:
                            try:
                                val_float = float(val)
                                val_str = f"{val_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                            except:
                                val_str = str(val)
                        
                        # Formatação da variação
                        try:
                            var_float = float(var) * 100 if abs(float(var)) < 1 else float(var)
                            var_str = f"{var_float:.2f}%".replace(".", ",")
                            cor_var = "#00FF00" if var_float >= 0 else "#FF4B4B"
                        except:
                            var_str = str(var)
                            cor_var = "gray"
                        
                        with cols[j]:
                            with st.container(border=True):
                                st.markdown(f"<div style='text-align: center; margin-top: -5px; margin-bottom: 5px; line-height: 1.1;'><b>{nome}</b><br><span style='font-size: 10px; color: gray;'>{classe}</span></div>", unsafe_allow_html=True)
                                st.markdown(f"<div style='text-align: center; font-size: 1.5rem; font-weight: bold;'>{val_str}</div>", unsafe_allow_html=True)
                                st.markdown(f"<div style='text-align: center; font-size: 0.9rem; color: {cor_var}; font-weight: bold;'>{var_str}</div>", unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Erro ao processar os dados da aba Macro: {e}")