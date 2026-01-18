#!/usr/bin/env python3
from __future__ import annotations

import datetime

import cftime
import click

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--start-date",
    default="0001-01-01",
    help="Starting date, format is YYYY-MM-DD.",
)
@click.option(
    "--stop-option",
    default="nyears",
    type=click.Choice(["ndays", "nminutes", "nyears", "nmonths", "nseconds", "nhours"]),
    help="Unit to increment date by.",
)
@click.option(
    "--stop-n",
    default="1",
    help="Number of units (see --stop-option) to increment date by.",
)
@click.option(
    "--calendar",
    type=click.Choice(
        [
            "standard",
            "gregorian",
            "proleptic_gregorian",
            "noleap",
            "julian",
            "all_leap",
            "365_day",
            "366_day",
            "360_day",
        ],
    ),
    help="Accepts valid calendars in cftime 1.6.4.",
)
def find_enddate(start_date, stop_option, stop_n, calendar):
    """Calculate an end_date for a given cftime compliant calendar given a
    start_date and amount to increment forward by. Resolves edge cases
    where start_date.day is not a valid date in end_date.month (including
    leap day discrepancies) by rounding down (e.g. 03-31 -> 1 month -> 04-30).

    Args:
        start_date (str): starting date in YYYY-MM-DD format.
        stop_option (str): {'ndays', 'nminutes', 'nyears', 'nmonths', 'nseconds', 'nhours'} \
            Unit to increment date by.
        stop_n (int): Number of units (see stop_option) to increment date by.
        calendar (str): {'standard', 'gregorian', 'proleptic_gregorian', 'noleap', \
            'julian', 'all_leap', '365_day', '366_day', '360_day'}. \
            Must be a Valid cftime calendar.

    Returns:
        cftime.datetime: end_date given the parameters.
    """
    # Process inputs
    try:
        year, month, day = (int(i) for i in start_date.split("-"))
    except ValueError:
        raise ValueError("start_date must be in format YYYY-MM-DD.")

    try:
        stop_n = int(stop_n)
    except ValueError:
        raise ValueError("stop_n must be an integer.")

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
    elif stop_option in ["ndays", "nminutes", "nseconds", "nhours"]:
        option = stop_option[1:]  # strip n from beginning for timedelta args
        kwargs = {option: stop_n}
        time_delta = datetime.timedelta(**kwargs)
        end_date = end_date + time_delta
    else:
        raise ValueError(
            "stop_option must be one of ['ndays', 'nminutes', 'nyears', 'nmonths', 'nseconds', 'nhours'].",
        )

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
    end_date = find_enddate(standalone_mode=False)

    # Calling with -h/--help flag returns an int.
    # Allows for help message to be called without error.
    if isinstance(end_date, cftime.datetime):
        print(end_date.strftime("%Y-%m-%d"))
