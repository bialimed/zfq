#!/usr/bin/env python3

__author__ = 'Frederic Escudie'
__copyright__ = 'Copyright (C) 2023 CHU Toulouse'
__license__ = 'GNU General Public License'
__version__ = '1.1.0'

import argparse
import csv
import hashlib
import json
import logging
import os
import psutil
import shutil
import sys
import subprocess
import time


########################################################################
#
# FUNCTIONS
#
########################################################################
class LoggerAction(argparse.Action):
    """Manages logger level parameters (The value "INFO" becomes logging.info and so on)."""

    def __call__(self, parser, namespace, values, option_string=None):
        log_level = None
        if values == "DEBUG":
            log_level = logging.DEBUG
        elif values == "INFO":
            log_level = logging.INFO
        elif values == "WARNING":
            log_level = logging.WARNING
        elif values == "ERROR":
            log_level = logging.ERROR
        elif values == "CRITICAL":
            log_level = logging.CRITICAL
        setattr(namespace, self.dest, log_level)


def submitMonitoredProcess(cmd, wait=1):
    start_time = time.time()
    with open("error.txt", "w") as fh_err:
        with open("log.txt", "w") as fh_stdout:
            proc = subprocess.Popen(cmd, shell=True, stderr=fh_err, stdout=fh_stdout)
        max_mem = getMaxExecMem(proc.pid, "rss", wait)
        end_time = time.time()
        if proc.poll() != 0:
            raise Exception("Error in subprocess: {}".format(cmd))
    return start_time, end_time, max_mem


def getMaxExecMem(pid, tag="rss", wait=1):
    max_mem = 0
    check = False
    proc = psutil.Process(pid)
    while proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE:
        max_mem = max(max_mem, getattr(proc.memory_info(), tag))
        check = True
        time.sleep(wait)
    return max_mem if check else None


def compress(cmd, input, output, metrics, retry=0):
    complete_cmd = cmd.replace('#IN#', input).replace('#OUT#', output)
    log.debug(complete_cmd)
    is_ended = False
    while not is_ended:
        try:
            start_time, end_time, metrics["compress_mem"] = submitMonitoredProcess(complete_cmd, 2)
            is_ended = True
            metrics["compress_time"] = end_time - start_time
            metrics["compress_size"] = getFileSize(output)
        except Exception:
            retry -= 1
            with open("error.txt") as reader:
                metrics["compress_error"] = reader.readlines()
            metrics["compress_nb_retries"] += 1
            if retry < 0:
                is_ended = True
            log.warning(complete_cmd)


def decompress(cmd, input, output, metrics, retry=0):
    complete_cmd = cmd.replace('#IN#', input).replace('#OUT#', output)
    log.debug(complete_cmd)
    is_ended = False
    while not is_ended:
        try:
            start_time, end_time, metrics["decompress_mem"] = submitMonitoredProcess(complete_cmd, 2)
            is_ended = True
            metrics["decompress_time"] = end_time - start_time
            metrics["decompress_size"] = getFileSize(output)
            metrics["decompress_hash"] = md5sum(output, chunk_size=8192)
        except Exception:
            retry -= 1
            with open("error.txt") as reader:
                metrics["decompress_error"] = reader.readlines()
            metrics["decompress_nb_retries"] += 1
            if retry < 0:
                is_ended = True
            log.warning(complete_cmd)


def getFileSize(path):
    file_stats = os.stat(path)
    return file_stats.st_size


def md5sum(path, chunk_size=8192):
    """
    Return MD5 checksum for the file.

    :param path: Path to the file.
    :type path: str
    :param chunk_size: Size of chunks.
    :type chunk_size: int
    :return: MD5 checksum for the file.
    :rtype: str
    """
    hashsum = hashlib.md5()
    with open(path, "rb") as reader:
        chunk = reader.read(chunk_size)
        while chunk:  # while chunk := reader.read(chunk_size):
            hashsum.update(chunk)
            chunk = reader.read(chunk_size)
    return hashsum.hexdigest()


