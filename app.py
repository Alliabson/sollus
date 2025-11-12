import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# Define a configuração da página
# layout="wide" usa a tela inteira, como no seu BI desktop.
# ISSO DEVE SER O PRIMEIRO COMANDO STREAMLIT
st.set_page_config(layout="wide", page_title="Controle Financeiro GSA")

# --- Função Helper de Formatação ---
def format_brl(value):
    """
    Formata um número float para o padrão BRL (R$ 1.234,56).
    """
    try:
        # Formata como en-US (ex: 1,234.56)
        formatted = f"{float(value):,.2f}"
        # Inverte os separadores para o padrão pt-BR
        # 1. Troca vírgula por placeholder: 1X234.56
        # 2. Troca ponto por vírgula: 1X234,56
        # 3. Troca placeholder por ponto: 1.234,56
        formatted_br = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {formatted_br}"
    except (ValueError, TypeError):
        return "R$ 0,00"

# --- Estilização CSS Customizada ---
# Injeta CSS para replicar a aparência verde do seu Power BI
st.markdown("""
<style>
    /* Títulos dos sub-cabeçalhos (Extratos, Saldo) */
    h3 {
        color: #FFFFFF;
        background-color: #4CAF50; /* Verde do seu BI */
        padding: 10px;
        border-radius: 5px;
        text-align: center;
    }
    
    /* Styling dos cartões KPI (Métricas) */
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
        /* --- CORREÇÃO DE COMPATIBILIDADE (NAVEGADORES) --- */
        color: #333333 !important; 
        background-color: transparent !important; 
        user-select: none !important;
    }
    
    /* Cabeçalho das tabelas (DataFrames) */
    .stDataFrame th {
        background-color: #E8F5E9; /* Verde claro */
        font-size: 1.1em;
        font-weight: bold;
        color: #333333;
    }

    /* Estilos para a tabela de extratos HTML */
    .extratos-table {
        width: 100%;
        border-collapse: collapse;
    }
    .extratos-table th {
        background-color: #E8F5E9; /* Verde claro (do .stDataFrame th) */
        font-size: 1.1em;
        font-weight: bold;
        color: #333333;
        padding: 8px;
        text-align: left;
        border-bottom: 2px solid #4CAF50; /* Linha verde */
        /* --- Posição fixa para o cabeçalho --- */
        position: sticky;
        top: 0;
        z-index: 1;
    }
    .extratos-table td {
        padding: 8px;
        border-bottom: 1px solid #DDDDDD; /* Linha cinza entre-linhas */
        vertical-align: top;
    }
    .extratos-table tr:last-child td {
        border-bottom: none;
    }

    /* --- CORREÇÃO BARRA DE ROLAGEM --- */
    /* Adiciona um container com altura fixa e rolagem */
    .table-container {
        height: 400px; /* Mesma altura da outra tabela */
        overflow-y: auto; /* Adiciona barra de rolagem vertical */
        border: 1px solid #E0E0E0; /* Borda leve para o container */
        border-radius: 5px;
    }
    /* --- FIM DA CORREÇÃO --- */

    /* Remove o espaço extra no topo da página */
    .block-container {
        padding-top: 2rem;
    }

    /* Oculta o "Made with Streamlit" */
    footer {visibility: hidden;}
    
</style>
""", unsafe_allow_html=True)

