import streamlit as st
import requests
from fpdf import FPDF
import base64
import pandas as pd
import socket
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import datetime # Importado para tratamento de datas
import re # Importado para tratamento de strings e validações

# Inicializa as variáveis de estado da sessão do Streamlit,
# garantindo que elas existam antes de serem acessadas para evitar KeyError.
# Isso é crucial para campos que são preenchidos por busca de CEP.
if "comprador_cep_pf" not in st.session_state:
    st.session_state.comprador_cep_pf = ""
if "comprador_end_residencial_pf" not in st.session_state:
    st.session_state.comprador_end_residencial_pf = ""
if "comprador_bairro_pf" not in st.session_state:
    st.session_state.comprador_bairro_pf = ""
if "comprador_cidade_pf" not in st.session_state:
    st.session_state.comprador_cidade_pf = ""
if "comprador_estado_pf" not in st.session_state:
    st.session_state.comprador_estado_pf = ""
if "comprador_numero_pf" not in st.session_state:
    st.session_state.comprador_numero_pf = ""

if "conjuge_cep_pf" not in st.session_state:
    st.session_state.conjuge_cep_pf = ""
if "conjuge_end_residencial_pf" not in st.session_state:
    st.session_state.conjuge_end_residencial_pf = ""
if "conjuge_bairro_pf" not in st.session_state:
    st.session_state.conjuge_bairro_pf = ""
if "conjuge_cidade_pf" not in st.session_state:
    st.session_state.conjuge_cidade_pf = ""
if "conjuge_estado_pf" not in st.session_state:
    st.session_state.conjuge_estado_pf = ""
if "conjuge_numero_pf" not in st.session_state:
    st.session_state.conjuge_numero_pf = ""

if "comprador_cep_pj" not in st.session_state:
    st.session_state.comprador_cep_pj = ""
if "comprador_end_residencial_comercial_pj" not in st.session_state:
    st.session_state.comprador_end_residencial_comercial_pj = ""
if "comprador_bairro_pj" not in st.session_state:
    st.session_state.comprador_bairro_pj = ""
if "comprador_cidade_pj" not in st.session_state:
    st.session_state.comprador_cidade_pj = ""
if "comprador_estado_pj" not in st.session_state:
    st.session_state.comprador_estado_pj = ""
if "comprador_numero_pj" not in st.session_state:
    st.session_state.comprador_numero_pj = ""

if "representante_cep_pj" not in st.session_state:
    st.session_state.representante_cep_pj = ""
if "representante_end_residencial_pj" not in st.session_state:
    st.session_state.representante_end_residencial_pj = ""
if "representante_bairro_pj" not in st.session_state:
    st.session_state.representante_bairro_pj = ""
if "representante_cidade_pj" not in st.session_state:
    st.session_state.representante_cidade_pj = ""
if "representante_estado_pj" not in st.session_state:
    st.session_state.representante_estado_pj = ""
if "representante_numero_pj" not in st.session_state:
    st.session_state.representante_numero_pj = ""

if "conjuge_cep_pj" not in st.session_state:
    st.session_state.conjuge_cep_pj = ""
if "conjuge_end_residencial_pj" not in st.session_state:
    st.session_state.conjuge_end_residencial_pj = ""
if "conjuge_bairro_pj" not in st.session_state:
    st.session_state.conjuge_bairro_pj = ""
if "conjuge_cidade_pj" not in st.session_state:
    st.session_state.conjuge_cidade_pj = ""
if "conjuge_estado_pj" not in st.session_state:
    st.session_state.conjuge_estado_pj = ""
if "conjuge_numero_pj" not in st.session_state:
    st.session_state.conjuge_numero_pj = ""

# Adicionado para pessoas vinculadas
if "endereco_pessoa_pj" not in st.session_state:
    st.session_state.endereco_pessoa_pj = ""
if "bairro_pessoa_pj" not in st.session_state:
    st.session_state.bairro_pessoa_pj = ""
if "cidade_pessoa_pj" not in st.session_state:
    st.session_state.cidade_pessoa_pj = ""
if "estado_pessoa_pj" not in st.session_state:
    st.session_state.estado_pessoa_pj = ""

# Adicionado para dependentes PF
if "dependentes_pf_temp" not in st.session_state:
    st.session_state.dependentes_pf_temp = []

# Adicionado para dependentes PJ
if "dependentes_pj_temp" not in st.session_state:
    st.session_state.dependentes_pj_temp = []

# Inicialização dos novos campos da proposta
if "proposta_valor_imovel" not in st.session_state:
    st.session_state.proposta_valor_imovel = ""
if "proposta_forma_pagamento_imovel" not in st.session_state:
    st.session_state.proposta_forma_pagamento_imovel = ""
if "proposta_valor_honorarios" not in st.session_state:
    st.session_state.proposta_valor_honorarios = ""
if "proposta_forma_pagamento_honorarios" not in st.session_state:
    st.session_state.proposta_forma_pagamento_honorarios = ""
if "proposta_conta_bancaria" not in st.session_state:
    st.session_state.proposta_conta_bancaria = ""
if "proposta_valor_ir" not in st.session_state:
    st.session_state.proposta_valor_ir = ""
if "proposta_valor_escritura" not in st.session_state:
    st.session_state.proposta_valor_escritura = ""
if "proposta_observacoes" not in st.session_state:
    st.session_state.proposta_observacoes = ""
if "proposta_corretor_angariador" not in st.session_state:
    st.session_state.proposta_corretor_angariador = ""
if "proposta_corretor_vendedor" not in st.session_state:
    st.session_state.proposta_corretor_vendedor = ""
if "proposta_data_negociacao" not in st.session_state:
    st.session_state.proposta_data_negociacao = datetime.date.today()

# Configuração de sessão com retry para requisições HTTP
session = requests.Session()
retry = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retry)
session.mount('http://', adapter)
session.mount('https://', adapter)

REGIMES_DE_BENS = [
    "",
    "Comunhão Universal de Bens",
    "Comunhão Parcial de Bens",
    "Separação Total de Bens",
    "Separação Obrigatória de Bens",
    "Participação Final nos Aquestos",
]

