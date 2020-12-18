# -*- coding: utf-8 -*-
"""Biblioteca com funcoes do fundobr."""

import logging
import os
import shutil
import sys

import requests


log = logging.getLogger(__name__)


def msg(color, msg_text, exitcode=0, *, end="\n", flush=True, output=None):
    """
    Print colored text.

    Arguments:
        color          (str): color name (blue, red, green, yellow,
                              cyan or nocolor)
        msg_text       (str): text to be printed
        exitcode  (int, opt): Optional parameter. If exitcode is different
                              from zero, it terminates the script, i.e,
                              it calls sys.exit with the exitcode informed

    Keyword arguments (optional):
        end            (str): string appended after the last char in "msg_text"
                              default a newline
        flush   (True/False): whether to forcibly flush the stream.
                              default True
        output      (stream): a file-like object (stream).
                              default sys.stdout

    Example:
        msg("blue", "nice text in blue")
        msg("red", "Error in my script. terminating", 1)
    """
    color_dic = {
        "blue": "\033[0;34m",
        "red": "\033[1;31m",
        "green": "\033[0;32m",
        "yellow": "\033[0;33m",
        "cyan": "\033[0;36m",
        "resetcolor": "\033[0m",
    }

    if not output:
        output = sys.stdout

    if not color or color == "nocolor":
        print(msg_text, end=end, file=output, flush=flush)
    else:
        if color not in color_dic:
            raise ValueError("Invalid color")
        print(
            "{}{}{}".format(color_dic[color], msg_text, color_dic["resetcolor"]),
            end=end,
            file=output,
            flush=flush,
        )

    if exitcode:
        sys.exit(exitcode)


def setup_logging(logfile=None, *, filemode="a", date_format=None, log_level="DEBUG"):
    """
    Configure logging.

    Arguments (opt):
        logfile     (str): log file to write the log messages
                               If not specified, it shows log messages
                               on screen (stderr)
    Keyword arguments (opt):
        filemode    (a/w): a - log messages are appended to the file (default)
                           w - log messages overwrite the file
        date_format (str): date format in strftime format
                           default is %m/%d/%Y %H:%M:%S
        log_level   (str): specifies the lowest-severity log message
                           DEBUG, INFO, WARNING, ERROR or CRITICAL
                           default is DEBUG
    """
    dict_level = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    if log_level not in dict_level:
        raise ValueError("Invalid log_level")
    if filemode not in ["a", "w"]:
        raise ValueError("Invalid filemode")

    if not date_format:
        date_format = "%m/%d/%Y %H:%M:%S"

    log_fmt = "%(asctime)s %(module)s %(funcName)s %(levelname)s %(message)s"

    logging.basicConfig(
        level=dict_level[log_level],
        format=log_fmt,
        datefmt=date_format,
        filemode=filemode,
        filename=logfile,
    )

    return logging.getLogger(__name__)


def create_dir(dir_name):
    """
    Create a local directory. It supports nested directory.

    Params:
        dir_name   (str): Directory to create
    """
    # Check if dir_name already exist
    if os.path.exists(dir_name):
        if os.path.isfile(dir_name):
            msg(
                "red",
                "Error: path {} exists and is not a directory".format(dir_name),
                1,
            )
    else:
        try:
            os.makedirs(dir_name)
        except PermissionError:
            msg("red", "Error: PermissionError to create dir {}".format(dir_name), 1)


def download_file(url, local_file, *, allow_redirects=True, decode=True):
    """
    Download a file.

    Arguments:
        url                    (str): URL to download
        local_file             (str): Local filename to store the downloaded
                                      file

    Keyword arguments (opt):
        allow_redirects (True/False): Allow request to redirect url
                                      default: True
        decode          (True/False): Decode compressed responses like gzip
                                      default: True

    Return:
        Request response
    """
    with requests.get(url, stream=True, allow_redirects=allow_redirects) as res:
        if decode:
            res.raw.decode_content = True

        if res.status_code == 200:
            msg("nocolor", "Downloading arquivo: {}...".format(local_file))
            with open(local_file, "wb") as fd:
                shutil.copyfileobj(res.raw, fd)

    return res


# vim: ts=4
