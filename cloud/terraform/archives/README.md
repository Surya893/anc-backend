# Legacy Terraform Configurations (Archived)

This directory contains deprecated Terraform configurations that have been superseded by the environment-based structure in the parent directory.

## Files

- **main_v2.tf**: Comprehensive v2.0 configuration with enhanced features (superseded)
- **main_working.tf**: Simplified working configuration with core modules (superseded)

## Why Archived?

These files were merged and rationalized into:
- `environments/dev/main.tf` - Development environment
- `environments/prod/main.tf` - Production environment

The new structure provides:
- ✅ Clear environment separation (dev vs prod)
- ✅ Consistent variable naming across environments
- ✅ Unified Terraform state management per environment
- ✅ Shared module configuration
- ✅ Centralized documentation

## Migration Guide

If you have existing infrastructure deployed with these configs:

1. Back up your current state:
   ```bash
   terraform state pull > backup.tfstate
   ```

2. Migrate to new environment configuration:
   ```bash
   cd environments/dev/  # or environments/prod/
   terraform init
   terraform plan
   terraform apply
   ```

3. Verify new infrastructure matches old deployment

4. Archive old state files after verification

## Reference

For complete Terraform setup, see:
- [../README.md](../README.md) - Terraform deployment guide
- [../environments/dev/main.tf](../environments/dev/main.tf) - Dev environment
- [../environments/prod/main.tf](../environments/prod/main.tf) - Prod environment