# --- Carregamento de Dados (Funções) ---
# @st.cache_data armazena o resultado da função, evitando recarregar da API
# a cada interação do usuário.
@st.cache_data(ttl=600) # Cache de 10 minutos
def load_data(api_token):
    """
    Carrega dados das APIs de movimentos e saldos (Aba 1).
    """
    try:
        headers = {"Authorization": f"Bearer {api_token}"}
        
        # 1. Carregar Movimentos Bancários (fMovimentos)
        url_movimentos = "https://api.flow2.com.br/v1/movimentosBancarios?DesabilitarPaginacao=true&DataMovimentoMaiorOuIgualA=2025-01-01"
        response_mov = requests.get(url_movimentos, headers=headers)
        response_mov.raise_for_status() 
        data_mov = response_mov.json()
        
        df_movimentos = pd.json_normalize(data_mov, record_path=['itens'])
        df_movimentos = df_movimentos.rename(columns={
            "valor": "Valor", "dataMovimento": "DataMovimento", "descricao": "Descricao",
            "operacao": "Operacao", "nomeBanco": "Banco"
        })
        if 'Operacao' in df_movimentos.columns:
            df_movimentos['Operacao'] = df_movimentos['Operacao'].astype(str)
        
        df_movimentos['Valor'] = pd.to_numeric(df_movimentos['Valor'])
        df_movimentos['DataMovimento'] = pd.to_datetime(df_movimentos['DataMovimento'])
        df_movimentos['Data'] = df_movimentos['DataMovimento'].dt.date
        df_movimentos['Horario'] = df_movimentos['DataMovimento'].dt.time
        df_movimentos['Descricao'] = df_movimentos['Descricao'].str.upper()
        colunas_mov = ['Data', 'Horario', 'Descricao', 'Valor', 'Operacao', 'Banco']
        df_movimentos = df_movimentos[colunas_mov]

        # 2. Carregar Saldo dos Bancos (fSaldoBancos)
        url_saldos = "https://api.flow2.com.br/v1/saldoBancos"
        response_saldos = requests.get(url_saldos, headers=headers)
        response_saldos.raise_for_status()
        data_saldos = response_saldos.json()
        
        df_saldos = pd.json_normalize(data_saldos)
        df_saldos = df_saldos.rename(columns={"banco.nome": "Banco", "saldo": "Saldo dos bancos"})
        df_saldos['Saldo dos bancos'] = pd.to_numeric(df_saldos['Saldo dos bancos'])
        df_saldos = df_saldos[['Banco', 'Saldo dos bancos']]
        
        return df_movimentos, df_saldos

    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao carregar dados da API (Financeiro): {e}")
        return None, None
    except Exception as e:
        st.error(f"Erro ao processar os dados (Financeiro): {e}")
        return None, None

@st.cache_data(ttl=600) # Cache de 10 minutos
def load_receber(api_token):
    """
    Carrega dados da API de Contas a Receber (Aba 2).
    """
    try:
        headers = {"Authorization": f"Bearer {api_token}"}
        # --- CORREÇÃO: Munda da API /boletos para /recebers ---
        # Adiciona DesabilitarPaginacao=true pois o JSON de exemplo tem a mesma estrutura (itens, totalizador)
        url_receber = "https://api.flow2.com.br/v1/recebers?DesabilitarPaginacao=true"
        response = requests.get(url_receber, headers=headers)
        response.raise_for_status() # Lança erro para 4xx/5xx

        # --- CORREÇÃO (Erro "Expecting value...") ---
        # Se a resposta for vazia, o .json() falha.
        if not response.text:
            return pd.DataFrame() # Retorna um DataFrame vazio
            
        data = response.json()
        
        # Normaliza a partir da chave 'itens', como no JSON de exemplo
        df_receber = pd.json_normalize(data, record_path=['itens'])
        return df_receber

    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao carregar dados da API de Contas a Receber: {e}")
        return None
    except requests.exceptions.JSONDecodeError as e:
        st.error(f"Erro ao decodificar JSON da API de Contas a Receber: {e}.")
        return None
    except Exception as e:
        st.error(f"Erro inesperado ao carregar Contas a Receber: {e}")
        return None

# --- Início da Interface ---

st.title("CONTROLE FINANCEIRO | Departamento Financeiro")

# Carrega o token da API
try:
    api_token = st.secrets["FLOW_API_TOKEN"]
except KeyError:
    st.error("Token da API (FLOW_API_TOKEN) não encontrado. Por favor, configure seu arquivo secrets.toml.")
    st.stop()

# --- CRIAÇÃO DAS ABAS ---
tab1, tab2 = st.tabs(["🏦 Controle Bancário", "🧾 Contas a Receber"])