def _buscar_cep_viacep(cep):
    url = f"https://viacep.com.br/ws/{cep}/json/"
    try:
        response = session.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        if "erro" not in data:
            return data, None
        else:
            return None, f"CEP não encontrado na ViaCEP: {cep}"
    except requests.exceptions.Timeout:
        return None, "Tempo de conexão esgotado com ViaCEP."
    except requests.exceptions.ConnectionError:
        return None, "Não foi possível conectar ao servidor ViaCEP."
    except requests.exceptions.RequestException as e:
        return None, f"Erro na ViaCEP: {str(e)}"

def _buscar_cep_brasilapi(cep):
    url = f"https://brasilapi.com.br/api/cep/v1/{cep}"
    try:
        response = session.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        return {
            'logradouro': data.get('street', ''),
            'bairro': data.get('neighborhood', ''),
            'localidade': data.get('city', ''),
            'uf': data.get('state', '')
        }, None
    except requests.exceptions.Timeout:
        return None, "Tempo de conexão esgotado com Brasil API."
    except requests.exceptions.ConnectionError:
        return None, "Não foi possível conectar ao servidor Brasil API."
    except requests.exceptions.RequestException as e:
        return None, f"Erro na Brasil API: {str(e)}"

def _buscar_cep_postmon(cep):
    url = f"https://api.postmon.com.br/v1/cep/{cep}"
    try:
        response = session.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        return {
            'logradouro': data.get('logradouro', ''),
            'bairro': data.get('bairro', ''),
            'localidade': data.get('cidade', ''),
            'uf': data.get('estado', '')
        }, None
    except requests.exceptions.Timeout:
        return None, "Tempo de conexão esgotado com Postmon."
    except requests.exceptions.ConnectionError:
        return None, "Não foi possível conectar ao servidor Postmon."
    except requests.exceptions.RequestException as e:
        return None, f"Erro na Postmon: {str(e)}"

def buscar_cep(cep):
    if not cep:
        return None, "Por favor, insira um CEP para buscar."
    cep_limpo = cep.replace("-", "").replace(".", "").strip()
    if len(cep_limpo) != 8 or not cep_limpo.isdigit():
        return None, "CEP inválido. Por favor, insira 8 dígitos numéricos."

    endereco_info, error_msg = _buscar_cep_viacep(cep_limpo)
    if endereco_info:
        return endereco_info, None
    else:
        st.warning(f"ViaCEP falhou: {error_msg}. Tentando Brasil API...")
        endereco_info, error_msg = _buscar_cep_brasilapi(cep_limpo)
        if endereco_info:
            return endereco_info, None
        else:
            st.warning(f"Brasil API falhou: {error_msg}. Tentando Postmon...")
            endereco_info, error_msg = _buscar_cep_postmon(cep_limpo)
            if endereco_info:
                return endereco_info, None
            else:
                return None, f"Todas as APIs de CEP falharam: {error_msg}"

def sanitize_text(text):
    if isinstance(text, str):
        text = text.replace('\u2013', '-')
        text = text.replace('\u2014', '--')
        text = text.replace('\u2019', "'")
        text = text.replace('\u201C', '"')
        text = text.replace('\u201D', '"')
        text = text.encode('latin-1', 'ignore').decode('latin-1')
        text = text.strip()
    return text

def _on_cep_search_callback(tipo_campo: str, cep_key: str):
    cep_value = st.session_state[cep_key]
    if cep_value:
        endereco_info, error_msg = buscar_cep(cep_value)
        if endereco_info:
            mapping = {
                'pf': {
                    'logradouro': 'comprador_end_residencial_pf',
                    'bairro': 'comprador_bairro_pf',
                    'localidade': 'comprador_cidade_pf',
                    'uf': 'comprador_estado_pf',
                },
                'conjuge_pf': {
                    'logradouro': 'conjuge_end_residencial_pf',
                    'bairro': 'conjuge_bairro_pf',
                    'localidade': 'conjuge_cidade_pf',
                    'uf': 'conjuge_estado_pf',
                },
                'empresa_pj': {
                    'logradouro': 'comprador_end_residencial_comercial_pj',
                    'bairro': 'comprador_bairro_pj',
                    'localidade': 'comprador_cidade_pj',
                    'uf': 'comprador_estado_pj',
                },
                'administrador_pj': {
                    'logradouro': 'representante_end_residencial_pj',
                    'bairro': 'representante_bairro_pj',
                    'localidade': 'representante_cidade_pj',
                    'uf': 'representante_estado_pj',
                },
                'conjuge_pj': {
                    'logradouro': 'conjuge_end_residencial_pj',
                    'bairro': 'conjuge_bairro_pj',
                    'localidade': 'conjuge_cidade_pj',
                    'uf': 'conjuge_estado_pj',
                },
                'pessoa_pj': {
                    'logradouro': 'endereco_pessoa_pj',
                    'bairro': 'bairro_pessoa_pj',
                    'localidade': 'cidade_pessoa_pj',
                    'uf': 'estado_pessoa_pj'
                }
            }
            target_keys = mapping.get(tipo_campo)
            if target_keys:
                for campo_origem, session_key in target_keys.items():
                    try:
                        st.session_state[session_key] = endereco_info.get(campo_origem, '')
                    except Exception as e:
                        st.warning(f"Erro ao definir o valor de {session_key}: {str(e)}")
                st.success("Endereço preenchido!")
            else:
                st.error("Tipo de campo de endereço desconhecido.")
        elif error_msg:
            st.error(error_msg)
    else:
        st.warning("Por favor, digite um CEP para buscar.")

def formatar_cpf(cpf: str) -> str:
    cpf = re.sub(r'[^0-9]', '', cpf)
    if len(cpf) == 11:
        return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
    return cpf

def formatar_cnpj(cnpj: str) -> str:
    cnpj = re.sub(r'[^0-9]', '', cnpj)
    if len(cnpj) == 14:
        return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
    return cnpj

def formatar_telefone(telefone: str) -> str:
    telefone = re.sub(r'[^0-9]', '', telefone)
    if len(telefone) == 11 and telefone[2] == '9':
        return f"({telefone[:2]}) {telefone[2:7]}-{telefone[7:]}"
    elif len(telefone) == 10:
        return f"({telefone[:2]}) {telefone[2:6]}-{telefone[6:]}"
    return telefone

