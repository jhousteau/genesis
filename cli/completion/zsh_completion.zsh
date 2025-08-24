#compdef g genesis
# Genesis CLI Zsh Completion
# Auto-completion for Genesis CLI with Zsh enhancements
#
# Installation:
#   Add to your fpath and autoload, or place in site-functions directory
#
# Features:
#   - Contextual completion with descriptions
#   - Dynamic completion for GCP resources
#   - Intelligent suggestion based on current context

_genesis_cli() {
    local context state line
    typeset -A opt_args

    # Main command structure
    _arguments -C \
        '(-h --help)'{-h,--help}'[Show help message]' \
        '(-v --verbose)'{-v,--verbose}'[Enable verbose logging]' \
        '(--environment -e)'{--environment,-e}'[Environment]:environment:(dev development staging production prod test)' \
        '(--project-id -p)'{--project-id,-p}'[GCP project ID]:project-id:' \
        '--config[Configuration file path]:config file:_files -g "*.yaml"' \
        '--dry-run[Show what would be done without executing]' \
        '(--output -o)'{--output,-o}'[Output format]:format:(json yaml table text list tree)' \
        '1: :->commands' \
        '*: :->args'

    case $state in
        commands)
            _values 'Genesis CLI commands' \
                'vm[VM management commands]' \
                'container[Container orchestration commands]' \
                'infra[Infrastructure management commands]' \
                'agent[Agent management commands]' \
                'help[Show help for topics]'
            ;;
        args)
            case $words[2] in
                vm)
                    _genesis_vm_commands
                    ;;
                container)
                    _genesis_container_commands
                    ;;
                infra)
                    _genesis_infra_commands
                    ;;
                agent)
                    _genesis_agent_commands
                    ;;
                help)
                    _values 'Help topics' \
                        'quickstart[Quick start guide]' \
                        'troubleshooting[Common issues and solutions]' \
                        'vm[VM management help]' \
                        'container[Container orchestration help]' \
                        'infra[Infrastructure management help]' \
                        'agent[Agent management help]'
                    ;;
            esac
            ;;
    esac
}

_genesis_vm_commands() {
    local context state line
    typeset -A opt_args

    _arguments -C \
        '1: :->vm_subcommands' \
        '*: :->vm_args'

    case $state in
        vm_subcommands)
            _values 'VM management commands' \
                'create-pool[Create agent VM pool]' \
                'scale-pool[Scale agent VM pool]' \
                'health-check[Check VM health status]' \
                'list-pools[List all VM pools]' \
                'list-instances[List all VM instances]' \
                'start[Start VM instances]' \
                'stop[Stop VM instances]' \
                'restart[Restart VM instances]' \
                'list-templates[List VM templates]' \
                'update-template[Update VM template]'
            ;;
        vm_args)
            case $words[3] in
                create-pool)
                    _arguments \
                        '--type[Agent type]:type:(backend-developer frontend-developer platform-engineer data-engineer qa-automation sre security devops architect project-manager tech-lead integration)' \
                        '--size[Initial pool size]:size:' \
                        '--machine-type[VM machine type]:machine-type:(e2-micro e2-small e2-medium e2-standard-2 e2-standard-4 e2-standard-8 n2-standard-2 n2-standard-4)' \
                        '--preemptible[Use preemptible instances]' \
                        '--zones[Deployment zones]:zones:(us-central1-a us-central1-b us-central1-c us-east1-a us-east1-b)'
                    ;;
                scale-pool)
                    _arguments \
                        '1:pool_name:' \
                        '--size[Target pool size]:size:' \
                        '--min[Minimum pool size]:min:' \
                        '--max[Maximum pool size]:max:' \
                        '--enable-autoscaling[Enable autoscaling]'
                    ;;
                health-check)
                    _arguments \
                        '--pool[Specific pool to check]:pool:' \
                        '--instance[Specific instance to check]:instance:'
                    ;;
            esac
            ;;
    esac
}

