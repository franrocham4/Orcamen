import logging
import os
import re
from datetime import datetime, date
from decimal import Decimal, InvalidOperation

import openpyxl
import pandas as pd

logger = logging.getLogger(__name__)

CANDIDATOS_COLUNAS = {
    'nome': ['nome', 'fornecedor', 'beneficiário', 'beneficiario', 'razão social', 'razao social',
             'empresa', 'colaborador', 'funcionário', 'funcionario'],
    'valor': ['valor', 'valor total', 'total', 'r$', 'montante', 'valor bruto', 'vlr', 'vl total'],
    'valor_pago': ['valor pago', 'vl pago', 'pago', 'valor pg', 'vlr pago'],
    'valor_pendente': ['valor pendente', 'pendente', 'saldo', 'restante', 'a pagar', 'saldo devedor'],
    'data_vencimento': ['vencimento', 'data vencimento', 'data de vencimento', 'dt vencimento', 'venc', 'data venc'],
    'data_pagamento': ['data pagamento', 'dt pagamento', 'data de pagamento', 'data pg', 'pago em'],
    'mes_referencia': ['mês', 'mes', 'mês ref', 'mes ref', 'mês referência', 'competência', 'competencia',
                       'período', 'periodo', 'ref'],
    'status': ['status', 'situação', 'situacao', 'estado', 'situação pagamento'],
    'categoria': ['categoria', 'tipo', 'classificação', 'classificacao', 'natureza', 'centro de custo', 'cc'],
    'observacoes': ['observações', 'observacoes', 'obs', 'observação', 'notas', 'comentários', 'comentarios'],
    'responsavel': ['responsável', 'responsavel', 'resp', 'usuario', 'usuário', 'operador'],
    'banco': ['banco', 'bank', 'instituição', 'instituicao'],
    'forma_pagamento': ['forma pagamento', 'forma de pagamento', 'tipo pagamento', 'modalidade', 'pix', 'ted', 'boleto'],
    'numero_nf': ['nf', 'nota fiscal', 'número nf', 'num nf', 'invoice', 'nf-e'],
    'descricao': ['descrição', 'descricao', 'historico', 'histórico', 'memo'],
    'referencia': ['referência', 'referencia', 'código', 'codigo', 'id', 'número', 'numero'],
    'competencia': ['competência', 'competencia'],
    'fornecedor': ['fornecedor', 'vendor', 'prestador'],
}

MAPEAMENTO_STATUS = {
    'pago': ['pago', 'pg', '✓', 'sim', 'yes', 'paid', 'quitado', 'liquidado', 's'],
    'pendente': ['pendente', 'aberto', 'não', 'nao', 'no', 'pending', 'a pagar', 'em aberto'],
    'atrasado': ['atrasado', 'vencido', 'late', 'overdue', 'em atraso'],
    'cancelado': ['cancelado', 'cancelled', 'canceled', 'estornado', 'anulado'],
}


def parse_decimal(valor):
    if valor is None:
        return None
    if isinstance(valor, (int, float)):
        try:
            return Decimal(str(round(float(valor), 2)))
        except (InvalidOperation, ValueError):
            return None
    if isinstance(valor, Decimal):
        return valor

    texto = str(valor).strip()
    texto = re.sub(r'[R$\s]', '', texto)
    # Brazilian format: 1.234,56 → remove thousand-sep dots, replace comma decimal
    if re.match(r'^\d{1,3}(\.\d{3})*,\d{2}$', texto):
        texto = texto.replace('.', '').replace(',', '.')
    elif ',' in texto:
        # Other comma-decimal format (e.g. 1234,56): replace comma with dot
        texto = texto.replace(',', '.')
    else:
        # Remove all but the last dot (handles accidental extra dots)
        dot_count = texto.count('.')
        if dot_count > 1:
            texto = texto.replace('.', '', dot_count - 1)
    try:
        return Decimal(texto)
    except (InvalidOperation, ValueError):
        return None


def parse_date(valor):
    if valor is None:
        return None
    if isinstance(valor, (date, datetime)):
        return valor.date() if isinstance(valor, datetime) else valor

    texto = str(valor).strip()
    formatos = ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%d/%m/%y', '%m/%Y']
    for fmt in formatos:
        try:
            return datetime.strptime(texto, fmt).date()
        except ValueError:
            continue
    return None


def normalizar_status(valor):
    if not valor:
        return 'pendente'
    texto = str(valor).strip().lower()
    for status, candidatos in MAPEAMENTO_STATUS.items():
        if texto in candidatos:
            return status
    return 'pendente'


