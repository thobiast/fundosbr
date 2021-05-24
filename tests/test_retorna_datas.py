# -*- coding: utf-8 -*-
"""Test retorna_datas function."""

import datetime
from unittest.mock import patch, Mock
import pytest
from fundosbr import fundosbr


@pytest.mark.parametrize(
    "d_ini, d_fim, expected_result",
    [
        (202102, 202105, ["202102", "202103", "202104", "202105"]),
        (202011, 202102, ["202011", "202012", "202101", "202102"]),
        (202101, 202101, ["202101"]),
    ],
)
def test_retorna_datasr(d_ini, d_fim, expected_result):
    """Test intervalo das datas retornadas."""
    fundosbr.log = Mock()
    resp = fundosbr.retorna_datas(d_ini, d_fim)
    assert resp == expected_result


@pytest.mark.parametrize(
    "d_ini, d_fim, msg_1, msg_2, msg_3",
    [
        (202004, 202003, "red", "Erro: Data de inicio maior que data fim", 1),
        (200104, 202003, "red", "Erro data de inicio menor que: 200501", 1),
    ],
)
def test_retorna_datas_datas(d_ini, d_fim, msg_1, msg_2, msg_3):
    """
    Test se data fim maior que data inicio e se data inicio
    maior que data disponvel pela CVM.
    """
    fundosbr.msg = Mock()
    fundosbr.log = Mock()
    fundosbr.retorna_datas(d_ini, d_fim)
    fundosbr.msg.assert_called_with(msg_1, msg_2, msg_3)


@pytest.mark.parametrize("d_ini, d_fim", [(202106, 202107), (202101, 202106)])
def test_retorna_datas_data_maior_hoje(d_ini, d_fim):
    """Test se data passada eh maior do que hoje."""
    fundosbr.msg = Mock()
    fundosbr.log = Mock()
    datetime = Mock(return_value=202105)
    fundosbr.retorna_datas(d_ini, d_fim)
    fundosbr.msg.assert_called_with(
        "red", "Erro data de inicio ou fim maior que data de hoje", 1
    )


# vim: ts=4