# --- ABA 1: CONTROLE BANCÁRIO ---
with tab1:
    # Carrega os dados para esta aba
    df_movimentos, df_saldos = load_data(api_token)

    if df_movimentos is None or df_saldos is None:
        st.error("Falha ao carregar dados. Verifique a API e o Token.")
        st.stop() # Usamos st.stop() para parar a execução apenas desta aba

    st.subheader("Filtros")
    col1, col2 = st.columns([1, 2])

    with col1:
        min_date = df_movimentos['Data'].min()
        max_date = df_movimentos['Data'].max()
        date_range = st.date_input(
            "Período", [min_date, max_date],
            min_value=min_date, max_value=max_date, format="DD/MM/YYYY"
        )
        
        if len(date_range) == 2:
            start_date_filter = date_range[0]
            end_date_filter = date_range[1]
        else:
            start_date_filter = min_date
            end_date_filter = max_date

    with col2:
        all_banks_mov = df_movimentos['Banco'].unique()
        all_banks_saldos = df_saldos['Banco'].unique()
        all_banks = sorted(list(set(list(all_banks_mov) + list(all_banks_saldos))))
        selected_banks = st.multiselect(
            "Banco(s)", options=all_banks, default=all_banks
        )

    # Aplicação dos Filtros
    df_mov_filtered = df_movimentos[
        (df_movimentos['Data'] >= start_date_filter) &
        (df_movimentos['Data'] <= end_date_filter) &
        (df_movimentos['Banco'].isin(selected_banks))
    ]
    df_saldos_filtered = df_saldos[
        df_saldos['Banco'].isin(selected_banks)
    ]

    # KPIs (Métricas)
    st.divider()
    total_entradas = df_mov_filtered[~df_mov_filtered['Operacao'].str.contains('-')]['Valor'].sum()
    total_saidas = df_mov_filtered[df_mov_filtered['Operacao'].str.contains('-')]['Valor'].sum()
    saldo_atual = total_entradas - total_saidas

    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Total de entradas", format_brl(total_entradas))
    kpi2.metric("Total de saídas", format_brl(total_saidas), 
                 delta=format_brl(-total_saidas), delta_color="inverse")
    kpi3.metric("Saldo atual", format_brl(saldo_atual))

    # Tabelas (Visuais)
    st.divider()
    table1, table2 = st.columns([2, 1])

    with table1:
        st.subheader("Extratos Bancários")
        df_extratos = df_mov_filtered.copy()
        
        df_extratos['Total Entradas'] = df_extratos.apply(
            lambda row: row['Valor'] if '-' not in row['Operacao'] else 0, axis=1
        )
        df_extratos['Total Saídas'] = df_extratos.apply(
            lambda row: row['Valor'] if '-' in row['Operacao'] else 0, axis=1
        )
        
        df_display = df_extratos.groupby(['Data', 'Descricao']).agg({
            'Total Entradas': 'sum', 'Total Saídas': 'sum'
        }).reset_index()
        
        df_display = df_display[(df_display['Total Entradas'] != 0) | (df_display['Total Saídas'] != 0)]
        df_display = df_display.sort_values(by='Data', ascending=False)

        df_display_formatted = df_display.copy()
        df_display_formatted['Data'] = pd.to_datetime(df_display_formatted['Data']).dt.strftime('%d/%m/%Y')
        df_display_formatted['Total Entradas'] = df_display_formatted['Total Entradas'].apply(
            lambda x: format_brl(x) if x > 0 else ""
        )
        df_display_formatted['Total Saídas'] = df_display_formatted['Total Saídas'].apply(
            lambda x: f"<span style='color:red; font-weight:bold;'>{format_brl(x)}</span>" if x > 0 else ""
        )
        df_display_formatted = df_display_formatted.rename(columns={'Descricao': 'Descrição'})
        
        # Converte para HTML
        html_table = df_display_formatted[['Data', 'Descrição', 'Total Entradas', 'Total Saídas']].to_html(
            escape=False, index=False, border=0, classes="extratos-table"
        )
        
        # --- APLICAÇÃO DA BARRA DE ROLAGEM ---
        # Envolve a tabela HTML no 'div' com rolagem
        st.markdown(f'<div class="table-container">{html_table}</div>', unsafe_allow_html=True)

    with table2:
        st.subheader("Saldo de todas as contas")
        df_saldos_display = df_saldos_filtered.copy().sort_values(by='Banco')
        
        total_saldo_contas = df_saldos_display['Saldo dos bancos'].sum()
        total_row = pd.DataFrame([{'Banco': 'Total', 'Saldo dos bancos': total_saldo_contas}])
        df_saldos_display = pd.concat([df_saldos_display, total_row], ignore_index=True)

        df_saldos_display['Saldo dos bancos'] = df_saldos_display['Saldo dos bancos'].apply(
            lambda x: format_brl(x)
        )

        st.dataframe(
            df_saldos_display,
            use_container_width=True,
            hide_index=True,
            height=400 # O st.dataframe já tem barra de rolagem nativa com 'height'
        )

