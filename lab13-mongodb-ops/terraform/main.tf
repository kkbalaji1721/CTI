# Lab 13 - Terraform for a MongoDB Atlas FREE-TIER (M0) cluster
# Requires: Terraform >= 1.5 and Atlas API keys exported as
#   MONGODB_ATLAS_PUBLIC_KEY / MONGODB_ATLAS_PRIVATE_KEY
# Based on the chapter-13 reference main.tf, with fixes for M0 (see README "Terraform notes").

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    mongodbatlas = {
      source  = "mongodb/mongodbatlas"
      version = "~> 1.16"
    }
  }
}

provider "mongodbatlas" {}   # reads keys from environment variables

resource "mongodbatlas_project" "nosql_labs" {
  name   = "NoSQL Labs - Training"
  org_id = var.atlas_org_id
}

resource "mongodbatlas_cluster" "training" {
  project_id = mongodbatlas_project.nosql_labs.id
  name       = "training-cluster"

  # Free tier (M0) is a shared "TENANT" cluster that is hosted on a backing cloud provider
  provider_name               = "TENANT"
  backing_provider_name       = "AWS"
  provider_region_name        = "AP_SOUTH_1" # Mumbai - if Atlas rejects it for M0, use US_EAST_1
  provider_instance_size_name = "M0"
}

resource "mongodbatlas_database_user" "lab_user" {
  project_id         = mongodbatlas_project.nosql_labs.id
  username           = "lab_user"
  password           = var.atlas_user_password
  auth_database_name = "admin"

  roles {
    role_name     = "readWriteAnyDatabase"
    database_name = "admin"
  }
}

resource "mongodbatlas_project_ip_access_list" "allow_all" {
  project_id = mongodbatlas_project.nosql_labs.id
  cidr_block = "0.0.0.0/0"
  comment    = "Allow all IPs for training (NOT for production)"
}

output "connection_string" {
  value       = mongodbatlas_cluster.training.connection_strings[0].standard_srv
  description = "MongoDB Atlas SRV connection string (without credentials)"
}

output "cluster_uri" {
  value       = "mongodb+srv://lab_user:${var.atlas_user_password}@${replace(mongodbatlas_cluster.training.connection_strings[0].standard_srv, "mongodb+srv://", "")}/?retryWrites=true&w=majority"
  sensitive   = true
  description = "Full URI incl. password (use: terraform output -raw cluster_uri)"
}

variable "atlas_org_id" {
  description = "MongoDB Atlas Organization ID"
  type        = string
}

variable "atlas_user_password" {
  description = "Password for the lab database user"
  type        = string
  sensitive   = true
}
