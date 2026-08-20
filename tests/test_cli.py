"""Phase 9 tests: pgx_interpreter.cli, exercised via real subprocess
invocations of `python3 -m pgx_interpreter.cli ...` -- the exact same
invocation `main.nf`'s PGX_REPORT process makes (see main.nf's own
comments). Testing through a subprocess rather than calling `run_report()`
directly is deliberate here: it is the one place in this test suite that
actually exercises argument parsing, exit codes, and stdout/stderr as an
external caller (Nextflow, or a person at a terminal) would see them --
everything below `main()` is already covered indirectly by every other
gene/evidence/report test in this suite.

Network-free by design, same as tests/test_evidence.py: every recommending
test below points `--evidence-cache-dir` at `tests/fixtures/evidence/`, so
the live ClinPGx API is never actually called.

Plain `assert` statements only -- must run identically under pytest and
tests/run_tests.py (DEVELOPMENT_WORKFLOW.md item 2). Subprocess-based tests
work fine under both runners since `subprocess` is stdlib.
"""
import csv
import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_CACHE_DIR = REPO_ROOT / "tests" / "fixtures" / "evidence"
TPMT_NORMAL_VCF = REPO_ROOT / "tests" / "fixtures" / "tpmt" / "normal_function.vcf"
TPMT_HET_VCF = REPO_ROOT / "tests" / "fixtures" / "tpmt" / "het_reduced_function.vcf"
ALL_NORMAL_VCF = REPO_ROOT / "assets" / "example_sample_all_normal.vcf"


def _run_cli(args: list, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "pgx_interpreter.cli", *args],
        cwd=cwd,
        env={"PYTHONPATH": str(REPO_ROOT)},
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_report_all_five_genes_normal_with_recommendations():
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp)
        result = _run_cli(
            [
                "report",
                "--vcf", str(ALL_NORMAL_VCF),
                "--sample-id", "DEMO001",
                "--genome-build", "GRCh38",
                "--formats", "json,tsv",
                "--evidence-cache-dir", str(EVIDENCE_CACHE_DIR),
                "--out-dir", str(out_dir),
            ]
        )
        assert result.returncode == 0, result.stderr
        assert (out_dir / "DEMO001.json").is_file()
        assert (out_dir / "DEMO001.tsv").is_file()

        payload = json.loads((out_dir / "DEMO001.json").read_text())
        genes = {g["gene"] for g in payload["genes"]}
        assert genes == {"TPMT", "DPYD", "SLCO1B1", "CYP2C19", "NUDT15"}
        for section in payload["genes"]:
            assert section["predicted_phenotype"]["confidence"] == "supported"
            # Every gene should have a Tier 2 recommendation attached, since
            # the evidence cache has all four guidelines and every phenotype
            # here is a "Normal"/"Normal function" call this project's
            # recommendation tables recognize. TPMT+NUDT15 get theirs via
            # the compound path (both genes present in the default --genes
            # list) -- see evidence.recommend_compound_thiopurine().
            assert section["gene_drug_relationship"]["drug"] is not None

        by_gene = {g["gene"]: g for g in payload["genes"]}
        assert by_gene["TPMT"]["gene_drug_relationship"]["drug"] == "mercaptopurine"
        assert by_gene["NUDT15"]["gene_drug_relationship"]["drug"] == "mercaptopurine"
        assert by_gene["TPMT"]["gene_drug_relationship"] == by_gene["NUDT15"]["gene_drug_relationship"]

        rows = list(csv.DictReader(io.StringIO((out_dir / "DEMO001.tsv").read_text()), delimiter="\t"))
        assert len(rows) == 5
        assert {r["gene"] for r in rows} == {"TPMT", "DPYD", "SLCO1B1", "CYP2C19", "NUDT15"}


def test_report_single_gene_subset():
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp)
        result = _run_cli(
            [
                "report",
                "--vcf", str(TPMT_NORMAL_VCF),
                "--sample-id", "TPMT_ONLY",
                "--genes", "tpmt",  # lower-case on purpose -- must be case-insensitive
                "--formats", "json",
                "--evidence-cache-dir", str(EVIDENCE_CACHE_DIR),
                "--out-dir", str(out_dir),
            ]
        )
        assert result.returncode == 0, result.stderr
        payload = json.loads((out_dir / "TPMT_ONLY.json").read_text())
        assert len(payload["genes"]) == 1
        assert payload["genes"][0]["gene"] == "TPMT"


