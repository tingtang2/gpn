# GPN-MSA application to *Homo sapiens*

## Resources
* [Model](https://huggingface.co/songlab/gpn-msa-sapiens)
* [MSA](https://huggingface.co/datasets/songlab/multiz100way)
* [Training windows](https://huggingface.co/datasets/songlab/gpn-msa-sapiens-dataset)
* [Benchmark variants (including predictions)](https://huggingface.co/datasets/songlab/human_variants)
* [Full ~530M gnomAD variants (including predictions)](https://huggingface.co/datasets/songlab/gnomad)
* [Logo track at UCSC Genome Browser](https://genome.ucsc.edu/s/gbenegas/gpn-msa-sapiens)

## Reproducing the analysis
* Dependencies: `workflow/envs/general.yaml`
* Running Snakemake: `snakemake --cores all`
