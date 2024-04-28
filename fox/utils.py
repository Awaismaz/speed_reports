import pandas as pd
import numpy as np
import time
from django.shortcuts import render
from django.http import JsonResponse
from io import StringIO
# from weasyprint import HTML
from django.http import HttpResponse


def format_hour(x):
    slot = "AM"
    if x // 12 == 1:
        slot = "PM"
    hour = x % 12
    if hour == 0:
        hour = 12
    formatted_time = f"{hour} {slot}"
    return formatted_time

def speed_report(direction_filter, lane_filter, filtered_data, request=None):
    speed_by_hour = pd.pivot_table(
        filtered_data,
        values="header",
        index=["hour"],
        columns=["Speed Bins"],
        aggfunc="count",
        fill_value=0,
        margins=True,
        margins_name="Grand Total",
    )
    time_dict = {}
    for i in range(24):
        time_dict[i + 1] = format_hour(i)

    speed_by_hour = speed_by_hour.rename(index=time_dict)
    speed_by_hour.index.name = 'Hour'
    speed_by_hour.columns.name = 'Speed Bins (km/h)'


    return generate_reports(
        speed_by_hour, "SPEED", direction_filter, lane_filter,filtered_data=filtered_data,request=request
    )

def get_violations(enforcement_limit, filtered_data):
    lanes = filtered_data["lane"].unique()
    lanes.sort()

    # Calculate combined violation percentage
    violations_count_combined = filtered_data[filtered_data["speed"] >= enforcement_limit].shape[
        0
    ]
    total_vehicles_combined = filtered_data.shape[0]
    combined_percentage = (
        (violations_count_combined / total_vehicles_combined) * 100
        if total_vehicles_combined > 0
        else 0
    )
    combined_percentage = round(combined_percentage)
    # Calculate lane-wise violation percentages
    lane_violations = {}
    for lane in lanes:
        lane_data = filtered_data[filtered_data["lane"] == lane]
        violations_count = lane_data[lane_data["speed"] >= enforcement_limit].shape[0]
        total_vehicles = lane_data.shape[0]
        lane_percentage = (
            (violations_count / total_vehicles) * 100 if total_vehicles > 0 else 0
        )
        lane_violations[lane] = round(lane_percentage)

    # Return combined and lane-wise percentages
    return {"combined": combined_percentage, "lane_wise": lane_violations}

def get_speed_bins(selected_percentile, filtered_data):
    speed_bins_tables = {}

    # Calculate 85th percentile for combined data
    percentile_speed_combined = np.percentile(
        filtered_data["speed"].dropna(), selected_percentile
    )
    speed_bins_combined = pd.pivot_table(
        filtered_data, values="header", columns=["Speed Bins"], aggfunc="count", fill_value=0
    )
    speed_bins_combined = speed_bins_combined.rename(index={"header": "Vehicles"})
    speed_bins_tables["combined"] = [speed_bins_combined, percentile_speed_combined]

    lanes = filtered_data["lane"].unique()
    lanes.sort()

    for lane in lanes:
        # Filter the DataFrame for the current lane
        lane_df = filtered_data[filtered_data["lane"] == lane]

        # Calculate 85th percentile for the current lane
        percentile_speed_lane = np.percentile(
            lane_df["speed"].dropna(), selected_percentile
        )

        # Create the pivot table for the current lane
        speed_bins_lane = pd.pivot_table(
            lane_df,
            values="header",
            columns=["Speed Bins"],
            aggfunc="count",
            fill_value=0,
        )
        speed_bins_lane = speed_bins_lane.rename(index={"header": "Vehicles"})

        # Store the table and percentile speed in the dictionary
        speed_bins_tables[lane] = [speed_bins_lane, percentile_speed_lane]

    return speed_bins_tables

