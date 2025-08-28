output "service_account_emails" {
  description = "Map of service account names to their email addresses"
  value = {
    for sa_name, sa in google_service_account.service_accounts :
    sa_name => sa.email
  }
}

output "service_account_ids" {
  description = "Map of service account names to their unique IDs"
  value = {
    for sa_name, sa in google_service_account.service_accounts :
    sa_name => sa.unique_id
  }
}

output "service_account_keys" {
  description = "Map of service account names to their private keys (if created)"
  value = {
    for sa_name, key in google_service_account_key.keys :
    sa_name => key.private_key
  }
  sensitive = true
}
