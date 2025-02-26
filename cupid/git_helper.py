"""
Class useful for git stuff
"""
from __future__ import annotations

import os
import re
import subprocess


def run_git_cmd(git_cmd, cwd=os.getcwd()):
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


class GitHelper:
    def __init__(self, publish_dir, version_name, publish_url=None):
        self.version_name = version_name
        self.publish_dir = publish_dir
        self.check_pub_dir_clean()

        if publish_url is None:
            publish_url = self.get_publish_url()
        self.publish_url = publish_url
        self.published_to_url = "/".join(
            [self.publish_url, "versions", self.version_name],
        )

    def check_pub_dir_clean(self):
        status = run_git_cmd(f"git -C {self.publish_dir} status")
        if status[-1] != "nothing to commit, working tree clean":
            raise RuntimeError(f"self.publish_dir not clean: {self.publish_dir}")

    def commit(self, modified_files, new_files):
        status = run_git_cmd(f"git -C {self.publish_dir} status")
        if status[-1] != "nothing to commit, working tree clean":
            # Stage
            print("Staging...")
            git_cmd = (
                f"git -C {self.publish_dir} add {os.path.join(self.publish_dir, '*')}"
            )
            status = run_git_cmd(git_cmd)

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
            status = run_git_cmd(git_cmd)

            # Push
            print("Pushing...")
            git_cmd = f"git -C {self.publish_dir} push"
            status = run_git_cmd(git_cmd)

            print("Done! Published to " + self.published_to_url)
            print("It might take a bit for GitHub.io to generate that URL")
        else:
            print("Nothing to commit")

    def get_publish_url(self):
        cmd = "git config --get remote.origin.url"
        publish_repo_url = run_git_cmd(cmd, cwd=self.publish_dir)[0]

        cmd = "git rev-parse --show-toplevel"
        publish_dir_repo_top = run_git_cmd(cmd, cwd=self.publish_dir)[0]
        subdirs = str(os.path.realpath(self.publish_dir)).replace(
            publish_dir_repo_top,
            "",
        )

        if "git@github.com:" in publish_repo_url:
            gh_user = re.compile(r"git@github.com:(\w+)").findall(publish_repo_url)[0]
            repo_name = re.compile(r"/(.+).git").findall(publish_repo_url)[0]
            publish_url = f"https://{gh_user}.github.io/{repo_name}" + subdirs
        else:
            raise NotImplementedError(
                " ".join(
                    [
                        f"Not sure how to handle publish_repo_url {publish_repo_url}.",
                        "Provide PUBLISH_URL in options.py.",
                    ],
                ),
            )

        return publish_url

    def publish(self):

        status = run_git_cmd(f"git -C {self.publish_dir} status")
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