def percentile_report(direction_filter, lane_filter, filtered_data, request=None):
    # Define the percentiles you want to calculate
    percentiles = list(range(5, 96, 10))

    def calculate_hourly_percentiles(group):
        return pd.Series(
            np.percentile(group["speed"].dropna(), percentiles),
            index=[f"{p}th" for p in percentiles],
        )

    hourly_percentiles = filtered_data.groupby("hour").apply(calculate_hourly_percentiles)

    overall_percentiles = np.percentile(filtered_data["speed"].dropna(), percentiles)

    hourly_percentiles.loc["Overall"] = overall_percentiles

    violations = pd.Series(index=[f"{p}th" for p in percentiles], dtype=int)

    for p in percentiles:
        percentile_speed = np.percentile(filtered_data["speed"].dropna(), p)
        violations[f"{p}th"] = (filtered_data["speed"] > percentile_speed).sum()

    hourly_percentiles.loc["Violations"] = violations

    hourly_percentiles = hourly_percentiles.round().astype(int)

    time_dict = {i + 1: format_hour(i) for i in range(24)}
    time_dict["Overall"] = "Overall"
    time_dict["Violations"] = "Violations"
    hourly_percentiles = hourly_percentiles.rename(index=time_dict)

    return generate_reports(
        hourly_percentiles,
        "PERCENTILES",
        direction_filter,
        lane_filter,
        filtered_data=filtered_data,
        request=request
    )

def speed_by_class_report(direction_filter, lane_filter, filtered_data, request=None):
    speed_by_class = pd.pivot_table(
        filtered_data,
        values="header",
        index="Speed Bins",
        columns="length_bin",
        aggfunc="count",
        fill_value=0,
        margins=True,
        margins_name="Grand Total",
    )

    return generate_reports(
        speed_by_class,
        "SPEED BY CLASSIFICATION",
        direction_filter,
        lane_filter,
        advance=True,
        filtered_data=filtered_data,
        request=request
    )

def class_report(direction_filter, lane_filter, filtered_data, request=None):
    class_by_hour = pd.pivot_table(
        filtered_data,
        values="header",
        index=["hour"],
        columns=["length_bin"],
        aggfunc="count",
        fill_value=0,
        margins=True,
        margins_name="Grand Total",
    )

    time_dict = {}
    for i in range(24):
        time_dict[i + 1] = format_hour(i)

    class_by_hour = class_by_hour.rename(index=time_dict)
    return generate_reports(
        class_by_hour, "CLASS", direction_filter, lane_filter, filtered_data=filtered_data, request=request
    )

def volume_report(direction_filter, lane_filter, filtered_data, request=None):
    volume_by_hour = pd.pivot_table(
        filtered_data,
        values="header",
        index=["month", "Day with Weekday"],
        columns=["hour"],
        aggfunc="count",
        fill_value=0,
    )

    month_dict = {
        1: "Jan",
        2: "Feb",
        3: "Mar",
        4: "Apr",
        5: "May",
        6: "Jun",
        7: "Jul",
        8: "Aug",
        9: "Sep",
        10: "Oct",
        11: "Nov",
        12: "Dec",
    }
    concatenated = pd.concat(
        [
            pd.concat(
                [
                    y,
                    pd.DataFrame(y.sum())
                    .transpose()
                    .rename(index={0: (x, f"{month_dict[x]} Total")}),
                ]
            )
            for x, y in volume_by_hour.groupby("month")
        ]
    )

    volume_by_hour = pd.concat(
        [
            concatenated,
            pd.DataFrame(volume_by_hour.sum())
            .transpose()
            .rename(index={0: ("Grand", "Total")}),
        ]
    )
    volume_by_hour = volume_by_hour.rename(index=month_dict, level=0)

    time_dict = {}
    for i in range(24):
        time_dict[i + 1] = format_hour(i)
    volume_by_hour = volume_by_hour.rename(columns=time_dict)

    return generate_reports(
        volume_by_hour, "VOLUME", direction_filter, lane_filter, filtered_data=filtered_data, request=request
    )

