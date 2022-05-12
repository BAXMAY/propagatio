from django.shortcuts import render

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

        # return user to required page
        return render(request, 'charta/index.html', {'output': outputDict})