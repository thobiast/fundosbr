#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para mostrar dados de fundos de investimento.

Busca dados do site da CVM
"""

import argparse
import datetime
import logging
import os
import sys


DIR_PATH = os.path.dirname(os.path.realpath(__file__))
sys.path.append(DIR_PATH)
from fundosbrlib import create_dir
from fundosbrlib import download_file
from fundosbrlib import msg
from fundosbrlib import setup_logging

import pandas as pd

URL_CADASTRAL_DIARIO = "http://dados.cvm.gov.br/dados/FI/CAD/DADOS"
URL_INFORME_DIARIO = "http://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS"

# Diretorio para guardar os arquivos csv
DADOS_DIR = "/tmp/fundosbr_dados"


##############################################################################
# Parse da linha de comando
##############################################################################
def parse_parameters():
    """Command line parser."""
    epilog = """
    Example of use:
        %(prog)s busca -h
        %(prog)s busca -n verde
        %(prog)s busca -c 22.187.946/0001-41
        %(prog)s busca -n "ip participa" -t acoes
        %(prog)s informe -h
        %(prog)s informe 73.232.530/0001-39 -datainicio 202011 -datafim 202012
    """
    parser = argparse.ArgumentParser(
        description="Informacoes sobre fundos de investimentos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog,
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", dest="debug", help="debug flag"
    )
    # Adiciona opcoes dos subcomandos
    subparsers = parser.add_subparsers(title="Comandos", dest="command")

    # Busca fundo
    busca_parser = subparsers.add_parser("busca", help="Busca fundo")
    busca_parser.add_argument("-n", dest="name", help="Nome do fundo")
    busca_parser.add_argument(
        "-t",
        dest="type",
        choices=["acoes", "multimercado", "cambial", "rendafixa"],
        help="Tipo do fundo",
    )
    busca_parser.add_argument("-c", dest="cnpj", help="CNPJ do fundo")
    busca_parser.add_argument(
        "-a", dest="all", action="store_true", help="Busca fundos cancelados tambem"
    )
    busca_parser.set_defaults(func=cmd_busca_fundo)

    # Informes dos fundos
    informe_parser = subparsers.add_parser("informe", help="Informes fundo")
    informe_parser.add_argument(
        "-datainicio", type=int, dest="datainicio", help="Data inicio (YYYYMM)"
    )
    informe_parser.add_argument(
        "-datafim", type=int, dest="datafim", help="Data fim (YYYYMM)"
    )
    informe_parser.add_argument(
        "-m",
        "--mensal",
        dest="mensal",
        action="store_true",
        help="Mostra estatistica mensal",
    )
    informe_parser.add_argument("cnpj", help="CNPJ do fundo")
    informe_parser.set_defaults(func=cmd_informes_fundo)

    # Compara fundos
    compara_parser = subparsers.add_parser("compara", help="Comparas fundos")
    compara_parser.add_argument(
        "-datainicio", type=int, dest="datainicio", help="Data inicio (YYYYMM)"
    )
    compara_parser.add_argument(
        "-datafim", type=int, dest="datafim", help="Data fim (YYYYMM)"
    )
    compara_parser.add_argument(
        "-m",
        "--mensal",
        dest="mensal",
        action="store_true",
        help="Mostra estatistica mensal",
    )
    compara_parser.add_argument("cnpj", help="CNPJ do fundo")
    compara_parser.set_defaults(func=cmd_compara_fundo)

    # Rank dos fundos
    rank_parser = subparsers.add_parser("rank", help="Rank fundos")
    rank_parser.add_argument(
        "tipo",
        choices=["acoes", "multimercado", "cambial", "rendafixa"],
        help="Tipo do fundo",
    )
    rank_parser.add_argument(
        "-top", type=int, default=10, dest="top", help="Numero de fundos para retornar"
    )
    rank_type_group = rank_parser.add_mutually_exclusive_group(required=True)
    rank_type_group.add_argument(
        "-c",
        "--cotistas",
        dest="cotistas",
        action="store_true",
        help="Rank por numero de cotistas",
    )
    rank_type_group.add_argument(
        "-p",
        "--pl",
        dest="patrimonio",
        action="store_true",
        help="Rank por patrimonio liquido",
    )
    rank_parser.set_defaults(func=cmd_rank_fundo)

    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit(0)

    return parser.parse_args()


class Cadastral:
    """Class com informacoes cadastral dos fundos."""

    csv_columns = {
        "CNPJ_FUNDO": "CNPJ do fundo",
        "DENOM_SOCIAL": "Denominação Social",
        "DT_REG": "Data de registro",
        "DT_CONST": "Data de constituição",
        "DT_CANCEL": "Data de cancelamento",
        "SIT": "Situação",
        "DT_INI_SIT": "Data início da situação",
        "DT_INI_ATIV": "Data de início de atividade",
        "DT_INI_EXERC": "Data início do exercício social",
        "DT_FIM_EXERC": "Data fim do exercício social",
        "CLASSE": "Classe",
        "DT_INI_CLASSE": "Data de início na classe",
        "RENTAB_FUNDO": "Forma de rentabilidade do fundo (indicador de desempenho)",
        "CONDOM": "Forma de condomínio",
        "FUNDO_COTAS": "Indica se é fundo de cotas",
        "FUNDO_EXCLUSIVO": "Indica se é fundo exclusivo",
        "TRIB_LPRAZO": "Indica se possui tributação de longo prazo",
        "INVEST_QUALIF": "Indica se é destinado a investidores qualificados",
        "TAXA_PERFM": "Taxa de performance",
        "INF_TAXA_PERFM": "Informações Adicionais (Taxa de performance)",
        "TAXA_ADM": "Taxa de administração",
        "INF_TAXA_ADM": "Informações Adicionais (Taxa de administração)",
        "VL_PATRIM_LIQ": "Valor do patrimônio líquido",
        "DT_PATRIM_LIQ": "Data do patrimônio líquido",
        "DIRETOR": "Nome do Diretor Responsável",
        "CNPJ_ADMIN": "CNPJ do Administrador",
        "ADMIN": "Nome do Administrador",
        "PF_PJ_GESTOR": "Indica se o gestor é pessoa física ou jurídica",
        "CPF_CNPJ_GESTOR": "Informa o código de identificação do gestor pessoa física ou jurídica",
        "GESTOR": "Nome do Gestor",
        "CNPJ_AUDITOR": "CNPJ do Auditor",
        "AUDITOR": "Nome do Auditor",
        "CNPJ_CUSTODIANTE": "CNPJ do Custodiante",
        "CUSTODIANTE": "Nome do Custodiante",
        "CNPJ_CONTROLADOR": "CNPJ do Controlador",
        "CONTROLADOR": "Nome do Controlador",
    }

    def __init__(self):
        """Initialize cadastral class."""
        self.pd_df = None
        self.filename = None

    def download_inf_cadastral(self):
        """Download do arquivo cadastral mais recente."""
        # Tenta baixar um arquivo cadastral dos ultimos 30 dias
        for num_d_ago in range(1, 30):
            data_to_download = self.days_ago(num_d_ago)
            if datetime.datetime.strptime(data_to_download, "%Y%m%d").weekday() > 4:
                log.debug("Pulando data %s. Final de semana", data_to_download)
                continue

            file_name = "inf_cadastral_fi_{}.csv".format(data_to_download)
            url = "{}/{}".format(URL_CADASTRAL_DIARIO, file_name)
            local_file = "{}/{}".format(DADOS_DIR, file_name)

            if os.path.exists(local_file):
                log.debug("Arquivo cadastral '%s' ja existe localmente", file_name)
                self.filename = local_file
            else:
                log.debug(
                    "Tentando baixar arquivo do dia: %s", (self.days_ago(num_d_ago))
                )
                res = download_file(url, local_file)
                if res.status_code == 404:
                    log.debug("Arquivo nao encontrado no site da cvm")
                elif res.status_code == 200:
                    log.debug("Arquivo baixado com sucesso: %s", file_name)
                    self.filename = local_file

            if self.filename:
                break

    def load_csv(self):
        """Cria o DataFrame com o arquivo csv."""
        log.debug("Carregando csv cadastral")
        create_dir(DADOS_DIR)
        self.download_inf_cadastral()
        self.pd_df = pd.read_csv(
            self.filename, sep=";", encoding="ISO-8859-1", index_col="CNPJ_FUNDO"
        )

    def busca_fundos(self, name=None, fundo_classe=None, all_situacoes=False):
        """
        Busca informacoes sobre o fundos.

        Parametros:
            name                  (str): Parte do nome do fundo
            fundo_classe          (str): Classe do fundo (acoes, mm, fixa e cambial)
            all_situacoes  (True/False): Remove fundos com situacao cancelada

        Retorna um dataframe
        """
        # Filtra fundo pelo nome
        if name:
            fundo_df = self.pd_df[
                self.pd_df["DENOM_SOCIAL"].str.contains(name, na=False, case=False)
            ]
        else:
            fundo_df = self.pd_df

        f_classe_dic = {
            "acoes": "Fundo de Ações",
            "multimercado": "Fundo Multimercado",
            "cambial": "Fundo Cambial",
            "rendafixa": "Fundo de Renda Fixa",
        }
        # Filtra fundo por classe
        if fundo_classe:
            fundo_df = fundo_df.loc[fundo_df["CLASSE"] == f_classe_dic[fundo_classe]]

        # Remove fundos cancelados
        if not all_situacoes:
            fundo_df = fundo_df.loc[~(fundo_df["SIT"] == "CANCELADA")]

        return fundo_df

    def busca_fundo_cnpj(self, cnpj):
        """Retorna dataframe de um fundo."""
        if not isinstance(self.pd_df, pd.DataFrame):
            self.load_csv()

        # No arquivo cadastral alguns fundos tem o mesmo cnpj.
        # Retorna o primeiro encontrado
        fundo_df = self.pd_df.loc[[cnpj], :]
        return fundo_df.iloc[0, :]

    def fundo_social_nome(self, cnpj):
        """Retorna o nome social do fundo."""
        return self.busca_fundo_cnpj(cnpj)["DENOM_SOCIAL"]

    def fundo_gestor_nome(self, cnpj):
        """Retorna o nome do gestor do fundo."""
        return self.busca_fundo_cnpj(cnpj)["GESTOR"]

    def mostra_detalhes_fundo(self, cnpj):
        """Mostra detalhes cadastral do fundo."""
        try:
            fundo_df = self.busca_fundo_cnpj(cnpj).copy()
        except KeyError:
            msg("red", "Erro: Fundo com cnpj {} nao encontrado".format(cnpj), 1)

        fundo_df.rename(index=self.csv_columns, inplace=True)
        for col in fundo_df.index:
            msg("cyan", col, end=": ")
            msg("nocolor", fundo_df.loc[col])

    @staticmethod
    def days_ago(days=0, fmt_day="%Y%m%d"):
        """
        Retorna data como string.

        Parametros:
            days        (int): Numero de dias para tras para retornar
            fmt_day     (str): Formato da data retornada
        """
        d_ago = datetime.datetime.now() - datetime.timedelta(days=days)
        return d_ago.strftime(fmt_day)


class Informe:
    """Class com os informes diario do fundo."""

    reais_format = "R${:,.2f}"
    csv_columns = {
        "CNPJ_FUNDO": "CNPJ do fundo",
        "DT_COMPTC": "Data de competencia do documento",
        "VL_TOTAL": "Valor total carteira",
        "VL_QUOTA": "Valor cota",
        "VL_PATRIM_LIQ": "Valor patrimonio liquido",
        "CAPTC_DIA": "Captacao dia",
        "RESG_DIA": "Resgate dia",
        "NR_COTST": "Numero cotistas",
    }

    def __init__(self):
        """Initialize informe class."""
        self.pd_df = pd.DataFrame()
        self.filenames = set()

    def download_informe_mensal(self, data):
        """
        Download do arquivo csv com informe mensal.

        Parametros:
            data     (int): Data para baixar o arquivo.
                            formato do arquivo da CVM (YYYYMM)
        """
        create_dir(DADOS_DIR)

        file_name = "inf_diario_fi_{}.csv".format(data)

        url = "{}/{}".format(URL_INFORME_DIARIO, file_name)
        local_file = "{}/{}".format(DADOS_DIR, file_name)

        if os.path.exists(local_file):
            log.debug("Arquivo informe '%s' ja existe localmente", file_name)
            self.filenames.add(local_file)
            return True

        log.debug("Tentando baixar arquivo do dia: %s", file_name)
        res = download_file(url, local_file)
        if res.status_code == 404:
            log.debug("Arquivo nao encontrado no site da cvm")
        elif res.status_code == 200:
            log.debug("Arquivo baixado com sucesso: %s", file_name)
            self.filenames.add(local_file)
            return True
        else:
            log.debug("download resposnse: %s", res)

        return False

    def load_informe_csv(self, cnpj=None):
        """
        Cria DataFrame com os dados dos arquivos csv de informe.

        Parametros:
            cnpj      (str): Cnpj do(s) fundo(s) para criar o DataFrame.
                             Cnpj(s) devem ser separados pelo caractere ','
                             Se nao especificado, cria com todos
        """
        cnpj_list = []
        if cnpj:
            cnpj_list.extend(cnpj.split(","))
        log.debug("cnpj: %s", cnpj_list)

        for file_mes in self.filenames:
            log.debug("pandas read_csv arquivo: %s", file_mes)
            informe_mensal = pd.read_csv(
                file_mes,
                sep=";",
                encoding="ISO-8859-1",
                index_col=["CNPJ_FUNDO", "DT_COMPTC"],
                parse_dates=True,
            )
            log.debug("Arquivo carregado com sucesso")
            if cnpj_list:
                try:
                    self.pd_df = pd.concat([self.pd_df, informe_mensal.loc[cnpj_list]])
                except KeyError:
                    msg("red", "Erro: cnpj(s) '{}' nao encontrado".format(cnpj_list), 1)
            else:
                self.pd_df = pd.concat([self.pd_df, informe_mensal])
            log.debug("DataFrame criado com sucesso")

    def remove_index_cnpj(self):
        """
        Retorna dataframe sem cnpj no index.

        Os methods dessa classe que mostram dados dos informes nao
        suportam mais de um cnpj. Retorna dataframe com apenas data de index
        """
        fundo_df = self.pd_df

        if "CNPJ_FUNDO" in fundo_df.index.names:
            if fundo_df.index.unique(level="CNPJ_FUNDO").size > 1:
                msg("red", "Erro: Este method nao suporta mais de um fundo", 1)
            fundo_df.reset_index(level="CNPJ_FUNDO", drop=True, inplace=True)

        return fundo_df

    def mostra_informe_fundo(self):
        """Mostra os informes de um fundo."""
        fundo_df = self.remove_index_cnpj()

        fundo_df.index.names = ["Data"]
        fundo_df.sort_index(inplace=True)

        # Adiciona no dataframe informacoes da rentabilidade diaria e acumulada da cota
        fundo_df["Rent. cota dia"] = fundo_df["VL_QUOTA"].pct_change()
        fundo_df["Rent. acumulada"] = (
            (1 + fundo_df["Rent. cota dia"]).cumprod() - 1
        ) * 100
        fundo_df["Rent. cota dia"] = fundo_df["Rent. cota dia"] * 100

        return fundo_df.rename(columns=self.csv_columns).to_string(
            formatters={
                self.csv_columns["VL_TOTAL"]: self.reais_format.format,
                self.csv_columns["VL_PATRIM_LIQ"]: self.reais_format.format,
                self.csv_columns["CAPTC_DIA"]: self.reais_format.format,
                self.csv_columns["RESG_DIA"]: self.reais_format.format,
                "Rent. cota dia": "{:.2f}%".format,
                "Rent. acumulada": "{:.2f}%".format,
            }
        )

    def calc_valores_periodo(self):
        """
        Calcula valores do periodo.

        Return: Dicionario:
                    key: nome da medida
                    value: valor da medida
        """
        fundo_df = self.remove_index_cnpj()

        fundo_df.index.names = ["Data"]
        fundo_df.sort_index(inplace=True)

        cota = fundo_df["NR_COTST"].iloc[-1] - fundo_df["NR_COTST"].iloc[0]
        rent = (
            (fundo_df["VL_QUOTA"].iloc[-1] - fundo_df["VL_QUOTA"].iloc[0])
            / fundo_df["VL_QUOTA"].iloc[0]
        ) * 100
        capt_resg = fundo_df["CAPTC_DIA"].sum() - fundo_df["RESG_DIA"].sum()

        calc = {
            "Saldo cotista": "{}".format(cota),
            "Rentabilidade cota": "{:.2f}%".format(rent),
            "Saldo entre captacao e resgate": "R${:,.2f}".format(capt_resg),
        }

        log.debug("calc: %s", calc)
        return calc

    def mostra_estatistica_mensal(self):
        """Mostra estatistica mensal do fundo."""
        fundo_df = self.remove_index_cnpj()

        fundo_df.index.names = ["Data"]
        fundo_df.sort_index(inplace=True)

        gp = fundo_df.groupby(
            [fundo_df.index.year.rename("ano"), fundo_df.index.month.rename("mes")]
        )

        # Calcula rentabilidade da cota e entre o ultimo dia de cada mes, ie
        # final do mes com o final do mes anterior
        cota_s = gp["VL_QUOTA"].last().pct_change().dropna() * 100
        dif_cotista_s = gp["NR_COTST"].last().diff().dropna()
        # Para fazer o calculo entre o primeiro e o ultimo dia de cada mes
        # cota_s = ((gp["VL_QUOTA"].last() /  gp["VL_QUOTA"].first()) - 1) * 100
        # dif_cotista_s = gp["NR_COTST"].last() - gp["NR_COTST"].first()

        # Saldo entre captacao e resgate
        captacao_s = gp["CAPTC_DIA"].sum() - gp["RESG_DIA"].sum()

        mes_df = pd.concat(
            [cota_s, dif_cotista_s, captacao_s.to_frame(name="Captacao")],
            axis="columns",
            sort=True,
        )
        mes_df.dropna(inplace=True)
        if mes_df.empty:
            msg(
                "red",
                "Dados insuficientes para exibir dados mensais. "
                "Aumente o intervalo requisitado",
                1,
            )

        return mes_df.rename(
            columns={"VL_QUOTA": "Rentabilidade", "NR_COTST": "Dif. Cotistas"}
        ).to_string(
            justify="center",
            formatters={
                "Rentabilidade": "{:.2f}%".format,
                "Dif. Cotistas": "{:.0f}".format,
                "Captacao": self.reais_format.format,
            },
        )


class Compara:
    """Class para comparar performance dos fundos."""

    def __init__(self, cadastral, informe, cnpjs=None):
        """
        Initialize cadastral class.

        Parametros:
            cadastral (obj): Instancia da classe Cadastral
            informe   (obj): Instancia da classe Informe
            cnpj      (str): Cnpj(s) devem ser separados pelo caractere ','
        """
        self.informe = informe
        self.cadastral = cadastral
        if cnpjs:
            self.cnpjs = cnpjs.split(",")

    def denom_social_cnpjs(self):
        """
        Consulta nome social dos cnpjs.

        Return: dicionario
                    Key: cnpj
                    Value: nome social fundo
        """
        denom_social = {}
        for cnpj in self.cnpjs:
            denom_social[cnpj] = self.cadastral.fundo_social_nome(cnpj)

        log.debug("denom social: %s", denom_social)
        return denom_social

    def rentabilidade_periodo(self):
        """Mostra rentabilidade do periodo."""
        # Coloca cpnj como coluna
        fundo_df = self.informe.pd_df.reset_index(level="CNPJ_FUNDO")
        fundo_df.sort_index(level="DT_COMPTC", inplace=True)

        rent_s = (
            (
                fundo_df.groupby("CNPJ_FUNDO")["VL_QUOTA"].last()
                / fundo_df.groupby("CNPJ_FUNDO")["VL_QUOTA"].first()
            )
            - 1
        ) * 100
        rent_df = rent_s.to_frame()

        # Adiciona coluna com nome social dos fundos
        denom_social = self.denom_social_cnpjs()
        rent_df["Denominacao social"] = rent_df.index.map(
            mapper=(lambda x: denom_social[x])
        )

        return rent_df.rename(columns={"VL_QUOTA": "Rentabilidade"}).to_string(
            formatters={"Rentabilidade": "{:.2f}%".format}
        )

    def rentabilidade_mensal(self):
        """Mostra rentabiliadde mensal dos fundos."""
        fundo_df = self.informe.pd_df.reset_index(level="CNPJ_FUNDO")
        fundo_df.sort_index(level="DT_COMPTC", inplace=True)

        mes_ts = (
            fundo_df.groupby("CNPJ_FUNDO")["VL_QUOTA"].resample("M").last().pct_change()
            * 100
        )
        mes_df = mes_ts.to_frame(name="Rentabilidade")
        mes_df = mes_df.pivot_table(
            index="DT_COMPTC", columns="CNPJ_FUNDO", values="Rentabilidade"
        )
        mes_df.index.name = "Data"

        return mes_df.dropna().to_string(float_format="{:.2f}%".format)

    def compara_fundos(self, cnpj):
        """
        Compara performance entre fundos.

        Parametros:
            cnpj      (str): Cnpj(s) devem ser separados pelo caractere ','
        """
        # Cria dataframe do informe com os cnpj
        self.informe.load_informe_csv(cnpj)

        msg("cyan", "Rentabilidade do periodo:")
        print(self.rentabilidade_periodo())

        msg("cyan", "\nRentabilidade mensal:")
        print(self.rentabilidade_mensal())

    def rank_simples(self, tipo_fundo, top, col_filtro):
        """
        Retorna rank dos fundos considerando apenas o ultima posicao no informe.

        Parametros:
            tipo_fundo      (str): Classe do fundo (acoes, mm, fixa e cambial)
            top             (int): Numero de fundos no rank
            col_filtro      (str): Coluna do informe para fazer o rank
        """
        # Buscando cnpj dos fundos
        self.cadastral.load_csv()
        cadastral_df = self.cadastral.busca_fundos(fundo_classe=tipo_fundo)
        # Apenas fundos em funcionamento
        fundos_cnpj = cadastral_df.loc[
            cadastral_df["SIT"] == "EM FUNCIONAMENTO NORMAL"
        ].index.values.tolist()
        log.debug("lista dos cnpjs carregado com sucesso")

        # Cria dataframe do informe com os cnpj
        self.informe.load_informe_csv()
        log.debug("Filtrando os cnpj no informe")
        fundo_df = self.informe.pd_df.loc[(fundos_cnpj,), [col_filtro]]
        fundo_df.reset_index(level="CNPJ_FUNDO", inplace=True)
        fundo_df.sort_index(level="DT_COMPTC", inplace=True)
        fundo_df = (
            fundo_df.groupby("CNPJ_FUNDO")
            .last()
            .sort_values(by=col_filtro, ascending=False)
            .head(top)
        )

        # Addiciona nome social
        self.cnpjs = fundo_df.index.values.tolist()
        denom_social = self.denom_social_cnpjs()
        fundo_df["Denominacao social"] = fundo_df.index.map(
            mapper=(lambda x: denom_social[x])
        )

        return fundo_df.rename(
            columns={
                "NR_COTST": "Numero Cotistas",
                "VL_PATRIM_LIQ": "Patrimonio liquido",
            }
        ).to_string(formatters={"Patrimonio liquido": "R${:,.2f}".format})


##############################################################################
# Validas datas passadas na linha de comando
##############################################################################
def retorna_datas(datainicio=None, datafim=None):
    """Valida datas."""
    # Menor data com dados disponiveis pela CVM
    menor_data_disp = 200501
    # Ano e mes corrente
    ano_mes = int(datetime.datetime.now().strftime("%Y%m"))

    # Se nao for especificado, retorna data atual
    d_fim = datafim if datafim else datetime.datetime.now().strftime("%Y%m")
    d_ini = datainicio if datainicio else datetime.datetime.now().strftime("%Y%m")
    log.debug("data inicio: %s, data fim: %s", datainicio, datafim)

    if int(d_ini) > int(d_fim):
        msg("red", "Erro: Data de inicio maior que data fim", 1)

    if int(d_ini) < menor_data_disp or int(d_fim) < menor_data_disp:
        msg("red", "Erro data de inicio menor que: {}".format(menor_data_disp), 1)

    if int(d_ini) > ano_mes or int(d_fim) > ano_mes:
        msg("red", "Erro data de inicio ou fim maior que data de hoje", 1)

    return d_ini, d_fim


##############################################################################
# Comando rank
##############################################################################
def cmd_rank_fundo(args):
    """Rank dos fundos."""
    datainicio, datafim = retorna_datas()

    inf_cadastral = Cadastral()
    informe = Informe()
    compara = Compara(inf_cadastral, informe)

    for data in range(int(datainicio), int(datafim) + 1, 1):
        compara.informe.download_informe_mensal(data)

    if args.cotistas:
        col_filtro = "NR_COTST"
    if args.patrimonio:
        col_filtro = "VL_PATRIM_LIQ"

    pd.set_option("max_colwidth", None)
    pd.set_option("max_rows", None)
    pd.set_option("display.width", None)
    print(compara.rank_simples(args.tipo, args.top, col_filtro))


##############################################################################
# Comando compara
##############################################################################
def cmd_compara_fundo(args):
    """Compara performance dos fundos."""
    datainicio, datafim = retorna_datas(args.datainicio, args.datafim)

    inf_cadastral = Cadastral()
    informe = Informe()
    compara = Compara(inf_cadastral, informe, args.cnpj)

    for data in range(int(datainicio), int(datafim) + 1, 1):
        compara.informe.download_informe_mensal(data)

    compara.compara_fundos(args.cnpj)


##############################################################################
# Comando informe
##############################################################################
def cmd_informes_fundo(args):
    """Busa informes dos fundos."""
    datainicio, datafim = retorna_datas(args.datainicio, args.datafim)

    # Mostra informacoes cadastral do fundo
    inf_cadastral = Cadastral()
    inf_cadastral.load_csv()
    try:
        inf_cadastral.busca_fundo_cnpj(args.cnpj)
    except KeyError:
        msg("red", "Erro: Fundo com cnpj {} nao encontrado".format(args.cnpj), 1)
    msg("cyan", "Denominacao Social: ", end="")
    msg("nocolor", inf_cadastral.fundo_social_nome(args.cnpj))
    msg("cyan", "Nome do Gestor: ", end="")
    msg("nocolor", inf_cadastral.fundo_gestor_nome(args.cnpj))
    msg("", "")

    # Informes
    informe = Informe()
    for data in range(int(datainicio), int(datafim) + 1, 1):
        informe.download_informe_mensal(data)

    # Mostra os informes
    informe.load_informe_csv(args.cnpj)
    print(informe.mostra_informe_fundo())

    # Calculo do periodo (cota, saldo cotistas, etc)
    msg("cyan", "Saldo no periodo")
    for key, value in informe.calc_valores_periodo().items():
        msg("cyan", key, end=": ")
        msg("nocolor", "{}".format(value))

    # Rentabilidade mensal
    if args.mensal:
        msg("cyan", "Estatistica mensal:")
        print(informe.mostra_estatistica_mensal())


##############################################################################
# Comando busca
##############################################################################
def cmd_busca_fundo(args):
    """Busca informacoes cadastral sobre os fundos."""
    inf_cadastral = Cadastral()
    inf_cadastral.load_csv()
    if args.cnpj:
        inf_cadastral.mostra_detalhes_fundo(args.cnpj)
    else:
        fundo = inf_cadastral.busca_fundos(args.name, args.type, args.all)
        if fundo.empty:
            msg("red", "Erro: Fundo com nome {} nao encontrado".format(args.name), 1)

        pd.set_option("max_colwidth", None)
        pd.set_option("max_rows", None)
        pd.set_option("display.width", None)
        print(
            fundo[["DENOM_SOCIAL", "SIT", "CLASSE"]].rename(
                columns=Cadastral.csv_columns
            )
        )


##############################################################################
# Main function
##############################################################################
def main():
    """Command line execution."""
    global log

    # Parser da linha de comando
    args = parse_parameters()
    # Configura log --debug
    log = setup_logging() if args.debug else logging
    log.debug("CMD line args: %s", vars(args))

    args.func(args)


##############################################################################
# Run from command line
##############################################################################
if __name__ == "__main__":
    main()

# vim: ts=4
