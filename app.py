import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date

# Define a configuração da página
st.set_page_config(layout="wide", page_title="Aplicação Financeira")

# --- Configuração Segura da API ---
def setup_api():
    """Configura a API token de forma segura"""
    try:
        # Tenta pegar do Streamlit Secrets (produção)
        if 'FLOW_API_TOKEN' in st.secrets:
            return st.secrets['FLOW_API_TOKEN']
    except:
        pass
    
    # Fallback: input do usuário (desenvolvimento)
    st.sidebar.title("🔐 Autenticação")
    token = st.sidebar.text_input("API Token Flow2:", type="password")
    
    if token:
        st.sidebar.success("✅ Token configurado!")
        return token
    else:
        st.sidebar.error("❌ Token da API é obrigatório")
        st.stop()

# Inicializa a API
API_TOKEN = setup_api()

# --- Funções Helper ---

def format_brl(value):
    """
    Formata um número float para o padrão BRL (R$ 1.234,56).
    """
    try:
        if pd.isna(value) or value == 0:
            return "R$ 0,00"
        # Formata como en-US (ex: 1,234.56)
        formatted = f"{float(value):,.2f}"
        # Inverte os separadores para o padrão pt-BR
        formatted_br = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {formatted_br}"
    except (ValueError, TypeError):
        return "R$ 0,00"

def get_status(row):
    """
    Calcula o status de um título (A vencer, Vence hoje, Vencido, Baixado).
    """
    try:
        # 1. Verifica se foi pago (Baixado)
        if pd.notna(row.get('dataBaixa')) or pd.notna(row.get('dataCredito')):
            return "Baixado" 
        
        # 2. Prepara as datas para comparação
        today = pd.to_datetime(date.today()).normalize()
        vencimento = pd.to_datetime(row.get('dataVencimentoReal')).normalize()
        
        # 3. Verifica se a data de vencimento é válida
        if pd.isna(vencimento):
            return "A vencer"
            
        # 4. Compara as datas
        if vencimento == today:
            return "Vence hoje" 
        elif vencimento < today:
            return "Vencido"
        else:
            return "A vencer" 
    except Exception:
        return "A vencer"

# --- Estilização CSS Customizada ---
st.markdown("""
<style>
    /* Abas */
    [data-testid="stTabs"] {
        background-color: #FAFAFA;
        border: 1px solid #E0E0E0;
        border-radius: 10px;
        padding: 10px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    /* Botão da Aba Ativa */
    [data-testid="stTabs"] button[aria-selected="true"] {
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
        border-radius: 5px;
    }
    /* Botão da Aba Inativa */
    [data-testid="stTabs"] button {
        background-color: transparent;
        color: #555555;
        border: none;
        border-radius: 5px;
    }

    /* Títulos dos sub-cabeçalhos */
    h3 {
        color: #FFFFFF;
        background-color: #4CAF50;
        padding: 10px;
        border-radius: 5px;
        text-align: center;
    }
    
    /* Styling dos cartões KPI */
    [data-testid="stMetric"] {
        background-color: #FAFAFA;
        border: 1px solid #E0E0E0;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    [data-testid="stMetricLabel"] {
        font-weight: bold;
        color: #555555;
    }
    [data-testid="stMetricValue"] {
        font-size: 2em;
        font-weight: bold;
        color: #333333 !important; 
        background-color: transparent !important; 
    }
    
    /* Cabeçalho das tabelas */
    .stDataFrame th {
        background-color: #E8F5E9;
        font-size: 1.1em;
        font-weight: bold;
        color: #333333;
    }

    .stDataFrame td {
        color: #333333 !important;
    }

    /* Tabela de extratos HTML */
    .extratos-table-container {
        height: 400px;
        overflow-y: auto;
        border: 1px solid #E0E0E0;
        border-radius: 5px;
    }
    .extratos-table {
        width: 100%;
        border-collapse: collapse;
    }
    .extratos-table th {
        background-color: #E8F5E9;
        font-size: 1.1em;
        font-weight: bold;
        color: #333333;
        padding: 8px;
        text-align: left;
        border-bottom: 2px solid #4CAF50;
        position: sticky;
        top: 0;
    }
    .extratos-table td {
        padding: 8px;
        border-bottom: 1px solid #DDDDDD;
        color: #333333 !important;
    }

    .block-container {
        padding-top: 2rem;
    }

    footer {visibility: hidden;}
    #MainMenu {visibility: visible;}
</style>
""", unsafe_allow_html=True)

