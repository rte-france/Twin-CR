path "secret/data/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/*" {
  capabilities = ["read", "list"]
}

path "pki/issue/*" {
  capabilities = ["create", "update"]
}
