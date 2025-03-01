"""
Class useful for git stuff including publishing a git page for sharing CUPiD.
"""
from __future__ import annotations

import os
import re
import subprocess
from urllib.parse import quote


class GitHelper:
    def __init__(self, publish_dir, version_name, publish_url=None):
        """
        Initializes an instance for managing the publishing of a Git repository.

        This constructor:
        1. Sets the version name and publish directory.
        2. Checks if the publish directory is clean (no uncommitted changes).
        3. Determines the publish URL if not provided.
        4. Constructs the final published URL, ensuring proper encoding.

        Args:
            publish_dir (str): The directory where the repository is located.
            version_name (str): The version identifier for the publication.
            publish_url (str, optional): The base publish URL. If not provided, it is derived from the repository.

        Attributes:
            version_name (str): The version being published.
            publish_dir (str): The directory containing the repository.
            publish_url (str): The base URL where the version will be published.
            published_to_url (str): The full URL of the published version, with special characters encoded.

        Raises:
            RuntimeError: If the publish directory is not clean.
        """
        self.version_name = version_name
        self.publish_dir = os.path.realpath(publish_dir)
        self.check_pub_dir_clean()

        if publish_url is None:
            publish_url = self.get_publish_url()
        self.publish_url = publish_url

        # Get URL to print, handling spaces and special characters
        self.published_to_url = "/".join(
            [self.publish_url, "versions", self.version_name],
        )
        self.published_to_url = quote(self.published_to_url)
        self.published_to_url = re.sub("http(s?)%3A", r"http\1:", self.published_to_url)

    def check_pub_dir_clean(self):
        """
        Checks if the Git working directory in the publish directory is clean.
        If the working tree is not clean, it raises a `RuntimeError`.
        """
        status = self.run_git_cmd(f"git -C {self.publish_dir} status")
        if status[-1] != "nothing to commit, working tree clean":
            raise RuntimeError(f"self.publish_dir not clean: {self.publish_dir}")

    def commit(self, modified_files, new_files):
        """
        Stages, commits, and pushes changes in the Git repository within the publish directory.

        This function:
        1. Checks the repository status.
        2. If there are changes to commit, it:
            - Stages all modified and new files.
            - Commits the changes with a message including the version name.
            - Pushes the commit to the remote repository.
        3. If no changes are detected, it prints a message indicating there is nothing to commit.

        Args:
            modified_files (list[str]): List of modified files to be committed.
            new_files (list[str]): List of newly added files to be committed.

        Prints:
            - Staging, committing, and pushing progress updates.
            - The publish URL if changes are successfully pushed.
        """
        status = self.run_git_cmd(f"git -C {self.publish_dir} status")
        if status[-1] != "nothing to commit, working tree clean":
            # Stage
            print("Staging...")
            git_cmd = (
                f"git -C {self.publish_dir} add {os.path.join(self.publish_dir, '*')}"
            )
            status = self.run_git_cmd(git_cmd)

            # Commit
            print("Committing...")
            git_cmd = [
                "git",
                "-C",
                self.publish_dir,
                "commit",
                "-m",
                f"Add version '{self.version_name}'",
            ]
            status = self.run_git_cmd(git_cmd)

            # Push
            print("Pushing...")
            git_cmd = f"git -C {self.publish_dir} push"
            status = self.run_git_cmd(git_cmd)

            print("Done! Published to " + self.published_to_url)
            print("It might take a bit for GitHub.io to generate that URL")
        else:
            print("Nothing to commit")

    def get_publish_url(self):
        """
        Retrieves the publish URL for the Git repository based on its remote origin URL.

        The function determines the repository's remote URL and root directory, then constructs
        the appropriate GitHub Pages URL if the repository is hosted on GitHub. If the repository
        is not hosted on GitHub, a `NotImplementedError` is raised.

        Returns:
            str: The constructed publish URL for the repository.

        Raises:
            NotImplementedError: If the remote URL format is not recognized.
        """
        cmd = "git config --get remote.origin.url"
        publish_repo_url = self.run_git_cmd(cmd, cwd=self.publish_dir)[0]

        cmd = "git rev-parse --show-toplevel"
        publish_dir_repo_top = self.run_git_cmd(cmd, cwd=self.publish_dir)[0]
        subdirs = str(os.path.realpath(self.publish_dir)).replace(
            publish_dir_repo_top,
            "",
        )

        if "git@github.com:" in publish_repo_url:
            gh_user = re.compile(r"git@github.com:(\w+)").findall(publish_repo_url)[0]
            repo_name = re.compile(r"/(.+).git").findall(publish_repo_url)[0]
            publish_url = f"https://{gh_user}.github.io/{repo_name}" + subdirs
        elif "https://github.com/" in publish_repo_url:
            gh_user = re.compile(r"https://github.com/(\w+)").findall(publish_repo_url)
            gh_user = gh_user[0]
            repo_name = re.compile(r"https://github.com/\w+/(\w+)").findall(
                publish_repo_url,
            )[0]
            publish_url = f"https://{gh_user}.github.io/{repo_name}" + subdirs
        else:
            raise NotImplementedError(
                f"Not sure how to handle publish_repo_url {publish_repo_url}.",
            )

        return publish_url

    def publish(self):
        """
        Identifies modified and untracked files in the Git repository within the publish directory
        and commits the changes.

        The function runs `git status` to determine modified and new (untracked) files.
        It then prints the files being updated or added and commits them using `self.commit()`.

        Raises:
            Exception: If any error occurs while executing the Git command.

        """
        status = self.run_git_cmd(f"git -C {self.publish_dir} status")
        modified_files = []
        new_files = []
        in_untracked_files = False
        for line in status:
            if not in_untracked_files:
                if re.compile("^\tmodified:").match(line):
                    modified_files.append(line.split(" ")[-1])
                elif line == "Untracked files:":
                    in_untracked_files = True
            else:
                if line == "":
                    break
                if (
                    line
                    != '  (use "git add <file>..." to include in what will be committed)'
                ):
                    new_files.append(line.replace("\t", ""))
        if modified_files:
            print("Updating files:\n   " + "\n   ".join(modified_files))
        if new_files:
            print("Adding files:\n   " + "\n   ".join(new_files))

        self.commit(modified_files, new_files)

    def run_git_cmd(self, git_cmd, cwd=os.getcwd()):
        """
        Executes a Git command in the specified working directory and returns the output as a list of lines.

        Args:
            git_cmd (str or list): The Git command to execute. Can be a string or a list of command components.
            cwd (str, optional): The directory where command should be executed. Defaults to current working directory.

        Returns:
            list: A list of strings representing the output lines of the command.

        Raises:
            subprocess.CalledProcessError: If the Git command fails, prints the command, working directory, and
                error message before raising the exception.
            Exception: If any other error occurs during execution.
        """
        if not isinstance(git_cmd, list):
            git_cmd = git_cmd.split(" ")
        try:
            git_result = subprocess.check_output(
                git_cmd,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=cwd,
            ).splitlines()
        except subprocess.CalledProcessError as e:
            print("Command: " + " ".join(e.cmd))
            print("Working directory: " + cwd)
            print("Message: ", e.stdout)
            raise e
        except Exception as e:
            raise e
        return git_result
