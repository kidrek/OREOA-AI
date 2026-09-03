# Referentiel d'artefacts ForensicArtifacts

Referentiel amont (ForensicArtifacts, Apache-2.0) telecharge et bake dans l'image a
chaque build (`doctor fix`) - jamais reference a l'execution, jamais edite localement.
Version exacte bakes : trace in-image `/referentiels/traces/` et champ `referentiels`
du manifest d'affaire (consigne a l'ingestion).

## Usage (execution conteneurisee via dt)

```
dt python3 /work/scripts/referentiels.py artefacts match  <manifest>   # rapprochement collections
dt python3 /work/scripts/referentiels.py artefacts expand <NomArtefact> # sources resolues + outils
dt python3 /work/scripts/referentiels.py artefacts index  /work/catalogue/artefacts.md  # regen index
dt python3 /work/scripts/referentiels.py artefacts check                  # integrite
```

## Rattachement aux signaux du catalogue

Le referentiel decrit les **emplacements de collecte** ; la logique de detection reste
dans les catalogues SF (catalogue/windows.md, linux.md, memoire.md, reseau.md) et les
chaines de correlation. Rattachement principal (amont 731 definitions, extraits) :

| Signal | Artefacts du referentiel | Note |
|--------|--------------------------|------|
| SF-W-001 Service cree | `WindowsEventLogs` | EventID 7045 (System.evtx) |
| SF-W-002 Run/RunOnce | `WindowsRegistryFilesAndTransactionLogs` | ruche NTUSER.DAT par utilisateur |
| SF-W-003 Tache planifiee | `WindowsScheduledTasks` | + journaux 4698/4699 (WindowsEventLogs) |
| SF-W-010/011 PowerShell, exe temporaire | `WindowsEventLogs`, `WindowsPrefetchFiles`, `WindowsAMCacheHveFile` | PowerShell Operational couvert par *.evtx |
| SF-W-012/013 UserAssist, MountPoints2 | `WindowsRegistryFilesAndTransactionLogs` | ruches NTUSER.DAT |
| SF-W-020/021 PsExec, logon type 3 | `WindowsEventLogs` | Security.evtx 4624/7045 |
| SF-W-030/031 lsass, comsvcs | `WindowsEventLogs` (Sysmon 10) + memoire volatile | SF-M-007 en complement |
| SF-W-040 Journal efface | `WindowsEventLogs` | EventID 1102 |
| SF-L-001/002/003 SSH burst, root | `LinuxAuthLogs` | + `LinuxSecureLogs` si present |
| SF-L-004 authorized_keys | `SSHAuthorizedKeysFiles` | par utilisateur |
| SF-L-010 sudo | `LinuxAuthLogs`, `UnixSudoersConfigurationFile` | |
| SF-L-011/012 download+exec, /tmp | `BashShellHistoryFile`, `ShellHistoryFile`, `RootUserShellHistory` | |
| SF-L-020 crontab | `LinuxCronTabs` | + `LinuxSystemdTimers`, `LinuxAtJobs` |
| SF-L-021 nouveau compte | `UnixPasswdFile`, `UnixShadowFile` | |
| SF-L-030 purge journaux | `LinuxAuthLogs`, `LinuxSysLogFiles`, `LinuxSystemdJournalLogs` | |
| SF-M-001 a SF-M-021 (memoire) | hors referentiel fichiers | dump volatile : `connaissances/memoire/exploitation-volatility.md` |
| SF-R-001 a SF-R-010 (reseau) | capture : hors referentiel fichiers | journaux corrélables : `WindowsFirewallLogFile`, `UFWLogFile`, `UnixHostsFile` |

## Regles

1. Un artefact absent d'une collecte est un **ecart** (acquisition incomplere) : le signal
   du catalogue reste testable uniquement sur les collections presentes - jamais de
   conclusion d'absence de compromission (regle catalogue)
2. Les definitions amont ne sont jamais modifiees : un artefact specifique au SI analyse
   se cree dans `referentiels-kit/artifacts/` (suffixe `Kit`)
3. Un signal du catalogue sans artefact correspondant = candidat a une contribution amont
   (PR au depot ForensicArtifacts) - tracer dans le journal de l'affaire puis en REX

<!-- genere:artefacts:debut -->
Index genere depuis le referentiel bake (731 definitions, amont + kit) - ne pas editer cette section.

