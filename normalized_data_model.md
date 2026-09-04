# Normalized Data Model — proposal v0.1
 
Target: one DuckDB database per case (`derived/case.duckdb`), fed from per-evidence Parquet files (`derived/<EV-id>/parquet/<table>.parquet`) so any evidence can be re-ingested or dropped without rebuilding the whole case. All family tables share a **core** column set; a single long-format `events` table provides the cross-artifact timeline.
 
## Principles
 
1. **One normalized record ⇐ exactly one source record.** Every row keeps `source_ref` pointing to the exact origin (evidence id, artifact, file inside the archive, row/offset). The original record is kept verbatim in `raw` (JSON). Nothing is dropped, only projected.
2. **Deterministic identity.** `record_id = sha256(ev_id | artifact | source_ref)`. Re-ingesting the same evidence yields the same ids → ingest is idempotent.
3. **Timestamps**: `TIMESTAMP` in UTC, microsecond precision. Unknown → `NULL`, never epoch 0. Every timestamp column has a sibling `<col>_desc` only where the semantic is ambiguous; otherwise the column name carries it (`ts_created`, `ts_modified`, …). Per-host `clock_skew_seconds` lives in `hosts` and is applied at **query time**, never at ingest.
4. **Wide + long.** Family tables are wide (one row per artifact entry, several timestamps). The `events` table is long (one row per timestamp of a record) and is *generated* from the family tables — it is the timeline and the correlation backbone.
5. **OS-agnostic columns, OS-specific extras.** Columns common to all OSes are first-class; OS/tool specifics go into `extra` (STRUCT/JSON). No `sid` column on Linux rows, no `uid` on Windows rows: use the generic `user_id` + `user_id_type`.
6. **Paths**: keep `path` as found; add `path_norm` (forward slashes, lowercase on Windows/macOS, case preserved on Linux, drive letter kept). Never normalize away information.
7. **Controlled vocabularies** (enums below) are closed lists; anything else goes to `extra` and is reported by the ingest as "unmapped value" so the vocabulary can be extended deliberately.
8. **Mappings as data.** `mappings/<tool>/<artifact>.yaml` declares source-field → target-column for each parser output (Velociraptor artifact, plaso parser, Dissect plugin, Hayabusa, Volatility). Adding a source = adding a YAML, not code. Each mapping declares the target `family`, the `artifact` name (ForensicArtifacts vocabulary), and optional post-processing (e.g. split `cmdline` into `exe_path` + `args`).
9. **Versioned.** `schema_version` stored in the DB; `parser_version` and `mapping_version` on every row.
## Core columns (present on every family table)
 
| Column | Type | Notes |
|---|---|---|
| `record_id` | VARCHAR | sha256, see above |
| `case_id` | VARCHAR | |
| `ev_id` | VARCHAR | evidence id from manifest |
| `host` | VARCHAR | canonical hostname (from `hosts`) |
| `os` | ENUM | `windows`, `linux`, `macos`, `android`, `ios`, `unknown` |
| `artifact` | VARCHAR | ForensicArtifacts name (`WindowsPrefetchFiles`, `LinuxAuthLogs`, …) or `custom:<name>` |
| `family` | ENUM | table name (redundant, useful in `events`) |
| `user_name` | VARCHAR | as observed |
| `user_id` | VARCHAR | SID / uid / GUID |
| `user_id_type` | ENUM | `sid`, `uid`, `guid`, `email`, `unknown` |
| `source_tool` | VARCHAR | `velociraptor`, `plaso`, `dissect`, `hayabusa`, `zircolite`, `volatility3`, `hindsight`, `manual` |
| `source_path` | VARCHAR | path of the parsed file inside the evidence |
| `source_ref` | VARCHAR | row number / offset / event record id / MFT entry |
| `parser_version` | VARCHAR | |
| `mapping_version` | VARCHAR | |
| `ingested_at` | TIMESTAMP | |
| `tags` | VARCHAR[] | free tags set by hunts/agent/analyst (`analyst:reviewed`, `lead:P3`) |
| `extra` | JSON | unmapped source fields |
| `raw` | JSON | original record verbatim |
 
## Reference tables
 
**`hosts`** — `host`, `os`, `os_version`, `build`, `arch`, `domain`, `tz` (IANA), `clock_skew_seconds`, `ips` (VARCHAR[]), `ev_ids` (VARCHAR[]), `role`, `criticity`. Filled from `case.yaml` + inventory; `case.yaml` wins on conflict.
 
