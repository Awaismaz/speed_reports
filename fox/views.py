from django.shortcuts import render
from django.http import HttpResponse
import pandas as pd
import numpy as np
import datetime
import locale
from io import StringIO
from .utils import *
locale.setlocale(locale.LC_ALL, "")
from django.contrib.auth.decorators import login_required
# views.py
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


def time_to_bin(s):
    hour = s.split(":")[0]
    return hour


def format_hour(x):
    slot = "AM"
    if x // 12 == 1:
        slot = "PM"
    hour = x % 12
    if hour == 0:
        hour = 12
    formatted_time = f"{hour} {slot}"
    return formatted_time


def speed_to_bin(df, bins=17):
    max_speed = df["speed"].max()
    bin_width = max_speed / bins
    speed_bins = np.arange(0, max_speed, bin_width).tolist()
    speed_bins.append(400)
    labels = [
        f"{int(speed_bins[x])}-{int(speed_bins[x+1])}"
        for x in range(len(speed_bins) - 1)
    ]

    labels[-1] = f"{int(speed_bins[-2])}-{int(np.ceil(max_speed))}"

    return pd.cut(df["speed"], bins=speed_bins, labels=labels)

      

def length_to_bin(df):
    length_bins = [0, 2, 3, 5, 6, 8, 9, 12, 15, 18, 21, 24, 26]
    labels = [
        f"{length_bins[x]}-{length_bins[x+1]} m" for x in range(len(length_bins) - 1)
    ]
    length_bins.append(400)
    labels.append("26+ m")
    return pd.cut(df["length"], bins=length_bins, labels=labels)


def check_weekday(x):
    y = x.split("/")
    d = datetime.date(int(y[2]), int(y[1]), int(y[0]))
    return d.weekday()


def day_with_weekday(x):
    y = x.split("/")
    d = datetime.date(int(y[2]), int(y[1]), int(y[0]))
    day_dict = {
        0: "M",
        1: "T",
        2: "W",
        3: "T",
        4: "F",
        5: "S",
        6: "S",
    }
    return f"{y[0]} {day_dict[d.weekday()]}"


def lane_number(x):
    x = str(x)
    if not x.isdigit():
        my_dict = {
            "A": "10",
            "B": "11",
            "C": "12",
            "D": "13",
            "E": "14",
            "F": "15",
            "G": "16",
        }
        return my_dict[x]
    return x


def load_data(file, product=0):
    # w.report_type.clear()

    print(product)

    if product == 0:
        df = pd.read_csv(
            file,
            names=[
                "header",
                "date",
                "time",
                "lane",
                "direction",
                "length",
                "speed",
                "epoch",
            ],
        )
        df["day"] = df["date"].apply(lambda x: int(x.split("/")[0]))
        df["month"] = df["date"].apply(lambda x: int(x.split("/")[1]))
        df["year"] = df["date"].apply(lambda x: int(x.split("/")[2]))
        df["weekday"] = df["date"].apply(lambda x: check_weekday(x))
        df["Day with Weekday"] = df["date"].apply(lambda x: day_with_weekday(x))
        df["hour"] = df["time"].apply(lambda x: int(time_to_bin(x)) + 1)
        df["time_bin"] = df["hour"].apply(lambda x: format_hour(x - 1))
        df["lane"] = df["lane"].apply(lambda x: lane_number(x))
        df["Speed Bins"] = speed_to_bin(df)
        df["length_bin"] = length_to_bin(df)
        df["date"] = pd.to_datetime(df["date"], dayfirst=True)
        df["time"] = pd.to_datetime(df["time"], format="%H:%M:%S.%f").dt.time


    else:
        df = pd.read_csv(file)
        df.columns = ["date", "time", "direction", "speed", "a_count", "r_count"]
        df = df.dropna(how="all")
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%d/%m/%Y")
        # df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d').dt.strftime('%d/%m/%Y')
        df["time"] = df["time"].str.strip()
        df["hour"] = df["time"].apply(lambda x: int(time_to_bin(x)) + 1)
        df["time"] = pd.to_datetime(df["time"], format="%H:%M:%S").dt.time
        df["month"] = df["date"].apply(lambda x: int(x.split("/")[1]))
        df["year"] = df["date"].apply(lambda x: int(x.split("/")[2]))
        df["weekday"] = df["date"].apply(lambda x: check_weekday(x))
        df["Day with Weekday"] = df["date"].apply(lambda x: day_with_weekday(x))
        df["time_bin"] = df["hour"].apply(lambda x: format_hour(x - 1))
        df["direction"] = df["direction"].str.strip()
        df["Speed Bins"] = speed_to_bin(df)
        df["a_count"] = pd.to_numeric(df["a_count"], errors="coerce").fillna(0)
        df["r_count"] = pd.to_numeric(df["r_count"], errors="coerce").fillna(0)
        df["date"] = pd.to_datetime(df["date"], dayfirst=True)
        df["lane"] = df["direction"].map({"A": "1", "R": "2"})
        df["header"] = "DS"
        
        # w.report_type.addItems(["Speed", "Volume", "Percentile"])

    print(df.head())
    return df


