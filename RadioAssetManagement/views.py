# in bv project_root/views.py of een app views.py
from django.shortcuts import render
from django.contrib import messages

def index(request):

    return render(request, "index.html")