def generate_reports(data, category, direction_filter, lane_filter, advance=False,filtered_data=None, request=None):

    table_html = data.to_html()

    ADT = pd.pivot_table(
        filtered_data,
        values="header",
        index=["date"],
        aggfunc="count",
        fill_value=0,
    )["header"].mean()
    Factor = 1.011167
    AADT = ADT * Factor

    company_header = request.POST.get('companyHeader')
    report_location = request.POST.get('locationInput')
    site_code = request.POST.get('siteCodeInput')
    report_description = request.POST.get('reportDescription')
    export_format = request.POST.get('exportFormat')
    show_aadt = request.POST.get('showAADT') == 'on'
    start_date_str   =   request.session['start_date']
    end_date_str    =  request.session['end_date']
    speed_limit = '110'

    timestr = time.strftime("%Y%m%d-%H%M%S")
    # location = request.POST.get('locationInput')
    site = request.POST.get('siteCodeInput')

    # report_description = request.POST.get('reportDescription')
    export_format = request.POST.get('exportFormat')

    file_name = site + f"_{category}_" + timestr

    context = {
        'direction_filter': direction_filter,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'lane_filter': lane_filter,
        'my_table': table_html,
        'category': category,
        'advance': advance,
        'site_code': site_code,
        'report_description': report_description,
        'report_location': report_location,
        'company_header': company_header,
        'ADT': ADT,
        'Factor': Factor,
        'AADT': AADT,
        'show_aadt': show_aadt,
        'speed_limit': speed_limit,
        'file_name':file_name,
    }

    html_content = render(request, 'fox/template.html', context).content.decode('utf-8')
        
    if request.session['preview']:
        return JsonResponse({'html_content': html_content})


    else:
        if export_format == 'csv':
            import csv
            # Prepare CSV response
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{file_name}.csv"'
            
            # Create a CSV writer
            writer = csv.writer(response)
            
            # Write metadata before the table
            writer.writerow(['Company Header:', context['company_header']])
            writer.writerow(['Location:', context['report_location']])
            writer.writerow(['Site Code:', context['site_code']])
            writer.writerow(['Report Description:', context['report_description']])
            writer.writerow([])
            writer.writerow(['Category:', context['category']])
            writer.writerow(['Direction Filter:', context['direction_filter']])
            writer.writerow(['Lane Filter:', context['lane_filter']])
            writer.writerow(['Start Date:', context['start_date']])
            writer.writerow(['End Date:', context['end_date']])
            writer.writerow(['Speed Limit:', context['speed_limit']])
            writer.writerow([])
            
            # Write DataFrame to CSV
            data.to_csv(path_or_buf=response, index=True, mode='a')
            
            # Write metadata after the table
            writer.writerow([])
            writer.writerow(['ADT:', context['ADT']])
            writer.writerow(['Factor:', context['Factor']])
            writer.writerow(['AADT:', context['AADT']])

        elif export_format == 'excel':
            from openpyxl import Workbook


            # Prepare Excel response
            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename="{file_name}.xlsx"'

            # Create a workbook and select the active worksheet
            workbook = Workbook()
            worksheet = workbook.active
            worksheet.title = 'Complete Report'

            # Writing metadata before the table
            metadata = [
                ['Company Header:', context['company_header']],
                ['Location:', context['report_location']],
                ['Site Code:', context['site_code']],
                ['Report Description:', context['report_description']],
                ['', ''],
                ['Category:', context['category']],
                ['Direction Filter:', context['direction_filter']],
                # ['Lane Filter:', context['lane_filter']],
                ['Start Date:', context['start_date']],
                ['End Date:', context['end_date']],
                ['Speed Limit:', context['speed_limit']],
                ['', '']
            ]
            
            for row in metadata:
                worksheet.append(row)

            # Calculate the starting row for actual data
            data_start_row = len(metadata) + 1
            
            from openpyxl.utils.dataframe import dataframe_to_rows

            # Convert DataFrame to Excel
            for r in dataframe_to_rows(data, index=True, header=True):
                worksheet.append(r)

            # Append additional metadata after the data
            additional_metadata = [
                ['', ''],
                ['ADT:', context['ADT']],
                ['Factor:', context['Factor']],
                ['AADT:', context['AADT']]
            ]
            
            for row in additional_metadata:
                worksheet.append(row)

            # Save workbook to response
            workbook.save(response)

        return response