**`evidence`** — mirror of `manifest.json` for joins: `ev_id`, `host`, `kind`, `sha256`, `collected_at`, `time_range_start`, `time_range_end`.
 
## Family tables
 
### `events` (long, generated)
Timeline view; regenerated from the family tables after every ingest step.
`ts`, `ts_desc` (ENUM: `created`, `modified`, `accessed`, `metadata_changed`, `executed`, `first_run`, `last_run`, `logged`, `visited`, `downloaded`, `logon`, `logoff`, `installed`, `deleted`, `renamed`, `connected`, `written`, `other`), `family`, `record_id`, `host`, `user_name`, `summary` (one-line human string built by the mapping), `path_norm`, `technique_ids` (VARCHAR[]), plus core lineage columns (`ev_id`, `artifact`, `source_tool`).
 
### `fs_entries` — filesystem metadata
MFT, ext4/XFS inodes (Dissect), APFS/HFS+ catalog, KAPE file lists.
`path`, `path_norm`, `name`, `ext`, `is_dir`, `is_deleted`, `size`, `inode` (MFT entry / inode number), `parent_inode`, `ts_created`, `ts_modified`, `ts_accessed`, `ts_metadata_changed`, `fn_ts_created`, `fn_ts_modified`, `fn_ts_accessed`, `fn_ts_metadata_changed` (Windows $FILE_NAME set; NULL elsewhere), `owner`, `mode`, `attributes` (VARCHAR[]), `hash_md5`, `hash_sha1`, `hash_sha256`, `ads_names` (VARCHAR[]), `volume`.
 
### `fs_journal` — filesystem change journals
USN Journal, $LogFile, ext4 journal, fsevents, Windows Search? no — only change journals.
`ts`, `op` (ENUM: `create`, `delete`, `rename_old`, `rename_new`, `modify`, `truncate`, `attr_change`, `security_change`, `hardlink`, `other`), `path`, `path_norm`, `name`, `inode`, `parent_inode`, `usn`, `reason_raw`, `volume`.
 
### `log_events` — structured logs
EVTX, syslog, journald, auditd, macOS unified log, application logs.
`ts`, `channel` (`Security`, `Sysmon/Operational`, `auth.log`, `journald`, `unifiedlog:<subsystem>`), `provider`, `event_id` (VARCHAR — EID, auditd type, unified-log category), `level` (ENUM: `critical`, `error`, `warning`, `info`, `verbose`, `unknown`), `computer`, `pid`, `process_name`, `message`, `fields` (JSON — parsed EventData / audit key-values / unified log payload), `record_number`.
 
### `executions` — evidence of program execution
Prefetch, Amcache, Shimcache, BAM/DAM, UserAssist, SRUM app usage, shell histories, `lastlog`, LSQuarantine, Sysmon EID 1 / auditd EXECVE **projected** (the row stays in `log_events`; `derived_from` links them).
`ts_first`, `ts_last`, `run_count`, `exe_path`, `exe_path_norm`, `exe_name`, `args`, `cmdline`, `cwd`, `pid`, `ppid`, `parent_path`, `hash_sha1`, `hash_sha256`, `signer`, `loaded_files` (VARCHAR[], Prefetch), `volume`, `derived_from` (record_id or NULL), `evidence_type` (ENUM: `prefetch`, `amcache`, `shimcache`, `bam`, `userassist`, `srum`, `shell_history`, `quarantine`, `process_creation_log`, `audit`, `other`).
 
### `processes` — memory / live state
Volatility 3 pslist/psscan/cmdline/netscan, Velociraptor pslist.
`pid`, `ppid`, `name`, `path`, `cmdline`, `ts_created`, `ts_exited`, `session_id`, `is_hidden`, `is_injected`, `injection_detail`, `handles_count`, `threads_count`, `dlls` (VARCHAR[]), `snapshot_ts`.
 
