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
            file_name = "inf_cadastral_fi_{}.csv".format(self.days_ago(num_d_ago))

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
            fundo_classe          (str): Classe do fundo (acoes, mm, fixa cambial)
            all_situacoes  (True/False): Remove fundos com situacao cancelada

        Retorna um dataframe
        """
        pd.set_option("max_colwidth", None)
        pd.set_option("max_rows", None)
        pd.set_option("display.width", None)

        # Filtra fundo por nome
        if name:
            fundo_df = self.pd_df[
                self.pd_df["DENOM_SOCIAL"].str.contains(name, na=False, case=False)
            ]
        else:
            fundo_df = self.pd_df

        # Filtra fundo por classe
        if fundo_classe == "acoes":
            fundo_df = fundo_df.loc[fundo_df["CLASSE"] == "Fundo de Ações"]
        if fundo_classe == "multimercado":
            fundo_df = fundo_df.loc[fundo_df["CLASSE"] == "Fundo Multimercado"]
        if fundo_classe == "cambial":
            fundo_df = fundo_df.loc[fundo_df["CLASSE"] == "Fundo Cambial"]
        if fundo_classe == "rendafixa":
            fundo_df = fundo_df.loc[fundo_df["CLASSE"] == "Fundo de Renda Fixa"]

        # Remove fundos cancelados
        if not all_situacoes:
            fundo_df = fundo_df.loc[~(fundo_df["SIT"] == "CANCELADA")]

        return fundo_df

    def busca_fundo_cnpj(self, cnpj):
        """Retorna dataframe de um fundo."""
        return self.pd_df.loc[cnpj]

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
        Cria DataFrame com os dados dos arquivos csv baixados.

        Parametros:
            cnpj      (str): Cnpj do fundo para criar o DataFrame
                             Se nao especificado, cria com todos
        """
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
            if cnpj:
                self.pd_df = pd.concat([self.pd_df, informe_mensal.loc[cnpj]])
            else:
                self.pd_df = pd.concat([self.pd_df, informe_mensal])

    def mostra_informe_fundo(self, mensal=None):
        """Mostra os informes de um fundo."""
        fundo_df = self.pd_df.sort_index()

        # Pega informacoes do periodo todo
        saldo_cotistas = fundo_df["NR_COTST"].iloc[-1] - fundo_df["NR_COTST"].iloc[0]
        rentabilidade_cota = (
            (fundo_df["VL_QUOTA"].iloc[-1] - fundo_df["VL_QUOTA"].iloc[0])
            / fundo_df["VL_QUOTA"].iloc[0]
        ) * 100
        saldo_capt = fundo_df["CAPTC_DIA"].sum() - fundo_df["RESG_DIA"].sum()

        # Adiciona coluna com rentabilidade diaria da cota
        fundo_df["Rentabilidade cota"] = (
            (fundo_df["VL_QUOTA"] / fundo_df["VL_QUOTA"].shift(1)) - 1
        ) * 100

        fundo_df.index.names = ["Data"]
        print(
            fundo_df.rename(columns=self.csv_columns).to_string(
                formatters={
                    self.csv_columns["VL_TOTAL"]: self.reais_format.format,
                    self.csv_columns["VL_PATRIM_LIQ"]: self.reais_format.format,
                    self.csv_columns["CAPTC_DIA"]: self.reais_format.format,
                    self.csv_columns["RESG_DIA"]: self.reais_format.format,
                    "Rentabilidade cota": "{:.2f}%".format,
                }
            )
        )
        msg("cyan", "Saldo no periodo")

        msg("cyan", "Numero de cotistas: ", end="")
        msg("nocolor", "{}".format(saldo_cotistas))

        msg("cyan", "Rentabilidade cota: ", end="")
        msg("nocolor", "{:.2f}%".format(rentabilidade_cota))

        msg("cyan", "Saldo entre captacao e resgate: ", end="")
        msg("nocolor", "R${:,.2f}".format(saldo_capt))

        if mensal:
            self.mostra_estatistica_mensal(fundo_df)

    def mostra_estatistica_mensal(self, fundo_df):
        """Mostra estatistica mensal do fundo."""
        msg("cyan", "\nEstatistica mensal")

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
            axis=1,
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

        print(
            mes_df.rename(
                columns={"VL_QUOTA": "Rentabilidade", "NR_COTST": "Dif. Cotistas"}
            ).to_string(
                justify="center",
                formatters={
                    "Rentabilidade": "{:.2f}%".format,
                    "Dif. Cotistas": "{:.0f}".format,
                    "Captacao": self.reais_format.format,
                },
            )
        )


##############################################################################
# Comando informe
##############################################################################
def cmd_informes_fundo(args):
    """Busa informes dos fundos."""
    # Valida valores de data inicio e data fim
    datafim = args.datafim if args.datafim else datetime.datetime.now().strftime("%Y%m")
    datainicio = (
        args.datainicio if args.datainicio else datetime.datetime.now().strftime("%Y%m")
    )
    log.debug("data inicio: %s, data fim: %s", datainicio, datafim)
    if int(datainicio) > int(datafim):
        msg("red", "Erro: Data de inicio maior que data fim", 1)

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

    informe.load_informe_csv(args.cnpj)
    informe.mostra_informe_fundo(args.mensal)


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
