# Running the missing CMS regions on AWS (region-parallel)

The national CMS parquet is missing 7 regions (Mahalapye, Ngami, North East,
Okavango, Serowe-Palapye, Southern, Tutume). They are independent, so we run all
7 in parallel on one spot EC2 instance and download the results. HiGHS is
open-source, so no solver license is needed.

WARNING: the payload contains PRIVATE Botswana MoH data. Use encrypted transfer
(scp over SSH), an encrypted EBS volume, and terminate + wipe when done.

Prereqs: AWS CLI configured; an EC2 key pair (`.pem`); a security group allowing
inbound SSH (port 22) from your IP.

## 1. Build the payload (local)

```bash
bash national_pipeline/aws/make_payload.sh   # -> national_pipeline/aws/payload.tar.gz (gitignored)
```

## 2. Launch a MEMORY-optimized spot instance (encrypted EBS)

This job is memory-bound: each region's adjustable-robust model peaks around
~10-15 GB, so 7 regions in parallel need ~80-100 GB. Use a memory-optimized
instance. r7i.4xlarge (16 vCPU, 128 GB) comfortably runs all 7 at once; step down
to r7i.2xlarge (8 vCPU, 64 GB) if you run ~4 at a time. Do NOT use a compute
instance like c7i.4xlarge (only 32 GB) — it will OOM, exactly like the cluster did.

Adjust REGION, KEY, SG, and the AMI (a current Ubuntu 22.04 x86_64 AMI).

```bash
aws ec2 run-instances \
  --image-id <ubuntu-22.04-ami-id> \
  --instance-type r7i.4xlarge \
  --instance-market-options MarketType=spot \
  --key-name <your-key> \
  --security-group-ids <sg-id> \
  --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":30,"Encrypted":true}}]' \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=cms-missing}]'
# record InstanceId and PublicDnsName from the output (or via: aws ec2 describe-instances)
```

## 3. Upload + run (encrypted scp, then the job)

```bash
HOST=ubuntu@<public-dns>
KEY=<path/to/key.pem>
scp -i "$KEY" national_pipeline/aws/payload.tar.gz national_pipeline/aws/run_on_ec2.sh "$HOST":~
ssh -i "$KEY" "$HOST" 'bash ~/run_on_ec2.sh'        # runs all 7 regions in parallel (a few hours)
```

Tip: run the ssh command inside `tmux`/`screen`, or append `> run.log 2>&1 &` on the
instance so a dropped connection does not kill the job.

## 4. Download the results

```bash
scp -i "$KEY" "$HOST":~/cms/national_pipeline/results/cms_results_missing.parquet \
    national_pipeline/results/
```

## 5. Merge locally into the full parquet

```bash
cd national_pipeline && python run_missing_regions.py merge   # -> cms_results_full.parquet
```

This concatenates the existing 11 regions with the new 7 into
`national_pipeline/cms_results_full.parquet` (the original `cms_results.parquet`
is never modified).

## 6. Wipe + terminate (data governance)

```bash
ssh -i "$KEY" "$HOST" 'rm -rf ~/cms ~/payload.tar.gz'
aws ec2 terminate-instances --instance-ids <instance-id>   # encrypted EBS is deleted on terminate
# remove the local payload too:
rm -f national_pipeline/aws/payload.tar.gz
```

## Notes

- Solver is `run_cms_two.SOLVER` (HiGHS). MOSEK breaks on this problem.
- The run is region-parallel (`ProcessPoolExecutor`, one worker per region). To go
  faster you would also parallelize the 3 policies within each region on a larger
  instance (a code change, not covered here).
- Each `run_region` is single-threaded, so more vCPUs beyond ~8 do not speed a
  single region; they only let more regions run at once (we have 7).