# --- FUNÇÃO HELPER PARA COLUNAS COM MULTICELL ---
def pdf_two_columns(pdf, col1_text, col1_width, col2_text, col2_width):
    """
    Imprime duas células lado a lado, onde a segunda pode ser multilinha (MultiCell),
    garantindo que a próxima escrita comece abaixo da maior das duas.
    """
    # Salva a posição inicial
    x_start = pdf.get_x()
    y_start = pdf.get_y()

    # Imprime a primeira coluna (Célula simples)
    pdf.cell(col1_width, 6, col1_text, 0, 0)

    # Salva a posição X após a primeira coluna para iniciar a segunda
    x_col2 = pdf.get_x()
    
    # Retorna Y para o topo para imprimir a segunda coluna
    pdf.set_xy(x_col2, y_start)
    
    # Imprime a segunda coluna (MultiCell)
    # A MultiCell quebrará linhas automaticamente, mas voltaria para a margem esquerda.
    # Para evitar isso, ajustamos a margem esquerda temporariamente.
    original_l_margin = pdf.l_margin
    pdf.set_left_margin(x_col2) # Define a nova margem esquerda como o início da col2
    pdf.multi_cell(col2_width, 6, col2_text, 0, 'L')
    
    # Restaura a margem esquerda original
    pdf.set_left_margin(original_l_margin)
    
    # Calcula a nova posição Y (abaixo do que foi impresso)
    y_end = pdf.get_y()
    
    # Reposiciona o cursor para a linha seguinte, na margem original
    pdf.set_xy(original_l_margin, y_end)


