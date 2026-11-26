# Nomad ACL policy of the session-manager job (workload-associated): the job submits, follows and stops the sessions
namespace "default" {
  capabilities = ["parse-job", "submit-job", "read-job", "list-jobs", "read-logs"]
}
