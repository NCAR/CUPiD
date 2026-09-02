#!/usr/bin/env python3
from __future__ import annotations

import datetime
import sys

import cftime
import click

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--start-dates",
    default="0001-01-01",
    help="Starting date or list of starting dates, format is YYYY-MM-DD.",
)
@click.option(
    "--stop-option",
    default="nyears",
    type=click.Choice(["ndays", "nminutes", "nyears", "nmonths", "nseconds", "nhours"]),
    help="Unit to increment date by.",
)
@click.option(
    "--stop-ns",
    default="1",
    help="Number or list of numbers of units (see --stop-option) to increment date by.",
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
@click.option(
    "--cases",
    default=None,
    help="List of case names, can be used to determine desired size of start_dates and stop_ns",
)
def find_enddates(start_dates, stop_option, stop_ns, calendar, cases):
    """Calculate an end_date for a given cftime compliant calendar given a
    start_date and amount to increment forward by. Resolves edge cases
    where start_date.day is not a valid date in end_date.month (including
    leap day discrepancies) by rounding down (e.g. 03-31 -> 1 month -> 04-30).

    Args:
        start_dates (str): comma-separated list of starting dates in YYYY-MM-DD format.
        stop_option (str): {'ndays', 'nminutes', 'nyears', 'nmonths', 'nseconds', 'nhours'} \
            Unit to increment date by.
        stop_ns (int): comma-separated list of number of units (see stop_option) to increment date by.
                      Must be length of start_dates or length 1 (=> same stop_n for each start_date)
        calendar (str): {'standard', 'gregorian', 'proleptic_gregorian', 'noleap', \
            'julian', 'all_leap', '365_day', '366_day', '360_day'}. \
            Must be a Valid cftime calendar.

    Returns:
        cftime.datetime: comma-separated list of end_dates given the parameters.
    """
    # Turn off traceback when raising an exception
    sys.tracebacklimit = 0

    # Process inputs
    if not isinstance(start_dates, list):
        start_dates = start_dates.split(",")
    if cases:
        if not isinstance(cases, list):
            cases = cases.split(",")
        num_cases = len(cases)
        if len(start_dates) == 1:
            start_dates = num_cases * start_dates
        if len(start_dates) != num_cases:
            raise ValueError(
                f"start_dates is length {len(start_dates)}, not {num_cases}",
            )
    if not isinstance(stop_ns, list):
        stop_ns = stop_ns.split(",")
    if len(start_dates) != len(stop_ns) and len(stop_ns) != 1:
        raise ValueError(
            f"start_dates is len {len(start_dates)} and stop_ns is length {len(stop_ns)}; "
            + "these need to match (or stop_ns must be length 1)",
        )
    if len(stop_ns) == 1:
        stop_ns = len(start_dates) * [stop_ns[0]]
    end_dates = []
    for start_date, stop_n in zip(start_dates, stop_ns):
        end_dates.append(find_enddate(start_date, stop_option, stop_n, calendar))
    return end_dates


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
    end_dates = find_enddates(standalone_mode=False)

    # Calling with -h/--help flag returns an int.
    # Allows for help message to be called without error.
    for n, end_date in enumerate(end_dates):
        if isinstance(end_date, cftime.datetime):
            if n < len(end_dates) - 1:
                print(f'{end_date.strftime("%Y-%m-%d")},', end="")
            else:
                print(end_date.strftime("%Y-%m-%d"))
