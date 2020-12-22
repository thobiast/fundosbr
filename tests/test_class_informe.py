# -*- coding: utf-8 -*-
"""Test Informe class."""

import pytest
from unittest.mock import patch, Mock
from io import StringIO
import pandas as pd
from fundosbr import fundosbr


@pytest.fixture
def df_informe():
    data_csv = StringIO(
        """CNPJ_FUNDO;DT_COMPTC;VL_TOTAL;VL_QUOTA;VL_PATRIM_LIQ;CAPTC_DIA;RESG_DIA;NR_COTST
11.000.000/0000-00;2020-02-01;1234.51;10.00000;1111111113.61;1.00;0.00;10
11.000.000/0000-00;2020-02-03;1234.52;12.00000;1111111113.62;2.00;0.00;11
11.000.000/0000-00;2020-02-15;1234.53;14.00000;1111111113.63;0.00;0.00;12
11.000.000/0000-00;2020-02-22;1234.54;12.00000;1111111113.64;4.00;1.00;13
11.000.000/0000-00;2020-02-23;1234.55;16.00000;1111111113.65;1.00;2.00;14
11.000.000/0000-00;2020-03-02;1234.51;10.00000;1111111113.61;1.00;0.00;15
11.000.000/0000-00;2020-03-10;1234.51;12.00000;1111111113.61;1.00;1.00;16
11.000.000/0000-00;2020-03-12;1234.51;16.00000;1111111113.61;1.00;0.00;17
11.000.000/0000-00;2020-03-29;1234.51;18.00000;1111111113.61;1.00;0.00;18
11.000.000/0000-00;2020-04-01;1234.51;16.00000;1111111113.61;0.00;0.00;17
11.000.000/0000-00;2020-04-12;1234.51;18.00000;1111111113.61;0.00;4.00;19
11.000.000/0000-00;2020-04-18;1234.51;22.00000;1111111113.61;1.00;0.00;21
11.000.000/0000-00;2020-04-30;1234.51;28.00000;1111111113.61;1.00;0.00;25"""
    )
    df = pd.read_csv(
        data_csv,
        sep=";",
        encoding="ISO-8859-1",
        index_col=["CNPJ_FUNDO", "DT_COMPTC"],
        parse_dates=True,
    )
    return df


expected_result_mostra_informe_fundo = """           Valor total carteira  Valor cota Valor patrimonio liquido Captacao dia Resgate dia  Numero cotistas Rent. cota dia Rent. acumulada
Data                                                                                                                                         
2020-02-01           R$1,234.51        10.0       R$1,111,111,113.61       R$1.00      R$0.00               10           nan%            nan%
2020-02-03           R$1,234.52        12.0       R$1,111,111,113.62       R$2.00      R$0.00               11         20.00%          20.00%
2020-02-15           R$1,234.53        14.0       R$1,111,111,113.63       R$0.00      R$0.00               12         16.67%          40.00%
2020-02-22           R$1,234.54        12.0       R$1,111,111,113.64       R$4.00      R$1.00               13        -14.29%          20.00%
2020-02-23           R$1,234.55        16.0       R$1,111,111,113.65       R$1.00      R$2.00               14         33.33%          60.00%
2020-03-02           R$1,234.51        10.0       R$1,111,111,113.61       R$1.00      R$0.00               15        -37.50%          -0.00%
2020-03-10           R$1,234.51        12.0       R$1,111,111,113.61       R$1.00      R$1.00               16         20.00%          20.00%
2020-03-12           R$1,234.51        16.0       R$1,111,111,113.61       R$1.00      R$0.00               17         33.33%          60.00%
2020-03-29           R$1,234.51        18.0       R$1,111,111,113.61       R$1.00      R$0.00               18         12.50%          80.00%
2020-04-01           R$1,234.51        16.0       R$1,111,111,113.61       R$0.00      R$0.00               17        -11.11%          60.00%
2020-04-12           R$1,234.51        18.0       R$1,111,111,113.61       R$0.00      R$4.00               19         12.50%          80.00%
2020-04-18           R$1,234.51        22.0       R$1,111,111,113.61       R$1.00      R$0.00               21         22.22%         120.00%
2020-04-30           R$1,234.51        28.0       R$1,111,111,113.61       R$1.00      R$0.00               25         27.27%         180.00%"""


def test_mostra_informe_fundo(df_informe):
    fundosbr.log = Mock()
    informe = fundosbr.Informe()
    with patch.object(informe, "pd_df", df_informe):
        x = informe.mostra_informe_fundo()
    assert x == expected_result_mostra_informe_fundo


def test_calc_saldo_periodo(df_informe):
    expected_result = {
        "Saldo cotista": "15",
        "Rentabilidade cota": "180.00%",
        "Saldo entre captacao e resgate": "R$6.00",
    }
    fundosbr.log = Mock()
    informe = fundosbr.Informe()
    with patch.object(informe, "pd_df", df_informe):
        x = informe.calc_saldo_periodo()
    assert x == expected_result


def test_calc_estatistica_mensal(df_informe):
    expected_result = """         Rentabilidade Dif. Cotistas Captacao
ano  mes                                     
2020 3       12.50%          4        R$3.00 
     4       55.56%          7       R$-2.00 """
    fundosbr.log = Mock()
    informe = fundosbr.Informe()
    with patch.object(informe, "pd_df", df_informe):
        x = informe.calc_estatistica_mensal()
    assert x == expected_result
