import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# Define a configuração da página
# layout="wide" usa a tela inteira, como no seu BI desktop.
st.set_page_config(layout="wide", page_title="Controle Bancário")

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
    }
    
    /* Cabeçalho das tabelas (DataFrames) */
    .stDataFrame th {
        background-color: #E8F5E9; /* Verde claro */
        font-size: 1.1em;
        font-weight: bold;
        color: #333333;
    }

    /* --- INÍCIO DA CORREÇÃO 1: Restaurar CSS da Tabela HTML --- */
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
    }
    .extratos-table td {
        padding: 8px;
        border-bottom: 1px solid #DDDDDD; /* Linha cinza entre-linhas */
        vertical-align: top;
    }
    /* Remove a borda da última linha */
    .extratos-table tr:last-child td {
        border-bottom: none;
    }
    /* --- FIM DA CORREÇÃO 1 --- */

    /* Remove o espaço extra no topo da página */
    .block-container {
        padding-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# --- Carregamento de Dados ---
# @st.cache_data armazena o resultado da função, evitando recarregar da API
# a cada interação do usuário.
@st.cache_data(ttl=600) # Cache de 10 minutos
def load_data(api_token):
    """
    Carrega dados das APIs de movimentos e saldos.
    """
    try:
        # 1. Headers de autenticação
        headers = {"Authorization": f"Bearer {api_token}"}
        
        # 2. Carregar Movimentos Bancários (fMovimentos)
        # Usamos a data de início da sua consulta M
        url_movimentos = "https://api.flow2.com.br/v1/movimentosBancarios?DesabilitarPaginacao=true&DataMovimentoMaiorOuIgualA=2025-01-01"
        response_mov = requests.get(url_movimentos, headers=headers)
        response_mov.raise_for_status() # Lança erro se a requisição falhar
        
        data_mov = response_mov.json()
        
        # Replicando a lógica do Power Query com Pandas
        df_movimentos = pd.json_normalize(data_mov, record_path=['itens'])
        
        # Renomeia colunas para facilitar (baseado na sua expansão)
        df_movimentos = df_movimentos.rename(columns={
            "valor": "Valor",
            "dataMovimento": "DataMovimento",
            "descricao": "Descricao",
            "operacao": "Operacao",
            "nomeBanco": "Banco"
        })
        
        # --- INÍCIO DA CORREÇÃO 2: Garantir que 'Operacao' é string ---
        # Garante que a coluna 'Operacao' seja do tipo string para o filtro .str.contains()
        if 'Operacao' in df_movimentos.columns:
            df_movimentos['Operacao'] = df_movimentos['Operacao'].astype(str)
        # --- FIM DA CORREÇÃO 2 ---
        
        # Transformações de tipo e coluna
        df_movimentos['Valor'] = pd.to_numeric(df_movimentos['Valor'])
        df_movimentos['DataMovimento'] = pd.to_datetime(df_movimentos['DataMovimento'])
        df_movimentos['Data'] = df_movimentos['DataMovimento'].dt.date
        df_movimentos['Horario'] = df_movimentos['DataMovimento'].dt.time
        df_movimentos['Descricao'] = df_movimentos['Descricao'].str.upper()
        
        # Seleciona colunas principais
        colunas_mov = ['Data', 'Horario', 'Descricao', 'Valor', 'Operacao', 'Banco']
        df_movimentos = df_movimentos[colunas_mov]

        # 3. Carregar Saldo dos Bancos (fSaldoBancos)
        url_saldos = "https://api.flow2.com.br/v1/saldoBancos"
        response_saldos = requests.get(url_saldos, headers=headers)
        response_saldos.raise_for_status()
        
        data_saldos = response_saldos.json()
        
        # Replicando a lógica do Power Query com Pandas
        # A consulta M usa Table.FromList, indicando uma lista de JSONs
        df_saldos = pd.json_normalize(data_saldos)
        
        # Renomeia colunas (baseado na sua expansão)
        df_saldos = df_saldos.rename(columns={
            "banco.nome": "Banco",
            "saldo": "Saldo dos bancos"
        })
        
        # Transformação de tipo
        df_saldos['Saldo dos bancos'] = pd.to_numeric(df_saldos['Saldo dos bancos'])
        
        # Seleciona colunas principais
        df_saldos = df_saldos[['Banco', 'Saldo dos bancos']]
        
        return df_movimentos, df_saldos

    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao carregar dados da API: {e}")
        return None, None
    except Exception as e:
        st.error(f"Erro ao processar os dados: {e}")
        return None, None

# --- Início da Interface ---

st.title("CONTROLE BANCÁRIO | Departamento Financeiro")

# Carrega o token da API a partir dos "secrets" do Streamlit
# Veja o arquivo secrets.toml.example
try:
    api_token = st.secrets["FLOW_API_TOKEN"]
except KeyError:
    st.error("Token da API (FLOW_API_TOKEN) não encontrado. Por favor, configure seu arquivo secrets.toml.")
    st.stop()

# Carrega os dados
df_movimentos, df_saldos = load_data(api_token)

# Se o carregamento falhar, para a execução
if df_movimentos is None or df_saldos is None:
    st.stop()

# --- Filtros (como no BI) ---
st.subheader("Filtros")
col1, col2 = st.columns([1, 2])

with col1:
    # Filtro de Período (dCalendario)
    # Lógica do DAX replicada: min e max da tabela de fatos
    min_date = df_movimentos['Data'].min()
    max_date = df_movimentos['Data'].max()
    
    date_range = st.date_input(
        "Período",
        [min_date, max_date],
        min_value=min_date,
        max_value=max_date,
        format="DD/MM/YYYY"
    )
    
    # Garante que temos um range válido
    if len(date_range) == 2:
        start_date_filter = date_range[0]
        end_date_filter = date_range[1]
    else:
        # Fallback caso o usuário limpe o campo
        start_date_filter = min_date
        end_date_filter = max_date

with col2:
    # Filtro de Banco(s)
    # Pega nomes de bancos de ambas as tabelas para garantir
    all_banks_mov = df_movimentos['Banco'].unique()
    all_banks_saldos = df_saldos['Banco'].unique()
    all_banks = sorted(list(set(list(all_banks_mov) + list(all_banks_saldos))))
    
    selected_banks = st.multiselect(
        "Banco(s)",
        options=all_banks,
        default=all_banks
    )

# --- Aplicação dos Filtros ---

# Filtra o DataFrame de movimentos
df_mov_filtered = df_movimentos[
    (df_movimentos['Data'] >= start_date_filter) &
    (df_movimentos['Data'] <= end_date_filter) &
    (df_movimentos['Banco'].isin(selected_banks))
]

# Filtra o DataFrame de saldos
# O filtro de data não se aplica aqui, assim como no BI
df_saldos_filtered = df_saldos[
    df_saldos['Banco'].isin(selected_banks)
]

# --- KPIs (Métricas) ---

st.divider()

# Replicando as medidas DAX de cálculo
# --- INÍCIO DA CORREÇÃO 3: Restaurar lógica de KPI (hífen) ---
total_entradas = df_mov_filtered[~df_mov_filtered['Operacao'].str.contains('-')]['Valor'].sum()
total_saidas = df_mov_filtered[df_mov_filtered['Operacao'].str.contains('-')]['Valor'].sum()
# --- FIM DA CORREÇÃO 3 ---
saldo_atual = total_entradas - total_saidas

# Exibe os KPIs em colunas
kpi1, kpi2, kpi3 = st.columns(3)
kpi1.metric("Total de entradas", f"R$ {total_entradas:,.2f}")
kpi2.metric("Total de saídas", f"R$ {total_saidas:,.2f}", 
             delta=f"R$ {-total_saidas:,.2f}", delta_color="inverse") # Opcional: delta negativo
kpi3.metric("Saldo atual", f"R$ {saldo_atual:,.2f}")


# --- Tabelas (Visuais) ---

st.divider()
table1, table2 = st.columns([2, 1]) # Coluna 1 é 2x mais larga

with table1:
    st.subheader("Extratos Bancários")
    
    # Recria a tabela de extrato com colunas separadas
    # Replicando as medidas DAX (visual)
    df_extratos = df_mov_filtered.copy()
    
    # --- INÍCIO DA CORREÇÃO 4: Restaurar lógica da tabela (hífen) ---
    df_extratos['Total Entradas'] = df_extratos.apply(
        lambda row: row['Valor'] if '-' not in row['Operacao'] else 0,
        axis=1
    )
    df_extratos['Total Saídas'] = df_extratos.apply(
        lambda row: row['Valor'] if '-' in row['Operacao'] else 0,
        axis=1
    )
    # --- FIM DA CORREÇÃO 4 ---
    
    # Agrupa por Data e Descrição, como no seu visual
    df_display = df_extratos.groupby(
        ['Data', 'Descricao']
    ).agg({
        'Total Entradas': 'sum',
        'Total Saídas': 'sum'
    }).reset_index()
    
    # Filtra linhas vazias (onde ambas são 0, caso haja outros tipos de operação)
    df_display = df_display[(df_display['Total Entradas'] != 0) | (df_display['Total Saídas'] != 0)]
    
    # Ordena pela Data mais recente
    df_display = df_display.sort_values(by='Data', ascending=False)

    # Formatação para exibição
    df_display_formatted = df_display.copy()
    df_display_formatted['Data'] = pd.to_datetime(df_display_formatted['Data']).dt.strftime('%d/%m/%Y')
    df_display_formatted['Total Entradas'] = df_display_formatted['Total Entradas'].apply(
        lambda x: f"R$ {x:,.2f}" if x > 0 else ""
    )
    # --- INÍCIO DA CORREÇÃO 5: Restaurar cor vermelha ---
    df_display_formatted['Total Saídas'] = df_display_formatted['Total Saídas'].apply(
        # Adiciona o estilo de cor vermelha e negrito para saídas
        lambda x: f"<span style='color:red; font-weight:bold;'>R$ {x:,.2f}</span>" if x > 0 else ""
    )
    # --- FIM DA CORREÇÃO 5 ---

    # Renomeia colunas para o visual
    df_display_formatted = df_display_formatted.rename(columns={'Descricao': 'Descrição'})
    
    # --- INÍCIO DA CORREÇÃO 6: Restaurar exibição em HTML ---
    # Converte o dataframe para HTML, 'escape=False' permite renderizar o CSS
    html_table = df_display_formatted[['Data', 'Descrição', 'Total Entradas', 'Total Saídas']].to_html(
        escape=False, 
        index=False, 
        border=0, # Remove bordas
        classes="extratos-table" # Adiciona uma classe CSS
    )
    # Exibe a tabela HTML
    st.markdown(html_table, unsafe_allow_html=True)
    # --- FIM DA CORREÇÃO 6 ---

with table2:
    st.subheader("Saldo de todas as contas")
    
    # Prepara o dataframe de saldos para exibição
    df_saldos_display = df_saldos_filtered.copy().sort_values(by='Banco')
    
    # Adiciona a linha de Total (como no Power BI)
    total_saldo_contas = df_saldos_display['Saldo dos bancos'].sum()
    total_row = pd.DataFrame([{'Banco': 'Total', 'Saldo dos bancos': total_saldo_contas}])
    df_saldos_display = pd.concat([df_saldos_display, total_row], ignore_index=True)

    # Formatação
    df_saldos_display['Saldo dos bancos'] = df_saldos_display['Saldo dos bancos'].apply(
        lambda x: f"R$ {x:,.2f}"
    )

    st.dataframe(
        df_saldos_display,
        use_container_width=True,
        hide_index=True,
        height=400 # Mesma altura da outra tabela
    )