def test_report_partial_vcf_coverage_reports_insufficient_data_not_a_guess():
    # A real, honest scenario a Nextflow-orchestrated batch run could hit:
    # a VCF that only covers one gene's positions, but the report is
    # requested for all four (the CLI's default). The other three genes
    # must come back insufficient_data, not a silently-guessed *1/*1.
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp)
        result = _run_cli(
            [
                "report",
                "--vcf", str(TPMT_NORMAL_VCF),
                "--sample-id", "PARTIAL",
                "--formats", "json",
                "--evidence-cache-dir", str(EVIDENCE_CACHE_DIR),
                "--out-dir", str(out_dir),
            ]
        )
        assert result.returncode == 0, result.stderr
        payload = json.loads((out_dir / "PARTIAL.json").read_text())
        by_gene = {g["gene"]: g for g in payload["genes"]}
        assert by_gene["TPMT"]["predicted_phenotype"]["confidence"] == "supported"
        for gene in ("DPYD", "SLCO1B1", "CYP2C19"):
            assert by_gene[gene]["predicted_phenotype"]["confidence"] == "insufficient_data"
            assert by_gene[gene]["gene_drug_relationship"]["drug"] is None


def test_no_recommendations_flag_leaves_gene_drug_relationship_empty():
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp)
        result = _run_cli(
            [
                "report",
                "--vcf", str(TPMT_NORMAL_VCF),
                "--sample-id", "NOREC",
                "--genes", "TPMT",
                "--formats", "json",
                "--no-recommendations",
                "--out-dir", str(out_dir),
            ]
        )
        assert result.returncode == 0, result.stderr
        payload = json.loads((out_dir / "NOREC.json").read_text())
        assert payload["genes"][0]["gene_drug_relationship"]["drug"] is None


def test_unknown_gene_fails_loudly_with_nonzero_exit():
    with tempfile.TemporaryDirectory() as tmp:
        result = _run_cli(
            [
                "report",
                "--vcf", str(TPMT_NORMAL_VCF),
                "--sample-id", "X",
                "--genes", "TPMT,NOTAREALGENE",
                "--out-dir", tmp,
            ]
        )
        assert result.returncode != 0
        assert "NOTAREALGENE" in result.stderr
        assert not (Path(tmp) / "X.json").exists()


def test_missing_vcf_fails_loudly_with_nonzero_exit():
    with tempfile.TemporaryDirectory() as tmp:
        result = _run_cli(
            [
                "report",
                "--vcf", str(Path(tmp) / "does_not_exist.vcf"),
                "--sample-id", "X",
                "--out-dir", tmp,
            ]
        )
        assert result.returncode != 0
        assert "does_not_exist.vcf" in result.stderr


def test_unknown_format_fails_loudly_before_touching_the_filesystem():
    with tempfile.TemporaryDirectory() as tmp:
        result = _run_cli(
            [
                "report",
                "--vcf", str(TPMT_NORMAL_VCF),
                "--sample-id", "X",
                "--genes", "TPMT",
                "--formats", "json,pdf",  # PDF is explicitly out of scope, see report.py
                "--out-dir", tmp,
            ]
        )
        assert result.returncode != 0
        assert "pdf" in result.stderr
        assert not any(Path(tmp).iterdir())


def test_ambiguous_phenotype_correctly_gets_no_recommendation():
    # TPMT's flagship *3A unphased-ambiguity case (Plan §3a): confidence is
    # "ambiguous", not "supported" -- recommend() must not attach a drug
    # recommendation to a call this project itself isn't confident about.
    star3a_vcf = REPO_ROOT / "tests" / "fixtures" / "tpmt" / "star3a_unphased_ambiguous.vcf"
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp)
        result = _run_cli(
            [
                "report",
                "--vcf", str(star3a_vcf),
                "--sample-id", "AMBIG",
                "--genes", "TPMT",
                "--formats", "json",
                "--evidence-cache-dir", str(EVIDENCE_CACHE_DIR),
                "--out-dir", str(out_dir),
            ]
        )
        assert result.returncode == 0, result.stderr
        payload = json.loads((out_dir / "AMBIG.json").read_text())
        section = payload["genes"][0]
        assert section["predicted_phenotype"]["confidence"] == "ambiguous"
        assert section["gene_drug_relationship"]["drug"] is None