@login_required
def index(request):
    user = request.user
    context = {'lanes': range(1,17),
               'export_formats': [
                    {'id': 'pdfFormat', 'value': 'pdf', 'label': 'PDF'},
                    {'id': 'excelFormat', 'value': 'excel', 'label': 'Excel'},
                    {'id': 'csvFormat', 'value': 'csv', 'label': 'CSV'}
                    # Add more formats here if needed
                ],
                'report_types': [
                    {'value': 'Speed', 'label': 'Speed'},
                    {'value': 'Classification', 'label': 'Classification'},
                    {'value': 'Volume', 'label': 'Volume'},
                    {'value': 'Percentile', 'label': 'Percentile'},
                    {'value': 'Speed by Classification', 'label': 'Speed by Classification'}
                    # Add more types here if needed
                ],
                'speed_bins_counts': [17, 11, 6],
                'custom_bin': {'id': 'speedBinCustom', 'label': 'Custom'},
                'company_header': user.company_header,
                'location': user.location,
                'site_code': user.site_code,
                'report_description': user.report_description
            }
    if request.method == "POST":
        # Handle form data, e.g., loading files, generating reports
        if 'load_file' in request.POST:
            # Mimic load_file functionality
            file_path = request.POST.get('file_path')  # Assuming file path is provided for simplicity
            product = request.POST.get('product_type')
            global_data = load_data(file_path, product)
            context['global_data'] = global_data.to_html()  # Example way to pass data to template
    return render(request, 'fox/index.html', context)


@login_required
@csrf_exempt
def upload_file(request):
    if request.method == 'POST' and request.FILES['myfile']:
        myfile = request.FILES['myfile']

        try:

            product_type = request.POST.get('selectDevice', 0)
            data = load_data(myfile, int(product_type))

            request.session['global_data'] = data.to_json()
            request.session['filtered_data'] = data.to_json()
            request.session['direction_filter'] = "All"
            request.session['start_date'] = data["date"].min().strftime('%Y-%m-%d')
            request.session['end_date'] = data["date"].max().strftime('%Y-%m-%d')
            request.session['lanes'] = list(data['lane'].unique())

            # Return a success response, including any relevant information
            response_data = {
                'status': 'success',
                'message': 'Data Loaded Successfully!',
                'total_records': len(data),
                'start_date': data["date"].min().strftime('%Y-%m-%d'),  # Format date if needed
                'end_date': data["date"].max().strftime('%Y-%m-%d'),  # Format date if needed
                'available_lanes': list(data['lane'].unique()),
            }

            return JsonResponse(response_data)
        except Exception as e:
            print("problem")
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'No File Selected'})

