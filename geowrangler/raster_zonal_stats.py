# AUTOGENERATED! DO NOT EDIT! File to edit: ../notebooks/03_raster_zonal_stats.ipynb.

# %% auto 0
__all__ = ['create_raster_zonal_stats', 'create_exactextract_zonal_stats']

# %% ../notebooks/03_raster_zonal_stats.ipynb 8
from pathlib import Path
from typing import Any, Dict, Union, List
import warnings
import json

import geopandas as gpd
import pandas as pd
import rasterio
import rasterstats as rs
from exactextract import exact_extract
from exactextract.raster import RasterioRasterSource

from .vector_zonal_stats import _expand_aggs, _fillnas, _fix_agg

# %% ../notebooks/03_raster_zonal_stats.ipynb 9
def create_raster_zonal_stats(
    aoi: Union[  # The area of interest geodataframe, or path to the vector file
        str, gpd.GeoDataFrame
    ],
    data: Union[str, Path],  # The path to the raster data file
    aggregation: Dict[  # A dict specifying the aggregation. See `create_zonal_stats` from the `geowrangler.vector_zonal_stats` module for more details
        str, Any
    ],
    extra_args: Dict[  # Extra arguments passed to `rasterstats.zonal_stats` method
        str, Any
    ] = dict(
        layer=0,
        band_num=1,
        nodata=None,
        affine=None,
        all_touched=False,
    ),
) -> gpd.GeoDataFrame:
    """Compute zonal stats with a vector areas of interest (aoi) from raster data sources.
    This is a thin layer  over the `zonal_stats` method from
    the `rasterstats` python package for compatibility with other geowrangler modules.
    This method currently only supports 1 band for each call, so if you want to create zonal
    stats for multiple bands with the same raster data, you can call this method for
    each band (make sure to specify the correct `band_num` in the `extra_args` parameter).
    See https://pythonhosted.org/rasterstats/manual.html#zonal-statistics for more details
    """
    fixed_agg = _fix_agg(aggregation)

    if "stats" in extra_args:
        extra_args.pop("stats")  # use aggregation

    if "geojson_out" in extra_args:
        extra_args.pop("geojson_out")  # never add features

    if "categorical" in extra_args:
        extra_args.pop("categorical")  # no use for categorical and categorical maps
    if "categorical_map" in extra_args:
        extra_args.pop("categorical_map")

    if "prefix" in extra_args:
        extra_args.pop("prefix")  # use agg['column'] as prefix

    if "add_stats" in extra_args:
        extra_args.pop("add_stats")  # always use stats only

    if "nodata" in extra_args:
        nodata = extra_args["nodata"]
        if nodata is None:
            extra_args.pop("nodata")
            with rasterio.open(data) as src:
                extra_args["nodata"] = src.nodata

    stats = fixed_agg["func"]
    prefix = fixed_agg["column"] + "_"

    renamed_columns = {
        f"{prefix}{func}": fixed_agg["output"][i]
        for (i, func) in enumerate(fixed_agg["func"])
        if f"{prefix}{func}" != fixed_agg["output"][i]
    }
    results_dict = rs.zonal_stats(
        vectors=aoi,
        raster=data,
        stats=stats,
        geojson_out=False,
        categorical=False,
        category_map=None,
        prefix=prefix,
        **extra_args,
    )

    results = pd.DataFrame.from_records(results_dict)
    results.rename(columns=renamed_columns, inplace=True)
    expanded_aggs = _expand_aggs([fixed_agg])

    if type(aoi) == str:
        aoi = gpd.read_file(aoi)

    _fillnas(expanded_aggs, results, aoi)

    aoi = aoi.merge(results, how="left", left_index=True, right_index=True)

    return aoi

# %% ../notebooks/03_raster_zonal_stats.ipynb 30
def _validate_aggs(aggregations, band_count):
    "Validate aggregations based on band count, dropping invalid entries"
    aggregations_validated = []

    # Iterate over the list of dictionaries
    for agg in aggregations:
        # Check if the 'band' value is less than or equal to band_count
        if agg["band"] > band_count:
            warnings.warn(
                f"Band number in {json.dumps(agg)}  is invalid. Aggregation will be skipped."
            )
            continue
        aggregations_validated.append(agg)

    return aggregations_validated

