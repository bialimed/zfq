#!/usr/bin/env python3

__author__ = 'Frederic Escudie'
__copyright__ = 'Copyright (C) 2023 CHU Toulouse'
__license__ = 'GNU General Public License'
__version__ = '1.0.0'

import argparse
import gzip
import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import tarfile
import uuid


def compress(in_path, out_path, skip_check, log, threads=1):
    """
    Compress FastQ file to zfq.

    :param in_path: Path to raw file (format: FastQ). It can be gzipped.
    :type in_path: str
    :param out_path: Path to compressed file (format: zfq).
    :type out_path: str
    :param skip_check: Skip md5sum comparison between original file (before compression) and compressed file after uncompression. Check should be skipped only if the original file was gzipped with a compression level different of 9.'
    :type skip_check: bool
    :param log: Logger of the script.
    :type log: logging.Logger
    :param threads: Number of compression threads.
    :type threads: int
    """
    # Create tmp dir
    dest_dir = os.path.dirname(out_path)
    tmp_dir = os.path.join(dest_dir, str(uuid.uuid4()))
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)
    # Process
    try:
        modif_time = os.path.getmtime(in_path)
        # Split fastq components
        log.debug("Split FastQ file components")
        with suitableOpen(in_path) as reader:
            with open(os.path.join(tmp_dir, "head.txt"), "w") as writer_head:
                with open(os.path.join(tmp_dir, "seq.fa"), "w") as writer_seq:
                    with open(os.path.join(tmp_dir, "qual.txt"), "w") as writer_qual:
                        writer_seq.write(">\n")
                        rec_id = reader.readline()
                        while rec_id:
                            writer_head.write(rec_id[1:])
                            writer_seq.write(reader.readline().strip())
                            reader.readline()  # separator
                            writer_qual.write(reader.readline())
                            rec_id = reader.readline()
        # Get info
        log.debug("Store input info")
        metrics = subprocess.check_output(
            ["wc", "-lm", os.path.join(tmp_dir, "qual.txt")]
        )
        nb_lines, nb_nt, file_name = metrics.strip().split()
        with open(os.path.join(tmp_dir, "info.json"), "w") as writer_info:
            writer_info.write(json.dumps({
                "seq": int(nb_lines),
                "nt": int(nb_nt),
                "md5": md5sum(in_path),
                "mtime": modif_time
            }))
        # Compress sequences
        log.debug("Zstd compress sequences")
        silentexec([
            "zstd",
            "--no-progress",
            "-T{}".format(threads),
            "-18",
            os.path.join(tmp_dir, "seq.fa")
        ])
        os.remove(os.path.join(tmp_dir, "seq.fa"))
        # Compress qualities
        log.debug("Zstd compress qualities")
        silentexec([
            "zstd",
            "--no-progress",
            "-T{}".format(threads),
            os.path.join(tmp_dir, "qual.txt")
        ])
        os.remove(os.path.join(tmp_dir, "qual.txt"))
        # Compress headers
        log.debug("Zstd compress headers")
        silentexec([
            "zstd",
            "--no-progress",
            "-T{}".format(threads),
            os.path.join(tmp_dir, "head.txt")
        ])
        os.remove(os.path.join(tmp_dir, "head.txt"))
        # Create tar
        log.debug("Create archive")
        with tarfile.open(out_path, mode="w") as archive:
            # Headers
            archive.add(
                os.path.join(tmp_dir, "head.txt.zst"),
                arcname="head.txt.zst",
                recursive=False,
            )
            # Sequences
            archive.add(
                os.path.join(tmp_dir, "seq.fa.zst"),
                arcname="seq.fa.zst",
                recursive=False,
            )
            # Qualities
            archive.add(
                os.path.join(tmp_dir, "qual.txt.zst"),
                arcname="qual.txt.zst",
                recursive=False,
            )
            # Info
            archive.add(
                os.path.join(tmp_dir, "info.json"),
                arcname="info.json",
                recursive=False,
            )
        os.utime(out_path, (modif_time, modif_time))
    finally:
        shutil.rmtree(tmp_dir)
    # Test archive consistency
    if not skip_check:
        log.debug("Test file consistency after uncompressing")
        test_file_path = out_path + ".testmd5"
        uncompress(out_path, test_file_path, False, FakeLogger())
        os.remove(test_file_path)