@login_required
@csrf_exempt
def filter_data(request):
    # Assuming 'global_data' is stored in the session as a serialized DataFrame
    global_data_serialized = request.session.get('global_data', None)
    if global_data_serialized is None:
        return JsonResponse({'error': 'Global data not found'}, status=404)

    # Deserialize the global_data
    df = pd.read_json(StringIO(global_data_serialized), dtype={'lane': str})

    # Extract filter criteria from request
    direction_filter = request.POST.get('direction', 'All')
    if direction_filter=="Approaching":
        direction_filter="A"
    if direction_filter=="Receding":
        direction_filter="R"    
    start_date_str = request.POST.get('startDate', '')
    end_date_str = request.POST.get('endDate', '')
    lane_filters = request.POST.getlist('lanes')  # Assuming lanes are passed as query parameters

    print(direction_filter,start_date_str,end_date_str,lane_filters)
    # Convert date strings to numpy datetime64
    start_date = np.datetime64(start_date_str) if start_date_str else np.datetime64('1900-01-01')
    end_date = np.datetime64(end_date_str) if end_date_str else np.datetime64('2100-01-01')

    # Apply filters
    mask = (df["date"] >= start_date) & (df["date"] <= end_date)
    filtered_df = df.loc[mask]


    if direction_filter != "All":
        filtered_df = filtered_df[filtered_df["direction"] == direction_filter]

    if lane_filters:  # Assuming 'All' is not a part of lane_filters
        filtered_df = filtered_df[filtered_df["lane"].isin(lane_filters)]

    # Serialize and store the filtered data for future use
    request.session['filtered_data'] = filtered_df.to_json()
    request.session['direction_filter'] = direction_filter
    request.session['start_date'] = start_date_str
    request.session['end_date'] = end_date_str
    request.session['lanes'] = lane_filters

    # Prepare the response
    response_data = {
        'total_records': len(filtered_df),
        # Include any other data you wish to return
    }

    return JsonResponse(response_data)

@login_required
@csrf_exempt
def preview_report(request):
    user = request.user

    selected_bins = request.POST.get('speedBins')  # Get the selected speed bins option
    
    if selected_bins == 'custom':
        selected_bins = request.POST.get('customBinValue', None)  # Get the custom bins value if 'custom' is selected       
    
    request.session['selected_bins'] = selected_bins
    


    # Retrieve data from form fields
    company_header = request.POST.get('companyHeader')
    location = request.POST.get('locationInput')
    site_code = request.POST.get('siteCodeInput')
    report_description = request.POST.get('reportDescription')
    
    # Update the user's information
    user.company_header = company_header if company_header else user.company_header
    user.location = location if location else user.location
    user.site_code = site_code if site_code else user.site_code
    user.report_description = report_description if report_description else user.report_description
    
    # Save the changes to the database
    user.save()

    action = request.POST.get('action', 'preview')  # Default to 'preview'
    request.session['preview'] = True if action == 'preview' else False

    # Parsing form data

    report_type = request.POST.get('reportType')

    lane_filter=request.session['lanes']
    direction_filter = request.session['direction_filter']

    filtered_data=pd.read_json(StringIO(request.session['filtered_data']), dtype={'lane': str})

    filtered_data["Speed Bins"] = speed_to_bin(filtered_data, int(selected_bins))

    if report_type == "Speed":
        return speed_report(direction_filter, lane_filter, filtered_data, request)

    elif report_type == "Classification":
        return class_report(direction_filter, lane_filter, filtered_data, request)


    elif report_type == "Volume":
        return volume_report(direction_filter, lane_filter, filtered_data, request)


    elif report_type == "Percentile":
        return percentile_report(direction_filter, lane_filter, filtered_data, request)


    elif report_type == "Speed by Classification":
        return speed_by_class_report(direction_filter, lane_filter, filtered_data, request)

    else:
        pass

