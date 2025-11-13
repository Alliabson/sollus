import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date

# Define a configuração da página
# layout="wide" usa a tela inteira, como no seu BI desktop.
# ISSO DEVE SER O PRIMEIRO COMANDO STREAMLIT
st.set_page_config(layout="wide", page_title="Aplicação Financeira")

# --- Funções Helper ---

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

def get_status(row):
    """
    Calcula o status de um título (A Receber, Recebido, Vencido).
    """
    # Se 'dataBaixa' (data de pagamento) existe, está Recebido.
    # Usando 'dataCredito' como fallback, conforme mapeamento
    if pd.notna(row['dataBaixa']) or pd.notna(row['dataCredito']):
        return "Recebido"
    
    # Se não foi pago, verifica o vencimento
    today = pd.to_datetime(date.today())
    vencimento = pd.to_datetime(row['dataVencimentoReal'])
    
    if pd.isna(vencimento):
        return "A Receber" # Sem data de vencimento
        
    if vencimento < today:
        return "Vencido"
    else:
        return "A Receber"

# --- Estilização CSS Customizada ---
# Injeta CSS para replicar a aparência verde do seu Power BI
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
        background-color: #4CAF50; /* Verde */
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

    /* Títulos dos sub-cabeçalhos (Filtros, Extratos, Saldo) */
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

    /* Estilos para a tabela de extratos HTML (com barra de rolagem) */
    .extratos-table-container {
        height: 400px; /* Altura fixa para barra de rolagem */
        overflow-y: auto; /* Adiciona barra de rolagem vertical */
        border: 1px solid #E0E0E0;
        border-radius: 5px;
    }
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
        position: sticky; /* Faz o cabeçalho "grudar" no topo */
        top: 0;
    }
    .extratos-table td {
        padding: 8px;
        border-bottom: 1px solid #DDDDDD; /* Linha cinza entre-linhas */
        vertical-align: top;
    }
    .extratos-table tr:last-child td {
        border-bottom: none;
    }

    /* Remove o espaço extra no topo da página */
    .block-container {
        padding-top: 2rem;
    }

    /* Oculta o "Made with Streamlit" */
    footer {visibility: hidden;}
    
    /* Garante que o menu (hamburguer) está visível */
    #MainMenu {visibility: visible;}

