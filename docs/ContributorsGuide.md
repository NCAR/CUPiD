# Welcome to the CUPiD Contributor's Guide!

Now that your repository is set up, if you would like to add a diagnostics notebook, you can follow the [guide to adding diagnostics notebooks](https://ncar.github.io/CUPiD/addingnotebookstocollection.html).

In order to contribute code to this repository, we recommend that you get started with these steps:

0. [Open an issue](https://github.com/NCAR/CUPiD/issues) prior to development
1. Set up git and make an account if needed.
2. Create your personal fork of the repository by going to the [CUPiD repository](https://github.com/NCAR/CUPiD) and clicking the `Fork` button. Clone your personal repository by going to your forked repository, clicking the green `Code` button, and then, in your terminal, run `git clone --recurse-submodules https://github.com/<YOUR GIT USERNAME>/CUPiD`
3. Check out a new branch with a name that is relevant to the changes you want to make: `git checkout -b <BRANCH NAME>`
4. [Install CUPiD](https://ncar.github.io/CUPiD/index.html#installing), relevant environments, and setup `pre-commit`.
5. Make your edits and add your name to our `contributors.md` file to make sure we recognize your contributions
6. Merge in recent changes from master
7. Ensure that `pre-commit` checks all pass from the `cupid-dev` environment
8. IF updating `github.io` pages, test with the steps listed below, otherwise proceed to #9:
    - Create the environment necessary for building documentation with `$ conda env create -f environments/docs.yml`
    - Activate the docs environment: `$ conda activate cupid-docs`
    - Change into the `docs` directory: `$ cd docs`
    - Build the documentation: `$ make html`
    - View the documentation to make sure it rendered correctly: `$ open _build/html/index.html`
9. Submit a Pull Request
10. Await review
11. Update PR with any requested changes
12. Repository admins will merge the PR
