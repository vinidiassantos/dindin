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
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
            margin-top: -10px; 
            margin-bottom: 10px;
            align-items: end;
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
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
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
        
        /* Ajustes finos nos cards de ação */
        div[data-testid="column"] div[data-testid="stVerticalBlockBorderWrapper"] { padding: 8px !important; }
        div[data-testid="column"] div[data-testid="stMetricValue"] { font-size: 1.15rem !important; }
        div[data-testid="column"] div[data-testid="stMarkdownContainer"] p { font-size: 11px !important; }
        
        .compact-list { margin-top: 0px; margin-bottom: 0px; padding-left: 20px; line-height: 1.3; font-size: 13px; }
        .compact-list li { margin-bottom: 3px; }
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
    """Transforma 'R$ 1.147,50' ou '-R$ 32,21' em float"""
    if pd.isna(val) or val == "": return 0.0
    s = str(val).replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".")
    try: return float(s)
    except: return 0.0

def limpar_pct(val):
    """Transforma '0,01%' em float 0.01"""
    if pd.isna(val) or val == "": return 0.0
    s = str(val).replace("%", "").replace(",", ".").replace(" ", "")
    try: return float(s)
    except: return 0.0

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
    'VALE3': 'Vale S.A. (Mineração)', 'WEGE3': 'WEG S.A. (Motores)', 'ITSA4': 'Itaúsa (Holding)', 
    'BOVA11': 'iShares (ETF Ibov)', 'CEAB3': 'C&A Modas (Varejo)', 'XPML11': 'XP Malls (FII Shoppings)', 
    'MCCI11': 'Mauá Capital (FII Papel)', 'PETR4': 'Petrobras (Petróleo)', 'BBAS3': 'Banco do Brasil (Banco)', 
    'ITUB4': 'Itaú Unibanco (Banco)', 'BBDC4': 'Bradesco (Banco)', 'MGLU3': 'Magazine Luiza (Varejo)', 
    'LREN3': 'Lojas Renner (Varejo)', 'VIVT3': 'Telefônica Vivo (Telecom)', 'TAEE11': 'Taesa (Energia)', 
    'KLBN11': 'Klabin (Papel/Celulose)', 'SANB11': 'Santander (Banco)', 'BPAC11': 'BTG Pactual (Banco)', 
    'HGLG11': 'CSHG Logística (FII)', 'KNRI11': 'Kinea Renda (FII Híbrido)', 'MXRF11': 'Maxi Renda (FII Papel)'
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
    return """<ul class="compact-list"><li><b>VALE3:</b> Ação sobe forte após 'call' positiva. <a class="news-link" href="https://valor.globo.com" target="_blank">[Ler mais]</a></li><li><b>WEGE3:</b> Dispara 4,4% hoje. <a class="news-link" href="https://br.investing.com" target="_blank">[Ler mais]</a></li></ul>"""

def get_oportunidades_renda_variavel():
    return """<ul class="compact-list"><li><b>Small Caps:</b> BB-BI inclui <b>Pine (PINE4)</b>. <a class="news-link" href="https://investalk.bb.com.br" target="_blank">[Ler mais]</a></li><li><b>Exportadoras:</b> Dólar alto coloca <b>Suzano (SUZB3)</b> no radar. <a class="news-link" href="https://www.infomoney.com.br" target="_blank">[Ler mais]</a></li></ul>"""

def get_noticias_renda_fixa(titulos):
    noticias = []
    for titulo in titulos:
        noticias.append(f'<li><b>{titulo}:</b> Acompanhe as taxas do Tesouro Direto hoje. <a class="news-link" href="https://www.infomoney.com.br" target="_blank">[Ler mais]</a></li>')
    return "<ul class='compact-list'>" + "".join(noticias) + "</ul>"

def get_oportunidades_renda_fixa():
    return """<ul class="compact-list"><li><b>IPCA+:</b> Juro real volta a 8% ao ano; oportunidade em títulos longos. <a class="news-link" href="https://www.seudinheiro.com" target="_blank">[Ler mais]</a></li></ul>"""