</style>
""", unsafe_allow_html=True)

# --- Carregamento de Dados (Cache) ---

@st.cache_data(ttl=600) # Cache de 10 minutos
def load_movimentos_e_saldos(api_token):
    """
    Carrega dados das APIs de movimentos e saldos.
    """
    try:
        headers = {"Authorization": f"Bearer {api_token}"}
        
        # 1. Carregar Movimentos Bancários (fMovimentos)
        url_movimentos = "https://api.flow2.com.br/v1/movimentosBancarios?DesabilitarPaginacao=true&DataMovimentoMaiorOuIgualA=2025-01-01"
        response_mov = requests.get(url_movimentos, headers=headers)
        response_mov.raise_for_status()
        data_mov = response_mov.json()
        
        if 'itens' in data_mov and data_mov['itens']:
            df_movimentos = pd.json_normalize(data_mov, record_path=['itens'])
        else:
            # Retorna um DataFrame vazio se não houver 'itens'
            st.warning("API de Movimentos não retornou 'itens'.")
            cols_mov = ['Data', 'Horario', 'Descricao', 'Valor', 'Operacao', 'Banco']
            df_movimentos = pd.DataFrame(columns=cols_mov)
            
        # Renomeia colunas
        df_movimentos = df_movimentos.rename(columns={
            "valor": "Valor",
            "dataMovimento": "DataMovimento",
            "descricao": "Descricao",
            "operacao": "Operacao",
            "nomeBanco": "Banco"
        })
        
        # Garante que 'Operacao' é string
        if 'Operacao' in df_movimentos.columns:
            df_movimentos['Operacao'] = df_movimentos['Operacao'].astype(str)
        
        # Transformações de tipo e coluna
        df_movimentos['Valor'] = pd.to_numeric(df_movimentos.get('Valor', 0))
        df_movimentos['DataMovimento'] = pd.to_datetime(df_movimentos.get('DataMovimento', None))
        
        if 'DataMovimento' in df_movimentos:
            df_movimentos['Data'] = df_movimentos['DataMovimento'].dt.date
            df_movimentos['Horario'] = df_movimentos['DataMovimento'].dt.time
        else:
            df_movimentos['Data'] = pd.NaT
            df_movimentos['Horario'] = pd.NaT

        df_movimentos['Descricao'] = df_movimentos.get('Descricao', '').astype(str).str.upper()

        # 2. Carregar Saldo dos Bancos (fSaldoBancos)
        url_saldos = "https://api.flow2.com.br/v1/saldoBancos"
        response_saldos = requests.get(url_saldos, headers=headers)
        response_saldos.raise_for_status()
        data_saldos = response_saldos.json()
        
        if data_saldos:
            df_saldos = pd.json_normalize(data_saldos)
        else:
            st.warning("API de Saldos não retornou dados.")
            cols_saldos = ['Banco', 'Saldo dos bancos']
            df_saldos = pd.DataFrame(columns=cols_saldos)

        # Renomeia colunas
        df_saldos = df_saldos.rename(columns={
            "banco.nome": "Banco",
            "saldo": "Saldo dos bancos"
        })
        
        df_saldos['Saldo dos bancos'] = pd.to_numeric(df_saldos.get('Saldo dos bancos', 0))
        
        # Garante que as colunas principais existem
        df_movimentos = df_movimentos.reindex(columns=['Data', 'Horario', 'Descricao', 'Valor', 'Operacao', 'Banco'])
        df_saldos = df_saldos.reindex(columns=['Banco', 'Saldo dos bancos'])

        return df_movimentos, df_saldos

    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao carregar dados da API (Mov/Saldos): {e}")
        return None, None
    except Exception as e:
        st.error(f"Erro ao processar os dados (Mov/Saldos): {e}")
        return None, None

@st.cache_data(ttl=600) # Cache de 10 minutos
def load_receber_e_clientes(api_token):
    """
    Carrega dados das APIs de Contas a Receber (/recebers) e Clientes.
    """
    try:
        headers = {"Authorization": f"Bearer {api_token}"}
        
        # 1. Carregar Contas a Receber (/v1/recebers)
        url_receber = "https://api.flow2.com.br/v1/recebers?DesabilitarPaginacao=true"
        response_receber = requests.get(url_receber, headers=headers)
        response_receber.raise_for_status()
        
        # CORREÇÃO (Erro "Expecting value"): Verifica se a resposta não está vazia
        try:
            data_receber = response_receber.json()
        except requests.exceptions.JSONDecodeError:
            st.warning("A API de Contas a Receber (/recebers) retornou uma resposta vazia.")
            data_receber = {} # Define como dicionário vazio para não falhar

        # Normaliza os 'itens' (títulos)
        if 'itens' in data_receber and data_receber['itens']:
            df_receber = pd.json_normalize(data_receber, record_path=['itens'])
        else:
            # Retorna um DataFrame vazio se não houver 'itens'
            st.warning("API de Contas a Receber não retornou 'itens'.")
            df_receber = pd.DataFrame() # DataFrame vazio

        # 2. Carregar Clientes (/v1/clientes)
        url_clientes = "https://api.flow2.com.br/v1/clientes?DesabilitarPaginacao=true"
        response_clientes = requests.get(url_clientes, headers=headers)
        response_clientes.raise_for_status()
        
        try:
            data_clientes = response_clientes.json()
        except requests.exceptions.JSONDecodeError:
            st.warning("A API de Clientes retornou uma resposta vazia.")
            data_clientes = {}

        # Normaliza os 'itens' (clientes)
        if 'itens' in data_clientes and data_clientes['itens']:
            df_clientes = pd.json_normalize(data_clientes, record_path=['itens'])
            # Renomeia colunas para o 'merge'
            df_clientes = df_clientes.rename(columns={
                "id": "idCliente", 
                "nomeRazaoSocial": "Cliente"
            })
            df_clientes = df_clientes[['idCliente', 'Cliente']] # Seleciona só o necessário
        else:
            st.warning("API de Clientes não retornou 'itens'.")
            df_clientes = pd.DataFrame(columns=['idCliente', 'Cliente']) # DataFrame vazio

        # 3. Juntar as tabelas (Merge/VLOOKUP)
        if not df_receber.empty:
            if 'idCliente' not in df_receber.columns:
                 df_receber['idCliente'] = pd.NA
                 
            if not df_clientes.empty:
                df_final = pd.merge(
                    df_receber,
                    df_clientes,
                    on="idCliente",
                    how="left" # Mantém todos os títulos, mesmo sem cliente correspondente
                )
            else:
                df_final = df_receber
            
            # Preenche clientes nulos
            if 'Cliente' not in df_final.columns:
                df_final['Cliente'] = "Cliente não informado"
            
            df_final['Cliente'] = df_final['Cliente'].fillna("Cliente não informado")
        else:
            df_final = df_receber
            if 'Cliente' not in df_final.columns:
                 df_final['Cliente'] = "Cliente não informado"

        return df_final

    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao carregar dados da API (Receber/Clientes): {e}")
        return None
    except Exception as e:
        st.error(f"Erro ao processar os dados (Receber/Clientes): {e}")
        return None

# --- Início da Interface ---

st.title("APLICAÇÃO FINANCEIRA")

# Carrega o token da API a partir dos "secrets" do Streamlit
try:
    api_token = st.secrets["FLOW_API_TOKEN"]
except KeyError:
    st.error("Token da API (FLOW_API_TOKEN) não encontrado. Por favor, configure seu arquivo secrets.toml.")
    st.stop()

# Cria as Abas principais
tab_bancario, tab_receber = st.tabs(["🏦 Controle Bancário", "🧾 Contas a Receber"])


# --- ABA 1: CONTROLE BANCÁRIO ---
with tab_bancario:
    
    # Carrega os dados
    df_movimentos, df_saldos = load_movimentos_e_saldos(api_token)

    # Se o carregamento falhar, para a execução desta aba
    if df_movimentos is None or df_saldos is None:
        st.error("Falha ao carregar dados bancários. Verifique a API e o Token.")
    else:
        st.subheader("Filtros")
        col1_cb, col2_cb = st.columns([1, 2])

        with col1_cb:
            # Filtro de Período (dCalendario)
            min_date_mov = df_movimentos['Data'].min()
            max_date_mov = df_movimentos['Data'].max()
            
            # Fallback se não houver datas
            if pd.isna(min_date_mov): min_date_mov = date.today()
            if pd.isna(max_date_mov): max_date_mov = date.today()

            date_range_mov = st.date_input(
                "Período",
                [min_date_mov, max_date_mov],
                min_value=min_date_mov,
                max_value=max_date_mov,
                format="DD/MM/YYYY",
                key="date_range_mov" # Chave única para este filtro
            )
            
            start_date_filter_mov, end_date_filter_mov = min_date_mov, max_date_mov
            if len(date_range_mov) == 2:
                start_date_filter_mov = date_range_mov[0]
                end_date_filter_mov = date_range_mov[1]

        with col2_cb:
            # Filtro de Banco(s)
            all_banks_mov = df_movimentos['Banco'].dropna().unique()
            all_banks_saldos = df_saldos['Banco'].dropna().unique()
            all_banks = sorted(list(set(list(all_banks_mov) + list(all_banks_saldos))))
            
            selected_banks = st.multiselect(
                "Banco(s)",
                options=all_banks,
                default=all_banks,
                key="selected_banks"
            )

        # --- Aplicação dos Filtros (Controle Bancário) ---
        
        # Garante que as datas de filtro não são NaT
        if pd.isna(start_date_filter_mov): start_date_filter_mov = min_date_mov
        if pd.isna(end_date_filter_mov): end_date_filter_mov = max_date_mov
            
        df_mov_filtered = df_movimentos[
            (df_movimentos['Data'] >= start_date_filter_mov) &
            (df_movimentos['Data'] <= end_date_filter_mov) &
            (df_movimentos['Banco'].isin(selected_banks))
        ]
        
        df_saldos_filtered = df_saldos[
            df_saldos['Banco'].isin(selected_banks)
        ]

        # --- KPIs (Métricas) ---
        st.divider()

        total_entradas = df_mov_filtered[~df_mov_filtered['Operacao'].astype(str).str.contains('-')]['Valor'].sum()
        total_saidas = df_mov_filtered[df_mov_filtered['Operacao'].astype(str).str.contains('-')]['Valor'].sum()
        saldo_atual = total_entradas - total_saidas

        kpi1_cb, kpi2_cb, kpi3_cb = st.columns(3)
        kpi1_cb.metric("Total de entradas", format_brl(total_entradas))
        kpi2_cb.metric("Total de saídas", format_brl(total_saidas), 
                         delta=format_brl(-total_saidas), delta_color="inverse")
        kpi3_cb.metric("Saldo atual", format_brl(saldo_atual))

        # --- Tabelas (Visuais) ---
        st.divider()
        table1_cb, table2_cb = st.columns([2, 1])

        with table1_cb:
            st.subheader("Extratos Bancários")
            
            df_extratos = df_mov_filtered.copy()
            
            df_extratos['Total Entradas'] = df_extratos.apply(
                lambda row: row['Valor'] if '-' not in str(row['Operacao']) else 0,
                axis=1
            )
            df_extratos['Total Saídas'] = df_extratos.apply(
                lambda row: row['Valor'] if '-' in str(row['Operacao']) else 0,
                axis=1
            )
            
            # Garante que 'Descricao' existe antes de agrupar
            if 'Descricao' not in df_extratos.columns:
                df_extratos['Descricao'] = "N/A"
                
            df_display = df_extratos.groupby(
                ['Data', 'Descricao']
            ).agg({
                'Total Entradas': 'sum',
                'Total Saídas': 'sum'
            }).reset_index()
            
            df_display = df_display[(df_display['Total Entradas'] != 0) | (df_display['Total Saídas'] != 0)]
            df_display = df_display.sort_values(by='Data', ascending=False)

            # Formatação para exibição
            df_display_formatted = df_display.copy()
            df_display_formatted['Data'] = pd.to_datetime(df_display_formatted['Data']).dt.strftime('%d/%m/%Y')
            df_display_formatted['Total Entradas'] = df_display_formatted['Total Entradas'].apply(
                lambda x: format_brl(x) if x > 0 else ""
            )
            df_display_formatted['Total Saídas'] = df_display_formatted['Total Saídas'].apply(
                lambda x: f"<span style='color:red; font-weight:bold;'>{format_brl(x)}</span>" if x > 0 else ""
            )

            df_display_formatted = df_display_formatted.rename(columns={'Descricao': 'Descrição'})
            
            # --- CORREÇÃO (Barra de Rolagem): Usa o container HTML ---
            html_table = df_display_formatted[['Data', 'Descrição', 'Total Entradas', 'Total Saídas']].to_html(
                escape=False, 
                index=False, 
                border=0,
                classes="extratos-table"
            )
            # Envolve a tabela no container com altura fixa
            st.markdown(f'<div class="extratos-table-container">{html_table}</div>', unsafe_allow_html=True)

        with table2_cb:
            st.subheader("Saldo de todas as contas")
            
            df_saldos_display = df_saldos_filtered.copy().sort_values(by='Banco')
            
            total_saldo_contas = df_saldos_display['Saldo dos bancos'].sum()
            total_row = pd.DataFrame([{'Banco': 'Total', 'Saldo dos bancos': total_saldo_contas}])
            df_saldos_display = pd.concat([df_saldos_display, total_row], ignore_index=True)

            df_saldos_display['Saldo dos bancos'] = df_saldos_display['Saldo dos bancos'].apply(format_brl)

            st.dataframe(
                df_saldos_display,
                use_container_width=True,
                hide_index=True,
                height=400 # Mesma altura da outra tabela
            )


# --- ABA 2: CONTAS A RECEBER ---
with tab_receber:
    
    # Carrega os dados
    df_receber_raw = load_receber_e_clientes(api_token)

    if df_receber_raw is None or df_receber_raw.empty:
        st.error("Falha ao carregar dados de Contas a Receber. Verifique a API e o Token.")
    else:
        try:
            # --- Preparação e Limpeza de Dados (Contas a Receber) ---
            df_receber = df_receber_raw.copy()
            
            # Mapeamento de colunas (conforme sua lista)
            # .get() previne KeyError se a coluna não existir
            df_receber['dataVencimentoReal'] = pd.to_datetime(df_receber.get('dataVencimentoReal', None), errors='coerce')
            df_receber['dataBaixa'] = pd.to_datetime(df_receber.get('dataBaixa', None), errors='coerce')
            df_receber['dataCredito'] = pd.to_datetime(df_receber.get('dataCredito', None), errors='coerce')
            df_receber['situacao'] = df_receber.get('situacao', 'Indefinido')
            
            # --- CORREÇÃO (abs()): Aplica abs() na criação da coluna 'Valor' ---
            # Isso garante que todos os valores (para KPIs e tabelas) sejam positivos
            df_receber['Valor'] = pd.to_numeric(df_receber.get('valorAReceberParcela', 0), errors='coerce').fillna(0).abs()
            
            # --- ADICIONADO: Coluna "Código do Projeto" ---
            df_receber['Codigo Projeto'] = df_receber.get('codigoProjeto', 'N/A').fillna('N/A')

            # Colunas de data para filtro (apenas data, sem hora)
            df_receber['Vencimento'] = df_receber['dataVencimentoReal'].dt.date
            df_receber['Recebido em'] = df_receber['dataBaixa'].dt.date # Usando 'dataBaixa' (pagamento)
            
            # Coluna de Status (Vencido, A Receber, Recebido)
            df_receber['Status'] = df_receber.apply(get_status, axis=1)
            
            # --- Fim da Preparação ---

            # --- Filtros (Contas a Receber) ---
            st.subheader("Filtros de Contas a Receber")
            col1_cr, col2_cr = st.columns([1, 1])

            with col1_cr:
                # Filtro de Status
                status_options = sorted(df_receber['Status'].unique())
                selected_status = st.multiselect(
                    "Status (Calculado)",
                    options=status_options,
                    default=status_options, # Começa com todos selecionados
                    key="selected_status"
                )

            with col2_cr:
                # Filtro de Período de Vencimento
                min_date_cr = df_receber['Vencimento'].min()
                max_date_cr = df_receber['Vencimento'].max()

                # Fallback se não houver datas
                if pd.isna(min_date_cr): min_date_cr = date.today()
                if pd.isna(max_date_cr): max_date_cr = date.today()

                date_range_cr = st.date_input(
                    "Período de Vencimento",
                    [min_date_cr, max_date_cr],
                    min_value=min_date_cr,
                    max_value=max_date_cr,
                    format="DD/MM/YYYY",
                    key="date_range_cr"
                )
                
                start_date_filter_cr, end_date_filter_cr = min_date_cr, max_date_cr
                if len(date_range_cr) == 2:
                    start_date_filter_cr = date_range_cr[0]
                    end_date_filter_cr = date_range_cr[1]

            # --- Aplicação dos Filtros ---
            
            # CORREÇÃO DA LÓGICA DE FILTRO:
            
            # 1. KPIs (Cartões) são filtrados APENAS por Data
            # (Ignora o filtro de 'Status' para os KPIs)
            
            # Converte as datas de filtro para datetime.date (se não forem)
            if isinstance(start_date_filter_cr, datetime):
                start_date_filter_cr = start_date_filter_cr.date()
            if isinstance(end_date_filter_cr, datetime):
                end_date_filter_cr = end_date_filter_cr.date()

            # Cria um DataFrame base para os KPIs
            # Trata o caso de 'Vencimento' ser NaT (não pode ser comparado)
            kpi_df = df_receber[
                (df_receber['Vencimento'].notna()) & # Ignora títulos sem data de vencimento
                (df_receber['Vencimento'] >= start_date_filter_cr) &
                (df_receber['Vencimento'] <= end_date_filter_cr)
            ].copy()
            
            # 2. Tabela é filtrada por Data E Status
            df_receber_filtered = kpi_df[
                kpi_df['Status'].isin(selected_status)
            ].copy()

            # --- KPIs (Contas a Receber) ---
            st.divider()

            # Calcula KPIs a partir do kpi_df (filtrado por data)
            # --- CORREÇÃO (abs()): Remove o abs() da SOMA (já foi aplicado nos dados) ---
            total_a_receber = kpi_df[kpi_df['Status'] != 'Recebido']['Valor'].sum()
            total_vencido = kpi_df[kpi_df['Status'] == 'Vencido']['Valor'].sum()
            
            # KPI "Recebido no Mês" (Este MÊS) - Ignora todos os filtros
            today = date.today()
            df_recebido_mes = df_receber[
                (df_receber['Recebido em'].notna()) &
                (df_receber['Recebido em'] >= date(today.year, today.month, 1)) &
                (df_receber['Recebido em'] <= today)
            ]
            # --- CORREÇÃO (abs()): Remove o abs() da SOMA (já foi aplicado nos dados) ---
            total_recebido_mes = df_recebido_mes['Valor'].sum()

            kpi1_cr, kpi2_cr, kpi3_cr = st.columns(3)
            kpi1_cr.metric("Total a Receber (no período)", format_brl(total_a_receber))
            kpi2_cr.metric("Total Vencido (no período)", format_brl(total_vencido))
            kpi3_cr.metric("Total Recebido (Este Mês)", format_brl(total_recebido_mes))

            # --- Tabela (Contas a Receber) ---
            st.subheader("Detalhe de Contas a Receber")
            
            df_receber_display = df_receber_filtered.copy()
            
            # Formatação para exibição
            # A coluna 'Valor' agora será sempre positiva, corrigindo o print
            df_receber_display['Valor Parcela'] = df_receber_display['Valor'].apply(format_brl)
            
            # Formata as colunas de data (que são objetos 'date', não 'datetime')
            df_receber_display['Vencimento'] = df_receber_display['Vencimento'].apply(
                lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else ''
            )
            df_receber_display['Recebido em'] = df_receber_display['Recebido em'].apply(
                lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else ''
            )

            st.dataframe(
                df_receber_display[[
                    'Cliente',
                    'Codigo Projeto', # <-- COLUNA ADICIONADA
                    'Vencimento',
                    'Recebido em',
                    'Status',
                    'Valor Parcela'
                ]],
                use_container_width=True,
                hide_index=True,
                height=400
            )

            # --- Dados Brutos (Para Depuração) ---
            with st.expander("Dados Brutos (Primeiros 5)"):
                st.dataframe(df_receber_raw.head(5))

        except Exception as e:
            st.error(f"Erro ao processar e exibir os dados de Contas a Receber: {e}")
            st.info("Verifique se a API retornou dados e se os nomes das colunas estão corretos.")
            st.dataframe(df_receber_raw.head(5)) # Mostra dados brutos no erro