def gerar_pdf_pf(dados, dependentes=None, dados_proposta=None):
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('Helvetica', '', 10)
        
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, sanitize_text("Ficha Cadastral Pessoa Física - Cessão e Transferência de Direitos"), 0, 1, "C")
        pdf.ln(8)

        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, sanitize_text("Dados do Empreendimento e Imobiliária"), 0, 1, "L")
        pdf.set_font("Helvetica", "", 10)
        for key_suffix in ["empreendimento", "corretor", "imobiliaria", "qd", "lt", "ativo", "quitado"]:
            key = f"{key_suffix}_pf"
            value = dados.get(key, '')
            if value and sanitize_text(value):
                pdf.cell(0, 6, f"{sanitize_text(key_suffix.replace('_', ' ').title())}: {sanitize_text(str(value))}", 0, 1)
        pdf.ln(3)

        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, sanitize_text("Dados do COMPRADOR(A)"), 0, 1, "L")
        pdf.set_font("Helvetica", "", 10)
        
        nome_comprador = dados.get('comprador_nome_pf', '')
        profissao_comprador = dados.get('comprador_profissao_pf', '')
        if nome_comprador or profissao_comprador:
            pdf.cell(95, 6, f"Nome Completo: {sanitize_text(nome_comprador)}", 0, 0)
            pdf.cell(0, 6, f"Profissão: {sanitize_text(profissao_comprador)}", 0, 1)

        nacionalidade_comprador = dados.get('comprador_nacionalidade_pf', '')
        if nacionalidade_comprador:
            pdf.cell(0, 6, f"Nacionalidade: {sanitize_text(nacionalidade_comprador)}", 0, 1)

        fone_residencial_comprador = dados.get('comprador_fone_residencial_pf', '')
        fone_comercial_comprador = dados.get('comprador_fone_comercial_pf', '')
        if fone_residencial_comprador or fone_comercial_comprador:
            pdf.cell(95, 6, f"Fone Residencial: {sanitize_text(formatar_telefone(fone_residencial_comprador))}", 0, 0)
            pdf.cell(0, 6, f"Fone Comercial: {sanitize_text(formatar_telefone(fone_comercial_comprador))}", 0, 1)

        celular_comprador = dados.get('comprador_celular_pf', '')
        email_comprador = dados.get('comprador_email_pf', '')
        if celular_comprador or email_comprador:
            pdf.cell(95, 6, f"Celular: {sanitize_text(formatar_telefone(celular_comprador))}", 0, 0)
            pdf.cell(0, 6, f"E-mail: {sanitize_text(email_comprador)}", 0, 1)

        endereco_res_comprador = dados.get('comprador_end_residencial_pf', '')
        numero_comprador = dados.get('comprador_numero_pf', '')
        if endereco_res_comprador:
            endereco_linha = f"Endereço Residencial: {sanitize_text(endereco_res_comprador)}"
            if numero_comprador:
                endereco_linha += f", Nº {sanitize_text(numero_comprador)}"
            pdf.cell(0, 6, endereco_linha, 0, 1)

        bairro_comprador = dados.get('comprador_bairro_pf', '')
        cidade_comprador = dados.get('comprador_cidade_pf', '')
        estado_comprador = dados.get('comprador_estado_pf', '')
        cep_comprador = dados.get('comprador_cep_pf', '')

        if bairro_comprador or cidade_comprador or estado_comprador or cep_comprador:
            if bairro_comprador:
                pdf.cell(95, 6, f"Bairro: {sanitize_text(bairro_comprador)}", 0, 0)
            if cidade_comprador and estado_comprador:
                pdf.cell(0, 6, f"Cidade/Estado: {sanitize_text(cidade_comprador)}/{sanitize_text(estado_comprador)}", 0, 1)
            elif bairro_comprador: 
                pdf.ln(6) 
            
            if cep_comprador:
                pdf.cell(0, 6, f"CEP: {sanitize_text(cep_comprador)}", 0, 1)

        estado_civil_comprador = dados.get('comprador_estado_civil_pf', '')
        regime_bens_comprador = dados.get('comprador_regime_bens_pf', '')
        if estado_civil_comprador or regime_bens_comprador:
            pdf.cell(95, 6, f"Estado Civil: {sanitize_text(estado_civil_comprador)}", 0, 0)
            pdf.cell(0, 6, f"Regime de Bens: {sanitize_text(regime_bens_comprador)}", 0, 1)

        uniao_estavel_comprador = dados.get('comprador_uniao_estavel_pf', '')
        if uniao_estavel_comprador:
            pdf.cell(0, 6, f"União Estável: {sanitize_text(uniao_estavel_comprador)}", 0, 1)

        pdf.ln(3) 
        
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, sanitize_text("Condição de Convivência:"), 0, 1)
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 4.5, sanitize_text("Declara conviver em união estável - Apresentar comprovante de estado civil de cada um e a declaração de convivência em união estável com as assinaturas reconhecidas em Cartório."), 0, "L")
        pdf.ln(3)

        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, sanitize_text("Dados do CÔNJUGE/SÓCIO(A)"), 0, 1, "L")
        pdf.set_font("Helvetica", "", 10)
        
        nome_conjuge = dados.get('conjuge_nome_pf', '')
        profissao_conjuge = dados.get('conjuge_profissao_pf', '')
        if nome_conjuge or profissao_conjuge:
            pdf.cell(95, 6, f"Nome Completo Cônjuge/Sócio(a): {sanitize_text(nome_conjuge)}", 0, 0)
            pdf.cell(0, 6, f"Profissão Cônjuge/Sócio(a): {sanitize_text(profissao_conjuge)}", 0, 1)

        nacionalidade_conjuge = dados.get('conjuge_nacionalidade_pf', '')
        if nacionalidade_conjuge:
            pdf.cell(0, 6, f"Nacionalidade Cônjuge/Sócio(a): {sanitize_text(nacionalidade_conjuge)}", 0, 1)

        fone_residencial_conjuge = dados.get('conjuge_fone_residencial_pf', '')
        fone_comercial_conjuge = dados.get('conjuge_fone_comercial_pf', '')
        if fone_residencial_conjuge or fone_comercial_conjuge:
            pdf.cell(95, 6, f"Fone Residencial: {sanitize_text(formatar_telefone(fone_residencial_conjuge))}", 0, 0)
            pdf.cell(0, 6, f"Fone Comercial: {sanitize_text(formatar_telefone(fone_comercial_conjuge))}", 0, 1)

        celular_conjuge = dados.get('conjuge_celular_pf', '')
        email_conjuge = dados.get('conjuge_email_pf', '')
        if celular_conjuge or email_conjuge:
            pdf.cell(95, 6, f"Celular: {sanitize_text(formatar_telefone(celular_conjuge))}", 0, 0)
            pdf.cell(0, 6, f"E-mail: {sanitize_text(email_conjuge)}", 0, 1)

        endereco_res_conjuge = dados.get('conjuge_end_residencial_pf', '')
        numero_conjuge = dados.get('conjuge_numero_pf', '')
        if endereco_res_conjuge:
            endereco_linha_conjuge = f"Endereço Residencial: {sanitize_text(endereco_res_conjuge)}"
            if numero_conjuge:
                endereco_linha_conjuge += f", Nº {sanitize_text(numero_conjuge)}"
            pdf.cell(0, 6, endereco_linha_conjuge, 0, 1)
        
        bairro_conjuge = dados.get('conjuge_bairro_pf', '')
        cidade_conjuge = dados.get('conjuge_cidade_pf', '')
        estado_conjuge = dados.get('conjuge_estado_pf', '')
        cep_conjuge = dados.get('conjuge_cep_pf', '')

        if bairro_conjuge or cidade_conjuge or estado_conjuge or cep_conjuge:
            if bairro_conjuge:
                pdf.cell(95, 6, f"Bairro: {sanitize_text(bairro_conjuge)}", 0, 0)
            if cidade_conjuge and estado_conjuge:
                pdf.cell(0, 6, f"Cidade/Estado: {sanitize_text(cidade_conjuge)}/{sanitize_text(estado_conjuge)}", 0, 1)
            elif bairro_conjuge: 
                pdf.ln(6) 
            
            if cep_conjuge:
                pdf.cell(0, 6, f"CEP: {sanitize_text(cep_conjuge)}", 0, 1)
        
        pdf.ln(3)

        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, sanitize_text("DOCUMENTOS NECESSÁRIOS:"), 0, 1)
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 4.5, sanitize_text("CNH; RG e CPF; Comprovante do Estado Civil, Comprovante de Endereço, Comprovante de Renda, CND da Prefeitura e Nada Consta do Condomínio ou Associação."), 0, "L")
        pdf.ln(3)

        condomino_indicado = dados.get('condomino_indicado_pf', '')
        if condomino_indicado and sanitize_text(condomino_indicado):
            pdf.ln(5)
            pdf.set_font("Helvetica", "B", 10)
            pdf.multi_cell(0, 6, sanitize_text("No caso de Condomínio ou Loteamento Fechado, quando a cessão for emitida para sócio(a)(s), não casados entre si e nem conviventes é necessário indicar qual dos dois será o(a) condômino(a):"), 0, 'L')
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(0, 6, f"Indique aqui quem será o(a) condômino(a): {sanitize_text(condomino_indicado)}", 0, 1)
            pdf.ln(3)

        # Inserir Dados da Proposta em uma nova página, se houver
        if dados_proposta:
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 16)
            pdf.cell(0, 10, sanitize_text("Dados da Proposta"), 0, 1, "C")
            pdf.ln(5)
            pdf.set_font("Helvetica", "", 10)

            # Valor do imóvel e Forma de pagamento (imóvel)
            valor_imovel = dados_proposta.get('valor_imovel', '')
            forma_pagamento_imovel = dados_proposta.get('forma_pagamento_imovel', '')
            if valor_imovel or forma_pagamento_imovel:
                # --- CORREÇÃO MULTICELL EM COLUNA ---
                col1_text = f"Valor do imóvel: {sanitize_text(valor_imovel)}"
                col2_text = f"Forma de pagamento (Imóvel): {sanitize_text(forma_pagamento_imovel)}"
                pdf_two_columns(pdf, col1_text, 80, col2_text, 110)

            # Valor dos honorários e Forma de pagamento (honorários)
            valor_honorarios = dados_proposta.get('valor_honorarios', '')
            forma_pagamento_honorarios = dados_proposta.get('forma_pagamento_honorarios', '')
            if valor_honorarios or forma_pagamento_honorarios:
                # --- CORREÇÃO MULTICELL EM COLUNA ---
                col1_text = f"Valor dos honorários: {sanitize_text(valor_honorarios)}"
                col2_text = f"Forma de pagamento (Honorários): {sanitize_text(forma_pagamento_honorarios)}"
                pdf_two_columns(pdf, col1_text, 80, col2_text, 110)

            # Conta Bancária para transferência
            conta_bancaria = dados_proposta.get('conta_bancaria', '')
            if conta_bancaria:
                pdf.cell(0, 6, f"Conta Bancária para transferência: {sanitize_text(conta_bancaria)}", 0, 1)

            # Valor para declaração de imposto de renda
            valor_ir = dados_proposta.get('valor_ir', '')
            if valor_ir:
                pdf.cell(0, 6, f"Valor para declaração de imposto de renda: {sanitize_text(valor_ir)}", 0, 1)
            
            # Valor para escritura
            valor_escritura = dados_proposta.get('valor_escritura', '')
            if valor_escritura:
                pdf.cell(0, 6, f"Valor para escritura: {sanitize_text(valor_escritura)}", 0, 1)

            # Observações
            observacoes_proposta = dados_proposta.get('observacoes', '')
            if observacoes_proposta:
                pdf.multi_cell(0, 6, f"Observações: {sanitize_text(observacoes_proposta)}", 0, "L")
            
            # Corretor(a) angariador e Corretor(a) vendedor(a)
            corretor_angariador = dados_proposta.get('corretor_angariador', '')
            corretor_vendedor = dados_proposta.get('corretor_vendedor', '')
            if corretor_angariador or corretor_vendedor:
                pdf.cell(95, 6, f"Corretor(a) angariador: {sanitize_text(corretor_angariador)}", 0, 0)
                pdf.cell(0, 6, f"Corretor(a) vendedor(a): {sanitize_text(corretor_vendedor)}", 0, 1)

            # Data da negociação
            data_negociacao = dados_proposta.get('data_negociacao', '')
            if data_negociacao:
                pdf.cell(0, 6, f"Data da negociação: {sanitize_text(str(data_negociacao))}", 0, 1)

            pdf.ln(5)


        # Adiciona a seção de data e assinaturas
        pdf.ln(7)
        today = datetime.date.today()
        month_names = {
            1: "janeiro", 2: "fevereiro", 3: "março", 4: "abril", 5: "maio", 6: "junho",
            7: "julho", 8: "agosto", 9: "setembro", 10: "outubro", 11: "novembro", 12: "dezembro"
        }
        
        current_city_state = f"{sanitize_text(dados.get('comprador_cidade_pf', ''))}/{sanitize_text(dados.get('comprador_estado_pf', ''))}"
        pdf.cell(0, 6, f"{current_city_state}, {today.day} de {month_names[today.month]} de {today.year}", 0, 1, 'C')
        pdf.ln(7)

        pdf.cell(0, 0, "_" * 50, 0, 1, 'C')
        pdf.ln(3)
        pdf.cell(0, 4, sanitize_text("Assinatura do(a) Comprador(a)"), 0, 1, 'C')
        pdf.ln(7)

        pdf.cell(0, 6, f"Autorizado em: {today.strftime('%d/%m/%Y')}", 0, 1, 'C')
        pdf.ln(7)

        pdf.cell(0, 0, "_" * 50, 0, 1, 'C')
        pdf.ln(3)
        pdf.cell(0, 4, sanitize_text("Imobiliária Celeste"), 0, 1, 'C')
        
        if dependentes:
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 16)
            pdf.cell(0, 10, sanitize_text("LISTAGEM DE DEPENDENTES"), 0, 1, "C")
            pdf.ln(5)

            pdf.set_font("Helvetica", "", 10)
            for i, dep in enumerate(dependentes):
                pdf.set_font("Helvetica", "B", 10)
                pdf.cell(0, 6, f"DEPENDENTE {i+1}:", 0, 1, "L")
                pdf.set_font("Helvetica", "", 9)
                pdf.cell(0, 5, f"Nome: {sanitize_text(dep.get('nome', ''))}", 0, 1)
                pdf.cell(0, 5, f"CPF: {sanitize_text(formatar_cpf(dep.get('cpf', '')))}", 0, 1)
                pdf.cell(0, 5, f"Telefone Comercial: {sanitize_text(formatar_telefone(dep.get('telefone_comercial', '')))}", 0, 1)
                pdf.cell(0, 5, f"Celular: {sanitize_text(formatar_telefone(dep.get('celular', '')))}", 0, 1)
                pdf.cell(0, 5, f"E-mail: {sanitize_text(dep.get('email', ''))}", 0, 1)
                pdf.cell(0, 5, f"Grau de Parentesco: {sanitize_text(dep.get('grau_parentesco', ''))}", 0, 1)
                pdf.ln(3)
        
        pdf_output = pdf.output(dest='S').encode('latin-1')
        b64_pdf = base64.b64encode(pdf_output).decode('utf-8')
        return b64_pdf
    except Exception as e:
        st.error(f"Erro ao gerar PDF: {str(e)}")
        return None

