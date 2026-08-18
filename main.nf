#!/usr/bin/env nextflow
/*
 * pgx-interpretation-pipeline -- Nextflow orchestration (Plan §5 Phase 9).
 *
 * This workflow does exactly one thing: for each sample in a samplesheet,
 * run `pgx_interpreter.cli report` once (see pgx_interpreter/cli.py's own
 * module docstring for why one process per SAMPLE, not one process per
 * gene, was the deliberate design choice -- report.py's PGxResult objects
 * don't round-trip through JSON cleanly enough to split gene-calling and
 * report-assembly across separate Nextflow processes without a real
 * fidelity risk). All of the actual PGx logic -- variant parsing, allele
 * calling, phenotype assignment, Tier 2 recommendations, report rendering
 * -- lives in the Python package and was already built and validated in
 * Phases 1-8; this file's only job is fanning that CLI call out across
 * however many samples a real batch run needs, with Nextflow's usual
 * per-process isolation, retry, and resume semantics.
 *
 * IMPORTANT, stated plainly rather than glossed over (see HANDOFF.md's
 * Phase 9 session note and docs/VALIDATION.md §4 for the same pattern
 * already established with PharmCAT): this file's syntax was hand-written
 * and reviewed against Nextflow's documented DSL2 process/channel
 * semantics, and the underlying `pgx_interpreter.cli report` command it
 * shells out to was directly tested (tests/test_cli.py, real subprocess
 * invocations, 9 passing tests). A live `nextflow run main.nf` was NOT
 * executed in this Cowork sandbox -- the real Nextflow launcher requires
 * downloading its Java runtime from `www.nextflow.io/releases` (or GitHub
 * release assets), and both hosts return `403 blocked-by-allowlist` from
 * this sandbox's own network proxy, the same category of restriction
 * already documented for PharmCAT. Run it on a machine with real network
 * access (e.g. your WSL machine) to confirm; the "Getting started" section
 * below gives the exact command using this repo's own test fixtures, so a
 * first real run needs no external data.
 */

nextflow.enable.dsl = 2

params.input                = null
params.outdir               = 'results'
params.genome_build         = 'GRCh38'
params.genes                = 'TPMT,DPYD,SLCO1B1,CYP2C19'
params.formats               = 'json,tsv,html,markdown'
params.with_recommendations  = true
params.evidence_cache_dir    = null  // null -> pgx_interpreter.cli's own default cache location
params.help                  = false

def helpMessage() {
    log.info """
    pgx-interpretation-pipeline
    ============================
    Usage:
      nextflow run main.nf --input samplesheet.csv [options]

    Required:
      --input                 Path to a samplesheet CSV with columns: sample_id,vcf

    Optional:
      --outdir                Output directory (default: ${params.outdir})
      --genome_build           GRCh37 or GRCh38 (default: ${params.genome_build})
      --genes                  Comma-separated gene list (default: ${params.genes})
      --formats                Comma-separated report formats: json,tsv,html,markdown,docx
                                (default: ${params.formats}; docx needs python-docx installed)
      --with_recommendations   true/false -- attach Tier 2 drug recommendations (default: ${params.with_recommendations})
      --evidence_cache_dir     Override the Tier 2 evidence cache directory

    Example (using this repo's own test fixtures, no external data needed):
      nextflow run main.nf --input assets/samplesheet_example.csv \\
          --evidence_cache_dir tests/fixtures/evidence
    """.stripIndent()
}

if (params.help) {
    helpMessage()
    exit 0
}

if (!params.input) {
    error "Missing required parameter --input (path to a samplesheet CSV with columns: sample_id,vcf). Run with --help for usage."
}

process PGX_REPORT {
    tag "${sample_id}"
    publishDir "${params.outdir}/${sample_id}", mode: 'copy'

    input:
    tuple val(sample_id), path(vcf)

    output:
    path("${sample_id}.*"), emit: report_files

    script:
    def rec_flag   = params.with_recommendations ? '--with-recommendations' : '--no-recommendations'
    def cache_arg  = params.evidence_cache_dir ? "--evidence-cache-dir '${params.evidence_cache_dir}'" : ''
    """
    PYTHONPATH="${projectDir}" python3 -m pgx_interpreter.cli report \\
        --vcf '${vcf}' \\
        --sample-id '${sample_id}' \\
        --genome-build '${params.genome_build}' \\
        --genes '${params.genes}' \\
        --formats '${params.formats}' \\
        ${rec_flag} \\
        ${cache_arg} \\
        --out-dir .
    """
}

workflow {
    if (params.help) {
        return
    }

    samples_ch = Channel
        .fromPath(params.input, checkIfExists: true)
        .splitCsv(header: true)
        .map { row ->
            if (!row.sample_id || !row.vcf) {
                error "Samplesheet row missing sample_id or vcf column: ${row}"
            }
            tuple(row.sample_id, file(row.vcf))
        }

    PGX_REPORT(samples_ch)
}