def get_selected_time_ranges(request):
    time_ranges = []

    # Check if High Risk time periods are provided and checked
    for i in range(1, 4):
        highRisk = request.POST.get(f'highRisk{i}', None)
        startKey = f'highRisk{i}Start'
        endKey = f'highRisk{i}End'
        
        if highRisk:
            start = request.POST.get(startKey, '')
            end = request.POST.get(endKey, '')
            if start and end:  # Ensure both start and end times are provided
                time_ranges.append((f"High Risk {i}", start, end))

    return time_ranges

def apply_date_filter(request, f_data):
    dateSelection = request.POST.get('dateSelection')
    
    if dateSelection == 'range':
        start_date = request.POST.get('startDate', '')
        end_date = request.POST.get('endDate', '')
        mask = (f_data["date"] >= np.datetime64(start_date)) & (f_data["date"] <= np.datetime64(end_date))

    elif dateSelection == 'specific':
        specific_date = request.POST.get('specificDate', '')
        mask = f_data["date"] == np.datetime64(specific_date)

    filtered_data = f_data.loc[mask].copy()
    return filtered_data

def school_zone_study(request, f_data, direction_filter, lane_filter):
    date_filtered = apply_date_filter(request, f_data)
    time_ranges = get_selected_time_ranges(request)
    filtered_data = []

    for label, start_time, end_time in time_ranges:
        # Convert string times to pandas datetime.time objects for comparison
        start_time = pd.to_datetime(start_time).time()
        end_time = pd.to_datetime(end_time).time()

        # Assuming 'time' column is of type datetime.time
        mask = (date_filtered["time"] >= start_time) & (date_filtered["time"] <= end_time)
        temp_data = date_filtered.loc[mask].copy()
        temp_data["Time Bracket"] = label
        filtered_data.append(temp_data)

    combined_data = pd.concat(filtered_data, ignore_index=True) if filtered_data else pd.DataFrame()
    # Assuming get_violations() and other necessary functions are adapted for web context
    violations = get_violations(float(request.POST.get('postedSpeedLimit','20')), combined_data)

    # Create a multi-level pivot table
    pivot = pd.pivot_table(
        combined_data,
        values="header",
        index=["Time Bracket", "time_bin"],
        columns=["Speed Bins"],
        aggfunc="count",
        fill_value=0,
        margins=True,
        margins_name="Grand Total",
    )

    # Drop rows where all values across columns are zero
    pivot.replace(0, np.nan, inplace=True)
    pivot.dropna(how="all", inplace=True)
    pivot.fillna(0, inplace=True)
    pivot = pivot.astype(int)

    category = "SCHOOL ZONE STUDY"

    timestr = time.strftime("%Y%m%d-%H%M%S")
    site = ''
    file_name = site + f"_{category}_" + timestr

    table = pivot.to_html()
    # Load the template

    start_date = request.POST.get('startDate')
    end_date = request.POST.get('endDate')
    date_selection = request.POST.get('dateSelection')
    specific_date = request.POST.get('specificDate')
    speed_limit = request.POST.get('postedSpeedLimit')
    report_location = request.POST.get('locationInput')
    company_header = request.POST.get('companyHeader')
    site_code = request.POST.get('siteCodeInput')
    report_description = request.POST.get('reportDescription')


    if date_selection == 'specific':
        start_date = specific_date
        end_date = specific_date


    context = {
        'direction_filter': direction_filter,
        'start_date': start_date,
        'end_date': end_date,
        'lane_filter': lane_filter,  # Ensure lane_filter is defined based on your form/needs
        'my_table': table,
        'category': "SCHOOL ZONE STUDY",
        'advance': True,
        'site_code': site_code,
        'report_description': report_description,
        'report_location': report_location,
        'company_header': company_header,
        'speed_limit': speed_limit,
        'total_violations': violations["combined"],  # Ensure this matches your violations data structure
        'file_name': file_name,
    }

    html_content = render(request, 'fox/template.html', context).content.decode('utf-8')
       
    return JsonResponse({'html_content': html_content})