########################################################################
#
# MAIN
#
########################################################################
if __name__ == "__main__":
    # Manage parameters
    parser = argparse.ArgumentParser(description='Generate metrics for benchmark of sequence compression algorithms.')
    parser.add_argument('-l', '--logging-level', default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], action=LoggerAction, help='The logger level. [Default: %(default)s]')
    parser.add_argument('-w', '--working-dir', required=True, help='Path to working directory.')
    parser.add_argument('-v', '--version', action='version', version=__version__)
    group_input = parser.add_argument_group('Inputs')  # Inputs
    group_input.add_argument('-a', '--algorithms', required=True, help='Path to configuration file on algorithms. (format: JSON).')
    group_input.add_argument('-d', '--datasets', required=True, help='Path to configuration file on datasets. (format: JSON).')
    group_output = parser.add_argument_group('Outputs')  # Outputs
    group_output.add_argument('-m', '--metrics', required=True, help='Path to the metrics file. (format: CSV).')
    args = parser.parse_args()

    # Logger
    logging.basicConfig(format='%(asctime)s -- [%(filename)s][pid:%(process)d][%(levelname)s] -- %(message)s')
    log = logging.getLogger(os.path.basename(__file__))
    log.setLevel(args.logging_level)
    log.info("Command: " + " ".join(sys.argv))

    # Load configurations
    with open(args.algorithms) as reader:
        algorithms = json.load(reader)
    with open(args.datasets) as reader:
        datasets = json.load(reader)

    # Process
    with open(args.metrics, "w") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "dataset",
                "laboratory", "instrument_type", "matrix", "design",
                "file", "expected_hash", "decompress_hash", "soft",
                "decompress_size", "decompress_time", "decompress_mem",
                "compress_size", "compress_time", "compress_mem",
                "decompress_cmd", "decompress_nb_retries", "decompress_error",
                "compress_cmd", "compress_nb_retries", "compress_error"
            ]
        )
        writer.writeheader()
        for curr_dataset in datasets:
            for file in curr_dataset["paths"]:
                log.info("Process file {}.".format(file))
                if not os.path.exists(args.working_dir):
                    os.makedirs(args.working_dir)
                tmp_file = os.path.join(args.working_dir, os.path.basename(file))
                if file.endswith(".gz"):
                    shutil.copyfile(file, tmp_file)
                    ini_path = tmp_file[:-3]
                    subprocess.check_call(["gzip", "-d", tmp_file])
                else:
                    ini_path = tmp_file[:-4]
                    subprocess.check_call(["zfq.py", "uncompress", "-i", file, "-o", ini_path])
                expected_hash = md5sum(ini_path, chunk_size=8192)
                for algo in algorithms:
                    log.info("Porcess with soft {}.".format(algo["soft"]))
                    algo_metrics = {
                        "dataset": curr_dataset["name"],
                        "design": curr_dataset["design"],
                        "instrument_type": curr_dataset["instrument_type"],
                        "laboratory": curr_dataset["laboratory"],
                        "matrix": curr_dataset["matrix"],
                        "file": file,
                        "expected_hash": expected_hash,
                        "soft": algo["soft"],
                        "decompress_cmd": algo["decompress_cmd"],
                        "decompress_nb_retries": 0,
                        "decompress_size": None,
                        "decompress_time": None,
                        "decompress_mem": None,
                        "decompress_error": None,
                        "compress_cmd": algo["compress_cmd"],
                        "compress_nb_retries": 0,
                        "compress_size": None,
                        "compress_time": None,
                        "compress_mem": None,
                        "compress_error": None,
                        "decompress_hash": None
                    }
                    algo_dir = os.path.abspath(os.path.join(args.working_dir, algo["soft"]))
                    os.makedirs(algo_dir)
                    copy_path = os.path.join(algo_dir, "tmp_in.fastq")
                    shutil.copyfile(ini_path, copy_path)
                    compressed_path = os.path.join(algo_dir, "tmp_c")
                    compress(algo["compress_cmd"], copy_path, compressed_path, algo_metrics)
                    decompressed_path = os.path.join(algo_dir, "tmp_d")
                    decompress(algo["decompress_cmd"], compressed_path, decompressed_path, algo_metrics)
                    writer.writerow(algo_metrics)
                    shutil.rmtree(algo_dir)
                os.remove(ini_path)
            fh.flush()
            os.fsync(fh)
    log.info("End of job")