# ==========================================
# INTEGRAÇÃO COM GOOGLE SHEETS (LEITURA DINÂMICA)
# ==========================================
# Valores de Fallback (Caso a planilha falhe)
inv_rv = 1147.50; pos_rv = 1147.65; rent_rv = 0.01; ganho_rv_real = 0.15
inv_rf = 144373.68; pos_rf = 106779.65; rent_rf = 6.75; ganho_rf_real = 5129.14
inv_maria = 42723.32; pos_maria = 47341.00; ganho_maria = 4617.68; rent_maria = 10.81

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Lendo as abas exatas da planilha
    df_total = conn.read(worksheet="Total", ttl=10)
    df_rv = conn.read(worksheet="Renda Variável", ttl=10)
    df_rf = conn.read(worksheet="Renda Fixa", ttl=10)
    df_maria = conn.read(worksheet="Investimentos Maria", ttl=10)
    
    # Extração dos dados da aba Total (Ajuste os índices conforme a estrutura real da sua planilha)
    # Supondo que a linha 2 seja a linha de totais
    inv_rf = limpar_moeda(df_total.iloc[1, 1]) # B2
    pos_rf = limpar_moeda(df_total.iloc[1, 2]) # C2
    ganho_rf_real = limpar_moeda(df_total.iloc[1, 3]) # D2
    rent_rf = limpar_pct(df_total.iloc[1, 4]) # E2
    
    inv_rv = limpar_moeda(df_total.iloc[2, 1]) # B3
    pos_rv = limpar_moeda(df_total.iloc[2, 2]) # C3
    ganho_rv_real = limpar_moeda(df_total.iloc[2, 3]) # D3
    rent_rv = limpar_pct(df_total.iloc[2, 4]) # E3
    
    inv_maria = limpar_moeda(df_total.iloc[3, 1]) # B4
    pos_maria = limpar_moeda(df_total.iloc[3, 2]) # C4
    ganho_maria = limpar_moeda(df_total.iloc[3, 3]) # D4
    rent_maria = limpar_pct(df_total.iloc[3, 4]) # E4
    
    st.sidebar.success("📈 Dados do Google Sheets carregados!")
    
except Exception as e:
    st.sidebar.warning(f"⚠️ Usando dados locais (Planilha offline: {e})")

# Cálculo do Header: Apenas RV + RF (Sem a Maria)
inv_geral = inv_rv + inv_rf
pos_geral = pos_rv + pos_rf
rent_geral = ((pos_geral - inv_geral) / inv_geral) * 100 if inv_geral > 0 else 0

cor_rv = "#00FF00" if rent_rv >= 0 else "#FF4B4B"

