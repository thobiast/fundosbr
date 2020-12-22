# -*- coding: utf-8 -*-
"""Test Compara class."""

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
11.000.000/0000-00;2020-04-30;1234.51;28.00000;1111111113.61;1.00;0.00;25
22.000.000/0000-00;2020-02-01;1234.51;20.00000;1111111113.61;1.00;0.00;10
22.000.000/0000-00;2020-02-03;1234.52;22.00000;1111111113.62;2.00;0.00;11
22.000.000/0000-00;2020-02-15;1234.53;24.00000;1111111113.63;0.00;0.00;12
22.000.000/0000-00;2020-02-22;1234.54;22.00000;1111111113.64;4.00;1.00;13
22.000.000/0000-00;2020-02-23;1234.55;26.00000;1111111113.65;1.00;2.00;14
22.000.000/0000-00;2020-03-02;1234.51;20.00000;1111111113.61;1.00;0.00;15
22.000.000/0000-00;2020-03-10;1234.51;22.00000;1111111113.61;1.00;1.00;16
22.000.000/0000-00;2020-03-12;1234.51;26.00000;1111111113.61;1.00;0.00;17
22.000.000/0000-00;2020-03-29;1234.51;28.00000;1111111113.61;1.00;0.00;18
22.000.000/0000-00;2020-04-01;1234.51;26.00000;1111111113.61;0.00;0.00;17
22.000.000/0000-00;2020-04-12;1234.51;28.00000;1111111113.61;0.00;4.00;19
22.000.000/0000-00;2020-04-18;1234.51;22.00000;1111111113.61;1.00;0.00;21
22.000.000/0000-00;2020-04-30;1234.51;12.00000;1111111113.61;1.00;0.00;25"""
    )
    df = pd.read_csv(
        data_csv,
        sep=";",
        encoding="ISO-8859-1",
        index_col=["CNPJ_FUNDO", "DT_COMPTC"],
        parse_dates=True,
    )
    return df


def test_calc_rentabilidade_periodo(df_informe):
    expected_result = pd.DataFrame(
        {"Rentabilidade": [180.0, -40.0]},
        index=["11.000.000/0000-00", "22.000.000/0000-00"],
    )
    expected_result.index.name = "CNPJ_FUNDO"

    fundosbr.log = Mock()
    cadastral = Mock()
    cadastral.fundo_social_nome = Mock(return_value="TESTE")
    informe = Mock()
    compara = fundosbr.Compara(cadastral, informe)

    with patch.object(compara.informe, "pd_df", df_informe):
        x = compara.calc_rentabilidade_periodo()
    pd.testing.assert_frame_equal(x, expected_result)


def test_rentabilidade_mensal(df_informe):
    expected_result = """CNPJ_FUNDO  11.000.000/0000-00  22.000.000/0000-00
Data                                              
2020-03-31               12.50                7.69
2020-04-30               55.56              -57.14"""

    fundosbr.log = Mock()
    cadastral = Mock()
    cadastral.fundo_social_nome = Mock(return_value="TESTE")
    informe = Mock()
    compara = fundosbr.Compara(cadastral, informe)
    with patch.object(compara.informe, "pd_df", df_informe):
        x = compara.calc_rentabilidade_mensal()
    assert x.to_string(float_format="{:.2f}".format) == expected_result


def test_denom_social_cnpjs(df_informe):
    nome_fundo = "meu fundo"

    expected_result = df_informe
    expected_result["enominacao social"] = nome_fundo

    fundosbr.log = Mock()
    cadastral = Mock()
    cadastral.fundo_social_nome = Mock(return_value=nome_fundo)
    informe = Mock()
    compara = fundosbr.Compara(cadastral, informe)

    x = compara.adiciona_denom_social(df_informe)
    pd.testing.assert_frame_equal(x, expected_result)