# --- Carregamento de Dados (Cache) ---

@st.cache_data(ttl=600)
def load_movimentos_e_saldos(api_token):
    """
    Carrega dados das APIs de movimentos e saldos.
    """
    try:
        headers = {"Authorization": f"Bearer {api_token}"}
        
        # 1. Carregar Movimentos Bancários
        url_movimentos = "https://api.flow2.com.br/v1/movimentosBancarios?DesabilitarPaginacao=true&DataMovimentoMaiorOuIgualA=2025-01-01"
        response_mov = requests.get(url_movimentos, headers=headers, timeout=30)
        response_mov.raise_for_status()
        data_mov = response_mov.json()
        
        if 'itens' in data_mov and data_mov['itens']:
            df_movimentos = pd.json_normalize(data_mov, record_path=['itens'])
        else:
            df_movimentos = pd.DataFrame()
            
        # Processa movimentos se existirem dados
        if not df_movimentos.empty:
            df_movimentos = df_movimentos.rename(columns={
                "valor": "Valor",
                "dataMovimento": "DataMovimento",
                "descricao": "Descricao",
                "operacao": "Operacao",
                "nomeBanco": "Banco"
            })
            
            df_movimentos['Valor'] = pd.to_numeric(df_movimentos.get('Valor', 0), errors='coerce').fillna(0)
            df_movimentos['DataMovimento'] = pd.to_datetime(df_movimentos.get('DataMovimento'), errors='coerce')
            df_movimentos['Data'] = df_movimentos['DataMovimento'].dt.date
            df_movimentos['Horario'] = df_movimentos['DataMovimento'].dt.time
            df_movimentos['Descricao'] = df_movimentos.get('Descricao', '').astype(str).str.upper()
            df_movimentos['Operacao'] = df_movimentos.get('Operacao', '').astype(str)
        else:
            # Cria DataFrame vazio com colunas esperadas
            df_movimentos = pd.DataFrame(columns=['Data', 'Horario', 'Descricao', 'Valor', 'Operacao', 'Banco'])

        # 2. Carregar Saldo dos Bancos
        url_saldos = "https://api.flow2.com.br/v1/saldoBancos"
        response_saldos = requests.get(url_saldos, headers=headers, timeout=30)
        response_saldos.raise_for_status()
        data_saldos = response_saldos.json()
        
        if data_saldos:
            df_saldos = pd.json_normalize(data_saldos)
            df_saldos = df_saldos.rename(columns={
                "banco.nome": "Banco",
                "saldo": "Saldo dos bancos"
            })
            df_saldos['Saldo dos bancos'] = pd.to_numeric(df_saldos.get('Saldo dos bancos', 0), errors='coerce').fillna(0)
        else:
            df_saldos = pd.DataFrame(columns=['Banco', 'Saldo dos bancos'])

        return df_movimentos, df_saldos

    except Exception as e:
        st.error(f"Erro ao carregar dados bancários: {e}")
        return pd.DataFrame(), pd.DataFrame()

@st.cache_data(ttl=600)
def load_receber_e_clientes(api_token):
    """
    Carrega dados das APIs de Contas a Receber e Clientes.
    """
    try:
        headers = {"Authorization": f"Bearer {api_token}"}
        
        # 1. Carregar Contas a Receber
        url_receber = "https://api.flow2.com.br/v1/recebers?DesabilitarPaginacao=true"
        response_receber = requests.get(url_receber, headers=headers, timeout=30)
        response_receber.raise_for_status()
        data_receber = response_receber.json()

        # Normaliza os 'itens'
        if 'itens' in data_receber and data_receber['itens']:
            df_receber = pd.json_normalize(data_receber, record_path=['itens'])
        else:
            df_receber = pd.DataFrame()

        # 2. Carregar Clientes
        url_clientes = "https://api.flow2.com.br/v1/clientes?DesabilitarPaginacao=true"
        response_clientes = requests.get(url_clientes, headers=headers, timeout=30)
        response_clientes.raise_for_status()
        data_clientes = response_clientes.json()

        # Normaliza os clientes
        if 'itens' in data_clientes and data_clientes['itens']:
            df_clientes = pd.json_normalize(data_clientes, record_path=['itens'])
            df_clientes = df_clientes.rename(columns={
                "id": "idCliente", 
                "nomeRazaoSocial": "Cliente"
            })
            df_clientes = df_clientes[['idCliente', 'Cliente']] 
        else:
            df_clientes = pd.DataFrame(columns=['idCliente', 'Cliente'])

        # 3. Juntar as tabelas
        if not df_receber.empty:
            if 'idCliente' not in df_receber.columns:
                df_receber['idCliente'] = None
                 
            if not df_clientes.empty:
                df_final = pd.merge(df_receber, df_clientes, on="idCliente", how="left")
            else:
                df_final = df_receber
            
            df_final['Cliente'] = df_final.get('Cliente', 'Cliente não informado').fillna('Cliente não informado')
        else:
            df_final = pd.DataFrame()

        return df_final

    except Exception as e:
        st.error(f"Erro ao carregar dados de contas a receber: {e}")
        return pd.DataFrame()