# ==========================================
# CABEÇALHO COMPACTO
# ==========================================
header_html = f"""
<div class="header-grid" id="topo">
<div class="header-logo">
    <a href="#topo" target="_self" style="text-decoration: none; color: inherit; font-size: 2rem; font-weight: 700; line-height: 1;">💰 DinDin</a>
</div>
<div class="kpi-box"><div class="kpi-label">Total Investido (RV+RF)</div><div class="kpi-value">{fmt_brl(inv_geral)}</div></div>
<div class="kpi-box"><div class="kpi-label">Posição Atual</div><div class="kpi-value">{fmt_brl(pos_geral)}</div></div>
<div class="kpi-box"><div class="kpi-label">Rentab.</div><div class="kpi-value" style="color: #00FF00;">{fmt_pct(rent_geral)}</div></div>
<div class="kpi-box"><div class="kpi-label">Total Variável</div><div class="kpi-value">{fmt_brl(inv_rv)}</div><div class="kpi-sub" style="color: {cor_rv};">{fmt_pct(rent_rv)}</div></div>
<div class="kpi-box"><div class="kpi-label">Total Fixo</div><div class="kpi-value">{fmt_brl(inv_rf)}</div><div class="kpi-sub" style="color: #00FF00;">{fmt_pct(rent_rf)}</div></div>
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
    "📈 Renda Variável", "🏦 Renda Fixa", "👩 Invest Maria"
])

# ==========================================
# ABA 1: RENDA VARIÁVEL
# ==========================================
with aba_renda_variavel:
    st.subheader("Sua Carteira de Cotações")
    
    # Extraindo dados dinâmicos da aba Renda Variável
    # Ajuste os índices conforme a estrutura real da planilha
    try:
        # Supondo que os ativos comecem na linha 4 (índice 3) e as colunas sejam:
        # A: Ativo, B: Tipo, C: Setor, D: Cotas, E: Preço Pago, F: Preço Atual, G: Investido, H: Posição, I: Ganho, J: Rentab %, K: P/L, L: Div Yield %, M: Share %
        carteira_acoes = df_rv.iloc[3:, 0].dropna().tolist()
        inv_ativos = df_rv.iloc[3:, 6].apply(limpar_moeda).tolist()
        tipos = df_rv.iloc[3:, 1].fillna("Ação").tolist()
        setores = df_rv.iloc[3:, 2].fillna("-").tolist()
        pls = df_rv.iloc[3:, 10].apply(limpar_pct).tolist()
        dys = df_rv.iloc[3:, 11].apply(limpar_pct).tolist()
    except:
        # Fallback
        carteira_acoes = ['XPML11', 'MCCI11', 'ITSA4', 'BOVA11', 'CEAB3', 'VALE3', 'WEGE3']
        inv_ativos = [99.73, 89.89, 130.10, 173.23, 107.40, 322.70, 224.45]
        tipos = ["FII", "FII", "Ação", "ETF", "Ação", "Ação", "Ação"]
        setores = ["Shoppings", "Papel", "Bancos", "Índice", "Varejo", "Mineração", "Motores"]
        pls = [0.0] * len(carteira_acoes)
        dys = [0.0] * len(carteira_acoes)
    
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
        
        # Card 1
        with cols[0]:
            ativo = carteira_acoes[i]
            hist = buscar_dados(ativo)
            if not hist.empty:
                preco_atual = hist['Close'].iloc[-1]
                preco_anterior = hist['Close'].iloc[-2]
                variacao_pct = ((preco_atual - preco_anterior) / preco_anterior) * 100
                rsi = calcular_rsi(hist['Close'])
                min_6m = hist['Low'].tail(126).min()
                hist_5a = hist['Low'].tail(1260); min_5a = hist_5a.min()
                texto_data_5a = formatar_data_min(hist_5a.idxmin())
                share = (inv_ativos[i] / inv_rv) * 100 if inv_rv > 0 else 0
                sinal = "COMPRAR" if rsi < 35 else ("VENDER" if rsi > 70 else "MANTER")
                cor_sinal = "#00FF00" if rsi < 35 else ("#FF4B4B" if rsi > 70 else "#808080")
                nome_empresa = dicionario_empresas.get(ativo, "")
                link = gerar_link_investidor10(ativo)
                metricas = buscar_metricas_fundamentalistas(ativo)
                    
                with st.container(border=True):
                    st.markdown(f"<div style='text-align: center; margin-top: -5px; margin-bottom: 2px; line-height: 1.1;'><a class='ticker-link' href='{link}' target='_blank' style='font-size: 16px; font-weight: bold;'>{ativo}</a><br><span style='font-size: 10px; color: gray;'>{nome_empresa} | {setores[i]}</span></div>", unsafe_allow_html=True)
                    st.metric(label="Cotação Atual", value=fmt_brl(preco_atual), delta=f"{variacao_pct:.2f}%".replace(".", ","), label_visibility="collapsed")
                    
                    html_tecnico = f"<div style='font-size: 12px; line-height: 1.3; margin-top: -5px; margin-bottom: 5px;'>📉 <b>Mín 6m:</b> {fmt_brl(min_6m)}<br>⏳ <b>Mín 5a:</b> {fmt_brl(min_5a)}{texto_data_5a}<br>📊 <b>RSI:</b> {rsi:.1f}".replace(".", ",") + f"<br>🤖 <b>Sinal:</b> <span style='color:{cor_sinal}; font-weight: bold;'>{sinal}</span><br>💼 <b>Share:</b> {share:.1f}%".replace(".", ",") + "</div>"
                    st.markdown(html_tecnico, unsafe_allow_html=True)
                    
                    # Novos indicadores
                    if pls[i] > 0 or dys[i] > 0:
                        html_ind = "<hr style='margin: 4px 0; border-top: 1px solid rgba(128, 128, 128, 0.3);'>"
                        if pls[i] > 0: html_ind += f"<div style='font-size: 11px;'>💵 <b>P/L:</b> {pls[i]:.1f}</div>"
                        if dys[i] > 0: html_ind += f"<div style='font-size: 11px;'>💰 <b>Div. Yield:</b> {dys[i]:.1f}%</div>"
                        st.markdown(html_ind, unsafe_allow_html=True)
                    
                    if metricas.get("receita") or metricas.get("divida") or metricas.get("roe"):
                        html_indicadores = "<hr style='margin: 4px 0; border-top: 1px solid rgba(128, 128, 128, 0.3);'>"
                        if metricas.get("receita"): html_indicadores += f"<div style='font-size: 11px;'>💰 <b>Receita:</b> {fmt_grande(metricas['receita'])}</div>"
                        if metricas.get("divida"): html_indicadores += f"<div style='font-size: 11px;'>🏦 <b>Dív. Líq:</b> {fmt_grande(metricas['divida'])}</div>"
                        if metricas.get("roe"): html_indicadores += f"<div style='font-size: 11px;'>🏆 <b>ROE:</b> {fmt_pct(metricas['roe'])}</div>"
                        st.markdown(html_indicadores, unsafe_allow_html=True)
                    
                    st.progress(share / 100.0) 

        # Card 2
        with cols[1]:
            if i + 1 < len(carteira_acoes):
                ativo = carteira_acoes[i+1]
                hist = buscar_dados(ativo)
                if not hist.empty:
                    preco_atual = hist['Close'].iloc[-1]
                    preco_anterior = hist['Close'].iloc[-2]
                    variacao_pct = ((preco_atual - preco_anterior) / preco_anterior) * 100
                    rsi = calcular_rsi(hist['Close'])
                    min_6m = hist['Low'].tail(126).min()
                    hist_5a = hist['Low'].tail(1260); min_5a = hist_5a.min()
                    texto_data_5a = formatar_data_min(hist_5a.idxmin())
                    share = (inv_ativos[i+1] / inv_rv) * 100 if inv_rv > 0 else 0
                    sinal = "COMPRAR" if rsi < 35 else ("VENDER" if rsi > 70 else "MANTER")
                    cor_sinal = "#00FF00" if rsi < 35 else ("#FF4B4B" if rsi > 70 else "#808080")
                    nome_empresa = dicionario_empresas.get(ativo, "")
                    link = gerar_link_investidor10(ativo)
                    metricas = buscar_metricas_fundamentalistas(ativo)
                        
                    with st.container(border=True):
                        st.markdown(f"<div style='text-align: center; margin-top: -5px; margin-bottom: 2px; line-height: 1.1;'><a class='ticker-link' href='{link}' target='_blank' style='font-size: 16px; font-weight: bold;'>{ativo}</a><br><span style='font-size: 10px; color: gray;'>{nome_empresa} | {setores[i+1]}</span></div>", unsafe_allow_html=True)
                        st.metric(label="Cotação Atual", value=fmt_brl(preco_atual), delta=f"{variacao_pct:.2f}%".replace(".", ","), label_visibility="collapsed")
                        
                        html_tecnico = f"<div style='font-size: 12px; line-height: 1.3; margin-top: -5px; margin-bottom: 5px;'>📉 <b>Mín 6m:</b> {fmt_brl(min_6m)}<br>⏳ <b>Mín 5a:</b> {fmt_brl(min_5a)}{texto_data_5a}<br>📊 <b>RSI:</b> {rsi:.1f}".replace(".", ",") + f"<br>🤖 <b>Sinal:</b> <span style='color:{cor_sinal}; font-weight: bold;'>{sinal}</span><br>💼 <b>Share:</b> {share:.1f}%".replace(".", ",") + "</div>"
                        st.markdown(html_tecnico, unsafe_allow_html=True)
                        
                        if pls[i+1] > 0 or dys[i+1] > 0:
                            html_ind = "<hr style='margin: 4px 0; border-top: 1px solid rgba(128, 128, 128, 0.3);'>"
                            if pls[i+1] > 0: html_ind += f"<div style='font-size: 11px;'>💵 <b>P/L:</b> {pls[i+1]:.1f}</div>"
                            if dys[i+1] > 0: html_ind += f"<div style='font-size: 11px;'>💰 <b>Div. Yield:</b> {dys[i+1]:.1f}%</div>"
                            st.markdown(html_ind, unsafe_allow_html=True)
                        
                        if metricas.get("receita") or metricas.get("divida") or metricas.get("roe"):
                            html_indicadores = "<hr style='margin: 4px 0; border-top: 1px solid rgba(128, 128, 128, 0.3);'>"
                            if metricas.get("receita"): html_indicadores += f"<div style='font-size: 11px;'>💰 <b>Receita:</b> {fmt_grande(metricas['receita'])}</div>"
                            if metricas.get("divida"): html_indicadores += f"<div style='font-size: 11px;'>🏦 <b>Dív. Líq:</b> {fmt_grande(metricas['divida'])}</div>"
                            if metricas.get("roe"): html_indicadores += f"<div style='font-size: 11px;'>🏆 <b>ROE:</b> {fmt_pct(metricas['roe'])}</div>"
                            st.markdown(html_indicadores, unsafe_allow_html=True)
                        
                        st.progress(share / 100.0)

    # RADAR
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
        
        for i in range(0, len(oportunidades), 2):
            cols_op = st.columns(2)
            for j in range(2):
                if i + j < len(oportunidades):
                    op = oportunidades[i+j]
                    nome_empresa_radar = dicionario_empresas.get(op['ativo'], "")
                    link_op = gerar_link_investidor10(op['ativo'])
                    estrelas = "⭐" * op['score']
                    
                    with cols_op[j]:
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
    
    # Extraindo dados dinâmicos da aba Renda Fixa
    try:
        # Supondo que os ativos comecem na linha 2 (índice 1) e as colunas sejam:
        # A: Ativo, B: Vencimento, C: Taxa, D: Investido, E: Posição, F: Ganho, G: Rentab, H: Share
        ativos_fam = df_rf.iloc[1:, 0].dropna().tolist()
        inv_fam = df_rf.iloc[1:, 3].apply(limpar_moeda).tolist()
        pos_fam = df_rf.iloc[1:, 4].apply(limpar_moeda).tolist()
        gan_fam = df_rf.iloc[1:, 5].apply(limpar_moeda).tolist()
        rent_fam = df_rf.iloc[1:, 6].apply(limpar_pct).tolist()
    except:
        ativos_fam = ["IPCA+ 2032", "PRÉ 2032", "Selic 2031"]
        inv_fam = [2987.73, 1476.27, 96038.86]
        pos_fam = [3092.00, 1457.00, 101083.00]
        gan_fam = [104.27, -19.27, 5044.14]
        rent_fam = [3.49, -1.31, 5.25]

    resumo_rf_html = f"""
    <div class="resumo-grid">
        <div class="resumo-box"><div class="resumo-label">Total Investido</div><div class="resumo-value">{fmt_brl(inv_rf)}</div></div>
        <div class="resumo-box"><div class="resumo-label">Posição Atual</div><div class="resumo-value">{fmt_brl(pos_rf)}</div></div>
        <div class="resumo-box"><div class="resumo-label">Ganho Total</div><div class="resumo-value">{fmt_brl(ganho_rf_real)}</div></div>
        <div class="resumo-box"><div class="resumo-label">Rentabilidade Média</div><div class="resumo-value">{fmt_pct(rent_rf)}</div></div>
    </div>
    """
    st.markdown(resumo_rf_html, unsafe_allow_html=True)

    st.markdown("#### Detalhamento e Evolução Mês a Mês (2026)")
    
    df_fam, df_grafico_fam = gerar_tabela_renda_fixa(ativos_fam, inv_fam, pos_fam, gan_fam, rent_fam)
    df_fam.insert(5, "Share (%)", (df_fam["Investido (R$)"] / inv_rf) * 100)

    cols_to_center_fam = [c for c in df_fam.columns if c != 'Ativo']

    styled_fam = (df_fam.style
                  .map(style_taxa, subset=['Taxa (%)'])
                  .format({
                      "Investido (R$)": lambda x: fmt_brl(x), "Posição Atual (R$)": lambda x: fmt_brl(x),
                      "Ganho (R$)": lambda x: fmt_brl(x), "Taxa (%)": lambda x: fmt_pct(x),
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
    
    # Extraindo dados dinâmicos da aba Investimentos Maria
    try:
        # Supondo que os ativos comecem na linha 3 (índice 2) e as colunas sejam:
        # A: Ativo, B: Vencimento, C: Taxa, D: Investido, E: Posição, F: Ganho, G: Rentab, H: Share
        ativos_maria = df_maria.iloc[2:, 0].dropna().tolist()
        inv_maria_arr = df_maria.iloc[2:, 3].apply(limpar_moeda).tolist()
        pos_maria_arr = df_maria.iloc[2:, 4].apply(limpar_moeda).tolist()
        gan_maria_arr = df_maria.iloc[2:, 5].apply(limpar_moeda).tolist()
        rent_maria_arr = df_maria.iloc[2:, 6].apply(limpar_pct).tolist()
    except:
        ativos_maria = ["IPCA+ 2029", "IPCA+ 2032", "IPCA+ 2035 c/juros sem", "PRÉ 2032", "PRÉ 2035 c/juros sem", "SELIC 2031"]
        inv_maria_arr = [5779.67, 1580.87, 5444.10, 1452.61, 2370.30, 26095.77]
        pos_maria_arr = [6528.00, 1636.00, 5658.00, 1475.00, 2254.00, 29790.00]
        gan_maria_arr = [748.33, 55.13, 213.90, 22.39, -116.30, 3694.23]
        rent_maria_arr = [12.95, 3.49, 3.93, 1.54, -4.91, 14.16]

    resumo_maria_html = f"""
    <div class="resumo-grid">
        <div class="resumo-box"><div class="resumo-label">Total Investido</div><div class="resumo-value">{fmt_brl(inv_maria)}</div></div>
        <div class="resumo-box"><div class="resumo-label">Posição Atual</div><div class="resumo-value">{fmt_brl(pos_maria)}</div></div>
        <div class="resumo-box"><div class="resumo-label">Ganho Total</div><div class="resumo-value">{fmt_brl(ganho_maria)}</div></div>
        <div class="resumo-box"><div class="resumo-label">Rentabilidade Média</div><div class="resumo-value">{fmt_pct(rent_maria)}</div></div>
    </div>
    """
    st.markdown(resumo_maria_html, unsafe_allow_html=True)

    st.markdown("#### Detalhamento e Evolução Mês a Mês (2026)")
    
    df_maria, df_grafico_maria = gerar_tabela_renda_fixa(ativos_maria, inv_maria_arr, pos_maria_arr, gan_maria_arr, rent_maria_arr)
    df_maria.insert(5, "Share (%)", (df_maria["Investido (R$)"] / inv_maria) * 100)

    cols_to_center_maria = [c for c in df_maria.columns if c != 'Ativo']

    styled_maria = (df_maria.style
                    .map(style_taxa, subset=['Taxa (%)'])
                    .format({
                        "Investido (R$)": lambda x: fmt_brl(x), "Posição Atual (R$)": lambda x: fmt_brl(x),
                        "Ganho (R$)": lambda x: fmt_brl(x), "Taxa (%)": lambda x: fmt_pct(x),
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