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
$soft compress -i ${test_folder}/in.fastq -o $temp/$uniq.zfq -l WARNING \
&& \
$soft info -i $temp/$uniq.zfq > /dev/null \
&& \
$soft uncompress -i $temp/$uniq.zfq -o $temp/$uniq.fastq -l WARNING \
&& \
cmp ${test_folder}/in.fastq $temp/$uniq.fastq \
&& \
rm $temp/$uniq.fastq \
&& \
$soft uncompress -i $temp/$uniq.zfq -o $temp/$uniq.fastq.gz -r -l WARNING && gzip -d $temp/$uniq.fastq.gz \
&& \
cmp ${test_folder}/in.fastq $temp/$uniq.fastq \
&& \
rm $temp/$uniq.fastq \
&& \
# From fastq.gz
cp ${test_folder}/in.fastq $temp/${uniq}_in.fastq && gzip $temp/${uniq}_in.fastq \
&& \
$soft compress -i $temp/${uniq}_in.fastq.gz -o $temp/$uniq.zfq -l WARNING \
&& \
$soft info -i $temp/$uniq.zfq > /dev/null \
&& \
$soft uncompress -i $temp/$uniq.zfq -o $temp/$uniq.fastq -l WARNING \
&& \
cmp ${test_folder}/in.fastq $temp/$uniq.fastq \
&& \
rm $temp/$uniq.fastq \
&& \
$soft uncompress -i $temp/$uniq.zfq -o $temp/$uniq.fastq.gz -r  -l WARNING && gzip -d $temp/$uniq.fastq.gz \
&& \
cmp ${test_folder}/in.fastq $temp/$uniq.fastq \
&& \
rm $temp/${uniq}_in.fastq.gz $temp/$uniq.fastq \
&& \
# Log
echo -e "\033[92mSuccess\033[0m" || (echo -e "\033[91mError\033[0m" ; exit 1)