### `persistence` — autostart mechanisms
Run/RunOnce, services, scheduled tasks, WMI subscriptions, Winlogon, IFEO, startup folders, cron, systemd units/timers, rc scripts, LaunchAgents/Daemons, login items, kernel extensions, browser extensions (also in `browser`).
`mechanism` (ENUM: `run_key`, `service`, `scheduled_task`, `wmi_subscription`, `winlogon`, `ifeo`, `startup_folder`, `cron`, `systemd_unit`, `systemd_timer`, `rc_script`, `launch_agent`, `launch_daemon`, `login_item`, `kext`, `driver`, `browser_extension`, `shell_profile`, `other`), `name`, `location` (registry key / unit file / plist path), `target_path`, `target_path_norm`, `args`, `trigger` (schedule, event, boot, logon), `enabled`, `run_as`, `ts_created`, `ts_modified`, `hash_sha256`, `signer`.
 
### `accounts` — local and directory principals
SAM, `/etc/passwd` + `shadow` + `group`, macOS dslocal plists, AD extracts (ntds), account creation/deletion/modification events **projected** from logs.
`user_name`, `user_id`, `user_id_type`, `full_name`, `domain`, `groups` (VARCHAR[]), `is_admin`, `is_disabled`, `is_service`, `home`, `shell`, `ts_created`, `ts_modified`, `ts_last_logon`, `ts_password_changed`, `ts_deleted`, `logon_count`, `derived_from`.
 
### `auth_events` — authentication and privilege events
EVTX 4624/4625/4634/4648/4672/4768/4769/4776, sshd, PAM, sudo, `su`, login/screensaver on macOS, RDP/VPN logs.
`ts`, `event_type` (ENUM: `logon_success`, `logon_failure`, `logoff`, `explicit_credentials`, `privilege_assigned`, `ticket_request`, `ticket_granted`, `password_change`, `sudo`, `su`, `lock`, `unlock`, `other`), `logon_type` (VARCHAR — Windows type or `ssh`, `console`, `rdp`, `vpn`), `user_name`, `user_id`, `domain`, `target_user_name`, `src_ip`, `src_host`, `src_port`, `dst_host`, `auth_package`, `outcome` (ENUM: `success`, `failure`, `unknown`), `failure_reason`, `session_id`, `derived_from`.
 
### `browser` — browser activity
Chrome/Edge/Brave, Firefox, Safari: history, downloads, cookies, extensions, bookmarks, form data, cache index.
`browser` (ENUM: `chrome`, `edge`, `brave`, `firefox`, `safari`, `opera`, `other`), `profile`, `entry_type` (ENUM: `visit`, `download`, `cookie`, `extension`, `bookmark`, `search`, `form`, `cache`, `session`), `ts`, `ts_end`, `url`, `domain`, `title`, `referrer`, `transition`, `visit_count`, `target_path`, `target_path_norm`, `size`, `mime`, `state` (download complete/cancelled), `extension_id`, `extension_name`.
 
### `user_activity` — traces of interactive use
LNK, JumpLists, ShellBags, MRU/RecentDocs, OfficeMRU, WordWheel, RDP cache, Spotlight/Recent items, Dock, `.viminfo`, `.lesshst`.
`activity_type` (ENUM: `lnk`, `jumplist`, `shellbag`, `mru`, `recent_docs`, `office_mru`, `search_query`, `rdp_cache`, `spotlight`, `recent_items`, `editor_history`, `other`), `ts`, `ts_desc`, `target_path`, `target_path_norm`, `target_name`, `target_exists`, `target_size`, `source_app`, `volume_serial`, `volume_label`, `machine_id`, `drive_type`, `net_share`.
 
### `network` — network state and configuration
Netscan/netstat, WLAN profiles, hosts files, ARP, DNS cache, VPN configs, firewall logs **projected**, proxy/SRUM network usage.
`entry_type` (ENUM: `connection`, `listening`, `dns_cache`, `hosts_entry`, `arp`, `wifi_profile`, `interface`, `vpn_profile`, `firewall_rule`, `flow`, `other`), `ts`, `ts_end`, `proto`, `src_ip`, `src_port`, `dst_ip`, `dst_port`, `domain`, `state`, `pid`, `process_name`, `bytes_in`, `bytes_out`, `ssid`, `bssid`, `interface`, `direction`.
 
### `installed_software` — packages and applications
Uninstall keys, MSI, `dpkg`/`rpm`, Homebrew, `/Applications`, app stores, drivers.
`name`, `version`, `publisher`, `ts_installed`, `ts_modified`, `install_path`, `install_path_norm`, `source` (`uninstall_key`, `msi`, `dpkg`, `rpm`, `brew`, `app_bundle`, `store`, `driver`), `is_removed`.
 
