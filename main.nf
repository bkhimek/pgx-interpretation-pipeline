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
 * already documented for PharmCAT. A first real run (2026-08-19, Nextflow
 * 26.04.3) surfaced three real bugs, fixed the same day as they were found,
 * one at a time as each successive run reached further: (1) nextflow.config's
 * strict config parser rejected a bare top-level `def` variable declaration
 * mixed with config blocks (see nextflow.config's own comment); (2) this
 * file's DSL2 parser rejected bare top-level `if` statements (the
 * `--help`/missing-`--input` checks) sitting outside any process/workflow/
 * function -- both checks now live inside the `workflow { }` block below;
 * (3) the `PGX_REPORT` process's `publishDir` referenced the per-task input
 * variable `sample_id` in a plain interpolated string, which Nextflow
 * evaluates immediately at process-definition time (before any task's
 * inputs exist) unless wrapped in an explicit closure -- unlike `tag`, which
 * Nextflow does treat a plain string as dynamic for. (1) and (2) were
 * genuine newer-Nextflow-strictness changes; (3) was a real bug in the
 * original write, not version-specific. Run it on a machine with real
 * network access (e.g. your WSL machine) to confirm the fix; the "Getting
 * started" section below gives the exact command using this repo's own
 * test fixtures, so a first real run needs no external data.
 */

nextflow.enable.dsl = 2

// Parameter defaults live in nextflow.config's `params { }` block, not
// here -- deliberately not duplicated. Nextflow's documented parameter
// precedence puts values assigned directly in the pipeline script (this
// file) at LOWEST precedence, below both the command line and config
// files, so a second `params.x = ...` set here would be redundant at best;
// keeping exactly one place params are declared removes any doubt about
// which one is authoritative (a real, if usually harmless, footgun the
// nf-core community has already been burned by, per its own docs on this
// exact pattern).

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
      --cyp2c19_voriconazole   true/false -- add a second CYP2C19 section recommended for voriconazole
                                instead of the default clopidogrel (default: ${params.cyp2c19_voriconazole});
                                no-op unless CYP2C19 is in --genes and recommendations are enabled
      --thiopurine_drug        mercaptopurine, thioguanine, or azathioprine -- selects which CPIC
                                compound TPMT+NUDT15 table (Table 2/3/4) the compound recommendation
                                uses (default: mercaptopurine, i.e. leave unset); no-op unless both
                                TPMT and NUDT15 are in --genes and recommendations are enabled

    Example (using this repo's own test fixtures, no external data needed):
      nextflow run main.nf --input assets/samplesheet_example.csv \\
          --evidence_cache_dir tests/fixtures/evidence
    """.stripIndent()
}

process PGX_REPORT {
    tag "${sample_id}"
    // `tag` is one of a small set of directives Nextflow treats as
    // implicitly dynamic from a plain interpolated string (see Nextflow's
    // own docs: `tag "$sample_id"` is the documented pattern). `publishDir`
    // is NOT in that set -- referencing a per-task input variable
    // (`sample_id`, bound below in `input:`) requires an EXPLICIT closure,
    // or Nextflow evaluates the string immediately at process-definition
    // time, before any task's inputs are bound, and fails with "No such
    // variable: sample_id" (confirmed for real, 2026-08-19, Nextflow
    // 26.04.3 -- this was a genuine bug in the original write, not a
    // newer-Nextflow-strictness change like the two prior fixes this
    // session).
    publishDir(
        path: { "${params.outdir}/${sample_id}" },
        mode: 'copy'
    )

    input:
    tuple val(sample_id), path(vcf)

    output:
    path("${sample_id}.*"), emit: report_files

    script:
    def rec_flag    = params.with_recommendations ? '--with-recommendations' : '--no-recommendations'
    def cache_arg   = params.evidence_cache_dir ? "--evidence-cache-dir '${params.evidence_cache_dir}'" : ''
    def vori_flag   = params.cyp2c19_voriconazole ? '--cyp2c19-voriconazole' : ''
    def thio_arg    = params.thiopurine_drug ? "--thiopurine-drug '${params.thiopurine_drug}'" : ''
    """
    PYTHONPATH="${projectDir}" python3 -m pgx_interpreter.cli report \\
        --vcf '${vcf}' \\
        --sample-id '${sample_id}' \\
        --genome-build '${params.genome_build}' \\
        --genes '${params.genes}' \\
        --formats '${params.formats}' \\
        ${rec_flag} \\
        ${cache_arg} \\
        ${vori_flag} \\
        ${thio_arg} \\
        --out-dir .
    """
}

workflow {
    // Both checks below were formerly bare top-level `if` statements --
    // moved in here per this file's own header comment (a newer Nextflow
    // release rejects executable statements outside a process, workflow,
    // or function).
    if (params.help) {
        helpMessage()
        exit 0
    }

    if (!params.input) {
        error "Missing required parameter --input (path to a samplesheet CSV with columns: sample_id,vcf). Run with --help for usage."
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
