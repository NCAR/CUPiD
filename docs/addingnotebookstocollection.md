# How to add diagnostics notebooks

Generally, a good fit for a diagnostic notebook is one that reads in CESM output, does some processing, and outputs plots, values, and/or new files (images, data, etc.) that are useful for evaluating the run.

1. Install the `environments/cupid-analysis.yml` environment (see [installation instructions](https://ncar.github.io/CUPiD/index.html#installing)). Make sure that your notebook runs properly in this environment. If there are conflicts or missing dependencies, open an issue or talk to CUPiD developers so we can find a solution.
2. In your notebook, move all variables you might want to change (paths to data, dates to select, etc.) to a cell near the top. For example:

            sname = "run_name"
            data_path = "path/to/data"
            dates = {"start_date" = "01/01/01",
                                    "end_date" = "01/01/02"}

4. Tag this cell as `parameters`. This means that when the notebook is executed by `CUPiD`, a new cell will be inserted just below this one with all of the parameters specified in `config.yml` (see step 5). To tag it, in Jupyter Lab, click on the cell and click the button with two gears in the top right ("Property Inspector"). Open "Common Tools." There, you can see a section called "Cell Tags." Click "Add Tag," and add one called `parameters` (exactly as written). **If you don't want to fully set up CUPiD, stop here and we can integrate the notebook into a CUPiD workflow from here.**
---
**If you want to run your notebook through the `CUPiD` workflow yourself, follow the rest of the instructions:**

4. Move your new diagnostic notebook to the folder called `examples/nblibrary`.

5. Open `config.yml`. First, add your new notebook (as its name, minus the `.ipynb`) to the list of notebooks that will be computed (`compute_notebooks`). The notebooks will be executed in the order they are listed here. For example:

                your_new_nb_name:
                        parameter_groups:
                                none:
                                        param_specific_to_this_nb: some_value
                                        another_param: another_value
   
        If you just want the notebook run once on one set of parameters, keep the `parameter_groups: none:` notation as above. If you want the notebook executed multiple times with different parameter sets, the notation would look like this:

                your_new_nb_name:
                        parameter_groups:
                                group_1:
                                        param_1: some_string
                                        param_2: {key1: dict_entry1, key2: dict_entry2}
                                group_2:
                                        param_1: some_different_string
                                        param_2: {key1: dict_entry3, key2: dict_entry4}


6. If you'd like your new notebook included in the final Jupyter Book, add it to the Jupyter Book table of contents (`book_toc`). See [Jupyter Book's documentation](https://jupyterbook.org/en/stable/structure/toc.html) for different things you can do with this.

7. Update your parameters. Parameters that are specific to just this notebook should go under `parameter_groups` in the notebook's entry under `compute_notebooks`. Global parameters that you want passed in to every notebook in the collection should go under `global_params`.  When `CUPiD` executes your notebook, all of these parameters will get put in a new cell below the cell tagged `parameters` that you added in step 3. This means they will supercede the values of the parameters that you put in the cell above---the names, notation, etc. should match to make sure your notebook is able to find the variables it needs.
   
8. All set! Your collection can now be run and built with `cupid-run config.yml` and `cupid-build config.yml` as usual.