class FakeLogger:
    """Fake logger used to hide log outputs."""
    def critical(self, msg):
        pass

    def debug(self, msg):
        pass

    def error(self, msg):
        pass

    def info(self, msg):
        pass

    def warning(self, msg):
        pass


def info(in_path):
    """
    Display information from sequence file: number of sequences, number of nucleotids and original file md5sum.

    :param in_path: Path to the compressed file (format: zfq).
    :type in_path: str
    """
    with tarfile.open(in_path) as archive:
        with archive.extractfile("info.json") as reader_info:
            in_info = json.load(reader_info)
    print(json.dumps(in_info))


def isGzip(path):
    """
    Return True if the file is gziped.

    :param path: Path to processed file.
    :type path: str
    :return: True if the file is gziped.
    :rtype: bool
    """
    is_gzip = None
    FH_input = gzip.open(path)
    try:
        FH_input.readline()
        is_gzip = True
    except Exception:
        is_gzip = False
    finally:
        FH_input.close()
    return is_gzip


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


def md5sum(path, chunk_size=8192):
    """
    Return MD5 checksum for the uncompressed file.

    :param path: Path to the file.
    :type path: str
    :param chunk_size: Size of chunks.
    :type chunk_size: int
    :return: MD5 checksum for the uncompressed file.
    :rtype: str
    """
    hashsum = hashlib.md5()
    open_fct = gzip.open if isGzip(path) else open
    with open_fct(path, "rb") as reader:
        chunk = reader.read(chunk_size)
        while chunk:  # while chunk := reader.read(chunk_size):
            hashsum.update(chunk)
            chunk = reader.read(chunk_size)
    return hashsum.hexdigest()


def silentexec(cmd):
    """
    Execute subprocess with check_output and mask stderr.

    :param cmd: Command to execute.
    :type cmd: list
    """
    with open(os.devnull, "w") as writer:
        subprocess.check_output(cmd, stderr=writer)


def suitableOpen(path, mode="r"):
    """
    Return object file from suitable open (gzip.open or open) and mode on provided file.

    :param path: Path to the file.
    :type path: str
    :param mode: Open mode.
    :type mode: str
    :return: Object file from suitable open (gzip.open or open) and mode on provided file.
    :rtype: _io.TextIOWrapper or _io.BufferedReader
    """
    if mode in {"a", "r"}:
        if isGzip(path):
            return gzip.open(path, mode + "t")
        else:
            return open(path, mode)
    else:
        if path.endswith(".gz"):
            return gzip.open(path, mode + "t")
        else:
            return open(path, mode)


def uncompress(in_path, out_path, skip_check, log):
    """
    Uncompress zfq file to FastQ.

    :param in_path: Path to compressed file (format: zfq).
    :type in_path: str
    :param out_path: Path to raw file (format: Fastq). It can be gzipped if the file name endswith ".gz".
    :type out_path: str
    :param skip_check: Skip md5sum comparison between original file (before compression) and file after uncompression. Check should be skipped only if the original file was gzipped with a compression level different of 9.
    :type skip_check: bool
    :param log: Logger of the script.
    :type log: logging.Logger
    """
    # Create tmp dir
    dest_dir = os.path.dirname(out_path)
    tmp_dir = os.path.join(dest_dir, str(uuid.uuid4()))
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)

    # Process
    try:
        # Extract all
        log.debug("Extract archive in {}".format(tmp_dir))
        with tarfile.open(in_path) as archive:
            archive.extractall(tmp_dir)
        # Get info
        with open(os.path.join(tmp_dir, "info.json")) as reader_info:
            in_info = json.load(reader_info)
        # Uncompress sequences
        log.debug("Zstd decompress sequences")
        silentexec([
            "zstd",
            "--no-progress",
            "-d",
            os.path.join(tmp_dir, "seq.fa.zst")
        ])
        os.remove(os.path.join(tmp_dir, "seq.fa.zst"))
        # Uncompress qualities
        log.debug("Zstd decompress qualities")
        silentexec([
            "zstd",
            "--no-progress",
            "-d",
            os.path.join(tmp_dir, "qual.txt.zst")
        ])
        os.remove(os.path.join(tmp_dir, "qual.txt.zst"))
        # Uncompress headers
        log.debug("Zstd decompress IDs")
        silentexec([
            "zstd",
            "--no-progress",
            "-d",
            os.path.join(tmp_dir, "head.txt.zst")
        ])
        os.remove(os.path.join(tmp_dir, "head.txt.zst"))
        # Write FastQ
        log.debug("Write FastQ")
        with suitableOpen(out_path, "w") as writer_fastq:
            with open(os.path.join(tmp_dir, "head.txt")) as reader_head:
                with open(os.path.join(tmp_dir, "seq.fa")) as reader_seq:
                    with open(os.path.join(tmp_dir, "qual.txt")) as reader_qual:
                        reader_seq.read(2)
                        for rec_head, rec_qual in zip(reader_head, reader_qual):
                            rec_len = len(rec_qual) - 1
                            writer_fastq.write("@" + rec_head)
                            writer_fastq.write(reader_seq.read(rec_len) + "\n")
                            writer_fastq.write("+\n")
                            writer_fastq.write(rec_qual)
        os.utime(out_path, (in_info["mtime"], in_info["mtime"]))
        # Test consistency
        if not skip_check:
            log.debug("Check consistency from original file")
            if in_info["md5"] != md5sum(out_path):
                raise Exception("Uncompressed file from archive is not identical to original file.")
    finally:
        shutil.rmtree(tmp_dir)


