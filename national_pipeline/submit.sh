#!/bin/bash
#SBATCH --job-name=cms_simulation
#SBATCH --output=/scratch/network/el3205/cms/national_pipeline/logs/cms_%j.out
#SBATCH --error=/scratch/network/el3205/cms/national_pipeline/logs/cms_%j.err
#SBATCH --time=7-00:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G

mkdir -p /scratch/network/el3205/cms/national_pipeline/logs
module load anaconda3/2025.6
conda activate cms-env

cd /scratch/network/el3205/cms/national_pipeline
python run_cms_two.py
EOF