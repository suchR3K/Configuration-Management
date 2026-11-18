# Ansible Server Setup

Configure an Ubuntu 24.04 server with four tagged roles, then deploy a packaged static Lab Portal. This project extends the Linux Network Lab with configuration management.

## Scope

| Role | Responsibility |
|---|---|
| `base` | Refresh apt metadata, apply safe upgrades, install utilities and configure fail2ban for SSH |
| `nginx` | Install Nginx, enable a dedicated site and validate before reload |
| `app` | Upload a local tarball, extract a content-addressed release and activate it |
| `ssh` | Add a public key to an existing account, retaining other keys |

Roles run in the required order: base → nginx → app → ssh. Tags allow selective runs. Public-key preflight validation runs before changes on a full or ssh-tagged run.

The default inventory points to the existing lab server at `192.168.50.1`, SSH user `julia`. Update it for another target. The site uses **HTTP port 8080** and `/var/www/ansible-lab-portal`, separate from the earlier portal on port 80. The playbook does not change DHCP, DNS, routing, the default Nginx site or SSH authentication policy. It does install an enabled SSH fail2ban jail, which can temporarily ban repeated failed logins.

## Requirements

- Controller: Ubuntu/Linux (for example lab-client) with Python 3.11+, SSH client, a real SSH key pair and network access to the target. Ansible does not run natively in Windows PowerShell; use a Linux VM or WSL.
- Target: Ubuntu 24.04 with systemd, Python 3, working SSH on port 22, an existing user with sudo access and Internet access for packages.
- Port 8080 must be free. If the target has an input firewall, allow access from your lab client separately. No cloud account or public Internet exposure is needed.

## Install on the controller

Clone this repository on lab-client, change into its directory, then:

```bash
sudo apt-get update
sudo apt-get install -y python3-venv openssh-client
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
ansible-galaxy collection install -r requirements.yml
cp local.example.yml local.yml
```

Edit `local.yml` to point to your existing **public** key file. If you do not have a key pair, run `ssh-keygen -t ed25519` interactively and follow the prompts; do not overwrite an existing key. Keep private keys outside the repository. If your private key is passphrase-protected, load it into ssh-agent before use.

Verify the server identity and connection with `ssh julia@192.168.50.1`. The public key role needs an already working login, either an existing key or password authentication. For password-only initial access, install `sshpass` on the controller and add `--ask-pass` to the first Ansible run; do not store the password in inventory.

## Run

```bash
# No server changes: parse playbook and list tags
ansible-playbook setup.yml --syntax-check
ansible-playbook setup.yml --list-tags

# Configure everything; prompts for the remote sudo password
ansible-playbook setup.yml -e @local.yml --ask-become-pass

# Run again immediately and inspect the recap
ansible-playbook setup.yml -e @local.yml --ask-become-pass

# Deploy a changed archive after the initial complete setup
ansible-playbook setup.yml -e @local.yml --ask-become-pass --tags app

# Update only a particular configuration
ansible-playbook setup.yml -e @local.yml --ask-become-pass --tags nginx
ansible-playbook setup.yml -e @local.yml --ask-become-pass --tags ssh
ansible-playbook setup.yml -e @local.yml --ask-become-pass --tags base
```

`ansible.cfg` supplies the inventory, so `ansible-playbook setup.yml` also works when your defaults and existing SSH/sudo access are already suitable. Use `--limit lab-server` if the inventory is later expanded.

The second immediate run should report `changed=0` when inputs and package repositories are unchanged. A later package update, expired apt cache or configuration drift can legitimately cause changes. `base_upgrade_packages: false` disables upgrades for configuration-only runs; cache refresh and installation of missing packages still occur. The playbook reports a required reboot but does not reboot the server.

Check mode (`--check --diff`) is a useful preview on an already configured server, not proof of a working deployment. On a fresh target, dependent tasks may fail because packages and directories are not actually created; archive extraction is not fully simulated. Use CI and an actual run for verification.

## Website archive

`site-src/` contains the editable HTML and CSS; `files/lab-portal.tar.gz` is the deployable artifact. On Linux, rebuild it after editing:

```bash
tar -czf files/lab-portal.tar.gz -C site-src index.html styles.css
python tests/check_archive.py
```

Upload the **binary tar.gz file** using GitHub's Upload files, not by pasting its bytes into an editor. The archive must contain `index.html` and `styles.css` at its root. Use trusted project archives only; unarchive runs with elevated privileges. If supplying another archive, review its contents before deployment and adapt the archive validation test.

Releases are named after the archive SHA-256. Extraction finishes and a nonempty index is checked before `current` is switched. Older release directories are retained, not automatically deleted. Redeploy an earlier archive to roll back. This is a simple lab deployment, not a guaranteed atomic multi-file release or a complete drift/security auditing system. Nginx need not reload when static content changes.

The included page is a static description of the existing two-VM lab, not a live dashboard. Deploying it to a fresh server does not configure the DHCP/DNS/NAT services it describes.

## Verify from the lab client

```bash
curl -fsS http://192.168.50.1:8080/ -o /dev/null
curl -fsS http://192.168.50.1:8080/healthz -o /dev/null
ssh julia@192.168.50.1
```

Open `http://192.168.50.1:8080/` in a browser that can reach the lab network. `/healthz` checks that Nginx can serve the index; it does not validate other lab services. Windows may not directly reach a VirtualBox internal network.

## CI and validation status

GitHub Actions installs Ansible on a disposable Ubuntu 24.04 runner, checks the archive and playbook syntax, applies all roles locally, verifies HTTP/services/key installation, then requires zero changes on a second run. OS upgrades are disabled in CI to avoid modifying the runner's full package baseline. The temporary CI key is generated at runtime and never committed.

CI uses a local connection; it does not prove SSH connectivity or access from your actual client. Initial delivery: archive contents inspected; no successful Ansible run, CI result or VM deployment has been confirmed. Update this section with actual results after running the workflow and testing the target.

## Upload to GitHub

Create `ansible-server-setup`, extract the ZIP and upload its contents at the repository root. Preserve folder paths, including `.github/workflows/ansible.yml`. Do not nest everything inside an extra directory. Add the workflow last if creating files individually. Keep `local.yml`, private keys and the virtual environment out of Git.

The optional Git-based deployment stretch goal is not implemented here. The required tarball deployment is the initial scope.

## References

- [Ansible apt module](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/apt_module.html)
- [Ansible unarchive module](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/unarchive_module.html)
- [Ansible authorized_key module](https://docs.ansible.com/ansible/latest/collections/ansible/posix/authorized_key_module.html)