def gerar_pdf_pj(dados, dependentes=None, dados_proposta=None):
    """
    Gera um arquivo PDF com os dados da Ficha Cadastral de Pessoa Jurídica.
    """
    try:
        pdf = FPDF()
        pdf.add_page()
        
        # Usando fontes padrão do FPDF que suportam caracteres acentuados
        pdf.set_font('Helvetica', '', 10)
        
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, sanitize_text("Ficha Cadastral Pessoa Jurídica - Cessão e Transferência de Direitos"), 0, 1, "C")
        pdf.ln(8)

        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, sanitize_text("Dados do Empreendimento e Imobiliária"), 0, 1, "L")
        pdf.set_font("Helvetica", "", 10)
        for key_suffix in ["empreendimento", "corretor", "imobiliaria", "qd", "lt", "ativo", "quitado"]:
            key = f"{key_suffix}_pj"
            value = dados.get(key, '')
            if value and sanitize_text(value):
                pdf.cell(0, 6, f"{sanitize_text(key_suffix.replace('_', ' ').title())}: {sanitize_text(str(value))}", 0, 1)
        pdf.ln(3)

        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, sanitize_text("Dados do COMPRADOR(A)"), 0, 1, "L")
        pdf.set_font("Helvetica", "", 10)
        
        razao_social_comprador_pj = dados.get('comprador_razao_social_pj', '')
        nome_fantasia_comprador_pj = dados.get('comprador_nome_fantasia_pj', '')
        if razao_social_comprador_pj or nome_fantasia_comprador_pj:
            pdf.cell(95, 6, f"Razão Social: {sanitize_text(razao_social_comprador_pj)}", 0, 0)
            pdf.cell(0, 6, f"Nome Fantasia: {sanitize_text(nome_fantasia_comprador_pj)}", 0, 1)
        
        inscricao_estadual_comprador_pj = dados.get('comprador_inscricao_estadual_pj', '')
        if inscricao_estadual_comprador_pj:
            pdf.cell(0, 6, f"Inscrição Estadual: {sanitize_text(inscricao_estadual_comprador_pj)}", 0, 1)

        fone_residencial_comprador_pj = dados.get('comprador_fone_residencial_pj', '')
        fone_comercial_comprador_pj = dados.get('comprador_fone_comercial_pj', '')
        if fone_residencial_comprador_pj or fone_comercial_comprador_pj:
            pdf.cell(95, 6, f"Fone Residencial: {sanitize_text(formatar_telefone(fone_residencial_comprador_pj))}", 0, 0)
            pdf.cell(0, 6, f"Fone Comercial: {sanitize_text(formatar_telefone(fone_comercial_comprador_pj))}", 0, 1)

        celular_comprador_pj = dados.get('comprador_celular_pj', '')
        email_comprador_pj = dados.get('comprador_email_pj', '')
        if celular_comprador_pj or email_comprador_pj:
            pdf.cell(95, 6, f"Celular: {sanitize_text(formatar_telefone(celular_comprador_pj))}", 0, 0)
            pdf.cell(0, 6, f"E-mail: {sanitize_text(email_comprador_pj)}", 0, 1)

        endereco_res_comercial_comprador_pj = dados.get('comprador_end_residencial_comercial_pj', '')
        numero_comprador_pj = dados.get('comprador_numero_pj', '')
        if endereco_res_comercial_comprador_pj:
            endereco_linha_pj = f"Endereço Residencial/Comercial: {sanitize_text(endereco_res_comercial_comprador_pj)}"
            if numero_comprador_pj:
                endereco_linha_pj += f", Nº {sanitize_text(numero_comprador_pj)}"
            pdf.cell(0, 6, endereco_linha_pj, 0, 1)

        bairro_comprador_pj = dados.get('comprador_bairro_pj', '')
        cidade_comprador_pj = dados.get('comprador_cidade_pj', '')
        estado_comprador_pj = dados.get('comprador_estado_pj', '')
        cep_comprador_pj = dados.get('comprador_cep_pj', '')

        if bairro_comprador_pj or cidade_comprador_pj or estado_comprador_pj or cep_comprador_pj:
            if bairro_comprador_pj:
                pdf.cell(95, 6, f"Bairro: {sanitize_text(bairro_comprador_pj)}", 0, 0)
            if cidade_comprador_pj and estado_comprador_pj:
                pdf.cell(0, 6, f"Cidade/Estado: {sanitize_text(cidade_comprador_pj)}/{sanitize_text(estado_comprador_pj)}", 0, 1)
            elif bairro_comprador_pj: 
                pdf.ln(6)
            
            if cep_comprador_pj:
                pdf.cell(0, 6, f"CEP: {sanitize_text(cep_comprador_pj)}", 0, 1)
        
        pdf.ln(3)

        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, sanitize_text("Dados do REPRESENTANTE"), 0, 1, "L")
        pdf.set_font("Helvetica", "", 10)

        nome_representante = dados.get('representante_nome_pj', '')
        profissao_representante = dados.get('representante_profissao_pj', '')
        if nome_representante or profissao_representante:
            pdf.cell(95, 6, f"Nome Completo Representante: {sanitize_text(nome_representante)}", 0, 0)
            pdf.cell(0, 6, f"Profissão Representante: {sanitize_text(profissao_representante)}", 0, 1)

        nacionalidade_representante = dados.get('representante_nacionalidade_pj', '')
        if nacionalidade_representante:
            pdf.cell(0, 6, f"Nacionalidade Representante: {sanitize_text(nacionalidade_representante)}", 0, 1)

        fone_residencial_representante = dados.get('representante_fone_residencial_pj', '')
        fone_comercial_representante = dados.get('representante_fone_comercial_pj', '')
        if fone_residencial_representante or fone_comercial_representante:
            pdf.cell(95, 6, f"Fone Residencial: {sanitize_text(formatar_telefone(fone_residencial_representante))}", 0, 0)
            pdf.cell(0, 6, f"Fone Comercial: {sanitize_text(formatar_telefone(fone_comercial_representante))}", 0, 1)

        celular_representante = dados.get('representante_celular_pj', '')
        email_representante = dados.get('representante_email_pj', '')
        if celular_representante or email_representante:
            pdf.cell(95, 6, f"Celular: {sanitize_text(formatar_telefone(celular_representante))}", 0, 0)
            pdf.cell(0, 6, f"E-mail: {sanitize_text(email_representante)}", 0, 1)

        endereco_res_representante = dados.get('representante_end_residencial_pj', '')
        numero_representante = dados.get('representante_numero_pj', '')
        if endereco_res_representante:
            endereco_linha_rep = f"Endereço Residencial: {sanitize_text(endereco_res_representante)}"
            if numero_representante:
                endereco_linha_rep += f", Nº {sanitize_text(numero_representante)}"
            pdf.cell(0, 6, endereco_linha_rep, 0, 1)

        bairro_representante = dados.get('representante_bairro_pj', '')
        cidade_representante = dados.get('representante_cidade_pj', '')
        estado_representante = dados.get('representante_estado_pj', '')
        cep_representante = dados.get('representante_cep_pj', '')

        if bairro_representante or cidade_representante or estado_representante or cep_representante:
            if bairro_representante:
                pdf.cell(95, 6, f"Bairro: {sanitize_text(bairro_representante)}", 0, 0)
            if cidade_representante and estado_representante:
                pdf.cell(0, 6, f"Cidade/Estado: {sanitize_text(cidade_representante)}/{sanitize_text(estado_representante)}", 0, 1)
            elif bairro_representante: 
                pdf.ln(6)
            
            if cep_representante:
                pdf.cell(0, 6, f"CEP: {sanitize_text(cep_representante)}", 0, 1)
        
        pdf.ln(3)
        
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, sanitize_text("Dados do CÔNJUGE/SÓCIO(A)"), 0, 1, "L")
        pdf.set_font("Helvetica", "", 10)

        nome_conjuge_pj = dados.get('conjuge_nome_pj', '')
        profissao_conjuge_pj = dados.get('conjuge_profissao_pj', '')
        if nome_conjuge_pj or profissao_conjuge_pj:
            pdf.cell(95, 6, f"Nome Completo Cônjuge/Sócio(a) PJ: {sanitize_text(nome_conjuge_pj)}", 0, 0)
            pdf.cell(0, 6, f"Profissão Cônjuge/Sócio(a) PJ: {sanitize_text(profissao_conjuge_pj)}", 0, 1)

        nacionalidade_conjuge_pj = dados.get('conjuge_nacionalidade_pj', '')
        if nacionalidade_conjuge_pj:
            pdf.cell(0, 6, f"Nacionalidade Cônjuge/Sócio(a) PJ: {sanitize_text(nacionalidade_conjuge_pj)}", 0, 1)

        fone_residencial_conjuge_pj = dados.get('conjuge_fone_residencial_pj', '')
        fone_comercial_conjuge_pj = dados.get('conjuge_fone_comercial_pj', '')
        if fone_residencial_conjuge_pj or fone_comercial_conjuge_pj:
            pdf.cell(95, 6, f"Fone Residencial: {sanitize_text(formatar_telefone(fone_residencial_conjuge_pj))}", 0, 0)
            pdf.cell(0, 6, f"Fone Comercial: {sanitize_text(formatar_telefone(fone_comercial_conjuge_pj))}", 0, 1)

        celular_conjuge_pj = dados.get('conjuge_celular_pj', '')
        email_conjuge_pj = dados.get('conjuge_email_pj', '')
        if celular_conjuge_pj or email_conjuge_pj:
            pdf.cell(95, 6, f"Celular: {sanitize_text(formatar_telefone(celular_conjuge_pj))}", 0, 0)
            pdf.cell(0, 6, f"E-mail: {sanitize_text(email_conjuge_pj)}", 0, 1)

        endereco_res_conjuge_pj = dados.get('conjuge_end_residencial_pj', '')
        numero_conjuge_pj = dados.get('conjuge_numero_pj', '')
        if endereco_res_conjuge_pj:
            endereco_linha_conjuge_pj = f"Endereço Residencial: {sanitize_text(endereco_res_conjuge_pj)}"
            if numero_conjuge_pj:
                endereco_linha_conjuge_pj += f", Nº {sanitize_text(numero_conjuge_pj)}"
            pdf.cell(0, 6, endereco_linha_conjuge_pj, 0, 1)

        bairro_conjuge_pj = dados.get('conjuge_bairro_pj', '')
        cidade_conjuge_pj = dados.get('conjuge_cidade_pj', '')
        estado_conjuge_pj = dados.get('conjuge_estado_pj', '')
        cep_conjuge_pj = dados.get('conjuge_cep_pj', '')

        if bairro_conjuge_pj or cidade_conjuge_pj or estado_conjuge_pj or cep_conjuge_pj:
            if bairro_conjuge_pj:
                pdf.cell(95, 6, f"Bairro: {sanitize_text(bairro_conjuge_pj)}", 0, 0)
            if cidade_conjuge_pj and estado_conjuge_pj:
                pdf.cell(0, 6, f"Cidade/Estado: {sanitize_text(cidade_conjuge_pj)}/{sanitize_text(estado_conjuge_pj)}", 0, 1)
            elif bairro_conjuge_pj: 
                pdf.ln(6)
            
            if cep_conjuge_pj:
                pdf.cell(0, 6, f"CEP: {sanitize_text(cep_conjuge_pj)}", 0, 1)
        
        pdf.ln(3)

        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, sanitize_text("DOCUMENTOS NECESSÁRIAS:"), 0, 1)
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 4.5, sanitize_text("DA EMPRESA: CONTRATO SOCIAL E ALTERAÇÕES, COMPROVANTE DE ENDEREÇO, DECLARAÇÃO DE FATURAMENTO;"), 0, "L")
        pdf.multi_cell(0, 4.5, sanitize_text("DOS SÓCIOS E SEUS CÔNJUGES: CNH; RG e CPF, Comprovante do Estado Civil, Comprovante de Endereço, Comprovante de Renda, CND da Prefeitura e Nada Consta do Condomínio ou Associação."), 0, "L")
        pdf.ln(3)

        condomino_indicado = dados.get('condomino_indicado_pj', '')
        if condomino_indicado and sanitize_text(condomino_indicado):
            pdf.ln(5)
            pdf.set_font("Helvetica", "B", 10)
            pdf.multi_cell(0, 6, sanitize_text("No caso de Condomínio ou Loteamento Fechado, quando a empresa possuir mais de um(a) sócio(a) não casados entre si e nem conviventes, é necessário indicar qual do(a)(s) sócio(a)(s) será o(a) condômino(a):"), 0, 'L')
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(0, 6, f"Indique aqui quem será o(a) condômino(a): {sanitize_text(condomino_indicado)}", 0, 1)
            pdf.ln(3)

        # Inserir Dados da Proposta em uma nova página, se houver
        if dados_proposta:
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 16)
            pdf.cell(0, 10, sanitize_text("Dados da Proposta"), 0, 1, "C")
            pdf.ln(5)
            pdf.set_font("Helvetica", "", 10)

            # Valor do imóvel e Forma de pagamento (imóvel)
            valor_imovel = dados_proposta.get('valor_imovel', '')
            forma_pagamento_imovel = dados_proposta.get('forma_pagamento_imovel', '')
            if valor_imovel or forma_pagamento_imovel:
                # --- CORREÇÃO MULTICELL EM COLUNA ---
                col1_text = f"Valor do imóvel: {sanitize_text(valor_imovel)}"
                col2_text = f"Forma de pagamento (Imóvel): {sanitize_text(forma_pagamento_imovel)}"
                pdf_two_columns(pdf, col1_text, 80, col2_text, 110)

            # Valor dos honorários e Forma de pagamento (honorários)
            valor_honorarios = dados_proposta.get('valor_honorarios', '')
            forma_pagamento_honorarios = dados_proposta.get('forma_pagamento_honorarios', '')
            if valor_honorarios or forma_pagamento_honorarios:
                # --- CORREÇÃO MULTICELL EM COLUNA ---
                col1_text = f"Valor dos honorários: {sanitize_text(valor_honorarios)}"
                col2_text = f"Forma de pagamento (Honorários): {sanitize_text(forma_pagamento_honorarios)}"
                pdf_two_columns(pdf, col1_text, 80, col2_text, 110)

            # Conta Bancária para transferência
            conta_bancaria = dados_proposta.get('conta_bancaria', '')
            if conta_bancaria:
                pdf.cell(0, 6, f"Conta Bancária para transferência: {sanitize_text(conta_bancaria)}", 0, 1)

            # Valor para declaração de imposto de renda
            valor_ir = dados_proposta.get('valor_ir', '')
            if valor_ir:
                pdf.cell(0, 6, f"Valor para declaração de imposto de renda: {sanitize_text(valor_ir)}", 0, 1)
            
            # Valor para escritura
            valor_escritura = dados_proposta.get('valor_escritura', '')
            if valor_escritura:
                pdf.cell(0, 6, f"Valor para escritura: {sanitize_text(valor_escritura)}", 0, 1)

            # Observações
            observacoes_proposta = dados_proposta.get('observacoes', '')
            if observacoes_proposta:
                pdf.multi_cell(0, 6, f"Observações: {sanitize_text(observacoes_proposta)}", 0, "L")
            
            # Corretor(a) angariador e Corretor(a) vendedor(a)
            corretor_angariador = dados_proposta.get('corretor_angariador', '')
            corretor_vendedor = dados_proposta.get('corretor_vendedor', '')
            if corretor_angariador or corretor_vendedor:
                pdf.cell(95, 6, f"Corretor(a) angariador: {sanitize_text(corretor_angariador)}", 0, 0)
                pdf.cell(0, 6, f"Corretor(a) vendedor(a): {sanitize_text(corretor_vendedor)}", 0, 1)

            # Data da negociação
            data_negociacao = dados_proposta.get('data_negociacao', '')
            if data_negociacao:
                pdf.cell(0, 6, f"Data da negociação: {sanitize_text(str(data_negociacao))}", 0, 1)

            pdf.ln(5)

        # Adiciona a seção de data e assinaturas
        pdf.ln(7)
        today = datetime.date.today()
        month_names = {
            1: "janeiro", 2: "fevereiro", 3: "março", 4: "abril", 5: "maio", 6: "junho",
            7: "julho", 8: "agosto", 9: "setembro", 10: "outubro", 11: "novembro", 12: "dezembro"
        }
        
        current_city_state = f"{sanitize_text(dados.get('comprador_cidade_pj', ''))}/{sanitize_text(dados.get('comprador_estado_pj', ''))}"
        pdf.cell(0, 6, f"{current_city_state}, {today.day} de {month_names[today.month]} de {today.year}", 0, 1, 'C')
        pdf.ln(7)

        pdf.cell(0, 0, "_" * 50, 0, 1, 'C')
        pdf.ln(3)
        # Para PJ, o ideal seria "Assinatura do(a) Representante Legal" ou similar.
        pdf.cell(0, 4, sanitize_text("Assinatura do(a) Comprador(a)"), 0, 1, 'C')
        pdf.ln(7)

        pdf.cell(0, 6, f"Autorizado em: {today.strftime('%d/%m/%Y')}", 0, 1, 'C')
        pdf.ln(7)

        pdf.cell(0, 0, "_" * 50, 0, 1, 'C')
        pdf.ln(3)
        pdf.cell(0, 4, sanitize_text("Imobiliária Celeste"), 0, 1, 'C')

        if dependentes:
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 16)
            pdf.cell(0, 10, sanitize_text("LISTAGEM DE DEPENDENTES"), 0, 1, "C")
            pdf.ln(5)

            pdf.set_font("Helvetica", "", 10)
            for i, dep in enumerate(dependentes):
                pdf.set_font("Helvetica", "B", 10)
                pdf.cell(0, 6, f"DEPENDENTE {i+1}:", 0, 1, "L")
                pdf.set_font("Helvetica", "", 9)
                pdf.cell(0, 5, f"Nome: {sanitize_text(dep.get('nome', ''))}", 0, 1)
                pdf.cell(0, 5, f"CPF: {sanitize_text(formatar_cpf(dep.get('cpf', '')))}", 0, 1)
                pdf.cell(0, 5, f"Telefone Comercial: {sanitize_text(formatar_telefone(dep.get('telefone_comercial', '')))}", 0, 1)
                pdf.cell(0, 5, f"Celular: {sanitize_text(formatar_telefone(dep.get('celular', '')))}", 0, 1)
                pdf.cell(0, 5, f"E-mail: {sanitize_text(dep.get('email', ''))}", 0, 1)
                pdf.cell(0, 5, f"Grau de Parentesco: {sanitize_text(dep.get('grau_parentesco', ''))}", 0, 1)
                pdf.ln(3)
        
        pdf_output = pdf.output(dest='S').encode('latin-1')
        b64_pdf = base64.b64encode(pdf_output).decode('utf-8')
        return b64_pdf
    except Exception as e:
        st.error(f"Erro ao gerar PDF: {str(e)}")
        return None
```
```eof
