import intake
import yaml

def read_yaml(path_to_yaml):
    with open(path_to_yaml) as f:
        data = yaml.load(f, Loader=yaml.FullLoader) 
    return data


def get_collection(path_to_catalog, **kwargs):
    cat = intake.open_esm_datastore(path_to_catalog)
    ### note that the json file points to the csv, so the path that the
    ### yaml file contains doesn't actually get used. this can cause issues
    
    cat_subset = cat.search(**kwargs)
        
    if "variable" in kwargs.keys():
        
        def preprocess(ds):
            ## the double brackets return a Dataset rather than a DataArray
            ## this is fragile and could cause issues, i'm not totally sure what subsetting on time_bound does
            return ds[[kwargs["variable"], 'time_bound']]
    
        ## not sure what the chunking kwarg is doing here either
        dsets = cat_subset.to_dataset_dict(xarray_open_kwargs={'chunks': {'time': -1}}, preprocess=preprocess)
    
    else:
        dsets = cat_subset.to_dataset_dict()
        
    return dsets


