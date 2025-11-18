import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date

# Define a configuração da página
st.set_page_config(layout="wide", page_title="Aplicação Financeira")

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
        
        # Usa a coluna 'dataVencimentoReal' 
        dt_venc = row.get('dataVencimentoReal')
        
        # 2. Verifica se a data de vencimento é válida (NaT)
        if pd.isna(dt_venc):
            return "A vencer"
            
        # 3. Prepara as datas para comparação
        today = pd.to_datetime(date.today()).normalize()
        vencimento = pd.to_datetime(dt_venc).normalize()
        
        # 4. Compara as datas
        if vencimento == today:
            return "Vence hoje"  
        elif vencimento < today:
            return "Vencido"
        else:
            return "A vencer" 
    except Exception:
        return "A vencer"

# --- Estilização CSS ---
st.markdown("""
<style>
    .stTabs {
        background-color: #FAFAFA;
        border: 1px solid #E0E0E0;
        border-radius: 10px;
        padding: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
    }
    h3 {
        color: #FFFFFF;
        background-color: #4CAF50;
        padding: 10px;
        border-radius: 5px;
        text-align: center;
    }
    .stMetric {
        background-color: #FAFAFA;
        border: 1px solid #E0E0E0;
        border-radius: 10px;
        padding: 20px;
    }
    .stDataFrame th {
        background-color: #E8F5E9;
        font-weight: bold;
    }
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- Carregamento de Dados ---

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
            df_movimentos = pd.DataFrame(columns=['Data', 'Horario', 'Descricao', 'Valor', 'Operacao', 'Banco'])
            
        # Renomeia e processa colunas
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
            df_final = pd.DataFrame(columns=['Cliente'])

        return df_final

    except Exception as e:
        st.error(f"Erro ao carregar dados de contas a receber: {e}")
        return pd.DataFrame()

# --- Interface Principal ---

def main():
    st.title("APLICAÇÃO FINANCEIRA")
    
    # Verifica se o token existe
    try:
        api_token = st.secrets["FLOW_API_TOKEN"]
    except:
        st.error("Token da API não encontrado. Configure o arquivo secrets.toml")
        return
    
    # Cria abas
    tab1, tab2 = st.tabs(["🏦 Controle Bancário", "🧾 Contas a Receber"])
    
    # ABA 1: CONTROLE BANCÁRIO
    with tab1:
        df_movimentos, df_saldos = load_movimentos_e_saldos(api_token)
        
        if df_movimentos.empty and df_saldos.empty:
            st.info("Nenhum dado bancário disponível")
        else:
            # Filtros
            col1, col2 = st.columns([1, 2])
            with col1:
                if not df_movimentos.empty:
                    min_date = df_movimentos['Data'].min() if 'Data' in df_movimentos.columns else date.today()
                    max_date = df_movimentos['Data'].max() if 'Data' in df_movimentos.columns else date.today()
                    date_range = st.date_input("Período", [min_date, max_date], key="tab1_date")
                else:
                    date_range = [date.today(), date.today()]
            
            with col2:
                bancos = []
                if not df_movimentos.empty and 'Banco' in df_movimentos.columns:
                    bancos.extend(df_movimentos['Banco'].dropna().unique().tolist())
                if not df_saldos.empty and 'Banco' in df_saldos.columns:
                    bancos.extend(df_saldos['Banco'].dropna().unique().tolist())
                bancos = sorted(list(set(bancos)))
                bancos_selecionados = st.multiselect("Bancos", bancos, default=bancos, key="tab1_banks")
            
            # KPIs
            if not df_movimentos.empty:
                df_filtrado = df_movimentos[
                    (df_movimentos['Data'].between(date_range[0], date_range[1])) &
                    (df_movimentos['Banco'].isin(bancos_selecionados))
                ] if 'Data' in df_movimentos.columns else df_movimentos
                
                entradas = df_filtrado[~df_filtrado['Operacao'].str.contains('-', na=False)]['Valor'].sum()
                saidas = df_filtrado[df_filtrado['Operacao'].str.contains('-', na=False)]['Valor'].sum()
                saldo = entradas - saidas
            else:
                entradas = saidas = saldo = 0
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Entradas", format_brl(entradas))
            col2.metric("Saídas", format_brl(saidas))
            col3.metric("Saldo", format_brl(saldo))
            
            # Tabelas
            if not df_movimentos.empty:
                st.subheader("Movimentos Bancários")
                st.dataframe(df_filtrado[['Data', 'Descricao', 'Valor', 'Operacao', 'Banco']].head(50))
            
            if not df_saldos.empty:
                st.subheader("Saldos Bancários")
                st.dataframe(df_saldos[df_saldos['Banco'].isin(bancos_selecionados)])
    
    # ABA 2: CONTAS A RECEBER
    with tab2:
        df_receber = load_receber_e_clientes(api_token)
        
        if df_receber.empty:
            st.info("Nenhuma conta a receber encontrada")
        else:
            # Preprocessamento dos dados
            try:
                # Tratamento de datas - CORREÇÃO PRINCIPAL
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
                
                # Colunas de exibição
                df_receber['Vencimento'] = df_receber['dataVencimentoReal'].dt.date
                df_receber['Recebido em'] = df_receber['dataBaixa'].dt.date
                df_receber['Projeto'] = df_receber.get('codigoProjeto', 'N/A')
                
            except Exception as e:
                st.error(f"Erro no processamento dos dados: {e}")
            
            # Filtros
            col1, col2 = st.columns(2)
            with col1:
                status_opcoes = df_receber['Status'].unique().tolist() if 'Status' in df_receber.columns else []
                status_selecionados = st.multiselect("Status", status_opcoes, default=status_opcoes)
            
            with col2:
                if 'Vencimento' in df_receber.columns:
                    min_venc = df_receber['Vencimento'].min()
                    max_venc = df_receber['Vencimento'].max()
                    if pd.isna(min_venc): min_venc = date.today()
                    if pd.isna(max_venc): max_venc = date.today()
                    periodo = st.date_input("Período Vencimento", [min_venc, max_venc], key="tab2_date")
                else:
                    periodo = [date.today(), date.today()]
            
            # Aplicar filtros
            if 'Status' in df_receber.columns and 'Vencimento' in df_receber.columns:
                df_filtrado = df_receber[
                    (df_receber['Status'].isin(status_selecionados)) &
                    (df_receber['Vencimento'].between(periodo[0], periodo[1]))
                ]
            else:
                df_filtrado = df_receber
            
            # KPIs
            total_receber = df_filtrado[df_filtrado['Status'] != 'Baixado']['Valor'].sum() if 'Status' in df_filtrado.columns else 0
            total_vencido = df_filtrado[df_filtrado['Status'] == 'Vencido']['Valor'].sum() if 'Status' in df_filtrado.columns else 0
            
            # Recebido este mês
            hoje = date.today()
            recebido_mes = df_receber[
                (df_receber['Recebido em'].notna()) &
                (df_receber['Recebido em'] >= date(hoje.year, hoje.month, 1)) &
                (df_receber['Recebido em'] <= hoje)
            ]['Valor'].sum() if 'Recebido em' in df_receber.columns else 0
            
            col1, col2, col3 = st.columns(3)
            col1.metric("A Receber", format_brl(total_receber))
            col2.metric("Vencido", format_brl(total_vencido))
            col3.metric("Recebido Mês", format_brl(recebido_mes))
            
            # Tabela principal
            st.subheader("Detalhe de Contas a Receber")
            
            colunas_exibir = ['Cliente', 'Projeto', 'Vencimento', 'Recebido em', 'Status', 'Valor']
            colunas_disponiveis = [col for col in colunas_exibir if col in df_filtrado.columns]
            
            if colunas_disponiveis:
                df_display = df_filtrado[colunas_disponiveis].copy()
                if 'Valor' in df_display.columns:
                    df_display['Valor'] = df_display['Valor'].apply(format_brl)
                if 'Projeto' in df_display.columns:
                    df_display = df_display.rename(columns={'Projeto': 'Nº projeto'})
                
                st.dataframe(df_display, use_container_width=True, height=400)
            else:
                st.warning("Nenhuma coluna disponível para exibição")

# Executa a aplicação
if __name__ == "__main__":
    main()
