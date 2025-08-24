"""
Shell Completion Module
Provides auto-completion support for various shells.
"""

import os
import subprocess
from pathlib import Path
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class ShellCompletion:
    """
    Shell completion manager following REACT methodology.

    R - Responsive: Adapts to different shell environments
    E - Efficient: Fast completion lookup with caching
    A - Accessible: Clear completion descriptions and help
    C - Connected: Integrates with Genesis command structure
    T - Tested: Reliable completion across shell types
    """

    def __init__(self):
        self.completion_dir = Path(__file__).parent
        self.shell_type = self._detect_shell()

    def _detect_shell(self) -> Optional[str]:
        """Detect the current shell type."""
        shell = os.getenv("SHELL", "").lower()

        if "bash" in shell:
            return "bash"
        elif "zsh" in shell:
            return "zsh"
        elif "fish" in shell:
            return "fish"
        else:
            return None

    def install_completion(self, shell: Optional[str] = None) -> bool:
        """Install shell completion for the detected or specified shell."""
        target_shell = shell or self.shell_type

        if not target_shell:
            logger.warning("Could not detect shell type for completion installation")
            return False

        try:
            if target_shell == "bash":
                return self._install_bash_completion()
            elif target_shell == "zsh":
                return self._install_zsh_completion()
            elif target_shell == "fish":
                return self._install_fish_completion()
            else:
                logger.warning(f"Shell completion not supported for: {target_shell}")
                return False
        except Exception as e:
            logger.error(f"Failed to install {target_shell} completion: {e}")
            return False

    def _install_bash_completion(self) -> bool:
        """Install Bash completion."""
        completion_file = self.completion_dir / "bash_completion.sh"

        if not completion_file.exists():
            logger.error("Bash completion file not found")
            return False

        # Try system-wide installation first
        system_completion_dir = Path("/etc/bash_completion.d")
        if system_completion_dir.exists() and os.access(system_completion_dir, os.W_OK):
            target_file = system_completion_dir / "genesis"
            try:
                import shutil

                shutil.copy2(completion_file, target_file)
                logger.info(f"Installed Bash completion to {target_file}")
                return True
            except PermissionError:
                pass

        # Fall back to user installation
        user_completion_dir = Path.home() / ".local/share/bash-completion/completions"
        user_completion_dir.mkdir(parents=True, exist_ok=True)

        target_file = user_completion_dir / "genesis"
        try:
            import shutil

            shutil.copy2(completion_file, target_file)
            logger.info(f"Installed Bash completion to {target_file}")

            # Add to .bashrc if not already present
            bashrc = Path.home() / ".bashrc"
            if bashrc.exists():
                with open(bashrc, "r") as f:
                    bashrc_content = f.read()

                completion_line = f"source {target_file}"
                if completion_line not in bashrc_content:
                    with open(bashrc, "a") as f:
                        f.write(f"\n# Genesis CLI completion\n{completion_line}\n")
                    logger.info("Added completion source to .bashrc")

            return True
        except Exception as e:
            logger.error(f"Failed to install Bash completion: {e}")
            return False

    def _install_zsh_completion(self) -> bool:
        """Install Zsh completion."""
        completion_file = self.completion_dir / "zsh_completion.zsh"

        if not completion_file.exists():
            logger.error("Zsh completion file not found")
            return False

        # Find Zsh completion directory
        try:
            result = subprocess.run(
                ["zsh", "-c", "echo $fpath[1]"],
                capture_output=True,
                text=True,
                check=True,
            )
            fpath_dir = Path(result.stdout.strip())
        except subprocess.CalledProcessError:
            # Fall back to common Zsh completion directory
            fpath_dir = Path.home() / ".zsh/completions"
            fpath_dir.mkdir(parents=True, exist_ok=True)

        target_file = fpath_dir / "_genesis"
        try:
            import shutil

            shutil.copy2(completion_file, target_file)
            logger.info(f"Installed Zsh completion to {target_file}")

            # Add fpath to .zshrc if using custom directory
            if not str(fpath_dir).startswith("/usr"):
                zshrc = Path.home() / ".zshrc"
                if zshrc.exists():
                    with open(zshrc, "r") as f:
                        zshrc_content = f.read()

                    fpath_line = f"fpath=({fpath_dir} $fpath)"
                    if str(fpath_dir) not in zshrc_content:
                        with open(zshrc, "a") as f:
                            f.write(
                                f"\n# Genesis CLI completion\n{fpath_line}\nautoload -Uz compinit && compinit\n"
                            )
                        logger.info("Added fpath and compinit to .zshrc")

            return True
        except Exception as e:
            logger.error(f"Failed to install Zsh completion: {e}")
            return False

    def _install_fish_completion(self) -> bool:
        """Install Fish completion (placeholder for future implementation)."""
        logger.info("Fish completion not yet implemented")
        return False

    def generate_completion_script(self, shell: str) -> Optional[str]:
        """Generate completion script content for specified shell."""
        completion_files = {"bash": "bash_completion.sh", "zsh": "zsh_completion.zsh"}

        completion_file = completion_files.get(shell)
        if not completion_file:
            return None

        file_path = self.completion_dir / completion_file
        if not file_path.exists():
            return None

        try:
            with open(file_path, "r") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read completion file: {e}")
            return None

    def get_command_suggestions(
        self, current_input: str, context: List[str]
    ) -> List[str]:
        """Get command suggestions for dynamic completion."""
        suggestions = []

        # Main commands
        main_commands = ["vm", "container", "infra", "agent", "help"]

        if not context or len(context) == 0:
            # Complete main commands
            suggestions.extend(
                [cmd for cmd in main_commands if cmd.startswith(current_input)]
            )
        elif len(context) == 1:
            # Complete subcommands
            main_cmd = context[0]
            if main_cmd == "vm":
                vm_commands = [
                    "create-pool",
                    "scale-pool",
                    "health-check",
                    "list-pools",
                    "list-instances",
                ]
                suggestions.extend(
                    [cmd for cmd in vm_commands if cmd.startswith(current_input)]
                )
            elif main_cmd == "container":
                container_commands = [
                    "create-cluster",
                    "deploy",
                    "scale",
                    "logs",
                    "list-deployments",
                ]
                suggestions.extend(
                    [cmd for cmd in container_commands if cmd.startswith(current_input)]
                )
            elif main_cmd == "infra":
                infra_commands = ["plan", "apply", "destroy", "status", "validate"]
                suggestions.extend(
                    [cmd for cmd in infra_commands if cmd.startswith(current_input)]
                )
            elif main_cmd == "agent":
                agent_commands = [
                    "start",
                    "stop",
                    "status",
                    "migrate",
                    "cage",
                    "claude-talk",
                ]
                suggestions.extend(
                    [cmd for cmd in agent_commands if cmd.startswith(current_input)]
                )
            elif main_cmd == "help":
                help_topics = [
                    "quickstart",
                    "troubleshooting",
                    "vm",
                    "container",
                    "infra",
                    "agent",
                ]
                suggestions.extend(
                    [topic for topic in help_topics if topic.startswith(current_input)]
                )

        return suggestions

    def show_installation_instructions(self) -> str:
        """Show installation instructions for shell completion."""
        shell = self.shell_type or "your shell"

        instructions = f"""
Genesis CLI Shell Completion Installation

DETECTED SHELL: {shell}

AUTOMATIC INSTALLATION:
  Run this command to install completion automatically:
  g completion install

MANUAL INSTALLATION:

For Bash:
  1. Copy the completion file to your completion directory:
     cp cli/completion/bash_completion.sh ~/.local/share/bash-completion/completions/genesis

  2. Add to your .bashrc:
     echo 'source ~/.local/share/bash-completion/completions/genesis' >> ~/.bashrc

  3. Reload your shell:
     source ~/.bashrc

For Zsh:
  1. Create completions directory if it doesn't exist:
     mkdir -p ~/.zsh/completions

  2. Copy the completion file:
     cp cli/completion/zsh_completion.zsh ~/.zsh/completions/_genesis

  3. Add to your .zshrc:
     echo 'fpath=(~/.zsh/completions $fpath)' >> ~/.zshrc
     echo 'autoload -Uz compinit && compinit' >> ~/.zshrc

  4. Reload your shell:
     source ~/.zshrc

VERIFICATION:
  After installation, test completion with:
  g <TAB>          # Should show main commands
  g vm <TAB>       # Should show VM subcommands
  g --<TAB>        # Should show global options

TROUBLESHOOTING:
  If completion doesn't work:
  1. Verify the completion file is in the right location
  2. Check that your shell sources the completion
  3. Try restarting your terminal session
  4. Run: g help troubleshooting
        """

        return instructions.strip()