### `registry` — Windows registry (generic)
Anything not projected into a semantic family stays queryable here.
`hive` (`SYSTEM`, `SOFTWARE`, `SAM`, `SECURITY`, `NTUSER`, `UsrClass`, `Amcache`, `other`), `key_path`, `key_path_norm`, `value_name`, `value_type`, `value_data` (VARCHAR), `value_data_raw` (BLOB), `ts_last_write`, `is_deleted`.
 
### `config_entries` — non-registry configuration
`/etc/*`, sshd_config, sudoers, plists, `.bashrc`, PAM, hosts.allow, launchd overrides.
`file_path`, `file_path_norm`, `section`, `key`, `value`, `ts_modified`, `is_default`.
 
### `files_of_interest` — collected file bodies and their analysis
Binaries, scripts, documents, quarantine, attachments; YARA/hash/signature results.
`path`, `path_norm`, `size`, `hash_md5`, `hash_sha1`, `hash_sha256`, `mime`, `magic`, `is_signed`, `signer`, `signature_valid`, `entropy`, `yara_matches` (VARCHAR[]), `strings_of_interest` (VARCHAR[]), `stored_at` (path under `derived/`), `ts_created`, `ts_modified`.
 
### `detections` — output of every detection engine
Sigma (Hayabusa/Zircolite/Chainsaw), hunts (SQL), YARA, IOC matches, agent-proposed leads once validated.
`ts`, `engine` (ENUM: `sigma`, `hunt`, `yara`, `ioc`, `analyst`, `agent`), `rule_id`, `rule_name`, `rule_version`, `level` (ENUM: `informational`, `low`, `medium`, `high`, `critical`), `technique_ids` (VARCHAR[]), `tactic_ids` (VARCHAR[]), `dfiq_question_ids` (VARCHAR[]), `matched_record_ids` (VARCHAR[]), `matched_family`, `host`, `user_name`, `summary`, `status` (ENUM: `new`, `reviewed`, `lead`, `finding`, `false_positive`), `lead_id`, `finding_id`.
 
### `iocs` — indicators known to the case
`value`, `ioc_type` (ENUM: `ip`, `domain`, `url`, `md5`, `sha1`, `sha256`, `email`, `filename`, `path`, `registry_key`, `mutex`, `user_agent`, `account`, `other`), `source` (`analyst`, `report:<name>`, `derived`), `ts_added`, `added_by`, `confidence` (ENUM: `low`, `medium`, `high`), `first_seen_record_id`, `notes`.
 
## Cross-cutting rules
 
- **Projection, not duplication of authority.** When a log event is also meaningful as an execution / auth / account / network fact, the row is projected into the semantic table with `derived_from = <log_events.record_id>`. The log row remains the source of truth; the projection makes correlation queries simple.
- **`summary` generation** is part of the mapping and must be deterministic and short (≤ 160 chars): `"[prefetch] first run of C:\Users\j.dupont\AppData\Local\Temp\upd.exe (run_count=3)"`.
- **Hunts** are SQL files in `hunts/<family>/<name>.sql` with a YAML header (id, title, DFIQ question ids, ATT&CK ids, applicable OS, output description). They read family tables and write into `detections` with `engine = 'hunt'`. They must be re-runnable (delete-then-insert by `rule_id`).
- **MCP result caps**: every `mcp-evidence` tool returns at most N rows (default 50, hard max 500), truncates VARCHAR to 512 chars, never returns `raw` unless explicitly requested with `include_raw=true` and the case type allows it.
- **Retention of `raw`**: mandatory. It is the audit trail from normalized row back to source bytes; storage cost is accepted.
## Open decisions
 
1. `events` as a materialized table (fast, rebuilt per ingest) vs a VIEW (always fresh, slower on large cases). Proposal: materialized, rebuilt incrementally per `ev_id`.
2. Whether `registry` should also be projected to a `windows_events`-like long form or only reachable through `events` via `ts_last_write`. Proposal: only via `events`.
3. Parquet per evidence *and* per table (many small files) vs one Parquet per evidence with a `family` column. Proposal: per table — simpler schemas, faster selective loads.
4. Android/iOS: reuse `fs_entries`, `browser`, `installed_software`, `log_events` + an `app_data` family for parsed SQLite app databases (ALEAPP/iLEAPP output). Deferred to phase 2.

