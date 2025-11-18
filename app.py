import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date

# Define a configuração da página
# ISSO DEVE SER O PRIMEIRO COMANDO STREAMLIT
st.set_page_config(layout="wide", page_title="Aplicação Financeira")

# --- Funções Helper ---

def format_brl(value):
    """
    Formata um número float para o padrão BRL (R$ 1.234,56).
    """
    try:
        formatted = f"{float(value):,.2f}"
        formatted_br = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {formatted_br}"
    except (ValueError, TypeError):
        return "R$ 0,00"

def get_status(row):
    """
    Calcula o status de um título (A vencer, Vence hoje, Vencido, Baixado).
    """
    # 1. Verifica se foi pago (Baixado)
    if pd.notna(row.get('dataBaixa')) or pd.notna(row.get('dataCredito')):
        return "Baixado"
    
    # 2. Obtém o valor da data de vencimento (já normalizado no código principal)
    dt_venc = row.get('dataVencimentoReal')
    
    # 3. Verifica se é NaT
    if pd.isna(dt_venc):
        return "A vencer"

    try:
        # 4. Normaliza as datas para comparação
        today = pd.Timestamp.now().normalize()
        
        # Garante que dt_venc é timestamp e remove info de timezone se houver (fallback)
        vencimento = pd.to_datetime(dt_venc).tz_localize(None).normalize()
        
        # 5. Compara as datas
        if vencimento == today:
            return "Vence hoje"
        elif vencimento < today:
            return "Vencido"
        else:
            return "A vencer"
            
    except (AttributeError, ValueError, TypeError):
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
    [data-testid="stTabs"] button[aria-selected="true"] {
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
        border-radius: 5px;
    }
    [data-testid="stTabs"] button {
        background-color: transparent;
        color: #555555;
        border: none;
        border-radius: 5px;
    }
    h3 {
        color: #FFFFFF;
        background-color: #4CAF50;
        padding: 10px;
        border-radius: 5px;
        text-align: center;
    }
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
    .stDataFrame th {
        background-color: #E8F5E9;
        font-size: 1.1em;
        font-weight: bold;
        color: #333333;
    }
    .stDataFrame td {
        color: #333333 !important;
    }
    .extratos-table td {
        padding: 8px;
        border-bottom: 1px solid #DDDDDD;
        vertical-align: top;
        color: #333333 !important;
    }
    @media (prefers-color-scheme: dark) {
        .stDataFrame td { color: #DDDDDD !important; }
        .extratos-table-container .extratos-table td { color: #333333 !important; }
    }
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
    .extratos-table tr:last-child td { border-bottom: none; }
    .block-container { padding-top: 2rem; }
    footer {visibility: hidden;}
    #MainMenu {visibility: visible;}
</style>
""", unsafe_allow_html=True)

# --- Carregamento de Dados (Cache) ---

@st.cache_data(ttl=600)
def load_movimentos_e_saldos(api_token):
    try:
        headers = {"Authorization": f"Bearer {api_token}"}
        
        # 1. Movimentos
        url_movimentos = "https://api.flow2.com.br/v1/movimentosBancarios?DesabilitarPaginacao=true&DataMovimentoMaiorOuIgualA=2025-01-01"
        response_mov = requests.get(url_movimentos, headers=headers)
        response_mov.raise_for_status()
        data_mov = response_mov.json()
        
        if 'itens' in data_mov and data_mov['itens']:
            df_movimentos = pd.json_normalize(data_mov, record_path=['itens'])
        else:
            cols_mov = ['Data', 'Horario', 'Descricao', 'Valor', 'Operacao', 'Banco']
            df_movimentos = pd.DataFrame(columns=cols_mov)
            
        df_movimentos = df_movimentos.rename(columns={
            "valor": "Valor", "dataMovimento": "DataMovimento",
            "descricao": "Descricao", "operacao": "Operacao", "nomeBanco": "Banco"
        })
        
        if 'Operacao' in df_movimentos.columns:
            df_movimentos['Operacao'] = df_movimentos['Operacao'].astype(str)
        
        df_movimentos['Valor'] = pd.to_numeric(df_movimentos.get('Valor', 0))
        df_movimentos['DataMovimento'] = pd.to_datetime(df_movimentos.get('DataMovimento', None), errors='coerce')
        df_movimentos['Data'] = df_movimentos['DataMovimento'].dt.date
        df_movimentos['Horario'] = df_movimentos['DataMovimento'].dt.time
        df_movimentos['Descricao'] = df_movimentos.get('Descricao', '').astype(str).str.upper()

        # 2. Saldos
        url_saldos = "https://api.flow2.com.br/v1/saldoBancos"
        response_saldos = requests.get(url_saldos, headers=headers)
        response_saldos.raise_for_status()
        data_saldos = response_saldos.json()
        
        if data_saldos:
            df_saldos = pd.json_normalize(data_saldos)
        else:
            cols_saldos = ['Banco', 'Saldo dos bancos']
            df_saldos = pd.DataFrame(columns=cols_saldos)

        df_saldos = df_saldos.rename(columns={"banco.nome": "Banco", "saldo": "Saldo dos bancos"})
        df_saldos['Saldo dos bancos'] = pd.to_numeric(df_saldos.get('Saldo dos bancos', 0))
        
        df_movimentos = df_movimentos.reindex(columns=['Data', 'Horario', 'Descricao', 'Valor', 'Operacao', 'Banco'])
        df_saldos = df_saldos.reindex(columns=['Banco', 'Saldo dos bancos'])

        return df_movimentos, df_saldos

    except Exception as e:
        st.error(f"Erro ao carregar dados da API (Mov/Saldos): {e}")
        return None, None

@st.cache_data(ttl=600)
def load_receber_e_clientes(api_token):
    try:
        headers = {"Authorization": f"Bearer {api_token}"}
        
        # 1. Receber
        url_receber = "https://api.flow2.com.br/v1/recebers?DesabilitarPaginacao=true"
        response_receber = requests.get(url_receber, headers=headers)
        response_receber.raise_for_status()
        try:
            data_receber = response_receber.json()
        except:
            data_receber = {}

        if 'itens' in data_receber and data_receber['itens']:
            df_receber = pd.json_normalize(data_receber, record_path=['itens'])
        else:
            df_receber = pd.DataFrame()

        # 2. Clientes
        url_clientes = "https://api.flow2.com.br/v1/clientes?DesabilitarPaginacao=true"
        response_clientes = requests.get(url_clientes, headers=headers)
        response_clientes.raise_for_status()
        try:
            data_clientes = response_clientes.json()
        except:
            data_clientes = {}

        if 'itens' in data_clientes and data_clientes['itens']:
            df_clientes = pd.json_normalize(data_clientes, record_path=['itens'])
            df_clientes = df_clientes.rename(columns={"id": "idCliente", "nomeRazaoSocial": "Cliente"})
            df_clientes = df_clientes[['idCliente', 'Cliente']]
        else:
            df_clientes = pd.DataFrame(columns=['idCliente', 'Cliente'])

        # 3. Merge
        if not df_receber.empty:
            if 'idCliente' not in df_receber.columns: df_receber['idCliente'] = pd.NA
            
            if not df_clientes.empty:
                df_final = pd.merge(df_receber, df_clientes, on="idCliente", how="left")
            else:
                df_final = df_receber
            
            if 'Cliente' not in df_final.columns: df_final['Cliente'] = "Cliente não informado"
            df_final['Cliente'] = df_final['Cliente'].fillna("Cliente não informado")
        else:
            df_final = df_receber
            if 'Cliente' not in df_final.columns: df_final['Cliente'] = "Cliente não informado"

        return df_final

    except Exception as e:
        st.error(f"Erro ao carregar dados da API (Receber/Clientes): {e}")
        return None

# --- Início da Interface ---

st.title("APLICAÇÃO FINANCEIRA")

try:
    api_token = st.secrets["FLOW_API_TOKEN"]
except KeyError:
    st.error("Token da API (FLOW_API_TOKEN) não encontrado.")
    st.stop()

tab_bancario, tab_receber = st.tabs(["🏦 Controle Bancário", "🧾 Contas a Receber"])

# --- ABA 1: CONTROLE BANCÁRIO ---
with tab_bancario:
    df_movimentos, df_saldos = load_movimentos_e_saldos(api_token)

    if df_movimentos is None or df_saldos is None:
        st.error("Falha ao carregar dados bancários.")
    else:
        st.subheader("Filtros")
        col1_cb, col2_cb = st.columns([1, 2])

        with col1_cb:
            min_date_mov = df_movimentos['Data'].min()
            max_date_mov = df_movimentos['Data'].max()
            if pd.isna(min_date_mov): min_date_mov = date.today()
            if pd.isna(max_date_mov): max_date_mov = date.today()

            date_range_mov = st.date_input("Período", [min_date_mov, max_date_mov], min_value=min_date_mov, max_value=max_date_mov, format="DD/MM/YYYY", key="date_range_mov")
            
            start_date_filter_mov, end_date_filter_mov = min_date_mov, max_date_mov
            if len(date_range_mov) == 2:
                start_date_filter_mov, end_date_filter_mov = date_range_mov

        with col2_cb:
            all_banks_mov = df_movimentos['Banco'].dropna().unique()
            all_banks_saldos = df_saldos['Banco'].dropna().unique()
            all_banks = sorted(list(set(list(all_banks_mov) + list(all_banks_saldos))))
            selected_banks = st.multiselect("Banco(s)", options=all_banks, default=all_banks, key="selected_banks")

        if pd.isna(start_date_filter_mov): start_date_filter_mov = min_date_mov
        if pd.isna(end_date_filter_mov): end_date_filter_mov = max_date_mov
        
        df_mov_filtered = df_movimentos[
            (df_movimentos['Data'].notna()) & 
            (df_movimentos['Data'] >= start_date_filter_mov) &
            (df_movimentos['Data'] <= end_date_filter_mov) &
            (df_movimentos['Banco'].isin(selected_banks))
        ]
        
        df_saldos_filtered = df_saldos[df_saldos['Banco'].isin(selected_banks)]

        st.divider()
        total_entradas = df_mov_filtered[~df_mov_filtered['Operacao'].astype(str).str.contains('-')]['Valor'].sum()
        total_saidas = df_mov_filtered[df_mov_filtered['Operacao'].astype(str).str.contains('-')]['Valor'].sum()
        saldo_atual = total_entradas - total_saidas

        kpi1_cb, kpi2_cb, kpi3_cb = st.columns(3)
        kpi1_cb.metric("Total de entradas", format_brl(total_entradas))
        kpi2_cb.metric("Total de saídas", format_brl(total_saidas), delta=format_brl(-total_saidas), delta_color="inverse")
        kpi3_cb.metric("Saldo atual", format_brl(saldo_atual))

        st.divider()
        table1_cb, table2_cb = st.columns([2, 1])

        with table1_cb:
            st.subheader("Extratos Bancários")
            df_extratos = df_mov_filtered.copy()
            df_extratos['Total Entradas'] = df_extratos.apply(lambda row: row['Valor'] if '-' not in str(row['Operacao']) else 0, axis=1)
            df_extratos['Total Saídas'] = df_extratos.apply(lambda row: row['Valor'] if '-' in str(row['Operacao']) else 0, axis=1)
            if 'Descricao' not in df_extratos.columns: df_extratos['Descricao'] = "N/A"
            
            df_display = df_extratos.groupby(['Data', 'Descricao']).agg({'Total Entradas': 'sum', 'Total Saídas': 'sum'}).reset_index()
            df_display = df_display[(df_display['Total Entradas'] != 0) | (df_display['Total Saídas'] != 0)].sort_values(by='Data', ascending=False)

            df_display_formatted = df_display.copy()
            df_display_formatted['Data'] = pd.to_datetime(df_display_formatted['Data']).dt.strftime('%d/%m/%Y')
            df_display_formatted['Total Entradas'] = df_display_formatted['Total Entradas'].apply(lambda x: format_brl(x) if x > 0 else "")
            df_display_formatted['Total Saídas'] = df_display_formatted['Total Saídas'].apply(lambda x: f"<span style='color:red; font-weight:bold;'>{format_brl(x)}</span>" if x > 0 else "")
            df_display_formatted = df_display_formatted.rename(columns={'Descricao': 'Descrição'})
            
            html_table = df_display_formatted[['Data', 'Descrição', 'Total Entradas', 'Total Saídas']].to_html(escape=False, index=False, border=0, classes="extratos-table")
            st.markdown(f'<div class="extratos-table-container">{html_table}</div>', unsafe_allow_html=True)

        with table2_cb:
            st.subheader("Saldo de todas as contas")
            df_saldos_display = df_saldos_filtered.copy().sort_values(by='Banco')
            total_saldo_contas = df_saldos_display['Saldo dos bancos'].sum()
            total_row = pd.DataFrame([{'Banco': 'Total', 'Saldo dos bancos': total_saldo_contas}])
            df_saldos_display = pd.concat([df_saldos_display, total_row], ignore_index=True)
            df_saldos_display['Saldo dos bancos'] = df_saldos_display['Saldo dos bancos'].apply(format_brl)
            st.dataframe(df_saldos_display, use_container_width=True, hide_index=True, height=400)

# --- ABA 2: CONTAS A RECEBER ---
with tab_receber:
    
    df_receber_raw = load_receber_e_clientes(api_token)

    if df_receber_raw is None or df_receber_raw.empty:
        st.error("Falha ao carregar dados de Contas a Receber.")
    else:
        try:
            # --- Preparação e Limpeza de Dados (Contas a Receber) ---
            df_receber = df_receber_raw.copy()
            
            # --- CORREÇÃO DO ERRO DE DATAS E TIMEZONE (IDs 264, 342) ---
            
            # 1. Garante conversão para datetime com UTC=True para lidar com strings como "T01:00:00-03:00"
            df_receber['dataVencimentoReal'] = pd.to_datetime(df_receber.get('dataVencimentoReal'), utc=True, errors='coerce')
            
            # 2. Remove a informação de fuso horário (converte para timezone-naive)
            # Isso unifica "2025-01-01 01:00:00+00:00" e "2025-01-01 00:00:00" para o mesmo tipo
            df_receber['dataVencimentoReal'] = df_receber['dataVencimentoReal'].dt.tz_localize(None)

            # 3. Normaliza para meia-noite (remove horas, minutos, segundos) mantendo formato Timestamp
            df_receber['dataVencimentoReal'] = df_receber['dataVencimentoReal'].dt.normalize()

            # Tratamento das outras datas
            df_receber['dataBaixa'] = pd.to_datetime(df_receber.get('dataBaixa'), errors='coerce')
            df_receber['dataCredito'] = pd.to_datetime(df_receber.get('dataCredito'), errors='coerce')
            
            df_receber['situacao'] = df_receber.get('situacao', 'Indefinido')
            df_receber['Valor'] = pd.to_numeric(df_receber.get('valorAReceberParcela', 0), errors='coerce').fillna(0).abs()
            
            # Colunas auxiliares para exibição (dt.date cria objeto date, não Timestamp)
            df_receber['Vencimento_Display'] = df_receber['dataVencimentoReal'].dt.date
            df_receber['Recebido em'] = df_receber['dataBaixa'].dt.date 
            
            # Aplica o cálculo de status
            df_receber['Status'] = df_receber.apply(get_status, axis=1)
            df_receber['Projeto'] = df_receber.get('codigoProjeto', 'N/A')

            # --- Fim da Preparação ---

            # --- Filtros ---
            st.subheader("Filtros de Contas a Receber")
            col1_cr, col2_cr = st.columns([1, 1])

            with col1_cr:
                status_options = sorted(df_receber['Status'].unique())
                selected_status = st.multiselect("Status (Calculado)", options=status_options, default=status_options, key="selected_status")

            with col2_cr:
                # Usa a coluna normalizada (Timestamp) para pegar min/max, mas exibe como data
                min_date_cr = df_receber['dataVencimentoReal'].min()
                max_date_cr = df_receber['dataVencimentoReal'].max()

                # Fallback se min/max forem NaT
                if pd.isna(min_date_cr): min_date_cr = pd.Timestamp.now().normalize()
                if pd.isna(max_date_cr): max_date_cr = pd.Timestamp.now().normalize()

                # Converte para .date() para o widget do Streamlit
                date_range_cr = st.date_input(
                    "Período de Vencimento",
                    [min_date_cr.date(), max_date_cr.date()],
                    min_value=min_date_cr.date(),
                    max_value=max_date_cr.date(),
                    format="DD/MM/YYYY",
                    key="date_range_cr"
                )
                
                start_date_filter_cr, end_date_filter_cr = min_date_cr.date(), max_date_cr.date()
                if len(date_range_cr) == 2:
                    start_date_filter_cr = date_range_cr[0]
                    end_date_filter_cr = date_range_cr[1]

            # --- Aplicação dos Filtros ---
            
            # Converte os inputs do filtro (date) para Timestamp (datetime64) para comparar com o DataFrame
            start_ts = pd.Timestamp(start_date_filter_cr)
            end_ts = pd.Timestamp(end_date_filter_cr) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)

            # Filtragem Robusta (Timestamp vs Timestamp)
            kpi_df = df_receber[
                (df_receber['dataVencimentoReal'].notna()) & 
                (df_receber['dataVencimentoReal'] >= start_ts) &
                (df_receber['dataVencimentoReal'] <= end_ts)
            ].copy()
            
            df_receber_filtered = kpi_df[kpi_df['Status'].isin(selected_status)].copy()

            # --- KPIs ---
            st.divider()
            total_a_receber = kpi_df[kpi_df['Status'] != 'Baixado']['Valor'].sum()
            total_vencido = kpi_df[kpi_df['Status'] == 'Vencido']['Valor'].sum()
            
            today_date = date.today()
            df_recebido_mes = df_receber[
                (df_receber['Recebido em'].notna()) &
                (df_receber['Recebido em'] >= date(today_date.year, today_date.month, 1)) &
                (df_receber['Recebido em'] <= today_date)
            ]
            total_recebido_mes = df_recebido_mes['Valor'].sum()

            kpi1_cr, kpi2_cr, kpi3_cr = st.columns(3)
            kpi1_cr.metric("Total a Receber (no período)", format_brl(total_a_receber))
            kpi2_cr.metric("Total Vencido (no período)", format_brl(total_vencido))
            kpi3_cr.metric("Total Recebido (Este Mês)", format_brl(total_recebido_mes))

            # --- Tabela ---
            st.subheader("Detalhe de Contas a Receber")
            df_receber_display = df_receber_filtered.copy()
            df_receber_display['Valor Parcela'] = df_receber_display['Valor'].apply(format_brl)
            
            # Usa a coluna Vencimento_Display (que é .date object) para formatar string
            df_receber_display['Vencimento'] = df_receber_display['Vencimento_Display'].apply(
                lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else ''
            )
            df_receber_display['Recebido em'] = df_receber_display['Recebido em'].apply(
                lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else ''
            )
            
            st.dataframe(
                df_receber_display[[
                    'Cliente', 'Projeto', 'Vencimento', 'Recebido em', 'Status', 'Valor Parcela'
                ]],
                use_container_width=True,
                hide_index=True,
                height=400
            )

            with st.expander("Dados Brutos (Primeiros 5)"):
                st.dataframe(df_receber_raw.head(5))

        except Exception as e:
            st.error(f"Erro ao processar dados de Contas a Receber: {e}")
            st.write("Detalhe do erro:")
            st.write(e)
            st.dataframe(df_receber_raw.head(5))
