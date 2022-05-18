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

        # call function
        outputDict = export_spreadsheet(num_week)

        data = supabase.table("nivo_data").update({"jsonString": outputDict}).eq("id", 1).execute()
        assert len(data.data) > 0

        # return user to required page
        return render(request, 'charta/index.html', {'output': outputDict})

def fetchTableData(request):
    '''
    '''

    data = supabase.table("nivo_data").select("jsonString").eq('id', 1).execute()
    assert len(data.data) > 0

    tableData = json.loads(data.data[0]['jsonString'])
    print(tableData)
    return JsonResponse(tableData)