if __name__ == "__main__":
    # Manage parameters
    parser = argparse.ArgumentParser(description='Compress or uncompress FastQ file.')
    parser.add_argument('-v', '--version', action='version', version=__version__)
    sub_parsers = parser.add_subparsers(dest="command")
    compress_parser = sub_parsers.add_parser("compress", help="Compress FastQ file to zfq.")
    compress_parser.add_argument('-i', '--input', required=True, help='Path to raw file (format: FastQ). It can be gzipped.')
    compress_parser.add_argument('-l', '--logging-level', default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], action=LoggerAction, help='The logger level. [Default: %(default)s]')
    compress_parser.add_argument('-o', '--output', required=True, help='Path to compressed file (format: zfq).')
    compress_parser.add_argument('-r', '--remove', action='store_true', help='Remove input file after process.')
    compress_parser.add_argument('-s', '--skip-check', action='store_true', help='Skip md5sum comparison between original file (before compression) and compressed file after uncompression.')
    compress_parser.add_argument('-t', '--threads', type=int, default=1, help='Number of compression threads. [Default: %(default)s]')
    info_parser = sub_parsers.add_parser("info", help="Return information from sequence file: number of sequences, number of nucleotids and original file md5sum.")
    info_parser.add_argument('-i', '--input', required=True, help='Path to compressed file (format: zfq).')
    uncompress_parser = sub_parsers.add_parser("uncompress", help="Uncompress zfq file to FastQ.")
    uncompress_parser.add_argument('-i', '--input', required=True, help='Path to compressed file (format: zfq).')
    uncompress_parser.add_argument('-l', '--logging-level', default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], action=LoggerAction, help='The logger level. [Default: %(default)s]')
    uncompress_parser.add_argument('-o', '--output', required=True, help='Path to raw file (format: Fastq). It can be gzipped if the file name endswith ".gz".')
    uncompress_parser.add_argument('-r', '--remove', action='store_true', help='Remove input file after process.')
    uncompress_parser.add_argument('-s', '--skip-check', action='store_true', help='Skip md5sum comparison between original file (before compression) and file after uncompress.')
    args = parser.parse_args()

    # Actions
    if args.command == "info":
        info(args.input)
    else:
        # Logger
        logging.basicConfig(format='%(asctime)s -- [%(filename)s][pid:%(process)d][%(levelname)s] -- %(message)s')
        log = logging.getLogger(os.path.basename(__file__))
        log.setLevel(args.logging_level)
        log.info("Command: " + " ".join(sys.argv))
        # Process
        if args.command == "compress":
            compress(args.input, args.output, args.skip_check, log, args.threads)
        else:
            uncompress(args.input, args.output, args.skip_check, log)
        if args.remove:
            os.remove(args.input)
        log.info("End of job")