# %% ../notebooks/03_raster_zonal_stats.ipynb 31
def create_exactextract_zonal_stats(
    aoi: Union[
        str, gpd.GeoDataFrame
    ],  # The area of interest geodataframe, or path to the vector file
    data: Union[str, Path],  # The path to the raster data file
    aggregations: List[Dict[str, Any]],  # List of agg specs
    extra_args: dict = dict(
        strategy="feature-sequential", max_cells_in_memory=30000000
    ),
) -> gpd.GeoDataFrame:
    """
    Computes zonal statistics from raster data sources using vector areas of interest (AOI).

    This function is a wrapper over the `exact_extract` method from the `exactextract` Python package,
    designed for compatibility with other geowrangler modules. It takes a list of agg specs,
    with each agg spec applied to a specific band.
    See https://github.com/isciences/exactextract/blob/master/python/README.md for more details.

    Parameters
    ----------
    aoi : GeoDataframe
        A GeoDataframe specifying geometries.
    data : str
        Path to the raster file.
    aggregations: list[Dict]: list of aggregation specs, which are dictionaries which specify the ff.

        - band (int): band number of the input raster to aggregate
        - func (list[str]): list of operations to perform (i.e. "mean", "median", "count"). For a full list of
        possible exactextract functions, see: https://github.com/isciences/exactextract/tree/master?tab=readme-ov-file#supported-statistics
        - output (str or list[str], option): output columns for operation.
            If None (default), the output column name will be given as band_<band number>_<func> for all functions.
            If str, the output column name will be given as <output>_<func> for all functions.
            If list(str), the list items will be used as the column names, in order of the passed funcs.
        - nodata_val (int or float, optional): nodata value to use in calculation.

    extra_args : dict


    Example usage
    --------
    create_exactextract_zonal_stats(
        aoi=aoi_gdf,
        data="path/to/raster.tif",
        aggregations=[
            dict(band=1, func=["mean", "sum"], nodata_val=-9999) # default - band_1_mean, band_1_sum
            dict(band=1, func=["mean", "sum"], output=["pop_mean", "pop_sum"]),
            dict(band=2, func=["mean", "sum"]) # default - band_2_mean, band_2_sum
            dict(band=2, func=["mean", "sum"], output="prefix") # prefix_mean, prefix_sum
        ],
    )
    """
    # TODO: figure out NODATA handling

    # Handle extra arguments, issuing warnings for non-default behavior.
    if "weights" in extra_args:
        warnings.warn(
            "Input weights raster will be used for all passed aggregations. To use different weights for each aggregation, call `get_exactextract_zonal_stats` multiple times."
        )

    # If output, include_cols, or include_geom, return the raw exactextract results instead
    # These values conflict with the intended postprocessing steps (renaming/filtering, joining to input gdf)
    RETURN_RAW_RESULTS = False
    if "output" not in extra_args:
        extra_args["output"] = "pandas"
    else:
        if extra_args["output"] != "pandas":
            RETURN_RAW_RESULTS = True
        if extra_args["output"] == "gdal":  # requires osgeo (heavy dependency)
            raise ValueError(
                "extra_args['output'] is set to 'gdal', which is currently unsupported. Please choose a different option."
            )

    if "include_cols" in extra_args:
        RETURN_RAW_RESULTS = True

    if "include_geom" in extra_args:
        RETURN_RAW_RESULTS = True

    if RETURN_RAW_RESULTS:
        warnings.warn(
            "Defaulting to raw exactextract output using arguments in output, include_cols, and/or include_geom. Column names: band_<band number>_<func>."
        )

    if isinstance(aoi, str) or isinstance(aoi, Path):
        aoi = gpd.read_file(aoi)

    # Open raster and run exactextract
    with rasterio.open(data) as dst:
        # Validate passed aggregations based on band count and compile
        aggregations = _validate_aggs(aggregations, dst.count)
        all_operations = set()
        for agg in aggregations:
            all_operations.update(agg["func"])
        all_operations = sorted(all_operations)
        if aoi.crs != dst.crs:
            warnings.warn(
                f"The CRS of the AOI ({aoi.crs}) and the raster data ({dst.crs}) do not match!"
            )

        # If input is single band, the output is processed to band_1_<func> for all funcs
        # This is automatically done with singleband inputs
        if dst.count == 1:
            results = exact_extract(data, aoi, all_operations, **extra_args)
            if RETURN_RAW_RESULTS:
                return results
            results = results.rename(
                columns={col: f"band_1_{col}" for col in results.columns}
            )
        else:
            results = exact_extract(data, aoi, all_operations, **extra_args)
            if RETURN_RAW_RESULTS:
                return results

    # Create new columns as specified by agg specs
    # Each renamed column will be a copy of its corresponding result column
    out_cols = []
    for agg in aggregations:
        result_cols = [f"band_{agg['band']}_{func}" for func in agg["func"]]

        if "output" not in agg:
            agg_out_cols = result_cols

        elif isinstance(agg["output"], str):
            agg_out_cols = [f"{agg['output']}_{func}" for func in agg["func"]]

        elif isinstance(agg["output"], list) and all(
            isinstance(item, str) for item in agg.get("output")
        ):
            assert len(agg["output"]) == len(
                agg["func"]
            ), f"Output list only has {len(agg['output'])}, expected {len(agg['func'])}"
            agg_out_cols = agg.get("output")

        # Add output columns to result
        for agg_out_col, result_col in zip(agg_out_cols, result_cols):
            results[agg_out_col] = results[result_col]
        out_cols.extend(agg_out_cols)

    # Return only the columns specified
    output_results = results.loc[:, out_cols]
    print(list(output_results.columns.values))
    return aoi.merge(output_results, how="left", left_index=True, right_index=True)