def mapear_colunas(colunas_planilha):
    mapeamento = {}
    colunas_normalizadas = {c.lower().strip(): c for c in colunas_planilha if c is not None}

    for campo, candidatos in CANDIDATOS_COLUNAS.items():
        for candidato in candidatos:
            if candidato in colunas_normalizadas:
                mapeamento[campo] = colunas_normalizadas[candidato]
                break

    return mapeamento


def processar_aba(df, nome_aba):
    from apps.pagamentos.models import Pagamento

    if df.empty:
        logger.info(f"  Aba '{nome_aba}' está vazia, ignorando.")
        return []

    df.columns = [str(c).strip() if c is not None else '' for c in df.columns]
    df = df[[c for c in df.columns if c and c != 'nan']]

    mapeamento = mapear_colunas(df.columns)
    logger.info(f"  Aba '{nome_aba}': {len(df)} linhas, mapeamento: {mapeamento}")

    campos_mapeados = set(mapeamento.values())
    registros = []

    for idx, row in df.iterrows():
        valores = [v for v in row.values if pd.notna(v) and str(v).strip()]
        if not valores:
            continue

        pagamento_dict = {
            'linha_planilha': idx + 2,
            'aba_planilha': nome_aba,
            'dados_extras': {},
        }

        for campo, coluna in mapeamento.items():
            valor_bruto = row.get(coluna)
            if pd.isna(valor_bruto):
                pagamento_dict[campo] = None
                continue

            if campo in ('valor', 'valor_pago', 'valor_pendente'):
                pagamento_dict[campo] = parse_decimal(valor_bruto)
            elif campo in ('data_vencimento', 'data_pagamento'):
                pagamento_dict[campo] = parse_date(valor_bruto)
            elif campo == 'status':
                pagamento_dict[campo] = normalizar_status(valor_bruto)
            else:
                v = str(valor_bruto).strip() if pd.notna(valor_bruto) else None
                pagamento_dict[campo] = v if v else None

        if 'status' not in pagamento_dict:
            pagamento_dict['status'] = 'pendente'

        for coluna in df.columns:
            if coluna not in campos_mapeados:
                valor_extra = row.get(coluna)
                if pd.notna(valor_extra) and str(valor_extra).strip():
                    pagamento_dict['dados_extras'][coluna] = str(valor_extra)

        registros.append(pagamento_dict)

    return registros


def processar_excel(caminho_arquivo):
    from apps.pagamentos.models import Pagamento, ImportacaoExcel

    logger.info(f"📊 Iniciando processamento: {caminho_arquivo}")

    if not os.path.exists(caminho_arquivo):
        msg = f"Arquivo não encontrado: {caminho_arquivo}"
        logger.error(msg)
        ImportacaoExcel.objects.create(
            arquivo_nome=os.path.basename(caminho_arquivo),
            sucesso=False,
            mensagem=msg,
        )
        return {'sucesso': False, 'mensagem': msg, 'registros': 0}

    try:
        logger.info("  Lendo abas da planilha...")
        abas = pd.read_excel(
            caminho_arquivo,
            engine='openpyxl',
            sheet_name=None,
            dtype=str,
        )
        logger.info(f"  Abas encontradas: {list(abas.keys())}")

        todos_registros = []
        abas_processadas = []

        for nome_aba, df in abas.items():
            logger.info(f"  Processando aba: '{nome_aba}'")
            registros = processar_aba(df, nome_aba)
            todos_registros.extend(registros)
            if registros:
                abas_processadas.append(nome_aba)

        logger.info(f"  Limpando {Pagamento.objects.count()} registros antigos...")
        Pagamento.objects.all().delete()

        objetos = [Pagamento(**r) for r in todos_registros]
        logger.info(f"  Inserindo {len(objetos)} registros...")

        Pagamento.objects.bulk_create(objetos, batch_size=500)

        mensagem = (
            f"Importação concluída: {len(objetos)} registros de "
            f"{len(abas_processadas)} aba(s): {', '.join(abas_processadas)}"
        )
        logger.info(f"✅ {mensagem}")

        ImportacaoExcel.objects.create(
            arquivo_nome=os.path.basename(caminho_arquivo),
            registros_importados=len(objetos),
            sucesso=True,
            mensagem=mensagem,
            abas_processadas=abas_processadas,
        )

        return {
            'sucesso': True,
            'mensagem': mensagem,
            'registros': len(objetos),
            'abas': abas_processadas,
        }

    except Exception as e:
        msg = f"Erro ao processar Excel: {type(e).__name__}: {e}"
        logger.error(msg, exc_info=True)
        ImportacaoExcel.objects.create(
            arquivo_nome=os.path.basename(caminho_arquivo),
            sucesso=False,
            mensagem=msg,
        )
        return {'sucesso': False, 'mensagem': msg, 'registros': 0}
