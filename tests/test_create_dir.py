# -*- coding: utf-8 -*-
"""Test create_dir function."""

from unittest.mock import patch
import pytest
from fundosbr.fundosbrlib import create_dir

dir_name = "mydirtest"


@patch("os.makedirs", autospec=True)
@patch("os.path.exists", autospec=True)
def test_create_dir(mock_exists, mock_makedirs):
    """Test directory creation."""
    mock_exists.return_value = False
    create_dir(dir_name)
    mock_makedirs.assert_called_once_with(dir_name)


@patch("os.makedirs", autospec=True)
@patch("os.path.isfile", autospec=True)
@patch("os.path.exists", autospec=True)
def test_create_dir_already_exist(mock_exists, mock_isfile, mock_makedirs):
    """Test not try to create directory if it already exist."""
    mock_exists.return_value = True
    mock_isfile.return_value = False
    create_dir("mydirtest")
    mock_makedirs.assert_not_called()


@patch("fundosbr.fundosbrlib.msg")
@patch("os.makedirs", autospec=True)
@patch("os.path.isfile", autospec=True)
@patch("os.path.exists", autospec=True)
def test_create_dir_exist_but_file(mock_exists, mock_isfile, mock_makedirs, mock_msg):
    """Test error if path exist but is a file."""
    mock_exists.return_value = True
    mock_isfile.return_value = True
    create_dir(dir_name)
    mock_msg.assert_called_once_with(
        "red", "Error: path {} exists and is not a directory".format(dir_name), 1
    )


@patch("fundosbr.fundosbrlib.msg")
@patch("os.makedirs", autospec=True)
@patch("os.path.exists", autospec=True)
def test_create_dir_path_is_file(mock_exists, mock_makedirs, mock_msg):
    """Test permission denied error to create dir."""
    mock_exists.return_value = False
    mock_makedirs.side_effect = PermissionError
    create_dir(dir_name)
    mock_msg.assert_called_once_with(
        "red", "Error: PermissionError to create dir {}".format(dir_name), 1
    )


# vim: ts=4