# --- Início da Interface ---

st.title("📊 APLICAÇÃO FINANCEIRA")

# Cria as Abas principais
tab_bancario, tab_receber = st.tabs(["🏦 Controle Bancário", "🧾 Contas a Receber"])

# --- ABA 1: CONTROLE BANCÁRIO ---
with tab_bancario:
    
    df_movimentos, df_saldos = load_movimentos_e_saldos(API_TOKEN)

    if df_movimentos.empty and df_saldos.empty:
        st.info("📭 Nenhum dado bancário disponível no momento")
    else:
        st.subheader("🔧 Filtros")
        col1, col2 = st.columns([1, 2])

        with col1:
            if not df_movimentos.empty and 'Data' in df_movimentos.columns:
                min_date = df_movimentos['Data'].min()
                max_date = df_movimentos['Data'].max()
                if pd.isna(min_date): min_date = date.today()
                if pd.isna(max_date): max_date = date.today()
                date_range = st.date_input("📅 Período", [min_date, max_date], key="tab1_date")
            else:
                date_range = [date.today(), date.today()]

        with col2:
            bancos = []
            if not df_movimentos.empty and 'Banco' in df_movimentos.columns:
                bancos.extend(df_movimentos['Banco'].dropna().unique().tolist())
            if not df_saldos.empty and 'Banco' in df_saldos.columns:
                bancos.extend(df_saldos['Banco'].dropna().unique().tolist())
            bancos = sorted(list(set(bancos)))
            bancos_selecionados = st.multiselect("🏦 Bancos", bancos, default=bancos, key="tab1_banks")

        # Aplicar filtros
        if not df_movimentos.empty:
            df_filtrado = df_movimentos[
                (df_movimentos['Data'].between(date_range[0], date_range[1])) &
                (df_movimentos['Banco'].isin(bancos_selecionados))
            ] if 'Data' in df_movimentos.columns else df_movimentos
        else:
            df_filtrado = df_movimentos

        # KPIs
        st.divider()
        st.subheader("📈 Métricas")

        if not df_filtrado.empty:
            entradas = df_filtrado[~df_filtrado['Operacao'].str.contains('-', na=False)]['Valor'].sum()
            saidas = df_filtrado[df_filtrado['Operacao'].str.contains('-', na=False)]['Valor'].sum()
            saldo = entradas - saidas
        else:
            entradas = saidas = saldo = 0

        col1, col2, col3 = st.columns(3)
        col1.metric("💰 Entradas", format_brl(entradas))
        col2.metric("💸 Saídas", format_brl(saidas), delta=format_brl(-saidas), delta_color="inverse")
        col3.metric("💳 Saldo", format_brl(saldo))

        # Tabelas
        st.divider()
        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("📋 Extratos Bancários")
            if not df_filtrado.empty:
                # Preparar dados para exibição
                df_display = df_filtrado.copy()
                df_display['Total Entradas'] = df_display.apply(
                    lambda row: row['Valor'] if '-' not in str(row['Operacao']) else 0, axis=1
                )
                df_display['Total Saídas'] = df_display.apply(
                    lambda row: row['Valor'] if '-' in str(row['Operacao']) else 0, axis=1
                )
                
                df_grouped = df_display.groupby(['Data', 'Descricao']).agg({
                    'Total Entradas': 'sum', 'Total Saídas': 'sum'
                }).reset_index()
                
                df_grouped = df_grouped[(df_grouped['Total Entradas'] != 0) | (df_grouped['Total Saídas'] != 0)]
                df_grouped = df_grouped.sort_values('Data', ascending=False)
                
                # Formatar para HTML
                df_formatted = df_grouped.copy()
                df_formatted['Data'] = pd.to_datetime(df_formatted['Data']).dt.strftime('%d/%m/%Y')
                df_formatted['Total Entradas'] = df_formatted['Total Entradas'].apply(
                    lambda x: format_brl(x) if x > 0 else ""
                )
                df_formatted['Total Saídas'] = df_formatted['Total Saídas'].apply(
                    lambda x: f"<span style='color:red; font-weight:bold;'>{format_brl(x)}</span>" if x > 0 else ""
                )
                df_formatted = df_formatted.rename(columns={'Descricao': 'Descrição'})
                
                html_table = df_formatted.to_html(escape=False, index=False, classes="extratos-table")
                st.markdown(f'<div class="extratos-table-container">{html_table}</div>', unsafe_allow_html=True)
            else:
                st.info("Nenhum movimento encontrado para os filtros selecionados")

        with col2:
            st.subheader("🏦 Saldos")
            if not df_saldos.empty:
                df_saldos_filtrado = df_saldos[df_saldos['Banco'].isin(bancos_selecionados)]
                if not df_saldos_filtrado.empty:
                    total_saldo = df_saldos_filtrado['Saldo dos bancos'].sum()
                    df_display_saldos = df_saldos_filtrado.copy()
                    df_display_saldos['Saldo dos bancos'] = df_display_saldos['Saldo dos bancos'].apply(format_brl)
                    
                    # Adicionar linha de total
                    total_row = pd.DataFrame([{'Banco': 'TOTAL', 'Saldo dos bancos': format_brl(total_saldo)}])
                    df_display_saldos = pd.concat([df_display_saldos, total_row], ignore_index=True)
                    
                    st.dataframe(df_display_saldos, use_container_width=True, height=400)
                else:
                    st.info("Nenhum saldo encontrado")
            else:
                st.info("Nenhum saldo disponível")

