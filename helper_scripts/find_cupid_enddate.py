#!/usr/bin/env python3
from __future__ import annotations

import datetime

import cftime
import click

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--start-date",
    required=True,
    help="Starting date, format is YYYY-MM-DD.",
)
@click.option(
    "--stop_option",
    required=True,
    help="Unit to increment date by.",
)
@click.option(
    "--stop_n",
    required=True,
    help="Number of units (option) to increment date by.",
)
@click.option(
    "--calendar",
    required=True,
    help="Calendar type. See cftime calendar types for additional information.",
)
def find_enddate(start_date, stop_n, stop_option, calendar):
    # Process inputs
    year, month, day = (int(i) for i in start_date.split("-"))
    calendar_map = {"GREGORIAN": "proleptic_gregorian", "NO_LEAP": "noleap"}
    calendar = calendar_map[calendar]
    stop_n = int(stop_n)

    start_date = cftime.datetime(year, month, day, calendar=calendar)
    end_date = start_date

    # Make modifications
    if stop_option == "nyears":
        end_day = start_date.day
        end_month = start_date.month
        end_year = start_date.year + stop_n
    elif stop_option == "nmonths":
        end_day = start_date.day
        end_month = start_date.month + stop_n % 12
        end_year = start_date.year + stop_n // 12
    elif stop_option == "ndays":
        time_delta = datetime.timedelta(days=stop_n)
        end_date = end_date + time_delta

    # If stop_option is nyears or nmonths, need to handle edge cases where
    # start_date.day is not a valid date in end_date.month (e.g. running
    # for one month from March 31st). In these cases, we stop at the end of
    # the computed end_month (April 30th in the example above).
    if stop_option in ["nyears", "nmonths"]:
        try:
            end_date = cftime.datetime(
                end_year,
                end_month,
                end_day,
                calendar=calendar,
            )
        except ValueError:
            end_day = cftime.datetime(end_year, end_month, 1).daysinmonth
            end_date = cftime.datetime(
                end_year,
                end_month,
                end_day,
                calendar=calendar,
            )

    return end_date


if __name__ == "__main__":
    # standalone_mode=False lets the sript print the result to stdout
    # (Note that find_enddate() returns a cftime.datetime object if
    # imported directly in a python script.)
    print(find_enddate(standalone_mode=False).strftime("%Y-%m-%d"))
