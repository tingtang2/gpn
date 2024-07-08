import argparse
from Bio import SeqIO, bgzf
from Bio.Seq import Seq
from datasets import load_dataset
import gzip
import numpy as np
import os
import pandas as pd
import tempfile
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments

import gpn.model
from gpn.data import Genome, load_dataset_from_file_or_dir, token_input_id


max_lengths = {
    'LongSafari/hyenadna-tiny-1k-seqlen-hf': 1024,
    'LongSafari/hyenadna-small-32k-seqlen-hf': 32768,
    'LongSafari/hyenadna-medium-160k-seqlen-hf': 160000,
    'LongSafari/hyenadna-medium-450k-seqlen-hf': 450000,
    'LongSafari/hyenadna-large-1m-seqlen-hf': 1_000_000,
}


class CLMforVEPModel(torch.nn.Module):
    def __init__(self, model_path):
        super().__init__()
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path, trust_remote_code=True,
        )

    def log_likelihood(self, input_ids):
        B = input_ids.shape[0]
        labels = input_ids#.clone()
        logits = self.model(input_ids=input_ids).logits
        logits = logits.float()
        # Shift so that tokens < n predict n
        shift_logits = logits[..., :-1, :].contiguous()
        shift_labels = labels[..., 1:].contiguous()

        loss_fct = torch.nn.CrossEntropyLoss(reduction="none")
        shift_logits = shift_logits.view(-1, self.model.vocab_size)
        shift_labels = shift_labels.view(-1)
        # Enable model parallelism
        shift_labels = shift_labels.to(shift_logits.device)
        loss = loss_fct(shift_logits, shift_labels)
        res = -loss.reshape(B, -1).mean(dim=-1)
        return res

    def get_llr(self, input_ids_ref, input_ids_alt):
        return self.log_likelihood(input_ids_alt) - self.log_likelihood(input_ids_ref)

    def forward(
        self,
        input_ids_ref_fwd=None,
        input_ids_alt_fwd=None,
        input_ids_ref_rev=None,
        input_ids_alt_rev=None,
    ):
        llr_fwd = self.get_llr(input_ids_ref_fwd, input_ids_alt_fwd)
        llr_rev = self.get_llr(input_ids_ref_rev, input_ids_alt_rev)
        llr = (llr_fwd+llr_rev)/2
        return llr


