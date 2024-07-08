# GPN (Genomic Pre-trained Network)
[![hgt_genome_392c4_a47ce0](https://user-images.githubusercontent.com/5766420/228109137-85d48559-d1ae-4c9a-94b5-c79fc06ad45d.png)](  https://genome.ucsc.edu/s/gbenegas/gpn-arabidopsis)

Code and resources from [GPN paper](https://doi.org/10.1073/pnas.2311219120) and [GPN-MSA paper](https://doi.org/10.1101/2023.10.10.561776).

## Table of contents
- [Installation](#installation)
- [Minimal usage](#minimal-usage)
- [GPN](#gpn)
- [GPN-MSA](#gpn-msa)
- [Citation](#citation)

## Installation
```bash
pip install git+https://github.com/songlab-cal/gpn.git
```

## Minimal usage
```python
import gpn.model
from transformers import AutoModelForMaskedLM

model = AutoModelForMaskedLM.from_pretrained("songlab/gpn-brassicales")
# or
model = AutoModelForMaskedLM.from_pretrained("songlab/gpn-msa-sapiens")
```

## GPN
Can also be called GPN-SS (single sequence).

### Examples
* Play with the model: `examples/ss/basic_example.ipynb` [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/songlab-cal/gpn/blob/main/examples/ss/basic_example.ipynb)

### Code and resources from specific papers
* [*Arabidopsis thaliana*](analysis/arabidopsis)

### Training on your own data
1. [Snakemake workflow to create a dataset](workflow/make_dataset)
    - Can automatically download data from NCBI given a list of accessions, or use your own fasta files.
2. Training
    - Will automatically detect all available GPUs.
    - Track metrics on [Weights & Biases](https://wandb.ai/)
    - Implemented models: `ConvNet`, `GPNRoFormer` (Transformer)
    - Specify config overrides: e.g. `--config_overrides n_layers=30`
    - Example:
```bash
WANDB_PROJECT=your_project torchrun --nproc_per_node=$(echo $CUDA_VISIBLE_DEVICES | awk -F',' '{print NF}') -m gpn.ss.run_mlm --do_train --do_eval \
    --fp16 --report_to wandb --prediction_loss_only True --remove_unused_columns False \
    --dataset_name results/dataset --tokenizer_name gonzalobenegas/tokenizer-dna-mlm \
    --soft_masked_loss_weight_train 0.1 --soft_masked_loss_weight_evaluation 0.0 \
    --weight_decay 0.01 --optim adamw_torch \
    --dataloader_num_workers 16 --seed 42 \
    --save_strategy steps --save_steps 10000 --evaluation_strategy steps \
    --eval_steps 10000 --logging_steps 10000 --max_steps 120000 --warmup_steps 1000 \
    --learning_rate 1e-3 --lr_scheduler_type constant_with_warmup \
    --run_name your_run --output_dir your_output_dir --model_type ConvNet \
    --per_device_train_batch_size 512 --per_device_eval_batch_size 512 --gradient_accumulation_steps 1 \
    --torch_compile
```
3. Extract embeddings
    - Input file requires `chrom`, `start`, `end`
    - Example:
```bash
torchrun --nproc_per_node=$(echo $CUDA_VISIBLE_DEVICES | awk -F',' '{print NF}') -m gpn.ss.get_embeddings windows.parquet genome.fa.gz 100 your_output_dir \
    results.parquet --per-device-batch-size 4000 --is-file --dataloader-num-workers 16
```
4. Variant effect prediction
    - Input file requires `chrom`, `pos`, `ref`, `alt`
    - Example:
```bash
torchrun --nproc_per_node=$(echo $CUDA_VISIBLE_DEVICES | awk -F',' '{print NF}') -m gpn.ss.run_vep variants.parquet genome.fa.gz 512 your_output_dir results.parquet \
    --per-device-batch-size 4000 --is-file --dataloader-num-workers 16
```

## GPN-MSA

### Examples
* Play with the model: `examples/msa/basic_example.ipynb`
* Variant effect prediction: `examples/msa/vep.ipynb`
* Training (human): `examples/msa/training.ipynb`

### Code and resources from specific papers
* [Human](analysis/human)

### Training on other species (e.g. plants)
Under construction.

## Citation
GPN:
```bibtex
@article{benegas2023dna,
    author = {Gonzalo Benegas  and Sanjit Singh Batra  and Yun S. Song },
    title = {DNA language models are powerful predictors of genome-wide variant effects},
    journal = {Proceedings of the National Academy of Sciences},
    volume = {120},
    number = {44},
    pages = {e2311219120},
    year = {2023},
    doi = {10.1073/pnas.2311219120},
    URL = {https://www.pnas.org/doi/abs/10.1073/pnas.2311219120},
    eprint = {https://www.pnas.org/doi/pdf/10.1073/pnas.2311219120},
}
```

GPN-MSA:
```bibtex
@article{benegas2023gpnmsa,
	author = {Gonzalo Benegas and Carlos Albors and Alan J. Aw and Chengzhong Ye and Yun S. Song},
	title = {GPN-MSA: an alignment-based DNA language model for genome-wide variant effect prediction},
	elocation-id = {2023.10.10.561776},
	year = {2023},
	doi = {10.1101/2023.10.10.561776},
	publisher = {Cold Spring Harbor Laboratory},
	URL = {https://www.biorxiv.org/content/early/2023/10/11/2023.10.10.561776},
	eprint = {https://www.biorxiv.org/content/early/2023/10/11/2023.10.10.561776.full.pdf},
	journal = {bioRxiv}
}
```