@login_required
@csrf_exempt  # Use only if necessary and understand the security implications
def community_report(request):
    if request.method == 'POST':
        filtered_data=pd.read_json(StringIO(request.session['filtered_data']), dtype={'lane': str})

        # Extract form data
        site = request.POST.get('locationInput')
        timestr = time.strftime("%Y%m%d-%H%M%S")
        file_name = f"{site}_Summary_{timestr}"

        # Assuming 'get_speed_bins' and 'get_violations' are adapted utility functions
        selected_percentile = int(request.POST.get('percentileSelect', 85))  # Default percentile
        speed_bins_tables = get_speed_bins(selected_percentile, filtered_data)

        speed_limit = int(request.POST.get('postedSpeedLimit', 0))
        tolerance = int(request.POST.get('enforcementTolerance', 0))
        enforcement_limit = speed_limit + tolerance + 1
        violations = get_violations(enforcement_limit,filtered_data)
        total_violations = violations["combined"]
        adjusted_violations = total_violations * 1.8
        
        # Convert combined_table DataFrame to HTML
        combined_table_html = speed_bins_tables["combined"][0].to_html(classes='table')  # DataFrame to HTML
        combined_percentile_value = speed_bins_tables["combined"][1]  # Percentile value

        lane_tables_html = {}
        for lane, table_info in speed_bins_tables.items():
            if lane != 'combined':  # Skip 'combined' since it's handled separately
                df_html = table_info[0].to_html(classes='table')  # Convert DataFrame to HTML
                percentile_value = table_info[1]  # Percentile value
                lane_tables_html[lane] = {'html': df_html, 'percentile': percentile_value}


        context = {
            'combined_table_html': combined_table_html,
            'combined_percentile_value': combined_percentile_value,
            'lane_tables_html': lane_tables_html,
            'location': request.POST.get('locationInput'),
            'start_date': request.POST.get('startDate'),
            'end_date': request.POST.get('endDate'),
            'closest_street': request.POST.get('closestCrossStreet'),
            'speed_limit': speed_limit,
            'tolerance': tolerance,
            'enforcement_limit': enforcement_limit,
            'total_violations': violations["combined"],
            'adjusted_violations' : adjusted_violations,
            'lane_violations': violations["lane_wise"],
            'combined_table': speed_bins_tables["combined"],
            'lane_tables': speed_bins_tables,
            'percentile': selected_percentile,
            'category': "Summary",
            'equipment_used': request.POST.get('equipmentUsed'),
            'installed_by': request.POST.get('installedBy'),
            'requested_by': request.POST.get('requestedBy'),
            'needle_angle': 60,
            'show_speed_limit': 'showSpeedLimit' in request.POST,
            'show_tolerance': 'showEnforcementTolerance' in request.POST,
            'show_dates': 'includeAnalysisDates' in request.POST,
            'show_equipment_used': 'includeEquipmentUsed' in request.POST,
            'show_installed_by': 'includeInstalledBy' in request.POST,
            'show_requested_by': 'includeRequestedBy' in request.POST,
            'show_numeric_data': 'includeNumericData' in request.POST,
            'map_location': request.POST.get('locationInput'),
            'file_name': file_name,
        }


        html_content = render(request, 'fox/report.html', context).content.decode('utf-8')
    
        return JsonResponse({'html_content': html_content})

    # Handle non-POST request or redirect as appropriate
    return HttpResponse("Method not allowed", status=405)

@login_required
@csrf_exempt  # Use only if necessary and understand the security implications
def school_zone(request):
    direction_filter=request.POST.get('directionSelect','All')
    lane_filter=request.session['lanes']
    filtered_data=pd.read_json(StringIO(request.session['filtered_data']), dtype={'lane': str})
    filtered_data['time'] = pd.to_datetime(filtered_data['time'], format='%H:%M:%S', errors='coerce').dt.time

    return school_zone_study(request, filtered_data, direction_filter, lane_filter)