| Artefact | OS | Sources | Description |
|----------|----|---------|-------------|
| `AllUsersAppDataEnvironmentVariable` | Windows | 1 REGISTRY_VALUE | The %ProgramData% environment variable. |
| `AllUsersProfileEnvironmentVariable` | Windows | 1 REGISTRY_KEY | The %AllUsersProfile% environment variable. |
| `AnacronFiles` | Linux | 1 FILE | Anacron files. |
| `ApacheAccessLogs` | Linux,Windows | 2 FILE | Location where Apache access logs are stored |
| `ApacheConfigurationFolder` | Linux | 1 FILE | Location where Apache keeps configuration files |
| `ApacheDefaultSiteConfigurationFile` | Linux | 1 FILE | Location where Apache keeps the default site configuration file. |
| `ApacheErrorLogs` | Linux,Windows | 2 FILE | Location where Apache error logs are stored |
| `ApacheKafkaLogFiles` | Linux | 1 FILE | Apache Kafka Log files |
| `AptitudeLogFiles` | Linux | 1 FILE | Linux aptitude package manager log files. |
| `APTSources` | Linux | 1 FILE | APT package sources list |
| `APTTrustKeys` | Linux | 1 FILE | APT trusted keys |
| `BashShellConfigurationFile` | Darwin,Linux,Windows | 3 FILE | Bourne Again shell (bash) configuration files. |
| `BashShellHistoryFile` | Darwin,Linux,Windows | 2 FILE | Bourne Again shell (bash) history files. |
| `BashShellSessionFile` | Darwin | 1 FILE | Bourne Again shell (bash) session files. |
| `Bit9LocalCache` | Windows | 1 FILE | Bit9 local cache database. |
| `BourneShellHistoryFile` | Darwin,Linux,Windows | 2 FILE | Bourne shell (sh) history files. |
| `BrowserCache` | Darwin,Linux,Windows | 1 ARTIFACT_GROUP | Web browser cache of multiple web browsers. |
| `BrowserHistory` | Darwin,Linux,Windows | 1 ARTIFACT_GROUP | Web browser history of multiple web browsers. |
| `ChromeExtensionRegistryKeys` | Windows | 1 REGISTRY_KEY | Chrome extensions installed by writing windows registry keys. |
| `ChromeFileSystem` | Darwin,Linux,Windows | 3 FILE | Google Chrome, Beta, Canary and Chromium File System files. The File System directory back... |
| `ChromeIndexedDB` | Darwin,Linux,Windows | 3 FILE | Google Chrome, Beta, Canary and Chromium IndexedDB files. The IndexedDB directory contains... |
| `ChromeLocalStorage` | Darwin,Linux,Windows | 3 FILE | Google Chrome, Beta, Canary and Chromium Local Storage files. Chrome 60 and earlier versio... |
| `ChromePlatformNotifications` | Darwin,Linux,Windows | 3 FILE | Google Chrome Platform Notifications LevelDB. The Platform Notifications directory contain... |
| `ChromePreferences` | Darwin,Linux,Windows | 3 FILE | Chrome Preferences file. |
| `ChromeSessionStorage` | Darwin,Linux,Windows | 3 FILE | Google Chrome, Beta, Canary and Chromium Sessions and Session Storage files. The Sessions ... |
| `ChromeStorage` | Darwin,Linux,Windows | 1 ARTIFACT_GROUP | Google Chrome, Canary and Chromium browser artifacts for Storage APIs. Includes Web Storag... |
| `ChromiumBasedBrowsersCache` | Darwin,Linux,Windows | 3 FILE | Caches of multiple Chromium-based browsers (Google Chrome, Brave, Chromium, Yandex, Opera,... |
| `ChromiumBasedBrowsersCookiesDatabaseFile` | Darwin,Linux,Windows | 3 FILE | Cookies database file for multiple Chromium-based browsers, such as Google Chrome, Brave, ... |
| `ChromiumBasedBrowsersExtensionActivitySQLiteDatabaseFile` | Darwin,Linux,Windows | 3 FILE | Browser Extension Activity SQLite database file for Chromium-based browsers, such as Googl... |
| `ChromiumBasedBrowsersExtensions` | Darwin,Linux,Windows | 3 FILE | Browser extension files for multiple Chromium-based browsers, such as Google Chrome, Brave... |
| `ChromiumBasedBrowsersFaviconsDatabaseFile` | Darwin,Linux,Windows | 3 FILE | Favicons database file for multiple Chromium-based browsers, such as Google Chrome, Brave,... |
| `ChromiumBasedBrowsersHistoryDatabaseFile` | Darwin,Linux,Windows | 3 FILE | Browsing history database file for multiple Chromium-based browsers, such as Google Chrome... |
| `ChromiumBasedBrowsersLoginDataDatabaseFile` | Darwin,Linux,Windows | 3 FILE | Login Data database file for multiple Chromium-based browsers, such as Google Chrome, Brav... |
| `ChromiumBasedBrowsersWebDataDatabaseFile` | Darwin,Linux,Windows | 3 FILE | Web Data database file for multiple Chromium-based browsers, such as Google Chrome, Brave,... |
| `CloudStorageClients` | Darwin,Linux,Windows | 1 ARTIFACT_GROUP | Multiple cloud storage client artifacts. |
| `ContainerdConfig` | Linux | 1 FILE | containerd configuration files |
| `ContainerdLogs` | Linux | 1 FILE | containerd related events in the log files |
| `ContainerdRootDirectory` | Linux | 1 PATH | containerd default root directory. |
| `CronAtAllowDenyFiles` | Linux | 1 FILE | Files containing users authorised to run cron or at jobs. |
| `CrowdstrikeAgentID` | Darwin,Linux,Windows | 1 COMMAND, 1 FILE, 1 REGISTRY_VALUE | Identifier of a CrowdStrike agent. |
| `CrowdstrikeQuarantine` | Darwin,Windows | 2 FILE | Crowdstrike stores quarantined files encoded on disk. |
| `CShellConfigurationFile` | Darwin,Linux,Windows | 3 FILE | C shell (csh) configuration files. |
| `CupsJobCacheFile` | Darwin,Linux | 3 FILE | Common UNIX Printing System (CUPS) job cache file. |
| `DebianPackagesLogFiles` | Linux | 1 FILE | Linux dpkg log files. |
| `DebianPackagesStatus` | Linux | 1 FILE | Linux dpkg status file. |
| `DebianVersion` | Linux | 1 FILE | Debian version information. |
| `DLLHijackLocations` | Windows | 1 FILE | DLL search order hijacking locations collected from base Windows 7. |
| `DNSResolvConfFile` | Linux | 1 FILE | DNS Resolver configuration file. |
| `DockerContainerConfig` | Linux | 1 FILE | Docker container configuration files |
| `DockerRootDirectory` | tous | 1 PATH | Docker default root directory. |
| `DropboxClient` | Darwin,Linux,Windows | 2 FILE | Dropbox cloud storage client artifacts. |
| `ElasticsearchAccessLog` | Linux | 1 FILE | Location where Elasticsearch access logs are stored. |
| `ElasticsearchAuditLog` | Linux | 1 FILE | Location where Elasticsearch audit logs are stored. |
| `ElasticsearchGCLog` | Linux | 1 FILE | Location where Elasticsearch GC logs are stored. |
| `ElasticsearchLogs` | Linux | 1 FILE | Location where Elasticsearch logs are stored. |
| `ElasticsearchServerLog` | Linux | 1 FILE | Location where Elasticsearch server logs are stored. |
| `EsetAVQuarantine` | Darwin,Windows | 2 FILE | Eset Anti-Virus Quarantine (Infected) files. |
| `ESXApiForwarder` | ESXi | 1 FILE | Records activities related to the vSphere Trust Authority API forwarder. |
| `ESXiAttestationService` | ESXi | 1 FILE | Records activities related to the vSphere Trust Authority Attestation Service. |
| `ESXiAuthenticationLog` | ESXi | 1 FILE | Contains all events related to authentication for the local system. |
| `ESXiHostAgentLog` | ESXi | 1 FILE | Contains information about the agent that manages and configures the ESXi host and its vir... |
| `ESXiKeyProviderService` | ESXi | 1 FILE | Records activities related to the vSphere Trust Authority Key Provider Service. |
| `ESXiQuickBootLog` | ESXi | 1 FILE | Contains all events related to restarting an ESXi host through Quick Boot. |
| `ESXiShellLog` | ESXi | 1 FILE | Contains a record of all commands typed into the ESXi Shell and shell events (for example,... |
| `ESXiSystemLogsDirectory` | ESXi | 1 FILE | ESXi System Logs Directory |
| `ESXiSystemMessageslog` | ESXi | 1 FILE | Contains all general log messages and can be used for troubleshooting. This information wa... |
| `ESXiTrustedInfrastructureAgentLog` | ESXi | 1 FILE | Records activities related to the Client Service on the ESXi Trusted Host. |
| `ESXiVMKernelLog` | ESXi | 1 FILE | Records activities related to virtual machines and ESXi. |
| `ESXiVMKernelSummaryLog` | ESXi | 1 FILE | Used to determine uptime and availability statistics for ESXi (comma separated). |
| `ESXiVMKernelWarningsLog` | ESXi | 1 FILE | Records activities related to virtual machines. |
| `ESXTokenService` | ESXi | 1 FILE | Records activities related to the vSphere Trust Authority ESX Token Service. |
| `FirefoxAddOns` | Darwin,Linux,Windows | 3 FILE | Firefox browser add-ons/extensions. |
| `FirefoxCache` | Darwin,Linux,Windows | 3 FILE | Mozilla Firefox browser caches. |
| `FirefoxCookies` | Darwin,Linux,Windows | 3 FILE | Firefox browser cookies (cookies.sqlite). |
| `FirefoxDownloads` | Darwin,Linux,Windows | 3 FILE | Firefox browser downloads (downloads.sqlite). |
| `FirefoxHistory` | Darwin,Linux,Windows | 3 FILE | Firefox browser history (places.sqlite). |
| `FishShellConfigurationFile` | Linux | 1 FILE | FishShell (fish) configuration files. |
| `FishShellHistoryFile` | Darwin,Linux | 1 FILE | Fish shell (fish) history files. |
| `FlatpakAppPaths` | Linux | 1 PATH | Get paths of installed Flatpak app. |
| `FreeDesktopTrashFiles` | Linux | 1 FILE | FreeDesktop.org Trash Files. |
| `FreeDesktopTrashInfoFiles` | Linux | 1 FILE | FreeDesktop.org Trash Info Files. |
| `GKEDockerContainerLogs` | Linux | 1 FILE | Location where stdout and stderr from containers is logged in a Google Kubernetes Engine (... |
| `GnomeApplicationState` | Linux | 1 FILE | Gnome application state for frequent application data. |
| `GnomeEvolution` | Linux | 1 FILE | Gnome Evolution files. |
| `GnomeTracker` | Linux | 1 FILE | Gnome Tracker database and backup files. |
| `GoogleDriveClient` | Darwin,Windows | 2 FILE | Google Drive cloud storage client artifacts. |
| `GTKRecentlyUsedDatabase` | Linux | 1 FILE | GTK Recent Manager database. |
| `HadoopAppLogs` | Linux | 1 FILE | Location where Hadoop application logs are stored |
| `HadoopAppRoot` | Linux | 1 FILE | Location where Hadoop application files are stored |
| `HadoopYarnLogs` | Linux | 1 FILE | Location where Hadoop Yarn LevelDB/Timeline files are stored |
| `HAProxyLogFiles` | Linux | 1 FILE | HAProxy Log files |
| `HostAccessPolicyConfiguration` | Linux | 1 FILE | Linux files related to host access policy configuration. |
| `InternetExplorer6Settings` | Windows | 1 REGISTRY_VALUE | Registry keys affecting default behavior for Microsoft Internet Explorer 6. |
| `InternetExplorerBrowserHelperObjects` | Windows | 1 REGISTRY_KEY | Loaded on Internet Explorer startup |
| `InternetExplorerCache` | Windows | 1 FILE | Microsoft Internet Explorer (MSIE) browser cache. * MSIE 4 - 9 Temporary Internet files. *... |
| `InternetExplorerCookies` | Windows | 1 FILE | Microsoft Internet Explorer (MSIE) browser cookies. * MSIE 4 - 9 Cache files (index.dat) |
| `InternetExplorerHistory` | Windows | 1 ARTIFACT_GROUP | Microsoft Internet Explorer (MSIE) browser history. * MSIE 4 - 9 Cache files (index.dat); ... |
| `InternetExplorerHistoryDatabaseFile` | Windows | 1 FILE | Microsoft Internet Explorer (MSIE) 10 browser history database file (WebCacheV*.dat). |
| `InternetExplorerIndexDatFiles` | Windows | 1 FILE | Microsoft Internet Explorer (MSIE) 4 - 9 cache and history files (index.dat). |
| `InternetExplorerProtectedModeDisable` | Windows | 1 REGISTRY_KEY | Microsoft Internet Explorer (MSIE) Protected Mode Banner can be suppressed by setting NoPr... |
| `InternetExplorerProtectedModeElevationPolicies` | Windows | 1 REGISTRY_VALUE | Trust levels of apps launched from low rights IE sessions. The ElevationPolicy dictates ho... |
| `InternetExplorerTypedURLsKeys` | Windows | 1 REGISTRY_KEY | Microsoft Internet Explorer TypedUrls keys. |
| `IPTablesRules` | Linux | 1 COMMAND | List IPTables rules. |
| `JavaCacheFiles` | Windows,Linux,Darwin | 3 FILE | Java Plug-in cache. |
| `JenkinsLogFile` | Linux | 1 FILE | Jenkins log file |
| `JupyterConfigFile` | Darwin,Linux,Windows | 2 FILE | Jupyter notebook configuration file |
| `KasperskyCaretoDarwinFile` | Darwin | 1 FILE | Kaspersky Careto Darwin file system indicators of compromise (IOCs). |
| `KasperskyCaretoIndicators` | Windows,Darwin | 1 ARTIFACT_GROUP | Kaspersky Careto indicators of compromise (IOCs). |
| `KasperskyCaretoWindowsFile` | Windows | 1 FILE | Kaspersky Careto Windows file system indicators of compromise (IOCs). |
| `KasperskyCaretoWindowsRegistryValue` | Windows | 1 REGISTRY_VALUE | Kaspersky Careto Windows Registry indicators of compromise (IOCs). |
| `KernelModules` | Linux | 1 FILE | Kernel modules to be loaded on boot. |
| `KornShellConfigurationFile` | Darwin,Linux,Windows | 3 FILE | KornShell (ksh) configuration files. |
| `KubernetesCertificates` | Linux | 1 FILE | Certificate files that are used for a Kubernetes cluster. The files are typically only pre... |
| `KubernetesClusterDatabase` | Linux | 1 FILE | Kubernetes cluster (etcd) database. The cluster database is hosted within a Pod and can be... |
| `KubernetesKubelet` | Linux | 1 PATH | Installation path of the (Kubernetes) Kubelet component. This component is installed on al... |
| `KubernetesKubeletConfiguration` | Linux | 1 FILE | Files that stores the configuration of the local (Kubernetes) Kubelet. |
| `KubernetesKubeletNetworkPKI` | Linux | 1 PATH | Certificates and other keyfiles used for Kubelet and Kubernetes general PKI. |
| `KubernetesKubeletPod` | Linux | 1 PATH | Path of (Kubernetes) Kubelet component information about Pods scheduled to run on a partic... |
| `KubernetesKubeletPodContainer` | Linux | 1 PATH | Path where the container resources created within a (Kubernetes) Pod are located. The path... |
| `KubernetesKubeletPodLogs` | Linux | 1 FILE | Location where the log data of (Kubernetes) Pods can be found. The path's name would conta... |
| `KubernetesKubeletPodManifest` | Linux | 1 FILE | Manifest file that has been used to deploy a (Kubernetes) Pod. The manifest contains the P... |
| `KubernetesKubeletPodVolumes` | Linux | 1 PATH | Volumes and other objects that are mounted into a (Kubernetes) Pod and respectively into t... |
| `KubernetesLogs` | Linux | 1 FILE | Log files that contain information about the Kubernetes installation of a node. |
| `LessHistoryFile` | Linux | 1 FILE | less history file which remembers search and shell commands |
| `LinuxASLREnabled` | Linux | 1 FILE | Kernel ASLR state. |
| `LinuxAtJobs` | Linux | 1 FILE | Linux at jobs. |
| `LinuxAtJobsTemporaryOutputs` | Linux | 1 FILE | Linux at jobs temporary outputs. |
| `LinuxAuditLogs` | Linux | 1 FILE | Linux audit log files. |
| `LinuxAuthLogs` | Linux | 1 FILE | Linux authentication log files. |
| `LinuxCACertificates` | Linux | 1 FILE | Linux CA Certificates. |
| `LinuxCACertificatesConfiguration` | tous | 1 FILE | Linux CA Certificates configuration file. |
| `LinuxCronLogs` | Linux | 1 FILE | Linux cron log files. |
| `LinuxCronTabs` | Linux | 1 FILE | Crontab files. |
| `LinuxDaemonLogFiles` | Linux | 1 FILE | Linux daemon log files. |
| `LinuxDHCPConfigurationFile` | Linux | 1 FILE | Linux DHCP Configuration File |
| `LinuxDistributionRelease` | Linux | 1 FILE | Linux distribution release information of non-LSB compliant systems. |
| `LinuxDSDTTable` | Linux | 1 FILE | Linux file containing DSDT table. |
| `LinuxFstab` | Linux | 1 FILE | Linux fstab file. |
| `LinuxGrubConfiguration` | Linux | 1 FILE | Linux grub configuration file. |
| `LinuxHostnameFile` | Linux | 1 FILE | Linux hostname file. |
| `LinuxIfUpDownScripts` | Linux | 1 FILE | ifupdown scripts executed whenever a network interface goes up or down respectively. |
| `LinuxIgnoreICMPBroadcasts` | Linux | 1 FILE | Whether the system ignores ICMP pings. |
| `LinuxInitrdFiles` | Linux | 1 FILE | Initrd (initramfs) files in /boot/ executed on startup. |
| `LinuxIssueFile` | Linux | 1 FILE | Linux prelogin message and identification (issue) file. |
| `LinuxKerberosConfiguration` | Linux | 1 FILE | Linux Kerberos configuration information. |
| `LinuxKernelBootloader` | Linux | 1 FILE | Bootloader state acquired from the kernel. |
| `LinuxKernelLogFiles` | Linux | 1 FILE | Linux kernel log files. |
| `LinuxKernelModuleRestrictions` | Linux | 1 FILE | Module loading controls. |
| `LinuxKernelModuleTaintStatus` | Linux | 1 FILE | Taint state of loaded modules (binary blobs, unsigned modules etc). |
| `LinuxLastlogFile` | Linux | 1 FILE | Linux lastlog file. |
| `LinuxLoaderSystemPreloadFile` | Linux | 1 FILE | Linux dynamic linker/loader system-wide preload file (ld.so.preload). |
| `LinuxLocalTime` | Linux | 1 FILE | Local time zone configuration |
| `LinuxLSBInit` | Linux | 1 FILE | Linux LSB-style init scripts. |
| `LinuxLSBRelease` | Linux | 1 FILE | Linux Standard Base (LSB) release information |
| `LinuxMessagesLogFiles` | Linux | 1 FILE | Linux messages log files. |
| `LinuxMountCmd` | Linux | 1 COMMAND | Linux output of mount |
| `LinuxMountInfo` | Linux | 1 ARTIFACT_GROUP | Linux mount options. |
| `LinuxNetworkIpForwardingState` | Linux | 1 FILE | IP forwarding states. |
| `LinuxNetworkManager` | Linux | 1 FILE | Linux NetworkManager files. |
| `LinuxNetworkPathFilteringSettings` | Linux | 1 FILE | States that determine how the system responds to route manipulation. |
| `LinuxNetworkRedirectState` | Linux | 1 FILE | Redirect send/receive states. |
| `LinuxNssCachePasswdFile` | Linux | 1 FILE | Local NSS database for remote directory services. |
| `LinuxPamConfigs` | Linux | 1 FILE | Configuration files for PAM. |
| `LinuxPasswdFile` | Linux | 1 FILE | Linux passwd file. A passwd file consist of colon separated values in the format: username... |
| `LinuxProcArp` | Linux | 1 FILE | ARP table via /proc/net/arp. |
| `LinuxProcMounts` | Linux | 1 FILE | Current mounted filesystems. |
| `LinuxProcSysHardeningSettings` | Linux | 1 ARTIFACT_GROUP | Linux sysctl settings obtained from /proc/sys. |
| `LinuxRelease` | Linux | 1 FILE | Linux specific distribution information. See: lsb_release(1) man page, or the LSB Specific... |
| `LinuxReleaseInfo` | Linux | 1 ARTIFACT_GROUP | Release information for Linux platforms. |
| `LinuxRestrictedDmesgReadPrivileges` | Linux | 1 FILE | Restrict whether non-privileged users can read dmesg. |
| `LinuxRestrictedKernelPointerReadPrivileges` | Linux | 1 FILE | Memory address obfuscation settings. |
| `LinuxRsyslogConfigs` | Linux | 1 FILE | Linux rsyslog configurations. |
| `LinuxScheduleFiles` | Linux | 1 ARTIFACT_GROUP | All Linux job scheduling files. |
| `LinuxSecureFsLinks` | Linux | 1 FILE | Security controls to restrict operations on links in world writable directories. |
| `LinuxSecureSuidCoreDumps` | Linux | 1 FILE | Security controls for suid core dumps. |
| `LinuxServices` | Linux | 1 ARTIFACT_GROUP | Services running on a Linux system. |
| `LinuxSSDTTables` | Linux | 1 FILE | Linux files containing SSDT table. |
| `LinuxSudoReplayLogs` | Linux | 1 FILE | Linux sudoreplay log files. |
| `LinuxSyncookieState` | Linux | 1 FILE | Whether the system uses syncookies. |
| `LinuxSysctlCmd` | Linux | 1 COMMAND | Linux output of systctl -a. |
| `LinuxSysctlConfigurationFiles` | Linux | 1 FILE | Linux sysctl preload/configuration files. |
| `LinuxSysLogFiles` | Linux | 1 FILE | Linux syslog log files. |
| `LinuxSyslogNgConfigs` | Linux | 1 FILE | Linux syslog-ng configurations. |
| `LinuxSystemdJournalConfig` | Linux | 1 FILE | Linux systemd journal config file |
| `LinuxSystemdJournalLogs` | Linux | 1 FILE | Linux systemd journal log files |
| `LinuxSystemdOSRelease` | Linux | 1 FILE | Linux systemd /etc/os-release file |
| `LinuxSystemdServices` | Linux | 1 FILE | Linux systemd service unit files |
| `LinuxSystemdTimers` | Linux | 1 FILE | Linux systemd Timer files |
| `LinuxSysVInit` | Linux | 1 FILE | Services started by sysv-style init scripts. |
| `LinuxTimezoneFile` | Linux | 1 FILE | Linux timezone file. |
| `LinuxUdevRules` | Linux | 1 FILE | Linux udev rules for the events received by the udev's daemon from the Linux kernel. |
| `LinuxUtmpFiles` | Linux | 1 FILE | Linux btmp, utmp and wtmp login record files. |
| `LinuxWtmp` | Linux | 1 FILE | Linux wtmp login record file |
| `LinuxXinetd` | Linux | 1 FILE | Linux xinetd configurations. |
| `ListProcessesPsCommand` | Linux | 1 COMMAND | Full process listing via the 'ps' command. |
| `LoadedKernelModules` | Linux | 1 COMMAND | Linux output of lsmod. |
| `LocateDatabase` | Linux | 1 FILE | locate/mlocate database and updatedb configuration. |
| `LoginPolicyConfiguration` | Linux | 1 FILE | Linux files related to login policy configuration. |
| `MacOSAddressBookImagesSQLiteDatabaseFile` | Darwin | 1 FILE | Address book images SQLite database file. |
| `MacOSAirportPreferencesPlistFile` | Darwin | 1 FILE | Airport (wireless networking) preferences property list (plist) file. |
| `MacOSApplePushServiceSQLiteDatabaseFile` | Darwin | 1 FILE | Apple push service SQLite database file. |
| `MacOSAppleSetupDoneFile` | Darwin | 1 FILE | Mac OS .AppleSetupDone file that hints to the system installation date and time. |
| `MacOSAppleSystemLogFile` | Darwin | 1 FILE | Apple system log (ASL) files. |
| `MacOSApplicationBundleCacheSQLiteDatabaseFile` | Darwin | 1 FILE | Application bundle cache SQLite database file. |
| `MacOSApplicationResourcesStringsPlistFile` | Darwin | 1 FILE | Application resources strings plist file. |
| `MacOSApplicationsDirectory` | Darwin | 1 PATH | Contents of the Applications directory. |
| `MacOSApplicationsRecentItems` | Darwin | 1 FILE | Recent Items application specific |
| `MacOSAssetCacheInfoSQLiteDatabaseFile` | Darwin | 1 FILE | Asset cache information SQLite database file. |
| `MacOSAtJobs` | Darwin | 1 FILE | MacOS at jobs |
| `MacOSAuditLogFile` | Darwin | 1 FILE | Audit log files. |
| `MacOSAuthorizationRulesSQLiteDatabaseFile` | Darwin | 1 FILE | Authorization rules SQLite database file. Superscedes /etc/authorization seen Mac OS X 10.... |
| `MacOSBluetoothPlistFile` | Darwin | 1 FILE | Bluetooth preferences and paired device information property list (plist) file |
| `MacOSCalendarCacheSQLiteDatabaseFile` | Darwin | 1 FILE | Calendar cache SQLite database file. |
| `MacOSCallHistoryCacheSQLiteDatabaseFile` | Darwin | 1 FILE | Call history cache SQLite database file. |
| `MacOSCodeSignatureCodeResourcesPlistFile` | Darwin | 1 FILE | Code signature CodeResources plist file. |
| `MacOSContentsInfoPlistFile` | Darwin | 1 FILE | Contents Info.plist file. |
| `MacOSContentsVersionPlistFile` | Darwin | 1 FILE | Contents version.plist file. |
| `MacOSCoreAnalyticsFile` | Darwin | 1 FILE | CoreAnalytics log files. |
| `MacOSCronTabs` | Darwin | 1 FILE | Cron tabs |
| `MacOSDirectoryServicesLocalNodesSQLiteDatabaseFile` | Darwin | 1 FILE | Directory services local nodes database. |
| `MacOSDockConfigurationPlistFile` | Darwin | 1 FILE | Dock configuration property list (plist) file. This property list contains information abo... |
| `MacOSDuetActivitySchedulerSQLiteDatabaseFile` | Darwin | 1 FILE | Duet activity scheduler database. |
| `MacOSDuetinteractionCSQLiteDatabaseFile` | Darwin | 1 FILE | Duet interactionC database. |
| `MacOSDuetKnowledgeCSQLiteDatabaseFile` | Darwin | 1 FILE | Duet knowledgeC User and Application usage database. |
| `MacOSDuetSQLiteDatabaseFile` | Darwin | 1 FILE | Duet database. |
| `MacOSDuetSystemEventsSQLiteDatabaseFile` | Darwin | 1 FILE | Duet system events database. |
| `MacOSFSEventsFile` | Darwin | 1 FILE | File system events disk log stream (fsevents) files. |
| `MacOSGatekeeperOpaqueConfigurationSQLiteDatabaseFile` | Darwin | 1 FILE | Gatekeeper opaque configuration database. |
| `MacOSGlobalPreferencesPlistFile` | Darwin | 1 FILE | Global preferences property list (plist) file. This property list contains information abo... |
| `MacOSiCloudAccounts` | Darwin | 1 FILE | iCloud Accounts |
| `MacOSiCloudPreferences` | Darwin | 1 FILE | iCloud user preferences |
| `MacOSIdentityServicesSQLiteDatabaseFile` | Darwin | 1 FILE | Identity services SQLite database file. |
| `MacOSiDevices` | Darwin | 1 FILE | Attached iDevices |
| `MacOSInstallationHistoryPlistFile` | Darwin | 1 FILE | Software installation history property list (plist) file. |
| `MacOSInstallationLogFile` | Darwin | 1 FILE | Software installation log file |
| `MacOSiOSBackupInfo` | Darwin | 1 FILE | iOS device backup information |
| `MacOSiOSBackupManifest` | Darwin | 1 FILE | iOS device backup apps information |
| `MacOSiOSBackupMbdb` | Darwin | 1 FILE | iOS device backup files information |
| `MacOSiOSBackupsMainDirectory` | Darwin | 1 FILE | iOS device backups directory |
| `MacOSiOSBackupStatus` | Darwin | 1 FILE | iOS device backup status information. |
| `MacOSiTunesInterfaceBuilderDocumentPlistFile` | Darwin | 1 FILE | iTunes Interface Builder document (*.itxib) plist file. |
| `MacOSKernelExtensionFile` | Darwin | 1 FILE | Kernel extension (.kext) files. |
| `MacOSKeyboardLayoutPlistFile` | Darwin | 1 FILE | Keyboard layout property list (plist) file. |
| `MacOSLastlogFile` | Darwin | 1 FILE | Lastlog file. |
| `MacOSLaunchAgentsPlistFile` | Darwin | 1 FILE | Launch Agents property list (plist) files. |
| `MacOSLaunchDaemonsPlistFile` | Darwin | 1 FILE | Launch Daemons property list (plist) files. |
| `MacOSLoadedKexts` | Darwin | 1 COMMAND | MacOS Loaded Kernel Extensions. |
| `MacOSLogFile` | Darwin | 1 FILE | Miscellaneous system log files. |
| `MacOSLoginWindowPlistFile` | Darwin | 1 FILE | Log-in window information property list (plist) file |
| `MacOSMailAccounts` | Darwin | 1 FILE | Mail Accounts. Until now only V2, V3 and V5 have been observed. |
| `MacOSMailBackupTOC` | Darwin | 1 FILE | Mail Backup Table of Content. Until now only V2, V3 and V5 have been observed. |
| `MacOSMailboxes` | Darwin | 1 FILE | Mail Mailbox Directory. Until now only V2, V3 and V5 have been observed. |
| `MacOSMailDownloadAttachments` | Darwin | 1 FILE | Mail Downloads Directory |
| `MacOSMailEnvelopIndex` | Darwin | 1 FILE | Mail Envelope Index. Until now only V2, V3 and V5 have been observed. |
| `MacOSMailIMAP` | Darwin | 1 FILE | Mail IMAP Synched Mailboxes. Until now only V2, V3 and V5 have been observed. |
| `MacOSMailMainDirectory` | Darwin | 1 FILE | Mail Main Folder. Until now only V2, V3 and V5 have been observed. |
| `MacOSMailOpenedAttachments` | Darwin | 1 FILE | Mail Opened Attachments |
| `MacOSMailPOP` | Darwin | 1 FILE | Mail POP Synched Mailboxes. Until now only V2, V3 and V5 have been observed. |
| `MacOSMailPreferences` | Darwin | 1 FILE | Mail Preferences |
| `MacOSMailRecentContacts` | Darwin | 1 FILE | Mail Recent Contacts |
| `MacOSMailSignatures` | Darwin | 1 FILE | Mail Signatures by Account. Until now only V2, V3 and V5 have been observed. |
| `MacOSMessageChatSQLiteDatabaseFile` | Darwin | 1 FILE | iMessage chat SQLite database file. |
| `MacOSMountedDMGs` | Darwin | 1 COMMAND | MacOS Mounted DMG files. |
| `MacOSNetworkUsageSQLiteDatabaseFile` | Darwin | 1 FILE | Network usage SQLite database file. |
| `MacOSNotesSQLiteDatabaseFile` | Darwin | 1 FILE | Notes SQLite database file. |
| `MacOSNotificationCenterSQLiteDatabaseFile` | Darwin | 1 FILE | MacOS NotificationCenter SQLite database files. |
| `MacOSPeriodicSystemFunctionConfigurationFile` | Darwin | 1 FILE | Configuration files of system function scripts that should run periodically. |
| `MacOSQuarantineEventsSQLiteDatabaseFile` | Darwin | 1 FILE | Quarantine events SQLite database file. |
| `MacOSRecentItemsPlistFile` | Darwin | 1 FILE | Recent items property list (plist) file. |
| `MacOSRemoteDesktopAdministratorSystem` | Darwin | 1 FILE | Apple Remote Desktop (ARD) was first released in 2002 and is Apple’s desktop management sy... |
| `MacOSRemoteDesktopClientSystem` | Darwin | 1 FILE | Apple Remote Desktop (ARD) was first released in 2002 and is Apple’s desktop management sy... |
| `MacOSResourcesInfoStringsPlistFile` | Darwin | 1 FILE | Resources InfoPlist.strings plist file. |
| `MacOSResourcesLocalizableStringsPlistFile` | Darwin | 1 FILE | Resources Localizable.strings plist file. |
| `MacOSSidebarListsPlistFile` | Darwin | 1 FILE | Sidebar lists preferences property list (plist) file. This property list contains the name... |
| `MacOSSiriAnalyticsSQLiteDatabaseFile` | Darwin | 1 FILE | Siri analytics SQLite database file. |
| `MacOSSiriSuggestionsEntitiesSQLiteDatabaseFile` | Darwin | 1 FILE | Siri suggestions entities SQLite database file. |
| `MacOSSiriSuggestionsPendingQueueSQLiteDatabaseFile` | Darwin | 1 FILE | Siri suggestions pending queue SQLite database file. |
| `MacOSSiriSuggestionsSnippetsSQLiteDatabaseFile` | Darwin | 1 FILE | Siri suggestions snippets SQLite database file. |
| `MacOSSleepimageFile` | Darwin | 1 FILE | Sleepimage file which contains the content of memory before going to sleep |
| `MacOSSoftwareUpdatePreferencesPlistFile` | Darwin | 1 FILE | Software update preferences property list (plist) files. |
| `MacOSSpotlightStoreVolumeConfigurationPlistFile` | Darwin | 1 FILE | Spotlight store volume configuration plist file. |
| `MacOSSpotlightVolumeConfigurationPlistFile` | Darwin | 1 FILE | Spotlight volume configuration plist file. |
| `MacOSStartupItemsPlistFile` | Darwin | 1 FILE | Startup Items property list (plist) files. |
| `MacOSSwapFile` | Darwin | 1 FILE | Swap file |
| `MacOSSystemConfigurationPreferencesPlistFile` | Darwin | 1 FILE | System configuration preferences property list (plist) file. |
| `MacOSSystemLogFile` | Darwin | 1 FILE | System log file. |
| `MacOSSystemPolicySQLiteDatabaseFile` | Darwin | 1 FILE | System policy database. |
| `MacOSSystemPreferencesPlistFile` | Darwin | 1 FILE | System Preferences property list (plist) files |
| `MacOSSystemVersionPlistFile` | Darwin | 1 FILE | Operating system name and version property list (plist) file |
| `MacOSTCCSQLiteDatabaseFile` | Darwin | 1 FILE | Transparency, Consent, Control (TCC) framework SQLite database files. |
| `MacOSTextReplacementsSQLiteDatabaseFile` | Darwin | 1 FILE | Text replacements SQLite database file. |
| `MacOSTimeMachinePlistFile` | Darwin | 1 FILE | Time Machine information property list (plist) file |
| `MacOSUnifiedLogging` | Darwin | 1 FILE | Apple Unified Logging and Activity Tracing |
| `MacOSUserAccountsSQLiteDatabaseFile` | Darwin | 1 FILE | User Accounts SQLite database files. Seen Accounts3.sqlite and Accounts4.sqlite |
| `MacOSUserApplicationLogFile` | Darwin | 1 FILE | User applications log files. |
| `MacOSUserApplicationSupportDirectory` | Darwin | 1 PATH | Contents of the user Application Support directories. |
| `MacOSUserDesktopDirectory` | Darwin | 1 PATH | Contents of the user Desktop directories. |
| `MacOSUserDockDesktopPictureSQLiteDatabaseFile` | Darwin | 1 FILE | Dock user desktop picture SQLite database file. |
| `MacOSUserDocumentsDirectory` | Darwin | 1 PATH | Contents of the user Documents directories. |
| `MacOSUserGlobalPreferencesPlistFile` | Darwin | 1 FILE | User global preferences property list (plist) file. |
| `MacOSUserKeychainFile` | Darwin | 1 FILE | User keychain files. |
| `MacOSUserKeychainOCSPCacheSQLiteDatabaseFile` | Darwin | 1 FILE | User keychain CRL and OCSP cache SQLite database file. |
| `MacOSUserLibraryDirectory` | Darwin | 1 PATH | Contents of the user Library directories. |
| `MacOSUserLocalItemsKeychainKeybagSQLiteDatabaseFile` | Darwin | 1 FILE | User (iCloud) local items keychain keybag SQLite database file. |
| `MacOSUserLocalItemsKeychainRecordsSQLiteDatabaseFile` | Darwin | 1 FILE | User (iCloud) local items keychain encrypted records SQLite database file. |
| `MacOSUserLoginItemsPlistFile` | Darwin | 1 FILE | User login items property list (plist) file. |
| `MacOSUserMoviesDirectory` | Darwin | 1 PATH | Contents of the user Movies directories. |
| `MacOSUserMusicDirectory` | Darwin | 1 PATH | Contents of the user Music directories. |
| `MacOSUserPasswordHashesPlistFile` | Darwin | 1 FILE | User password hashes property list (plist) files. |
| `MacOSUserPicturesDirectory` | Darwin | 1 PATH | Contents of the user Pictures directories. |
| `MacOSUserPreferencesDirectory` | Darwin | 1 FILE | Contents of the user Preferences directories. |
| `MacOSUserPublicDirectory` | Darwin | 1 PATH | Contents of the user Public directories. |
| `MacOSUserTrashDirectory` | Darwin | 1 FILE | Contents of the user Trash directories. |
| `MacOSUtmpxFile` | Darwin | 1 FILE | Utmpx login record file. |
| `MacOSWalletSQLiteDatabaseFile` | Darwin | 1 FILE | Apple Wallet SQLite database file. |
| `MacOSWirelessDiagnosticDataPersistentSQLiteDatabaseFile` | Darwin | 1 FILE | Apple Wireless Diagnostic Data (AWDD) persistent SQLite database file. |
| `MacOSXcodeiOSDeviceLogsSQLiteDatabaseFile` | Darwin | 1 FILE | Xcode iOS Device Logs SQLite database file. |
| `MicrosoftAVLogs` | Windows | 1 FILE | Microsoft Anti-Virus log files. |
| `MicrosoftAVQuarantine` | Windows | 1 FILE | Microsoft Anti-Virus Quarantine (Infected) files. |
| `MicrosoftIISLogs` | Windows | 1 FILE | Internet Information Services (IIS) web server's log files. |
| `MicrosoftOfficeAutosave` | Windows | 1 FILE | Automatically created Microsoft Office recovery files. |
| `MicrosoftOfficeMRU` | Darwin,Windows | 1 FILE, 1 REGISTRY_VALUE | Microsoft Office Most Recently Used |
| `MicrosoftOutlookOSTFiles` | Windows | 1 FILE | Microsoft Outlook OST Files |
| `MicrosoftOutlookPABFiles` | Windows | 1 FILE | Microsoft Outlook PAB Files |
| `MicrosoftOutlookPSTFiles` | Windows | 1 FILE | Microsoft Outlook PST Files |
| `MicrosoftSqlServerErrorLogs` | Windows | 1 FILE | Microsoft SQL Server's error log files. |
| `MongoDBConfigurationFile` | Darwin,Linux | 2 FILE | MongoDB configuration file. |
| `MongoDBDatabasePath` | Darwin,Linux,Windows | 2 FILE, 1 PATH | MongoDB database Path. |
| `MongoDBLogFiles` | Linux | 1 FILE | MongoDB log files. |
| `MozillaThunderbird` | Linux | 1 FILE | Mozilla Thunderbird files. |
| `MySQLConfigurationFiles` | Linux | 1 FILE | MySQL configuration files. |
| `MySQLDataDictionary` | Linux | 1 FILE | MySQL data dictionary. |
| `MySQLDataDirectory` | Linux | 1 FILE | MySQL data directory. |
| `MySQLHistoryFile` | Linux | 1 FILE | MySQL History file. |
| `MySQLLogFiles` | Linux | 1 FILE | MySQL log files. |
| `NanoHistoryFile` | Linux | 1 FILE | nano history file that logs search and replace strings. |
| `NetgroupConfiguration` | Linux | 1 FILE | Linux netgroup configuration. |
| `NfsExportsFile` | Linux,Darwin | 2 FILE | NFS Exports configuration |
| `NginxAccessLogs` | Linux,Windows | 2 FILE | Location where nginx access logs are stored |
| `NginxErrorLogs` | Linux | 1 FILE | Location where nginx error logs are stored |
| `NodeJSPackageManagerCacheFiles` | Darwin,Linux,Windows | 2 FILE | Node JS package manager (NPM) cache files |
| `NpmPackagesPath` | Linux | 1 PATH | Get path of NPM packages that are globally installed (currently linux only). |
| `NTFSLogFile` | Windows | 1 FILE | The NTFS $LogFile file system metadata file. |
| `NTFSMFTFiles` | Windows | 1 FILE | The NTFS $MFT and $MFTMirr file system metadata files. |
| `NTFSUSNJournal` | Windows | 1 FILE | The NTFS $UsnJnrl file system metadata file. Note that this currently does not include the... |
| `NtpConfFile` | Linux | 1 FILE | The configuration file for ntpd. e.g. ntp.conf. |
| `OpenSearchLogFiles` | Linux | 1 FILE | OpenSearch log files. |
| `OperaHistoryFile` | Darwin,Linux,Windows | 3 FILE | Opera browser history (global_history.dat) file. |
| `OsqueryLogFiles` | Linux | 1 FILE | Osquery daemon log files |
| `PCIDevicesInfoFiles` | Linux | 1 FILE | Info and config files for PCI devices located on the system. |
| `PostgreSQLConfigurationFiles` | Linux | 1 FILE | PostgreSQL configuration files. |
| `PostgreSQLDataDirectory` | Linux | 1 FILE | PostgreSQL data directory. |
| `PostgreSQLHistoryFile` | Linux | 1 FILE | PostgreSQL History file. |
| `PostgreSQLLogFiles` | Linux | 1 FILE | PostgreSQL log files. |
| `PythonDistInfo` | Linux | 1 FILE | Python module files distributed in the dist-info format of PEP-0376 (currently linux only)... |
| `PythonDistInfoPath` | Linux | 1 PATH | Get the path of Python module files distributed in the dist-info format of PEP-0376 (curre... |
| `PythonEggInfo` | Linux | 1 FILE | Python module files distributed in .egg formats (currently linux only). Python eggs can ha... |
| `PythonHistoryFile` | Linux | 1 FILE | Python REPL history file. |
| `PythonModuleInfo` | tous | 1 ARTIFACT_GROUP | Python module installation information. |
| `PythonWheelInfo` | Linux | 1 FILE | Python module files distributed in the wheel format (currently linux only). Zip archives w... |
| `RedisConfigFile` | Darwin,Linux,Windows | 3 FILE | Redis configuration file |
| `RedisConfigurationFile` | Linux | 1 FILE | Redis configuration files. |
| `RedisDataDirectory` | Linux | 1 FILE | Redis Data Directory. |
| `RedisLogFiles` | Linux | 1 FILE | Redis log files. |
| `RHostsFile` | Linux | 1 FILE | RHosts file. |
| `RootUserShellConfigs` | Darwin,Linux | 1 FILE | Common Unix root shell configuration files. |
| `RootUserShellHistory` | Darwin,Linux | 1 FILE | Common Unix root shell history files. |
| `RubyGems` | Linux | 1 FILE | Ruby Gems (currently linux only). |
| `SafariAutoFillCorrectionsSQLiteDatabaseFile` | Darwin | 1 FILE | Safari browser auto-fill corrections SQLite database file. |
| `SafariCacheSQLiteDatabaseFile` | Darwin,Windows | 2 FILE | Safari browser cache (cache.db) SQLite database file. |
| `SafariCloudAutoFillCorrectionsSQLiteDatabaseFile` | Darwin | 1 FILE | Safari browser cloud auto-fill corrections SQLite database file. |
| `SafariCookies` | Darwin | 1 FILE | Safari Cookies database. |
| `SafariDownloadsPlistFile` | Darwin,Windows | 2 FILE | Safari downloads history (Downloads.plist) property list (plist) file. |
| `SafariExtensions` | Darwin | 1 FILE | Safari browser extensions. |
| `SafariFaviconsCacheSQLiteDatabaseFile` | Darwin | 1 FILE | Safari browser favicons cache SQLite database file. |
| `SafariHistory` | Darwin,Windows | 1 ARTIFACT_GROUP | Safari browser history. |
| `SafariHistoryPlistFile` | Darwin,Windows | 2 FILE | Safari browser history (History.plist) property list (plist) file. |
| `SafariHistorySQLiteDatabaseFile` | Darwin | 1 FILE | Safari browser history SQLite database file. |
| `SafariPerSitePreferencesSQLiteDatabaseFile` | Darwin | 1 FILE | Safari browser per site preferences SQLite database file. |
| `SafariTabSnapshotsMetadataSQLiteDatabaseFile` | Darwin | 1 FILE | Safari browser tab snapshots metadata SQLite database file. |
| `SafariTouchIconCacheSettingsSQLiteDatabaseFile` | Darwin | 1 FILE | Safari browser touch icon cache settings SQLite database file. |
| `SambaConfigFile` | Linux | 1 FILE | Samba configuration file |
| `SambaLogFiles` | Linux | 1 FILE | Samba log files. |
| `SantaLogs` | Darwin | 1 FILE | Local Santa logs. |
| `SecretsServiceDatabaseFile` | Linux | 1 FILE | The System Security Services Daemon (SSSD) database file. |
| `ShellConfigurationFile` | Darwin,Linux,Windows | 1 ARTIFACT_GROUP | Group of shell configuration files. |
| `ShellHistoryFile` | Darwin,Linux,Windows | 1 ARTIFACT_GROUP | Group of shell history files. |
| `ShellLogoutFile` | Darwin,Linux,Windows | 2 FILE | Shell logout file. |
| `ShellProfileFile` | Darwin,Linux,Windows | 3 FILE | Shell profile file. |
| `SignalApplicationContent` | Linux | 1 FILE | Signal Application Content and Configuration |
| `SignalDatabase` | Linux | 1 FILE | Signal Database file. |
| `SkyDriveClient` | Windows | 1 FILE | Microsoft Sky Drive cloud storage client artifacts. Note that Sky Drive was renamed to One... |
| `SkypeChatSync` | Darwin | 1 FILE | Chat Sync Directory |
| `SkypeDb` | Darwin | 1 FILE | Main Skype database |
| `SkypeMainDirectory` | Darwin | 1 PATH | Skype Directory |
| `SkypePreferences` | Darwin | 1 FILE | Skype Preferences and Recent Searches |
| `SkypeUserProfile` | Darwin | 1 FILE | Skype User profile |
| `SophosAVLogs` | Darwin,Windows | 2 FILE | Sophos Anti-Virus log files. |
| `SophosAVQuarantine` | Darwin,Windows | 2 FILE | Sophos Anti-Virus Quarantine (Infected) files. |
| `SQLiteHistoryFile` | Linux | 1 FILE | SQLite History file. |
| `SSHAuthorizedKeysFiles` | Linux | 1 FILE | SSH authorized keys files. |
| `SshdConfigFile` | Linux,Darwin | 2 FILE | Sshd configuration |
| `SSHHostPubKeys` | Linux | 1 FILE | SSH host public keys |
| `SSHKnownHostsFiles` | Linux | 1 FILE | SSH known_hosts files. |
| `SshUserConfigFile` | Linux,Darwin | 1 FILE | User ssh configuration file |
| `SymantecAVLogs` | Windows | 1 FILE | Symantec Anti-Virus Log Files. |
| `SymantecAVQuarantine` | Windows | 1 FILE | Symantec Anti-Virus quarantine (infected) and cloud submission files. |
| `SystemDriveEnvironmentVariable` | Windows | 1 REGISTRY_VALUE | The %SystemDrive% environment variable, usually "C:". This value isn't actually present in... |
| `TeeShellConfigurationFile` | Darwin,Linux,Windows | 2 FILE | Tee shell (tcsh) configuration files. |
| `ThumbnailCacheFolder` | Linux | 1 FILE | Thumbnail cache folder. |
| `TomcatFiles` | Darwin,Linux,Windows | 1 ARTIFACT_GROUP | Tomcat files. |
| `TomcatLogFiles` | Darwin,Linux,Windows | 3 FILE | Tomcat log files. |
| `TomcatPasswordFile` | Darwin,Linux,Windows | 3 FILE | Tomcat password file. |
| `TriageApplicationConfigsAndLogs` | Linux,Windows | 2 ARTIFACT_GROUP | Group of configuration files and logs of installed applications. |
| `TriageDatabaseConfigsAndLogs` | Linux | 1 ARTIFACT_GROUP | Group of configuration files and logs of installed databases. |
| `TriageExecution` | Windows | 1 ARTIFACT_GROUP | Group of process/command execution related artifacts. |
| `TriageExternalMedia` | Windows | 1 ARTIFACT_GROUP | Group of external media data or events related artifacts. |
| `TriageFileSystem` | Windows | 1 ARTIFACT_GROUP | Group of file system related artifacts. |
| `TriageHistoryFiles` | Linux,Windows | 2 ARTIFACT_GROUP | Group of history files related artifacts. |
| `TriageInteractiveActivity` | Linux,Windows | 2 ARTIFACT_GROUP | Group of interactive user activity related artifacts. |
| `TriageNetwork` | Linux,Windows | 2 ARTIFACT_GROUP | Group of network related artifacts. |
| `TriagePersistence` | Linux,Windows | 2 ARTIFACT_GROUP | Group of persistence mechanism related artifacts. |
| `TriageSecurityAgents` | Windows | 1 ARTIFACT_GROUP | Group of endpoint detection and response related artifacts. |
| `TriageSystemConfiguration` | Linux,Windows | 2 ARTIFACT_GROUP | Group of configuration files related artifacts. |
| `TriageSystemLogs` | Linux,Windows | 2 ARTIFACT_GROUP | Group of system logs related artifacts. |
| `TriageUserConfiguration` | Linux | 1 ARTIFACT_GROUP | Group of user configuration related artifacts. |
| `TriageWebBrowserExtensions` | Linux,Windows | 1 ARTIFACT_GROUP | Group of web browser extensions related artifacts. |
| `TriageWebBrowserHistory` | Windows | 1 ARTIFACT_GROUP | Group of web browser history related artifacts. |
| `UFWConfigFiles` | Linux | 1 FILE | UFW Configuration files. |
| `UFWLogFile` | Linux | 1 FILE | UFW Log file. |
| `UnixGroupsFile` | Darwin,Linux | 2 FILE | Unix groups file. |
| `UnixHostsFile` | Darwin,Linux | 2 FILE | Unix hosts file |
| `UnixLocalTimeConfigurationFile` | Darwin,Linux | 2 FILE | Unix local time zone configuration file. |
| `UnixPasswdFile` | Darwin,Linux | 2 FILE | Unix passwd file. |
| `UnixShadowBackupFile` | Darwin,Linux | 2 FILE | Unix shadow backup file. |
| `UnixShadowFile` | Darwin,Linux | 2 FILE | Unix shadow file. |
| `UnixSudoersConfigurationFile` | Darwin,Linux | 2 FILE | Unix sudoers configuration file. |
| `UnixUsersGroups` | Darwin,Linux | 1 ARTIFACT_GROUP | Unix users and groups files. |
| `UnixUtmpFile` | Darwin,Linux | 2 FILE | Utmp login record files. |
| `UserDownloadsDirectory` | Darwin,Linux,Windows | 2 PATH | Contents of user Downloads directories. |
| `UsersDirectory` | Darwin,Windows | 1 PATH | Contents of the Users directory. |
| `vCenterServerAgentLog` | ESXi | 1 FILE | Contains information about the agent that communicates with vCenter Server (if the host is... |
| `Viminfo` | Linux | 1 FILE | Viminfo file. |
| `VSCodeExtensionsPath` | Darwin,Linux,Windows | 2 PATH | Get paths of Visual Studio Code extensions |
| `vSphereClientLogsDirectory` | ESXi | 1 FILE | vSphere Client Logs Directory |
| `WebKitPubSubSQLiteDatabaseFile` | Darwin | 1 FILE | WebKit RSS feed (PubSub) SQLite database file. |
| `WgetHSTSdatabase` | Linux | 1 FILE | Default wget HTTP Strict Transport Security (HSTS) database |
| `WinDomainName` | Windows | 1 REGISTRY_VALUE | The Windows domain the system is connected to. |
| `WindowsActionCenterSettings` | Windows | 1 REGISTRY_VALUE | Windows Action Center Settings Malware can modify these keys to disable notifications that... |
| `WindowsActiveDesktop` | Windows | 1 REGISTRY_KEY | Windows Active Desktop settings and components. |
| `WindowsActiveDirectoryDatabaseFile` | Windows | 1 FILE | Windows Active Directory database file (ntds.dit). |
| `WindowsActiveSyncAutoStart` | Windows | 1 REGISTRY_KEY | Windows ActiveSync AutoStart entries |
| `WindowsActivitiesCacheDatabase` | Windows | 1 FILE | SQLite database containing the Windows activities cache. |
| `WindowsAlternateShell` | Windows | 1 REGISTRY_VALUE | Alternate Shell to be run via Userinit. |
| `WindowsAMCacheHveFile` | Windows | 1 FILE | The AMCache file, stored in the Windows NT Registry file format. |
| `WindowsAppCertDLLs` | Windows | 1 REGISTRY_KEY | Windows AppCertDLLs persistence. |
| `WindowsAppCompatCache` | Windows | 1 REGISTRY_VALUE | Windows Application Compatibility Cache |
| `WindowsAppInitDLLs` | Windows | 1 REGISTRY_VALUE | Windows Application Initial (AppInit) DLLs persistence. AppInit DLLs is a mechanism that a... |
| `WindowsApplicationCompatibilityInstalledShimDatabases` | Windows | 1 FILE | Windows Application Compatibility Installed Shim Databases. drvmain.sdb, frxmain.sdb, msim... |
| `WindowsApplicationCompatibilityShimDatabaseMappings` | Windows | 1 REGISTRY_VALUE | Windows Application Compatibility Shim Database Mappings. Mappings between the Windows App... |
| `WindowsApplicationCompatibilityShims` | Windows | 1 ARTIFACT_GROUP | Windows Application Compatibility Shim Database Files and Application Mappings |
| `WindowsApplicationRegistration` | Windows | 1 REGISTRY_KEY | Windows Application Registration (AppPath) Registry keys. |
| `WindowsAppXRT` | Windows | 1 FILE | WinAppXRT DLL loaded by .Net applications when the APPX_PROCESS environment variable is se... |
| `WindowsAutoexecBat` | Windows | 1 FILE | Windows autoexec.bat file |
| `WindowsAutomaticDebugging` | Windows | 1 REGISTRY_VALUE | Windows automatic debugging (Aedebug) |
| `WindowsAutomaticDebuggingExclusionList` | Windows | 1 REGISTRY_KEY | Windows automatic debugging (Aedebug) exclusion list |
| `WindowsAutorun` | Windows | 1 FILE | Filebased Tests. |
| `WindowsAvailableTimeZones` | Windows | 1 REGISTRY_KEY | Timezones available on a Windows system. |
| `WindowsBackgroundActivityModeratorKeys` | Windows | 1 REGISTRY_KEY | Windows Background Activity Moderator (BAM) and Desktop Activity Moderator (DAM) registry ... |
| `WindowsBITSQueueManagerDatabases` | Windows | 1 FILE | Databases that contain the Windows BITS jobs definition and state. |
| `WindowsBootConfigurationDataRegistryFiles` | Windows | 1 FILE | Boot Configuration Data (BCD) Windows Registry files. |
| `WindowsBootConfigurationSettings` | Windows | 1 REGISTRY_VALUE | Windows Boot Configuration Settings |
| `WindowsBootVerificationProgram` | Windows | 1 REGISTRY_VALUE | Path to custom startup verification program. |
| `WindowsCIMRepositoryFiles` | Windows | 1 FILE | Windows Common Information Model (CIM) repository. Persistent database that holds the sche... |
| `WindowsCodePage` | Windows | 1 REGISTRY_VALUE | The system code page. |
| `WindowsCOMInprocHandlers` | Windows | 1 REGISTRY_VALUE | Windows COM in-process handlers |
| `WindowsCOMInprocServers` | Windows | 1 REGISTRY_VALUE | Windows COM in-process servers |
| `WindowsCOMLocalServers` | Windows | 1 REGISTRY_VALUE | Windows COM local servers |
| `WindowsCommandProcessorAutoRun` | Windows | 1 REGISTRY_VALUE | Commands that are run each time the Command Processor (Cmd.exe) is started. |
| `WindowsCommonFilePlacementAttacks` | Windows | 1 FILE | Common files associated with search order hijacking and other file placement attacks. |
| `WindowsCOMProperties` | Windows | 1 REGISTRY_VALUE | Various properties of Windows COM Objects. These artifacts are meant to highlight properti... |
| `WindowsComputerName` | Windows | 1 REGISTRY_VALUE | The name of the system. |
| `WindowsCOMRegisteredTypeLibraries` | Windows | 1 REGISTRY_VALUE | Windows COM registered type libraries |
| `WindowsConfigSys` | Windows | 1 FILE | Windows config.sys file |
| `WindowsControlPanelFilePaths` | Windows | 1 REGISTRY_KEY | DLLs listed here will be run when the user opens the Windows Control Panel. |
| `WindowsCortanaDatabase` | Windows | 1 FILE | Windows Cortana database |
| `WindowsCrashDumps` | Windows | 1 FILE | Windows Error Reporting (WER) files and crash dumps. The files include information about t... |
| `WindowsCredentialProviderFilters` | Windows | 1 REGISTRY_KEY | Windows Credential Provider Filters |
| `WindowsCredentialProviders` | Windows | 1 REGISTRY_KEY | CLSIDs of applications to use as Credential Providers |
| `WindowsCryptnetUrlCacheContent` | Windows | 1 FILE | Content of a Windows cache of files downloaded from the internet. Helpful when investigati... |
| `WindowsCryptnetUrlCacheMetadata` | Windows | 1 FILE | Metadata of a Windows cache of files downloaded from the internet. Helpful when investigat... |
| `WindowsCurrentVersion` | Windows | 1 REGISTRY_VALUE | The Windows current version |
| `WindowsDebugger` | Windows | 1 REGISTRY_VALUE | Windows Debugger peristence or AV disable. |
| `WindowsDefenderExclusions` | Windows | 1 REGISTRY_KEY | Directories, processes and extensions configured not to be scanned by Windows Defender. Th... |
| `WindowsDefenderScanDetectionHistoryFiles` | Windows | 1 FILE | Microsoft Windows Defender scan detection history files. |
| `WindowsDisallowedSystemCertificates` | Windows | 1 REGISTRY_KEY | Windows Disallowed System Certificates Malware can add code-signing certificates associate... |
| `WindowsDNSSettings` | Windows | 1 REGISTRY_VALUE | Windows Registry Keys that contain DNS and DHCP settings. |
| `WindowsDomainCachedCredentials` | Windows | 1 REGISTRY_VALUE | Windows domain cached credentials |
| `WindowsDomainName` | Windows | 1 REGISTRY_VALUE | The domain the system is connected to. |
| `WindowsEnvironmentUserLoginScripts` | Windows | 1 REGISTRY_VALUE | User login scripts configured via Windows environment variables. |
| `WindowsEnvironmentVariableAllUsersAppData` | Windows | 1 REGISTRY_VALUE | The %ProgramData% environment variable. |
| `WindowsEnvironmentVariableAllUsersProfile` | Windows | 1 REGISTRY_VALUE | The system-wide %AllUsersProfile% environment variable contains the path of the of the "Al... |
| `WindowsEnvironmentVariableAppxProcess` | Windows | 1 REGISTRY_VALUE | The user-specific %APPX_PROCESS% environment variable is used for .NET applications. If se... |
| `WindowsEnvironmentVariableCommonProgramFiles` | Windows | 1 REGISTRY_VALUE | The %COMMONPROGRAMFILES% environment variable contains the path of the common program file... |
| `WindowsEnvironmentVariableCommonProgramFilesX86` | Windows | 1 REGISTRY_VALUE | The %COMMONPROGRAMFILES(X86)% environment variable contains the path of the 32-bit common ... |
| `WindowsEnvironmentVariableComSpec` | Windows | 1 REGISTRY_VALUE | The %ComSpec% environment variable contains the path of the command processor, typically "... |
| `WindowsEnvironmentVariableDriverData` | Windows | 1 REGISTRY_VALUE | The %DriverData% environment variable contains the path of the directory used for temporar... |
| `WindowsEnvironmentVariablePath` | Windows | 1 REGISTRY_VALUE | The %PATH% environment variable contains an ordered list of paths of directories that will... |
| `WindowsEnvironmentVariableProfilesDirectory` | Windows | 1 REGISTRY_VALUE | The %ProfilesDirectory% environment variable contain a path of a directory that contains t... |
| `WindowsEnvironmentVariableProgramData` | Windows | 1 REGISTRY_VALUE | The %ProgramData% environment variable contains a path of the "Program Data" directory. |
| `WindowsEnvironmentVariableProgramFiles` | Windows | 1 PATH, 1 REGISTRY_VALUE | The %ProgramFiles% environment variable contains a path of the "Program Files" directory. |
| `WindowsEnvironmentVariableProgramFilesX86` | Windows | 1 PATH, 1 REGISTRY_VALUE | The %ProgramFiles(x86)% environment variable contains a path of the 32-bit "Program Files"... |
| `WindowsEnvironmentVariableSystemDrive` | Windows | 1 ARTIFACT_GROUP | The %SystemDrive% environment variable contains the letter of the drive in which the syste... |
| `WindowsEnvironmentVariableSystemRoot` | Windows | 1 PATH, 1 REGISTRY_VALUE | The %SystemRoot%, environment variable contains the path of the system directory, typicall... |
| `WindowsEnvironmentVariableTemp` | Windows | 1 REGISTRY_VALUE | The %TEMP% environment variable. |
| `WindowsEnvironmentVariableWinDir` | Windows | 1 PATH, 1 REGISTRY_VALUE | The %WinDir%, environment variable contains the path of the Windows directory, typically "... |
| `WindowsEventLogApplication` | Windows | 1 FILE | Application Windows Event Log. |
| `WindowsEventLogPublishers` | Windows | 1 REGISTRY_KEY | Windows EventLog publishers (or providers) Registry keys. |
| `WindowsEventLogs` | Windows | 1 FILE | Windows Event logs. |
| `WindowsEventLogSecurity` | Windows | 1 FILE | Security Windows Event Log. |
| `WindowsEventLogSources` | Windows | 1 REGISTRY_KEY | Windows EventLog sources Registry keys. |
| `WindowsEventLogSystem` | Windows | 1 FILE | System Windows Event Log. |
| `WindowsEventTracingLogFiles` | Windows | 1 FILE | Event Tracing for Windows (ETW) log files. |
| `WindowsExcludeFromKnownDLLs` | Windows | 1 REGISTRY_VALUE | ExcludeFromKnownDLLs can be used to bypass search order hijacking protection. |
| `WindowsExplorerAppKey` | Windows | 1 REGISTRY_VALUE | Handlers for special keys on some keyboards (file path or CLSID). |
| `WindowsExplorerAutoplayHandlers` | Windows | 1 REGISTRY_KEY | Handlers for autoplay events in Windows Explorer. |
| `WindowsExplorerContextMenuHandlers` | Windows | 1 REGISTRY_VALUE | Handlers for subcommands on context menu |
| `WindowsExplorerNamespaceCommonPlaces` | Windows | 1 REGISTRY_KEY | CLSIDs listed here are used to populate the Common Places items. |
| `WindowsExplorerNamespaceControlPanel` | Windows | 1 REGISTRY_KEY | CLSIDs listed here are used to populate the Control Panel items. |
| `WindowsExplorerNamespaceDesktop` | Windows | 1 REGISTRY_KEY | CLSIDs listed here are used to populate the Desktop items. |
| `WindowsExplorerNamespaceMyComputer` | Windows | 1 REGISTRY_KEY | CLSIDs listed here are used to populate the MyComputer items. |
| `WindowsExplorerNamespaceNetworkNeighborhood` | Windows | 1 REGISTRY_KEY | CLSIDs listed here are used to populate the Network Neighborhood items. |
| `WindowsExplorerNamespacePrintersAndFaxes` | Windows | 1 REGISTRY_KEY | CLSIDs listed here are used to populate the Printer and Fax items. |
| `WindowsExplorerSettings` | Windows | 1 REGISTRY_VALUE | Windows Explorer Settings Malware can modify these keys to make it more difficult for the ... |
| `WindowsFileTypeAutorunAssociations` | Windows | 1 REGISTRY_VALUE | Registry value for what application class identifier (CLSID) to launch for a file extensio... |
| `WindowsFirewallAuthorizedApplications` | Windows | 1 REGISTRY_KEY | Windows Firewall Authorized Applications Malware can add paths to this list to more easily... |
| `WindowsFirewallEnabledRules` | Windows | 1 COMMAND | Command to list the enabled Windows Firewall rules. |
| `WindowsFirewallGloballyOpenPorts` | Windows | 1 REGISTRY_KEY | Windows Firewall Globally Open Ports Malware can add to the list of open ports to avoid ha... |
| `WindowsFirewallLogFile` | Windows | 1 FILE | Windows Firewall default logfile |
| `WindowsFirewallPolicySettings` | Windows | 1 REGISTRY_VALUE | Windows Firewall Policy Settings Malware can modify these settings to more easily communic... |
| `WindowsFirewallRules` | Windows | 1 COMMAND | Command to list the configured Windows Firewall rules. |
| `WindowsFontDrivers` | Windows | 1 REGISTRY_KEY | Windows font drivers from the Registry. |
| `WindowsGroupPolicyScripts` | Windows | 1 FILE | Windows group policy scripts |
| `WindowsHelpCenterDatabaseFile` | Windows | 1 FILE | Windows Help Center database file (HCdata.edb). |
| `WindowsHostsFiles` | Windows | 1 FILE | The Windows hosts and lmhosts file. |
| `WindowsHotkeyReplacement` | Windows | 1 FILE | Hotkey executable replacement. |
| `WindowsIconServiceLib` | Windows | 1 REGISTRY_VALUE | Windows Icon Service Library Name The value should default to 'IconCodecService.dll' |
| `WindowsInstallationDateTime` | Windows | 1 REGISTRY_VALUE | Windows installation date and time |
| `WindowsLanguage` | Windows | 1 REGISTRY_VALUE | The system language. |
| `WindowsLogoffScript` | Windows | 1 REGISTRY_VALUE | Windows policy logoff script |
| `WindowsLogonScript` | Windows | 1 REGISTRY_VALUE | Windows policy logon script |
| `WindowsLSAAuthenticationPackages` | Windows | 1 REGISTRY_VALUE | Authentication Packages can be injected into LSASS. |
| `WindowsLSANotificationPackages` | Windows | 1 REGISTRY_VALUE | Notification Packages can be injected into LSASS. |
| `WindowsLSASecurityPackages` | Windows | 1 REGISTRY_VALUE | Security Packages can be injected into LSASS. |
| `WindowsMapNetworkDriveMRU` | Windows | 1 REGISTRY_KEY | Recently mapped network shares. |
| `WindowsMetroApplicationCache` | Windows | 1 FILE | Windows Metro application cache. |
| `WindowsMetroApplicationCookies` | Windows | 1 FILE | Windows Metro application cookies. |
| `WindowsMetroApplicationHistory` | Windows | 1 FILE | Windows Metro application history. |
| `WindowsMetroUserPinnedFavoriteTiles` | Windows | 1 FILE | Windows Metro user-pinned favorite tiles. |
| `WindowsMostRecentApplication` | Windows | 1 REGISTRY_VALUE | Windows Most Recent Application name key |
| `WindowsMountedDevices` | Windows | 1 REGISTRY_KEY | Windows mounted devices |
| `WindowsMSDTCDLLs` | Windows | 1 REGISTRY_KEY | Windows MSDTC attempts to load these DLLs on start |
| `WindowsMultiMediaDrivers` | Windows | 1 REGISTRY_KEY | Configured drivers for different multimedia filetypes. |
| `WindowsNetworkShellHelpers` | Windows | 1 REGISTRY_KEY | Windows Network Shell (netsh) helpers are loaded on boot |
| `WindowsOpenSaveMRU` | Windows | 1 REGISTRY_KEY | Information about files opened or saved in a Windows shell dialog. |
| `WindowsOpenSavePidlMRU` | Windows | 1 REGISTRY_KEY | Information about files opened or saved in a Windows shell dialog. |
| `WindowsPendingFileRenames` | Windows | 1 REGISTRY_VALUE | Windows Pending file renames on reboot |
| `WindowsPendingGPOs` | Windows | 1 REGISTRY_VALUE | Windows Pending GPOs registry settings. This is a persistence mechanism known to be used b... |
| `WindowsPersistenceMechanisms` | Windows | 1 ARTIFACT_GROUP | Persistence mechanisms in Windows. |
| `WindowsPersistenceRegistryKeys` | Windows | 1 ARTIFACT_GROUP | Windows Registry keys used for persistence. |
| `WindowsPLAPProviders` | Windows | 1 REGISTRY_KEY | Windows Pre-Logon Access Provider (PLAP) Providers |
| `WindowsPolicyDisallowRun` | Windows | 1 REGISTRY_KEY | Restrict users from running specific applications, typically used by malware to block AV. |
| `WindowsPortProxyConfiguration` | Windows | 1 REGISTRY_KEY | Windows PortProxy registry keys (set by netsh portproxy command or manually). |
| `WindowsPowerShellDefaultProfiles` | Windows | 1 FILE | Default PowerShell Profile files. These files are executed by default when PowerShell star... |
| `WindowsPowerShellEnableScripts` | Windows | 1 REGISTRY_VALUE | Registry keys that control whether PowerShell scripts can execute directly. |
| `WindowsPowerShellExecutionPolicies` | Windows | 1 REGISTRY_VALUE | PowerShell Script Execution Policies for all users, and the system. |
| `WindowsPowerShellHistory` | Windows | 1 FILE | History of commands executed in an interactive PowerShell session. |
| `WindowsPrefetchFiles` | Windows | 1 FILE | Windows Prefetch files. |
| `WindowsPrintMonitors` | Windows | 1 REGISTRY_VALUE | Windows Print Monitor DLL config. |
| `WindowsProductName` | Windows | 1 REGISTRY_VALUE | The Windows product name |
| `WindowsProgramsCache` | Windows | 1 REGISTRY_VALUE | Windows Programs Cache |
| `WindowsProgramsCacheJumpLists` | Windows | 1 REGISTRY_VALUE | Windows Programs Cache Jump Lists |
| `WindowsProxyPACAutoConfigURL` | Windows | 1 REGISTRY_VALUE | Windows Proxy PAC AutoConfigURL. |
| `WindowsProxyServerSettings` | Windows | 1 REGISTRY_VALUE | Windows Proxy Server Settings. Malware can modify these settings to redirect traffic throu... |
| `WindowsPushNotificationDatabaseFile` | Windows | 1 FILE | The Windows Push Notification (WPN) database file. |
| `WindowsRDPClientBitmapCache` | Windows | 1 FILE | Artifacts of RDP connection contents |
| `WindowsRecentFileCacheBCF` | Windows | 1 FILE | The RecentFileCache.bcf file. |
| `WindowsRecycleBin` | Windows | 1 FILE | Windows Recycle Bin (Recyler, $Recycle.Bin) files. |
| `WindowsRecycleBinMetadata` | Windows | 1 FILE | Windows Recycle Bin (Recyler, $Recycle.Bin) metadata files only. |
| `WindowsRegistryCurrentControlSet` | Windows | 1 REGISTRY_VALUE | The current control set of the Windows Registry. |
| `WindowsRegistryFilesAndTransactionLogs` | Windows | 1 ARTIFACT_GROUP | Windows user and system Registry files and transaction logs. |
| `WindowsRegistryProfiles` | Windows | 1 REGISTRY_VALUE | Get SIDs for all users on the system with profiles present in the Registry. This looks in ... |
| `WindowsReleaseIdentifier` | Windows | 1 REGISTRY_VALUE | The Windows 10 release identifier (or version number). This Windows Registry value contain... |
| `WindowsRoverAutostartDLL` | Windows | 1 FILE | Windows Rover autostart DLL. The DLL loaded via the Windows Rover autostart mechanism. If ... |
| `WindowsRoverAutostartKey` | Windows | 1 REGISTRY_KEY | Windows Rover autostart Registry key. When set userinit.exe will load the DLL at %SystemRo... |
| `WindowsRunGrpConv` | Windows | 1 REGISTRY_VALUE | The Windows RunGrpConv Registry value. When this Registry value is non-zero userinit.exe w... |
| `WindowsRunKeys` | Windows | 1 REGISTRY_KEY | Windows Run and RunOnce keys. Note users.sid will currently only expand to SIDs with profi... |
| `WindowsRunServices` | Windows | 1 REGISTRY_KEY | Windows Run Services. |
| `WindowsScheduledTasks` | Windows | 1 FILE | Windows Scheduled Tasks. |
| `WindowsScreenSaverExecutable` | Windows | 1 REGISTRY_VALUE | ScreenSaver Executable |
| `WindowsSearchDatabaseFile` | Windows | 1 FILE | Windows Search database (Windows.edb). |
| `WindowsSearchFilterHandlers` | Windows | 1 REGISTRY_VALUE | Windows Search filter handlers configured for file types and applications. Windows Search ... |
| `WindowsSecurityCenterSettings` | Windows | 1 REGISTRY_VALUE | Windows Security Center Settings Malware can modify these settings to avoid detection on a... |
| `WindowsSecurityProviders` | Windows | 1 REGISTRY_KEY | Security Providers DLLs |
| `WindowsSecuritySettingsDatabases` | Windows | 1 FILE | Windows security settings databases (secedit.sdb and spsecupd.sdb) |
| `WindowsServiceControlManagerExtension` | Windows | 1 REGISTRY_VALUE | Windows service control manager extension |
| `WindowsServices` | Windows | 1 REGISTRY_KEY | Windows service and driver configurations. |
| `WindowsSessionManagerBootExecute` | Windows | 1 REGISTRY_VALUE | Windows Session Manager BootExecute persistence. |
| `WindowsSessionManagerExecute` | Windows | 1 REGISTRY_VALUE | Windows Session Manager Execute persistence This entry shouldn't be populated after Window... |
| `WindowsSessionManagerS0InitialCommand` | Windows | 1 REGISTRY_VALUE | Windows Session Manager S0InitialCommand persistence This entry shouldn't be populated aft... |
| `WindowsSessionManagerSetupExecute` | Windows | 1 REGISTRY_VALUE | Windows Session Manager SetupExecute persistence This entry shouldn't be populated after W... |
| `WindowsSessionManagerSubSystems` | Windows | 1 REGISTRY_VALUE | Windows Session Manager SubSystems persistence |
| `WindowsSessionManagerWOWCommandLine` | Windows | 1 REGISTRY_VALUE | Windows Session Manager Windows-on-Windows (WOW) command line |
| `WindowsSetupApiLogs` | Windows | 1 FILE | Windows setup API logs. |
| `WindowsSetupCommandLine` | Windows | 1 REGISTRY_VALUE | Command line invocation used for custom setup and deployment tasks |
| `WindowsSharedTaskScheduler` | Windows | 1 REGISTRY_KEY | Runs on windows boot. |
| `WindowsShellExecuteHooks` | Windows | 1 REGISTRY_KEY | Shell execution hooks are called when ShellExecuteEx() is called. |
| `WindowsShellExtensions` | Windows | 1 REGISTRY_KEY | Approved extensions to the Windows Shell (explorer.exe). |
| `WindowsShellHandlersRegistryKeys` | Windows | 1 REGISTRY_KEY | Windows registry values for shell handler artifacts. ContextMenuHandlers are added to righ... |
| `WindowsShellIconOverlayIdentifiers` | Windows | 1 REGISTRY_KEY | Called to display custom icons. |
| `WindowsShellLoadAndRun` | Windows | 1 REGISTRY_VALUE | Windows Shell Load and Run values |
| `WindowsShellOpenCommand` | Windows | 1 REGISTRY_VALUE | Executed every time this file type is opened. For most file types, the value should be '"%... |
| `WindowsShellRunasCommand` | Windows | 1 REGISTRY_VALUE | Executed every time an executable or script file type is run as administrator. For most fi... |
| `WindowsShellServiceObjects` | Windows | 1 REGISTRY_KEY | Windows Shell (explorer.exe) service objects delayed load. |
| `WindowsShutdownScript` | Windows | 1 REGISTRY_VALUE | Windows policy shutdown script |
| `WindowsSiemensWinCCLogFile` | Windows | 1 FILE | Siemens WinCC software logs. |
| `WindowsSmsRouterInterceptStoreDatabaseFile` | Windows | 1 FILE | Windows SmsRouter intercept store database file (SmsInterceptStore.db) |
| `WindowsStartupFolderModification` | Windows | 1 REGISTRY_VALUE | Windows startup folder Registry values. |
| `WindowsStartupFolders` | Windows | 1 FILE | Windows startup folder persistence. |
| `WindowsStartupInfo` | Windows | 1 FILE | StartupInfo XML files. The files include the user account's Security Identifier (SID) in t... |
| `WindowsStartupScript` | Windows | 1 REGISTRY_VALUE | Windows policy startup script |
| `WindowsStateRepositoryDeploymentDatabaseFile` | Windows | 1 FILE | The State Reposistory deployment database file (StateRepository-Deployment.srd). |
| `WindowsStateRepositoryMachineDatabaseFile` | Windows | 1 FILE | The State Reposistory machine database file (StateRepository-Machine.srd). |
| `WindowsStubPaths` | Windows | 1 REGISTRY_VALUE | Windows StubPath persistence. Each time a user logs in, the Active Setup Installed Compone... |
| `WindowsSuperFetchFiles` | Windows | 1 FILE | Windows SuperFetch files. |
| `WindowsSystemIniFiles` | Windows | 1 FILE | Windows system ini files |
| `WindowsSystemPolicyShell` | Windows | 1 REGISTRY_VALUE | Windows System policy replacement shell (custom user interface). |
| `WindowsSystemRegistryFiles` | Windows | 1 FILE | Windows system Registry files. |
| `WindowsSystemRegistryFilesAndTransactionLogs` | Windows | 1 ARTIFACT_GROUP | Windows system Registry files and transaction logs. |
| `WindowsSystemRegistryFilesAndTransactionLogsBackup` | Windows | 1 ARTIFACT_GROUP | Backup of Windows system Registry files and transaction logs. |
| `WindowsSystemRegistryFilesBackup` | Windows | 1 FILE | Backup of Windows system Registry files. |
| `WindowsSystemRegistryTransactionLogFiles` | Windows | 1 FILE | Windows system Registry transaction log files. |
| `WindowsSystemRegistryTransactionLogFilesBackup` | Windows | 1 FILE | Backup of Windows system Registry transaction log files. These files have been observed to... |
| `WindowsSystemResourceUsageMonitorDatabaseFile` | Windows | 1 FILE | Windows System Resource Usage Monitor (SRUM) database file. |
| `WindowsSystemRestoreSettings` | Windows | 1 REGISTRY_VALUE | Windows System Restore Settings Some malware, especially ransomware, will disable system r... |
| `WindowsSystemSettings` | Windows | 1 REGISTRY_VALUE | Windows System Settings Malware can modify these keys to make it more difficult for the us... |
| `WindowsTempDirectories` | Windows | 1 FILE | Contents of the Windows temporary directories |
| `WindowsTerminalServerInitialProgram` | Windows | 1 REGISTRY_VALUE | Windows Terminal Server Initial Program |
| `WindowsTerminalServerRunKeys` | Windows | 1 REGISTRY_KEY | Windows Terminal Server Run keys |
| `WindowsTerminalServerStartupPrograms` | Windows | 1 REGISTRY_VALUE | Windows Terminal Server Startup Programs |
| `WindowsThumbcacheDatabaseFiles` | Windows | 1 FILE | Windows thumbcache_*.db files. |
| `WindowsTileDataLayerDatabase` | Windows | 1 FILE | Windows tile data layer database (vedatamodel.edb) The tile data layer database is used to... |
| `WindowsTimezone` | Windows | 1 REGISTRY_VALUE | The time zone of the system as a Windows time zone name or in MUI form. |
| `WindowsToolPaths` | Windows | 1 REGISTRY_KEY | Paths to windows tools such as defrag, chkdsk. |
| `WindowsUninstallKeys` | Windows | 1 REGISTRY_KEY | Uninstall Registry keys |
| `WindowsUpdateBuildRevision` | Windows | 1 REGISTRY_VALUE | Windows kernel update build revision (UBR). This Windows Registry value contains the month... |
| `WindowsUpdateCatalogDatabaseFile` | Windows | 1 FILE | Windows Update catalog package signatures database file (catdb). |
| `WindowsUpdateDataStoreDatabaseFile` | Windows | 1 FILE | Windows Update data store database file (DataStore.edb). |
| `WindowsUpdateLogFile` | Windows | 1 FILE | Windows Update log files. |
| `WindowsUpdateSettings` | Windows | 1 REGISTRY_VALUE | Windows Update Settings |
| `WindowsUpdateStatus` | Windows | 1 REGISTRY_VALUE | Windows auto update status. |
| `WindowsUpdateStoreDatabaseFile` | Windows | 1 FILE | The Update Service Orchestrator (USO) private update store database file. |
| `WindowsUpgradeSettings` | Windows | 1 REGISTRY_VALUE | Windows Upgrade Settings Malware sometimes disables a machine ability to upgrade from prev... |
| `WindowsUserAccessLogging` | Windows | 1 FILE | User Access Logging (UAL) databases. UAL is a local data aggregation feature (enabled by d... |
| `WindowsUserAccountControlSettings` | Windows | 1 REGISTRY_VALUE | Windows User Account Control Settings Malware sometimes disables UAC to make it easier to ... |
| `WindowsUserAutomaticDestinationsJumpLists` | Windows | 1 FILE | Windows user AutomaticDestinations Jump Lists. |
| `WindowsUserCustomDestinationsJumpLists` | Windows | 1 FILE | Windows user CustomDestinations Jump Lists. |
| `WindowsUserJumpLists` | Windows | 1 ARTIFACT_GROUP | Windows user Jump Lists. |
| `WindowsUserRecentFiles` | Windows | 1 FILE | Windows user specific recent files. |
| `WindowsUserRegistryFiles` | Windows | 1 FILE | Windows user specific Registry files. |
| `WindowsUserRegistryFilesAndTransactionLogs` | Windows | 1 ARTIFACT_GROUP | Windows user Registry files and transaction logs. |
| `WindowsUserRegistryTransactionLogFiles` | Windows | 1 FILE | Windows user Registry transaction log files. |
| `WindowsUserShellFolders` | Windows | 1 REGISTRY_KEY | The Shell Folders information for Windows users. |
| `WindowsWebCacheStorageQuotaDatabaseFile` | Windows | 1 FILE | Windows WebCache storage quota database file (CacheStorage.edb) |
| `WindowsWinlogonAppSetup` | Windows | 1 REGISTRY_VALUE | Windows Winlogon Appsetup |
| `WindowsWinlogonAvailableShells` | Windows | 1 REGISTRY_KEY | Windows Server Winlogon Available Shells Used to specify an alternate shell application to... |
| `WindowsWinlogonGinaDLL` | Windows | 1 REGISTRY_VALUE | Windows Gina DLL replacement. |
| `WindowsWinlogonGPExtensions` | Windows | 1 REGISTRY_VALUE | Windows Winlogon Group Policy Extensions These keys specify DLLs that should be loaded whe... |
| `WindowsWinlogonNotify` | Windows | 1 REGISTRY_VALUE | Windows Winlogon Notify DLL names. |
| `WindowsWinlogonShell` | Windows | 1 REGISTRY_VALUE | Windows shell replacement. |
| `WindowsWinlogonSystem` | Windows | 1 REGISTRY_VALUE | Applications launched by Winlogon in the system context during the system initialisation. |
| `WindowsWinlogonTaskman` | Windows | 1 REGISTRY_VALUE | Windows Winlogon Taskman replacement. |
| `WindowsWinlogonUiHost` | Windows | 1 REGISTRY_VALUE | Windows Winlogon UI screen application |
| `WindowsWinlogonUserinit` | Windows | 1 REGISTRY_VALUE | Windows Winlogon Userinit replacement. |
| `WindowsWinlogonVMApplet` | Windows | 1 REGISTRY_VALUE | Windows VMApplet replacement. |
| `WindowsWinstart` | Windows | 1 FILE | Windows winstart.bat file |
| `WindowsWordWheelQueryRegistryKey` | Windows | 1 REGISTRY_KEY | Keywords searched in from the Windows start menu, potentially resulting in files or folder... |
| `WindowsXMLEventLogApplication` | Windows | 1 FILE | Application Windows XML Event Log. |
| `WindowsXMLEventLogPowerShell` | Windows | 1 FILE | PowerShell Windows XML Event Logs. |
| `WindowsXMLEventLogSecurity` | Windows | 1 FILE | Security Windows XML Event Log. |
| `WindowsXMLEventLogSysmon` | Windows | 1 FILE | Sysmon Windows XML Event Log. |
| `WindowsXMLEventLogSystem` | Windows | 1 FILE | System Windows XML Event Log. |
| `WindowsXMLEventLogTerminalServices` | Windows | 1 FILE | TerminalServices Windows XML Event Log. |
| `WinRARAVScan` | Windows | 1 REGISTRY_VALUE | Executable run to scan a file when it is opened by WinRAR. |
| `WinRARExternalViewer` | Windows | 1 REGISTRY_VALUE | Executable run when a file is opened by WinRAR inside an archive. |
| `WinSock2LayeredServiceProviders` | Windows | 1 REGISTRY_KEY | Used to filter TCP/IP traffic through WinSock2. |
| `WinSock2NamespaceProviders` | Windows | 1 REGISTRY_VALUE | Used to provide name-resolution services through WinSock2 |
| `WMIAccountUsersDomain` | Windows | 1 WMI | Fill out user AD domain information based on username. We expect this artifact to be colle... |
| `WMIAntivirusProduct` | Windows | 1 WMI | Enumerate the registered antivirus. |
| `WMICCMRUA` | Windows | 1 WMI | Enumerate instances of CCM_RecentlyUsedApps. |
| `WMIComputerSystemProduct` | Windows | 1 WMI | Computer System Product including Identifiying number queried from WMI. |
| `WMIDNSClientCache` | Windows | 1 WMI | DNS client cache via Windows Management Instrumentation (WMI). |
| `WMIDrivers` | Windows | 1 WMI | Installed drivers via Windows Management Instrumentation (WMI). |
| `WMIEnumerateASEC` | Windows | 1 WMI | Enumerate instances of ActiveScriptEventConsumer. |
| `WMIEnumerateCLEC` | Windows | 1 WMI | Enumerate instances of CommandLineEventConsumer. |
| `WMIHotFixes` | Windows | 1 WMI | Installed hotfixes via Windows Management Instrumentation (WMI). |
| `WMIInstalledSoftware` | Windows | 1 WMI | Installed software via Windows Management Instrumentation (WMI). |
| `WMILastBootupTime` | Windows | 1 WMI | Last system boot time (UTC) retrieved from WMI. |
| `WMILoggedOnSessions` | Windows | 1 WMI | Logged on users queried from WMI. |
| `WMILoggedOnUsers` | Windows | 1 WMI | Logged on users queried from WMI. |
| `WMILogicalDisks` | Windows | 1 WMI | Disk information via Windows Management Instrumentation (WMI). |
| `WMILoginUsers` | Windows | 1 WMI | Login Users via Windows Management Instrumentation (WMI). This WMI query may take a long t... |
| `WMINetNeighbors` | Windows | 1 WMI | TCP/IP neighbors via Windows Management Instrumentation (WMI). |
| `WMINetTCPConnections` | Windows | 1 WMI | TCP connections via Windows Management Instrumentation (WMI). |
| `WMINetUDPEndpoints` | Windows | 1 WMI | UDP endpoints via Windows Management Instrumentation (WMI). |
| `WMIOperatingSystem` | Windows | 1 WMI | Operating system installed on the computer via Windows Management Instrumentation (WMI). |
| `WMIPhysicalMemory` | Windows | 1 WMI | Physical memory information via Windows Management Instrumentation (WMI). |
| `WMIProcessList` | Windows | 1 WMI | Process listing via Windows Management Instrumentation (WMI). |
| `WMIProfileUsersHomeDir` | Windows | 1 WMI | Get user homedir from Win32_UserProfile based on a known user's SID. This artifact relies ... |
| `WMIScheduledTasks` | Windows | 1 WMI | Scheduled tasks that are registered on the computer via Windows Management Instrumentation... |
| `WMIServices` | Windows | 1 WMI | Services queried from WMI. |
| `WMIStartupCommands` | Windows | 1 WMI | Commands that run automatically when a user logs onto the computer system via Windows Mana... |
| `WMIUsers` | Windows | 1 WMI | Users via Windows Management Instrumentation (WMI). Note that in a domain setup, this will... |
| `WMIVolumeShadowCopies` | Windows | 1 WMI | A List of Volume Shadow Copies from WMI. |
| `WordpressConfigFile` | Linux,Darwin | 1 FILE | WordPress configuration file |
| `XChatLogs` | Linux | 1 FILE | XChat Log Files |
| `XDGAutostartEntries` | Linux | 1 FILE | XDG Autostart Entries |
| `YumSources` | Linux | 1 FILE | Yum package sources list |
| `ZeitgeistDatabase` | Linux | 1 FILE | Zeitgeist user activity database. |
| `ZShellConfigurationFile` | Darwin,Linux,Windows | 3 FILE | Z shell (zsh) configuration files. |
| `ZShellHistoryFile` | Darwin,Linux,Windows | 2 FILE | Z shell (zsh) history files. |
<!-- genere:artefacts:fin -->