# --- ABA 2: CONTAS A RECEBER ---
with tab_receber:
    
    df_receber_raw = load_receber_e_clientes(API_TOKEN)

    if df_receber_raw.empty:
        st.info("📭 Nenhuma conta a receber encontrada")
    else:
        try:
            # Preprocessamento dos dados
            df_receber = df_receber_raw.copy()
            
            # TRATAMENTO ROBUSTO DE DATAS
            def get_data_vencimento(row):
                # Tenta dataVencimentoNominal primeiro
                nominal = row.get('dataVencimentoNominal')
                if pd.notna(nominal) and nominal != '':
                    return nominal
                # Fallback para dataVencimentoReal
                real = row.get('dataVencimentoReal')
                if pd.notna(real) and real != '':
                    return real
                return pd.NaT
            
            df_receber['dataVencimentoFinal'] = df_receber.apply(get_data_vencimento, axis=1)
            df_receber['dataVencimentoReal'] = pd.to_datetime(df_receber['dataVencimentoFinal'], errors='coerce')
            df_receber = df_receber.drop('dataVencimentoFinal', axis=1)
            
            # Outras datas
            df_receber['dataBaixa'] = pd.to_datetime(df_receber.get('dataBaixa'), errors='coerce')
            df_receber['dataCredito'] = pd.to_datetime(df_receber.get('dataCredito'), errors='coerce')
            
            # Valor
            df_receber['Valor'] = pd.to_numeric(df_receber.get('valorBruto', 0), errors='coerce').fillna(0).abs()
            
            # Status
            df_receber['Status'] = df_receber.apply(get_status, axis=1)
            
            # Colunas de exibição - VERIFICAÇÃO SEGURA
            if 'dataVencimentoReal' in df_receber.columns:
                df_receber['Vencimento'] = df_receber['dataVencimentoReal'].dt.date
            else:
                df_receber['Vencimento'] = pd.NaT
                
            if 'dataBaixa' in df_receber.columns:
                df_receber['Recebido em'] = df_receber['dataBaixa'].dt.date
            else:
                df_receber['Recebido em'] = pd.NaT
                
            df_receber['Nº projeto'] = df_receber.get('codigoProjeto', 'N/A')
            
        except Exception as e:
            st.error(f"❌ Erro no processamento dos dados: {e}")
            st.info("📋 Dados brutos para análise:")
            st.dataframe(df_receber_raw.head(10))
            st.stop()

        # Filtros - COM VERIFICAÇÃO DE SEGURANÇA
        st.subheader("🔧 Filtros")
        col1, col2 = st.columns(2)

        with col1:
            if 'Status' in df_receber.columns:
                status_opcoes = df_receber['Status'].unique().tolist()
                status_selecionados = st.multiselect(
                    "📊 Status", 
                    status_opcoes, 
                    default=status_opcoes,
                    key="tab2_status"
                )
            else:
                status_selecionados = []
                st.warning("Coluna 'Status' não encontrada")

        with col2:
            if 'Vencimento' in df_receber.columns:
                # Filtro seguro para datas
                try:
                    min_venc = df_receber['Vencimento'].min()
                    max_venc = df_receber['Vencimento'].max()
                    if pd.isna(min_venc): 
                        min_venc = date.today()
                    if pd.isna(max_venc): 
                        max_venc = date.today()
                    
                    periodo = st.date_input(
                        "📅 Período Vencimento", 
                        [min_venc, max_venc], 
                        key="tab2_date"
                    )
                except Exception as e:
                    st.error(f"Erro ao processar datas: {e}")
                    periodo = [date.today(), date.today()]
            else:
                periodo = [date.today(), date.today()]
                st.warning("Coluna 'Vencimento' não encontrada")

        # Aplicar filtros com segurança
        df_filtrado = df_receber.copy()
        
        if 'Status' in df_receber.columns and status_selecionados:
            df_filtrado = df_filtrado[df_filtrado['Status'].isin(status_selecionados)]
            
        if 'Vencimento' in df_receber.columns:
            try:
                df_filtrado = df_filtrado[
                    (df_filtrado['Vencimento'].notna()) &
                    (df_filtrado['Vencimento'] >= periodo[0]) &
                    (df_filtrado['Vencimento'] <= periodo[1])
                ]
            except Exception as e:
                st.error(f"Erro ao filtrar por data: {e}")

        # KPIs
        st.divider()
        st.subheader("📈 Métricas")

        total_receber = 0
        total_vencido = 0
        recebido_mes = 0

        if 'Status' in df_filtrado.columns and 'Valor' in df_filtrado.columns:
            total_receber = df_filtrado[df_filtrado['Status'] != 'Baixado']['Valor'].sum()
            total_vencido = df_filtrado[df_filtrado['Status'] == 'Vencido']['Valor'].sum()
        
        # Recebido este mês (ignora filtros)
        if 'Recebido em' in df_receber.columns and 'Valor' in df_receber.columns:
            hoje = date.today()
            try:
                recebido_mes_df = df_receber[
                    (df_receber['Recebido em'].notna()) &
                    (df_receber['Recebido em'] >= date(hoje.year, hoje.month, 1)) &
                    (df_receber['Recebido em'] <= hoje)
                ]
                recebido_mes = recebido_mes_df['Valor'].sum()
            except Exception:
                recebido_mes = 0

        col1, col2, col3 = st.columns(3)
        col1.metric("💰 A Receber", format_brl(total_receber))
        col2.metric("⚠️ Vencido", format_brl(total_vencido))
        col3.metric("✅ Recebido Mês", format_brl(recebido_mes))

        # Tabela principal
        st.divider()
        st.subheader("📋 Detalhe de Contas a Receber")
        
        colunas_exibir = ['Cliente', 'Nº projeto', 'Vencimento', 'Recebido em', 'Status', 'Valor']
        colunas_disponiveis = [col for col in colunas_exibir if col in df_filtrado.columns]
        
        if colunas_disponiveis:
            df_display = df_filtrado[colunas_disponiveis].copy()
            
            # Formatar colunas
            if 'Valor' in df_display.columns:
                df_display['Valor'] = df_display['Valor'].apply(format_brl)
                df_display = df_display.rename(columns={'Valor': 'Valor Parcela'})
            
            if 'Vencimento' in df_display.columns:
                df_display['Vencimento'] = df_display['Vencimento'].apply(
                    lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else ''
                )
            
            if 'Recebido em' in df_display.columns:
                df_display['Recebido em'] = df_display['Recebido em'].apply(
                    lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else ''
                )
            
            st.dataframe(df_display, use_container_width=True, height=400)
            
            # Estatísticas
            st.info(f"📊 Mostrando {len(df_display)} de {len(df_receber)} registros")
        else:
            st.warning("Nenhuma coluna disponível para exibição")
            st.info("Colunas disponíveis no DataFrame:")
            st.write(list(df_filtrado.columns))

        # Dados brutos para debug
        with st.expander("🔍 Dados Brutos (Primeiros 10)"):
            st.dataframe(df_receber_raw.head(10))
