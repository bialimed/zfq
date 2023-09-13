# zfq: FastQ file compressor.

## Table of Contents
* [Description](#description)
* [Performance](#copyright)
* [Installation](#installation)
* [Usage example](#usage_example)
* [Copyright](#copyright)
* [Contact](#contact)


## Description
zfq is a **lossless** compression/uncompression wrapper for FastQ files.

### Key features:
* Universal:
  * zfq is based on a non-specialized compression algorithm. This somewhat
  reduces its compression performance, but means it can handle any FastQ (no
  character limit in sequences headers or qualities).
  * Without reference genome.
* Robust:
  * Wrapp a standard software (zstd) well maintained and tested.
  * Decompression result is automaticly tested after each compression.
  * md5sum of the original file is stored to be automaticly tested after each
  decompression.
  * No fail on benchmark dataset composed by 722 files from Illumina and PacBio
  instruments.
* Performant:
  * Compression rate:
    * is better than standard text compression (up to 2 times better than gzip
    best). 
    * is less than specialised software (*************************) but it can work on all fastq and
    here are no nasty surprises on decompression.
  * compression/decompression time and compression ratio ********************************
* Userfriendly:
  * gzipped fastq can be directly take as input or write as output.
  * `zfq info` instantly provide the number of sequences and nucleotids stored
  in the file.

### How it works

Compress:

  1. Write number of reads, nucleotids, modification time and original md5sum
  in info file.
  2. Split FastQ three parts: headers, sequences (without new line) and qualities.
  3. Compress each part with zstd.
  4. Store all compressed files and input info in tar archive.
  5. Apply original modification time to archive.
  6. Decompress file in temporary file to compare md5sum of the original file
  and decompressed file.

Decompress:
  1. Extract files.
  2. Decompress with zstd.
  3. Merge each parts (sequences are splitted using quality length).
  4. Apply original modification time to decompressed file.
  5. Compare md5sum of the original file (from info file) and decompressed file.


## Benchmarks

### Software

* Text compression:
  * gzip (https://www.gnu.org/software/gzip/) in two modes: *default* and *best*.
  * zstd (https://github.com/facebook/zstd) in two modes: *13* and *ultra 22*.

* Sequences compression:
  * lfastqc (https://github.uconn.edu/sya12005/LFastqC)
  * lfqc (https://github.com/mariusmni/lfqc)
  * picard (https://broadinstitute.github.io/picard/command-line-overview.html) to convert as uBAM
  * quip (https://github.com/dcjones/quip)
  * zfq

### Dataset

 * 722 files
 * Sequencers types: Illumina (MiSeq, NextSeq and NovaSeq) and PacBio (Sequel 2)
 * Library: amplicon, capture and whole
 * Matrix: DNA, ctDNA and RNA

### Results
************************************


## Installation

### Requirements

* python (`>=3.7`)
* [zstd](https://github.com/facebook/zstd) (`>=1.4.4`) a fast lossless
compression algorithm developped by meta.

### Build

```
python -m pip install git+https://github.com/bialimed/zfq.git@1.0.0
```


## Usage example

### Compress fastq(.gz) file:
Command:
`zfq.py compress -i SRR.fastq.gz -o SRR.fastq.zfq -r`

Option:
In this example `-r/--remove` is used to remove zfq file after decompression. 

STDOUT:
```
zfq.py compress -i SRR.fastq.gz -o SRR.fastq.zfq
2023-09-05 11:48:20,483 -- [zfq.py][pid:3163205][INFO] -- Command: zfq.py compress -i SRR.fastq.gz -o SRR.fastq.zfq
2023-09-05 11:48:21,341 -- [zfq.py][pid:3163205][INFO] -- End of job
```

### Get information from original file:
Command:
`zfq.py info -i SRR.fastq.zfq`

STDOUT:
```
{'seq': 14615, 'nt': 1865822, 'md5': 'c1f5e805b3a076d5c58fa206f2c30ac5', 'mtime': 1693907258.333263}
```

### Convert zfq to fastq.gz
Command:
`zfq.py uncompress -i SRR.fastq.zfq -o SRR2.fastq.gz -r`

Option:
In this example `-r/--remove` is used to remove zfq file after decompression. 

STDOUT:
```
2023-09-05 11:55:42,348 -- [zfq.py][pid:3164218][INFO] -- Command: zfq.py uncompress -i SRR.fastq.zfq -o SRR2.fastq.gz -r
2023-09-05 11:55:44,066 -- [zfq.py][pid:3164218][INFO] -- End of job
```


## Copyright
2023 Laboratoire d'Anatomo-Cytopathologie de l'Institut Universitaire du Cancer
Toulouse - Oncopole
