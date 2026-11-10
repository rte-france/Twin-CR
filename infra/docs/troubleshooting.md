## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `ansible.legacy.setup` fails: `/usr/bin/python3 not found` | Fresh OrbStack Debian image ships without Python 3 | `orb -m twineu-dev sudo apt update && orb -m twineu-dev sudo apt install -y python3` |
| `Save Vault credentials on host` fails: `builtin_function_or_method object has no element 0` | Jinja resolves `.keys` as the dict method, not the JSON key `keys` | Already fixed in `roles/hashicorp/tasks/main.yml` (uses `vault_init_resp.json['keys'][0]`) |
| `Vault is sealed` on any `vault secrets enable/write` task | A previous run failed **after** Vault init but **before** `vault.creds` was written to disk. The unseal key is unrecoverable once lost. | Dev only — wipe and reinit: `sudo systemctl stop vault && sudo rm -rf /opt/vault/data/* /etc/vault.d/vault.creds && sudo systemctl start vault`, then re-run `make dev-mac` |
| Keycloak: `--optimized flag was used for first ever server start` | Official Keycloak image isn't pre-built; `--optimized` requires a `kc.sh build` step first | Drop `--optimized` from the `start` args (already fixed in `roles/keycloak/templates/keycloak.nomad.hcl.j2`) |
| Keycloak: `Key material not provided to setup HTTPS` | Keycloak refuses plain HTTP by default; TLS is terminated upstream by Traefik | Set `KC_HTTP_ENABLED="true"` + `KC_PROXY_HEADERS="xforwarded"` (already set) |
| Keycloak: `ISPN000540: No such JGroups stack 'dns-ping'` | `dns-ping` isn't a built-in JGroups stack in Keycloak 26 | Use `KC_CACHE_STACK="tcp"` (already set) — needed only if `count > 1` |
| Keycloak admin login fails with `user_not_found` even though the deploy succeeded | The realm was imported via a separate `kc.sh import` prestart task, which ran DB migrations *before* the main `kc.sh start` boot — Keycloak no longer considered the DB "fresh" and silently skipped creating the `KC_BOOTSTRAP_ADMIN_*` user | Fixed: realm import now happens inline via `kc.sh start --import-realm` in the same boot (see `roles/keycloak/templates/keycloak.nomad.hcl.j2`). If you still hit this on old data, wipe `/opt/twineu/postgres/data` and redeploy for a truly fresh bootstrap |
| `dnsmasq` job fails: `driver does not allow the following capabilities: net_admin` | Nomad's Docker driver whitelists allowed Linux capabilities by default; `NET_ADMIN` isn't in it, and dnsmasq doesn't need it just to answer DNS queries | Removed `cap_add = ["NET_ADMIN"]` from `roles/hashicorp/templates/dnsmasq.nomad.j2` |

---
