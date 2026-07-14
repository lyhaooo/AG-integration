from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DatasetSpec:
    name: str
    folder: str
    baseline: str


DATASETS = (
    DatasetSpec("Barnes", "Barnes", "Barnes.csv"),
    DatasetSpec("Brandimarte", "Brandimarte", "Brandimarte.csv"),
    DatasetSpec("Dauzere", "Dauzere", "Dauzere.csv"),
    DatasetSpec("Hurink_edata", "Hurink_edata", "hurink_edata.csv"),
    DatasetSpec("Hurink_rdata", "Hurink_rdata", "Hurink_rdata.csv"),
    DatasetSpec("Hurink_vdata", "Hurink_vdata", "hurink_vdata.csv"),
)


@dataclass(frozen=True)
class FJSPInstance:
    name: str
    path: Path
    optimal: float
    num_jobs: int
    num_machines: int
    operations: list[list[list[tuple[int, int]]]]


def _read_baselines(path: Path) -> dict[str, float]:
    values: dict[str, float] = {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.reader(handle):
            if len(row) < 2:
                continue
            try:
                values[Path(row[0].strip()).stem.lower()] = float(row[1])
            except ValueError:
                continue
    return values


def parse_fjs(path: Path) -> tuple[int, int, list[list[list[tuple[int, int]]]]]:
    lines = [line.split() for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    if not lines or len(lines[0]) < 2:
        raise ValueError(f"无效 FJSP 文件: {path.name}")
    num_jobs, num_machines = int(lines[0][0]), int(lines[0][1])
    if len(lines) < num_jobs + 1:
        raise ValueError(f"FJSP 作业行不足: {path.name}")
    jobs: list[list[list[tuple[int, int]]]] = []
    for job_index in range(num_jobs):
        tokens = [int(value) for value in lines[job_index + 1]]
        operation_count, cursor = tokens[0], 1
        job: list[list[tuple[int, int]]] = []
        for _ in range(operation_count):
            choices, cursor = tokens[cursor], cursor + 1
            machines: list[tuple[int, int]] = []
            for _ in range(choices):
                machine, duration = tokens[cursor], tokens[cursor + 1]
                cursor += 2
                machines.append((machine - 1, duration))
            if not machines:
                raise ValueError(f"工序没有可选机器: {path.name}")
            job.append(machines)
        jobs.append(job)
    return num_jobs, num_machines, jobs


def load_dataset(data_root: Path, spec: DatasetSpec) -> list[FJSPInstance]:
    baselines = _read_baselines(data_root / spec.baseline)
    instances: list[FJSPInstance] = []
    for path in sorted((data_root / spec.folder).glob("*.fjs")):
        optimal = baselines.get(path.stem.lower())
        if optimal is None or optimal <= 0:
            continue
        jobs, machines, operations = parse_fjs(path)
        instances.append(FJSPInstance(path.stem, path, optimal, jobs, machines, operations))
    return instances


def dataset_catalog(data_root: Path) -> list[dict]:
    catalog = []
    for spec in DATASETS:
        count = len(list((data_root / spec.folder).glob("*.fjs")))
        catalog.append({"name": spec.name, "instance_count": count})
    return catalog

