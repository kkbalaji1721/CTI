"""Small threat-intelligence corpus for the RAG demonstration."""

DOCUMENTS = [
    {
        "source": "CISA-KEV-ransomware-advisory",
        "text": (
            "Threat actors exploiting internet-facing VPN appliances have used stolen credentials "
            "and unpatched edge devices to gain initial access. Recent ransomware incidents show "
            "attackers validating accounts, disabling endpoint defenses, and moving laterally over "
            "SMB and remote administration tools. Defenders should inventory exposed appliances, "
            "apply vendor security updates, require phishing-resistant multifactor authentication, "
            "and remove dormant accounts. Monitor authentication logs for impossible travel, unusual "
            "new devices, repeated failures followed by success, and privilege changes. Segment "
            "management networks and restrict remote access to approved sources. Preserve endpoint "
            "and identity logs before containment. Isolate affected systems, rotate exposed secrets, "
            "and validate backups offline before recovery. Report confirmed exploitation through "
            "the organization's incident-response process."
        ),
    },
    {
        "source": "MITRE-ATTACK-phishing-loader",
        "text": (
            "A phishing campaign distributes a password-protected archive containing a shortcut "
            "that launches a script and retrieves a second-stage loader. The lure impersonates "
            "routine invoice and shipping notifications. The loader establishes persistence with "
            "a scheduled task, fingerprints the host, and contacts rotating command-and-control "
            "domains over encrypted web traffic. Defenders can reduce exposure by filtering "
            "untrusted attachments, blocking script execution from user-writable folders, and "
            "limiting outbound connections from office applications. Investigate suspicious "
            "scheduled tasks, newly created script interpreters, unusual DNS lookups, and child "
            "processes spawned by document readers. Detonate samples only in an isolated analysis "
            "environment. Collect email headers and endpoint telemetry, quarantine matching "
            "messages, and reset credentials if users entered them on an untrusted site."
        ),
    },
    {
        "source": "CISA-cloud-identity-intrusion",
        "text": (
            "Cloud identity intrusions frequently begin with stolen refresh tokens, consent "
            "phishing, or weakly protected service accounts. An attacker may register a new "
            "application, grant excessive OAuth permissions, create forwarding rules, and access "
            "mail or storage without triggering a password prompt. Review sign-in events, token "
            "issuance, application consent grants, mailbox rules, and changes to conditional "
            "access. Revoke active sessions and refresh tokens, disable unauthorized applications, "
            "and rotate credentials for affected identities. Require multifactor authentication "
            "and use phishing-resistant factors for privileged roles. Assign service principals "
            "only the permissions they need, monitor dormant accounts, and alert on anomalous "
            "locations or unfamiliar devices. Preserve audit logs before changing tenant settings "
            "so investigators can establish a timeline and identify accessed resources."
        ),
    },
    {
        "source": "CERT-linux-webshell-advisory",
        "text": (
            "Web servers exposed to an unpatched application vulnerability may be compromised "
            "with a web shell that enables remote command execution. Operators often stage scripts "
            "in writable upload directories, create unexpected service accounts, and use the "
            "server as a pivot to internal systems. Compare web roots and system binaries with "
            "known-good baselines, inspect recent file changes, review process ancestry, and "
            "correlate web access logs with outbound network connections. Patch the vulnerable "
            "application, remove public write access where possible, and place the service behind "
            "a restrictive reverse proxy. If compromise is confirmed, isolate the host, retain a "
            "forensic image and logs, rotate credentials accessible to the service, and rebuild "
            "from trusted media. Do not rely on deleting a suspicious file as proof that the "
            "intrusion has been eradicated."
        ),
    },
    {
        "source": "NIST-supply-chain-malware-note",
        "text": (
            "A compromised software update can deliver malware through a trusted vendor channel. "
            "Risk reduction depends on verifying package provenance, validating digital signatures, "
            "pinning dependency versions, and reviewing changes before deployment. Maintain an "
            "inventory of software components and use a software bill of materials to identify "
            "affected versions quickly. Monitor build agents for unexpected network activity, "
            "new credentials, modified pipeline definitions, and artifacts that differ from "
            "reproducible builds. Separate signing keys from general-purpose CI workers and "
            "require protected approvals for production releases. When an upstream compromise is "
            "announced, identify all deployed versions, preserve relevant build logs, revoke "
            "exposed tokens, and follow vendor and government advisories. Restore services only "
            "after validating clean artifacts and reviewing the full dependency chain."
        ),
    },
]
