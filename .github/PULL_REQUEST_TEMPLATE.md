### Description of changes:
* [ ] Please add an explanation of what your changes do and why you'd like us to include them.

#### All PRs Checklist (if these do not apply, feel free to remove this section):
* [ ] Have you followed the guidelines in our [Contributor's Guide](https://ncar.github.io/CUPiD/ContributorGuide.html)?
* [ ] Have you checked to ensure there aren't other open [Pull Requests](../../../pulls) for the same update/change?
* [ ] Have you made sure that the [`pre-commit` checks passed (#8 in Adding Notebooks Guide)](https://ncar.github.io/CUPiD/addingnotebookstocollection.html)?
* [ ] Have you successfully tested your changes locally?

#### New notebook PR Additional Checklist:
* [ ] Have you [hidden the code cells (#8 in Adding Notebooks Guide)](https://ncar.github.io/CUPiD/addingnotebookstocollection.html) in your notebook?
* [ ] Have you removed any unused parameters from your cell tagged with `parameters`? These can cause confusing warnings that show up as `DAG build with warnings`.
* [ ] Have you moved any observational data that you are using to `/glade/campaign/cesm/development/cross-wg/diagnostic_framework/CUPiD_obs_data` and ensured that it follows this format within that directory: `COMPONENT/analysis_datasets/RESOLUTION/PROCESSED_FIELD_TYPE`?