_genesis_container_commands() {
    local context state line
    typeset -A opt_args

    _arguments -C \
        '1: :->container_subcommands' \
        '*: :->container_args'

    case $state in
        container_subcommands)
            _values 'Container orchestration commands' \
                'create-cluster[Create GKE cluster]' \
                'list-clusters[List GKE clusters]' \
                'delete-cluster[Delete GKE cluster]' \
                'deploy[Deploy container service]' \
                'scale[Scale container deployment]' \
                'list-deployments[List deployments]' \
                'list-services[List services]' \
                'list-pods[List pods]' \
                'logs[View container logs]' \
                'registry[Container registry operations]'
            ;;
        container_args)
            case $words[3] in
                create-cluster)
                    _arguments \
                        '1:cluster_name:' \
                        '--autopilot[Use Autopilot mode]' \
                        '--region[Cluster region]:region:(us-central1 us-east1 us-west1 us-west2 europe-west1)' \
                        '--node-pools[Node pool configurations]:node-pools:'
                    ;;
                deploy)
                    _arguments \
                        '--service[Service name]:service:(agent-cage claude-talk)' \
                        '--version[Service version]:version:' \
                        '--replicas[Number of replicas]:replicas:' \
                        '--namespace[Kubernetes namespace]:namespace:'
                    ;;
                scale)
                    _arguments \
                        '--deployment[Deployment name]:deployment:' \
                        '--replicas[Target replicas]:replicas:' \
                        '--namespace[Kubernetes namespace]:namespace:'
                    ;;
                logs)
                    _arguments \
                        '--service[Service name]:service:(agent-cage claude-talk)' \
                        '--pod[Pod name]:pod:' \
                        '(-f --follow)'{-f,--follow}'[Follow logs]' \
                        '--lines[Number of lines to show]:lines:'
                    ;;
            esac
            ;;
    esac
}

_genesis_infra_commands() {
    local context state line
    typeset -A opt_args

    _arguments -C \
        '1: :->infra_subcommands' \
        '*: :->infra_args'

    case $state in
        infra_subcommands)
            _values 'Infrastructure management commands' \
                'plan[Plan infrastructure changes]' \
                'apply[Apply infrastructure changes]' \
                'destroy[Destroy infrastructure]' \
                'status[Show infrastructure status]' \
                'validate[Validate Terraform configuration]' \
                'init[Initialize Terraform]' \
                'cost[Infrastructure cost analysis]'
            ;;
        infra_args)
            case $words[3] in
                plan|apply|destroy)
                    _arguments \
                        '--module[Specific module]:module:(bootstrap vm-management container-orchestration networking security state-backend service-accounts workload-identity)' \
                        '--target[Specific resource to target]:target:' \
                        '--auto-approve[Auto-approve changes]'
                    ;;
                cost)
                    _values 'Cost commands' \
                        'estimate[Estimate costs]' \
                        'analyze[Analyze current costs]' \
                        'optimize[Get cost optimization suggestions]'
                    ;;
            esac
            ;;
    esac
}

_genesis_agent_commands() {
    local context state line
    typeset -A opt_args

    _arguments -C \
        '1: :->agent_subcommands' \
        '*: :->agent_args'

    case $state in
        agent_subcommands)
            _values 'Agent management commands' \
                'start[Start agents]' \
                'stop[Stop agents]' \
                'status[Show agent status]' \
                'list[List all agents]' \
                'migrate[Migrate agents between systems]' \
                'cage[Agent-cage management]' \
                'claude-talk[Claude-talk MCP server management]'
            ;;
        agent_args)
            case $words[3] in
                start)
                    _arguments \
                        '--type[Agent type]:type:(backend-developer frontend-developer platform-engineer data-engineer qa-automation sre security devops architect project-manager tech-lead integration)' \
                        '--count[Number of agents]:count:' \
                        '--environment[Agent environment]:environment:(dev staging prod)'
                    ;;
                stop)
                    _arguments \
                        '--type[Agent type]:type:(backend-developer frontend-developer platform-engineer data-engineer qa-automation sre)' \
                        '--id[Specific agent ID]:id:' \
                        '--all[Stop all agents]'
                    ;;
                migrate)
                    _arguments \
                        '--from[Source system]:from:(legacy vm-based)' \
                        '--to[Target system]:to:(agent-cage container-based)' \
                        '--agent-types[Specific agent types]:agent-types:(backend-developer frontend-developer platform-engineer)' \
                        '--batch-size[Migration batch size]:batch-size:'
                    ;;
                cage|claude-talk)
                    _values 'Service management commands' \
                        'status[Show service status]' \
                        'restart[Restart service]' \
                        'logs[View service logs]' \
                        'sessions[List active sessions]'
                    ;;
            esac
            ;;
    esac
}

# Register the completion function
_genesis_cli "$@"
