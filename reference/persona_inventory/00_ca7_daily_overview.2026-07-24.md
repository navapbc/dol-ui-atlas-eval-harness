# NJ DOL LOOPS — CA-7 Daily Batch Schedule: Overview

This knowledge space covers the **daily batch schedule** of the NJ Department of Labor
LOOPS mainframe system, as scheduled by CA-7 (the job scheduler). It contains the
schedule itself, the JCL for every scheduled job, the COBOL source reachable from those
jobs, and analysis documents produced during the AWS Transform modernization assessment.

## What the daily schedule is

Every processing day, CA-7 releases a network of batch jobs. The network root is
**L200DSHD** (the daily shutdown/kickoff job): it triggers the CICS shutdown chain and
the subsystem processing chains, and everything else follows via job-completion
triggers. The daily forecast used here (`DOLDAILYD061526`, taken 2026-06-15) contains
**1,892 scheduled job occurrences (1,886 distinct jobs)** across these subsystems:

| SYS | Jobs | What it is |
|---|---|---|
| LOP | 1,018 | Unemployment Insurance benefits processing (jobs `L2*`, `Z*`) |
| DABS | 564 | Disability & Family Leave Insurance benefits (jobs `D2*`) |
| IMS | 128 | IMS database utility/maintenance chains |
| TRA | 82 | Training/appeals-related processing |
| WDP | 66 | Wage data processing |
| RMS, B187, CICS, NJCFS, WAGE, LOP/SAVE, I/O | ~30 | Small operational families (print routing, state accounting interface, CICS control) |

The full job → trigger → JCL-member map is in `01_schedule_job_table.md`.

## Key daily business flows

- **DABS payment cycle (`D2PAD1xx`)**: payment triggers are generated (D2PAD150),
  de-duplicated and split into 10 database ranges (D2PAD152), fed into regular payments,
  followed by adjustments (D2PAD140/D2PAD146/D2PAD148) and reporting chains.
  Family Leave (FLI) records are split from Disability (DABS) records throughout via the
  FLI indicator set by program DABI0020.
- **UI continued-claim / certification processing (LOP `L2*` chains)**: certification
  intake, edits, pay/no-pay decisioning, and downstream extracts. (The Weekly
  Certification module has its own dedicated knowledge space.)
- **Database backup/maintenance chains (`D2DB*`, IMS jobs)**: nightly shutdown,
  image-copy/backup, change-accumulation, restart.
- **Interfaces**: FTP/NDM transfer jobs (`L2FTP*`), email/report distribution, NJCFS
  state accounting, Treasury/check-related handoffs.

## What is in this space

1. **The schedule** — `01_schedule_job_table.md`: every scheduled job, its subsystem,
   nesting level, and triggering job/dataset.
2. **JCL source** — `source/jcl/` folder: 1,864 JCL members (library JCLIBALL), the
   jobs the schedule runs. One file per member, named `<MEMBER>.txt`.
3. **COBOL source** — `source/cobol/` and `source/copybooks/` folders: 773 COBOL
   programs and copybooks, one file per member,
   (library LIBRMASTRALL) statically reachable from the scheduled JCL.
4. **Analysis documents** — how this slice was scoped (`02_...`), source inventory and
   quality (`03_...`), and coverage gaps (`04_...`).
5. **Business rules (BRE)** — `bre_*.md` files (added after each AWS Transform Business
   Rule Extraction run): per-program business rules and program flows.

## Scale

- 1,864 JCL members, ~256K effective lines of JCL
- 473 COBOL programs (~400K effective LOC) + 300 copybooks
- Highest-complexity programs: UIMB0004, UIMB0025, UIMB0003 (DB2 batch),
  DXCR227M, DXCR227E (wage/benefit reconciliation family)

## Honest limitations (read before answering coverage questions)

- **Not all called programs have source here.** 677 programs invoked by these jobs are
  absent from the available source libraries, most notably the `TDC*` report-program
  family (371), `FLC*` (47), and `DAB*` (39). Jobs that call them (for example the DABS
  reporting steps) have their JCL here, but the program logic is a black box.
- **UIMI vs UIMB naming**: JCL invokes DB2 programs by load-module names `UIMI*`; the
  source members are named `UIMB*` (the PROGRAM-ID inside is the UIMB name). The source
  is present, but tooling that matches by member name may report them missing.
- Dataset-level lineage is partial: no catalog (LISTCAT) export was available, so
  dataset references cannot be fully resolved to physical files.
- IMS PSB/DBD gen was not available (101 missing PSBs), so IMS database access details
  come from program source only.
- The schedule is a single-day forecast; jobs DEMANDed ad hoc or on monthly/quarterly
  schedules are out of scope here (the monthly schedule is a separate, smaller slice).
