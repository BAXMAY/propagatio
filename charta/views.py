from calendar import month
from django.shortcuts import render

import os
import json
from django.http import JsonResponse
from supabase import create_client, Client

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# Create your views here.

def index(request):
    if request.method == 'GET':
        return render(request, 'charta/index.html', {'output': ''})

    if request.method == 'POST' and 'run_script' in request.POST:
        # import function to run
        from .export_spreadsheet import export_spreadsheet

        num_week = int(request.POST.get('num_week'))

        month = int(request.POST.get('month'))

        year = int(request.POST.get('year'))

        # call function
        outputDict = export_spreadsheet(num_week)

        updateDict = {
            "jsonString": outputDict,
            "month": month,
            "year": year
        }

        #   Check if data of month year is already in table
        data = supabase.table("nivo_data").select("id").eq("year", year).eq("month", month).limit(1).execute()

        newData = None

        #   Update if exist
        if len(data.data) > 0:
            newData = supabase.table("nivo_data").update(updateDict).eq("id", data.data[0]['id']).execute()
        #   Insert if not exist
        else:
            newData = supabase.table("nivo_data").insert(updateDict).execute()

        assert newData != None
        assert len(newData.data) > 0

        # return user to required page
        return render(request, 'charta/index.html', {'output': outputDict})

def fetchTableData(request):
    '''
    '''

    data = supabase.table("nivo_data").select("jsonString").eq('year', 2022).eq('month', 5).execute()
    assert len(data.data) > 0

    tableData = json.loads(data.data[0]['jsonString'])
    print(tableData)
    return JsonResponse(tableData)