def run_vep(
    variants, genome, tokenizer, model, window_size,
    per_device_batch_size=8, dataloader_num_workers=0,
):
    def tokenize(seqs):
        return tokenizer(
            seqs,
            padding=True,
            return_attention_mask=False,
        )["input_ids"]

    def get_tokenized_seq(vs):
        # we convert from 1-based coordinate (standard in VCF) to 
        # 0-based, to use with Genome
        chrom = np.array(vs["chrom"])
        n = len(chrom)
        pos = np.array(vs["pos"]) - 1
        start = pos - window_size//2
        end = pos + window_size//2

        chrom_size = genome.get_all_intervals().set_index("chrom").end

        unbounded_start = start.copy()
        unbounded_end = end.copy()

        for i in range(n):
            chrom_current = chrom[i]
            start[i] = max(0, start[i])
            end[i] = min(chrom_size[chrom_current], end[i])

        seq_fwd, seq_rev = zip(*(
            genome.get_seq_fwd_rev(chrom[i], start[i], end[i]) for i in range(n)
        ))
        seq_fwd = [x.upper() for x in seq_fwd]
        seq_rev = [x.upper() for x in seq_rev]

        ref_fwd = np.array(vs["ref"])
        alt_fwd = np.array(vs["alt"])
        ref_rev = np.array([str(Seq(x).reverse_complement()) for x in ref_fwd])
        alt_rev = np.array([str(Seq(x).reverse_complement()) for x in alt_fwd])

        pos_fwd = window_size // 2 - (start - unbounded_start)
        pos_rev = window_size // 2 - (unbounded_end - end) - 1

        def prepare_output(seq, pos, ref, alt):
            seq_ref = []
            seq_alt = []
            for i in range(n):
                assert seq[i][pos[i]] == ref[i], f"{seq[i][pos[i]]}, {ref[i]}"
                seq_ref.append(seq[i])
                one_seq_alt = list(seq[i])
                one_seq_alt[pos[i]] = alt[i]
                one_seq_alt = "".join(one_seq_alt)
                seq_alt.append(one_seq_alt)
            return tokenize(seq_ref), tokenize(seq_alt)

        res = {}
        res["input_ids_ref_fwd"], res["input_ids_alt_fwd"] = prepare_output(
            seq_fwd, pos_fwd, ref_fwd, alt_fwd
        )
        res["input_ids_ref_rev"], res["input_ids_alt_rev"] = prepare_output(
            seq_rev, pos_rev, ref_rev, alt_rev
        )
        return res

    variants.set_transform(get_tokenized_seq)
    training_args = TrainingArguments(
        output_dir=tempfile.TemporaryDirectory().name,
        per_device_eval_batch_size=per_device_batch_size,
        dataloader_num_workers=dataloader_num_workers,
        remove_unused_columns=False,
    )
    trainer = Trainer(model=model, args=training_args)
    return trainer.predict(test_dataset=variants).predictions


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run zero-shot variant effect prediction with AutoModelForMaskedLM"
    )
    parser.add_argument(
        "variants_path", type=str,
        help="Variants path. Needs the following columns: chrom,pos,ref,alt. pos should be 1-based",
    )
    parser.add_argument(
        "genome_path", type=str, help="Genome path (fasta, potentially compressed)",
    )
    parser.add_argument(
        "model_path", help="Model path (local or on HF hub)", type=str
    )
    parser.add_argument("output_path", help="Output path (parquet)", type=str)
    parser.add_argument(
        "--per-device-batch-size",
        help="Per device batch size",
        type=int,
        default=8,
    )
    parser.add_argument(
        "--tokenizer-path", type=str,
        help="Tokenizer path (optional, else will use model_path)",
    )
    parser.add_argument(
        "--dataloader-num-workers", type=int, default=0, help="Dataloader num workers"
    )
    parser.add_argument(
        "--split", type=str, default="test", help="Dataset split",
    )
    parser.add_argument(
        "--is-file", action="store_true", help="VARIANTS_PATH is a file, not directory",
    )
    args = parser.parse_args()

    variants = load_dataset_from_file_or_dir(
        args.variants_path, split=args.split, is_file=args.is_file,
    )
    subset_chroms = np.unique(variants["chrom"])
    genome = Genome(args.genome_path, subset_chroms=subset_chroms)

    df = variants.to_pandas()
    df["is_valid"] = True
    #df["is_valid"] = (
    #    (df.source == "ClinVar") |
    #    ((df.label=="Common") & (df.consequence.str.contains("missense")))
    #)
    # Additional code to select only 1000 from each label
    #valid_indices = df[df.is_valid].groupby('label').apply(lambda x: x.sample(min(len(x), 1000), random_state=1)).index.get_level_values(1)
    #df["is_valid"] = df.index.isin(valid_indices)

    print(df.is_valid.value_counts())
    variants = variants.select(np.where(df.is_valid)[0])

    tokenizer = AutoTokenizer.from_pretrained(
        args.tokenizer_path if args.tokenizer_path else args.model_path,
        trust_remote_code=True,
    )
    model = CLMforVEPModel(args.model_path)
    pred = run_vep(
        variants, genome, tokenizer, model, max_lengths[args.model_path],
        per_device_batch_size=args.per_device_batch_size,
        dataloader_num_workers=args.dataloader_num_workers,
    )
    directory = os.path.dirname(args.output_path)
    if directory != "" and not os.path.exists(directory):
        os.makedirs(directory)
    df.loc[df.is_valid, "score"] = pred
    print(df["score"])
    df[["score"]].to_parquet(args.output_path, index=False)