def test_nudt15_requested_alone_gets_no_recommendation_no_tpmt_to_pair_with():
    # A real, documented limitation, not a bug: CPIC's dosing tables are
    # keyed on the joint TPMT+NUDT15 phenotype, so a NUDT15-only report has
    # no confident recommendation to attach -- see
    # evidence.recommend_compound_thiopurine()'s and genes/nudt15.py's own
    # docstrings.
    nudt15_normal_vcf = REPO_ROOT / "tests" / "fixtures" / "nudt15" / "normal_function.vcf"
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp)
        result = _run_cli(
            [
                "report",
                "--vcf", str(nudt15_normal_vcf),
                "--sample-id", "NUDT15_ONLY",
                "--genes", "NUDT15",
                "--formats", "json",
                "--evidence-cache-dir", str(EVIDENCE_CACHE_DIR),
                "--out-dir", str(out_dir),
            ]
        )
        assert result.returncode == 0, result.stderr
        payload = json.loads((out_dir / "NUDT15_ONLY.json").read_text())
        assert payload["genes"][0]["predicted_phenotype"]["confidence"] == "supported"
        assert payload["genes"][0]["gene_drug_relationship"]["drug"] is None


def test_tpmt_and_nudt15_together_get_the_compound_recommendation():
    # Confirms the compound path is reachable through a real subprocess
    # invocation, not just through evidence.py's own unit tests -- the same
    # "at least one real end-to-end check per code path" discipline as
    # every other CLI test in this file.
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp)
        result = _run_cli(
            [
                "report",
                "--vcf", str(ALL_NORMAL_VCF),
                "--sample-id", "PAIR",
                "--genes", "TPMT,NUDT15",
                "--formats", "json",
                "--evidence-cache-dir", str(EVIDENCE_CACHE_DIR),
                "--out-dir", str(out_dir),
            ]
        )
        assert result.returncode == 0, result.stderr
        payload = json.loads((out_dir / "PAIR.json").read_text())
        by_gene = {g["gene"]: g for g in payload["genes"]}
        assert by_gene["TPMT"]["gene_drug_relationship"]["drug"] == "mercaptopurine"
        assert by_gene["NUDT15"]["gene_drug_relationship"]["drug"] == "mercaptopurine"


def test_cyp2c19_voriconazole_flag_adds_a_second_cyp2c19_section():
    # report.py's renderers have no gene-uniqueness assumption (confirmed
    # directly in cli.py's own docstring before choosing this design) --
    # this flag should produce TWO "CYP2C19" sections, one per drug.
    cyp2c19_normal_vcf = REPO_ROOT / "tests" / "fixtures" / "cyp2c19" / "normal_function.vcf"
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp)
        result = _run_cli(
            [
                "report",
                "--vcf", str(cyp2c19_normal_vcf),
                "--sample-id", "VORI",
                "--genes", "CYP2C19",
                "--formats", "json,tsv",
                "--evidence-cache-dir", str(EVIDENCE_CACHE_DIR),
                "--cyp2c19-voriconazole",
                "--out-dir", str(out_dir),
            ]
        )
        assert result.returncode == 0, result.stderr
        payload = json.loads((out_dir / "VORI.json").read_text())
        cyp2c19_sections = [g for g in payload["genes"] if g["gene"] == "CYP2C19"]
        assert len(cyp2c19_sections) == 2
        drugs = {s["gene_drug_relationship"]["drug"] for s in cyp2c19_sections}
        assert drugs == {"clopidogrel", "voriconazole"}

        rows = list(csv.DictReader(io.StringIO((out_dir / "VORI.tsv").read_text()), delimiter="\t"))
        assert len(rows) == 2
        assert {r["recommended_drug"] for r in rows} == {"clopidogrel", "voriconazole"}


def test_cyp2c19_voriconazole_flag_is_a_noop_when_cyp2c19_not_requested():
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp)
        result = _run_cli(
            [
                "report",
                "--vcf", str(TPMT_NORMAL_VCF),
                "--sample-id", "NOVORI",
                "--genes", "TPMT",
                "--formats", "json",
                "--evidence-cache-dir", str(EVIDENCE_CACHE_DIR),
                "--cyp2c19-voriconazole",
                "--out-dir", str(out_dir),
            ]
        )
        assert result.returncode == 0, result.stderr
        payload = json.loads((out_dir / "NOVORI.json").read_text())
        assert len(payload["genes"]) == 1
        assert payload["genes"][0]["gene"] == "TPMT"


def test_written_file_paths_are_printed_to_stdout():
    # main.nf needs a predictable, parseable way to know what got written --
    # one absolute/relative path per line on stdout, nothing else.
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp)
        result = _run_cli(
            [
                "report",
                "--vcf", str(TPMT_NORMAL_VCF),
                "--sample-id", "X",
                "--genes", "TPMT",
                "--formats", "json,tsv",
                "--no-recommendations",
                "--out-dir", str(out_dir),
            ]
        )
        assert result.returncode == 0, result.stderr
        printed_lines = [line for line in result.stdout.splitlines() if line.strip()]
        assert len(printed_lines) == 2
        assert all(Path(line).is_file() for line in printed_lines)
