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
def load_boletos(api_token):
    """
    Carrega dados da API de boletos (Aba 2).
    """
    try:
        headers = {"Authorization": f"Bearer {api_token}"}
        url_boletos = "https://api.flow2.com.br/v1/boletos?IdsReceber=0"
        response = requests.get(url_boletos, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data

    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao carregar dados da API de Boletos: {e}")
        return None
    except Exception as e:
        st.error(f"Erro ao processar os dados de Boletos: {e}")
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
tab1, tab2 = st.tabs(["🏦 Controle Bancário", "🧾 Boletos (em breve)"])

# --- ABA 1: CONTROLE BANCÁRIO ---
with tab1:
    # Carrega os dados para esta aba
    df_movimentos, df_saldos = load_data(api_token)

    if df_movimentos is None or df_saldos is None:
        st.error("Falha ao carregar dados. Verifique a API e o Token.")
        st.stop()

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

# --- ABA 2: CONTROLE DE BOLETOS ---
with tab2:
    st.warning("Página em Construção!")
    
    # Carrega os dados para esta aba
    data_boletos = load_boletos(api_token)
    
    if data_boletos is None:
        st.error("Falha ao carregar dados dos boletos. Verifique a API e o Token.")
        st.stop()

    st.info("Para que eu possa construir os filtros (Vencido, A Vencer, etc.), preciso saber os nomes das colunas. Por favor, olhe os dados abaixo e me diga quais colunas correspondem a: \n 1. Data de Vencimento \n 2. Valor do Boleto \n 3. Status (ex: 'ABERTO', 'PAGO')")

    st.subheader("Dados Brutos da API (para depuração)")
    st.json(data_boletos)

    st.subheader("DataFrame Normalizado (Tentativa)")
    st.info("Estou assumindo que os dados estão em uma chave 'itens', como na API de movimentos. Se a tabela abaixo estiver vazia ou errada, os dados brutos acima nos ajudarão a corrigir.")

    try:
        # Tenta normalizar com 'itens' (comum em APIs paginadas)
        df_boletos = pd.json_normalize(data_boletos, record_path=['itens'])
        st.dataframe(df_boletos, use_container_width=True)
    except Exception as e:
        st.warning(f"Falha ao normalizar com 'itens': {e}")
        st.info("Tentando normalizar a raiz do JSON (se não for paginado)...")
        try:
            # Tenta normalizar a raiz (se a API retornar uma lista simples de objetos)
            df_boletos_root = pd.json_normalize(data_boletos)
            st.dataframe(df_boletos_root, use_container_width=True)
        except Exception as e2:
            st.error(f"Falha ao normalizar a raiz também: {e2}")