# --- ABA 2: CONTAS A RECEBER (FUNCIONAL) ---
with tab2:
    # Carrega os dados para esta aba
    df_receber = load_receber(api_token)
    
    if df_receber is None:
        st.error("Falha ao carregar dados de Contas a Receber. Verifique a API e o Token.")
        st.stop() # Para a execução desta aba

    if df_receber.empty:
        st.info("Nenhum item de Contas a Receber encontrado.")
        st.stop()

    try:
        # --- Transformação dos Dados (Baseado no JSON de exemplo) ---
        hoje = pd.Timestamp.now().date()
        
        # Converte colunas de data (ignorando erros se já forem nulas)
        df_receber['dataVencimentoReal'] = pd.to_datetime(df_receber['dataVencimentoReal'], errors='coerce').dt.date
        df_receber['dataBaixa'] = pd.to_datetime(df_receber['dataBaixa'], errors='coerce').dt.date
        
        # Função para definir o status
        def get_status(row):
            # O novo JSON tem a coluna 'situacao', mas podemos usar a dataBaixa para ser mais seguro
            if pd.notna(row['dataBaixa']):
                return "Recebido"
            if pd.isna(row['dataVencimentoReal']):
                return "Sem Vencimento"
            if row['dataVencimentoReal'] < hoje:
                return "Vencido"
            if row['dataVencimentoReal'] == hoje:
                return "Vence Hoje"
            return "A Receber"

        df_receber['Status'] = df_receber.apply(get_status, axis=1)
        
        # --- ATUALIZAÇÃO: Usa 'valorParcela' como a coluna de valor principal
        df_receber['Valor'] = pd.to_numeric(df_receber['valorParcela'])
        df_receber['Cliente'] = df_receber['cliente.nomeRazaoSocial']

        # --- KPIs (Métricas) ---
        st.divider()
        total_a_receber = df_receber[df_receber['Status'].isin(['A Receber', 'Vence Hoje'])]['Valor'].sum()
        total_vencido = df_receber[df_receber['Status'] == 'Vencido']['Valor'].sum()
        
        mes_atual = hoje.month
        ano_atual = hoje.year
        recebido_mes = df_receber[
            (df_receber['Status'] == 'Recebido') &
            (df_receber['dataBaixa'].apply(lambda x: x.month == mes_atual if pd.notna(x) else False)) &
            (df_receber['dataBaixa'].apply(lambda x: x.year == ano_atual if pd.notna(x) else False))
        ]['Valor'].sum()

        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Total a Receber (e Vence Hoje)", format_brl(total_a_receber))
        kpi2.metric("Total Vencido (não recebido)", format_brl(total_vencido), delta_color="inverse")
        kpi3.metric("Total Recebido (Este Mês)", format_brl(recebido_mes))

        # --- Filtros ---
        st.divider()
        st.subheader("Filtros de Contas a Receber")
        
        col_f1, col_f2 = st.columns(2)
        
        with col_f1:
            status_options = sorted(df_receber['Status'].unique())
            selected_status = st.multiselect(
                "Status",
                options=status_options,
                default=status_options
            )
        
        with col_f2:
            # Lida com datas de vencimento que podem ser nulas (NaT)
            min_venc = df_receber['dataVencimentoReal'].min()
            max_venc = df_receber['dataVencimentoReal'].max()
            
            if pd.isna(min_venc):
                min_venc = hoje
            if pd.isna(max_venc):
                max_venc = hoje
                
            venc_date_range = st.date_input(
                "Período de Vencimento",
                [min_venc, max_venc],
                min_value=min_venc,
                max_value=max_venc,
                format="DD/MM/YYYY"
            )

        # --- Aplicação dos Filtros ---
        if len(venc_date_range) == 2:
            start_venc_filter = venc_date_range[0]
            end_venc_filter = venc_date_range[1]
        else:
            start_venc_filter = min_venc
            end_venc_filter = max_venc

        # Filtra o dataframe
        # Lida com NaT (datas nulas) não sendo filtradas corretamente
        df_receber_filtered = df_receber[
            (df_receber['Status'].isin(selected_status)) &
            (df_receber['dataVencimentoReal'] >= start_venc_filter) &
            (df_receber['dataVencimentoReal'] <= end_venc_filter)
        ]

        # --- Tabela de Contas a Receber ---
        st.subheader("Detalhe de Contas a Receber")
        
        df_receber_display = df_receber_filtered.copy()
        
        # Formatação para exibição
        df_receber_display['Valor'] = df_receber_display['Valor'].apply(format_brl)
        df_receber_display['Vencimento'] = pd.to_datetime(df_receber_display['dataVencimentoReal']).dt.strftime('%d/%m/%Y')
        df_receber_display['Recebido em'] = pd.to_datetime(df_receber_display['dataBaixa']).dt.strftime('%d/%m/%Y')
        
        df_receber_display['Vencimento'] = df_receber_display['Vencimento'].replace('NaT', '')
        df_receber_display['Recebido em'] = df_receber_display['Recebido em'].replace('NaT', '')

        st.dataframe(
            df_receber_display[[
                'Status', 'Vencimento', 'Cliente', 'Valor', 'Recebido em', 'numero', 'parcela'
            ]],
            use_container_width=True,
            hide_index=True,
            height=500
        )

    except Exception as e:
        st.error(f"Erro ao processar e exibir os dados de Contas a Receber: {e}")
        st.info("Verifique se a API retornou dados.")
