#!/bin/bash

# Parameters
soft="zfq.py"
if [ "$#" -eq 1 ]; then
    soft=$1
fi
test_folder=`dirname $0`
uniq=`python3 -c 'import uuid; print(uuid.uuid4())'`
temp=`python3 -c 'import tempfile; print(tempfile.gettempdir())'`

# From fastq
$soft compress -i ${test_folder}/in.fastq -o $temp/$uniq.zfq \
&& \
$soft info -i $temp/$uniq.zfq \
&& \
$soft decompress -i $temp/$uniq.zfq -o $temp/$uniq.fastq \
&& \
cmp ${test_folder}/in.fastq $temp/$uniq.fastq \
&& \
$soft decompress -i $temp/$uniq.zfq -o $temp/$uniq.fastq.gz -r && gzip -d $temp/$uniq.fastq.gz \
&& \
cmp ${test_folder}/in.fastq $temp/$uniq.fastq \
&& \
rm $temp/$uniq.fastq \
&& \
# From fastq.gz
cp ${test_folder}/in.fastq $temp/${uniq}_in.fastq && gzip $temp/${uniq}_in.fastq \
&& \
$soft compress -i $temp/${uniq}_in.fastq.gz -o $temp/$uniq.zfq \
&& \
$soft info -i $temp/$uniq.zfq \
&& \
$soft decompress -i $temp/$uniq.zfq -o $temp/$uniq.fastq && gzip $temp/$uniq.fastq \
&& \
cmp $temp/${uniq}_in.fastq.gz $temp/$uniq.fastq.gz \
&& \
$soft decompress -i $temp/$uniq.zfq -o $temp/$uniq.fastq.gz -r \
&& \
cmp $temp/${uniq}_in.fastq.gz $temp/$uniq.fastq.gz \
&& \
rm $temp/${uniq}_in.fastq.gz $temp/$uniq.fastq.gz \
&& \
# Log
echo "Success"
