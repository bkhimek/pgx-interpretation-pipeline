# PharmCAT live comparison — runbook

This is the one remaining open item from Phase 7's original validation checklist (`docs/VALIDATION.md` §4): a **live** PharmCAT run, sample by sample, compared against this project's own calls. Section 4 already documents a real, honest reason this couldn't be done from inside the Cowork sandbox this project was built in — no Java 17+, no bcftools/htslib, and the PharmCAT installer/release-asset hosts are blocked by that sandbox's own network allowlist. None of those blockers apply on your WSL machine, which is why this is a "you run it, I help interpret it" runbook rather than something delivered pre-built.

## What you'll need

- **Java 17+** (PharmCAT's own minimum; 25 is currently recommended). Check with `java -version`.
- **bcftools >= 1.18** and **htslib >= 1.18** (for `bgzip`/`tabix`) on `PATH`. PharmCAT's VCF Preprocessor calls these directly.
- **A GRCh38 reference genome FASTA.** This is the heaviest step here — PharmCAT's preprocessor normalizes/left-aligns variants against it, and there's no way around needing it. Budget a few GB of disk and download time.
- **PharmCAT itself.**

Since your shell prompt shows `(base)`, you likely already have conda/mamba — that's the easiest path for all of the above:

```bash
conda create -n pharmcat -c bioconda -c conda-forge pharmcat bcftools htslib openjdk=17
conda activate pharmcat
pharmcat_pipeline --version   # sanity check
```

If `bioconda` doesn't have a current `pharmcat` package by the time you try this, fall back to PharmCAT's own one-line installer (`curl -fsSL https://get.pharmcat.org | bash`) — see `pharmcat.clinpgx.org/using/Setup-PharmCAT/` for the current instructions either way, since install methods can change.

## Getting a GRCh38 reference

If you don't already have one on your WSL machine:

```bash
mkdir -p ~/refs && cd ~/refs
curl -o GRCh38.fa.gz https://ftp.ensembl.org/pub/release-110/fasta/homo_sapiens/dna/Homo_sapiens.GRCh38.dna.primary_assembly.fa.gz
gunzip GRCh38.fa.gz
samtools faidx GRCh38.fa   # from the same conda env (samtools ships with htslib)
```

(Any GRCh38 primary-assembly FASTA works — if you already have one from another project, point at that instead and skip this step.)

## Test samples — reuse this repo's own real GeT-RM fixtures

`tests/fixtures/getrm/{tpmt,dpyd,slco1b1,cyp2c19}/*.vcf` are real GeT-RM reference-material genotypes, each already validated against this project's own calls (`docs/VALIDATION.md` §3) and each citing its real consensus diplotype in its own header comments. Running the same files through PharmCAT gives a genuine three-way comparison for free: **real GeT-RM ground truth vs. this project's call vs. PharmCAT's call** — not just a two-way "does PharmCAT agree with us" check.

A good first-pass subset (one interesting case per gene, not all 31 — expand later if this goes smoothly):

| Gene | Sample | Why this one |
|---|---|---|
| TPMT | `tests/fixtures/getrm/tpmt/NA12753.vcf` | The flagship unphased-ambiguity case (`*1/*3A` vs `*3B/*3C`) — see if PharmCAT's own "AND"/"OR" partial-variant-list behavior (`docs/VALIDATION.md` §4) looks the way its docs describe against a real sample. |
| DPYD | `tests/fixtures/getrm/dpyd/HG00118.vcf` | A real sample with variants at two independent DPYD loci at once — this project declines to call it; worth seeing how PharmCAT's own multi-locus handling actually behaves here. |
| SLCO1B1 | `tests/fixtures/getrm/slco1b1/NA10847.vcf` | Dosage-inferred `*15/*5` — a clean, unambiguous real case, good first test for whether PharmCAT's preprocessor even accepts this repo's minimal per-gene VCF format at all (see caveat below). |
| CYP2C19 | `tests/fixtures/getrm/cyp2c19/GM17203.vcf` | The real compound-heterozygous `*2/*17` sample that independently confirmed this project's central architectural design decision (`docs/VALIDATION.md` §3) — the single most interesting case to see PharmCAT's own take on. |

## A real unknown, stated plainly rather than glossed over

This repo's VCF fixtures are deliberately minimal — 2-5 positions per file, exactly the defining variants for one gene, no surrounding genomic context. PharmCAT's VCF Preprocessor is built around full-coverage VCFs and **might** reject or warn on a file this sparse (e.g. missing contig-length metadata, no calls at PharmCAT's other expected PGx positions for the same gene). This has not been tested — there was no way to test it from the Cowork sandbox this project was built in. Try the SLCO1B1 sample first (structurally simplest); if the preprocessor errors out or behaves oddly, that's a real, useful finding to report back, not a failure — it would mean the next step is either relaxing the preprocessor's strictness settings (it has flags for this) or sourcing fuller VCFs for the same Coriell sample IDs (many GeT-RM samples are also 1000 Genomes participants with full public VCF coverage available from EBI/NCBI).

## Running it

```bash
conda activate pharmcat
pharmcat_pipeline \
    --reference ~/refs/GRCh38.fa \
    tests/fixtures/getrm/slco1b1/NA10847.vcf \
    -o /tmp/pharmcat_out
```

`pharmcat_pipeline` runs preprocessing, the Named Allele Matcher, the Phenotyper, and the Reporter in one shot, producing a JSON report (and an HTML one) under `/tmp/pharmcat_out`. Repeat for each sample in the table above (or loop over all of `tests/fixtures/getrm/`).

## What to send back

For each sample: the PharmCAT JSON output (or just the relevant gene section — diplotype call, phenotype, any warnings/messages PharmCAT attached), plus whatever error or warning text appeared if the preprocessor had trouble with the minimal VCF. Paste it in chat or attach the files — either works. From there, the actual comparison write-up (a real Section 4 for `docs/VALIDATION.md`, replacing the current "attempted, found infeasible" language) is something to do together in the next session, sample by sample, the same rigor as every other comparison in this project.
