#!/bin/bash
# Genesis CLI Bash Completion
# Auto-completion for Genesis CLI following REACT methodology
#
# Installation:
#   source this file in your .bashrc or copy to /etc/bash_completion.d/
#
# Usage:
#   g <TAB>         - Show main commands
#   g vm <TAB>      - Show VM subcommands
#   g --<TAB>       - Show global options

_genesis_completion() {
    local cur prev words cword
    _init_completion || return

    # Main commands
    local main_commands="vm container infra agent help"

    # VM subcommands
    local vm_commands="create-pool scale-pool health-check list-pools list-instances start stop restart list-templates update-template"

    # Container subcommands
    local container_commands="create-cluster list-clusters delete-cluster deploy scale list-deployments list-services list-pods logs registry"

    # Infrastructure subcommands
    local infra_commands="plan apply destroy status validate init cost"

    # Agent subcommands
    local agent_commands="start stop status list migrate cage claude-talk"

    # Global options
    local global_options="--environment --project-id --config --verbose --dry-run --output --help --version"

    # Output formats
    local output_formats="json yaml table text list tree"

    # Agent types
    local agent_types="backend-developer frontend-developer platform-engineer data-engineer qa-automation sre security devops architect project-manager tech-lead integration"

    # Environments
    local environments="dev development staging production prod test"

    # Help topics
    local help_topics="quickstart troubleshooting vm container infra agent"

    case $cword in
        1)
            # Complete main commands
            if [[ $cur == -* ]]; then
                COMPREPLY=($(compgen -W "$global_options" -- "$cur"))
            else
                COMPREPLY=($(compgen -W "$main_commands" -- "$cur"))
            fi
            ;;
        2)
            case $prev in
                vm)
                    COMPREPLY=($(compgen -W "$vm_commands" -- "$cur"))
                    ;;
                container)
                    COMPREPLY=($(compgen -W "$container_commands" -- "$cur"))
                    ;;
                infra)
                    COMPREPLY=($(compgen -W "$infra_commands" -- "$cur"))
                    ;;
                agent)
                    COMPREPLY=($(compgen -W "$agent_commands" -- "$cur"))
                    ;;
                help)
                    COMPREPLY=($(compgen -W "$help_topics" -- "$cur"))
                    ;;
                --environment|-e)
                    COMPREPLY=($(compgen -W "$environments" -- "$cur"))
                    ;;
                --output|-o)
                    COMPREPLY=($(compgen -W "$output_formats" -- "$cur"))
                    ;;
            esac
            ;;
        *)
            # Handle options and context-specific completion
            case $prev in
                --type)
                    COMPREPLY=($(compgen -W "$agent_types" -- "$cur"))
                    ;;
                --environment|-e)
                    COMPREPLY=($(compgen -W "$environments" -- "$cur"))
                    ;;
                --output|-o)
                    COMPREPLY=($(compgen -W "$output_formats" -- "$cur"))
                    ;;
                --service)
                    local services="agent-cage claude-talk"
                    COMPREPLY=($(compgen -W "$services" -- "$cur"))
                    ;;
                --module)
                    local modules="bootstrap vm-management container-orchestration networking security state-backend service-accounts workload-identity"
                    COMPREPLY=($(compgen -W "$modules" -- "$cur"))
                    ;;
                --machine-type)
                    local machine_types="e2-micro e2-small e2-medium e2-standard-2 e2-standard-4 e2-standard-8 n2-standard-2 n2-standard-4 n2-standard-8"
                    COMPREPLY=($(compgen -W "$machine_types" -- "$cur"))
                    ;;
                --region)
                    local regions="us-central1 us-east1 us-west1 us-west2 europe-west1 europe-west2 asia-east1 asia-southeast1"
                    COMPREPLY=($(compgen -W "$regions" -- "$cur"))
                    ;;
                --zones)
                    local zones="us-central1-a us-central1-b us-central1-c us-east1-a us-east1-b us-west1-a us-west1-b"
                    COMPREPLY=($(compgen -W "$zones" -- "$cur"))
                    ;;
                *)
                    # Default to global options if we don't know what to complete
                    if [[ $cur == -* ]]; then
                        COMPREPLY=($(compgen -W "$global_options" -- "$cur"))
                    fi
                    ;;
            esac
            ;;
    esac

    # Handle file/path completion for certain options
    case $prev in
        --config)
            _filedir "yaml"
            ;;
        --target)
            # Could be enhanced to complete Terraform resource names
            ;;
    esac
}

# Enable completion for 'g' command
complete -F _genesis_completion g

# Also enable for full 'genesis' command if used
complete -F _genesis_completion genesis
